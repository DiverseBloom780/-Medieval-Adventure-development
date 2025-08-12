import warnings
warnings.filterwarnings("ignore", category=UserWarning)
import pygame
import math
import sys
import random

# Initialize Pygame
try:
    pygame.init()
except Exception as e:
    print(f"Failed to initialize Pygame: {e}")
    sys.exit(1)

# Constants
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

# Colors
SKY_BLUE = (173, 216, 230)
GREEN = (34, 139, 34)
BROWN = (165, 42, 42)
STONE_GRAY = (192, 192, 192)
TREE_GREEN = (0, 128, 0)
WATER_BLUE = (0, 191, 255)
SKIN_COLOR = (255, 218, 185)
HAIR_COLOR = (139, 69, 19)
BOW_COLOR = (165, 42, 42)
STRING_COLOR = (0, 0, 0)
ARROW_COLOR = (128, 0, 0)

def draw_tree(screen, x, y):
    pygame.draw.line(screen, BROWN, (x, y), (x, y - 50), 5)
    pygame.draw.circle(screen, TREE_GREEN, (x, y - 70), 30)

def draw_castle(screen, x, y):
    pygame.draw.rect(screen, STONE_GRAY, (x, y, 100, 100))
    pygame.draw.rect(screen, BROWN, (x + 40, y + 80, 20, 20))

def draw_archer(screen, x, y):
    # The head
    pygame.draw.circle(screen, SKIN_COLOR, (x, y), 10)
    pygame.draw.circle(screen, HAIR_COLOR, (x, y - 10), 5)

    # The body
    pygame.draw.line(screen, BROWN, (x, y + 10), (x, y + 30), 5)

    # The arms
    pygame.draw.line(screen, BROWN, (x, y + 15), (x - 10, y + 25), 5)
    pygame.draw.line(screen, BROWN, (x, y + 15), (x + 10, y + 25), 5)

    # The legs
    pygame.draw.line(screen, BROWN, (x, y + 30), (x - 5, y + 50), 5)
    pygame.draw.line(screen, BROWN, (x, y + 30), (x + 5, y + 50), 5)

    # The bow
    pygame.draw.line(screen, BOW_COLOR, (x + 10, y + 25), (x + 20, y + 15), 5)
    pygame.draw.line(screen, BOW_COLOR, (x + 20, y + 15), (x + 10, y + 5), 5)
    pygame.draw.line(screen, STRING_COLOR, (x + 20, y + 15), (x + 10, y + 15), 2)

class Arrow:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = 10

    def draw(self, screen):
        # The shaft
        pygame.draw.line(screen, ARROW_COLOR, (self.x, self.y), (self.x + 15, self.y), 3)
        # The fletchings
        pygame.draw.line(screen, (255, 255, 255), (self.x, self.y - 2), (self.x + 5, self.y - 2), 1)
        pygame.draw.line(screen, (255, 255, 255), (self.x, self.y + 2), (self.x + 5, self.y + 2), 1)
        # The arrowhead
        pygame.draw.polygon(screen, ARROW_COLOR, [(self.x + 15, self.y - 2), (self.x + 20, self.y), (self.x + 15, self.y + 2)])

    def update(self):
        self.x += self.speed

class EnemySwordsman:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = 2

    def draw(self, screen):
        # The head
        pygame.draw.circle(screen, SKIN_COLOR, (self.x, self.y), 10)
        # The body
        pygame.draw.line(screen, BROWN, (self.x, self.y + 10), (self.x, self.y + 30), 5)
        # The arms
        pygame.draw.line(screen, BROWN, (self.x, self.y + 15), (self.x - 10, self.y + 25), 5)
        pygame.draw.line(screen, BROWN, (self.x, self.y + 15), (self.x + 10, self.y + 25), 5)
        # The legs
        pygame.draw.line(screen, BROWN, (self.x, self.y + 30), (self.x - 5, self.y + 50), 5)
        pygame.draw.line(screen, BROWN, (self.x, self.y + 30), (self.x + 5, self.y + 50), 5)
        # The sword
        pygame.draw.line(screen, (128, 128, 128), (self.x + 10, self.y + 25), (self.x + 20, self.y + 25), 3)

    def update(self):
        self.x -= self.speed

class EnemyArcher:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = 2

    def draw(self, screen):
        # The head
        pygame.draw.circle(screen, SKIN_COLOR, (self.x, self.y), 10)
        # The body
        pygame.draw.line(screen, BROWN, (self.x, self.y + 10), (self.x, self.y + 30), 5)
        # The arms
        pygame.draw.line(screen, BROWN, (self.x, self.y + 15), (self.x - 10, self.y + 25), 5)
        pygame.draw.line(screen, BROWN, (self.x, self.y + 15), (self.x + 10, self.y + 25), 5)
        # The legs
        pygame.draw.line(screen, BROWN, (self.x, self.y + 30), (self.x - 5, self.y + 50), 5)
        pygame.draw.line(screen, BROWN, (self.x, self.y + 30), (self.x + 5, self.y + 50), 5)
        # The bow
        pygame.draw.line(screen, BOW_COLOR, (self.x + 10, self.y + 25), (self.x + 20, self.y + 15), 5)
        pygame.draw.line(screen, BOW_COLOR, (self.x + 20, self.y + 15), (self.x + 10, self.y + 5), 5)
        pygame.draw.line(screen, STRING_COLOR, (self.x + 20, self.y + 15), (self.x + 10, self.y + 15), 2)

    def update(self):
        self.x -= self.speed

class Ballista:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.arrow_speed = 10
        self.arrows = []

    def draw(self, screen):
        pygame.draw.rect(screen, STONE_GRAY, (self.x, self.y, 20, 20))
        pygame.draw.line(screen, BROWN, (self.x + 10, self.y + 20), (self.x + 10, self.y + 40), 5)

    def update(self):
        for arrow in self.arrows:
            arrow.update()
            if arrow.x > SCREEN_WIDTH:
                self.arrows.remove(arrow)

    def fire(self):
        self.arrows.append(Arrow(self.x + 10, self.y + 30))

class EnemyArrow:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = 10

    def draw(self, screen):
        # The shaft
        pygame.draw.line(screen, ARROW_COLOR, (self.x, self.y), (self.x - 15, self.y), 3)
        # The fletchings
        pygame.draw.line(screen, (255, 255, 255), (self.x, self.y - 2), (self.x - 5, self.y - 2), 1)
        pygame.draw.line(screen, (255, 255, 255), (self.x, self.y + 2), (self.x - 5, self.y + 2), 1)
        # The arrowhead
        pygame.draw.polygon(screen, ARROW_COLOR, [(self.x - 15, self.y - 2), (self.x - 20, self.y), (self.x - 15, self.y + 2)])

    def update(self):
        self.x -= self.speed

def main():
    try:
        # Set up display
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Medieval Adventure")

        # Archer position
        archer_x = 100
        archer_y = int(SCREEN_HEIGHT * 0.6) - 50

        # Arrows
        arrows = []

        # Enemy swordsmen
        enemy_swordsmen = [EnemySwordsman(800, int(SCREEN_HEIGHT * 0.6) - 50)]

        # Enemy archers
        enemy_archers = [EnemyArcher(900, int(SCREEN_HEIGHT * 0.6) - 50)]
        enemy_arrows = []

        # Ballista
        ballista = Ballista(450, 300)

        # Game loop
        clock = pygame.time.Clock()
        running = True
        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        arrows.append(Arrow(archer_x + 20, archer_y + 15))
                    if event.key == pygame.K_f:
                        ballista.fire()

            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                archer_x -= 5
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                archer_x += 5
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                archer_y -= 5
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                archer_y += 5

            # Ensure archer stays within screen bounds
            archer_x = max(0, min(archer_x, SCREEN_WIDTH))
            archer_y = max(0, min(archer_y, SCREEN_HEIGHT))

            # Update arrows
            for arrow in arrows:
                arrow.update()
                if arrow.x > SCREEN_WIDTH:
                    arrows.remove(arrow)

            # Update enemies
            for enemy in enemy_swordsmen:
                enemy.update()
                if enemy.x < 0:
                    enemy_swordsmen.remove(enemy)
            for enemy in enemy_archers:
                enemy.update()
                if enemy.x < 0:
                    enemy_archers.remove(enemy)
                if random.randint(0, 100) < 5:
                    enemy_arrows.append(EnemyArrow(enemy.x, enemy.y + 15))
            for arrow in enemy_arrows:
                arrow.update()
                if arrow.x < 0:
                    enemy_arrows.remove(arrow)

            # Update ballista
            ballista.update()

            # Draw the game
            screen.fill(SKY_BLUE)
            ground_y = int(SCREEN_HEIGHT * 0.6)
            pygame.draw.rect(screen, GREEN, (0, ground_y, SCREEN_WIDTH, int(SCREEN_HEIGHT * 0.4)))
            draw_castle(screen, 400, ground_y - 100)
            ballista.draw(screen)
            draw_tree(screen, 600, ground_y + 50)
            draw_tree(screen, 800, ground_y + 50)
            draw_tree(screen, 1000, ground_y + 50)
            draw_archer(screen, archer_x, archer_y)
            for arrow in arrows:
                arrow.draw(screen)
            for enemy in enemy_swordsmen:
                enemy.draw(screen)
            for enemy in enemy_archers:
                enemy.draw(screen)
            for arrow in enemy_arrows:
                arrow.draw(screen)
            for arrow in ballista.arrows:
                arrow.draw(screen)
            pygame.display.update()

            # Update the game clock
            clock.tick(60)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        pygame.quit()

if __name__ == "__main__":
    main()
