# glass.py
import pygame
import random

from config import GLASS_FILL_PER_PARTICLE
from geometry import get_glass_triangle, point_in_triangle
from obb import create_wall_obbs_from_triangle, point_in_obb
from particles import Particle


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
        # 액체 surface 초기화
        self.liquid_surface.fill((0, 0, 0, 0))

        # 액체 다각형 그리기
        self._draw_liquid_polygon(self.liquid_surface)

        # 잔 → 액체 → spill/splash 순으로 렌더
        screen.blit(self.img, self.rect)
        screen.blit(self.liquid_surface, (0, 0))

        for sp in self.spill_particles:
            sp.draw(screen)
        for sp in self.splash_particles:
            sp.draw(screen)

    # -------------------------------------------------
    # 내부: 액체 삼각형 렌더
    # -------------------------------------------------
    def _draw_liquid_polygon(self, surface):
        # 화면에 보이는 부분은 0~1 사이로 클램프
        visible = max(0.0, min(1.0, self.fill_amount))

        top_left = pygame.Vector2(self.tri["top_left"])
        top_right = pygame.Vector2(self.tri["top_right"])
        bottom = pygame.Vector2(self.tri["bottom"])

        current_y = bottom.y + (top_left.y - bottom.y) * visible
        left_x  = bottom.x + (top_left.x  - bottom.x) * visible
        right_x = bottom.x + (top_right.x - bottom.x) * visible

        poly = [
            (bottom.x, bottom.y),
            (left_x, current_y),
            (right_x, current_y),
        ]

        LIQUID_COLOR = (255, 110, 170, 200)  # 약간 투명한 칵테일
        pygame.draw.polygon(surface, LIQUID_COLOR, poly)
