# lightning.py
# Procedural lightning bolts with a simple manager and screen flash.
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple
import pygame
import random
import math

Point = Tuple[int, int]

def _mid_displace(p0: Point, p1: Point, roughness: float, depth: int, rng: random.Random) -> List[Point]:
    """Recursive midpoint displacement to create a jagged polyline."""
    if depth <= 0:
        return [p0, p1]
    x0, y0 = p0; x1, y1 = p1
    mx = (x0 + x1) / 2.0
    my = (y0 + y1) / 2.0
    # perpendicular offset
    dx, dy = (x1 - x0), (y1 - y0)
    length = max(1.0, math.hypot(dx, dy))
    nx, ny = -dy / length, dx / length
    offset = (rng.uniform(-1.0, 1.0) * roughness * length * 0.12)
    mid = (int(mx + nx * offset), int(my + ny * offset))
    left = _mid_displace(p0, mid, roughness * 0.65, depth - 1, rng)
    right = _mid_displace(mid, p1, roughness * 0.65, depth - 1, rng)
    return left[:-1] + right

@dataclass
class LightningBolt:
    points: List[Point]
    ttl: float = 0.12
    thickness: int = 3

    def update(self, dt: float) -> None:
        self.ttl = max(0.0, self.ttl - dt)

    @property
    def alive(self) -> bool:
        return self.ttl > 0.0

    def draw(self, s: pygame.Surface) -> None:
        if len(self.points) < 2:
            return
        alpha = int(200 * min(1.0, self.ttl / 0.12) + 40)
        glow = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        pygame.draw.lines(glow, (255, 255, 255, alpha), False, self.points, self.thickness)
        s.blit(glow, (0, 0), special_flags=pygame.BLEND_PREMULTIPLIED)

@dataclass
class LightningManager:
    width: int
    height: int
    seed: int = 0
    bolts: List[LightningBolt] = field(default_factory=list)
    flash_alpha: float = 0.0
    _rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self) -> None:
        self._rng.seed(self.seed)

    def respawn(self, *, seed: int) -> None:
        self._rng.seed(seed)
        self.bolts.clear()
        self.flash_alpha = 0.0

    def maybe_strike(self, probability: float) -> bool:
        if self._rng.random() < probability:
            self._spawn_bolt()
            return True
        return False

    def _spawn_bolt(self) -> None:
        x0 = self._rng.randint(0, self.width)
        y0 = self._rng.randint(0, int(self.height * 0.25))
        x1 = self._rng.randint(int(self.width * 0.15), int(self.width * 0.85))
        y1 = self._rng.randint(int(self.height * 0.45), int(self.height * 0.85))
        pts = _mid_displace((x0, y0), (x1, y1), roughness=0.9, depth=5, rng=self._rng)
        self.bolts.append(LightningBolt(pts, ttl=0.12 + self._rng.uniform(0.0, 0.06), thickness=self._rng.randint(2, 4)))
        # Trigger a quick flash
        self.flash_alpha = 0.14 + self._rng.uniform(0.0, 0.08)

    def update(self, dt: float) -> None:
        for b in self.bolts:
            b.update(dt)
        self.bolts = [b for b in self.bolts if b.alive]
        self.flash_alpha = max(0.0, self.flash_alpha - dt * 1.8)

    def draw(self, s: pygame.Surface) -> None:
        for b in self.bolts:
            b.draw(s)
