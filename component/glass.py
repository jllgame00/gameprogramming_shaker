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
    셰이커에서 나온 used_volume으로
    물줄기 경로와 잔 내부 채움을 담당하는 컴포넌트.
    """

    def __init__(self, glass_img, screen_width, screen_height, baseline_y):
        self.img = glass_img
        self.rect = self.img.get_rect()
        self.rect.midbottom = (screen_width * 0.72, baseline_y)

        tri = get_glass_triangle(self.rect)
        self.tl = pygame.Vector2(tri["top_left"])
        self.tr = pygame.Vector2(tri["top_right"])
        self.b = pygame.Vector2(tri["bottom"])

        # 바닥 히트 지점 살짝 위로
        BOTTOM_RAISE = 8
        self.b.y -= BOTTOM_RAISE

        # 0.0 ~ 1.0
        self.fill_amount = 0.0

        # 리퀴드 + 물줄기 레이어
        self.liquid_surface = pygame.Surface(
            (screen_width, screen_height), pygame.SRCALPHA
        )

        self.stream_points = []
        self.stream_time = 0.0
        self.base_curve_strength = 6.0
        self.last_pour_factor = 0.0

    def update_stream(
        self,
        dt: float,
        is_pouring: bool,
        mouth_pos: pygame.Vector2,
        pour_factor: float,
        used_volume: float,
    ):
        """
        dt, 붓기 상태, 셰이커 입구 위치, 기울기, 사용된 부피를 받아
        물줄기 polyline과 잔 내부 fill_amount를 갱신.
        """
        self.stream_time += dt
        self.last_pour_factor = pour_factor
        self.stream_points = []

        if not is_pouring or used_volume <= 0.0:
            return

        # 입구에서 수직 아래 레이
        ray_start = pygame.Vector2(mouth_pos)
        ray_dir = pygame.Vector2(0, 1)

        # 잔 벽과의 교차 지점
        hit_point, hit_side = self._ray_hit_wall(ray_start, ray_dir)

        if hit_point is None:
            # 잔 안에 안 맞음 → 바닥으로 그냥 떨어짐
            self._build_stream(ray_start, pour_factor)
            hit_glass = False
        else:
            # 잔 안쪽 벽 맞음 → 유입
            self._build_falling_and_sliding_stream(
                ray_start, hit_point, hit_side, pour_factor
            )
            hit_glass = True

        # 여기서부터가 핵심: “충돌 기반 유입”
        if hit_glass:
            delta_fill = used_volume / GLASS_CAPACITY
            self.fill_amount += delta_fill
            self.fill_amount = max(0.0, min(1.0, self.fill_amount))

    # -------- 물줄기 경로 생성 --------
    def _build_stream(self, ray_start, pour_factor):
        length = 150
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

    def _build_falling_and_sliding_stream(
        self,
        ray_start: pygame.Vector2,
        hit_point: pygame.Vector2,
        hit_side: str,
        pour_factor: float,
    ):
        f = max(0.0, min(1.0, self.fill_amount))

        num_fall_samples = 6
        wiggle_amp = STREAM_WIGGLE_AMP + STREAM_WIGGLE_AMP_EXTRA * pour_factor
        points = []

        # falling: 입구 → 충돌 지점
        for i in range(num_fall_samples + 1):
            t = i / num_fall_samples
            base = ray_start.lerp(hit_point, t)

            phase = self.stream_time * STREAM_WIGGLE_FREQ + t * math.pi * 2.0
            offset_x = math.sin(phase) * wiggle_amp

            p = pygame.Vector2(base.x + offset_x, base.y)
            points.append((p.x, p.y))

        # sliding: 충돌 지점 → 현재 수면이 벽과 만나는 지점
        left_surface = self.b.lerp(self.tl, f)
        right_surface = self.b.lerp(self.tr, f)

        if hit_side == "left":
            wall_start = self.tl
            surface_target = left_surface
        else:
            wall_start = self.tr
            surface_target = right_surface

        wall_end = surface_target

        wall_dir = (self.b - wall_start)
        if wall_dir.length_squared() > 0:
            normal = pygame.Vector2(-wall_dir.y, wall_dir.x).normalize()
        else:
            normal = pygame.Vector2(1, 0)

        num_slide_samples = 6
        slide_amp = wiggle_amp * 0.5

        for i in range(1, num_slide_samples + 1):
            t = i / num_slide_samples
            base = hit_point.lerp(wall_end, t)

            phase = self.stream_time * STREAM_WIGGLE_FREQ + t * math.pi * 2.0
            offset = normal * (math.sin(phase) * slide_amp)

            p = base + offset
            points.append((p.x, p.y))

        self.stream_points = points

    # -------- 레이 vs 잔 벽 충돌 --------
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

        qp = q - p
        t = qp.cross(s) / rxs
        u = qp.cross(r) / rxs

        if 0.0 <= u <= 1.0 and t >= 0.0:
            hit_point = p + r * t
            return hit_point, t
        return None

    def _draw_stream(self, surface: pygame.Surface):
        if len(self.stream_points) < 2:
            return

        f = max(0.0, min(1.0, self.last_pour_factor))
        width = int(STREAM_BASE_WIDTH + STREAM_EXTRA_WIDTH * f)
        color = (255, 200, 220, 230)

        pygame.draw.lines(
            surface,
            color,
            False,
            self.stream_points,
            width,
        )

    # -------- 렌더 --------
    def draw(self, screen: pygame.Surface):
        self.liquid_surface.fill((0, 0, 0, 0))

        # 물줄기 → 잔 내부 리퀴드 순서
        if len(self.stream_points) >= 2:
            self._draw_stream(self.liquid_surface)

        self._draw_liquid_polygon(self.liquid_surface)

        screen.blit(self.img, self.rect)
        screen.blit(self.liquid_surface, (0, 0))

    # -------- 잔 내부 리퀴드 폴리곤 --------
    def _draw_liquid_polygon(self, surface: pygame.Surface):
        f = max(0.0, min(1.0, self.fill_amount))
        if f <= 0.0:
            return

        tl = self.tl
        tr = self.tr
        b = self.b

        # 윗면 곡선
        NUM_TOP_SAMPLES = 10
        left_base = b.lerp(tl, f)
        right_base = b.lerp(tr, f)

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

        # 바닥 곡선
        bottom_fill = min(f, 0.30)
        left_bottom_base = b.lerp(tl, bottom_fill)
        right_bottom_base = b.lerp(tr, bottom_fill)

        ROUND_STRENGTH = 2.0
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

        poly = top_curve + list(reversed(bottom_curve))
        LIQUID_COLOR = (255, 200, 220, 230)
        pygame.draw.polygon(surface, LIQUID_COLOR, poly)
