# powerups_manager.py
# Centralized spawn/update/draw/pickup handling for PowerUps (with FX & magnet support).
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import pygame
import random

from powerups import PowerUp, POWERUP_DROP_CHANCE, spawn_powerup_at
from powerups_fx import FloatingText, RingBurst

@dataclass
class PowerUpManager:
    width: int
    height: int
    rng: random.Random = field(default_factory=random.Random)
    powerups: List[PowerUp] = field(default_factory=list)
    fx: List[object] = field(default_factory=list)  # mixed FloatingText/RingBurst

    def clear(self) -> None:
        self.powerups.clear()
        self.fx.clear()

    # ---------------- Spawning ----------------
    def maybe_drop(self, x: float, y: float, chance: float = POWERUP_DROP_CHANCE) -> None:
        if self.rng.random() < chance:
            self.powerups.append(spawn_powerup_at(x, y - 12))

    def force_drop(self, x: float, y: float, kind: str) -> None:
        self.powerups.append(spawn_powerup_at(x, y - 12, kind=kind))

    # ---------------- Update/Draw ----------------
    def update(self, dt: float, game) -> None:
        # Player center & magnet radius if available
        player = getattr(game, "player", None)
        player_center: Optional[Tuple[float, float]] = None
        magnet_radius = 0.0
        player_rect: Optional[pygame.Rect] = None

        if player is not None:
            # Derive a reasonable pickup center from player's rect or x/y
            if hasattr(player, "rect"):
                try:
                    pr = player.rect  # property
                except Exception:
                    pr = None
            else:
                pr = None
            if isinstance(pr, pygame.Rect):
                player_rect = pr
                player_center = pr.center
            else:
                px = getattr(player, "x", 0.0)
                py = getattr(player, "y", 0.0)
                player_center = (px, py)

            # Magnet/pickup radius (opt-in)
            magnet_radius = float(getattr(player, "pickup_magnet_radius", 0.0))

        # Update powerups
        for p in self.powerups:
            p.update(dt, player_center=player_center, magnet_radius=magnet_radius)

        # Pickups (point or rect)
        collected: List[PowerUp] = []
        for p in self.powerups:
            picked = False
            if player_rect is not None:
                picked = p.collides_with_rect(player_rect)
            elif player_center is not None:
                picked = p.collides_with_point(player_center[0], player_center[1])

            if picked:
                label = p.apply(game)
                collected.append(p)
                # FX & sounds
                self.fx.append(RingBurst(x=p.x, y=p.y, radius=14, radius_to=40, color=p.color))
                self.fx.append(FloatingText(x=p.x, y=p.y - 4, text=label, color=(20, 20, 20)))
                sfx_pick = getattr(game, "sfx_pickup", None)
                if sfx_pick is not None:
                    try:
                        sfx_pick.play()
                    except Exception:
                        pass

        if collected:
            self.powerups = [p for p in self.powerups if p not in collected]

        # Cull expired
        self.powerups = [p for p in self.powerups if p.alive]

        # Update FX
        next_fx = []
        for f in self.fx:
            f.update(dt)
            if getattr(f, "alive", True):
                next_fx.append(f)
        self.fx = next_fx

    def draw(self, screen: pygame.Surface) -> None:
        for p in self.powerups:
            p.draw(screen)
        for f in self.fx:
            f.draw(screen)
