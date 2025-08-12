
# clouds.py
# Soft, layered cloud sprites drifting across the sky (no external assets).
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Dict
import pygame
import random

@dataclass
class Cloud:
    surf: pygame.Surface
    x: float
    y: float
    speed: float
    scale: float

class CloudLayer:
    def __init__(self, width: int, height: int, *, seed: int = 0,
                 speed: float = 18.0, alpha: int = 150, scale: float = 1.0,
                 count: int = 18) -> None:
        self.width = width
        self.height = height
        self.base_speed = speed
        self.alpha = alpha
        self.scale_factor = scale
        self.count = count
        self._rng = random.Random(seed)
        self._clouds: List[Cloud] = []
        self._spawn_initial()

    def respawn(self, *, seed: int) -> None:
        self._rng.seed(seed)
        self._clouds.clear()
        self._spawn_initial()

    def to_dict(self) -> Dict:
        return {
            "alpha": self.alpha,
            "scale": self.scale_factor,
            "count": self.count,
            "speed": self.base_speed,
        }

    def from_dict(self, cfg: Dict) -> None:
        self.alpha = int(cfg.get("alpha", self.alpha))
        self.scale_factor = float(cfg.get("scale", self.scale_factor))
        self.count = int(cfg.get("count", self.count))
        self.base_speed = float(cfg.get("speed", self.base_speed))

    def set_density(self, density: float) -> None:
        # Adjust count based on density, clamp to reasonable range
        want = max(0, min(40, int(self.count * (0.3 + density))))
        if want > len(self._clouds):
            for _ in range(want - len(self._clouds)):
                self._clouds.append(self._make_cloud(off_right=True))
        elif want < len(self._clouds):
            self._clouds = self._clouds[:want]

    def _spawn_initial(self) -> None:
        for _ in range(self.count):
            self._clouds.append(self._make_cloud(off_right=False))

    def _make_cloud(self, *, off_right: bool) -> Cloud:
        # Build a soft cloud sprite by overlapping semi-transparent circles
        w = self._rng.randint(120, 220)
        h = self._rng.randint(50, 100)
        scale = self.scale_factor * self._rng.uniform(0.8, 1.3)
        w = int(w * scale)
        h = int(h * scale)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        tint = self._rng.randint(235, 255)
        for _ in range(self._rng.randint(6, 10)):
            rx = self._rng.randint(int(w * 0.1), int(w * 0.9))
            ry = self._rng.randint(int(h * 0.2), int(h * 0.85))
            rr = self._rng.randint(int(h * 0.25), int(h * 0.55))
            col = (tint, tint, tint, self._rng.randint(60, 120))
            pygame.draw.circle(surf, col, (rx, ry), rr)
        speed = self.base_speed * self._rng.uniform(0.6, 1.4)
        y = self._rng.randint(8, max(9, int(self.height * 0.55)))
        x = (self.width + self._rng.randint(0, self.width)) if off_right else self._rng.randint(-self.width, self.width)
        return Cloud(surf=surf, x=float(x), y=float(y), speed=speed, scale=scale)

    def update(self, dt: float, *, wind: float = 0.0) -> None:
        for c in self._clouds:
            c.x += (c.speed + wind) * dt
        # wrap-around & recycle
        for i, c in enumerate(self._clouds):
            if c.x > self.width + 40:
                self._clouds[i] = self._make_cloud(off_right=False)
                self._clouds[i].x = -self._clouds[i].surf.get_width() - 20

    def draw(self, s: pygame.Surface, *, y: int = 0, height: int = 0) -> None:
        # Optional clipping rectangle
        clip = None
        if height > 0:
            clip = pygame.Rect(0, y, self.width, height)
            prev = s.get_clip()
            s.set_clip(clip)

        for c in self._clouds:
            # respect global alpha of layer
            if self.alpha < 255:
                blit = c.surf.copy()
                blit.fill((255, 255, 255, self.alpha), special_flags=pygame.BLEND_RGBA_MULT)
                s.blit(blit, (int(c.x), int(c.y)))
            else:
                s.blit(c.surf, (int(c.x), int(c.y)))

        if height > 0 and clip is not None:
            s.set_clip(prev)
