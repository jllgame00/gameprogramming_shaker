import pygame, random
from config import SURFACE_DROPLET_LIFE, SURFACE_DROPLET_RADIUS

class Particle:
    def __init__(self, x, y, color=(255,90,150)):
        self.pos = pygame.Vector2(x,y)
        self.vel = pygame.Vector2(random.uniform(-0.5,0.5),
                                  random.uniform(1.0,2.0))
        self.color=color
        self.radius=3

    def update(self):
        self.vel.y += 0.08
        self.pos += self.vel

    def draw(self, surf):
        pygame.draw.circle(surf, self.color, (int(self.pos.x), int(self.pos.y)), self.radius)


class SurfaceDroplet:
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x,y)
        self.life = random.uniform(*SURFACE_DROPLET_LIFE)
        self.radius = SURFACE_DROPLET_RADIUS
        self.color = (255,120,180)

    def update(self, dt):
        self.life -= dt
        self.pos.x += random.uniform(-0.3,0.3)
        self.pos.y += random.uniform(-0.2,0.2)

    def draw(self, surf):
        pygame.draw.circle(surf, self.color, (int(self.pos.x), int(self.pos.y)), self.radius)