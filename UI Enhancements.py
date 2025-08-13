# In the Game class
def draw(self):
    # ...
    ui_font = pygame.font.SysFont("consolas", 24)

    # Health display
    health_text = ui_font.render(f"Health: {self.player.health}", True, (255, 255, 255))
    self.screen.blit(health_text, (10, 10))

    # Health bar
    health_bar_width = 100
    health_bar_height = 20
    health_bar_x = 10
    health_bar_y = 40
    pygame.draw.rect(self.screen, (255, 0, 0), (health_bar_x, health_bar_y, health_bar_width, health_bar_height), 2)
    pygame.draw.rect(self.screen, (0, 255, 0), (health_bar_x, health_bar_y, int(health_bar_width * self.player.health / 100), health_bar_height))

    # Score display
    score_text = ui_font.render(f"Score: {self.score}", True, (255, 255, 255))
    self.screen.blit(score_text, (10, 70))

    # Ammo display (if applicable)
    if hasattr(self.player, 'ammo'):
        ammo_text = ui_font.render(f"Ammo: {self.player.ammo}", True, (255, 255, 255))
        self.screen.blit(ammo_text, (10, 100))

    # Difficulty display
    difficulty_text = ui_font.render(f"Difficulty: {self.difficulty_level}", True, (255, 255, 255))
    self.screen.blit(difficulty_text, (10, 130))
