# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Tuple, Optional, Dict
import math
import random
import pygame

# ---------------------------------------------------------
# Visuals & tuning
# ---------------------------------------------------------
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

POWERUP_DROP_CHANCE   = 0.25   # used by PowerUpManager.maybe_drop(...)
POWERUP_TTL_SECONDS   = 14.0
POWERUP_RADIUS        = 12
POWERUP_BLINK_START   = 3.0    # start blinking N seconds before expiry
POWERUP_ARC_WIDTH     = 2      # TTL ring width

# ---------------------------------------------------------
# Types (string keys for easy integration)
# ---------------------------------------------------------
class PowerUpType:
    REPAIR_CASTLE = "repair"
    STAMINA_VIAL  = "stamina"
    TRIPLE_SHOT   = "triple"
    COIN_POUCH    = "coin"      # NEW: +score

ALL_POWERUP_TYPES = (
    PowerUpType.REPAIR_CASTLE,
    PowerUpType.STAMINA_VIAL,
    PowerUpType.TRIPLE_SHOT,
    PowerUpType.COIN_POUCH,
)

# Palette per type
TYPE_COLOR: Dict[str, Tuple[int, int, int]] = {
    PowerUpType.REPAIR_CASTLE: ( 80, 200, 120),
    PowerUpType.STAMINA_VIAL:  ( 70, 170, 220),
    PowerUpType.TRIPLE_SHOT:   (230, 200,  60),
    PowerUpType.COIN_POUCH:    (250, 210,  80),
}

TYPE_LABEL: Dict[str, str] = {
    PowerUpType.REPAIR_CASTLE: "H",   # heal
    PowerUpType.STAMINA_VIAL:  "S",   # stamina
    PowerUpType.TRIPLE_SHOT:   "3",   # triple shot
    PowerUpType.COIN_POUCH:    "$",   # score
}

# Cached font (avoid recreating every frame)
_FONT_CACHE: Optional[pygame.font.Font] = None
def _get_font() -> pygame.font.Font:
    global _FONT_CACHE
    if _FONT_CACHE is None:
        _FONT_CACHE = pygame.font.SysFont("consolas", 16, bold=True)
    return _FONT_CACHE

# ---------------------------------------------------------
# PowerUp Entity
# ---------------------------------------------------------
@dataclass
class PowerUp:
    x: float
    y: float
    kind: str
    ttl: float = POWERUP_TTL_SECONDS
    ttl_max: float = POWERUP_TTL_SECONDS
    phase: float = 0.0  # for bobbing/pulse
    vx: float = 0.0     # used for magnet attraction
    vy: float = 0.0

    # --- Derived props ---
    @property
    def color(self) -> Tuple[int, int, int]:
        return TYPE_COLOR.get(self.kind, WHITE)

    @property
    def alive(self) -> bool:
        return self.ttl > 0.0

    @property
    def pos(self) -> Tuple[int, int]:
        # subtle bobbing for visibility
        bob = math.sin(self.phase) * 4.0
        return (int(self.x), int(self.y + bob))

    def rect(self) -> pygame.Rect:
        p = self.pos
        return pygame.Rect(p[0] - POWERUP_RADIUS, p[1] - POWERUP_RADIUS,
                           POWERUP_RADIUS * 2, POWERUP_RADIUS * 2)

    # --- Behaviour ---
    def update(self, dt: float, player_center: Optional[Tuple[float, float]] = None,
               magnet_radius: float = 0.0) -> None:
        """Bobbing, lifetime, optional magnet attraction to player."""
        self.phase += dt * 3.2
        self.ttl = max(0.0, self.ttl - dt)

        # Attraction to player if inside magnet radius (gentle tween)
        if player_center and magnet_radius > 0.0:
            px, py = player_center
            dx = px - self.x
            dy = py - self.y
            dist2 = dx*dx + dy*dy
            if dist2 <= magnet_radius * magnet_radius:
                dist = math.sqrt(dist2) if dist2 > 0 else 1.0
                nx, ny = dx / dist, dy / dist
                speed = 380.0  # px/s
                self.vx = nx * speed
                self.vy = ny * speed
                self.x += self.vx * dt
                self.y += self.vy * dt

    def draw(self, screen: pygame.Surface) -> None:
        p = self.pos
        # body
        pygame.draw.circle(screen, self.color, p, POWERUP_RADIUS)
        # outline
        pygame.draw.circle(screen, BLACK, p, POWERUP_RADIUS, 2)

        # TTL ring (remaining time)
        if self.ttl_max > 0.0:
            frac = max(0.0, min(1.0, self.ttl / self.ttl_max))
            start_ang = -math.pi / 2
            end_ang = start_ang + 2 * math.pi * frac
            rect = pygame.Rect(p[0] - POWERUP_RADIUS - 3, p[1] - POWERUP_RADIUS - 3,
                               (POWERUP_RADIUS + 3) * 2, (POWERUP_RADIUS + 3) * 2)
            pygame.draw.arc(screen, BLACK, rect, start_ang, end_ang, POWERUP_ARC_WIDTH)

        # Blink when near expiry
        if self.ttl <= POWERUP_BLINK_START:
            blink = 0.5 + 0.5 * math.sin(self.phase * 8.0)
            alpha = int(140 * blink)
            glow = pygame.Surface((POWERUP_RADIUS * 4, POWERUP_RADIUS * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*self.color, alpha),
                               (glow.get_width() // 2, glow.get_height() // 2),
                               POWERUP_RADIUS + 6, width=4)
            screen.blit(glow, (p[0] - glow.get_width() // 2, p[1] - glow.get_height() // 2))

        # label
        text = _get_font().render(TYPE_LABEL.get(self.kind, "?"), True, BLACK)
        screen.blit(text, text.get_rect(center=p))

    # --- Collision helpers ---
    def collides_with_point(self, px: float, py: float) -> bool:
        dx = self.x - px
        dy = self.y - py
        return (dx*dx + dy*dy) <= (POWERUP_RADIUS + 10) ** 2  # forgiving pickup

    def collides_with_rect(self, r: pygame.Rect) -> bool:
        return self.rect().colliderect(r)

    # --- Effect application ---
    def apply(self, game) -> str:
        """
        Apply the effect to the game/player.
        Returns a short pickup label for UI feedback.
        """
        player = getattr(game, "player", None)

        if self.kind == PowerUpType.REPAIR_CASTLE:
            # Avoid circular imports; read max from game with sensible defaults.
            castle_hp_max = getattr(game, "CASTLE_HP_MAX", getattr(game, "castle_hp_max", 500))
            game.castle_hp = min(castle_hp_max, getattr(game, "castle_hp", castle_hp_max) + 60)
            return "+60 HP (Castle)"

        if self.kind == PowerUpType.STAMINA_VIAL and player is not None:
            stamina_max = getattr(player, "stamina_max", getattr(player, "stamina", 100))
            player.stamina = stamina_max
            return "Stamina Full"

        if self.kind == PowerUpType.TRIPLE_SHOT and player is not None:
            # Prefer explicit method if user's Player implements it
            if hasattr(player, "activate_triple_shot"):
                player.activate_triple_shot(duration=8.0)
            else:
                # Fallback: set simple timers/flags the game can consume
                setattr(player, "triple_shot_timer",
                        getattr(player, "triple_shot_timer", 0.0) + 8.0)
                setattr(player, "triple_shot_active", True)
            return "Triple Shot"

        if self.kind == PowerUpType.COIN_POUCH:
            game.score = getattr(game, "score", 0) + 50
            return "+50 Score"

        return "Picked"
        

# ---------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------
def random_powerup_kind() -> str:
    """Weighted choice favoring bread‑and‑butter powerups."""
    roll = random.random()
    if roll < 0.36:
        return PowerUpType.REPAIR_CASTLE
    if roll < 0.70:
        return PowerUpType.STAMINA_VIAL
    if roll < 0.90:
        return PowerUpType.TRIPLE_SHOT
    return PowerUpType.COIN_POUCH

def spawn_powerup_at(x: float, y: float, kind: Optional[str] = None) -> PowerUp:
    return PowerUp(x=float(x), y=float(y), kind=kind or random_powerup_kind())
