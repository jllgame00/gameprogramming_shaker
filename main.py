import os
import math
import random
import pygame
from obb import OBB, create_wall_obbs_from_triangle, point_in_obb


pygame.init()

# --------------------------------
# 경로 설정
# --------------------------------
IMG_DIR = os.path.join("img")

def load_image(name):
    path = os.path.join(IMG_DIR, name)
    return pygame.image.load(path)

# --------------------------------
# 이미지 로드
# --------------------------------
background_img = load_image("background.png")
shaker_body_img = load_image("shaker_body.png")
shaker_cap_img = load_image("shaker_cap.png")
glass_img = load_image("glass.png")

SCREEN_WIDTH, SCREEN_HEIGHT = background_img.get_size()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Seolhwa - Shaker Prototype")

clock = pygame.time.Clock()
FPS = 60

# --------------------------------
# 모드
# --------------------------------
MODE_SHAKING = 0    # 흔들기 단계
MODE_MOVING  = 1    # 잔 위로 이동
MODE_POURING = 2    # 따르기 단계
mode = MODE_SHAKING

SHAKE_THRESHOLD = 2.0  # 흔들기 강도 임계

# --------------------------------
# 셰이커 위치 세팅
# --------------------------------
base_shaker_pos = pygame.Vector2(SCREEN_WIDTH*0.3, SCREEN_HEIGHT*0.55)
shaker_pos = base_shaker_pos.copy()

shaker_angle = 0.0
SHAKE_ANGLE_MIN = -130
SHAKE_ANGLE_MAX = 30

# 붓기 임계각
POUR_START_ANGLE = -90      # 이 각도부터 따르기 시작
POUR_MAX_ANGLE   = -120     # 이 각도부터 최대 유량

# 흔들기 관련
shake_power = 0.0
shake_timer = 0.0

# 셰이커 구조 정보
shaker_body_orig = shaker_body_img
shaker_body_rect = shaker_body_orig.get_rect(center=shaker_pos)

baseline_y = shaker_pos.y + shaker_body_rect.height*0.5

mouth_offset = pygame.Vector2(0, -shaker_body_rect.height*0.5 + 12)

# 캡 정보
shaker_cap_orig = shaker_cap_img
shaker_cap_rect = shaker_cap_orig.get_rect()

cap_offset = pygame.Vector2(
    0,
    -shaker_body_rect.height*0.5 - shaker_cap_rect.height*0.3
)

cap_side_pos = pygame.Vector2(
    SCREEN_WIDTH*0.45,
    baseline_y - shaker_cap_rect.height*0.5
)

cap_on_top = True

# 잔 위치
glass_rect = glass_img.get_rect()
glass_rect.midbottom = (SCREEN_WIDTH*0.72, baseline_y)

# 액체 전용 서피스(잔 앞에 올릴 거임)
liquid_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

# --------------------------------
# 잔 내부 삼각형
# --------------------------------
def get_glass_triangle():
    gw, gh = glass_rect.width, glass_rect.height

    # 이미지 기준:
    # - 잔 입구: 대략 위에서 0.12~0.18h 정도
    # - V자 바닥: 대략 위에서 0.45~0.5h 정도
    # => top_y, bottom_y를 glass_rect.top 기준으로 잡는 게 핵심
    top_y    = glass_rect.top + gh * 0.18   # 잔 안쪽 림 바로 아래
    bottom_y = glass_rect.top + gh * 0.48   # V자 내부 끝나는 지점

    cx = glass_rect.centerx

    # 내부 폭: 전체 폭의 약 0.66 정도만 사용 (외곽 라인 안쪽)
    half_inner_w = gw * 0.33

    top_left  = (cx - half_inner_w, top_y)
    top_right = (cx + half_inner_w, top_y)
    bottom    = (cx,              bottom_y)

    return {
        "top_left": top_left,
        "top_right": top_right,
        "bottom": bottom,
    }

# --------------------------------
# 용량 / 파티클 설정
# --------------------------------
MAX_SHAKER_VOLUME = 3.0          # 총량 더 크게
shaker_volume = MAX_SHAKER_VOLUME

VOLUME_PER_PARTICLE = 0.003      # 셰이커 소모는 조금 덜
GLASS_FILL_PER_PARTICLE = 0.004  # 잔 채우는 속도는 좀 더 눈에 보이게

class Particle:
    def __init__(self, x, y):
        # "물줄기" 스타일
        self.pos = pygame.Vector2(x + random.uniform(-2, 2), y)
        self.vel = pygame.Vector2(
            random.uniform(-0.1, 0.1),
            random.uniform(2.5, 3.5)
        )
        self.radius = 5
        self.color = (255, 110, 150)

    def update(self):
        self.vel.y += 0.08
        self.pos += self.vel

    def draw(self, surf):
        pygame.draw.circle(
            surf, self.color, (int(self.pos.x), int(self.pos.y)), self.radius
        )

particles = []
spill_particles = []   # 잔이 넘쳐서 떨어지는 입자
splash_particles = []  # 잔에 부딪혀 튕겨나가는 입자

fill_amount = 0.0

# --------------------------------
# Geometry Utils
# --------------------------------
def point_in_triangle(pt, a, b, c):
    (x, y) = pt
    def area(x1, y1, x2, y2, x3, y3):
        return abs((x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2)) / 2.0)

    A  = area(*a, *b, *c)
    A1 = area(x, y, *b, *c)
    A2 = area(*a, x, y, *c)
    A3 = area(*a, *b, x, y)

    return abs((A1 + A2 + A3) - A) < 0.3

def dist_point_to_segment(px, py, ax, ay, bx, by):
    # 점-선분 거리
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    seg_len2 = vx*vx + vy*vy
    if seg_len2 == 0:
        # a == b인 경우 그냥 점 거리
        dx, dy = px - ax, py - ay
        return math.hypot(dx, dy)

    t = (wx*vx + wy*vy) / seg_len2
    t = max(0.0, min(1.0, t))
    proj_x = ax + t*vx
    proj_y = ay + t*vy

    dx, dy = px - proj_x, py - proj_y
    return math.hypot(dx, dy)

def is_near_glass_side(pt, tri, margin=6):
    """잔 내부 삼각형의 좌/우 변에 margin 픽셀 이내로 접근했는지 검사."""
    x, y = pt
    tl = tri["top_left"]
    tr = tri["top_right"]
    bt = tri["bottom"]

    # 좌측 변: top_left -> bottom
    d_left = dist_point_to_segment(x, y, tl[0], tl[1], bt[0], bt[1])
    # 우측 변: top_right -> bottom
    d_right = dist_point_to_segment(x, y, tr[0], tr[1], bt[0], bt[1])

    return (d_left < margin) or (d_right < margin)




def draw_liquid(surf, tri, amount):
    visible = max(0.0, min(1.0, amount))

    tl = pygame.Vector2(tri["top_left"])
    tr = pygame.Vector2(tri["top_right"])
    bt = pygame.Vector2(tri["bottom"])

    current_y = bt.y + (tl.y - bt.y) * visible
    lx = bt.x + (tl.x - bt.x) * visible
    rx = bt.x + (tr.x - bt.x) * visible

    poly = [
        (bt.x, bt.y),
        (lx, current_y),
        (rx, current_y),
    ]

    LIQUID_RGBA = (255, 110, 170, 200)
    pygame.draw.polygon(surf, LIQUID_RGBA, poly)

# --------------------------------
# 메인 루프
# --------------------------------
running = True
mouse_dragging = False
prev_mouse_x = None
prev_mouse_y = None

while running:
    dt = clock.tick(FPS) / 1000.0

    # --------------------------------
    # MODE_SHAKING — 흔들기 단계
    # --------------------------------
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

    # --------------------------------
    # 이벤트 처리
    # --------------------------------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # ------------------------------
        # MODE_SHAKING: 흔들기
        # ------------------------------
        if mode == MODE_SHAKING:

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_dragging = True
                prev_mouse_x = event.pos[0]

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                mouse_dragging = False
                prev_mouse_x = None

                # 흔든 강도가 충분하면 이동 모드로
                if shake_power >= SHAKE_THRESHOLD:
                    mode = MODE_MOVING
                    base_shaker_pos = shaker_pos.copy()

            elif event.type == pygame.MOUSEMOTION and mouse_dragging:
                mx = event.pos[0]
                if prev_mouse_x is not None:
                    dx = mx - prev_mouse_x
                    shake_power += abs(dx) * 0.02
                    prev_mouse_x = mx


        # ------------------------------
        # MODE_MOVING: 잔 위로 이동
        # ------------------------------
        elif mode == MODE_MOVING:

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_dragging = True

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                mouse_dragging = False

                # 손 떼면 붓기 단계로 전환
                mode = MODE_POURING
                cap_on_top = False

            elif event.type == pygame.MOUSEMOTION and mouse_dragging:
                mx, my = event.pos
                shaker_pos.x = mx
                shaker_pos.y = my


        # ------------------------------
        # MODE_POURING: 각도 조절
        # ------------------------------
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


    # --------------------------------
    # 셰이커 회전 및 입구 위치 계산
    # --------------------------------
    rotated_body = pygame.transform.rotozoom(shaker_body_orig,
                                             shaker_angle, 1.0)
    body_rect = rotated_body.get_rect(center=shaker_pos)

    rotated_mouth_offset = mouth_offset.rotate(-shaker_angle)
    mouth_pos = shaker_pos + rotated_mouth_offset

    # --------------------------------
    # 붓기: 각도 기반 유량 계산
    # --------------------------------
    num_stream = 0  # splash 판정에 필요하므로 먼저 선언

    if mode == MODE_POURING and shaker_volume > 0:
        if shaker_angle <= POUR_START_ANGLE:
            over = min(1.0, max(0.0,
                (abs(shaker_angle) - abs(POUR_START_ANGLE))
                /
                (abs(POUR_MAX_ANGLE) - abs(POUR_START_ANGLE))
            ))

            base_stream = 1
            extra_stream = int(4 * over)
            num_stream = base_stream + extra_stream

            for _ in range(num_stream):
                if shaker_volume <= 0:
                    break
                particles.append(Particle(mouth_pos.x, mouth_pos.y))
                shaker_volume = max(0.0, shaker_volume - VOLUME_PER_PARTICLE)


    # --------------------------------
    # 파티클 업데이트 + 충돌 처리
    # --------------------------------
    tri = get_glass_triangle()
    a, b, c = tri["top_left"], tri["top_right"], tri["bottom"]
    # 잔 왼쪽/오른쪽 벽을 OBB로 생성
    left_obb, right_obb = create_wall_obbs_from_triangle(tri, thickness=8.0)

    for p in particles[:]:
        p.update()

        if p.pos.y > SCREEN_HEIGHT + 50:
            particles.remove(p)
            continue

        inside = point_in_triangle((p.pos.x, p.pos.y), a, b, c)
        hit_left = point_in_obb(p.pos.x, p.pos.y, left_obb)
        hit_right = point_in_obb(p.pos.x, p.pos.y, right_obb)
        side_hit = hit_left or hit_right

        # 1) 잔 안쪽 삼각형에 들어온 경우: 속도 상관없이 "주로 채워진다"
        if inside:
            if fill_amount < 1.0:
                fill_amount += GLASS_FILL_PER_PARTICLE
            else:
                # 이미 꽉 찼으면 밖으로 흘러내리는 spill로
                spill_particles.append(Particle(p.pos.x, p.pos.y))

            particles.remove(p)
            continue

        # 2) 잔 옆면(OBB)에 맞은 경우: 여기서만 splash / spill 판정
        if side_hit:
            # splash 조건은 좀 더 빡세게 (속도 더 커야 튀김)
            splash_condition = (
                p.vel.y > 6.0 or       # 속도 임계 ↑
                num_stream >= 4        # 콸콸 붓고 있을 때
            )

            if splash_condition:
                # 벽에 세게 부딪혀 위로 튀는 splash
                splash = Particle(p.pos.x, p.pos.y)
                splash.vel.y = -random.uniform(2.0, 4.0)
                splash.vel.x = random.uniform(-2.0, 2.0)
                splash_particles.append(splash)
            else:
                # 속도가 그렇게 크진 않으면, 벽을 타고 흘러내리는 spill
                spill = Particle(p.pos.x, p.pos.y)
                spill.vel.x += random.uniform(-0.3, 0.3)
                spill_particles.append(spill)

            particles.remove(p)
            continue



    #  overflow fall
    for s in spill_particles[:]:
        s.update()
        if s.pos.y > SCREEN_HEIGHT + 50:
            spill_particles.remove(s)

    # splash upward motion
    for sp in splash_particles[:]:
        sp.update()
        if sp.pos.y > SCREEN_HEIGHT + 50:
            splash_particles.remove(sp)


    # --------------------------------
    # 렌더링
    # --------------------------------
    screen.blit(background_img, (0, 0))

    # 액체 레이어 초기화
    liquid_surface.fill((0, 0, 0, 0))
    draw_liquid(liquid_surface, tri, fill_amount)

    # 잔 → 액체 → 셰이커 순서
    screen.blit(glass_img, glass_rect)
    screen.blit(liquid_surface, (0, 0))

    # 셰이커 바디
    screen.blit(rotated_body, body_rect)

    # 셰이커 캡
    if cap_on_top:
        rotated_cap = pygame.transform.rotozoom(shaker_cap_orig,
                                                shaker_angle, 1.0)
        rotated_cap_offset = cap_offset.rotate(-shaker_angle)
        cap_center = shaker_pos + rotated_cap_offset
        cap_rect = rotated_cap.get_rect(center=cap_center)
        screen.blit(rotated_cap, cap_rect)
    else:
        cap_rect = shaker_cap_orig.get_rect(center=cap_side_pos)
        screen.blit(shaker_cap_orig, cap_rect)

    # 파티클들 모두 그림
    for p in particles:
        p.draw(screen)
    for s in spill_particles:
        s.draw(screen)
    for sp in splash_particles:
        sp.draw(screen)

    pygame.display.flip()

pygame.quit()
