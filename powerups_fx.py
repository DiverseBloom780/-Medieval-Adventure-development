# powerups_fx.py
# Lightweight pickup visuals: floating text + expanding ring burst.
from __future__ import annotations
from dataclasses import dataclass
import pygame

@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: tuple[int, int, int] = (255, 255, 255)
    ttl: float = 1.1
    vy: float = -36.0
    _age: float = 0.0

    @property
    def alive(self) -> bool:
        return self._age < self.ttl

    def update(self, dt: float) -> None:
        self._age += dt
        self.y += self.vy * dt

    def draw(self, s: pygame.Surface) -> None:
        alpha = int(255 * max(0.0, 1.0 - self._age / self.ttl))
        font = pygame.font.SysFont("consolas", 16, bold=True)
        surf = font.render(self.text, True, self.color)
        # simple alpha fade
        if alpha < 255:
            surf = surf.copy()
            surf.set_alpha(alpha)
        s.blit(surf, surf.get_rect(center=(int(self.x), int(self.y))))

@dataclass
class RingBurst:
    x: float
    y: float
    radius: float
    radius_to: float
    color: tuple[int, int, int] = (255, 255, 255)
    ttl: float = 0.35
    _age: float = 0.0

    @property
    def alive(self) -> bool:
        return self._age < self.ttl

    def update(self, dt: float) -> None:
        self._age += dt

    def draw(self, s: pygame.Surface) -> None:
        t = min(1.0, self._age / self.ttl)
        r = int(self.radius + (self.radius_to - self.radius) * t)
        alpha = int(180 * (1.0 - t))
        surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, alpha), (surf.get_width() // 2, surf.get_height() // 2), r, 3)
        s.blit(surf, (int(self.x) - surf.get_width() // 2, int(self.y) - surf.get_height() // 2))
