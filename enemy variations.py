import pygame
import random
import math
import sys
from enum import Enum

# ---------- Safe init ----------
try:
    pygame.init()
except Exception as e:
    print(f"Failed to initialize Pygame: {e}")
    sys.exit(1)

# ---------- Constants ----------
SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 720
FPS = 60
GROUND_Y = int(SCREEN_HEIGHT * 0.68)

# Colors
SKY_BLUE = (173, 216, 230)
GRASS_GREEN = (34, 139, 34)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# Gameplay tuning
PLAYER_SPEED = 260
PLAYER_JUMP_VEL = -520
GRAVITY = 1400
PLAYER_MAX_HP = 100
PLAYER_IFRAMES = 1.0  # seconds of invulnerability after being hit
PLAYER_SHOT_COOLDOWN = 0.25
PLAYER_PROJECTILE_SPEED = 520
PLAYER_PROJECTILE_LIFETIME = 2.0

SPAWN_BASE_INTERVAL = 1.1  # seconds; decreases over time
SPAWN_MIN_INTERVAL = 0.35
DIFFICULTY_RAMP_EVERY = 15.0  # seconds
HP_RAMP_PER_STEP = 0.08  # +8% HP per step

# Enemy archetypes
ENEMY_STATS = {
    "knight": {
        "hp": 150,
        "speed": 90,
        "damage": 20,
        "size": (50, 60),
        "color": (200, 60, 60),
        "score": 30,
        "ranged": False,
    },
    "archer": {
        "hp": 80,
        "speed": 110,
        "damage": 15,
        "size": (36, 46),
        "color": (60, 200, 90),
        "score": 20,
        "ranged": True,
        "shoot_cooldown": 1.8,
        "proj_speed": 280,
        "proj_radius": 6,
    },
    "mage": {
        "hp": 100,
        "speed": 120,
        "damage": 25,
        "size": (42, 52),
        "color": (80, 80, 230),
        "score": 40,
        "ranged": True,
        "shoot_cooldown": 1.4,
        "proj_speed": 240,
        "proj_radius": 8,
    },
}

# ---------- Helpers ----------
def clamp(value, lo, hi):
    return lo if value < lo else hi if value > hi else value

def draw_text(surface, text, font, color, pos, align="topleft"):
    img = font.render(text, True, color)
    rect = img.get_rect()
    setattr(rect, align, pos)
    surface.blit(img, rect)
    return rect

# ---------- Game State Enum ----------
class GamePhase(Enum):
    TITLE = 0
    RUNNING = 1
    PAUSED = 2
    GAME_OVER = 3

# ---------- Sprites ----------
class Projectile(pygame.sprite.Sprite):
    def __init__(self, pos, vel, radius, color, lifetime, owner_tag):
        super().__init__()
        self.pos = pygame.math.Vector2(pos)
        self.vel = pygame.math.Vector2(vel)
        self.radius = radius
        self.color = color
        self.owner_tag = owner_tag  # "player" or "enemy"
        self.lifetime = lifetime
        self.age = 0.0
        d = radius * 2
        self.image = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (radius, radius), radius)
        self.rect = self.image.get_rect(center=self.pos)

    def update(self, dt):
        self.age += dt
        if self.age > self.lifetime:
            self.kill()
            return
        self.pos += self.vel * dt
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        if self.rect.right < 0 or self.rect.left > SCREEN_WIDTH or self.rect.bottom < 0 or self.rect.top > SCREEN_HEIGHT:
            self.kill()

class Enemy(pygame.sprite.Sprite):
    def __init__(self, enemy_type, hp_multiplier=1.0):
        super().__init__()
        self.enemy_type = enemy_type
        stats = ENEMY_STATS[enemy_type]
        w, h = stats["size"]
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        self.color = stats["color"]
        pygame.draw.rect(self.image, self.color, (0, 0, w, h), border_radius=6)
        self.rect = self.image.get_rect()
        self.rect.bottomleft = (SCREEN_WIDTH + random.randint(0, 120), GROUND_Y)
        self.pos = pygame.math.Vector2(self.rect.topleft)
        self.speed = stats["speed"]
        self.max_hp = int(stats["hp"] * hp_multiplier)
        self.hp = self.max_hp
        self.damage = stats["damage"]
        self.score_value = stats["score"]
        self.ranged = stats.get("ranged", False)
        self.shoot_cd_max = stats.get("shoot_cooldown", 1.0)
        self.shoot_cd = random.uniform(0.2, self.shoot_cd_max)
        self.proj_speed = stats.get("proj_speed", 0)
        self.proj_radius = stats.get("proj_radius", 6)

    def update(self, dt, projectiles_group):
        # Movement toward the player (leftwards)
        self.pos.x -= self.speed * dt
        self.rect.x = int(self.pos.x)
        # Simple ranged AI: shoot periodically
        if self.ranged:
            self.shoot_cd -= dt
            if self.shoot_cd <= 0:
                self.shoot_cd = self.shoot_cd_max
                # Shoot leftwards
                vel = (-self.proj_speed, 0)
                proj = Projectile(
                    pos=(self.rect.centerx - 10, self.rect.centery - 10),
                    vel=vel,
                    radius=self.proj_radius,
                    color=self.color,
                    lifetime=3.0,
                    owner_tag="enemy",
                )
                projectiles_group.add(proj)

        # Remove if fully off-screen
        if self.rect.right < -40:
            self.kill()

    def take_damage(self, amount):
        self.hp -= amount
        return self.hp <= 0

    def draw_hp_bar(self, surface):
        # Tiny HP bar above enemy
        bar_w = self.rect.w
        ratio = clamp(self.hp / self.max_hp, 0, 1)
        bg_rect = pygame.Rect(self.rect.left, self.rect.top - 8, bar_w, 4)
        fg_rect = pygame.Rect(self.rect.left, self.rect.top - 8, int(bar_w * ratio), 4)
        pygame.draw.rect(surface, (40, 40, 40), bg_rect)
        pygame.draw.rect(surface, (20, 220, 20), fg_rect)

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.w, self.h = 42, 58
        self.image = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        pygame.draw.rect(self.image, (240, 220, 90), (0, 0, self.w, self.h), border_radius=8)
        # A simple "helmet"
        pygame.draw.rect(self.image, (130, 110, 40), (6, 4, self.w - 12, 12), border_radius=4)
        self.rect = self.image.get_rect()
        self.rect.bottomleft = (40, GROUND_Y)
        self.pos = pygame.math.Vector2(self.rect.topleft)
        self.vel = pygame.math.Vector2(0, 0)
        self.on_ground = True
        self.hp = PLAYER_MAX_HP
        self.max_hp = PLAYER_MAX_HP
        self.iframes = 0.0
        self.shoot_cd = 0.0

    def handle_input(self, keys):
        ax = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            ax -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            ax += 1
        self.vel.x = ax * PLAYER_SPEED

    def jump(self):
        if self.on_ground:
            self.vel.y = PLAYER_JUMP_VEL
            self.on_ground = False

    def try_shoot(self, projectiles_group, aim_pos=None):
        if self.shoot_cd > 0:
            return
        self.shoot_cd = PLAYER_SHOT_COOLDOWN
        # Aim: towards mouse if provided, else straight right
        if aim_pos is None:
            vel = pygame.math.Vector2(PLAYER_PROJECTILE_SPEED, 0)
        else:
            dir_vec = pygame.math.Vector2(aim_pos) - pygame.math.Vector2(self.rect.center)
            if dir_vec.length_squared() < 1e-5:
                vel = pygame.math.Vector2(PLAYER_PROJECTILE_SPEED, 0)
            else:
                vel = dir_vec.normalize() * PLAYER_PROJECTILE_SPEED

        proj = Projectile(
            pos=(self.rect.centerx + 10, self.rect.centery - 8),
            vel=vel,
            radius=5,
            color=(30, 30, 30),
            lifetime=PLAYER_PROJECTILE_LIFETIME,
            owner_tag="player",
        )
        projectiles_group.add(proj)

    def apply_gravity(self, dt):
        self.vel.y += GRAVITY * dt

    def take_damage(self, amount):
        if self.iframes > 0:
            return False
        self.hp -= amount
        self.iframes = PLAYER_IFRAMES
        return self.hp <= 0

    def update(self, dt):
        self.shoot_cd = max(0.0, self.shoot_cd - dt)
        self.iframes = max(0.0, self.iframes - dt)

        # Horizontal move
        self.pos.x += self.vel.x * dt
        # Keep player within left 60% of screen
        left_bound = 0
        right_bound = int(SCREEN_WIDTH * 0.6) - self.rect.w
        self.pos.x = clamp(self.pos.x, left_bound, right_bound)

        # Vertical move + ground collision
        self.apply_gravity(dt)
        self.pos.y += self.vel.y * dt
        self.rect.topleft = (int(self.pos.x), int(self.pos.y))

        if self.rect.bottom >= GROUND_Y:
            self.rect.bottom = GROUND_Y
            self.pos.y = self.rect.top
            self.vel.y = 0
            self.on_ground = True

class Cloud(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        w = random.randint(90, 180)
        h = random.randint(40, 70)
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        # Stylized cloud (3 ellipses)
        for i in range(3):
            rw = int(w * random.uniform(0.6, 1.0))
            rh = int(h * random.uniform(0.6, 1.0))
            rx = random.randint(0, w - rw)
            ry = random.randint(0, h - rh)
            pygame.draw.ellipse(self.image, (250, 250, 255, 180), (rx, ry, rw, rh))
        self.rect = self.image.get_rect()
        self.rect.x = SCREEN_WIDTH + random.randint(0, 200)
        self.rect.y = random.randint(40, int(GROUND_Y * 0.5))
        self.speed = random.uniform(12, 35)

    def update(self, dt):
        self.rect.x -= int(self.speed * dt)
        if self.rect.right < -20:
            self.kill()

# ---------- Game ----------
class Game:
    def __init__(self):
        pygame.display.set_caption("Medieval Adventure")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()

        # Fonts
        self.font_lg = pygame.font.SysFont("consolas", 64)
        self.font_md = pygame.font.SysFont("consolas", 32)
        self.font_sm = pygame.font.SysFont("consolas", 20)

        # Groups
        self.all_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.clouds = pygame.sprite.Group()

        # Core
        self.player = Player()
        self.all_sprites.add(self.player)

        # Spawning / difficulty
        self.spawn_timer = 0.0
        self.spawn_interval = SPAWN_BASE_INTERVAL
        self.elapsed = 0.0
        self.hp_multiplier = 1.0

        # Score / state
        self.score = 0
        self.phase = GamePhase.TITLE
        self.shake_time = 0.0
        self.shake_mag = 0

        # Cloud bootstrap
        for _ in range(6):
            self.clouds.add(Cloud())

    # ----- UI Screens -----
    def title_screen(self):
        self.screen.fill(SKY_BLUE)
        self.draw_world_background()
        draw_text(self.screen, "Medieval Adventure", self.font_lg, BLACK, (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60), "center")
        draw_text(self.screen, "A/D or ←/→ to move · Space to jump · J / Click to shoot", self.font_md, BLACK, (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 12), "center")
        draw_text(self.screen, "Press Enter to Start", self.font_md, BLACK, (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60), "center")
        pygame.display.flip()

    def game_over_screen(self):
        self.screen.fill(SKY_BLUE)
        self.draw_world_background()
        draw_text(self.screen, "Game Over", self.font_lg, BLACK, (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60), "center")
        draw_text(self.screen, f"Score: {self.score}", self.font_md, BLACK, (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), "center")
        draw_text(self.screen, "Press R to Restart or Esc to Quit", self.font_md, BLACK, (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60), "center")
        pygame.display.flip()

    # ----- Spawning & Difficulty -----
    def maybe_spawn_enemy(self, dt):
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_timer = self.spawn_interval
            etype = random.choices(
                population=["knight", "archer", "mage"],
                weights=[0.45, 0.35, 0.20],
                k=1,
            )[0]
            enemy = Enemy(etype, hp_multiplier=self.hp_multiplier)
            self.enemies.add(enemy)
            self.all_sprites.add(enemy)

    def ramp_difficulty(self, dt):
        self.elapsed += dt
        steps = int(self.elapsed // DIFFICULTY_RAMP_EVERY)
        # Spawn rate tightens and HP scales
        self.spawn_interval = clamp(SPAWN_BASE_INTERVAL * (0.92 ** steps), SPAWN_MIN_INTERVAL, SPAWN_BASE_INTERVAL)
        self.hp_multiplier = 1.0 + HP_RAMP_PER_STEP * steps

    # ----- Events -----
    def handle_events(self):
        mouse_pos = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            if self.phase == GamePhase.TITLE:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    self.reset_run()
                    self.phase = GamePhase.RUNNING
            elif self.phase == GamePhase.RUNNING:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_w, pygame.K_SPACE, pygame.K_UP):
                        self.player.jump()
                    elif event.key == pygame.K_p:
                        self.phase = GamePhase.PAUSED
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit(0)
                    elif event.key == pygame.K_j:
                        self.player.try_shoot(self.projectiles)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_pos = pygame.mouse.get_pos()
                    self.player.try_shoot(self.projectiles, aim_pos=mouse_pos)
            elif self.phase == GamePhase.PAUSED:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:
                        self.phase = GamePhase.RUNNING
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit(0)
            elif self.phase == GamePhase.GAME_OVER:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.reset_run()
                        self.phase = GamePhase.RUNNING
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit(0)

        if self.phase == GamePhase.RUNNING and mouse_pos is None and pygame.mouse.get_pressed()[0]:
            # Allow holding mouse to autofire respecting cooldown
            self.player.try_shoot(self.projectiles, aim_pos=pygame.mouse.get_pos())

    # ----- Update & Draw -----
    def update(self, dt):
        if self.phase != GamePhase.RUNNING:
            return

        keys = pygame.key.get_pressed()
        self.player.handle_input(keys)

        # Clamp dt a bit to avoid physics explosions after window stalls
        dt = min(dt, 1 / 20)

        self.ramp_difficulty(dt)
        self.maybe_spawn_enemy(dt)

        # Clouds/background
        if random.random() < 0.01 and len(self.clouds) < 9:
            self.clouds.add(Cloud())
        self.clouds.update(dt)

        # Sprites
        self.player.update(dt)
        for enemy in list(self.enemies):
            enemy.update(dt, self.projectiles)
        self.projectiles.update(dt)

        # Collisions: player projectiles -> enemies
        for proj in [p for p in self.projectiles if p.owner_tag == "player"]:
            hits = [e for e in self.enemies if e.rect.colliderect(proj.rect)]
            if hits:
                proj.kill()
                for e in hits:
                    died = e.take_damage(40)
                    self.shake(0.12, 6)
                    if died:
                        self.score += e.score_value
                        e.kill()

        # Collisions: enemy projectiles -> player
        for proj in [p for p in self.projectiles if p.owner_tag == "enemy"]:
            if self.player.rect.colliderect(proj.rect):
                proj.kill()
                self.shake(0.18, 10)
                if self.player.take_damage(ENEMY_STATS["archer"]["damage"] if proj.radius <= 6 else ENEMY_STATS["mage"]["damage"]):
                    self.phase = GamePhase.GAME_OVER

        # Collisions: enemy body -> player
        touchers = [e for e in self.enemies if e.rect.colliderect(self.player.rect)]
        for e in touchers:
            self.shake(0.18, 10)
            if self.player.take_damage(e.damage):
                self.phase = GamePhase.GAME_OVER

        # Screen shake decay
        if self.shake_time > 0:
            self.shake_time -= dt

    def draw_world_background(self):
        # Sky
        self.screen.fill(SKY_BLUE)

        # Parallax hills
        hill_color_far = (120, 200, 160)
        hill_color_near = (80, 170, 130)
        # Far hill
        pygame.draw.ellipse(self.screen, hill_color_far, (-200, GROUND_Y - 200, 800, 300))
        pygame.draw.ellipse(self.screen, hill_color_far, (400, GROUND_Y - 220, 900, 340))
        # Near hill
        pygame.draw.ellipse(self.screen, hill_color_near, (-160, GROUND_Y - 140, 700, 240))
        pygame.draw.ellipse(self.screen, hill_color_near, (520, GROUND_Y - 160, 820, 280))

        # Clouds
        self.clouds.draw(self.screen)

        # Ground
        pygame.draw.rect(self.screen, GRASS_GREEN, (0, GROUND_Y, SCREEN_WIDTH, SCREEN_HEIGHT - GROUND_Y))

    def draw(self):
        if self.phase == GamePhase.TITLE:
            self.title_screen()
            return
        if self.phase == GamePhase.GAME_OVER:
            self.game_over_screen()
            return

        # Camera shake offset
        ox = int(random.uniform(-self.shake_mag, self.shake_mag)) if self.shake_time > 0 else 0
        oy = int(random.uniform(-self.shake_mag, self.shake_mag)) if self.shake_time > 0 else 0

        # World
        self.draw_world_background()

        # Sprites (offset by shake)
        # Draw enemies + their HP bars
        for sprite in self.all_sprites:
            if sprite == self.player:
                continue
            self.screen.blit(sprite.image, (sprite.rect.x + ox, sprite.rect.y + oy))
            if isinstance(sprite, Enemy):
                sprite.draw_hp_bar(self.screen)
        # Draw player last (also offset)
        # Flicker effect during i-frames
        if self.player.iframes > 0 and int(pygame.time.get_ticks() * 0.02) % 2 == 0:
            pass  # skip draw half the time
        else:
            self.screen.blit(self.player.image, (self.player.rect.x + ox, self.player.rect.y + oy))

        # Projectiles drawn via sprite group
        for p in self.projectiles:
            self.screen.blit(p.image, (p.rect.x + ox, p.rect.y + oy))

        # HUD
        self.draw_hud()

        if self.phase == GamePhase.PAUSED:
            s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            s.fill((0, 0, 0, 120))
            self.screen.blit(s, (0, 0))
            draw_text(self.screen, "Paused", self.font_lg, WHITE, (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30), "center")
            draw_text(self.screen, "Press P to resume", self.font_md, WHITE, (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30), "center")

        pygame.display.flip()

    def draw_hud(self):
        # Health bar
        pad = 12
        bar_w, bar_h = 260, 20
        x, y = pad, pad
        pygame.draw.rect(self.screen, (40, 40, 40), (x - 2, y - 2, bar_w + 4, bar_h + 4))
        ratio = clamp(self.player.hp / self.player.max_hp, 0, 1)
        pygame.draw.rect(self.screen, (220, 40, 40), (x, y, int(bar_w * ratio), bar_h))
        draw_text(self.screen, f"HP: {self.player.hp}/{self.player.max_hp}", self.font_sm, WHITE, (x + 6, y + 2))

        # Score + difficulty info
        draw_text(self.screen, f"Score: {self.score}", self.font_md, BLACK, (SCREEN_WIDTH - 14, 14), "topright")
        draw_text(
            self.screen,
            f"Spawn {self.spawn_interval:.2f}s · HPx{self.hp_multiplier:.2f}",
            self.font_sm,
            BLACK,
            (SCREEN_WIDTH - 14, 50),
            "topright",
        )

        # Tiny control hint
        draw_text(self.screen, "P = Pause · R = Restart · Esc = Quit", self.font_sm, BLACK, (SCREEN_WIDTH - 14, 74), "topright")

    # ----- Effects -----
    def shake(self, time_s, magnitude):
        self.shake_time = max(self.shake_time, time_s)
        self.shake_mag = max(self.shake_mag, magnitude)

    # ----- Run Control -----
    def reset_run(self):
        self.all_sprites.empty()
        self.enemies.empty()
        self.projectiles.empty()
        self.clouds.empty()

        self.player = Player()
        self.all_sprites.add(self.player)

        for _ in range(6):
            self.clouds.add(Cloud())

        self.spawn_timer = 0.5
        self.spawn_interval = SPAWN_BASE_INTERVAL
        self.elapsed = 0.0
        self.hp_multiplier = 1.0
        self.score = 0
        self.shake_time = 0.0
        self.shake_mag = 0

    def run(self):
        # Initial title screen
        self.phase = GamePhase.TITLE

        while True:
            dt_ms = self.clock.tick(FPS)
            dt = dt_ms / 1000.0

            self.handle_events()

            if self.phase == GamePhase.RUNNING:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_r]:
                    self.reset_run()
                self.update(dt)

            self.draw()

# ---------- Entrypoint ----------
if __name__ == "__main__":
    Game().run()
