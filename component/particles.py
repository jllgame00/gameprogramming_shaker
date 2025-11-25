# component/particles.py
import pygame
import random

class Particle:
    """
    셰이커에서 떨어지는 물방울.
    상태:
    - 'falling' : 공중에서 중력 받아 떨어지는 중
    - 'sliding' : 잔의 벽면을 따라 미끄러지는 중
    """
    def __init__(self, x, y, color=(255, 110, 170)):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(
            random.uniform(-0.3, 0.3),
            random.uniform(1.0, 2.0)
        )
        self.color = color
        self.radius = 3

        # 상태 관리
        self.state = "falling"

        # 슬라이딩용
        self.wall_start = pygame.Vector2(0, 0)
        self.wall_end = pygame.Vector2(0, 0)
        self.slide_t = 0.0  # 0.0 = 벽 시작점, 1.0 = 벽 끝점(보통 바닥)

    def start_slide(self, wall_start: pygame.Vector2, wall_end: pygame.Vector2):
        """
        잔 벽에 붙어서 미끄러지기 시작.
        현재 위치를 벽 선분에 projection해서 slide_t 시작값 잡음.
        """
        self.state = "sliding"
        self.wall_start = wall_start
        self.wall_end = wall_end

        seg = self.wall_end - self.wall_start
        seg_len2 = seg.length_squared()
        if seg_len2 > 0:
            t = (self.pos - self.wall_start).dot(seg) / seg_len2
            t = max(0.0, min(1.0, t))
        else:
            t = 0.0
        self.slide_t = t

        # 슬라이딩하는 동안은 속도는 의미 없으니 0으로
        self.vel.update(0, 0)
        # 위치를 정확히 선분 위로 스냅
        self.pos = self.wall_start.lerp(self.wall_end, self.slide_t)

    def update(self, dt: float):
        if self.state == "falling":
            # 중력
            self.vel.y += 0.08
            self.pos += self.vel

        elif self.state == "sliding":
            # 선분을 따라 아래로 미끄러지게 (t 증가)
            SLIDE_SPEED = 1.2  # 1초에 선분의 1.2배를 탄다고 보면 됨 (감성 튜닝)
            self.slide_t += SLIDE_SPEED * dt
            if self.slide_t > 1.0:
                self.slide_t = 1.0
            self.pos = self.wall_start.lerp(self.wall_end, self.slide_t)

    def is_done_sliding(self) -> bool:
        """
        벽을 끝까지(바닥까지) 탄 경우 True.
        Glass에서 이 시점에 fill_amount를 올리고 제거하면 됨.
        """
        return self.state == "sliding" and self.slide_t >= 1.0

    def draw(self, surf: pygame.Surface):
        pygame.draw.circle(
            surf,
            self.color,
            (int(self.pos.x), int(self.pos.y)),
            self.radius
        )
