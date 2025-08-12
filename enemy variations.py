import pygame
import random
import sys

# Initialize Pygame
try:
    pygame.init()
except Exception as e:
    print(f"Failed to initialize Pygame: {e}")
    sys.exit(1)

# Constants
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
GROUND_Y = int(SCREEN_HEIGHT * 0.68)

# Colors
SKY_BLUE = (173, 216, 230)
GREEN = (34, 139, 34)

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.enemies = []

    def title_screen(self):
        title_font = pygame.font.SysFont("consolas", 64)
        title_text = title_font.render("Medieval Adventure", True, (0, 0, 0))
        start_text = pygame.font.SysFont("consolas", 32).render("Press Enter to Start", True, (0, 0, 0))

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    return

            self.screen.fill(SKY_BLUE)
            self.screen.blit(title_text, (SCREEN_WIDTH // 2 - title_text.get_width() // 2, SCREEN_HEIGHT // 2 - title_text.get_height() // 2))
            self.screen.blit(start_text, (SCREEN_WIDTH // 2 - start_text.get_width() // 2, SCREEN_HEIGHT // 2 + title_text.get_height() // 2 + 20))
            pygame.display.flip()
            self.clock.tick(FPS)

    def spawn_enemy(self):
        enemy_type = random.choice(["knight", "archer", "mage"])
        enemy = Enemy(SCREEN_WIDTH, GROUND_Y - 55, enemy_type)
        self.enemies.append(enemy)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)

    def update(self, dt):
        for enemy in self.enemies:
            enemy.update(dt)
            if enemy.x < 0:
                self.enemies.remove(enemy)

        if random.random() < 0.05:
            self.spawn_enemy()

    def draw(self):
        self.screen.fill(SKY_BLUE)
        pygame.draw.rect(self.screen, GREEN, (0, GROUND_Y, SCREEN_WIDTH, SCREEN_HEIGHT - GROUND_Y))

        for enemy in self.enemies:
            enemy.draw(self.screen)

        pygame.display.flip()

    def run(self):
        self.title_screen()
        while True:
            dt = self.clock.tick(FPS)
            self.handle_events()
            self.update(dt / 1000)
            self.draw()

class Enemy:
    def __init__(self, x, y, enemy_type):
        self.x = x
        self.y = y
        self.enemy_type = enemy_type
        self.hp = self.get_hp_by_type()
        self.speed = self.get_speed_by_type()
        self.damage = self.get_damage_by_type()

    def get_hp_by_type(self):
        if self.enemy_type == "knight":
            return 150
        elif self.enemy_type == "archer":
            return 80
        elif self.enemy_type == "mage":
            return 100

    def get_speed_by_type(self):
        if self.enemy_type == "knight":
            return 80
        elif self.enemy_type == "archer":
            return 100
        elif self.enemy_type == "mage":
            return 120

    def get_damage_by_type(self):
        if self.enemy_type == "knight":
            return 20
        elif self.enemy_type == "archer":
            return 15
        elif self.enemy_type == "mage":
            return 25

    def update(self, dt):
        self.x -= self.speed * dt

    def draw(self, screen):
        if self.enemy_type == "knight":
            pygame.draw.rect(screen, (255, 0, 0), (int(self.x), int(self.y), 50, 50))
        elif self.enemy_type == "archer":
            pygame.draw.rect(screen, (0, 255, 0), (int(self.x), int(self.y), 30, 30))
        elif self.enemy_type == "mage":
            pygame.draw.rect(screen, (0, 0, 255), (int(self.x), int(self.y), 40, 40))

if __name__ == "__main__":
    game = Game()
    game.run()
