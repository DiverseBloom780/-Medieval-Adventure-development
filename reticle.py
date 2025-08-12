# reticle.py
from __future__ import annotations
import pygame

def draw_reticle(screen: pygame.Surface, pos: tuple[int, int], radius: int = 10, thickness: int = 2) -> None:
    x, y = pos
    pygame.draw.circle(screen, (0, 0, 0), (x, y), radius + 2, thickness)
    pygame.draw.circle(screen, (255, 255, 255), (x, y), radius, thickness)
    pygame.draw.line(screen, (255, 255, 255), (x - radius - 6, y), (x - radius + 2, y), thickness)
    pygame.draw.line(screen, (255, 255, 255), (x + radius - 2, y), (x + radius + 6, y), thickness)
    pygame.draw.line(screen, (255, 255, 255), (x, y - radius - 6), (x, y - radius + 2), thickness)
    pygame.draw.line(screen, (255, 255, 255), (x, y + radius - 2), (x, y + radius + 6), thickness)
