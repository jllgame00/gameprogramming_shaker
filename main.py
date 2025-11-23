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
    path = os.path.join(IMG_DIR, name)
    img = pygame.image.load(path)
    return img

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
# 모드 / 상태
# --------------------------------
MODE_SHAKING = 0    # 셰이킹 단계
MODE_MOVING  = 1    # 잔 위로 위치 이동 단계
MODE_POURING = 2    # 붓기 단계

mode = MODE_SHAKING
SHAKE_THRESHOLD = 2.0   # 이 정도 이상 흔들면 이동 모드 진입

# --------------------------------
# 셰이커 / 잔 위치 세팅
# --------------------------------
# 셰이커 위치 (기본 위치)
base_shaker_pos = pygame.Vector2(SCREEN_WIDTH * 0.3, SCREEN_HEIGHT * 0.55)
shaker_pos = base_shaker_pos.copy()

shaker_angle = 0.0
SHAKE_ANGLE_MIN = -75
SHAKE_ANGLE_MAX = 30
POUR_THRESHOLD = -30  # 이 각도보다 많이 기울면 붓기 시작

# 흔들기 관련
shake_power = 0.0
shake_timer = 0.0

# 셰이커 바디 원본 / 렉트
shaker_body_orig = shaker_body_img
shaker_body_rect = shaker_body_orig.get_rect(center=shaker_pos)

# 셰이커 바닥 y (잔이랑 평행하게 맞출 높이)
baseline_y = shaker_pos.y + shaker_body_rect.height * 0.5

# 셰이커 입구 오프셋 (바디 중심 기준 상대 좌표)
mouth_offset = pygame.Vector2(0, -shaker_body_rect.height * 0.5 + 12)

# 캡 이미지 정보
shaker_cap_orig = shaker_cap_img
shaker_cap_rect = shaker_cap_orig.get_rect()

# 캡이 "바디 위에 얹혀 있을 때" 중심 위치 오프셋 (대략)
cap_offset = pygame.Vector2(
    0,
    -shaker_body_rect.height * 0.5 - shaker_cap_rect.height * 0.3
)

# 캡이 옆으로 치워졌을 때 위치
cap_side_pos = pygame.Vector2(SCREEN_WIDTH * 0.45,
                              baseline_y - shaker_cap_rect.height * 0.5)

# 처음에는 캡이 셰이커 위에 있음
cap_on_top = True

# 잔 위치 (바닥 y를 셰이커와 동일하게 맞춤)
glass_rect = glass_img.get_rect()
glass_rect.midbottom = (SCREEN_WIDTH * 0.72, baseline_y)


# --------------------------------
# 잔 내부 삼각형 (액체 영역)
# --------------------------------
def get_glass_triangle():
    gw, gh = glass_rect.width, glass_rect.height

    bottom = (glass_rect.centerx, glass_rect.bottom - gh * 0.40)
    top_y = glass_rect.top + gh * 0.20

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
        pygame.draw.circle(surface, self.color,
                           (int(self.pos.x), int(self.pos.y)), self.radius)

particles = []
fill_amount = 0.0          # 0 ~ 1
FILL_PER_PARTICLE = 0.006  # 한 입자당 얼마나 차는지

# --------------------------------
# 유틸 함수
# --------------------------------
def point_in_triangle(pt, a, b, c):
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
prev_mouse_y = None

while running:
    dt = clock.tick(FPS) / 1000.0

    # -----------------------------
    # 모드별 기본 업데이트
    # -----------------------------
    if mode == MODE_SHAKING:
        # 셰이킹 애니메이션 (좌우 덜덜)
        shake_timer += dt
        shake_power *= 0.9
        if shake_power < 0.01:
            shake_power = 0.0

        shake_offset_y = math.sin(shake_timer * 40) * shake_power * 5
        shaker_pos = pygame.Vector2(
            base_shaker_pos.x,
            base_shaker_pos.y + shake_offset_y
        )

    # MOVING / POURING 에서는 shaker_pos를 이벤트로만 움직임
    # (따로 처리 안 함)

    # -----------------------------
    # 이벤트 처리
    # -----------------------------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # -------------------------
        # MODE_SHAKING: 흔들기만, 각도/위치 고정
        # -------------------------
        if mode == MODE_SHAKING:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_dragging = True
                prev_mouse_x = event.pos[0]

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                mouse_dragging = False
                prev_mouse_x = None
                # 마우스 떼는 순간, 충분히 흔들었으면 이동 모드로 전환
                if shake_power >= SHAKE_THRESHOLD:
                    mode = MODE_MOVING
                    # 셰이커 위치를 기준 위치로 고정
                    shaker_pos = base_shaker_pos.copy()

            elif event.type == pygame.MOUSEMOTION and mouse_dragging:
                mx, my = event.pos
                if prev_mouse_x is not None:
                    dx = mx - prev_mouse_x
                    # 각도는 안 바꾸고, 흔든 강도만 올림
                    shake_power += abs(dx) * 0.02
                    prev_mouse_x = mx

        # -------------------------
        # MODE_MOVING: 잔 위로 위치 옮기기
        # -------------------------
        elif mode == MODE_MOVING:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_dragging = True

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                mouse_dragging = False
                # 위치 옮기기 끝 → 붓기 모드로 전환
                mode = MODE_POURING
                cap_on_top = False  # 캡 분리
                # 이때 위치를 기준 위치로 사용하도록 업데이트
                base_shaker_pos = shaker_pos.copy()

            elif event.type == pygame.MOUSEMOTION and mouse_dragging:
                mx, my = event.pos
                shaker_pos.x = mx
                shaker_pos.y = my

        # -------------------------
        # MODE_POURING: 각도만 조절해서 붓기
        # -------------------------
        elif mode == MODE_POURING:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_dragging = True
                prev_mouse_y = event.pos[1]

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                mouse_dragging = False
                prev_mouse_y = None

            elif event.type == pygame.MOUSEMOTION and mouse_dragging:
                my = event.pos[1]
                if prev_mouse_y is not None:
                    dy = my - prev_mouse_y      # 마우스 아래로 드래그 → 음료 붓기
                    shaker_angle += dy * 0.4    # 감도 조절
                    shaker_angle = max(SHAKE_ANGLE_MIN,
                                    min(SHAKE_ANGLE_MAX, shaker_angle))
                    prev_mouse_y = my

    # -----------------------------
    # 상태 업데이트 (공통)
    # -----------------------------
    # 셰이커 바디 회전
    rotated_body = pygame.transform.rotozoom(shaker_body_orig,
                                             shaker_angle, 1.0)
    body_rect = rotated_body.get_rect(center=shaker_pos)

    # 셰이커 입구 위치
    rotated_mouth_offset = mouth_offset.rotate(-shaker_angle)
    mouth_pos = shaker_pos + rotated_mouth_offset

    # 입자 생성 (붓기 모드 + 각도 임계치)
    if mode == MODE_POURING and shaker_angle < POUR_THRESHOLD:
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

    # 셰이커 캡
    if cap_on_top:
        # 바디와 함께 회전하는 캡
        rotated_cap = pygame.transform.rotozoom(shaker_cap_orig,
                                                shaker_angle, 1.0)
        rotated_cap_offset = cap_offset.rotate(-shaker_angle)
        cap_center = shaker_pos + rotated_cap_offset
        cap_rect = rotated_cap.get_rect(center=cap_center)
        screen.blit(rotated_cap, cap_rect)
    else:
        # 옆으로 치워진 캡
        cap_rect = shaker_cap_orig.get_rect(center=cap_side_pos)
        screen.blit(shaker_cap_orig, cap_rect)

    # 입자들
    for p in particles:
        p.draw(screen)

    pygame.display.flip()

pygame.quit()