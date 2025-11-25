# component/glass.py
import pygame
import math

from component.config import (
    GLASS_CAPACITY,
)
from component.geometry import get_glass_triangle


class Glass:
    """
    라인 기반 리퀴드 버전:
    - 파티클 안 쓰고, 셰이커 입구 위치 + 붓기 세기만으로
      물줄기(연속된 선) + 잔 내부 채움(fill_amount)을 처리.
    - 히트박스 = 잔 안쪽 벽 2개(대각선) + 바닥 점.
    """

    def __init__(self, glass_img, screen_width, screen_height, baseline_y):
        self.img = glass_img
        self.rect = self.img.get_rect()
        # 셰이커 바닥 y에 맞춰 midbottom 정렬
        self.rect.midbottom = (screen_width * 0.72, baseline_y)

        # 내부 삼각형 (위 두 점, 아래 한 점)
        self.tri = get_glass_triangle(self.rect)

        # 편하게 벡터로
        self.tl = pygame.Vector2(self.tri["top_left"])
        self.tr = pygame.Vector2(self.tri["top_right"])
        self.b  = pygame.Vector2(self.tri["bottom"])

        # 현재 잔 채움 정도 (0.0 ~ 1.0)
        self.fill_amount = 0.0

        # 리퀴드/물줄기 그릴 surface
        self.liquid_surface = pygame.Surface(
            (screen_width, screen_height), pygame.SRCALPHA
        )

        # 최근 프레임에서 계산된 물줄기 라인 (시각용)
        self.stream_points = []  # [(x, y), (x, y), ...]

    # -------------------------------------------------
    # 외부에서 매 프레임 호출:
    #   is_pouring: 지금 따르는 중인지
    #   mouth_pos : 셰이커 입구 위치
    #   pour_factor: 0~1, 얼마나 세게 붓는지
    # -------------------------------------------------
    def update_stream(self, dt, is_pouring, mouth_pos: pygame.Vector2, pour_factor: float):
        # 물줄기 포인트 초기화
        self.stream_points = []

        if not is_pouring:
            # 안 붓는 중이면 물줄기 없음
            return

        # 1) mouth_pos에서 수직 아래로 레이 쏨
        ray_start = pygame.Vector2(mouth_pos)
        ray_dir = pygame.Vector2(0, 1)  # 아래 방향

        # 2) 잔 왼/오 벽 (tl~b, tr~b)과 교점 찾기
        hit_point, hit_side = self._ray_hit_wall(ray_start, ray_dir)

        if hit_point is None:
            # 유리컵을 안 맞고 그냥 떨어진 경우 → 물줄기만 그리고 끝
            # (원하면 여기서 바닥에 튀는 연출 나중에 추가 가능)
            self.stream_points = [
                (ray_start.x, ray_start.y),
                (ray_start.x, ray_start.y + 200),
            ]
            return

        # 3) 물줄기 라인 포인트 구성
        #    (mouth → hit) + (hit → 바닥 방향으로 벽 타고 흐름)
        #    실제 바닥까지 다 그리면 너무 길면 감성에 맞게 중간까지만 그려도 됨.
        wall_end = self.b  # 바닥 점

        # 떨어지는 부분
        self.stream_points.append((ray_start.x, ray_start.y))
        self.stream_points.append((hit_point.x, hit_point.y))

        # 벽 타고 흐르는 부분: hit_point → wall_end
        SEGMENTS = 6
        for i in range(1, SEGMENTS + 1):
            t = i / SEGMENTS
            p = hit_point.lerp(wall_end, t)
            self.stream_points.append((p.x, p.y))

        # 4) 잔 채우기: 부은 세기 * 시간 = 부피
        #    pour_factor(0~1), GLASS_CAPACITY 기준으로 적당히 스케일
        #    → 일단 감성용 계수 0.25 정도 곱해보자
        FILL_SPEED = 0.25
        delta_fill = (pour_factor * dt * FILL_SPEED)
        self.fill_amount += delta_fill
        self.fill_amount = max(0.0, min(1.0, self.fill_amount))

    # -------------------------------------------------
    # 레이(입구→아래)가 잔 벽과 어디서 만나는지 계산
    # -------------------------------------------------
    def _ray_hit_wall(self, ray_start: pygame.Vector2, ray_dir: pygame.Vector2):
        # 벽 두 개: 왼쪽(tl~b), 오른쪽(tr~b)
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

        # 가장 가까운 교점 선택
        hit_candidates.sort(key=lambda item: item[0])
        _, hit_point, side = hit_candidates[0]
        return hit_point, side

    def _segment_intersection(self, ray_start, ray_dir, seg_a, seg_b):
        """
        2D에서
        - ray: P = ray_start + t * ray_dir
        - segment: Q = seg_a + u * (seg_b - seg_a), u in [0,1]
        교점 (t, u)를 구한 뒤, u in [0,1]일 때만 유효.
        반환: (hit_point, t_ray) 또는 None
        """
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

        # 물줄기 라인
        if len(self.stream_points) >= 2:
            pygame.draw.lines(
                self.liquid_surface,
                (255, 200, 220, 230),  # 약간 밝은 핑크
                False,
                self.stream_points,
                2
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
