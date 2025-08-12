# reticle_theme.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple

Color = Tuple[int, int, int]
ColorA = Tuple[int, int, int, int]  # RGBA

@dataclass
class ReticleTheme:
    base: Color = (255, 255, 255)
    outline: Color = (0, 0, 0)
    danger: Color = (255, 64, 64)
    cooldown: Color = (230, 200, 60)
    shadow: ColorA = (0, 0, 0, 90)

def default_theme() -> ReticleTheme:
    return ReticleTheme()

def high_contrast_theme() -> ReticleTheme:
    return ReticleTheme(
        base=(255, 255, 0),
        outline=(0, 0, 0),
        danger=(255, 0, 0),
        cooldown=(0, 255, 255),
        shadow=(0, 0, 0, 130),
    )

def colorblind_theme() -> ReticleTheme:
    # Deut/Friendly hues with strong luma separation
    return ReticleTheme(
        base=(255, 255, 255),
        outline=(0, 0, 0),
        danger=(255, 120, 0),
        cooldown=(120, 200, 255),
        shadow=(0, 0, 0, 110),
    )
