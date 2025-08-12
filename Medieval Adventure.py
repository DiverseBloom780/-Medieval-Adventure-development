# -*- coding: utf-8 -*-
"""
Medieval Adventure (Enhanced)
-----------------------------
A lightweight Pygame demo with:
- Title screen, pause, game-over and restart
- Player archer (mouse-aimed shots, sprint & stamina, HP)
- Ballista turret (heavy bolt with cooldown)
- Swordsmen, Archers and Brutes (enemy variants with simple AI)
- Wave system with accelerating difficulty
- Castle HP and loss condition
- Power-ups (heart, stamina, coin) dropped by enemies
- Score, HUD, and helpful keybinds
- Particles, floating damage numbers, screen shake
- Frame-rate independent movement (dt)
"""

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple
import random
import math
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

SCREEN_WIDTH  = 1920
SCREEN_HEIGHT = 1080
FPS = 60

GROUND_RATIO = 0.65
GROUND_Y = int(SCREEN_HEIGHT * GROUND_RATIO)

# Colors
SKY_BLUE    = (173, 216, 230)
GREEN       = ( 34, 139,  34)
BROWN       = (165,  42,  42)
STONE_GRAY  = (192, 192, 192)
TREE_GREEN  = (  0, 128,   0)
SKIN_COLOR  = (255, 218, 185)
HAIR_COLOR  = (139,  69,  19)
BOW_COLOR   = (165,  42,  42)
STRING_COL  = (  0,   0,   0)
ARROW_COLOR = (128,   0,   0)
RED         = (220,  40,  40)
GOLD        = (230, 200,  60)
BLACK       = (  0,   0,   0)
WHITE       = (255, 255, 255)
UI_BG       = ( 20,  22,  27)
UI_FG       = (212, 214, 218)

# Gameplay tuning
PLAYER_SPEED           = 320.0
PLAYER_SPRINT_SPEED    = 500.0
PLAYER_STAMINA_MAX     = 100.0
PLAYER_STAMINA_DRAIN   = 35.0        # per second
PLAYER_STAMINA_REGEN   = 22.0
PLAYER_MAX_HP          = 100

ARROW_SPEED            = 1000.0
ARROW_DAMAGE           = 22
ARROW_GRAVITY          = 900.0

BOLT_SPEED             = 1300.0
BOLT_DAMAGE            = 50
BOLT_COOLDOWN          = 1.1

ENEMY_HP               = 90
ENEMY_SWORD_SPEED      = 140.0
ENEMY_ARCHER_SPEED     = 110.0
ENEMY_ARCHER_RANGE     = 420.0
ENEMY_ARCHER_CADENCE   = 1.7
ENEMY_ARROW_SPEED      = 820.0
ENEMY_ARROW_GRAVITY    = 700.0
ENEMY_DPS_VS_CASTLE    = 15.0

# Brute variant
BRUTE_HP               = 200
BRUTE_SPEED            = 90.0
BRUTE_DPS_VS_CASTLE    = 28.0

CASTLE_HP_MAX          = 600

WAVE_BASE_SPAWN_RATE   = 1.0      # seconds; smaller = more frequent
WAVE_ACCELERATION      = 0.92     # multiplied each wave
WAVE_KILL_TARGET_STEP  = 12       # kills required per wave index (wave * step)

DROP_CHANCE            = 0.22     # per enemy death
SCREEN_SHAKE_TIME      = 0.22
SCREEN_SHAKE_INTENS    = 8.0

PARTICLE_COUNT_HIT     = 10
PARTICLE_LIFETIME      = 0.45


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def vec_norm_from(a: Tuple[float, float], b: Tuple[float, float]) -> pygame.math.Vector2:
    v = pygame.math.Vector2(b[0] - a[0], b[1] - a[1])
    if v.length_squared() == 0:
        return pygame.math.Vector2(1, 0)
    return v.normalize()


# ---------------------------------------------------------------------------
# Draw helpers
# ---------------------------------------------------------------------------

def draw_tree(s: pygame.Surface, x: int, y: int) -> None:
    pygame.draw.line(s, BROWN, (x, y), (x, y - 54), 6)
    pygame.draw.circle(s, TREE_GREEN, (x, y - 75), 30)
    pygame.draw.circle(s, TREE_GREEN, (x - 22, y - 66), 22)
    pygame.draw.circle(s, TREE_GREEN, (x + 22, y - 66), 22)

def draw_castle(s: pygame.Surface, rect: pygame.Rect, hp_frac: float) -> None:
    pygame.draw.rect(s, STONE_GRAY, rect, border_radius=2)
    # merlons
    w = 16
    for i in range(rect.left, rect.right, w * 2):
        pygame.draw.rect(s, STONE_GRAY, (i, rect.top - 12, w, 12))
    # gate
    gate = pygame.Rect(rect.centerx - 22, rect.bottom - 42, 44, 42)
    pygame.draw.rect(s, BROWN, gate, border_radius=2)
    # HP bar
    bw = rect.width; bh = 12
    bx, by = rect.left, rect.top - 22
    pygame.draw.rect(s, BLACK, (bx, by, bw, bh), border_radius=3)
    pygame.draw.rect(s, (60, 220, 90), (bx, by, int(bw * hp_frac), bh), border_radius=3)

def draw_archer(s: pygame.Surface, x: int, y: int, aim_dir: pygame.math.Vector2) -> None:
    # head & hair
    pygame.draw.circle(s, SKIN_COLOR, (x, y), 10)
    pygame.draw.circle(s, HAIR_COLOR, (x, y - 10), 5)
    # body
    pygame.draw.line(s, BROWN, (x, y + 10), (x, y + 30), 5)
    # arms & legs
    pygame.draw.line(s, BROWN, (x, y + 15), (x - 10, y + 25), 5)
    pygame.draw.line(s, BROWN, (x, y + 15), (x + 10, y + 25), 5)
    pygame.draw.line(s, BROWN, (x, y + 30), (x - 5, y + 52), 5)
    pygame.draw.line(s, BROWN, (x, y + 30), (x + 5, y + 52), 5)
    # bow in aim direction
    hand = (x + 10, y + 15)
    tip  = (hand[0] + int(aim_dir.x * 16), hand[1] + int(aim_dir.y * 16))
    pygame.draw.line(s, BOW_COLOR, hand, tip, 4)
    pygame.draw.line(s, STRING_COL, tip, hand, 1)

def draw_ui(s: pygame.Surface, font: pygame.font.Font, score: int, wave: int,
            player_hp: int, player_sta: float, castle_hp: int,
            paused: bool, game_over: bool) -> None:
    bar = pygame.Rect(0, 0, SCREEN_WIDTH, 44)
    pygame.draw.rect(s, UI_BG, bar)

    s_surf = font.render(f"Score: {score}", True, UI_FG)
    w_surf = font.render(f"Wave: {wave}", True, UI_FG)
    s.blit(s_surf, (12, 12))
    s.blit(w_surf, (150, 12))

    # HP
    hp_frac = clamp(player_hp / PLAYER_MAX_HP, 0, 1)
    pygame.draw.rect(s, BLACK, (260, 12, 180, 18), border_radius=4)
    pygame.draw.rect(s, (220, 70, 70), (260, 12, int(180 * hp_frac), 18), border_radius=4)
    s.blit(font.render("HP", True, UI_FG), (260 + 190, 12))

    # STA
    st_frac = clamp(player_sta / PLAYER_STAMINA_MAX, 0, 1)
    pygame.draw.rect(s, BLACK, (460, 12, 180, 18), border_radius=4)
    pygame.draw.rect(s, (70, 170, 220), (460, 12, int(180 * st_frac), 18), border_radius=4)
    s.blit(font.render("STA", True, UI_FG), (460 + 190, 12))

    # Castle
    c_frac = clamp(castle_hp / CASTLE_HP_MAX, 0, 1)
    pygame.draw.rect(s, BLACK, (660, 12, 220, 18), border_radius=4)
    pygame.draw.rect(s, (60, 220, 90), (660, 12, int(220 * c_frac), 18), border_radius=4)
    s.blit(font.render("Castle", True, UI_FG), (660 + 230, 12))

    # Right status
    if paused:
        t = font.render("PAUSED (P to resume)", True, GOLD)
        s.blit(t, (SCREEN_WIDTH - t.get_width() - 16, 12))
    elif game_over:
        t = font.render("GAME OVER (R to restart)", True, RED)
        s.blit(t, (SCREEN_WIDTH - t.get_width() - 16, 12))


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
    color: Tuple[int, int, int] = ARROW_COLOR
    radius: int = 2
    gravity: float = 0.0
    alive: bool = True

    def update(self, dt: float) -> None:
        self.vy += self.gravity * dt
        self.x  += self.vx * dt
        self.y  += self.vy * dt
        # ground cull
        if self.y >= GROUND_Y - 2:
            self.alive = False

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - self.radius), int(self.y - self.radius),
                           self.radius * 2, self.radius * 2)

    def draw(self, s: pygame.Surface) -> None:
        pygame.draw.circle(s, self.color, (int(self.x), int(self.y)), self.radius)


@dataclass
class FloatingText:
    text: str
    x: float
    y: float
    color: Tuple[int, int, int]
    lifetime: float = 0.9
    age: float = 0.0
    vy: float = -70.0

    def update(self, dt: float) -> None:
        self.age += dt
        self.y += self.vy * dt

    @property
    def alive(self) -> bool:
        return self.age < self.lifetime

    def draw(self, s: pygame.Surface, font: pygame.font.Font) -> None:
        alpha = clamp(1.0 - self.age / self.lifetime, 0.0, 1.0)
        surf = font.render(self.text, True, self.color)
        if alpha < 1.0:
            surf = surf.convert_alpha()
            surf.fill((255, 255, 255, int(255 * alpha)), special_flags=pygame.BLEND_RGBA_MULT)
        s.blit(surf, (int(self.x), int(self.y)))


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
        self.vy += 900.0 * dt  # gravity

    @property
    def alive(self) -> bool:
        return self.age < self.lifetime

    def draw(self, s: pygame.Surface) -> None:
        alpha = clamp(1.0 - self.age / self.lifetime, 0.0, 1.0)
        dot = pygame.Surface((3, 3), pygame.SRCALPHA)
        dot.fill((*self.color, int(255 * alpha)))
        s.blit(dot, (int(self.x), int(self.y)))


@dataclass
class Enemy:
    x: float
    y: float
    hp: int
    speed: float
    melee_dps: float
    is_archer: bool = False
    is_brute: bool = False
    preferred_range: float = ENEMY_ARCHER_RANGE
    shoot_cooldown: float = ENEMY_ARCHER_CADENCE
    shoot_timer: float = field(default_factory=lambda: random.uniform(0.1, ENEMY_ARCHER_CADENCE))

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - 10), int(self.y), 20, 52)

    def draw(self, s: pygame.Surface) -> None:
        # body
        pygame.draw.circle(s, SKIN_COLOR, (int(self.x), int(self.y)), 10)
        pygame.draw.line(s, BROWN, (self.x, self.y + 10), (self.x, self.y + 30), 5)
        pygame.draw.line(s, BROWN, (self.x, self.y + 15), (self.x - 10, self.y + 25), 5)
        pygame.draw.line(s, BROWN, (self.x, self.y + 15), (self.x + 10, self.y + 25), 5)
        pygame.draw.line(s, BROWN, (self.x, self.y + 30), (self.x - 5, self.y + 52), 5)
        pygame.draw.line(s, BROWN, (self.x, self.y + 30), (self.x + 5, self.y + 52), 5)
        # role indicator
        if self.is_archer:
            pygame.draw.line(s, BOW_COLOR, (self.x - 10, self.y + 25), (self.x - 22, self.y + 15), 4)
            pygame.draw.line(s, BOW_COLOR, (self.x - 22, self.y + 15), (self.x - 10, self.y + 5), 4)
            pygame.draw.line(s, STRING_COL, (self.x - 22, self.y + 15), (self.x - 10, self.y + 15), 1)
        else:
            sword_col = (160, 160, 160) if not self.is_brute else (180, 120, 60)
            pygame.draw.line(s, sword_col, (self.x + 10, self.y + 25), (self.x + 24, self.y + 25), 4)
        # HP bar
        barw = 26
        frac = clamp(self.hp / (BRUTE_HP if self.is_brute else ENEMY_HP), 0, 1)
        pygame.draw.rect(s, RED, (self.x - barw/2, self.y - 12, barw, 4))
        pygame.draw.rect(s, (0, 255, 0), (self.x - barw/2, self.y - 12, int(barw * frac), 4))

    def update(self, dt: float, castle_rect: pygame.Rect,
               player_x: float, enemy_arrows: List[Projectile]) -> float:
        """Returns DPS applied to the castle this frame (for melee)."""
        if self.is_archer:
            # maintain distance, then shoot
            desired_x = castle_rect.centerx + self.preferred_range
            if self.x > desired_x:
                self.x -= self.speed * dt
            self.shoot_timer -= dt
            if self.shoot_timer <= 0.0:
                self.shoot_timer = self.shoot_cooldown
                origin = (self.x - 22, self.y + 15)
                dirv = vec_norm_from(origin, (player_x, GROUND_Y - 54))
                enemy_arrows.append(Projectile(
                    x=origin[0], y=origin[1],
                    vx=dirv.x * ENEMY_ARROW_SPEED,
                    vy=dirv.y * ENEMY_ARROW_SPEED * 0.78,
                    damage=16, gravity=ENEMY_ARROW_GRAVITY, color=(70, 0, 0)
                ))
            return 0.0
        else:
            # advance to the wall
            wall_x = castle_rect.left + 24
            if self.x > wall_x:
                self.x -= self.speed * dt
                return 0.0
            # batter the wall
            return self.melee_dps


@dataclass
class Player:
    x: float
    y: float
    hp: int = PLAYER_MAX_HP
    stamina: float = PLAYER_STAMINA_MAX
    fire_cd: float = 0.22
    fire_timer: float = 0.0
    aim_dir: pygame.math.Vector2 = field(default_factory=lambda: pygame.math.Vector2(1, 0))

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - 10), int(self.y), 20, 52)

    def update(self, dt: float, keys: pygame.key.ScancodeWrapper) -> None:
        move = pygame.math.Vector2(
            (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT]),
            (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP]),
        )
        sprint = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        speed = PLAYER_SPRINT_SPEED if sprint and self.stamina > 0 else PLAYER_SPEED

        if move.length_squared() > 0:
            move = move.normalize()
            self.x += move.x * speed * dt
            self.y += move.y * speed * dt

        self.x = clamp(self.x, 20, SCREEN_WIDTH - 20)
        self.y = clamp(self.y, GROUND_Y - 60, GROUND_Y - 50)

        # stamina
        if sprint and move.length_squared() > 0 and self.stamina > 0:
            self.stamina = clamp(self.stamina - PLAYER_STAMINA_DRAIN * dt, 0, PLAYER_STAMINA_MAX)
        else:
            self.stamina = clamp(self.stamina + PLAYER_STAMINA_REGEN * dt, 0, PLAYER_STAMINA_MAX)

        # cooldown and aim
        self.fire_timer = max(0.0, self.fire_timer - dt)
        mx, my = pygame.mouse.get_pos()
        self.aim_dir = vec_norm_from((self.x + 10, self.y + 15), (mx, my))

    def try_fire(self, projectiles: List[Projectile]) -> None:
        if self.fire_timer == 0.0:
            origin = (self.x + 10, self.y + 15)
            projectiles.append(Projectile(
                x=origin[0], y=origin[1],
                vx=self.aim_dir.x * ARROW_SPEED,
                vy=self.aim_dir.y * ARROW_SPEED,
                damage=ARROW_DAMAGE, gravity=ARROW_GRAVITY, color=ARROW_COLOR
            ))
            self.fire_timer = self.fire_cd


@dataclass
class Ballista:
    x: float
    y: float
    cooldown: float = BOLT_COOLDOWN
    timer: float = 0.0

    def update(self, dt: float) -> None:
        self.timer = max(0.0, self.timer - dt)

    def fire(self, projectiles: List[Projectile]) -> None:
        if self.timer > 0.0:
            return
        mx, my = pygame.mouse.get_pos()
        dirv = vec_norm_from((self.x, self.y), (mx, my))
        projectiles.append(Projectile(
            x=self.x, y=self.y,
            vx=dirv.x * BOLT_SPEED, vy=dirv.y * BOLT_SPEED,
            damage=BOLT_DAMAGE, gravity=ARROW_GRAVITY * 0.6, color=(80, 40, 40), radius=3
        ))
        self.timer = self.cooldown

    def draw(self, s: pygame.Surface) -> None:
        # base
        pygame.draw.rect(s, STONE_GRAY, (self.x - 46, self.y + 22, 92, 20))
        # arm
        mx, my = pygame.mouse.get_pos()
        dirv = vec_norm_from((self.x, self.y), (mx, my))
        tip = (self.x + dirv.x * 42, self.y + dirv.y * 42)
        pygame.draw.line(s, BROWN, (self.x, self.y), tip, 6)
        # cooldown ring
        if self.timer > 0:
            frac = 1.0 - clamp(self.timer / self.cooldown, 0, 1)
            pygame.draw.circle(s, (80, 80, 80), (int(self.x), int(self.y)), 16, 2)
            pygame.draw.arc(s, GOLD, (self.x - 16, self.y - 16, 32, 32),
                            -math.pi/2, -math.pi/2 + 2*math.pi*frac, 3)


@dataclass
class PowerUp:
    kind: str       # "heart", "stamina", "coin"
    x: float
    y: float
    vy: float = 0.0
    alive: bool = True

    def update(self, dt: float) -> None:
        self.vy += 1200.0 * dt
        self.y  += self.vy * dt
        if self.y >= GROUND_Y - 6:
            self.y = GROUND_Y - 6
            self.vy = 0.0

    def draw(self, s: pygame.Surface) -> None:
        col = {"heart": RED, "stamina": (60, 180, 240), "coin": GOLD}.get(self.kind, WHITE)
        pygame.draw.circle(s, col, (int(self.x), int(self.y)), 8)
        pygame.draw.circle(s, BLACK, (int(self.x), int(self.y)), 8, 1)


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------

class Game:
    def __init__(self) -> None:
        flags = pygame.SCALED | pygame.RESIZABLE
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags, vsync=1)
        pygame.display.set_caption("Medieval Adventure — Enhanced")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 22)
        self.big_font = pygame.font.SysFont("consolas", 48)

        # State machine
        self.state = "title"  # "title" | "playing" | "paused" | "game_over"
        self.fullscreen = False

        # World surfaces (for screen shake)
        self.world_surface = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)

        self.reset()

    def reset(self) -> None:
        # World
        castle_w, castle_h = 200, 140
        self.castle_rect = pygame.Rect(440, GROUND_Y - castle_h, castle_w, castle_h)
        self.castle_hp = CASTLE_HP_MAX

        # Actors
        self.player = Player(x=120, y=GROUND_Y - 56)
        self.ballista = Ballista(x=self.castle_rect.centerx, y=self.castle_rect.top + 28)

        # Collections
        self.projectiles: List[Projectile] = []
        self.enemy_projectiles: List[Projectile] = []
        self.enemies: List[Enemy] = []
        self.powerups: List[PowerUp] = []
        self.particles: List[Particle] = []
        self.floaters: List[FloatingText] = []

        # Waves & spawn
        self.wave = 1
        self.kills_this_wave = 0
        self.spawn_rate = WAVE_BASE_SPAWN_RATE
        self.spawn_timer = 0.0

        # Meta
        self.score = 0
        self.paused = False
        self.game_over = False

        # Effects
        self.shake_timer = 0.0
        self.shake_intensity = 0.0

    # ---------------- State transitions ----------------

    def start(self) -> None:
        self.state = "playing"
        self.reset()

    def toggle_pause(self) -> None:
        if self.state == "playing":
            self.state = "paused"
        elif self.state == "paused":
            self.state = "playing"

    def set_game_over(self) -> None:
        self.state = "game_over"
        self.game_over = True

    # ---------------- Spawning & Waves ----------------

    def spawn_swordsman(self) -> None:
        self.enemies.append(Enemy(
            x=SCREEN_WIDTH + 30, y=GROUND_Y - 56,
            hp=ENEMY_HP, speed=ENEMY_SWORD_SPEED, melee_dps=ENEMY_DPS_VS_CASTLE
        ))

    def spawn_archer(self) -> None:
        self.enemies.append(Enemy(
            x=SCREEN_WIDTH + 30, y=GROUND_Y - 56,
            hp=ENEMY_HP, speed=ENEMY_ARCHER_SPEED, melee_dps=0.0, is_archer=True
        ))

    def spawn_brute(self) -> None:
        self.enemies.append(Enemy(
            x=SCREEN_WIDTH + 30, y=GROUND_Y - 56,
            hp=BRUTE_HP, speed=BRUTE_SPEED, melee_dps=BRUTE_DPS_VS_CASTLE, is_brute=True
        ))

    def try_spawn_enemies(self, dt: float) -> None:
        self.spawn_timer -= dt
        if self.spawn_timer <= 0.0:
            self.spawn_timer = max(0.25, self.spawn_rate)

            # Probabilities grow slightly with wave
            p_archer = clamp(0.30 + (self.wave - 1) * 0.05, 0.30, 0.85)
            p_brute  = clamp(0.10 + (self.wave - 1) * 0.03, 0.10, 0.40)

            self.spawn_swordsman()
            if random.random() < p_archer:
                self.spawn_archer()
            if random.random() < p_brute:
                self.spawn_brute()

    def advance_wave_if_ready(self) -> None:
        if self.kills_this_wave >= self.wave * WAVE_KILL_TARGET_STEP:
            self.wave += 1
            self.kills_this_wave = 0
            self.spawn_rate *= WAVE_ACCELERATION
            # small castle heal
            self.castle_hp = min(CASTLE_HP_MAX, self.castle_hp + 60)

    # ---------------- Update & Collisions ----------------

    def update(self, dt: float) -> None:
        if self.state != "playing":
            return

        # input state
        keys = pygame.key.get_pressed()

        # actors
        self.player.update(dt, keys)
        self.ballista.update(dt)

        # spawner
        self.try_spawn_enemies(dt)

        # projectiles
        for p in self.projectiles:
            p.update(dt)
        for p in self.enemy_projectiles:
            p.update(dt)

        # enemies & castle DPS
        dps = 0.0
        for e in self.enemies:
            dps += e.update(dt, self.castle_rect, self.player.x, self.enemy_projectiles)
        if dps > 0:
            self.castle_hp -= dps * dt
            self.trigger_screen_shake(SCREEN_SHAKE_TIME, SCREEN_SHAKE_INTENS)

        # powerups
        for pu in self.powerups:
            pu.update(dt)

        # effects
        for pt in self.particles:
            pt.update(dt)
        for ft in self.floaters:
            ft.update(dt)

        # collisions
        self.handle_collisions()

        # cleanup
        self.projectiles = [p for p in self.projectiles if p.alive and -60 <= p.x <= SCREEN_WIDTH + 60]
        self.enemy_projectiles = [p for p in self.enemy_projectiles if p.alive and -60 <= p.x <= SCREEN_WIDTH + 60]
        self.enemies = [e for e in self.enemies if e.hp > 0 and e.x > -60]
        self.particles = [pt for pt in self.particles if pt.alive]
        self.floaters = [ft for ft in self.floaters if ft.alive]
        self.powerups = [pu for pu in self.powerups if pu.alive]

        # wave
        self.advance_wave_if_ready()

        # lose condition
        if self.castle_hp <= 0 and self.state == "playing":
            self.set_game_over()

        # screen shake timer
        self.shake_timer = max(0.0, self.shake_timer - dt)

    def handle_collisions(self) -> None:
        # player projectiles vs enemies
        for proj in self.projectiles:
            if not proj.alive:
                continue
            pr = proj.rect()
            for e in self.enemies:
                if pr.colliderect(e.rect()):
                    e.hp -= proj.damage
                    self.score += 5
                    proj.alive = False
                    self.spawn_hit_effect(pr.centerx, pr.centery, (240, 60, 60))
                    if e.hp <= 0:
                        self.kills_this_wave += 1
                        self.score += 20 + (10 if e.is_brute else 0)
                        self.maybe_drop_powerup(e.x, e.y)
                        self.spawn_hit_effect(e.x, e.y, (255, 210, 120), pop=True)
                    else:
                        self.floaters.append(FloatingText(str(proj.damage), e.x, e.y - 24, GOLD))
                    break

        # enemy projectiles vs player / castle
        for proj in self.enemy_projectiles:
            if not proj.alive:
                continue
            pr = proj.rect()

            # player hit (smaller box)
            if pr.colliderect(self.player.rect.inflate(-6, -10)):
                self.player.hp -= proj.damage
                self.floaters.append(FloatingText(f"-{proj.damage}", self.player.x, self.player.y - 28, RED))
                proj.alive = False
                self.spawn_hit_effect(pr.centerx, pr.centery, (60, 60, 220))
                if self.player.hp <= 0:
                    # respawn penalty
                    self.player.hp = PLAYER_MAX_HP
                    self.castle_hp -= 60

            # castle hit
            elif pr.colliderect(self.castle_rect.inflate(8, 8)):
                self.castle_hp -= proj.damage * 0.5
                proj.alive = False
                self.spawn_hit_effect(pr.centerx, pr.centery, (130, 130, 130))
                self.trigger_screen_shake(SCREEN_SHAKE_TIME * 0.6, SCREEN_SHAKE_INTENS * 0.7)

        # player vs powerups
        for pu in self.powerups:
            if pu.alive and self.player.rect.inflate(20, 12).collidepoint(pu.x, pu.y):
                pu.alive = False
                if pu.kind == "heart":
                    self.player.hp = min(PLAYER_MAX_HP, self.player.hp + 25)
                    self.floaters.append(FloatingText("+HP", self.player.x, self.player.y - 30, (60, 220, 90)))
                elif pu.kind == "stamina":
                    self.player.stamina = min(PLAYER_STAMINA_MAX, self.player.stamina + 35)
                    self.floaters.append(FloatingText("+STA", self.player.x, self.player.y - 30, (60, 170, 240)))
                elif pu.kind == "coin":
                    self.score += 30
                    self.floaters.append(FloatingText("+30", self.player.x, self.player.y - 30, GOLD))

    def spawn_hit_effect(self, x: float, y: float, color: Tuple[int, int, int], pop: bool = False) -> None:
        n = PARTICLE_COUNT_HIT + (6 if pop else 0)
        for _ in range(n):
            ang = random.uniform(0, 2*math.pi)
            spd = random.uniform(100, 320) if pop else random.uniform(90, 230)
            self.particles.append(Particle(
                x=x, y=y, vx=math.cos(ang)*spd, vy=math.sin(ang)*spd, color=color
            ))

    def maybe_drop_powerup(self, x: float, y: float) -> None:
        if random.random() < DROP_CHANCE:
            kind = random.choices(["heart", "stamina", "coin"], weights=[0.35, 0.35, 0.30])[0]
            self.powerups.append(PowerUp(kind=kind, x=x, y=y))

    def trigger_screen_shake(self, t: float, intensity: float) -> None:
        self.shake_timer = max(self.shake_timer, t)
        self.shake_intensity = max(self.shake_intensity, intensity)

    # ---------------- Rendering ----------------

    def render(self) -> None:
        screen = self.screen
        screen.fill(SKY_BLUE)

        # compute shake offset
        ox = oy = 0
        if self.shake_timer > 0:
            ox = int(random.uniform(-self.shake_intensity, self.shake_intensity))
            oy = int(random.uniform(-self.shake_intensity, self.shake_intensity))

        # draw world to an off-screen surface for a simple camera shake
        self.world_surface.fill((0, 0, 0, 0))

        # ground
        pygame.draw.rect(self.world_surface, GREEN, (0, GROUND_Y, SCREEN_WIDTH, SCREEN_HEIGHT - GROUND_Y))

        # scenery
        draw_tree(self.world_surface, 700, GROUND_Y + 48)
        draw_tree(self.world_surface, 920, GROUND_Y + 56)
        draw_tree(self.world_surface, 1160, GROUND_Y + 64)

        # castle
        draw_castle(self.world_surface, self.castle_rect, clamp(self.castle_hp / CASTLE_HP_MAX, 0, 1))

        # ballista & player
        self.ballista.draw(self.world_surface)
        draw_archer(self.world_surface, int(self.player.x), int(self.player.y), self.player.aim_dir)

        # enemies
        for e in self.enemies:
            e.draw(self.world_surface)

        # projectiles
        for p in self.projectiles:
            p.draw(self.world_surface)
        for p in self.enemy_projectiles:
            p.draw(self.world_surface)

        # powerups
        for pu in self.powerups:
            pu.draw(self.world_surface)

        # particles
        for pt in self.particles:
            pt.draw(self.world_surface)

        # blit world with shake offset
        screen.blit(self.world_surface, (ox, oy))

        # floating texts on top
        for ft in self.floaters:
            ft.draw(screen, self.font)

        # UI or title/game-over overlays
        if self.state == "title":
            self.draw_title()
        else:
            draw_ui(screen, self.font, self.score, self.wave, self.player.hp,
                    self.player.stamina, int(self.castle_hp), self.state == "paused",
                    self.state == "game_over")
            if self.state == "paused":
                self.draw_center_text("PAUSED — Press P to resume")
            elif self.state == "game_over":
                self.draw_center_text("Game Over — Press R to Restart")

        pygame.display.flip()

    def draw_title(self) -> None:
        # Title background gradient-ish
        t_surf = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        t_surf.fill((0, 0, 0, 0))
        pygame.draw.rect(t_surf, (0, 0, 0, 90), (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
        self.screen.blit(t_surf, (0, 0))

        title = self.big_font.render("Medieval Adventure", True, UI_FG)
        prompt = self.font.render("Press Enter to Start •  F11: Fullscreen  •  Esc/Q: Quit", True, UI_FG)
        help1  = self.font.render("Controls: WASD to move • LMB/SPACE to shoot • RMB/F to fire Ballista", True, UI_FG)
        help2  = self.font.render("Shift to sprint • P: Pause • Enemies drop Hearts/Stamina/Coins", True, UI_FG)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, SCREEN_HEIGHT//2 - 140))
        self.screen.blit(help1, ((SCREEN_WIDTH - help1.get_width()) // 2, SCREEN_HEIGHT//2 - 40))
        self.screen.blit(help2, ((SCREEN_WIDTH - help2.get_width()) // 2, SCREEN_HEIGHT//2 - 10))
        self.screen.blit(prompt, ((SCREEN_WIDTH - prompt.get_width()) // 2, SCREEN_HEIGHT//2 + 80))

    def draw_center_text(self, text: str) -> None:
        surf = self.big_font.render(text, True, WHITE)
        self.screen.blit(surf, ((SCREEN_WIDTH - surf.get_width()) // 2,
                                60 + (44 + 10)))  # just below the top bar

    # ---------------- Input ----------------

    def handle_event(self, ev: pygame.event.Event) -> None:
        if ev.type == pygame.QUIT:
            pygame.quit()
            sys.exit(0)

        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                pygame.quit()
                sys.exit(0)

            if self.state == "title":
                if ev.key == pygame.K_RETURN:
                    self.start()
                elif ev.key == pygame.K_F11:
                    self.toggle_fullscreen()

            elif self.state == "playing":
                if ev.key == pygame.K_p:
                    self.toggle_pause()
                elif ev.key == pygame.K_SPACE:
                    self.player.try_fire(self.projectiles)
                elif ev.key == pygame.K_f:
                    self.ballista.fire(self.projectiles)
                elif ev.key == pygame.K_F11:
                    self.toggle_fullscreen()

            elif self.state == "paused":
                if ev.key == pygame.K_p:
                    self.toggle_pause()
                elif ev.key == pygame.K_F11:
                    self.toggle_fullscreen()

            elif self.state == "game_over":
                if ev.key == pygame.K_r:
                    self.start()
                elif ev.key == pygame.K_F11:
                    self.toggle_fullscreen()

        if ev.type == pygame.MOUSEBUTTONDOWN and self.state == "playing":
            if ev.button == 1:
                self.player.try_fire(self.projectiles)
            elif ev.button == 3:
                self.ballista.fire(self.projectiles)

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.SCALED, vsync=1)
        else:
            pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED | pygame.RESIZABLE, vsync=1)
        # Recreate world surface at new size
        self.world_surface = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)

    # ---------------- Main loop ----------------

    def run(self) -> None:
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                self.handle_event(ev)

            if self.state == "playing":
                self.update(dt)

            self.render()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    try:
        Game().run()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        pygame.quit()

if __name__ == "__main__":
    main()
