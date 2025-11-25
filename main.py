# main.py
import os
import pygame

from component.shaker import Shaker
from component.glass import Glass
from component.particles import Particle
from component.config import FPS

pygame.init()

# -------------------------------
# 경로 / 이미지 로드
# -------------------------------
IMG_DIR = os.path.join("img")

def load_image(name):
    return pygame.image.load(os.path.join(IMG_DIR, name))

background_img = load_image("background.png")
shaker_body_img = load_image("shaker_body.png")
shaker_cap_img = load_image("shaker_cap.png")
glass_img = load_image("glass.png")

SCREEN_WIDTH, SCREEN_HEIGHT = background_img.get_size()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Seolhwa - Shaker Prototype")

clock = pygame.time.Clock()

# -------------------------------
# 셰이커 / 잔 초기화
# -------------------------------
# baseline_y = 셰이커 바닥 높이를 기준으로 잔 위치 맞춤
temp_rect = shaker_body_img.get_rect()
baseline_y = SCREEN_HEIGHT * 0.55 + (temp_rect.height * 0.5)

shaker = Shaker(shaker_body_img,
                shaker_cap_img,
                SCREEN_WIDTH,
                SCREEN_HEIGHT)

glass = Glass(glass_img,
              SCREEN_WIDTH,
              SCREEN_HEIGHT,
              baseline_y)

particles = []   # 스트림 입자 리스트

# -------------------------------
# 게임 루프
# -------------------------------
running = True

while running:
    dt = clock.tick(FPS) / 1000.0
    events = pygame.event.get()

    for e in events:
        if e.type == pygame.QUIT:
            running = False
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_UP:
                glass.fill_amount += 0.05
            elif e.key == pygame.K_DOWN:
                glass.fill_amount -= 0.05

    glass.fill_amount = max(0.0, min(1.0, glass.fill_amount))

    screen.blit(background_img, (0, 0))
    glass.draw(screen)
    shaker.draw(screen)  # 있어도 되고, 없어도 되고

    pygame.display.flip()

pygame.quit()