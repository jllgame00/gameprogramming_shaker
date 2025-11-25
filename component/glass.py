# component/glass.py
import pygame
import math

from component.config import (
    GLASS_CAPACITY,
    STREAM_BASE_WIDTH,
    STREAM_EXTRA_WIDTH,
    STREAM_WIGGLE_AMP,
    STREAM_WIGGLE_AMP_EXTRA,
    STREAM_WIGGLE_FREQ,
)
from component.geometry import get_glass_triangle


class Glass:
    """
    - 셰이커 입구 위치 + 붓는 세기 + 사용된 부피로
      물줄기(곡선 polyline) + 잔 내부 채움(fill_amount)을 처리.
    - 물줄기는 잔 바닥까지 보여도 괜찮다는 전제로, 표면 클리핑 없음.
    - 히트박스 = 잔 안쪽 벽 2개(대각선) + 바닥점(조금 위로 올림).
    """

    def __init__(self, glass_img, screen_width, screen_height, baseline_y):
        self.img = glass_img
        self.rect = self.img.get_rect()
        # 셰이커 바닥 y에 맞춰 midbottom 정렬
        self.rect.midbottom = (screen_width * 0.72, baseline_y)

        # 내부 삼각형 (위 두 점, 아래 한 점)
        self.tri = get_glass_triangle(self.rect)
        self.tl = pygame.Vector2(self.tri["top_left"])
        self.tr = pygame.Vector2(self.tri["top_right"])
        self.b = pygame.Vector2(self.tri["bottom"])

        # 잔 바닥 hitbox를 약간 위로 올림 (스프라이트 뾰족한 끝은 제외)
        BOTTOM_RAISE = 8
        self.b.y -= BOTTOM_RAISE
        self.tri["bottom"] = (self.b.x, self.b.y)

        # 현재 잔 채움 정도 (0.0 ~ 1.0)
        self.fill_amount = 0.0

        # 리퀴드/물줄기 그릴 surface
        self.liquid_surface = pygame.Surface(
            (screen_width, screen_height), pygame.SRCALPHA
        )

        # 물줄기 polyline 포인트
        self.stream_points = []

        # 시간값 (wiggle용)
        self.stream_time = 0.0

        # 윗면 곡률 파라미터
        self.base_curve_strength = 6.0

        # 최근 붓기 세기(두께 계산용)
        self.last_pour_factor = 0.0

    # -------------------------------------------------
    # 외부에서 매 프레임 호출:
    #   dt          : delta time
    #   is_pouring  : 지금 실제로 붓는 중인지
    #   mouth_pos   : 셰이커 입구 위치 (world coords)
    #   pour_factor : 0~1, 얼마나 많이 기울였는지
    #   used_volume : 이 프레임 동안 셰이커에서 실제로 빠진 양
    # -------------------------------------------------
    def update_stream(self, dt, is_pouring, mouth_pos: pygame.Vector2,
                      pour_factor: float, used_volume: float):
        # 시간 업데이트 (wiggle용)
        self.stream_time += dt
        self.last_pour_factor = pour_factor

        # 직전 프레임 물줄기 초기화
        self.stream_points = []

        # 실제로 아무것도 안 부었으면 물줄기 없음
        if not is_pouring or used_volume <= 0.0:
            return

        # 1) 입구에서 수직 아래로 레이
        ray_start = pygame.Vector2(mouth_pos)
        ray_dir = pygame.Vector2(0, 1)  # 아래 방향

        # 2) 잔 왼/오 벽 (tl~b, tr~b)과 교점 찾기
        hit_point, hit_side = self._ray_hit_wall(ray_start, ray_dir)

        # 컵을 안 맞고 그냥 떨어지는 경우
        if hit_point is None:
            self._build_falling_only_stream(ray_start, pour_factor)
        else:
            # 컵 벽 맞으면: falling + sliding (바닥까지)
            self._build_falling_and_sliding_stream(
                ray_start, hit_point, hit_side, pour_factor
            )

        # 3) used_volume 기반으로 잔 채우기 (양 일치)
        delta_fill = used_volume / GLASS_CAPACITY
        self.fill_amount += delta_fill
        self.fill_amount = max(0.0, min(1.0, self.fill_amount))

    # -------------------------------------------------
    # 컵 안 안 맞고 그냥 떨어지는 경우
    # -------------------------------------------------
    def _build_falling_only_stream(self, ray_start, pour_factor):
        length = 150  # 최대 길이
        num_samples = 8

        wiggle_amp = STREAM_WIGGLE_AMP + STREAM_WIGGLE_AMP_EXTRA * pour_factor

        points = []
        for i in range(num_samples + 1):
            t = i / num_samples
            base = ray_start + pygame.Vector2(0, length * t)

            phase = self.stream_time * STREAM_WIGGLE_FREQ + t * math.pi * 2.0
            offset_x = math.sin(phase) * wiggle_amp

            p = pygame.Vector2(base.x + offset_x, base.y)
            points.append((p.x, p.y))

        self.stream_points = points

    # -------------------------------------------------
    # 컵 벽 맞고 흐르는 경우: falling + sliding (바닥까지 허용)
    # -------------------------------------------------
    def _build_falling_and_sliding_stream(self, ray_start, hit_point, hit_side,
                                          pour_factor):
        # 현재 잔 채움 정도
        f = max(0.0, min(1.0, self.fill_amount))

        # falling 구간 설정
        num_fall_samples = 6
        wiggle_amp = STREAM_WIGGLE_AMP + STREAM_WIGGLE_AMP_EXTRA * pour_factor

        points = []

        # 1) falling: ray_start → hit_point
        for i in range(num_fall_samples + 1):
            t = i / num_fall_samples
            base = ray_start.lerp(hit_point, t)

            phase = self.stream_time * STREAM_WIGGLE_FREQ + t * math.pi * 2.0
            offset_x = math.sin(phase) * wiggle_amp

            p = pygame.Vector2(base.x + offset_x, base.y)
            points.append((p.x, p.y))

        # ---------------------------
        # 2) sliding: hit_point → "현재 수면이 벽과 만나는 지점"까지
        # ---------------------------
        # 수면이 왼/오 벽과 만나는 지점
        left_surface  = self.b.lerp(self.tl, f)
        right_surface = self.b.lerp(self.tr, f)

        if hit_side == "left":
            wall_start = self.tl
            surface_target = left_surface
        else:
            wall_start = self.tr
            surface_target = right_surface

        # 만약 이미 수면이 hit_point보다 위에 있으면
        # → 벽 타고 내려갈 구간이 없으니 바로 수면 근처로만 연결
        # (시각적으로는 거의 바로 표면에 합류하는 느낌)
        if surface_target.y <= hit_point.y:
            # 그냥 hit_point에서 surface_target까지 짧게만 lerp
            wall_end = surface_target
        else:
            # 수면이 더 아래에 있으면, 그 지점까지 슬라이딩
            wall_end = surface_target

        # 벽 방향 (normal 계산용)
        wall_dir = (self.b - wall_start)
        if wall_dir.length_squared() > 0:
            normal = pygame.Vector2(-wall_dir.y, wall_dir.x).normalize()
        else:
            normal = pygame.Vector2(1, 0)

        num_slide_samples = 6
        slide_amp = wiggle_amp * 0.5  # 벽 타고 흐를 땐 더 얌전하게

        # hit_point → wall_end (보통 수면 근처)까지
        for i in range(1, num_slide_samples + 1):
            t = i / num_slide_samples
            base = hit_point.lerp(wall_end, t)

            phase = self.stream_time * STREAM_WIGGLE_FREQ + t * math.pi * 2.0
            offset = normal * (math.sin(phase) * slide_amp)

            p = base + offset
            points.append((p.x, p.y))

        self.stream_points = points


    # -------------------------------------------------
    # 레이(입구→아래)가 잔 벽과 어디서 만나는지 계산
    # -------------------------------------------------
    def _ray_hit_wall(self, ray_start: pygame.Vector2, ray_dir: pygame.Vector2):
        hit_candidates = []

        left_hit = self._segment_intersection(ray_start, ray_dir, self.tl, self.b)
        if left_hit is not None:
            hit_p, t_ray = left_hit
            if t_ray >= 0:
                hit_candidates.append((t_ray, hit_p, "left"))

        right_hit = self._segment_intersection(ray_start, ray_dir, self.tr, self.b)
        if right_hit is not None:
            hit_p, t_ray = right_hit
            if t_ray >= 0:
                hit_candidates.append((t_ray, hit_p, "right"))

        if not hit_candidates:
            return None, None

        hit_candidates.sort(key=lambda item: item[0])
        _, hit_point, side = hit_candidates[0]
        return hit_point, side

    def _segment_intersection(self, ray_start, ray_dir, seg_a, seg_b):
        p = ray_start
        r = ray_dir
        q = seg_a
        s = (seg_b - seg_a)

        rxs = r.cross(s)
        if abs(rxs) < 1e-6:
            return None  # 평행

        qp = q - p
        t = qp.cross(s) / rxs
        u = qp.cross(r) / rxs

        if 0.0 <= u <= 1.0 and t >= 0.0:
            hit_point = p + r * t
            return hit_point, t
        return None

    # -------------------------------------------------
    # 렌더
    # -------------------------------------------------
    def draw(self, screen: pygame.Surface):
        # 액체 surface 초기화
        self.liquid_surface.fill((0, 0, 0, 0))

        # 잔 내부 채워진 액체
        self._draw_liquid_polygon(self.liquid_surface)

        # --- 물줄기 라인 (곡선 polyline) ---
        if len(self.stream_points) >= 2:
            # 기울일수록 조금 더 두꺼워지게
            f = max(0.0, min(1.0, self.last_pour_factor))
            width = int(
                STREAM_BASE_WIDTH + STREAM_EXTRA_WIDTH * f
            )

            pygame.draw.lines(
                self.liquid_surface,
                (255, 200, 220, 230),
                False,
                self.stream_points,
                width
            )

        # 잔 → 액체+물줄기 순으로 렌더
        screen.blit(self.img, self.rect)
        screen.blit(self.liquid_surface, (0, 0))

    # -------------------------------------------------
    # 내부: 곡선 윗면 + 라운드 바닥 리퀴드 렌더
    # -------------------------------------------------
    def _draw_liquid_polygon(self, surface: pygame.Surface):
        f = max(0.0, min(1.0, self.fill_amount))
        if f <= 0.0:
            return

        tl = self.tl
        tr = self.tr
        b = self.b

        # ----- 곡선 윗면 -----
        NUM_TOP_SAMPLES = 10
        left_base = b.lerp(tl, f)
        right_base = b.lerp(tr, f)

        # 곡률 세기
        curve_strength = self.base_curve_strength * (1.0 - 0.6 * f)
        rim_y = min(tl.y, tr.y)

        top_curve = []
        for i in range(NUM_TOP_SAMPLES + 1):
            t = i / NUM_TOP_SAMPLES
            base_x = left_base.x + (right_base.x - left_base.x) * t
            base_y = left_base.y + (right_base.y - left_base.y) * t

            bulge = math.sin(t * math.pi) * curve_strength
            y = base_y + bulge
            if y < rim_y:
                y = rim_y

            top_curve.append((base_x, y))

        # ----- 라운드 바닥 -----
        bottom_fill = min(f, 0.30)

        left_bottom_base = b.lerp(tl, bottom_fill)
        right_bottom_base = b.lerp(tr, bottom_fill)

        ROUND_STRENGTH = 2.0  # 네가 골라준 값
        control = pygame.Vector2(b.x, b.y - ROUND_STRENGTH)

        bottom_curve = []
        NUM_BOTTOM_SAMPLES = 12
        for i in range(NUM_BOTTOM_SAMPLES + 1):
            u = i / NUM_BOTTOM_SAMPLES
            one_u = 1.0 - u

            bx = (one_u * one_u) * left_bottom_base.x \
                 + 2.0 * one_u * u * control.x \
                 + (u * u) * right_bottom_base.x
            by = (one_u * one_u) * left_bottom_base.y \
                 + 2.0 * one_u * u * control.y \
                 + (u * u) * right_bottom_base.y

            if by > b.y:
                by = b.y

            bottom_curve.append((bx, by))

        # 최종 폴리곤: 윗면(좌→우) + 바닥(U자, 우→좌)
        poly = top_curve + list(reversed(bottom_curve))

        LIQUID_COLOR = (255, 200, 220, 230)
        pygame.draw.polygon(surface, LIQUID_COLOR, poly)
