# lightning_theme.py
from __future__ import annotations
from dataclasses import dataclass

# RGBA colors for glow/core layers
ColorA = tuple[int, int, int, int]

@dataclass
class LightningStyle:
    # Visuals
    core_color: ColorA        = (255, 255, 255, 240)
    glow_color: ColorA        = (140, 180, 255, 170)
    outer_glow_color: ColorA  = (90, 150, 255, 110)
    core_thickness: int       = 2
    glow_thickness: int       = 6
    outer_glow_thickness: int = 10

    # Shape
    roughness: float = 0.9
    depth: int       = 5

    # Branching
    branch_chance: float = 0.45
    branch_depth: int    = 3

    # Flash
    flash_alpha_base: float  = 0.13
    flash_alpha_jitter: float = 0.07
    flash_fade_speed: float  = 2.0  # alpha per second

def default_style() -> LightningStyle:
    return LightningStyle()

def stormy_blue_style() -> LightningStyle:
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
        flash_alpha_base=0.16,
        flash_alpha_jitter=0.08,
        flash_fade_speed=2.6,
    )

def arcane_purple_style() -> LightningStyle:
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
        flash_alpha_base=0.12,
        flash_alpha_jitter=0.06,
        flash_fade_speed=2.0,
    )
