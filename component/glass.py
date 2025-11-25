# glass.py
import pygame
import random
import math

from component.config import GLASS_FILL_PER_PARTICLE
from component.geometry import get_glass_triangle, point_in_triangle
from component.obb import create_wall_obbs_from_triangle, point_in_obb
from component.particles import Particle


class Glass:
    def __init__(self, glass_img, screen_width, screen_height, baseline_y):
        self.img = glass_img
        self.rect = self.img.get_rect()
        # 셰이커 바닥 y에 맞춰 세팅
        self.rect.midbottom = (screen_width * 0.72, baseline_y)

        # 내부 hitbox(역삼각형)
        self.tri = get_glass_triangle(self.rect)
        self.left_obb, self.right_obb = create_wall_obbs_from_triangle(self.tri)

        # 잔 안에 채워진 양(논리)
        self.fill_amount = 0.0

        # overflow / splash용 파티클
        self.spill_particles = []
        self.splash_particles = []

        # 액체 렌더링용 surface
        self.liquid_surface = pygame.Surface(
            (screen_width, screen_height), pygame.SRCALPHA
        )

    # -------------------------------------------------
    # 업데이트: 메인 파티클 리스트와 상호작용
    # -------------------------------------------------
    def update(self, particles, dt):
        a = self.tri["top_left"]
        b = self.tri["top_right"]
        c = self.tri["bottom"]

        # 메인 낙하 파티클 처리
        for p in particles[:]:
            p.update()

            if p.pos.y > self.rect.bottom + 200:
                particles.remove(p)
                continue

            inside = point_in_triangle((p.pos.x, p.pos.y), a, b, c)
            hit_left = point_in_obb(p.pos.x, p.pos.y, self.left_obb)
            hit_right = point_in_obb(p.pos.x, p.pos.y, self.right_obb)
            side_hit = hit_left or hit_right

            # 1) 잔 내부로 잘 들어온 경우 → 잔 채우기
            if inside:
                self.fill_amount += GLASS_FILL_PER_PARTICLE
                particles.remove(p)
                continue

            # 2) 잔 옆면(OBB)에 맞은 경우 → spill / splash
            if side_hit:
                # 속도가 빠르면 튀기고, 아니면 옆으로 흘러내리게
                speed = p.vel.length()
                if speed > 4.5:
                    sp = Particle(p.pos.x, p.pos.y)
                    sp.vel.y = -random.uniform(2.0, 4.0)
                    sp.vel.x = random.uniform(-2.0, 2.0)
                    self.splash_particles.append(sp)
                else:
                    sp = Particle(p.pos.x, p.pos.y)
                    sp.vel.x += random.uniform(-0.4, 0.4)
                    self.spill_particles.append(sp)

                particles.remove(p)
                continue

        # spill/splash 업데이트
        for sp in self.spill_particles[:]:
            sp.update()
            if sp.pos.y > self.rect.bottom + 200:
                self.spill_particles.remove(sp)

        for sp in self.splash_particles[:]:
            sp.update()
            if sp.pos.y > self.rect.bottom + 200:
                self.splash_particles.remove(sp)

    # -------------------------------------------------
    # 렌더: 잔 안 액체 + 파티클
    # -------------------------------------------------
    def draw(self, screen):
        # 액체 레이어 초기화
        self.liquid_surface.fill((0, 0, 0, 0))

        # 곡선 리퀴드 폴리곤 그리기
        self._draw_liquid_polygon(self.liquid_surface)

        # 잔 → 액체 순으로 렌더
        screen.blit(self.img, self.rect)
        screen.blit(self.liquid_surface, (0, 0))


    # -------------------------------------------------
    # 내부: 액체 삼각형 렌더
    # -------------------------------------------------
    def _draw_liquid_polygon(self, surface: pygame.Surface):
        """
        곡선 리퀴드 폴리곤을 self.fill_amount에 맞게 그린다.
        surface: 보통 self.liquid_surface 를 넣어서 사용.
        """
        poly = self._build_liquid_polygon()
        if not poly:
            return

        LIQUID_COLOR = (255, 110, 170, 200)  # 살짝 투명한 코스모폴리탄 느낌
        pygame.draw.polygon(surface, LIQUID_COLOR, poly)


    def _build_liquid_polygon(self):
        """
        self.fill_amount (0.0 ~ 1.0)를 기반으로
        잔 안에 들어갈 '곡선 표면' 리퀴드 폴리곤을 계산해서 리스트로 반환.
        """
        f = max(0.0, min(1.0, self.fill_amount))
        if f <= 0.0:
            return []

        tl = pygame.Vector2(self.tri["top_left"])
        tr = pygame.Vector2(self.tri["top_right"])
        b  = pygame.Vector2(self.tri["bottom"])

        # bottom(0.0) -> top(1.0) 방향으로 선형 보간
        # 왼쪽/오른쪽 벽에서 현재 수위에 해당하는 점
        left_pt  = b.lerp(tl, f)
        right_pt = b.lerp(tr, f)

        # 곡선 표면을 만들 샘플 포인트 개수
        NUM_SAMPLES = 6
        curve_points = []

        for i in range(NUM_SAMPLES + 1):
            u = i / NUM_SAMPLES  # 0.0 ~ 1.0

            # x는 좌→우 선형 보간
            x = left_pt.x + (right_pt.x - left_pt.x) * u

            # y는 기본 수위 + 곡률 적용
            base_y = left_pt.y + (right_pt.y - left_pt.y) * u

            # 가운데가 살짝 볼록해지도록 sin 곡선 사용
            bulge = math.sin(u * math.pi)  # 0~1~0
            CURVE_STRENGTH = 4.0  # 곡률 세기(픽셀 단위)
            y = base_y - bulge * CURVE_STRENGTH

            curve_points.append((x, y))

        # 최종 폴리곤: bottom에서 곡선 표면을 감싸는 팬 형태
        poly = [(b.x, b.y)] + curve_points
        return poly