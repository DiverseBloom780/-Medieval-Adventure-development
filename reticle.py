# reticle.py
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Tuple, Optional

import pygame

try:
    # Optional AA helpers (fallbacks provided)
    import pygame.gfxdraw as _gfx
except Exception:  # pragma: no cover
    _gfx = None  # noqa: N816

from reticle_theme import ReticleTheme, default_theme

Vec2i = Tuple[int, int]
Color = Tuple[int, int, int]  # RGB only; alpha handled via SRCALPHA surfaces


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _mix_color(a: Color, b: Color, t: float) -> Color:
    t = _clamp(t, 0.0, 1.0)
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


@dataclass
class ReticleStyle:
    """Visual knobs for the reticle."""
    radius: int = 10
    thickness: int = 2
    cross_len: int = 8       # length of each crosshair tick
    gap: int = 4             # gap between center and cross tick start
    shadow_px: int = 2       # drop shadow offset; 0 = off
    center_dot: bool = False # draw a tiny center dot or not


class Reticle:
    """
    Animated, themable reticle with:
      - smooth mouse follow (smoothing)
      - subtle breathing pulse
      - bloom (expands briefly) on fire
      - cooldown arc (0..1)
      - danger tinting
      - optional shadow
    """
    def __init__(self,
                 style: Optional[ReticleStyle] = None,
                 theme: Optional[ReticleTheme] = None,
                 smoothing: float = 0.18) -> None:
        self.style = style or ReticleStyle()
        self.theme = theme or default_theme()
        self.smoothing = _clamp(smoothing, 0.0, 1.0)

        self._pos = pygame.Vector2(0, 0)
        self._t = 0.0                 # time accumulator (seconds)
        self._bloom = 0.0             # 0..1 bloom size add
        self._flash = 0.0             # 0..1 flash amount for color pop
        self.cooldown_ratio = 0.0     # 0 ready .. 1 cooling
        self.danger = False           # if True, tint toward danger color
        self._initialized = False

        # Internal timing support for function-style usage
        self._last_ticks = pygame.time.get_ticks()

    # --- State API ----------------------------------------------------------

    def set_style(self, radius: int | None = None, thickness: int | None = None) -> None:
        if radius is not None:
            self.style.radius = max(2, int(radius))
        if thickness is not None:
            self.style.thickness = max(1, int(thickness))

    def set_theme(self, theme: ReticleTheme) -> None:
        self.theme = theme

    def set_cooldown(self, ratio: float) -> None:
        self.cooldown_ratio = _clamp(float(ratio), 0.0, 1.0)

    def set_danger(self, danger: bool) -> None:
        self.danger = bool(danger)

    def kick_bloom(self, strength: float = 1.0) -> None:
        """Call on fire to expand reticle briefly."""
        self._bloom = min(1.0, self._bloom + max(0.0, strength))

    def flash(self, strength: float = 1.0) -> None:
        """Quick color pop (e.g., on hit)."""
        self._flash = min(1.0, self._flash + max(0.0, strength))

    # --- Update / Draw ------------------------------------------------------

    def update(self, target_pos: Vec2i, dt: Optional[float] = None) -> None:
        """
        Smoothly follow the target position. If dt is None, computes it
        from pygame ticks (useful when called from a stateless place).
        """
        ticks = pygame.time.get_ticks()
        if dt is None:
            if not self._initialized:
                self._initialized = True
                self._last_ticks = ticks
            dt = (ticks - self._last_ticks) / 1000.0
            self._last_ticks = ticks

        dt = max(0.0, min(dt, 1.0 / 30.0))  # avoid huge spikes

        # Init position instantly the first time
        if self._pos.length_squared() == 0:
            self._pos.update(*target_pos)

        # Smooth toward new target
        tp = pygame.Vector2(target_pos)
        self._pos += (tp - self._pos) * (1.0 - pow(1.0 - self.smoothing, max(dt * 60.0, 1.0)))

        # Animations
        self._t += dt
        self._bloom = max(0.0, self._bloom - dt * 3.2)
        self._flash = max(0.0, self._flash - dt * 6.0)

    def draw(self, screen: pygame.Surface) -> None:
        x, y = int(self._pos.x), int(self._pos.y)
        style = self.style
        base_col = self.theme.base
        outline = self.theme.outline

        # Pulse + bloom scale
        pulse = 1.0 + 0.06 * math.sin(self._t * math.tau * 0.65)
        bloom = 1.0 + 0.25 * self._bloom
        scale = pulse * bloom

        radius = int(style.radius * scale)
        thick = max(1, int(style.thickness * scale))
        gap = int(style.gap * scale)
        cross_len = int(style.cross_len * scale)

        # Color choice (danger + flash)
        col = base_col
        if self.danger:
            col = _mix_color(col, self.theme.danger, 0.65)
        if self._flash > 0.0:
            col = _mix_color(col, (255, 255, 255), min(1.0, self._flash))

        # Shadow
        if style.shadow_px > 0:
            self._draw_ring_shadow(screen, (x, y), radius, thick, style.shadow_px)

        # Main ring + outline
        self._draw_ring(screen, (x, y), radius, thick, col)
        if thick >= 2:
            # thin outline just outside the main ring
            self._draw_ring(screen, (x, y), radius + 1, 1, outline)

        # Crosshair ticks
        self._draw_cross(screen, (x, y), gap, cross_len, thick, col, outline)

        # Center dot (optional)
        if style.center_dot:
            pygame.draw.circle(screen, col, (x, y), max(1, thick // 2))

        # Cooldown arc (remaining cooldown portion)
        if self.cooldown_ratio > 0.0:
            self._draw_cooldown_arc(screen, (x, y), radius + 4, max(2, thick - 1), self.cooldown_ratio)

    # --- Primitives ---------------------------------------------------------

    def _draw_ring(self, s: pygame.Surface, pos: Vec2i, radius: int, width: int, color: Color) -> None:
        if radius <= 0 or width <= 0:
            return
        # AA outer edge if gfxdraw is available; then fill ring with draw.circle
        if _gfx:
            _gfx.aacircle(s, pos[0], pos[1], radius, color)
        pygame.draw.circle(s, color, pos, radius, width)

    def _draw_ring_shadow(self, s: pygame.Surface, pos: Vec2i, radius: int, width: int, offset: int) -> None:
        # draw shadow on its own alpha surface for soft edges
        size = (radius + width + offset + 3) * 2
        tmp = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cy = size // 2
        shadow_col = self.theme.shadow  # RGBA
        pygame.draw.circle(tmp, shadow_col, (cx + offset, cy + offset), radius, width)
        s.blit(tmp, (pos[0] - cx, pos[1] - cy))

    def _draw_cross(self, s: pygame.Surface, pos: Vec2i, gap: int, length: int, width: int,
                    color: Color, outline: Color) -> None:
        x, y = pos
        # Horizontal
        pygame.draw.line(s, color, (x - gap - length, y), (x - gap, y), width)
        pygame.draw.line(s, color, (x + gap, y), (x + gap + length, y), width)
        # Vertical
        pygame.draw.line(s, color, (x, y - gap - length), (x, y - gap), width)
        pygame.draw.line(s, color, (x, y + gap), (x, y + gap + length), width)

        # Outline nudge for clarity at small sizes
        if width >= 2:
            pygame.draw.line(s, outline, (x - gap - length, y), (x - gap, y), 1)
            pygame.draw.line(s, outline, (x + gap, y), (x + gap + length, y), 1)
            pygame.draw.line(s, outline, (x, y - gap - length), (x, y - gap), 1)
            pygame.draw.line(s, outline, (x, y + gap), (x, y + gap + length), 1)

    def _draw_cooldown_arc(self, s: pygame.Surface, pos: Vec2i, radius: int, width: int, ratio: float) -> None:
        # Draw an arc from -90 degrees spanning ratio * 360 degrees
        start = -math.pi / 2
        end = start + ratio * math.tau
        rect = pygame.Rect(pos[0] - radius, pos[1] - radius, radius * 2, radius * 2)
        pygame.draw.arc(s, self.theme.cooldown, rect, start, end, width)


# ---------------------------------------------------------------------------
# Backwards‑compatible function API
# ---------------------------------------------------------------------------

# Module‑level singleton for simple usage
_RETICLE: Optional[Reticle] = None

def _get_reticle() -> Reticle:
    global _RETICLE
    if _RETICLE is None:
        _RETICLE = Reticle()
    return _RETICLE

def draw_reticle(screen: pygame.Surface,
                 pos: Tuple[int, int],
                 radius: int = 10,
                 thickness: int = 2,
                 *,
                 cooldown_ratio: float = 0.0,
                 danger: bool = False,
                 dt: Optional[float] = None) -> None:
    """
    Backwards‑compatible drawing function with extra optional features:
      - cooldown_ratio: 0 ready .. 1 cooling (draws an arc)
      - danger: tint toward danger color
      - dt: pass your frame dt to advance animations; if omitted, we compute it
    """
    r = _get_reticle()
    # Update style if caller overrides radius/thickness (keeps old signature feeling)
    if radius != r.style.radius or thickness != r.style.thickness:
        r.set_style(radius=radius, thickness=thickness)
    r.set_cooldown(cooldown_ratio)
    r.set_danger(danger)
    r.update(pos, dt=dt)
    r.draw(screen)

def reticle_fire_bloom(strength: float = 1.0) -> None:
    """Call this when firing to expand the reticle briefly."""
    _get_reticle().kick_bloom(strength)

def reticle_flash(color_pop: float = 1.0) -> None:
    """Call this on a hit for a quick color pop."""
    _get_reticle().flash(color_pop)

def reticle_set_theme(theme: ReticleTheme) -> None:
    _get_reticle().set_theme(theme)
