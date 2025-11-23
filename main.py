import os
import math
import random
import pygame

pygame.init()

# --------------------------------
# 경로 설정
# --------------------------------
IMG_DIR = os.path.join("img")

def load_image(name):
    """디스플레이 세팅 전 convert() 안 쓰려고, 그냥 load만."""
    path = os.path.join(IMG_DIR, name)
    img = pygame.image.load(path)
    return img  # convert() 안 씀 → No video mode 에러 방지

# --------------------------------
# 이미지 로드
# --------------------------------
background_img = load_image("background.png")
shaker_body_img = load_image("shaker_body.png")
shaker_cap_img = load_image("shaker_cap.png")
glass_img = load_image("glass.png")

# 화면 크기 = 배경 크기 기준
SCREEN_WIDTH, SCREEN_HEIGHT = background_img.get_size()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Seolhwa - Shaker Prototype")

clock = pygame.time.Clock()
FPS = 60

# --------------------------------
# 셰이커 / 잔 위치 세팅
# --------------------------------
# 셰이커 위치 (왼쪽)
shaker_pos = pygame.Vector2(SCREEN_WIDTH * 0.3, SCREEN_HEIGHT * 0.55)
shaker_angle = 0.0
SHAKE_ANGLE_MIN = -75
SHAKE_ANGLE_MAX = 30
POUR_THRESHOLD = -30  # 이 각도보다 많이 기울면 붓기 시작

# 셰이커 바디 원본 / 렉트
shaker_body_orig = shaker_body_img
shaker_body_rect = shaker_body_orig.get_rect(center=shaker_pos)

# 셰이커 입구 오프셋 (바디 중심 기준 상대 좌표)
mouth_offset = pygame.Vector2(0, -shaker_body_rect.height * 0.5 + 12)

# 셰이커 캡 위치 (오른쪽에 놓여있는 상태)
cap_pos = pygame.Vector2(SCREEN_WIDTH * 0.45, SCREEN_HEIGHT * 0.52)

# 잔 위치 (오른쪽)
glass_pos = pygame.Vector2(SCREEN_WIDTH * 0.72, SCREEN_HEIGHT * 0.6)
glass_rect = glass_img.get_rect(midbottom=glass_pos)

# --------------------------------
# 잔 내부 삼각형 (액체 영역)
# --------------------------------
def get_glass_triangle():
    """
    glass_img 안에서 대략 V자 컵 영역 잡기.
    필요하면 비율 조정해서 눈으로 맞추면 됨.
    """
    gw, gh = glass_rect.width, glass_rect.height

    bottom = (glass_rect.centerx, glass_rect.centery - gh * 0.10)
    top_y = glass_rect.y + gh * 0.20

    top_left = (glass_rect.centerx - gw * 0.38, top_y)
    top_right = (glass_rect.centerx + gw * 0.38, top_y)

    return {
        "top_left": top_left,
        "top_right": top_right,
        "bottom": bottom,
    }

# --------------------------------
# 입자(액체) 시스템
# --------------------------------
class Particle:
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(random.uniform(-0.5, 0.5),
                                  random.uniform(1.0, 2.0))
        self.radius = 3
        self.color = (255, 90, 150)  # 코스모폴리탄 느낌

    def update(self):
        self.vel.y += 0.08  # 중력
        self.pos += self.vel

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, self.pos, self.radius)

particles = []
fill_amount = 0.0          # 0 ~ 1
FILL_PER_PARTICLE = 0.006  # 한 입자당 얼마나 차는지

# --------------------------------
# 유틸 함수
# --------------------------------
def point_in_triangle(pt, a, b, c):
    """점이 삼각형 내부에 있는지 체크 (면적 합)."""
    (x, y) = pt

    def area(x1, y1, x2, y2, x3, y3):
        return abs((x1 * (y2 - y3) +
                    x2 * (y3 - y1) +
                    x3 * (y1 - y2)) / 2.0)

    A = area(*a, *b, *c)
    A1 = area(x, y, *b, *c)
    A2 = area(*a, x, y, *c)
    A3 = area(*a, *b, x, y)

    return abs((A1 + A2 + A3) - A) < 0.3

def draw_liquid(surface, tri, amount):
    """마티니 잔 내부를 amount 비율만큼 채운다."""
    amount = max(0.0, min(1.0, amount))

    top_left = pygame.Vector2(tri["top_left"])
    top_right = pygame.Vector2(tri["top_right"])
    bottom = pygame.Vector2(tri["bottom"])

    current_y = bottom.y + (top_left.y - bottom.y) * amount
    left_x  = bottom.x + (top_left.x  - bottom.x) * amount
    right_x = bottom.x + (top_right.x - bottom.x) * amount

    poly = [
        (bottom.x, bottom.y),
        (left_x, current_y),
        (right_x, current_y),
    ]

    LIQUID_COLOR = (255, 110, 170)
    pygame.draw.polygon(surface, LIQUID_COLOR, poly)

# --------------------------------
# 메인 루프
# --------------------------------
running = True
mouse_dragging = False
prev_mouse_x = None

while running:
    dt = clock.tick(FPS) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # 마우스로 흔들기
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mouse_dragging = True
                prev_mouse_x = event.pos[0]

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                mouse_dragging = False
                prev_mouse_x = None

        elif event.type == pygame.MOUSEMOTION and mouse_dragging:
            mx, my = event.pos
            if prev_mouse_x is not None:
                dx = mx - prev_mouse_x
                shaker_angle += dx * -0.3  # 오른쪽으로 드래그 → 오른쪽 기울기
                shaker_angle = max(SHAKE_ANGLE_MIN,
                                   min(SHAKE_ANGLE_MAX, shaker_angle))
                prev_mouse_x = mx

        # 키보드로 미세 조정
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                shaker_angle += 3
            elif event.key == pygame.K_RIGHT:
                shaker_angle -= 3
            shaker_angle = max(SHAKE_ANGLE_MIN,
                               min(SHAKE_ANGLE_MAX, shaker_angle))

    # -----------------------------
    # 업데이트
    # -----------------------------
    # 셰이커 회전
    rotated_body = pygame.transform.rotozoom(shaker_body_orig,
                                             shaker_angle, 1.0)
    body_rect = rotated_body.get_rect(center=shaker_pos)

    # 입구 위치 계산
    rotated_offset = mouth_offset.rotate(-shaker_angle)
    mouth_pos = shaker_pos + rotated_offset

    # 일정 각도 이상 기울면 입자 생성
    if shaker_angle < POUR_THRESHOLD:
        if random.random() < 0.7:
            particles.append(Particle(mouth_pos.x, mouth_pos.y))

    tri = get_glass_triangle()
    a = tri["top_left"]
    b = tri["top_right"]
    c = tri["bottom"]

    for p in particles[:]:
        p.update()

        if p.pos.y > SCREEN_HEIGHT + 50:
            particles.remove(p)
            continue

        if point_in_triangle((p.pos.x, p.pos.y), a, b, c):
            fill_amount += FILL_PER_PARTICLE
            particles.remove(p)

    fill_amount = max(0.0, min(1.0, fill_amount))

    # -----------------------------
    # 렌더링
    # -----------------------------
    screen.blit(background_img, (0, 0))

    # 잔 + 액체
    screen.blit(glass_img, glass_rect)
    draw_liquid(screen, tri, fill_amount)

    # 셰이커 바디
    screen.blit(rotated_body, body_rect)

    # 셰이커 캡 (테이블에 놓여 있음)
    cap_rect = shaker_cap_img.get_rect(center=cap_pos)
    screen.blit(shaker_cap_img, cap_rect)

    # 입자들
    for p in particles:
        p.draw(screen)

    pygame.display.flip()

pygame.quit()
