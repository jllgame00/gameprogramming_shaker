import os
import math
import random
import pygame

# -------------------------
# 기본 설정
# -------------------------
pygame.init()

# 이미지 경로 (project 3/img)
IMG_DIR = os.path.join("img")

def load_image(name, alpha=True):
    path = os.path.join(IMG_DIR, name)
    img = pygame.image.load(path)
    return img.convert_alpha() if alpha else img.convert()

# 이미지 로드
background_img = load_image("background.png", alpha=False)
shaker_body_img = load_image("shaker_body.png")
shaker_cap_img = load_image("shaker_cap.png")
glass_img = load_image("glass.png")

# 화면 크기 = 배경 크기와 동일하게
SCREEN_WIDTH, SCREEN_HEIGHT = background_img.get_size()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Seolhwa - Shaker Prototype")

clock = pygame.time.Clock()
FPS = 60

# -------------------------
# 셰이커 / 잔 위치 세팅
# -------------------------

# 셰이커는 화면 왼쪽 중간쯤에 세움
shaker_pos = pygame.Vector2(SCREEN_WIDTH * 0.3, SCREEN_HEIGHT * 0.55)
shaker_angle = 0.0  # 0도 = 수직, 음수 = 오른쪽으로 기울기(잔 쪽으로)
SHAKE_ANGLE_MIN = -75  # 너무 많이 안 가게 제한
SHAKE_ANGLE_MAX =  30
POUR_THRESHOLD = -30   # 이 각도보다 많이 기울면 액체가 나옴

# 셰이커 피벗 = 바디 중심
shaker_body_orig = shaker_body_img
shaker_body_rect = shaker_body_orig.get_rect(center=shaker_pos)

# "입구" 위치를 셰이커 중심 기준 상대 좌표로 정의 (대충 윗쪽 위치)
# (0, -height/2 + offset) 느낌
mouth_offset = pygame.Vector2(0, -shaker_body_rect.height * 0.5 + 12)

# 셰이커 뚜껑은 일단 테이블 위에 따로 놓여 있는 상태(프로토타입)
cap_pos = pygame.Vector2(SCREEN_WIDTH * 0.45, SCREEN_HEIGHT * 0.52)

# 잔은 오른쪽에
glass_pos = pygame.Vector2(SCREEN_WIDTH * 0.72, SCREEN_HEIGHT * 0.6)
glass_rect = glass_img.get_rect(midbottom=glass_pos)

# -------------------------
# 잔 안쪽(마티니 컵) 좌표 정의
# -------------------------
# glass_img 안에서 대략적인 V자 컵의 모양을 잡기 위해,
# 화면 좌표로 삼각형 세 점을 만들어준다.
#
#   top_left ----- top_right
#        \         /
#         \       /
#          \     /
#           \   /
#            bottom

def get_glass_triangle():
    # 이미지 대략 비율로 잡음. 필요하면 숫자 조정하면 됨.
    gx, gy, gw, gh = glass_rect.x, glass_rect.y, glass_rect.width, glass_rect.height

    bottom = (glass_rect.centerx, glass_rect.centery - gh * 0.10)
    top_y = glass_rect.y + gh * 0.20

    top_left = (glass_rect.centerx - gw * 0.38, top_y)
    top_right = (glass_rect.centerx + gw * 0.38, top_y)

    return {
        "top_left": top_left,
        "top_right": top_right,
        "bottom": bottom,
    }

glass_tri = get_glass_triangle()

# -------------------------
# 액체 입자 시스템
# -------------------------
class Particle:
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(random.uniform(-0.5, 0.5), random.uniform(1.0, 2.0))
        self.radius = 3
        # 코스모폴리탄 느낌 색
        self.color = (255, 90, 150)

    def update(self):
        # 중력
        self.vel.y += 0.08
        self.pos += self.vel

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, self.pos, self.radius)

particles = []

# 잔 채워진 정도 (0.0 ~ 1.0)
fill_amount = 0.0
FILL_PER_PARTICLE = 0.006  # 입자당 얼마나 차는지

# -------------------------
# 유틸 함수들
# -------------------------
def point_in_triangle(pt, a, b, c):
    """점이 삼각형 내부에 있는지 체크 (면적 이용)"""
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
    """마티니 잔 내부 V자 부분을 amount 비율만큼 채운다."""
    amount = max(0.0, min(1.0, amount))  # clamp

    top_left = pygame.Vector2(tri["top_left"])
    top_right = pygame.Vector2(tri["top_right"])
    bottom = pygame.Vector2(tri["bottom"])

    # amount=0이면 bottom에 딱 붙고, amount=1이면 top line까지
    current_y = bottom.y + (top_left.y - bottom.y) * amount

    left_x  = bottom.x + (top_left.x  - bottom.x) * amount
    right_x = bottom.x + (top_right.x - bottom.x) * amount

    polygon_points = [
        (bottom.x, bottom.y),
        (left_x, current_y),
        (right_x, current_y),
    ]

    LIQUID_COLOR = (255, 110, 170)
    pygame.draw.polygon(surface, LIQUID_COLOR, polygon_points)

# -------------------------
# 메인 루프
# -------------------------
running = True
mouse_dragging = False
prev_mouse_x = None

while running:
    dt = clock.tick(FPS) / 1000.0  # 초 단위 delta time (필요하면 사용)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # 마우스로 셰이커 좌우 흔들어서 각도 조절
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
                shaker_angle += dx * -0.3  # 마우스 오른쪽으로 움직이면 오른쪽 기울기
                shaker_angle = max(SHAKE_ANGLE_MIN,
                                   min(SHAKE_ANGLE_MAX, shaker_angle))
                prev_mouse_x = mx

        # 키보드로도 미세 조정 가능 (좌우 키)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                shaker_angle += 3
            elif event.key == pygame.K_RIGHT:
                shaker_angle -= 3

            shaker_angle = max(SHAKE_ANGLE_MIN,
                               min(SHAKE_ANGLE_MAX, shaker_angle))

    # -------------------------
    # 로직 업데이트
    # -------------------------

    # 셰이커 회전
    rotated_body = pygame.transform.rotozoom(shaker_body_orig, shaker_angle, 1.0)
    body_rect = rotated_body.get_rect(center=shaker_pos)

    # 셰이커 입구 위치 계산 (mouth_offset을 각도만큼 회전)
    rotated_offset = mouth_offset.rotate(-shaker_angle)  # pygame은 반시계 양수라 부호 반전
    mouth_pos = shaker_pos + rotated_offset

    # 각도가 일정 기준 이상 기울어져 있으면 입자 생성
    if shaker_angle < POUR_THRESHOLD:
        # 초당 입자 여러 개 나오게 약간 랜덤
        if random.random() < 0.7:
            particles.append(Particle(mouth_pos.x, mouth_pos.y))

    # 입자 업데이트 & 잔 안에 들어갔는지 체크
    tri = get_glass_triangle()  # 혹시 잔 움직이면 매 프레임 재계산
    a = tri["top_left"]
    b = tri["top_right"]
    c = tri["bottom"]

    for p in particles[:]:
        p.update()

        # 화면 아래로 너무 떨어지면 삭제
        if p.pos.y > SCREEN_HEIGHT + 50:
            particles.remove(p)
            continue

        # 잔 내부 삼각형에 들어가면 -> 삭제 + 잔 채우기
        if point_in_triangle((p.pos.x, p.pos.y), a, b, c):
            fill_amount += FILL_PER_PARTICLE
            particles.remove(p)

    fill_amount = max(0.0, min(1.0, fill_amount))

    # -------------------------
    # 그리기
    # -------------------------
    screen.blit(background_img, (0, 0))

    # 잔 먼저 그리기
    screen.blit(glass_img, glass_rect)

    # 잔 안쪽 액체 채우기
    draw_liquid(screen, tri, fill_amount)

    # 셰이커 바디 그리기
    screen.blit(rotated_body, body_rect)

    # 셰이커 캡은 테이블 위에 그냥 놓여있는 걸로 (원하면 나중에 회전 연동)
    cap_rect = shaker_cap_img.get_rect(center=cap_pos)
    screen.blit(shaker_cap_img, cap_rect)

    # 입자들
    for p in particles:
        p.draw(screen)

    pygame.display.flip()

pygame.quit()