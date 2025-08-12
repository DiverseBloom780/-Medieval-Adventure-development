# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple
import math
import random
import pygame

# Visuals
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Drop & lifetime tuning
POWERUP_DROP_CHANCE   = 0.25   # 25% on enemy death
POWERUP_TTL_SECONDS   = 14.0
POWERUP_RADIUS        = 12

# Types
class PowerUpType:
    REPAIR_CASTLE = "repair"
    STAMINA_VIAL  = "stamina"
    TRIPLE_SHOT   = "triple"

# Palette per type
TYPE_COLOR = {
    PowerUpType.REPAIR_CASTLE: (80, 200, 120),
    PowerUpType.STAMINA_VIAL:  (70, 170, 220),
    PowerUpType.TRIPLE_SHOT:   (230, 200, 60),
}
TYPE_LABEL = {
    PowerUpType.REPAIR_CASTLE: "H",  # heal
    PowerUpType.STAMINA_VIAL:  "S",  # stamina
    PowerUpType.TRIPLE_SHOT:   "3",  # triple shot
}

@dataclass
class PowerUp:
    x: float
    y: float
    kind: str
    ttl: float = POWERUP_TTL_SECONDS
    phase: float = 0.0  # for bobbing

    @property
    def color(self) -> Tuple[int, int, int]:
        return TYPE_COLOR.get(self.kind, WHITE)

    def update(self, dt: float) -> None:
        self.phase += dt * 3.2
        self.ttl = max(0.0, self.ttl - dt)

    @property
    def alive(self) -> bool:
        return self.ttl > 0.0

    def draw(self, screen: pygame.Surface) -> None:
        bob = math.sin(self.phase) * 4.0
        pos = (int(self.x), int(self.y + bob))
        pygame.draw.circle(screen, self.color, pos, POWERUP_RADIUS)
        pygame.draw.circle(screen, BLACK, pos, POWERUP_RADIUS, 2)

        # label
        font = pygame.font.SysFont("consolas", 16, bold=True)
        text = font.render(TYPE_LABEL.get(self.kind, "?"), True, BLACK)
        rect = text.get_rect(center=pos)
        screen.blit(text, rect)

    def collides_with(self, px: float, py: float) -> bool:
        # player center-ish pickup
        dx = self.x - px
        dy = self.y - py
        return (dx*dx + dy*dy) <= (POWERUP_RADIUS + 10) ** 2

    def apply(self, game) -> None:
        """Apply the effect to the game/player. 'game' is your Game instance."""
        if self.kind == PowerUpType.REPAIR_CASTLE:
            from main import CASTLE_HP_MAX  # local import to avoid circular at import time
            game.castle_hp = min(CASTLE_HP_MAX, game.castle_hp + 60)
        elif self.kind == PowerUpType.STAMINA_VIAL:
            game.player.stamina = game.player.stamina_max
        elif self.kind == PowerUpType.TRIPLE_SHOT:
            game.player.activate_triple_shot(duration=8.0)

def random_powerup_kind() -> str:
    # Slightly weighted toward instant effects
    roll = random.random()
    if roll < 0.45:
        return PowerUpType.REPAIR_CASTLE
    if roll < 0.80:
        return PowerUpType.STAMINA_VIAL
    return PowerUpType.TRIPLE_SHOT

def spawn_powerup_at(x: float, y: float) -> PowerUp:
    return PowerUp(x=x, y=y, kind=random_powerup_kind())
