import pygame
import random

pygame.init()

# Set up the display
screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Medieval Adventure")

# Load images
player_image = pygame.image.load("player.png")
horse_image = pygame.image.load("horse.png")
sword_image = pygame.image.load("sword.png")
axe_image = pygame.image.load("axe.png")
mace_image = pygame.image.load("mace.png")
bow_image = pygame.image.load("bow.png")
crossbow_image = pygame.image.load("crossbow.png")
health_image = pygame.image.load("health.png")
shield_image = pygame.image.load("shield.png")
enemy_image = pygame.image.load("enemy.png")

# Load sounds
hit_sound = pygame.mixer.Sound("hit.wav")
game_music = pygame.mixer.music.load("game_music.wav")
pygame.mixer.music.play(-1)

# Set up game variables
player_pos = [screen_width // 2, screen_height // 2]
player_speed = 5
player_health = 100
player_weapon = "sword"
player_shield = False
riding_horse = False

horse_pos = [screen_width // 2 - 100, screen_height // 2]
horse_speed = 10

enemies = []
for i in range(50):
    enemy_x = random.randint(0, screen_width - 50)
    enemy_y = random.randint(0, screen_height - 50)
    enemies.append([enemy_x, enemy_y, 50, 50])

power_ups = []
for i in range(3):
    power_up_x = random.randint(0, screen_width - 50)
    power_up_y = random.randint(0, screen_height - 50)
    power_ups.append([power_up_x, power_up_y, "health"])

score = 0
level = 1
max_level = 3

# Set up game loop
running = True
clock = pygame.time.Clock()

while running:
    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if riding_horse:
                    riding_horse = False
                    player_speed = 5
                else:
                    if pygame.Rect(player_pos[0], player_pos[1], 50, 50).colliderect(pygame.Rect(horse_pos[0], horse_pos[1], 50, 50)):         
                       riding_horse =True
                       player_speed =horse_speed
            elif event.key == pygame.K_1:
               player_weapon = "sword"
            elif event.key == pygame.K_2:
               player_weapon = "axe"
            elif event.key == pygame.K_3:
               player_weapon = "mace"
            elif event.key == pygame.K_4:
               player_weapon = "bow"
            elif event.key == pygame.K_5:
               player_weapon = "crossbow"
            elif event.key == pygame.K_SPACE:
               player_shield = True
            elif event.key == pygame.K_q:
                player_shield = False

    for enemy in enemies:
        if pygame.Rect(player_pos[0], player_pos[1], 50, 50).colliderect(pygame.Rect(enemy[0], enemy[1], 50, 50)):
           
            if player_shield:
                pass
            else:
                if player_health > 0:
                    player_health -= 10
                enemies.remove(enemy)

    #


    # Draw the game
    screen.fill((255, 255, 255))
    if riding_horse:
        screen.blit(horse_image, horse_pos)
    else:
        screen.blit(player_image, player_pos)
    for enemy in enemies:
        pygame.draw.rect(screen, (255, 0, 0), pygame.Rect(enemy[0], enemy[1], 50, 50))
    pygame.display.update()

    # Update the game clock
    clock.tick(60)

# Quit the game
pygame.quit()