"""
Thin wrapper over the Anthropic SDK for the inspection pipeline.

Adds the three things a batch job over hundreds of frames actually needs:

* **On-disk response cache**, keyed by a hash of the full request. Re-running
  the pipeline after changing one layer should not re-pay for the layers that
  did not change, and a crash 300 frames in should not cost the first 300 again.
* **Token and cost accounting**, so a run reports what it spent.
* **Refusal handling** with server-side fallback, per Anthropic's guidance for
  Opus 5. Construction-hazard imagery involves people in danger, so an
  occasional safety-classifier refusal is realistic; a refused frame must be
  recorded as such, never silently counted as "safe".
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from . import config


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    calls: int = 0
    cached_calls: int = 0
    refusals: int = 0
    by_model: dict = field(default_factory=dict)

    def add(self, model, u, cached=False):
        self.calls += 1
        if cached:
            self.cached_calls += 1
            return
        it = getattr(u, "input_tokens", 0) or 0
        ot = getattr(u, "output_tokens", 0) or 0
        cr = getattr(u, "cache_read_input_tokens", 0) or 0
        cw = getattr(u, "cache_creation_input_tokens", 0) or 0
        self.input_tokens += it
        self.output_tokens += ot
        self.cache_read_tokens += cr
        self.cache_write_tokens += cw
        m = self.by_model.setdefault(model, {"in": 0, "out": 0, "cache_read": 0})
        m["in"] += it
        m["out"] += ot
        m["cache_read"] += cr

    def cost_usd(self) -> float:
        total = 0.0
        for model, t in self.by_model.items():
            p = config.PRICING.get(model)
            if not p:
                continue
            # Cache reads bill at 10% of the input rate; cache writes at 125%.
            # Close enough for a run summary.
            total += (t["in"] / 1e6) * p["in"]
            total += (t["out"] / 1e6) * p["out"]
            total += (t["cache_read"] / 1e6) * p["in"] * 0.10
        return total

    def summary(self) -> str:
        return (f"{self.calls} calls ({self.cached_calls} from cache), "
                f"{self.input_tokens:,} in / {self.output_tokens:,} out tokens, "
                f"{self.cache_read_tokens:,} cache-read, "
                f"{self.refusals} refusal(s), ~${self.cost_usd():.2f}")


class RefusalError(RuntimeError):
    """The model declined the request (stop_reason == 'refusal')."""


class ClaudeClient:
    def __init__(self, cfg: config.PipelineConfig, verbose: bool = True):
        self.cfg = cfg
        self.verbose = verbose
        self.usage = Usage()

        config.load_api_key()
        # A bare constructor also picks up an `ant auth login` profile, so we do
        # not require ANTHROPIC_API_KEY to be set.
        self.client = anthropic.Anthropic(
            max_retries=cfg.max_retries,
            timeout=cfg.timeout_s,
        )

        self.cache_dir = config.CACHE_DIR
        if cfg.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    @staticmethod
    def image_block(path: Path, media_type: str | None = None) -> dict:
        """Base64 image content block."""
        data = Path(path).read_bytes()
        if media_type is None:
            ext = Path(path).suffix.lower()
            media_type = {
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp",
            }.get(ext, "image/jpeg")
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.standard_b64encode(data).decode("utf-8"),
            },
        }

    # ------------------------------------------------------------------
    def _cache_key(self, model, system, messages, max_tokens, effort) -> str:
        h = hashlib.sha256()
        h.update(json.dumps({
            "model": model,
            "system": system,
            "messages": messages,
            "max_tokens": max_tokens,
            "effort": effort,
        }, sort_keys=True, default=str).encode("utf-8"))
        return h.hexdigest()[:32]

    def _cache_get(self, key):
        if not self.cfg.cache_enabled:
            return None
        f = self.cache_dir / f"{key}.json"
        if f.exists():
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None
        return None

    def _cache_put(self, key, payload):
        if not self.cfg.cache_enabled:
            return
        try:
            (self.cache_dir / f"{key}.json").write_text(
                json.dumps(payload), encoding="utf-8")
        except OSError:
            pass

    # ------------------------------------------------------------------
    def complete(self, *, layer: config.LayerConfig, system, messages,
                 label: str = "") -> str:
        """Run one request and return the concatenated text.

        `system` may be a string or a list of content blocks (use the list form
        with cache_control to cache a long stable prefix such as the OSHA
        corpus).
        """
        key = self._cache_key(layer.model, system, messages,
                              layer.max_tokens, layer.effort)
        hit = self._cache_get(key)
        if hit is not None:
            self.usage.add(layer.model, None, cached=True)
            if hit.get("refused"):
                raise RefusalError(hit.get("text", "refused"))
            return hit["text"]

        params = {
            "model": layer.model,
            "max_tokens": layer.max_tokens,
            "system": system,
            "messages": messages,
            "output_config": {"effort": layer.effort},
        }
        if layer.thinking:
            params["thinking"] = {"type": "adaptive"}

        # Server-side fallback: on a safety-classifier refusal the request is
        # rerouted rather than lost. Recommended default for Opus 5.
        params["betas"] = ["server-side-fallback-2026-07-01"]
        params["fallbacks"] = "default"

        last_exc = None
        for attempt in range(self.cfg.max_retries):
            try:
                # Streaming: max_tokens is large on B4 and long requests would
                # otherwise risk an HTTP timeout.
                with self.client.beta.messages.stream(**params) as stream:
                    msg = stream.get_final_message()
                break
            except (anthropic.RateLimitError, anthropic.APITimeoutError,
                    anthropic.APIConnectionError, anthropic.InternalServerError) as exc:
                last_exc = exc
                wait = min(2 ** attempt * 3, 45)
                if self.verbose:
                    print(f"      [{label}] {type(exc).__name__}, retry in {wait}s")
                time.sleep(wait)
            except anthropic.APIStatusError as exc:
                # 400/404 and friends are not worth retrying.
                raise RuntimeError(f"[{label}] API error {exc.status_code}: {exc}") from exc
        else:
            raise RuntimeError(f"[{label}] gave up after retries: {last_exc}")

        self.usage.add(layer.model, msg.usage)

        if getattr(msg, "stop_reason", None) == "refusal":
            self.usage.refusals += 1
            detail = getattr(msg, "stop_details", None)
            reason = getattr(detail, "category", None) or "unspecified"
            self._cache_put(key, {"text": f"refusal:{reason}", "refused": True})
            raise RefusalError(f"[{label}] model refused (category={reason})")

        text = "".join(b.text for b in msg.content if b.type == "text").strip()
        self._cache_put(key, {"text": text, "refused": False})
        return text
