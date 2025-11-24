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
    return img  # convert 생략 (간단하게)

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
# 셰이커 기본 위치
base_shaker_pos = pygame.Vector2(SCREEN_WIDTH * 0.3, SCREEN_HEIGHT * 0.55)
shaker_pos = base_shaker_pos.copy()

shaker_angle = 0.0
SHAKE_ANGLE_MIN = -130   # 더 많이 기울 수 있게
SHAKE_ANGLE_MAX =  30

# 90도 이후부터 쏟아지게
POUR_START_ANGLE = -90    # -90도부터 흐름 시작
POUR_MAX_ANGLE   = -120   # 여기서 최대 유량

# 흔들기 관련
shake_power = 0.0
shake_timer = 0.0

# 셰이커 바디 정보
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
cap_side_pos = pygame.Vector2(
    SCREEN_WIDTH * 0.45,
    baseline_y - shaker_cap_rect.height * 0.5
)

# 처음에는 캡이 셰이커 위에 있음
cap_on_top = True

# 잔 위치 (바닥 y를 셰이커와 동일하게 맞춤)
glass_rect = glass_img.get_rect()
glass_rect.midbottom = (SCREEN_WIDTH * 0.72, baseline_y)

# 액체를 그릴 서피스 (잔 앞에 반투명으로 올릴 예정)
liquid_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

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
# 셰이커 안 칵테일 양 / 잔 채움 관련
# --------------------------------
MAX_SHAKER_VOLUME = 1.0         # 셰이커 안에 있는 총 칵테일 양 (정규화)
shaker_volume = MAX_SHAKER_VOLUME

VOLUME_PER_PARTICLE = 0.004     # 입자 하나 나갈 때 셰이커에서 빠지는 양
GLASS_FILL_PER_PARTICLE = 0.003 # 잔에 들어올 때 fill_amount에 더해지는 양 (조금 느리게)

# --------------------------------
# 입자(액체) 시스템
# --------------------------------
class Particle:
    def __init__(self, x, y):
        # 수도꼭지 물줄기처럼: x 살짝만 퍼지고, 수직으로 빨리 떨어짐
        self.pos = pygame.Vector2(x + random.uniform(-2, 2), y)
        self.vel = pygame.Vector2(
            random.uniform(-0.1, 0.1),
            random.uniform(2.5, 3.5)
        )
        self.radius = 3  # 조금 더 굵은 물줄기
        self.color = (255, 90, 150)  # 코스모폴리탄 느낌

    def update(self):
        self.vel.y += 0.08  # 중력
        self.pos += self.vel

    def draw(self, surface):
        pygame.draw.circle(
            surface,
            self.color,
            (int(self.pos.x), int(self.pos.y)),
            self.radius
        )

particles = []
fill_amount = 0.0          # 잔 안에 채워진 정도 (0~이상, 1.0 넘으면 오버플로우 상태로 활용 가능)

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
    # 실제 fill_amount는 1.0 이상도 갈 수 있지만,
    # 화면에 보이는 건 0~1 사이까지만.
    visible = max(0.0, min(1.0, amount))

    top_left = pygame.Vector2(tri["top_left"])
    top_right = pygame.Vector2(tri["top_right"])
    bottom = pygame.Vector2(tri["bottom"])

    current_y = bottom.y + (top_left.y - bottom.y) * visible
    left_x  = bottom.x + (top_left.x  - bottom.x) * visible
    right_x = bottom.x + (top_right.x - bottom.x) * visible

    poly = [
        (bottom.x, bottom.y),
        (left_x, current_y),
        (right_x, current_y),
    ]

    # 반투명 액체 색상 (RGBA) — 잔 앞에 그릴 거라 투명도 중요
    LIQUID_COLOR = (255, 110, 170, 200)
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
    # MODE_SHAKING — 흔들기 단계
    # -----------------------------
    if mode == MODE_SHAKING:
        shake_timer += dt
        shake_power *= 0.9
        if shake_power < 0.01:
            shake_power = 0.0

        # 위아래 덜덜
        shake_offset_y = math.sin(shake_timer * 40) * shake_power * 5
        shaker_pos = pygame.Vector2(
            base_shaker_pos.x,
            base_shaker_pos.y + shake_offset_y
        )

    # -----------------------------
    # 이벤트 처리
    # -----------------------------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # --------------------------------
        # MODE_SHAKING
        # --------------------------------
        if mode == MODE_SHAKING:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_dragging = True
                prev_mouse_x = event.pos[0]

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                mouse_dragging = False
                prev_mouse_x = None

                # 흔들기 힘이 충분하면 이동 모드로
                if shake_power >= SHAKE_THRESHOLD:
                    mode = MODE_MOVING
                    base_shaker_pos = shaker_pos.copy()

            elif event.type == pygame.MOUSEMOTION and mouse_dragging:
                mx = event.pos[0]
                if prev_mouse_x is not None:
                    dx = mx - prev_mouse_x
                    shake_power += abs(dx) * 0.02
                    prev_mouse_x = mx

        # --------------------------------
        # MODE_MOVING — 잔 위로 이동
        # --------------------------------
        elif mode == MODE_MOVING:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_dragging = True

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                mouse_dragging = False

                # 마우스에서 손 떼면 붓기 단계로
                mode = MODE_POURING
                cap_on_top = False

            elif event.type == pygame.MOUSEMOTION and mouse_dragging:
                mx, my = event.pos
                shaker_pos.x = mx
                shaker_pos.y = my

        # --------------------------------
        # MODE_POURING — 각도 조절로 붓기
        # --------------------------------
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
                    dy = my - prev_mouse_y
                    shaker_angle += dy * 0.4
                    shaker_angle = max(SHAKE_ANGLE_MIN,
                                       min(SHAKE_ANGLE_MAX, shaker_angle))
                    prev_mouse_y = my

    # -----------------------------
    # 셰이커 회전 + 입구 위치 계산
    # -----------------------------
    rotated_body = pygame.transform.rotozoom(
        shaker_body_orig, shaker_angle, 1.0
    )
    body_rect = rotated_body.get_rect(center=shaker_pos)

    rotated_mouth_offset = mouth_offset.rotate(-shaker_angle)
    mouth_pos = shaker_pos + rotated_mouth_offset

    # -----------------------------
    # 붓기: 각도 기반 유량 계산
    # -----------------------------
    if mode == MODE_POURING and shaker_volume > 0:

        if shaker_angle <= POUR_START_ANGLE:  # -90도보다 더 기울면
            over = min(1.0, max(0.0,
                (abs(shaker_angle) - abs(POUR_START_ANGLE)) /
                (abs(POUR_MAX_ANGLE)   - abs(POUR_START_ANGLE))
            ))

            base_stream = 1
            extra_stream = int(4 * over)
            num_stream = base_stream + extra_stream

            for _ in range(num_stream):
                if shaker_volume <= 0:
                    break
                particles.append(Particle(mouth_pos.x, mouth_pos.y))
                shaker_volume = max(0.0, shaker_volume - VOLUME_PER_PARTICLE)

    # -----------------------------
    # 파티클 업데이트 & 잔 채우기
    # -----------------------------
    tri = get_glass_triangle()
    a, b, c = tri["top_left"], tri["top_right"], tri["bottom"]

    for p in particles[:]:
        p.update()

        if p.pos.y > SCREEN_HEIGHT + 50:
            particles.remove(p)
            continue

        if point_in_triangle((p.pos.x, p.pos.y), a, b, c):
            fill_amount += GLASS_FILL_PER_PARTICLE
            particles.remove(p)

    # -----------------------------
    # 렌더링
    # -----------------------------
    screen.blit(background_img, (0, 0))

    # 액체 서피스 비우기
    liquid_surface.fill((0, 0, 0, 0))

    # 액체 먼저 그림 (앞에), 잔 뒤에서 가리지 않음
    draw_liquid(liquid_surface, tri, fill_amount)

    # 잔 → 액체 → 셰이커 순으로 뿌리면 더 자연스럽게 보임
    screen.blit(glass_img, glass_rect)
    screen.blit(liquid_surface, (0, 0))

    # 셰이커 바디
    screen.blit(rotated_body, body_rect)

    # 셰이커 캡
    if cap_on_top:
        rotated_cap = pygame.transform.rotozoom(
            shaker_cap_orig, shaker_angle, 1.0
        )
        rotated_cap_offset = cap_offset.rotate(-shaker_angle)
        cap_center = shaker_pos + rotated_cap_offset
        cap_rect = rotated_cap.get_rect(center=cap_center)
        screen.blit(rotated_cap, cap_rect)
    else:
        cap_rect = shaker_cap_orig.get_rect(center=cap_side_pos)
        screen.blit(shaker_cap_orig, cap_rect)

    # 파티클 그리기
    for p in particles:
        p.draw(screen)

    pygame.display.flip()

pygame.quit()
