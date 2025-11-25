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
    라인 기반 리퀴드 버전:
    - 파티클 대신, 셰이커 입구 위치 + 붓는 세기 + 사용된 부피로
      물줄기(곡선 선분들) + 잔 내부 채움(fill_amount)을 처리.
    - 히트박스 = 잔 안쪽 벽 2개(대각선) + 바닥 점.
    """

    def __init__(self, glass_img, screen_width, screen_height, baseline_y):
        self.img = glass_img
        self.rect = self.img.get_rect()
        # 셰이커 바닥 y에 맞춰 midbottom 정렬
        self.rect.midbottom = (screen_width * 0.72, baseline_y)

        # 내부 삼각형
        self.tri = get_glass_triangle(self.rect)
        self.tl = pygame.Vector2(self.tri["top_left"])
        self.tr = pygame.Vector2(self.tri["top_right"])
        self.b  = pygame.Vector2(self.tri["bottom"])

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

        # 직전 프레임 물줄기 초기화
        self.stream_points = []

        # 실제로 아무것도 안 부었으면 물줄기 없음
        if not is_pouring or used_volume <= 0.0:
            return

        # 1) mouth_pos에서 수직 아래로 레이 쏨
        ray_start = pygame.Vector2(mouth_pos)
        ray_dir = pygame.Vector2(0, 1)  # 아래 방향

        # 2) 잔 왼/오 벽 (tl~b, tr~b)과 교점 찾기
        hit_point, hit_side = self._ray_hit_wall(ray_start, ray_dir)

        # 유리컵을 안 맞고 그냥 떨어진 경우: 공중 물줄기만
        if hit_point is None:
            self._build_falling_only_stream(ray_start, ray_dir, pour_factor)
        else:
            # 유리 벽 맞으면:
            # (1) falling 구간: mouth → hit
            # (2) sliding 구간: hit → b (벽 따라 아래로)
            self._build_falling_and_sliding_stream(ray_start, hit_point,
                                                   hit_side, pour_factor)

        # 3) used_volume 기반으로 잔 채우기
        delta_fill = used_volume / GLASS_CAPACITY
        self.fill_amount += delta_fill
        self.fill_amount = max(0.0, min(1.0, self.fill_amount))

    # -------------------------------------------------
    # falling-only stream: 컵 안 맞고 그냥 떨어지는 경우
    # -------------------------------------------------
    def _build_falling_only_stream(self, ray_start, ray_dir, pour_factor):
        length = 200  # 대충 아래로 200px 정도
        num_samples = 8

        wiggle_amp = STREAM_WIGGLE_AMP + STREAM_WIGGLE_AMP_EXTRA * pour_factor

        points = []
        for i in range(num_samples + 1):
            t = i / num_samples
            base = ray_start + ray_dir * (length * t)

            # x방향으로 sinusoidal wiggle
            phase = self.stream_time * STREAM_WIGGLE_FREQ + t * math.pi * 2.0
            offset_x = math.sin(phase) * wiggle_amp

            p = pygame.Vector2(base.x + offset_x, base.y)
            points.append((p.x, p.y))

        self.stream_points = points

    # -------------------------------------------------
    # falling + sliding stream: 컵 벽 맞고 흐르는 경우
    # -------------------------------------------------
    def _build_falling_and_sliding_stream(self, ray_start, hit_point, hit_side,
                                          pour_factor):
        # falling 구간 길이
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

        # 2) sliding: hit_point → b (해당 벽 쪽)
        if hit_side == "left":
            wall_start = self.tl
            wall_end = self.b
        else:
            wall_start = self.tr
            wall_end = self.b

        # hit_point 에서 시작해서 wall_end까지
        num_slide_samples = 6
        wall_dir = (wall_end - wall_start)
        # 벽에 수직인 방향(흘러내리면서 약간 안팎으로 흔들리게)
        if wall_dir.length_squared() > 0:
            normal = pygame.Vector2(-wall_dir.y, wall_dir.x).normalize()
        else:
            normal = pygame.Vector2(1, 0)

        slide_amp = wiggle_amp * 0.5  # 벽 타고 흐를 땐 약간 적게

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

        # 물줄기 라인 (곡선 polyline)
        if len(self.stream_points) >= 2:
            # 기울일수록 더 두꺼운 물줄기
            # 여기서는 wiggle에서 쓰는 pour_factor를 알 수 없으니까
            # 대략 fill_amount 기반으로 살짝 스케일해도 되고,
            # 또는 width는 Glass에 멤버로 저장해도 됨.
            # 간단하게: 중간 정도 두께 고정 + 나중에 필요하면 조정
            # → 대신 width 계산을 update_stream 안에서 하도록 바꾸는 게 더 깔끔한데
            # 지금은 BASE + EXTRA * 현재 채움 정도로 대충 감성 조정
            width = int(STREAM_BASE_WIDTH + STREAM_EXTRA_WIDTH * 0.5)

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
    # 내부: 단순 삼각형 리퀴드 렌더
    # -------------------------------------------------
    def _draw_liquid_polygon(self, surface: pygame.Surface):
        f = max(0.0, min(1.0, self.fill_amount))
        if f <= 0.0:
            return

        tl = self.tl
        tr = self.tr
        b  = self.b

        left_pt  = b.lerp(tl, f)
        right_pt = b.lerp(tr, f)

        poly = [
            (left_pt.x,  left_pt.y),
            (right_pt.x, right_pt.y),
            (b.x,        b.y),
        ]

        LIQUID_COLOR = (255, 110, 170, 200)
        pygame.draw.polygon(surface, LIQUID_COLOR, poly)
