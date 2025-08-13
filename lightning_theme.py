# lightning_theme.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Tuple, Dict, Any, Iterable, Optional
import colorsys
import json
import math
import random


# ---------- Types ----------
ColorA = Tuple[int, int, int, int]  # RGBA, 0-255 per channel


# ---------- Helpers ----------
def _clamp_u8(x: int) -> int:
    return 0 if x < 0 else 255 if x > 255 else int(x)


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else float(x)


def _clamp_pos(x: float, eps: float = 0.0) -> float:
    return eps if x < eps else float(x)


def _clamp_color(c: ColorA) -> ColorA:
    r, g, b, a = c
    return _clamp_u8(r), _clamp_u8(g), _clamp_u8(b), _clamp_u8(a)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_color(c1: ColorA, c2: ColorA, t: float) -> ColorA:
    return (
        _clamp_u8(round(_lerp(c1[0], c2[0], t))),
        _clamp_u8(round(_lerp(c1[1], c2[1], t))),
        _clamp_u8(round(_lerp(c1[2], c2[2], t))),
        _clamp_u8(round(_lerp(c1[3], c2[3], t))),
    )


def _rgb_to_hsv_u8(c: ColorA) -> Tuple[float, float, float, int]:
    r, g, b, a = c
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    return h, s, v, a


def _hsv_to_rgb_u8(h: float, s: float, v: float, a: int) -> ColorA:
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return _clamp_u8(round(r * 255)), _clamp_u8(round(g * 255)), _clamp_u8(round(b * 255)), _clamp_u8(a)


# ---------- Style ----------
@dataclass(slots=True, frozen=True)
class LightningStyle:
    """
    Theme parameters for rendering stylized lightning bolts. All values are engine-agnostic;
    they describe how a renderer should shape and color the effect.

    Fields kept from your original version remain with the same names to avoid breaking code.
    """

    # Visuals (layered stroke)
    core_color: ColorA = (255, 255, 255, 240)
    glow_color: ColorA = (140, 180, 255, 170)
    outer_glow_color: ColorA = (90, 150, 255, 110)
    core_thickness: int = 2
    glow_thickness: int = 6
    outer_glow_thickness: int = 10

    # Shape / noise
    roughness: float = 0.9          # amplitude of jitter; 0..~2
    depth: int = 5                  # subdivision depth (detail level)
    noise_scale: float = 1.0        # spatial frequency control
    taper: float = 0.75             # 0=no taper, 1=strong taper along the bolt

    # Branching
    branch_chance: float = 0.45     # base probability to start a branch
    branch_depth: int = 3           # how many recursive branch levels
    branch_angle_spread_deg: float = 35.0
    branch_probability_decay: float = 0.7
    branch_length_decay: float = 0.6
    branch_thickness_scale: float = 0.6

    # Flash / bloom
    flash_alpha_base: float = 0.13
    flash_alpha_jitter: float = 0.07
    flash_fade_speed: float = 2.0    # alpha per second
    bloom_power: float = 1.0         # for additive bloom / post fx

    # Animation
    speed: float = 1.0               # global animation multiplier
    flicker_strength: float = 0.2    # 0..1 intensity modulation
    flicker_hz: float = 12.0         # how fast flicker oscillates

    # ---------------- Lifecycle / validation ----------------
    def __post_init__(self):
        # clamp colors
        object.__setattr__(self, "core_color", _clamp_color(self.core_color))
        object.__setattr__(self, "glow_color", _clamp_color(self.glow_color))
        object.__setattr__(self, "outer_glow_color", _clamp_color(self.outer_glow_color))

        # ensure thickness order (outer >= glow >= core) and minimums
        core = max(1, int(self.core_thickness))
        glow = max(core, int(self.glow_thickness))
        outer = max(glow, int(self.outer_glow_thickness))
        object.__setattr__(self, "core_thickness", core)
        object.__setattr__(self, "glow_thickness", glow)
        object.__setattr__(self, "outer_glow_thickness", outer)

        # sane ranges
        object.__setattr__(self, "roughness", max(0.0, float(self.roughness)))
        object.__setattr__(self, "depth", max(1, int(self.depth)))
        object.__setattr__(self, "noise_scale", _clamp_pos(self.noise_scale, 1e-4))
        object.__setattr__(self, "taper", _clamp01(self.taper))

        object.__setattr__(self, "branch_chance", _clamp01(self.branch_chance))
        object.__setattr__(self, "branch_depth", max(0, int(self.branch_depth)))
        object.__setattr__(self, "branch_angle_spread_deg", max(0.0, float(self.branch_angle_spread_deg)))
        object.__setattr__(self, "branch_probability_decay", _clamp01(self.branch_probability_decay))
        object.__setattr__(self, "branch_length_decay", _clamp01(self.branch_length_decay))
        object.__setattr__(self, "branch_thickness_scale", _clamp01(self.branch_thickness_scale))

        object.__setattr__(self, "flash_alpha_base", max(0.0, float(self.flash_alpha_base)))
        object.__setattr__(self, "flash_alpha_jitter", max(0.0, float(self.flash_alpha_jitter)))
        object.__setattr__(self, "flash_fade_speed", max(0.0, float(self.flash_fade_speed)))
        object.__setattr__(self, "bloom_power", max(0.0, float(self.bloom_power)))

        object.__setattr__(self, "speed", max(0.0, float(self.speed)))
        object.__setattr__(self, "flicker_strength", _clamp01(self.flicker_strength))
        object.__setattr__(self, "flicker_hz", max(0.0, float(self.flicker_hz)))

    # ---------------- Convenience API ----------------
    def as_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict (JSON safe)."""
        return asdict(self)

    def to_json(self, **json_kwargs) -> str:
        """Serialize to JSON."""
        return json.dumps(self.as_dict(), **json_kwargs)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> LightningStyle:
        """Construct from a dict (missing keys fall back to dataclass defaults)."""
        return LightningStyle(**d)

    @staticmethod
    def from_json(s: str) -> LightningStyle:
        return LightningStyle.from_dict(json.loads(s))

    def scaled(self, alpha_mult: float = 1.0, thickness_mult: float = 1.0) -> LightningStyle:
        """Return a style with scaled layer alpha and thickness (useful for distance LOD)."""
        def _scale_a(c: ColorA) -> ColorA:
            r, g, b, a = c
            return (r, g, b, _clamp_u8(round(a * alpha_mult)))
        return LightningStyle(
            core_color=_scale_a(self.core_color),
            glow_color=_scale_a(self.glow_color),
            outer_glow_color=_scale_a(self.outer_glow_color),
            core_thickness=max(1, round(self.core_thickness * thickness_mult)),
            glow_thickness=max(1, round(self.glow_thickness * thickness_mult)),
            outer_glow_thickness=max(1, round(self.outer_glow_thickness * thickness_mult)),
            roughness=self.roughness,
            depth=self.depth,
            noise_scale=self.noise_scale,
            taper=self.taper,
            branch_chance=self.branch_chance,
            branch_depth=self.branch_depth,
            branch_angle_spread_deg=self.branch_angle_spread_deg,
            branch_probability_decay=self.branch_probability_decay,
            branch_length_decay=self.branch_length_decay,
            branch_thickness_scale=self.branch_thickness_scale,
            flash_alpha_base=self.flash_alpha_base,
            flash_alpha_jitter=self.flash_alpha_jitter,
            flash_fade_speed=self.flash_fade_speed,
            bloom_power=self.bloom_power,
            speed=self.speed,
            flicker_strength=self.flicker_strength,
            flicker_hz=self.flicker_hz,
        )

    def with_variation(self, rng: Optional[random.Random] = None, amount: float = 0.1) -> LightningStyle:
        """
        Jitter colors and a few dynamics to avoid repetitive strokes.
        'amount' is 0..1 and controls how far we wander.
        """
        r = rng or random
        amt = max(0.0, float(amount))

        def vary_color(c: ColorA, sat_var=0.1, val_var=0.1, a_var=0.1) -> ColorA:
            h, s, v, a = _rgb_to_hsv_u8(c)
            s = _clamp01(s * (1 + r.uniform(-sat_var, sat_var) * amt))
            v = _clamp01(v * (1 + r.uniform(-val_var, val_var) * amt))
            a = _clamp_u8(round(a * (1 + r.uniform(-a_var, a_var) * amt)))
            # small hue drift
            h = (h + r.uniform(-0.02, 0.02) * amt) % 1.0
            return _hsv_to_rgb_u8(h, s, v, a)

        return LightningStyle(
            core_color=vary_color(self.core_color),
            glow_color=vary_color(self.glow_color),
            outer_glow_color=vary_color(self.outer_glow_color),
            core_thickness=max(1, self.core_thickness + r.choice([-1, 0, 1])),
            glow_thickness=max(1, self.glow_thickness + r.choice([-1, 0, 1])),
            outer_glow_thickness=max(1, self.outer_glow_thickness + r.choice([-1, 0, 1])),
            roughness=self.roughness * (1 + r.uniform(-0.1, 0.15) * amt),
            depth=self.depth,
            noise_scale=self.noise_scale * (1 + r.uniform(-0.15, 0.15) * amt),
            taper=_clamp01(self.taper * (1 + r.uniform(-0.2, 0.2) * amt)),
            branch_chance=_clamp01(self.branch_chance * (1 + r.uniform(-0.2, 0.2) * amt)),
            branch_depth=self.branch_depth,
            branch_angle_spread_deg=max(0.0, self.branch_angle_spread_deg * (1 + r.uniform(-0.2, 0.2) * amt)),
            branch_probability_decay=_clamp01(self.branch_probability_decay * (1 + r.uniform(-0.15, 0.15) * amt)),
            branch_length_decay=_clamp01(self.branch_length_decay * (1 + r.uniform(-0.15, 0.15) * amt)),
            branch_thickness_scale=_clamp01(self.branch_thickness_scale * (1 + r.uniform(-0.15, 0.15) * amt)),
            flash_alpha_base=max(0.0, self.flash_alpha_base * (1 + r.uniform(-0.2, 0.2) * amt)),
            flash_alpha_jitter=max(0.0, self.flash_alpha_jitter * (1 + r.uniform(-0.2, 0.2) * amt)),
            flash_fade_speed=max(0.0, self.flash_fade_speed * (1 + r.uniform(-0.2, 0.2) * amt)),
            bloom_power=max(0.0, self.bloom_power * (1 + r.uniform(-0.2, 0.2) * amt)),
            speed=max(0.0, self.speed * (1 + r.uniform(-0.2, 0.2) * amt)),
            flicker_strength=_clamp01(self.flicker_strength * (1 + r.uniform(-0.3, 0.3) * amt)),
            flicker_hz=max(0.0, self.flicker_hz * (1 + r.uniform(-0.2, 0.2) * amt)),
        )

    def tinted(self, hue_shift_deg: float = 0.0, sat_mult: float = 1.0, val_mult: float = 1.0) -> LightningStyle:
        """Shift hue and scale saturation/value for all three layers."""
        def tint(c: ColorA) -> ColorA:
            h, s, v, a = _rgb_to_hsv_u8(c)
            h = (h + hue_shift_deg / 360.0) % 1.0
            s = _clamp01(s * sat_mult)
            v = _clamp01(v * val_mult)
            return _hsv_to_rgb_u8(h, s, v, a)

        return LightningStyle(
            core_color=tint(self.core_color),
            glow_color=tint(self.glow_color),
            outer_glow_color=tint(self.outer_glow_color),
            core_thickness=self.core_thickness,
            glow_thickness=self.glow_thickness,
            outer_glow_thickness=self.outer_glow_thickness,
            roughness=self.roughness,
            depth=self.depth,
            noise_scale=self.noise_scale,
            taper=self.taper,
            branch_chance=self.branch_chance,
            branch_depth=self.branch_depth,
            branch_angle_spread_deg=self.branch_angle_spread_deg,
            branch_probability_decay=self.branch_probability_decay,
            branch_length_decay=self.branch_length_decay,
            branch_thickness_scale=self.branch_thickness_scale,
            flash_alpha_base=self.flash_alpha_base,
            flash_alpha_jitter=self.flash_alpha_jitter,
            flash_fade_speed=self.flash_fade_speed,
            bloom_power=self.bloom_power,
            speed=self.speed,
            flicker_strength=self.flicker_strength,
            flicker_hz=self.flicker_hz,
        )

    def blend(self, other: LightningStyle, t: float) -> LightningStyle:
        """Interpolate between two styles (t in [0..1])."""
        t = _clamp01(t)
        return LightningStyle(
            core_color=_lerp_color(self.core_color, other.core_color, t),
            glow_color=_lerp_color(self.glow_color, other.glow_color, t),
            outer_glow_color=_lerp_color(self.outer_glow_color, other.outer_glow_color, t),
            core_thickness=round(_lerp(self.core_thickness, other.core_thickness, t)),
            glow_thickness=round(_lerp(self.glow_thickness, other.glow_thickness, t)),
            outer_glow_thickness=round(_lerp(self.outer_glow_thickness, other.outer_glow_thickness, t)),
            roughness=_lerp(self.roughness, other.roughness, t),
            depth=round(_lerp(self.depth, other.depth, t)),
            noise_scale=_lerp(self.noise_scale, other.noise_scale, t),
            taper=_clamp01(_lerp(self.taper, other.taper, t)),
            branch_chance=_clamp01(_lerp(self.branch_chance, other.branch_chance, t)),
            branch_depth=round(_lerp(self.branch_depth, other.branch_depth, t)),
            branch_angle_spread_deg=_lerp(self.branch_angle_spread_deg, other.branch_angle_spread_deg, t),
            branch_probability_decay=_clamp01(_lerp(self.branch_probability_decay, other.branch_probability_decay, t)),
            branch_length_decay=_clamp01(_lerp(self.branch_length_decay, other.branch_length_decay, t)),
            branch_thickness_scale=_clamp01(_lerp(self.branch_thickness_scale, other.branch_thickness_scale, t)),
            flash_alpha_base=max(0.0, _lerp(self.flash_alpha_base, other.flash_alpha_base, t)),
            flash_alpha_jitter=max(0.0, _lerp(self.flash_alpha_jitter, other.flash_alpha_jitter, t)),
            flash_fade_speed=max(0.0, _lerp(self.flash_fade_speed, other.flash_fade_speed, t)),
            bloom_power=max(0.0, _lerp(self.bloom_power, other.bloom_power, t)),
            speed=max(0.0, _lerp(self.speed, other.speed, t)),
            flicker_strength=_clamp01(_lerp(self.flicker_strength, other.flicker_strength, t)),
            flicker_hz=max(0.0, _lerp(self.flicker_hz, other.flicker_hz, t)),
        )

    # ---- Helper values a renderer might want ----
    def branch_probability_at_level(self, level: int) -> float:
        """Probability to spawn a branch at a given recursion level (0 = root)."""
        return _clamp01(self.branch_chance * (self.branch_probability_decay ** max(0, level)))

    def thickness_profile(self, t_norm: float) -> float:
        """
        Thickness multiplier along the bolt (t_norm in [0..1], 0 = start, 1 = end).
        Simple (1 - t)^taper profile; renderer can multiply this into layer thickness.
        """
        t = _clamp01(t_norm)
        return (1.0 - t) ** (0.1 + 3.0 * self.taper)


# ---------- Presets ----------
def _base_default() -> LightningStyle:
    return LightningStyle()

def _stormy_blue() -> LightningStyle:
    return LightningStyle(
        core_color=(255, 255, 255, 250),
        glow_color=(120, 170, 255, 190),
        outer_glow_color=(80, 140, 255, 120),
        core_thickness=2,
        glow_thickness=7,
        outer_glow_thickness=12,
        roughness=1.0,
        depth=6,
        branch_chance=0.55,
        branch_depth=3,
        branch_angle_spread_deg=40.0,
        flash_alpha_base=0.16,
        flash_alpha_jitter=0.08,
        flash_fade_speed=2.6,
        bloom_power=1.2,
        speed=1.0,
        flicker_strength=0.25,
        flicker_hz=13.0,
    )

def _arcane_purple() -> LightningStyle:
    return LightningStyle(
        core_color=(255, 240, 255, 240),
        glow_color=(200, 120, 255, 170),
        outer_glow_color=(150, 80, 255, 110),
        core_thickness=2,
        glow_thickness=6,
        outer_glow_thickness=10,
        roughness=0.85,
        depth=5,
        branch_chance=0.35,
        branch_depth=2,
        branch_angle_spread_deg=30.0,
        flash_alpha_base=0.12,
        flash_alpha_jitter=0.06,
        flash_fade_speed=2.0,
        bloom_power=1.1,
        speed=0.95,
        flicker_strength=0.18,
        flicker_hz=11.0,
    )

def _sunfire_gold() -> LightningStyle:
    return LightningStyle(
        core_color=(255, 255, 230, 255),
        glow_color=(255, 210, 120, 190),
        outer_glow_color=(255, 160, 70, 120),
        core_thickness=2,
        glow_thickness=7,
        outer_glow_thickness=12,
        roughness=0.8,
        depth=5,
        branch_chance=0.4,
        branch_depth=2,
        branch_angle_spread_deg=28.0,
        flash_alpha_base=0.18,
        flash_alpha_jitter=0.05,
        flash_fade_speed=2.2,
        bloom_power=1.4,
        speed=1.05,
        flicker_strength=0.22,
        flicker_hz=12.0,
    )

def _toxic_green() -> LightningStyle:
    return LightningStyle(
        core_color=(230, 255, 230, 245),
        glow_color=(160, 255, 120, 180),
        outer_glow_color=(90, 220, 70, 120),
        core_thickness=2,
        glow_thickness=6,
        outer_glow_thickness=10,
        roughness=1.1,
        depth=6,
        branch_chance=0.5,
        branch_depth=3,
        branch_angle_spread_deg=35.0,
        flash_alpha_base=0.14,
        flash_alpha_jitter=0.07,
        flash_fade_speed=2.4,
        bloom_power=1.3,
        speed=1.1,
        flicker_strength=0.28,
        flicker_hz=14.0,
    )

def _crimson() -> LightningStyle:
    return LightningStyle(
        core_color=(255, 230, 230, 240),
        glow_color=(255, 110, 110, 175),
        outer_glow_color=(255, 70, 70, 110),
        roughness=0.95,
        depth=6,
        branch_chance=0.5,
        branch_depth=3,
        branch_angle_spread_deg=36.0,
        flash_alpha_base=0.15,
        flash_alpha_jitter=0.08,
        flash_fade_speed=2.5,
        bloom_power=1.25,
        speed=1.0,
        flicker_strength=0.24,
        flicker_hz=12.5,
    )

def _ghost_white() -> LightningStyle:
    return LightningStyle(
        core_color=(255, 255, 255, 255),
        glow_color=(220, 230, 255, 180),
        outer_glow_color=(180, 200, 255, 120),
        roughness=0.6,
        depth=4,
        branch_chance=0.25,
        branch_depth=1,
        branch_angle_spread_deg=20.0,
        flash_alpha_base=0.10,
        flash_alpha_jitter=0.05,
        flash_fade_speed=1.8,
        bloom_power=1.0,
        speed=0.9,
        flicker_strength=0.12,
        flicker_hz=9.0,
    )

def _neon_cyan() -> LightningStyle:
    return LightningStyle(
        core_color=(220, 255, 255, 250),
        glow_color=(120, 255, 255, 185),
        outer_glow_color=(70, 230, 230, 120),
        roughness=1.05,
        depth=6,
        branch_chance=0.48,
        branch_depth=3,
        branch_angle_spread_deg=34.0,
        flash_alpha_base=0.16,
        flash_alpha_jitter=0.08,
        flash_fade_speed=2.4,
        bloom_power=1.35,
        speed=1.1,
        flicker_strength=0.26,
        flicker_hz=13.5,
    )

PRESETS: Dict[str, LightningStyle] = {
    "default": _base_default(),
    "stormy_blue": _stormy_blue(),
    "arcane_purple": _arcane_purple(),
    "sunfire_gold": _sunfire_gold(),
    "toxic_green": _toxic_green(),
    "crimson": _crimson(),
    "ghost_white": _ghost_white(),
    "neon_cyan": _neon_cyan(),
}


# ---------- Public preset API (kept for compatibility) ----------
def default_style() -> LightningStyle:
    return PRESETS["default"]


def stormy_blue_style() -> LightningStyle:
    return PRESETS["stormy_blue"]


def arcane_purple_style() -> LightningStyle:
    return PRESETS["arcane_purple"]


# ---------- Extra utilities ----------
def list_styles() -> Iterable[str]:
    """Names of all built-in presets."""
    return PRESETS.keys()


def get_style(name: str, *, fallback: Optional[str] = "default") -> LightningStyle:
    """Resolve a style by name with optional fallback."""
    if name in PRESETS:
        return PRESETS[name]
    if fallback is not None and fallback in PRESETS:
        return PRESETS[fallback]
    raise KeyError(f"Unknown style '{name}' and fallback '{fallback}' not available.")


def random_style(seed: Optional[int] = None, pool: Optional[Iterable[str]] = None) -> LightningStyle:
    """Pick a random preset (deterministic if seed provided)."""
    r = random.Random(seed)
    names = list(pool or PRESETS.keys())
    return PRESETS[r.choice(names)]


# ---------- Runtime flash helper ----------
@dataclass(slots=True)
class FlashState:
    """
    Tracks screen-flash alpha over time. Use with a LightningStyle to apply a brief
    full-screen additive flash when a bolt strikes.
    """
    alpha: float = 0.0

    def trigger(self, style: LightningStyle, rng: Optional[random.Random] = None) -> None:
        r = rng or random
        jitter = (r.random() * 2 - 1) * style.flash_alpha_jitter
        self.alpha = max(0.0, style.flash_alpha_base + jitter)

    def update(self, style: LightningStyle, dt: float) -> None:
        self.alpha = max(0.0, self.alpha - style.flash_fade_speed * max(0.0, dt))
