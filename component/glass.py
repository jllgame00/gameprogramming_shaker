# component/glass.py
import pygame

from component.config import GLASS_FILL_PER_PARTICLE
from component.geometry import get_glass_triangle, point_in_triangle


class Glass:
    """
    기능 우선 버전:
    - 삼각형 hitbox 안에 입자가 들어오면 fill_amount 증가
    - fill_amount(0~1)에 따라 단순 삼각형 리퀴드 렌더링
    """
    def __init__(self, glass_img, screen_width, screen_height, baseline_y):
        self.img = glass_img
        self.rect = self.img.get_rect()
        # 셰이커 바닥 y에 맞춰 midbottom 정렬
        self.rect.midbottom = (screen_width * 0.72, baseline_y)

        # 내부 삼각형
        self.tri = get_glass_triangle(self.rect)

        self.fill_amount = 0.0

        # 리퀴드 그릴 surface
        self.liquid_surface = pygame.Surface(
            (screen_width, screen_height), pygame.SRCALPHA
        )

    # -------------------------------------------------
    # 업데이트: 입자와 상호작용
    # -------------------------------------------------
    def update(self, particles, dt):
        a = self.tri["top_left"]
        b = self.tri["top_right"]
        c = self.tri["bottom"]

        for p in particles[:]:
            p.update()

            # 화면 아래로 떨어지면 제거
            if p.pos.y > self.rect.bottom + 200:
                particles.remove(p)
                continue

            inside = point_in_triangle((p.pos.x, p.pos.y), a, b, c)

            if inside:
                # 잔 채우기
                self.fill_amount += GLASS_FILL_PER_PARTICLE
                self.fill_amount = max(0.0, min(1.0, self.fill_amount))
                particles.remove(p)
                continue

    # -------------------------------------------------
    # 렌더
    # -------------------------------------------------
    def draw(self, screen: pygame.Surface):
        # 액체 surface 초기화
        self.liquid_surface.fill((0, 0, 0, 0))

        # 리퀴드 폴리곤 그리기
        self._draw_liquid_polygon(self.liquid_surface)

        # 잔 → 액체 순으로 그리기
        screen.blit(self.img, self.rect)
        screen.blit(self.liquid_surface, (0, 0))

    # -------------------------------------------------
    # 내부: 단순 삼각형 리퀴드 렌더
    # -------------------------------------------------
    def _draw_liquid_polygon(self, surface: pygame.Surface):
        f = max(0.0, min(1.0, self.fill_amount))
        if f <= 0.0:
            return

        tl = pygame.Vector2(self.tri["top_left"])
        tr = pygame.Vector2(self.tri["top_right"])
        b  = pygame.Vector2(self.tri["bottom"])

        # b(0) → tl/tr(1) 방향으로 선형 보간해서 현재 수위 라인 계산
        left_pt  = b.lerp(tl, f)
        right_pt = b.lerp(tr, f)

        # 단순 삼각형 폴리곤
        poly = [
            (left_pt.x,  left_pt.y),
            (right_pt.x, right_pt.y),
            (b.x,        b.y),
        ]

        LIQUID_COLOR = (255, 110, 170, 200)  # 살짝 투명한 칵테일 색
        pygame.draw.polygon(surface, LIQUID_COLOR, poly)
