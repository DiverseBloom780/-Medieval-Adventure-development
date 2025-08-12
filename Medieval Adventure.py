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
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PLAYER_SIZE = 50
HORSE_SIZE = 50
ENEMY_SIZE = 50

# Colors
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BROWN = (139, 69, 19)

class Player:
    def __init__(self):
        self.pos = [SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2]
        self.speed = 5
        self.health = 100
        self.weapon = "sword"
        self.shield = False

class Horse:
    def __init__(self):
        self.pos = [SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2]
        self.speed = 10

class Enemy:
    def __init__(self, player_pos):
        self.pos = self.generate_pos(player_pos)

    def generate_pos(self, player_pos):
        while True:
            pos = [random.randint(0, SCREEN_WIDTH - ENEMY_SIZE), random.randint(0, SCREEN_HEIGHT - ENEMY_SIZE)]
            if abs(player_pos[0] - pos[0]) > PLAYER_SIZE or abs(player_pos[1] - pos[1]) > PLAYER_SIZE:
                return pos

def main():
    try:
        # Set up display
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Medieval Adventure")

        # Game objects
        player = Player()
        horse = Horse()
        enemies = [Enemy(player.pos) for _ in range(50)]

        # Game loop
        clock = pygame.time.Clock()
        running = True
        riding_horse = False
        game_over = False

        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            keys = pygame.key.get_pressed()
            if riding_horse:
                if keys[pygame.K_UP]:
                    horse.pos[1] -= player.speed
                    horse.pos[1] = max(0, horse.pos[1])
                if keys[pygame.K_DOWN]:
                    horse.pos[1] += player.speed
                    horse.pos[1] = min(SCREEN_HEIGHT - HORSE_SIZE, horse.pos[1])
                if keys[pygame.K_LEFT]:
                    horse.pos[0] -= player.speed
                    horse.pos[0] = max(0, horse.pos[0])
                if keys[pygame.K_RIGHT]:
                    horse.pos[0] += player.speed
                    horse.pos[0] = min(SCREEN_WIDTH - HORSE_SIZE, horse.pos[0])
                player.pos = horse.pos
            else:
                if keys[pygame.K_UP]:
                    player.pos[1] -= player.speed
                    player.pos[1] = max(0, player.pos[1])
                if keys[pygame.K_DOWN]:
                    player.pos[1] += player.speed
                    player.pos[1] = min(SCREEN_HEIGHT - PLAYER_SIZE, player.pos[1])
                if keys[pygame.K_LEFT]:
                    player.pos[0] -= player.speed
                    player.pos[0] = max(0, player.pos[0])
                if keys[pygame.K_RIGHT]:
                    player.pos[0] += player.speed
                    player.pos[0] = min(SCREEN_WIDTH - PLAYER_SIZE, player.pos[0])

            # Collision detection
            for enemy in enemies[:]:
                if abs(player.pos[0] - enemy.pos[0]) < (PLAYER_SIZE + ENEMY_SIZE) // 2 and abs(player.pos[1] - enemy.pos[1]) < (PLAYER_SIZE + ENEMY_SIZE) // 2:
                    if not player.shield:
                        player.health -= 10
                        player.health = max(0, player.health)
                        if player.health <= 0:
                            game_over = True
                    enemies.remove(enemy)

            if game_over:
                screen.fill(WHITE)
                font = pygame.font.Font(None, 36)
                text = font.render("Game Over", True, RED)
                text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                screen.blit(text, text_rect)
                pygame.display.update()
                pygame.time.wait(2000)
                running = False

            # Draw the game
            screen.fill(WHITE)
            if riding_horse:
                pygame.draw.rect(screen, BROWN, (horse.pos[0], horse.pos[1], HORSE_SIZE, HORSE_SIZE))
            else:
                pygame.draw.rect(screen, GREEN, (player.pos[0], player.pos[1], PLAYER_SIZE, PLAYER_SIZE))
            for enemy in enemies:
                pygame.draw.rect(screen, RED, (enemy.pos[0], enemy.pos[1], ENEMY_SIZE, ENEMY_SIZE))
            pygame.display.update()

            # Update the game clock
            clock.tick(60)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        pygame.quit()

if __name__ == "__main__":
    main()
