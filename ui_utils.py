# ui_utils.py
from __future__ import annotations
from typing import Tuple
import math
import pygame

Color = Tuple[int, int, int]

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def lerp_color(c0: Color, c1: Color, t: float) -> Color:
    t = clamp(t, 0.0, 1.0)
    return (
        int(lerp(c0[0], c1[0], t)),
        int(lerp(c0[1], c1[1], t)),
        int(lerp(c0[2], c1[2], t)),
    )

def tri_lerp_color(c0: Color, c1: Color, c2: Color, t: float) -> Color:
    """
    2‑stop gradient: 0..0.5 between c0->c1, 0.5..1 between c1->c2
    """
    t = clamp(t, 0.0, 1.0)
    if t <= 0.5:
        k = t / 0.5
        return lerp_color(c0, c1, k)
    k = (t - 0.5) / 0.5
    return lerp_color(c1, c2, k)

def draw_text(
    s: pygame.Surface, text: str, font: pygame.font.Font, color: Color,
    pos: Tuple[int, int], shadow: bool = True,
    shadow_offset: Tuple[int, int] = (1, 1), shadow_alpha: int = 140
) -> None:
    if shadow:
        shadow_surf = font.render(text, True, (0, 0, 0))
        shadow_surf.set_alpha(shadow_alpha)
        s.blit(shadow_surf, (pos[0] + shadow_offset[0], pos[1] + shadow_offset[1]))
    s.blit(font.render(text, True, color), pos)

def draw_round_rect(
    s: pygame.Surface, color: Color, rect: pygame.Rect,
    radius: int = 6, width: int = 0
) -> None:
    pygame.draw.rect(s, color, rect, width=width, border_radius=radius)

def format_score(n: int) -> str:
    # 12,345 or 1.2k / 1.2M compact representation for large values
    if abs(n) >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"{n/1_000:.1f}k"
    return f"{n:,}"

def pulse(time_s: float, speed: float = 2.2, lo: float = 0.6, hi: float = 1.0) -> float:
    return lerp(lo, hi, 0.5 + 0.5 * math.sin(time_s * speed * 2 * math.pi))
