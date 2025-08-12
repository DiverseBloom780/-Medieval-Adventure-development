import warnings
warnings.filterwarnings("ignore", category=UserWarning)
import pygame
import math
import sys

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

def draw_tree(screen, x, y):
    pygame.draw.line(screen, BROWN, (x, y), (x, y - 50), 5)
    pygame.draw.circle(screen, TREE_GREEN, (x, y - 70), 30)

def draw_castle(screen, x, y):
    pygame.draw.rect(screen, STONE_GRAY, (x, y, 100, 100))
    pygame.draw.rect(screen, BROWN, (x + 40, y + 80, 20, 20))

def main():
    try:
        # Set up display
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Medieval Adventure")

        # Game loop
        clock = pygame.time.Clock()
        running = True
        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            # Draw the game
            screen.fill(SKY_BLUE)
            ground_y = int(SCREEN_HEIGHT * 0.6)
            pygame.draw.rect(screen, GREEN, (0, ground_y, SCREEN_WIDTH, int(SCREEN_HEIGHT * 0.4)))
            pygame.draw.ellipse(screen, WATER_BLUE, (800, ground_y + 50, 400, 100))
            draw_castle(screen, 400, ground_y - 100)
            draw_tree(screen, 600, ground_y + 50)
            draw_tree(screen, 1000, ground_y + 50)
            draw_tree(screen, 800, ground_y + 50)
            pygame.display.update()

            # Update the game clock
            clock.tick(60)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        pygame.quit()

if __name__ == "__main__":
    main()
