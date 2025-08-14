# ui_theme.py
from __future__ import annotations
from typing import Tuple

Color = Tuple[int, int, int]

# Base palette
WHITE: Color = (255, 255, 255)
BLACK: Color = (0, 0, 0)
UI_BG: Color = (25, 25, 28)
UI_FG: Color = (210, 210, 215)
ACCENT: Color = (230, 200, 60)

# Health palette (we lerp from RED -> YELLOW -> GREEN)
HEALTH_RED: Color = (220, 40, 40)
HEALTH_YELLOW: Color = (220, 180, 60)
HEALTH_GREEN: Color = (60, 220, 90)

# Difficulty colors
DIFF_COLORS = {
    "easy":   (120, 200, 120),
    "normal": (210, 210, 215),
    "hard":   (230, 150, 80),
    "nightmare": (230, 90, 90),
}
