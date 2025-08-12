# weather.py
# Tiny weather controller for Pygame scenes (rain, storm, fog, clouds).
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import pygame
import random
import math

Color = Tuple[int, int, int]

@dataclass
class Raindrop:
    x: float
    y: float
    vx: float
    vy: float
    life: float

    def update(self, dt: float, width: int, height: int) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        if self.y > height + 8:
            self.life = 0.0

    def draw(self, s: pygame.Surface) -> None:
        # draw as a short line
        end = (int(self.x - self.vx * 0.02), int(self.y - self.vy * 0.02))
        pygame.draw.line(s, (170, 170, 200), (int(self.x), int(self.y)), end, 1)

@dataclass
class WeatherController:
    width: int
    height: int
    seed: int = 4242
    state: str = "clear"  # clear | rain | storm | fog
    density: float = 0.0  # 0..1 base intensity
    wind: float = -60.0   # px/s (negative = left)
    drops: List[Raindrop] = field(default_factory=list)
    _rng: random.Random = field(default_factory=random.Random)
    _flash: float = 0.0   # storm flash timer
    _fog_phase: float = 0.0

    def __post_init__(self) -> None:
        self._rng.seed(self.seed)

    def set_state(self, state: str, density: float = 0.6) -> None:
        self.state = state
        self.density = max(0.0, min(1.0, density))

    def ambient_darkening(self) -> float:
        """Extra darkness to apply in world tint (0..1)."""
        if self.state == "clear":
            return 0.0
        if self.state == "fog":
            return 0.12 * self.density
        if self.state == "rain":
            return 0.18 * self.density
        if self.state == "storm":
            return 0.35 * self.density
        return 0.0

    def update(self, dt: float) -> None:
        # Rain/storm particle spawn
        if self.state in ("rain", "storm"):
            want = int(400 * self.density)
            while len(self.drops) < want:
                x = self._rng.uniform(-20, self.width + 20)
                y = self._rng.uniform(-50, -4)
                vx = self.wind + self._rng.uniform(-30, 10)
                vy = self._rng.uniform(400, 720) * (1.2 if self.state == "storm" else 1.0)
                life = self._rng.uniform(0.6, 2.0)
                self.drops.append(Raindrop(x, y, vx, vy, life))

        # Update particles
        for d in self.drops:
            d.update(dt, self.width, self.height)
        self.drops = [d for d in self.drops if d.life > 0.0]

        # Thunder flash
        if self.state == "storm":
            self._flash = max(0.0, self._flash - dt)
            if self._flash <= 0.0 and self._rng.random() < 0.02 * self.density:
                # occasional quick flash
                self._flash = self._rng.uniform(0.06, 0.18)

        # Fog phase for subtle motion
        if self.state == "fog":
            self._fog_phase += dt * 0.1

    # Background effects (behind world)
    def draw_background(self, s: pygame.Surface, ground_y: int) -> None:
        if self.state == "fog":
            # Low-lying fog bank (background)
            fog = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            for i in range(6):
                y = int(ground_y - 30 + i * 12 + math.sin(self._fog_phase + i) * 6)
                alpha = int(30 + i * 12 * self.density)
                pygame.draw.rect(fog, (210, 210, 210, alpha), (0, y, self.width, 14))
            s.blit(fog, (0, 0))

    # Foreground effects (in front of world)
    def draw_foreground(self, s: pygame.Surface) -> None:
        if self.state in ("rain", "storm"):
            for d in self.drops:
                d.draw(s)
        if self._flash > 0.0:
            veil = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            veil.fill((255, 255, 255, int(160 * min(1.0, self._flash * 10))))
            s.blit(veil, (0, 0))
        if self.state == "fog":
            # Foreground veil
            alpha = int(90 * self.density)
            fog = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            fog.fill((220, 220, 220, alpha))
            s.blit(fog, (0, 0))
