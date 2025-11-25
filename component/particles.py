# component/particles.py
import pygame
import random

class Particle:
    """
    셰이커에서 떨어지는 기본 물방울.
    - 중력으로 떨어짐
    - 단순 원형
    """
    def __init__(self, x, y, color=(255, 110, 170)):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(
            random.uniform(-0.3, 0.3),
            random.uniform(1.0, 2.0)
        )
        self.color = color
        self.radius = 3

    def update(self):
        # 중력
        self.vel.y += 0.08
        self.pos += self.vel

    def draw(self, surf: pygame.Surface):
        pygame.draw.circle(
            surf,
            self.color,
            (int(self.pos.x), int(self.pos.y)),
            self.radius
        )
