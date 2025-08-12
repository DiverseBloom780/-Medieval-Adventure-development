# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Medieval Adventure — Improved Pygame Demo (+ Day–Night Cycle)
-------------------------------------------------------------
Adds a reusable time-of-day system:
- Animated sky color across day phases
- Sun/Moon orbits
- Twinkling stars
- Night-time world tint

Everything draws with primitives (no assets required).
"""

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

import math
import random
import sys
import pygame
from dataclasses import dataclass, field
from typing import List, Tuple

# NEW: day–night cycle module
from timecycle import TimeOfDayCycle

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

MERLON_WIDTH = 14
GATE_WIDTH = 36
GATE_HEIGHT = 38
HEALTH_BAR_GREEN = (60, 220, 90)

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
    for i in range(rect.left, rect.right, MERLON_WIDTH * 2):
        pygame.draw.rect(screen, STONE_GRAY, (i, rect.top - 12, MERLON_WIDTH, 12))
    # gate
    gate = pygame.Rect(rect.centerx - GATE_WIDTH / 2, rect.bottom - GATE_HEIGHT, GATE_WIDTH, GATE_HEIGHT)
    pygame.draw.rect(screen, BROWN, gate, border_radius=2)
    # HP bar
    bar_w, bar_h = rect.width, 12
    bar_x, bar_y = rect.left, rect.top - 22
    pygame.draw.rect(screen, BLACK, (bar_x, bar_y, bar_w, bar_h), border_radius=3)
    fill_w = int(bar_w * hp_frac)
    pygame.draw.rect(screen, HEALTH_BAR_GREEN, (bar_x, bar_y, fill_w, bar_h), border_radius=3)

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

    # Status texts (placeholders for future states)
    if paused:
        t = font.render("PAUSED (P to Resume)", True, GOLD)
        screen.blit(t, (SCREEN_WIDTH - t.get_width() - 16, 10))
    elif game_over:
        t = font.render("GAME OVER (R to Restart)", True, RED)
        screen.blit(t, (SCREEN_WIDTH - t.get_width() - 16, 10))

# ---------------------------------------------------------------------------
# Entities (stubs kept to match your structure; not used in this minimal loop)
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
        self.vy += 800.0 * dt

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
        frac = clamp(self.hp / ENEMY_HP, 0, 1)
        pygame.draw.rect(screen, RED, (self.x - 10, self.y - 12, 20, 4))
        pygame.draw.rect(screen, (0, 255, 0), (self.x - 10, self.y - 12, int(20 * frac), 4))

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
        # Placeholder to match your original structure
        pass

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        # Display & timing
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Medieval Adventure")
        clock = pygame.time.Clock()
        font_big = pygame.font.Font(None, 64)
        font_small = pygame.font.Font(None, 32)
        font_ui = pygame.font.Font(None, 24)

        # NEW: day–night cycle
        cycle = TimeOfDayCycle(SCREEN_WIDTH, SCREEN_HEIGHT, duration=90.0)

        # Title screen
        start_screen = True
        while start_screen:
            dt = clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    start_screen = False

            cycle.update(dt)
            cycle.draw_sky(screen, GROUND_Y)

            # Simple ground to anchor the horizon visually
            pygame.draw.rect(screen, GREEN, (0, GROUND_Y, SCREEN_WIDTH, SCREEN_HEIGHT - GROUND_Y))

            title_text = font_big.render("Medieval Adventure", True, (0, 0, 0))
            start_text = font_small.render("Press Enter to Start", True, (0, 0, 0))
            screen.blit(title_text, title_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 50)))
            screen.blit(start_text, start_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 50)))

            pygame.display.update()

        # Minimal loop (castle showcase + cycle running)
        castle_rect = pygame.Rect(100, GROUND_Y - 100, 200, 100)
        running = True
        score, wave = 0, 1
        player_hp = PLAYER_MAX_HP
        player_sta = PLAYER_STAMINA_MAX
        castle_hp = CASTLE_HP_MAX
        paused = False
        game_over = False

        while running:
            dt = clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            # Update the day–night cycle
            cycle.update(dt)

            # Sky & background (feature integration)
            cycle.draw_sky(screen, GROUND_Y)

            # World
            pygame.draw.rect(screen, GREEN, (0, GROUND_Y, SCREEN_WIDTH, SCREEN_HEIGHT - GROUND_Y))
            draw_castle(screen, castle_rect, 1.0)

            # Optional scenery
            draw_tree(screen, 500, GROUND_Y + 48)
            draw_tree(screen, 720, GROUND_Y + 48)

            # Night-time world tint on top of world (feature integration)
            cycle.draw_world_tint(screen)

            # UI panel (placeholder values)
            draw_ui_panel(screen, font_ui, score, wave, player_hp, player_sta, castle_hp, paused, game_over)

            pygame.display.update()

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        pygame.quit()

if __name__ == "__main__":
    main()
