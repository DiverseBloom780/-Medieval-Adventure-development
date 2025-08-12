# timecycle.py
# Lightweight day–night cycle for Pygame scenes.
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple
import pygame
import math
import random


Color = Tuple[int, int, int]


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_color(c0: Color, c1: Color, t: float) -> Color:
    return (
        int(_lerp(c0[0], c1[0], t)),
        int(_lerp(c0[1], c1[1], t)),
        int(_lerp(c0[2], c1[2], t)),
    )


@dataclass
class TimeOfDayCycle:
    """A looping day–night cycle with sky color, sun/moon, and stars."""
    width: int
    height: int
    duration: float = 90.0  # seconds for a full cycle
    t: float = 0.0          # 0..1 progress through the cycle
    star_count: int = 140

    # internal
    _stars: List[Tuple[int, int, float, float, int]] = field(default_factory=list)

    # Keyframe colors (fraction of the cycle -> sky color)
    # You can tweak these for your aesthetic.
    _keys: List[Tuple[float, Color]] = field(default_factory=lambda: [
        (0.00, (12, 16, 38)),     # deep night
        (0.15, (80, 70, 110)),    # pre-dawn
        (0.25, (160, 170, 200)),  # dawn
        (0.50, (173, 216, 230)),  # day (sky blue)
        (0.70, (200, 160, 120)),  # golden hour
        (0.85, (70, 50, 90)),     # dusk
        (1.00, (12, 16, 38)),     # back to night
    ])

    def __post_init__(self) -> None:
        rng = random.Random(1337)
        for _ in range(self.star_count):
            x = rng.randrange(0, self.width)
            y = rng.randrange(0, int(self.height * 0.66))  # upper two-thirds of the screen
            base_alpha = rng.uniform(0.35, 0.95)
            phase = rng.uniform(0, math.tau)
            size = rng.choice((1, 1, 1, 2))  # mostly small stars
            self._stars.append((x, y, base_alpha, phase, size))

    # ---------------- Public API ----------------

    def update(self, dt: float) -> None:
        """Advance the cycle."""
        self.t = (self.t + (dt / self.duration)) % 1.0

    def sky_color(self) -> Color:
        """Interpolated sky color for the current time."""
        t = self.t
        keys = self._keys
        for i in range(len(keys) - 1):
            t0, c0 = keys[i]
            t1, c1 = keys[i + 1]
            if t0 <= t <= t1:
                k = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
                return _lerp_color(c0, c1, k)
        # fallback (shouldn't happen thanks to 1.00 key)
        return keys[-1][1]

    def night_factor(self) -> float:
        """0 (day) .. 1 (deep night), used for world tint and stars."""
        # Make night strongest around t in [0, 0.1] U [0.9, 1.0]
        t = self.t
        # distance from closest 'day center' (0.5)
        dist = min(abs(t - 0.5), abs((t + 1.0) - 0.5), abs((t - 1.0) - 0.5))
        # scale: near 0 at day center, ~1 at midnight
        nf = _clamp((0.5 - dist) * 2.0, 0.0, 1.0)
        return nf

    def draw_sky(self, surface: pygame.Surface, ground_y: int) -> None:
        """Draw the sky, stars, and sun/moon. Call before drawing world."""
        surface.fill(self.sky_color())
        self._draw_sun_moon(surface, ground_y)
        self._draw_stars(surface)

        # Simple warm horizon tint near ground (thin gradient)
        horizon_h = max(24, int(self.height * 0.08))
        overlay = pygame.Surface((self.width, horizon_h), pygame.SRCALPHA)
        # warmer tint at dusk/dawn; tie to night_factor subtly
        nf = self.night_factor()
        tint = (int(220 * (1 - nf) + 40 * nf), int(160 * (1 - nf) + 50 * nf), int(80 * (1 - nf) + 30 * nf), 80)
        for i in range(horizon_h):
            alpha = int(overlay.get_height() - i)  # fade upward
            col = (*tint[:3], int(tint[3] * (alpha / horizon_h)))
            pygame.draw.line(overlay, col, (0, i), (self.width, i))
        surface.blit(overlay, (0, ground_y - horizon_h))

    def draw_world_tint(self, surface: pygame.Surface) -> None:
        """Darken the entire scene at night. Call after drawing the world."""
        nf = self.night_factor()
        if nf <= 0.01:
            return
        alpha = int(140 * nf)
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((0, 0, 0, alpha))
        surface.blit(veil, (0, 0))

    # ---------------- Internals ----------------

    def _draw_stars(self, s: pygame.Surface) -> None:
        nf = self.night_factor()
        if nf <= 0.05:
            return
        now = pygame.time.get_ticks() / 1000.0
        for x, y, base, phase, size in self._stars:
            twinkle = 0.5 + 0.5 * math.sin(now * 2.0 + phase)
            a = int(255 * base * nf * twinkle)
            star = pygame.Surface((size, size), pygame.SRCALPHA)
            star.fill((255, 255, 255, a))
            s.blit(star, (x, y))

    def _draw_sun_moon(self, s: pygame.Surface, ground_y: int) -> None:
        # Center orbit below horizon; half the cycle sun above, half moon above
        cx, cy = self.width // 2, ground_y + 80
        r = int(min(self.width, self.height) * 0.42)

        # Sun path (t around 0.25..0.75 above horizon)
        ang_sun = math.tau * (self.t - 0.25)
        sx = cx + int(math.cos(ang_sun) * r)
        sy = cy - int(math.sin(ang_sun) * r)

        # Moon opposite the sun
        ang_moon = ang_sun + math.pi
        mx = cx + int(math.cos(ang_moon) * r)
        my = cy - int(math.sin(ang_moon) * r)

        # Draw whichever is above horizon (sy < ground_y)
        if sy < ground_y:
            pygame.draw.circle(s, (255, 240, 170), (sx, sy), 16)
            pygame.draw.circle(s, (255, 255, 255, 80), (sx, sy), 24, width=2)
        if my < ground_y:
            moon = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.circle(moon, (230, 230, 255), (16, 16), 12)
            # simple crescent
            pygame.draw.circle(moon, (0, 0, 0, 0), (12, 14), 12)
            s.blit(moon, (mx - 16, my - 16))
