"""
Configuration for the four-layer VLM/LLM safety-inspection pipeline.

Model mapping relative to the paper (Section 4.3), which ran open weights
locally on 2x RTX 3090:

    Layer                       Paper                 Here
    B1 Perceptual Abstraction   Gemma-3 12B VLM       Claude (vision)
    B2 Regulation Extraction    Llama-3.3 + RAG       Claude (text) + RAG
    B3 Safety Assessment        Gemma-3 12B VLM       Claude (vision)
    B4 Report Generation        DeepSeek-R1           Claude (higher effort)

The paper chose local open models specifically for on-site privacy, and says so;
using a cloud API trades that away for not needing a GPU cluster. That is the
deliberate difference in this reproduction, not an oversight - see docs/.

Every layer is separately configurable so that a cheaper model can be assigned
to the easy layers without touching the rest.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
DATA_DIR = REPO / "data"
RUNS_DIR = DATA_DIR / "runs"
DATASET_DIR = DATA_DIR / "datasets"
RESULTS_DIR = REPO / "results"
RULES_FILE = REPO / "pipeline" / "rules" / "osha_corpus.md"
PROMPTS_DIR = REPO / "pipeline" / "prompts"
CACHE_DIR = DATA_DIR / "llm_cache"

# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------
DEFAULT_MODEL = "claude-opus-5"

# Approximate USD per million tokens, used only for the pre-run cost estimate.
PRICING = {
    "claude-opus-5":    {"in": 5.00, "out": 25.00},
    "claude-sonnet-5":  {"in": 3.00, "out": 15.00},
    "claude-haiku-4-5": {"in": 1.00, "out": 5.00},
}


@dataclass
class LayerConfig:
    model: str = DEFAULT_MODEL
    max_tokens: int = 4000
    effort: str = "medium"
    thinking: bool = True


@dataclass
class PipelineConfig:
    # B1 - describe the scene. Vision, and the foundation everything else sits
    # on, so it gets real effort: a missed object here cannot be recovered later.
    b1: LayerConfig = field(default_factory=lambda: LayerConfig(
        max_tokens=1600, effort="medium"))

    # B2 - turn description + retrieved OSHA text into checkable rules. Text
    # only; the retrieval has already done the hard narrowing.
    b2: LayerConfig = field(default_factory=lambda: LayerConfig(
        max_tokens=1600, effort="medium"))

    # B3 - the actual safe/unsafe call. This is the layer the paper scores, and
    # the one whose errors show up in the confusion matrix, so it gets the most
    # effort of the per-frame layers.
    b3: LayerConfig = field(default_factory=lambda: LayerConfig(
        max_tokens=2000, effort="high"))

    # B4 - synthesise one report from every frame assessment. Runs once per run
    # rather than once per frame, so higher effort is nearly free here. This is
    # where the paper used a reasoning model.
    b4: LayerConfig = field(default_factory=lambda: LayerConfig(
        max_tokens=12000, effort="high"))

    # Single-pass baseline: one VLM call per frame, no rules, no layering.
    # Stands in for the paper's GPT-4o comparator - the point of the comparison
    # is layered-with-rules against monolithic, not vendor against vendor.
    baseline: LayerConfig = field(default_factory=lambda: LayerConfig(
        max_tokens=1200, effort="medium"))

    # RAG
    rag_top_k: int = 6

    # Runtime
    max_retries: int = 4
    timeout_s: float = 240.0
    cache_enabled: bool = True

    def set_model_everywhere(self, model: str):
        for layer in (self.b1, self.b2, self.b3, self.b4, self.baseline):
            layer.model = model


def load_api_key() -> str | None:
    """Resolve the API key from the environment or a .env file at the repo root.

    Returns None when nothing is found; the caller decides whether that is
    fatal. Note the SDK can also authenticate from an `ant auth login` profile
    with no key set at all, so a None here is not necessarily a failure.
    """
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key.strip()

    env_file = REPO / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            if name.strip() == "ANTHROPIC_API_KEY":
                value = value.strip().strip('"').strip("'")
                if value:
                    os.environ["ANTHROPIC_API_KEY"] = value
                    return value
    return None
