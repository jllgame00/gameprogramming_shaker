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

    # 1) 셰이커 상태 업데이트
    shaker.update(events, dt)

    # 2) 붓는 정도 계산
    is_pouring = shaker.is_pouring_now()
    mouth_pos = shaker.get_mouth_pos()
    pour_factor = shaker.get_pour_factor()

    # 3) 실제로 셰이커에서 빠진 양 계산
    used_volume = shaker.update_volume(dt, pour_factor)

    # 4) 잔 업데이트 (라인 기반 리퀴드)
    glass.update_stream(dt, is_pouring, mouth_pos, pour_factor, used_volume)

    # 5) 렌더링
    screen.blit(background_img, (0, 0))
    glass.draw(screen)
    shaker.draw(screen)

    pygame.display.flip()


pygame.quit()
