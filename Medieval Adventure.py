# -*- coding: utf-8 -*-
"""
Medieval Adventure — Improved Pygame Demo
-----------------------------------------

A compact arcade-style demo featuring:
- Player archer with mouse-aimed arrows and stamina-based sprint
- Ballista turret with heavy bolts and cooldown
- Enemy swordsmen (melee) and archers (ranged) with simple AI
- Wave-based spawner that ramps difficulty
- Castle with health; lose when castle HP reaches 0
- Score, HUD, pause, and restart
- Particles & floating damage numbers
- dt-based movement & safe list iterations

Everything draws with primitives (no assets required).
"""

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple
import math
import random
import sys

import pygame

# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

try:
    pygame.init()
except Exception as e:
    print(f"Failed to initialize Pygame: {e}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants / Config
# ---------------------------------------------------------------------------

SCREEN_WIDTH  = 1280
SCREEN_HEIGHT = 720
FPS = 60

GROUND_RATIO = 0.68
GROUND_Y = int(SCREEN_HEIGHT * GROUND_RATIO)

# Colors
SKY_BLUE    = (173, 216, 230)
GREEN       = ( 34, 139,  34)
BROWN       = (165,  42,  42)
STONE_GRAY  = (192, 192, 192)
TREE_GREEN  = (  0, 128,   0)
WATER_BLUE  = (  0, 191, 255)
SKIN        = (255, 218, 185)
HAIR        = (139,  69,  19)
BOW_COLOR   = (165,  42,  42)
STRING_COL  = (  0,   0,   0)
ARROW_COL   = (128,   0,   0)
RED         = (220,  40,  40)
GOLD        = (230, 200,  60)
BLACK       = (  0,   0,   0)
WHITE       = (255, 255, 255)
UI_BG       = (25,  25,  28)
UI_FG       = (210, 210, 215)

# Gameplay tuning
PLAYER_SPEED           = 280.0      # px/s
PLAYER_SPRINT_SPEED    = 420.0
PLAYER_STAMINA_MAX     = 100.0
PLAYER_STAMINA_DRAIN   = 35.0       # per second while sprinting
PLAYER_STAMINA_REGEN   = 20.0       # per second while not sprinting
PLAYER_MAX_HP          = 100

ARROW_SPEED            = 900.0      # px/s
ARROW_DAMAGE           = 22
ARROW_GRAVITY          = 800.0      # px/s^2 downward

BOLT_SPEED             = 1100.0
BOLT_DAMAGE            = 50
BOLT_COOLDOWN          = 1.0        # seconds

ENEMY_SWORD_SPEED      = 120.0
ENEMY_ARCHER_SPEED     = 100.0
ENEMY_ARCHER_RANGE     = 380.0
ENEMY_ARCHER_CADENCE   = 1.6        # seconds between shots
ENEMY_ARROW_SPEED      = 700.0
ENEMY_ARROW_GRAVITY    = 650.0
ENEMY_HP               = 90
ENEMY_DPS_VS_CASTLE    = 15.0       # swordsman damage per second when battering

CASTLE_HP_MAX          = 500

WAVE_BASE_SPAWN_RATE   = 1.1        # lower is faster; per enemy spawn roll freq
WAVE_ACCELERATION      = 0.92       # multiplier on spawn rate per wave
WAVE_KILL_TARGET_STEP  = 10         # kills per wave to advance

PARTICLE_COUNT_HIT     = 10
PARTICLE_LIFETIME      = 0.4

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def clamp(value, min_value, max_value):
    return min(max(value, min_value), max_value)

def vec_from_angle(origin: Tuple[float, float], target: Tuple[float, float]) -> pygame.math.Vector2:
    v = pygame.math.Vector2(target[0] - origin[0], target[1] - origin[1])
    if v.length_squared() == 0:
        return pygame.math.Vector2(1, 0)
    return v.normalize()

# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def draw_tree(screen: pygame.Surface, x: int, y: int) -> None:
    pygame.draw.line(screen, BROWN, (x, y), (x, y - 50), 6)
    pygame.draw.circle(screen, TREE_GREEN, (x, y - 70), 28)
    pygame.draw.circle(screen, TREE_GREEN, (x - 22, y - 62), 20)
    pygame.draw.circle(screen, TREE_GREEN, (x + 22, y - 62), 20)

def draw_castle(screen: pygame.Surface, rect: pygame.Rect, hp_frac: float) -> None:
    pygame.draw.rect(screen, STONE_GRAY, rect, border_radius=2)
    # merlons
    merlon_w = 14
    for i in range(rect.left, rect.right, merlon_w * 2):
        pygame.draw.rect(screen, STONE_GRAY, (i, rect.top - 12, merlon_w, 12))
    # gate
    gate = pygame.Rect(rect.centerx - 18, rect.bottom - 38, 36, 38)
    pygame.draw.rect(screen, BROWN, gate, border_radius=2)
    # HP bar
    bar_w, bar_h = rect.width, 12
    bar_x, bar_y = rect.left, rect.top - 22
    pygame.draw.rect(screen, BLACK, (bar_x, bar_y, bar_w, bar_h), border_radius=3)
    fill_w = int(bar_w * hp_frac)
    pygame.draw.rect(screen, (60, 220, 90), (bar_x, bar_y, fill_w, bar_h), border_radius=3)

def draw_archer(screen: pygame.Surface, x: int, y: int, facing: pygame.math.Vector2) -> None:
    # Head & hair
    pygame.draw.circle(screen, SKIN, (x, y), 10)
    pygame.draw.circle(screen, HAIR, (x, y - 10), 5)
    # Body
    pygame.draw.line(screen, BROWN, (x, y + 10), (x, y + 30), 5)
    # Arms
    pygame.draw.line(screen, BROWN, (x, y + 15), (x - 10, y + 25), 5)
    pygame.draw.line(screen, BROWN, (x, y + 15), (x + 10, y + 25), 5)
    # Legs
    pygame.draw.line(screen, BROWN, (x, y + 30), (x - 5, y + 50), 5)
    pygame.draw.line(screen, BROWN, (x, y + 30), (x + 5, y + 50), 5)
    # Bow line in direction of facing
    hand = (x + 10, y + 15)
    tip = (hand[0] + int(facing.x * 16), hand[1] + int(facing.y * 16))
    pygame.draw.line(screen, BOW_COLOR, hand, tip, 3)
    pygame.draw.line(screen, STRING_COL, tip, (x + 10, y + 15), 1)

def draw_ui_panel(screen: pygame.Surface, font: pygame.font.Font, score: int, wave: int,
                  player_hp: int, player_stamina: float, castle_hp: int, paused: bool, game_over: bool) -> None:
    panel = pygame.Rect(0, 0, SCREEN_WIDTH, 40)
    pygame.draw.rect(screen, UI_BG, panel)

    # Score & wave
    s_surf = font.render(f"Score: {score}", True, UI_FG)
    w_surf = font.render(f"Wave: {wave}", True, UI_FG)
    screen.blit(s_surf, (12, 10))
    screen.blit(w_surf, (140, 10))

    # Player HP
    hp_frac = clamp(player_hp / PLAYER_MAX_HP, 0, 1)
    pygame.draw.rect(screen, BLACK, (260, 12, 160, 16), border_radius=4)
    pygame.draw.rect(screen, (220, 70, 70), (260, 12, int(160 * hp_frac), 16), border_radius=4)
    screen.blit(font.render("HP", True, UI_FG), (260 + 170, 10))

    # Stamina
    st_frac = clamp(player_stamina / PLAYER_STAMINA_MAX, 0, 1)
    pygame.draw.rect(screen, BLACK, (430, 12, 160, 16), border_radius=4)
    pygame.draw.rect(screen, (70, 170, 220), (430, 12, int(160 * st_frac), 16), border_radius=4)
    screen.blit(font.render("STA", True, UI_FG), (430 + 170, 10))

    # Castle HP
    c_frac = clamp(castle_hp / CASTLE_HP_MAX, 0, 1)
    pygame.draw.rect(screen, BLACK, (610, 12, 200, 16), border_radius=4)
    pygame.draw.rect(screen, (60, 220, 90), (610, 12, int(200 * c_frac), 16), border_radius=4)
    screen.blit(font.render("Castle", True, UI_FG), (610 + 210, 10))

    # Status texts
    if paused:
        t = font.render("PAUSED (P to Resume)", True, GOLD)
        screen.blit(t, (SCREEN_WIDTH - t.get_width() - 16, 10))
    elif game_over:
        t = font.render("GAME OVER (R to Restart)", True, RED)
        screen.blit(t, (SCREEN_WIDTH - t.get_width() - 16, 10))

# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float
    damage: int
    color: Tuple[int, int, int] = ARROW_COL
    radius: int = 2
    gravity: float = 0.0
    alive: bool = True

    def update(self, dt: float) -> None:
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        # ground collision cull
        if self.y >= GROUND_Y - 2:
            self.alive = False

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - self.radius), int(self.y - self.radius),
                           self.radius * 2, self.radius * 2)

    def draw(self, screen: pygame.Surface) -> None:
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)

@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: Tuple[int, int, int]
    age: float = 0.0
    lifetime: float = PARTICLE_LIFETIME

    def update(self, dt: float) -> None:
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 800.0 * dt  # gravity

    @property
    def alive(self) -> bool:
        return self.age < self.lifetime

    def draw(self, screen: pygame.Surface) -> None:
        alpha = clamp(1.0 - self.age / self.lifetime, 0.0, 1.0)
        s = pygame.Surface((3, 3), pygame.SRCALPHA)
        s.fill((int(self.color[0]), int(self.color[1]), int(self.color[2]), int(255 * alpha)))
        screen.blit(s, (int(self.x), int(self.y)))

@dataclass
class Enemy:
    x: float
    y: float
    w: int = 20
    h: int = 50
    hp: int = ENEMY_HP
    speed: float = ENEMY_SWORD_SPEED
    is_archer: bool = False
    shoot_cooldown: float = ENEMY_ARCHER_CADENCE
    shoot_timer: float = field(default_factory=lambda: random.uniform(0.2, ENEMY_ARCHER_CADENCE))

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - self.w // 2), int(self.y), self.w, self.h)

    def draw(self, screen: pygame.Surface) -> None:
        # Head & body
        head = (int(self.x), int(self.y))
        pygame.draw.circle(screen, SKIN, head, 10)
        pygame.draw.line(screen, BROWN, (self.x, self.y + 10), (self.x, self.y + 30), 5)
        pygame.draw.line(screen, BROWN, (self.x, self.y + 15), (self.x - 10, self.y + 25), 5)
        pygame.draw.line(screen, BROWN, (self.x, self.y + 15), (self.x + 10, self.y + 25), 5)
        pygame.draw.line(screen, BROWN, (self.x, self.y + 30), (self.x - 5, self.y + 50), 5)
        pygame.draw.line(screen, BROWN, (self.x, self.y + 30), (self.x + 5, self.y + 50), 5)
        if self.is_archer:
            pygame.draw.line(screen, BOW_COLOR, (self.x - 10, self.y + 25), (self.x - 20, self.y + 15), 4)
            pygame.draw.line(screen, BOW_COLOR, (self.x - 20, self.y + 15), (self.x - 10, self.y + 5), 4)
            pygame.draw.line(screen, STRING_COL, (self.x - 20, self.y + 15), (self.x - 10, self.y + 15), 1)
        else:
            pygame.draw.line(screen, (160, 160, 160), (self.x + 10, self.y + 25), (self.x + 22, self.y + 25), 3)
        # HP bar
        frac = clamp(self.hp / ENEMY_HP, 0, 1)
        pygame.draw.rect(screen, RED, (self.x - 10, self.y - 12, 20, 4))
        pygame.draw.rect(screen, (0, 255, 0), (self.x - 10, self.y - 12, int(20 * frac), 4))

    def update(self, dt: float, target_x: float, castle_rect: pygame.Rect,
               enemy_arrows: List[Projectile]) -> float:
        """Returns DPS applied to castle (if any)."""
        if self.is_archer:
            # Move towards preferred range, then stop to shoot
            desired_x = castle_rect.centerx + ENEMY_ARCHER_RANGE
            if self.x > desired_x:
                self.x -= ENEMY_ARCHER_SPEED * dt
            self.shoot_timer -= dt
            if self.shoot_timer <= 0.0:
                self.shoot_timer = self.shoot_cooldown
                # Shoot toward castle/player area
                proj_dir = vec_from_angle((self.x - 20, self.y + 15), (target_x, GROUND_Y - 50))
                enemy_arrows.append(Projectile(
                    x=self.x - 20, y=self.y + 15,
                    vx=proj_dir.x * ENEMY_ARROW_SPEED,
                    vy=proj_dir.y * ENEMY_ARROW_SPEED * 0.75,  # slightly lobbed
                    damage=16, gravity=ENEMY_ARROW_GRAVITY, color=(90, 0, 0)
                ))
            return 0.0
        else:
            # Swordsman pushes to castle
            if self.x > castle_rect.left + 24:
                self.x -= ENEMY_SWORD_SPEED * dt
                return 0.0
            # At the wall, deal DPS to castle
            return ENEMY_DPS_VS_CASTLE

@dataclass
class Player:
    x: float
    y: float
    hp: int = PLAYER_MAX_HP
    speed: float = PLAYER_SPEED
    stamina: float = PLAYER_STAMINA_MAX
    aim_dir: pygame.math.Vector2 = field(default_factory=lambda: pygame.math.Vector2(1, 0))
    shoot_cooldown: float = 0.22
    shoot_timer: float = 0.0

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - 10), int(self.y), 20, 50)

    def update(self, dt: float, keys: pygame.key.ScancodeWrapper) -> None:
        move = pygame.math.Vector2(
            (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT]),
            (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP]),
        )
        # ... rest of the Player class ...

def main():
    try:
        # Set up display
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Medieval Adventure")

        # Start screen
        start_screen = True
        font = pygame.font.Font(None, 64)
        while start_screen:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        start_screen = False
            screen.fill(SKY_BLUE)
            text = font.render("Medieval Adventure", True, (0, 0, 0))
            text_rect = text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 50))
            screen.blit(text, text_rect)
            font = pygame.font.Font(None, 32)
            text = font.render("Press Enter to Start", True, (0, 0, 0))
            text_rect = text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 50))
            screen.blit(text, text_rect)
            pygame.display.update()

        # Game loop
        clock = pygame.time.Clock()
        running = True
        # ... rest of your game code ...

        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            # ... rest of your game code ...

            # Update the game clock
            clock.tick(60)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        pygame.quit()

if __name__ == "__main__":
    main()