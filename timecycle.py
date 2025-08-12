# timecycle.py
# Lightweight but featureful day–night cycle for Pygame scenes.
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple, Optional
import pygame
import math
import random

# Optional: easing helpers (fallbacks provided if module missing)
try:
    from easings import smoothstep, smootherstep
except Exception:
    def smoothstep(t: float) -> float:
        t = max(0.0, min(1.0, t))
        return t * t * (3 - 2 * t)

    def smootherstep(t: float) -> float:
        t = max(0.0, min(1.0, t))
        return t * t * t * (t * (t * 6 - 15) + 10)

Color = Tuple[int, int, int]
RGBA = Tuple[int, int, int, int]


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
class TemporalEvent:
    """Simple time-of-day event that triggers when cycle passes a key t."""
    t: float
    callback: Callable[[float], None]  # receives current t (0..1)
    name: str = ""


@dataclass
class TimeOfDayCycle:
    """
    Looping day–night cycle with:
      - Gradient sky, sun & moon with glow
      - Star field with twinkle
      - Night tint overlay
      - Time scaling, pause, manual set/get in hours
      - Event hooks (e.g., sunrise/sunset)
      - Save/restore (serialize)
    """
    width: int
    height: int
    duration: float = 90.0   # seconds for a full 24h cycle
    t: float = 0.0           # 0..1 normalized time-of-day
    timescale: float = 1.0   # global speed multiplier (0 pauses)
    paused: bool = False
    star_count: int = 140
    seed: int = 1337
    gradient_steps: int = 80
    sun_radius: int = 16
    moon_radius: int = 12

    # Keyframe colors (fraction of cycle -> sky color)
    # Ensure first key at 0.0 and last at 1.0 for seamless wrap.
    keys: List[Tuple[float, Color]] = field(default_factory=lambda: [
        (0.00, (12, 16, 38)),     # deep night
        (0.14, (70, 62, 98)),     # nautical dawn
        (0.22, (160, 170, 200)),  # dawn
        (0.50, (173, 216, 230)),  # day
        (0.70, (204, 164, 110)),  # golden hour
        (0.86, (60, 46, 80)),     # dusk
        (1.00, (12, 16, 38)),     # deep night
    ])

    # Internals
    _stars: List[Tuple[int, int, float, float, int]] = field(default_factory=list)
    _events: List[TemporalEvent] = field(default_factory=list)
    _prev_t: float = 0.0

    def __post_init__(self) -> None:
        rng = random.Random(self.seed)
        sky_h = int(self.height * 0.66)
        for _ in range(self.star_count):
            x = rng.randrange(0, self.width)
            y = rng.randrange(0, max(1, sky_h))
            base_alpha = rng.uniform(0.35, 0.95)
            phase = rng.uniform(0, math.tau)
            size = rng.choice((1, 1, 1, 2))  # mostly small stars
            self._stars.append((x, y, base_alpha, phase, size))

        # Normalize and sort keys (defensive)
        self.keys = sorted([(max(0.0, min(1.0, k)), c) for k, c in self.keys], key=lambda x: x[0])
        if self.keys[0][0] != 0.0:
            self.keys.insert(0, (0.0, self.keys[0][1]))
        if self.keys[-1][0] != 1.0:
            self.keys.append((1.0, self.keys[-1][1]))

    # ---------------- Public API ----------------

    @property
    def hours(self) -> float:
        """Current time in hours [0..24)."""
        return (self.t % 1.0) * 24.0

    def set_hours(self, hours: float) -> None:
        """Set time via hour value (0..24)."""
        self.t = (hours / 24.0) % 1.0

    def set_time(self, t: float) -> None:
        """Set normalized time directly (0..1)."""
        self.t = t % 1.0

    def advance(self, seconds: float) -> None:
        """Advance time by real seconds (ignores paused)."""
        if self.duration > 0:
            self._prev_t = self.t
            self.t = (self.t + (seconds * self.timescale) / self.duration) % 1.0
            self._fire_events()

    def update(self, dt: float) -> None:
        """Advance the cycle by dt seconds."""
        if self.paused or self.timescale == 0.0 or self.duration <= 0.0:
            return
        self._prev_t = self.t
        self.t = (self.t + (dt * self.timescale) / self.duration) % 1.0
        self._fire_events()

    def register_event(self, t: float, callback: Callable[[float], None], name: str = "") -> None:
        """Trigger callback when time crosses t (0..1) moving forward, including wrap."""
        self._events.append(TemporalEvent(t=t % 1.0, callback=callback, name=name))

    def clear_events(self) -> None:
        self._events.clear()

    def to_dict(self) -> Dict:
        return {
            "t": self.t,
            "duration": self.duration,
            "timescale": self.timescale,
            "paused": self.paused,
            "seed": self.seed,
        }

    def from_dict(self, data: Dict) -> None:
        self.t = float(data.get("t", self.t)) % 1.0
        self.duration = float(data.get("duration", self.duration))
        self.timescale = float(data.get("timescale", self.timescale))
        self.paused = bool(data.get("paused", self.paused))
        new_seed = int(data.get("seed", self.seed))
        if new_seed != self.seed:
            self.seed = new_seed
            self.__post_init__()  # rebuild stars deterministically

    # Visual queries ----------------------------------------------------------

    def sky_color(self) -> Color:
        """Interpolated sky color for the current time using smootherstep at segment level."""
        t = self.t
        keys = self.keys
        for i in range(len(keys) - 1):
            t0, c0 = keys[i]
            t1, c1 = keys[i + 1]
            if t0 <= t <= t1:
                k = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
                k = smootherstep(k)
                return _lerp_color(c0, c1, k)
        return keys[-1][1]

    def night_factor(self) -> float:
        """0 (day) .. 1 (deep night), used for world tint and stars."""
        # Use distance from day apex (t=0.5) with a smooth curve
        t = self.t
        # distance to nearest 0.5 modulo 1.0
        dist = min(abs(t - 0.5), abs((t + 1.0) - 0.5), abs((t - 1.0) - 0.5))
        nf = _clamp((0.5 - dist) * 2.0, 0.0, 1.0)
        return nf

    def sunlight_intensity(self) -> float:
        """Rough sunlight factor based on sun elevation (0..1)."""
        # Sun above horizon on t in ~[0.25, 0.75]
        # Map to [-pi/2..pi/2] across that window and take sin for elevation
        phase = (self.t - 0.25) * 2.0  # 0..1 across the daylight half
        phase = max(0.0, min(1.0, phase))
        elev = math.sin((phase * math.pi) - (math.pi / 2))
        return _clamp((elev + 1.0) * 0.5, 0.0, 1.0)

    def ambient_overlay(self, extra_dark: float = 0.0) -> RGBA:
        """RGBA veil based on night factor (and optional extra darkening e.g., weather)."""
        nf = self.night_factor()
        alpha = int(160 * (nf ** 1.3) + 180 * _clamp(extra_dark, 0.0, 1.0))
        return (0, 0, 0, _clamp(alpha, 0, 255))

    # Drawing ----------------------------------------------------------------

    def draw_sky(self, surface: pygame.Surface, ground_y: int) -> None:
        """Draw sky gradient, sun/moon and stars. Call before world rendering."""
        self._draw_gradient_sky(surface, ground_y)
        self._draw_sun_moon(surface, ground_y)
        self._draw_stars(surface)

    def draw_world_tint(self, surface: pygame.Surface, extra_dark: float = 0.0) -> None:
        """Darken entire scene based on night + optional extra darkening (e.g., weather)."""
        ov = self.ambient_overlay(extra_dark)
        if ov[3] <= 0:
            return
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill(ov)
        surface.blit(veil, (0, 0))

    # ---------------- Internals ----------------

    def _fire_events(self) -> None:
        """Trigger registered events that fall between previous t and new t (with wrap)."""
        prev, cur = self._prev_t, self.t
        if prev <= cur:
            window = (prev, cur)
            for ev in self._events:
                if window[0] < ev.t <= window[1]:
                    ev.callback(cur)
        else:
            # wrapped around 1.0 -> 0.0
            for ev in self._events:
                if ev.t > prev or ev.t <= cur:
                    ev.callback(cur)

    def _draw_gradient_sky(self, s: pygame.Surface, ground_y: int) -> None:
        """Vertical gradient: top sky -> horizon tint."""
        h = max(1, ground_y)
        steps = max(8, self.gradient_steps)
        top_col = self.sky_color()

        # Warm horizon color adjusts by time (warmer around dawn/dusk).
        nf = self.night_factor()
        sun_k = self.sunlight_intensity()
        # Dawn/dusk prominence curve
        dusk_dawn = math.exp(-((sun_k - 0.5) ** 2) * 18.0)
        base = (int(220 * (1 - nf) + 40 * nf), int(160 * (1 - nf) + 50 * nf), int(80 * (1 - nf) + 30 * nf))
        horizon = (
            int(_clamp(base[0] + 35 * dusk_dawn, 0, 255)),
            int(_clamp(base[1] + 25 * dusk_dawn, 0, 255)),
            int(_clamp(base[2] + 15 * dusk_dawn, 0, 255)),
        )

        # Fill gradient bands (fast enough for modest steps)
        for i in range(steps):
            y0 = int(i * h / steps)
            y1 = int((i + 1) * h / steps)
            k = i / max(1, steps - 1)
            k = smoothstep(k)
            col = _lerp_color(top_col, horizon, k)
            pygame.draw.rect(s, col, (0, y0, self.width, y1 - y0))

    def _draw_stars(self, s: pygame.Surface) -> None:
        nf = self.night_factor()
        if nf <= 0.05:
            return
        now = pygame.time.get_ticks() / 1000.0
        for x, y, base, phase, size in self._stars:
            twinkle = 0.5 + 0.5 * math.sin(now * 2.2 + phase)
            a = int(255 * base * nf * twinkle)
            if a <= 1:
                continue
            star = pygame.Surface((size, size), pygame.SRCALPHA)
            star.fill((255, 255, 255, a))
            s.blit(star, (x, y))

    def _draw_sun_moon(self, s: pygame.Surface, ground_y: int) -> None:
        # Orbit center slightly below horizon; half-cycle each above horizon.
        cx, cy = self.width // 2, ground_y + 80
        r = int(min(self.width, self.height) * 0.42)

        # Sun: t in [0.25..0.75] above horizon
        ang_sun = math.tau * (self.t - 0.25)
        sx = cx + int(math.cos(ang_sun) * r)
        sy = cy - int(math.sin(ang_sun) * r)

        # Moon opposite
        ang_moon = ang_sun + math.pi
        mx = cx + int(math.cos(ang_moon) * r)
        my = cy - int(math.sin(ang_moon) * r)

        # Draw whichever is above horizon
        if sy < ground_y:
            # glow strength by elevation
            elev = _clamp((ground_y - sy) / (ground_y + r), 0.0, 1.0)
            glow = int(70 + 120 * (1.0 - elev))
            pygame.draw.circle(s, (255, 240, 170), (sx, sy), self.sun_radius)
            pygame.draw.circle(s, (255, 255, 255, glow), (sx, sy), self.sun_radius + 8, width=2)

        if my < ground_y:
            moon = pygame.Surface((self.moon_radius * 2 + 8, self.moon_radius * 2 + 8), pygame.SRCALPHA)
            center = (moon.get_width() // 2, moon.get_height() // 2)
            pygame.draw.circle(moon, (230, 230, 255), center, self.moon_radius)
            # simple crescent effect
            pygame.draw.circle(moon, (0, 0, 0, 0), (center[0] - 4, center[1] + 2), self.moon_radius)
            s.blit(moon, (mx - center[0], my - center[1]))
