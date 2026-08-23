#!/usr/bin/env python3
"""
Generate the Gazebo worlds for scenarios A, B and C from
``sim/go2_sim/config/scenarios.yaml``.

Every hazard in the paper's Table 1 is realised out of geometric primitives
placed to reproduce the *spatial relationship* that constitutes the violation:
a cord lying inside a puddle, a load raised on forks, a ladder leaning against a
machine rather than a wall. That relational geometry is what the downstream VLM
has to read, so it is what the world has to encode.

Also emits OGRE materials + textures so the safety signs carry legible text.
Section 5 of the paper is explicit that sign text materially helps the VLM, and
that removing signs is part of what makes scenarios B and C harder - so the
signs have to actually be readable, not just coloured rectangles.

Usage:
    python scripts/generate_worlds.py
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
SIM = REPO / "sim" / "go2_sim"
WORLDS = SIM / "worlds"
MODELS = SIM / "models"
TEXTURES = MODELS / "materials" / "textures"
SCRIPTS = MODELS / "materials" / "scripts"

# --------------------------------------------------------------------------
# Colours (Gazebo ambient/diffuse RGBA)
# --------------------------------------------------------------------------
COL = {
    "brick":      (0.62, 0.24, 0.17, 1),
    "concrete":   (0.72, 0.72, 0.69, 1),
    "steel":      (0.55, 0.57, 0.60, 1),
    "alu":        (0.80, 0.82, 0.85, 1),
    "yellow":     (0.95, 0.78, 0.05, 1),
    "hivis":      (0.98, 0.45, 0.02, 1),
    "water":      (0.18, 0.32, 0.48, 0.72),
    "cord":       (0.10, 0.10, 0.11, 1),
    "skin":       (0.85, 0.68, 0.55, 1),
    "denim":      (0.24, 0.30, 0.42, 1),
    "shirt_grey": (0.58, 0.58, 0.60, 1),
    "machine":    (0.90, 0.55, 0.10, 1),
    "wood":       (0.68, 0.52, 0.32, 1),
    "dark":       (0.20, 0.20, 0.22, 1),
}


def rgba(c):
    return " ".join(f"{v:g}" for v in c)


# --------------------------------------------------------------------------
# SDF primitive helpers
# --------------------------------------------------------------------------
def _visual_collision(name, geom, colour, cast_shadows=True):
    return f"""
      <collision name="{name}_col">
        <geometry>{geom}</geometry>
      </collision>
      <visual name="{name}_vis">
        <cast_shadows>{'1' if cast_shadows else '0'}</cast_shadows>
        <geometry>{geom}</geometry>
        <material>
          <ambient>{rgba(colour)}</ambient>
          <diffuse>{rgba(colour)}</diffuse>
          <specular>0.1 0.1 0.1 1</specular>
        </material>
      </visual>"""


def box(name, size, pose, colour):
    sx, sy, sz = size
    geom = f"<box><size>{sx:g} {sy:g} {sz:g}</size></box>"
    return f"""
    <link name="{name}">
      <pose>{pose}</pose>
      <gravity>0</gravity>
      {_visual_collision(name, geom, colour)}
    </link>"""


def cyl(name, radius, length, pose, colour):
    geom = f"<cylinder><radius>{radius:g}</radius><length>{length:g}</length></cylinder>"
    return f"""
    <link name="{name}">
      <pose>{pose}</pose>
      <gravity>0</gravity>
      {_visual_collision(name, geom, colour)}
    </link>"""


def sphere(name, radius, pose, colour):
    geom = f"<sphere><radius>{radius:g}</radius></sphere>"
    return f"""
    <link name="{name}">
      <pose>{pose}</pose>
      <gravity>0</gravity>
      {_visual_collision(name, geom, colour)}
    </link>"""


def p(x, y, z, roll=0.0, pitch=0.0, yaw=0.0):
    return f"{x:g} {y:g} {z:g} {roll:g} {pitch:g} {yaw:g}"


def rot(dx, dy, yaw):
    """Rotate a local offset into world frame."""
    c, s = math.cos(yaw), math.sin(yaw)
    return dx * c - dy * s, dx * s + dy * c


# --------------------------------------------------------------------------
# Hazard prop library
#
# Each builder returns a list of link-XML strings, in world coordinates,
# given the hazard's anchor pose (x, y, z, roll, pitch, yaw).
# --------------------------------------------------------------------------
def prop_ladder(tag, x, y, z, yaw, lean=0.30, against_machine=False):
    """Extension ladder leaning back along `yaw`, tilted `lean` from vertical.

    OSHA 1926.1053 wants roughly a 4:1 ratio (about 14 deg from vertical);
    both variants here are deliberately outside that, and neither is tied off.

    Orientation maths: an SDF cylinder runs along its own +Z, and RPY composes
    as Rz(yaw)Ry(pitch)Rx(roll), so RPY (0, tilt, yaw) sends the local +Z to
    (cos(yaw)sin(tilt), sin(yaw)sin(tilt), cos(tilt)) - exactly the ladder's
    long axis. The rungs run along the horizontal perpendicular, which is the
    same construction at pitch = pi/2 and yaw + pi/2.
    """
    links = []
    h = 2.6
    tilt = lean if not against_machine else 0.55  # leaning on a machine = worse
    rail_sep = 0.42

    # Unit vector up the ladder, and the horizontal perpendicular to it.
    dx, dy, dz = math.cos(yaw) * math.sin(tilt), math.sin(yaw) * math.sin(tilt), math.cos(tilt)
    px_, py_ = -math.sin(yaw), math.cos(yaw)

    for i, side in enumerate((-1, 1)):
        bx = x + side * (rail_sep / 2) * px_
        by = y + side * (rail_sep / 2) * py_
        links.append(cyl(f"{tag}_rail{i}", 0.028, h,
                         p(bx + dx * h / 2, by + dy * h / 2, z + dz * h / 2,
                           0, tilt, yaw),
                         COL["alu"]))

    n_rungs = 8
    for r in range(n_rungs):
        f = (r + 0.5) / n_rungs * h
        links.append(cyl(f"{tag}_rung{r}", 0.018, rail_sep,
                         p(x + dx * f, y + dy * f, z + dz * f,
                           0, math.pi / 2, yaw + math.pi / 2),
                         COL["alu"]))
    return links


def prop_forklift(tag, x, y, z, yaw, raised_load=False):
    """Counterbalance forklift. With `raised_load`, bricks sit on elevated forks
    with nobody attending them - 1926.602(c)(1)."""
    links = []
    links.append(box(f"{tag}_body", (1.5, 0.95, 0.95), p(x, y, z + 0.55, 0, 0, yaw), COL["machine"]))
    links.append(box(f"{tag}_cab", (0.75, 0.85, 0.85), p(x, y, z + 1.45, 0, 0, yaw), COL["dark"]))
    # Mast at the front.
    mx, my = rot(0.85, 0, yaw)
    for i, side in enumerate((-1, 1)):
        ox, oy = rot(0.85, side * 0.32, yaw)
        links.append(box(f"{tag}_mast{i}", (0.09, 0.09, 2.1),
                         p(x + ox, y + oy, z + 1.05, 0, 0, yaw), COL["steel"]))
    fork_z = z + (1.35 if raised_load else 0.06)
    for i, side in enumerate((-1, 1)):
        ox, oy = rot(1.35, side * 0.28, yaw)
        links.append(box(f"{tag}_fork{i}", (1.05, 0.11, 0.045),
                         p(x + ox, y + oy, fork_z, 0, 0, yaw), COL["steel"]))
    if raised_load:
        # A pallet of bricks, elevated and unattended.
        px, py = rot(1.30, 0, yaw)
        links.append(box(f"{tag}_pallet", (0.95, 0.85, 0.10),
                         p(x + px, y + py, fork_z + 0.07, 0, 0, yaw), COL["wood"]))
        for r in range(3):
            for c_ in range(2):
                bx, by = rot(1.30 + (r - 1) * 0.26, (c_ - 0.5) * 0.34, yaw)
                links.append(box(f"{tag}_ld{r}{c_}", (0.24, 0.30, 0.22),
                                 p(x + bx, y + by, fork_z + 0.23, 0, 0, yaw), COL["brick"]))
    return links


def prop_bricks(tag, x, y, z, yaw, style="scatter"):
    """Bricks - 1926.25(a) housekeeping / 1926.602(c)(1) aisles kept clear."""
    links = []
    if style == "scatter":
        offs = [(0.0, 0.0, 0.0), (0.42, 0.25, 0.9), (-0.35, 0.4, 0.3), (0.6, -0.3, 1.7),
                (-0.55, -0.25, 2.4), (0.15, 0.62, 0.6), (-0.2, -0.6, 1.2), (0.75, 0.1, 0.4)]
        for i, (dx, dy, a) in enumerate(offs):
            links.append(box(f"{tag}_b{i}", (0.22, 0.11, 0.07),
                             p(x + dx, y + dy, z + 0.035, 0, 0, a), COL["brick"]))
    elif style == "pile":
        for i in range(14):
            layer, idx = divmod(i, 4)
            dx = (idx % 2) * 0.24 - 0.12 + layer * 0.02
            dy = (idx // 2) * 0.13 - 0.065
            links.append(box(f"{tag}_b{i}", (0.22, 0.11, 0.07),
                             p(x + dx, y + dy, z + 0.035 + layer * 0.075, 0, 0, 0.05 * i),
                             COL["brick"]))
    elif style == "stack":
        # A neat stack, but planted in the middle of the walkway.
        for layer in range(6):
            for idx in range(4):
                dx = (idx % 2) * 0.23 - 0.115
                dy = (idx // 2) * 0.12 - 0.06
                a = 0.0 if layer % 2 == 0 else math.pi / 2
                links.append(box(f"{tag}_s{layer}{idx}", (0.22, 0.11, 0.07),
                                 p(x + dx, y + dy, z + 0.035 + layer * 0.075, 0, 0, a),
                                 COL["brick"]))
    return links


def prop_puddle(tag, x, y, z, yaw):
    """Standing water. On its own this is benign; it is the cord lying in it
    that creates the 1926.404(b) / 1926.405(j)(1) violation."""
    return [cyl(f"{tag}_water", 0.85, 0.012, p(x, y, z + 0.006, 0, 0, 0), COL["water"])]


def prop_cord(tag, x, y, z, yaw, through_water=True):
    """Flexible cord snaking across the floor and through the puddle."""
    links = []
    n = 9
    for i in range(n):
        t = i / (n - 1) - 0.5
        wob = 0.28 * math.sin(i * 1.15)
        dx, dy = rot(t * 2.6, wob, yaw)
        seg_yaw = yaw + 0.32 * math.cos(i * 1.15)
        # Same orientation convention as the ladder: pitch pi/2 lays the
        # cylinder flat, pointing along seg_yaw.
        links.append(cyl(f"{tag}_c{i}", 0.017, 0.36,
                         p(x + dx, y + dy, z + 0.017, 0, math.pi / 2, seg_yaw),
                         COL["cord"]))
    # The plug end - no GFCI unit anywhere in the run.
    ex, ey = rot(1.35, 0.0, yaw)
    links.append(box(f"{tag}_plug", (0.11, 0.07, 0.055),
                     p(x + ex, y + ey, z + 0.03, 0, 0, yaw), COL["yellow"]))
    return links


def prop_worker(tag, x, y, z, yaw, hardhat=False, vest=False, height=0.0):
    """A worker. `height` raises them onto a ladder/lift/machine.

    Missing hard hat -> 1926.100(a); the PPE state is exactly what the
    downstream VLM has to call, so the vest and hat are visually distinct.
    """
    links = []
    base = z + height
    links.append(cyl(f"{tag}_leg_l", 0.075, 0.80, p(x - 0.09 * math.sin(yaw), y + 0.09 * math.cos(yaw), base + 0.40, 0, 0, 0), COL["denim"]))
    links.append(cyl(f"{tag}_leg_r", 0.075, 0.80, p(x + 0.09 * math.sin(yaw), y - 0.09 * math.cos(yaw), base + 0.40, 0, 0, 0), COL["denim"]))
    torso_col = COL["hivis"] if vest else COL["shirt_grey"]
    links.append(box(f"{tag}_torso", (0.26, 0.44, 0.62), p(x, y, base + 1.11, 0, 0, yaw), torso_col))
    # Arms.
    for i, side in enumerate((-1, 1)):
        ox, oy = rot(0.0, side * 0.27, yaw)
        links.append(cyl(f"{tag}_arm{i}", 0.055, 0.58, p(x + ox, y + oy, base + 1.12, 0, 0, 0), torso_col))
    links.append(cyl(f"{tag}_neck", 0.05, 0.09, p(x, y, base + 1.46, 0, 0, 0), COL["skin"]))
    links.append(sphere(f"{tag}_head", 0.115, p(x, y, base + 1.60, 0, 0, 0), COL["skin"]))
    if hardhat:
        links.append(sphere(f"{tag}_hat", 0.135, p(x, y, base + 1.655, 0, 0, 0), COL["yellow"]))
        links.append(cyl(f"{tag}_brim", 0.165, 0.02, p(x, y, base + 1.60, 0, 0, 0), COL["yellow"]))
    return links


def prop_ppe_on_floor(tag, x, y, z, yaw):
    """Hard hat and vest lying on the floor instead of being worn - the visual
    evidence the paper's Frame 16 walkthrough turns on."""
    links = []
    hx, hy = rot(0.55, 0.30, yaw)
    links.append(sphere(f"{tag}_hat", 0.135, p(x + hx, y + hy, z + 0.10, 0, 0, 0), COL["yellow"]))
    vx, vy = rot(0.30, -0.35, yaw)
    links.append(box(f"{tag}_vest", (0.42, 0.36, 0.05), p(x + vx, y + vy, z + 0.025, 0, 0, yaw + 0.4), COL["hivis"]))
    return links


def prop_machine(tag, x, y, z, yaw, large=False):
    """Industrial machine. When `large`, its top deck sits high enough that
    standing on it without edge protection triggers 1926.501(b)(1)."""
    links = []
    if large:
        links.append(box(f"{tag}_base", (2.2, 1.5, 1.75), p(x, y, z + 0.875, 0, 0, yaw), COL["machine"]))
        links.append(box(f"{tag}_deck", (2.3, 1.6, 0.08), p(x, y, z + 1.79, 0, 0, yaw), COL["steel"]))
    else:
        links.append(box(f"{tag}_base", (1.2, 0.9, 1.05), p(x, y, z + 0.525, 0, 0, yaw), COL["machine"]))
        links.append(box(f"{tag}_top", (1.25, 0.95, 0.06), p(x, y, z + 1.08, 0, 0, yaw), COL["steel"]))
    return links


def prop_lift_table(tag, x, y, z, yaw, platform_h=1.55):
    """Scissor-type material lift. Rated for material, not people -
    1926.552(b)(1)."""
    links = []
    links.append(box(f"{tag}_base", (1.25, 0.85, 0.14), p(x, y, z + 0.07, 0, 0, yaw), COL["steel"]))
    # Scissor legs, drawn as crossed diagonals.
    for i, side in enumerate((-1, 1)):
        ox, oy = rot(0.0, side * 0.34, yaw)
        for j, sgn in enumerate((1, -1)):
            links.append(box(f"{tag}_sc{i}{j}", (1.05, 0.06, 0.06),
                             p(x + ox, y + oy, z + platform_h / 2,
                               0, sgn * 0.95, yaw), COL["steel"]))
    links.append(box(f"{tag}_platform", (1.30, 0.90, 0.09),
                     p(x, y, z + platform_h, 0, 0, yaw), COL["steel"]))
    return links


def prop_crates(tag, x, y, z, yaw):
    """Crates stacked into an improvised step - not an approved means of access,
    1926.1051(a)."""
    links = []
    hs = [(0.0, 0.0, 0.45), (0.55, 0.08, 0.80), (1.05, -0.05, 1.15)]
    for i, (dx, dy, top) in enumerate(hs):
        ox, oy = rot(dx, dy, yaw)
        links.append(box(f"{tag}_cr{i}", (0.52, 0.44, top),
                         p(x + ox, y + oy, z + top / 2, 0, 0, yaw + 0.06 * i), COL["wood"]))
    return links


def prop_bricks_on_platform(tag, x, y, z, yaw, height=1.60):
    """Bricks left on a raised platform beside someone's feet -
    1926.250(a)(1)."""
    links = []
    for i in range(4):
        ox, oy = rot(-0.38 + (i % 2) * 0.24, 0.22 + (i // 2) * 0.13, yaw)
        links.append(box(f"{tag}_pb{i}", (0.22, 0.11, 0.07),
                         p(x + ox, y + oy, z + height + 0.08 + (i // 2) * 0.075, 0, 0, yaw), COL["brick"]))
    return links


def prop_sign(tag, x, y, z, yaw, texture):
    """Safety sign as a textured plate. Uses an OGRE material so the wording is
    actually legible to the camera."""
    return [f"""
    <link name="{tag}_sign">
      <pose>{p(x, y, z, 0, 0, yaw)}</pose>
      <gravity>0</gravity>
      <collision name="{tag}_sign_col">
        <geometry><box><size>0.04 0.90 0.60</size></box></geometry>
      </collision>
      <visual name="{tag}_sign_vis">
        <geometry><box><size>0.04 0.90 0.60</size></box></geometry>
        <material>
          <script>
            <uri>model://materials/scripts</uri>
            <uri>model://materials/textures</uri>
            <name>Go2Sim/{texture}</name>
          </script>
        </material>
      </visual>
    </link>""",
            cyl(f"{tag}_post", 0.035, z, p(x, y, z / 2, 0, 0, 0), COL["steel"])]


# --------------------------------------------------------------------------
# Map prop tokens (from scenarios.yaml) onto builders
# --------------------------------------------------------------------------
def build_props(hazard):
    hid = hazard["id"]
    x, y, z, _r, _pi, yaw = hazard["pose"]
    links = []
    for prop in hazard["props"]:
        tag = f"h{hid}_{prop}"
        if prop == "ladder_leaning":
            links += prop_ladder(tag, x, y, z, yaw, lean=0.34)
        elif prop == "ladder_on_machine":
            links += prop_ladder(tag, x + 0.75, y, z, yaw, against_machine=True)
        elif prop == "forklift":
            links += prop_forklift(tag, x + 1.5, y - 0.9, z, yaw + 0.6)
        elif prop == "forklift_raised_load":
            links += prop_forklift(tag, x, y, z, yaw, raised_load=True)
        elif prop == "brick_scatter":
            links += prop_bricks(tag, x, y, z, yaw, "scatter")
        elif prop == "brick_pile":
            links += prop_bricks(tag, x, y, z, yaw, "pile")
        elif prop == "brick_stack_walkway":
            links += prop_bricks(tag, x, y, z, yaw, "stack")
        elif prop == "water_puddle":
            links += prop_puddle(tag, x, y, z, yaw)
        elif prop == "extension_cord":
            links += prop_cord(tag, x, y, z, yaw)
        elif prop == "flexible_cord":
            links += prop_cord(tag, x, y, z, yaw, through_water=True)
        elif prop == "worker_no_ppe":
            links += prop_worker(tag, x, y, z, yaw, hardhat=False, vest=False)
        elif prop == "worker_vest_no_hardhat":
            links += prop_worker(tag, x, y, z, yaw, hardhat=False, vest=True, height=1.05)
        elif prop == "ppe_on_floor":
            links += prop_ppe_on_floor(tag, x, y, z, yaw)
        elif prop == "machine_block":
            links += prop_machine(tag, x + 0.75, y, z, yaw, large=False)
        elif prop == "large_machine":
            links += prop_machine(tag, x, y, z, yaw, large=True)
        elif prop == "worker_on_machine":
            links += prop_worker(tag, x, y, z, yaw + 1.2, hardhat=True, vest=True, height=1.83)
        elif prop == "lift_table":
            links += prop_lift_table(tag, x, y, z, yaw)
        elif prop == "worker_on_lift":
            links += prop_worker(tag, x, y, z, yaw, hardhat=True, vest=True, height=1.64)
        elif prop == "bricks_on_platform":
            links += prop_bricks_on_platform(tag, x, y, z, yaw)
        elif prop == "stacked_crates_as_step":
            links += prop_crates(tag, x, y, z, yaw)
        else:
            print(f"  ! unknown prop '{prop}' on hazard {hid}", file=sys.stderr)
    return links


# --------------------------------------------------------------------------
# Lab shell
# --------------------------------------------------------------------------
def build_lab(lab):
    sx, sy = lab["size_x"], lab["size_y"]
    h, t = lab["wall_height"], lab["wall_thickness"]
    links = []
    walls = [
        ("n", (sx, t, h), (sx / 2, sy, h / 2)),
        ("s", (sx, t, h), (sx / 2, 0.0, h / 2)),
        ("e", (t, sy, h), (sx, sy / 2, h / 2)),
        ("w", (t, sy, h), (0.0, sy / 2, h / 2)),
    ]
    for name, size, pos in walls:
        links.append(box(f"wall_{name}", size, p(*pos), COL["concrete"]))
    # A couple of interior columns: they occlude, which is what makes SLAM loop
    # closure and Nav2 replanning non-trivial rather than an empty-box demo.
    for i, (cx, cy) in enumerate([(4.2, 6.4), (8.4, 6.4)]):
        links.append(box(f"column_{i}", (0.35, 0.35, h), p(cx, cy, h / 2), COL["concrete"]))
    return links


# --------------------------------------------------------------------------
# Sign textures
# --------------------------------------------------------------------------
def make_sign_textures(signs):
    """Render each sign's wording to a PNG and emit one OGRE material each."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("! Pillow not available - signs will be untextured.", file=sys.stderr)
        return {}

    TEXTURES.mkdir(parents=True, exist_ok=True)
    SCRIPTS.mkdir(parents=True, exist_ok=True)

    def load_font(size):
        for cand in ("arialbd.ttf", "DejaVuSans-Bold.ttf", "arial.ttf"):
            try:
                return ImageFont.truetype(cand, size)
            except OSError:
                continue
        return ImageFont.load_default()

    mats = {}
    for sign in signs:
        text = sign["text"]
        # Header word drives the colour, per ANSI Z535: DANGER red, CAUTION yellow.
        header, _, body = text.partition(" - ")
        is_danger = header.strip().upper().startswith("DANGER")
        hdr_bg = (196, 18, 26) if is_danger else (255, 194, 14)
        hdr_fg = (255, 255, 255) if is_danger else (0, 0, 0)

        W, H = 768, 512
        img = Image.new("RGB", (W, H), (255, 255, 255))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 150], fill=hdr_bg)
        f_hdr = load_font(96)
        hw = d.textbbox((0, 0), header.strip(), font=f_hdr)
        d.text(((W - (hw[2] - hw[0])) / 2, (150 - (hw[3] - hw[1])) / 2 - hw[1]),
               header.strip(), font=f_hdr, fill=hdr_fg)

        f_body = load_font(52)
        words, lines, cur = body.split(), [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            if d.textbbox((0, 0), trial, font=f_body)[2] > W - 60 and cur:
                lines.append(cur)
                cur = w
            else:
                cur = trial
        if cur:
            lines.append(cur)
        yy = 190
        for ln in lines:
            bb = d.textbbox((0, 0), ln, font=f_body)
            d.text(((W - (bb[2] - bb[0])) / 2, yy), ln, font=f_body, fill=(0, 0, 0))
            yy += 62
        d.rectangle([0, 0, W - 1, H - 1], outline=(0, 0, 0), width=6)

        name = sign["id"]
        img.save(TEXTURES / f"{name}.png")
        mats[name] = name

    with open(SCRIPTS / "go2_sim.material", "w", encoding="utf-8") as fh:
        for name in mats:
            fh.write(f"""material Go2Sim/{name}
{{
  technique
  {{
    pass
    {{
      ambient 1.0 1.0 1.0 1.0
      diffuse 1.0 1.0 1.0 1.0
      texture_unit
      {{
        texture {name}.png
        filtering trilinear
      }}
    }}
  }}
}}

""")
    print(f"  signs: {len(mats)} texture(s) + material script")
    return mats


# --------------------------------------------------------------------------
# World assembly
# --------------------------------------------------------------------------
WORLD_HEADER = """<?xml version="1.0" ?>
<!-- GENERATED by scripts/generate_worlds.py - do not edit by hand.
     Edit sim/go2_sim/config/scenarios.yaml and regenerate. -->
<sdf version="1.6">
  <world name="construction_lab_{sid}">

    <physics type="ode">
      <max_step_size>0.004</max_step_size>
      <real_time_update_rate>250</real_time_update_rate>
    </physics>

    <!-- Lighting is tuned for the camera, not for looking pretty: too much
         ambient washes every surface toward white and the VLM loses the colour
         cues (hi-vis orange, yellow hard hat, red brick) it needs to tell
         hazards apart. -->
    <scene>
      <ambient>0.33 0.33 0.35 1</ambient>
      <background>0.62 0.66 0.72 1</background>
      <shadows>0</shadows>
    </scene>

    <!-- Sun declared inline rather than as <include>model://sun</include>:
         the include form makes Gazebo reach out to models.gazebosim.org, which
         stalls world load (and fails outright with no network). -->
    <light name="sun" type="directional">
      <pose>0 0 12 0 0 0</pose>
      <diffuse>0.75 0.75 0.73 1</diffuse>
      <specular>0.15 0.15 0.15 1</specular>
      <direction>-0.4 0.3 -0.9</direction>
      <cast_shadows>0</cast_shadows>
    </light>

    <!-- Extra fill light: the lab is enclosed, and the RGB frames feed a VLM,
         so the scene has to be bright enough to read. -->
    <light name="fill" type="directional">
      <pose>6 4.5 6 0 0 0</pose>
      <diffuse>0.35 0.35 0.38 1</diffuse>
      <specular>0.05 0.05 0.05 1</specular>
      <direction>-0.3 -0.4 -0.9</direction>
      <cast_shadows>0</cast_shadows>
    </light>

    <model name="ground">
      <static>1</static>
      <link name="ground_link">
        <collision name="ground_col">
          <geometry><plane><normal>0 0 1</normal><size>60 60</size></plane></geometry>
          <surface><friction><ode><mu>0.9</mu><mu2>0.9</mu2></ode></friction></surface>
        </collision>
        <visual name="ground_vis">
          <geometry><plane><normal>0 0 1</normal><size>60 60</size></plane></geometry>
          <material>
            <ambient>0.30 0.30 0.32 1</ambient>
            <diffuse>0.38 0.38 0.40 1</diffuse>
          </material>
        </visual>
      </link>
    </model>
"""

WORLD_FOOTER = """
  </world>
</sdf>
"""


def build_world(sid, scen, lab):
    parts = [WORLD_HEADER.format(sid=sid)]

    # Static shell.
    parts.append('    <model name="lab_shell">\n      <static>1</static>')
    parts.extend(build_lab(lab))
    parts.append("\n    </model>\n")

    # Signs.
    if scen.get("signs"):
        parts.append('    <model name="safety_signs">\n      <static>1</static>')
        for sign in scen["signs"]:
            sx, sy, sz, _r, _p, syaw = sign["pose"]
            parts.extend(prop_sign(sign["id"], sx, sy, sz, syaw, sign["id"]))
        parts.append("\n    </model>\n")

    # One static model per hazard, named by its Table 1 id so that anything
    # downstream can trace a Gazebo link straight back to an OSHA reference.
    for hz in scen["hazards"]:
        parts.append(f'    <!-- {hz["id"]}: {hz["violation"]} [{hz["osha_ref"]}] -->')
        parts.append(f'    <model name="hazard_{hz["id"]}">\n      <static>1</static>')
        parts.extend(build_props(hz))
        parts.append("\n    </model>\n")

    parts.append(WORLD_FOOTER)
    return "\n".join(parts)


def main():
    cfg = yaml.safe_load((SIM / "config" / "scenarios.yaml").read_text(encoding="utf-8"))
    lab = cfg["lab"]
    WORLDS.mkdir(parents=True, exist_ok=True)

    all_signs = {}
    for scen in cfg["scenarios"].values():
        for s in scen.get("signs", []):
            all_signs[s["id"]] = s
    make_sign_textures(list(all_signs.values()))

    for sid, scen in cfg["scenarios"].items():
        xml = build_world(sid, scen, lab)
        out = WORLDS / f"construction_scenario_{sid}.world"
        out.write_text(xml, encoding="utf-8")
        n_links = xml.count("<link name=")
        print(f"  scenario {sid}: {len(scen['hazards'])} hazards, "
              f"{len(scen.get('signs', []))} sign(s), {n_links} links -> {out.name}")

    print("Worlds generated.")


if __name__ == "__main__":
    main()
