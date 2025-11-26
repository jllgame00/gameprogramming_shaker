# component/shaker.py
import pygame
import math

from component.config import (
    SHAKE_THRESHOLD,
    POUR_START_ANGLE,
    POUR_MAX_ANGLE,
    MAX_SHAKER_VOLUME,
    POUR_RATE,
)


class Shaker:
    MODE_SHAKING = 0
    MODE_MOVING = 1
    MODE_POURING = 2

    def __init__(self, body_img, cap_img, screen_width, screen_height):
        self.body_orig = body_img
        self.cap_orig = cap_img

        self.base_pos = pygame.Vector2(screen_width * 0.3,
                                       screen_height * 0.55)
        self.pos = self.base_pos.copy()

        self.angle = 0.0
        self.shake_power = 0.0
        self.shake_timer = 0.0

        self.mode = Shaker.MODE_SHAKING

        self.mouse_dragging = False
        self.prev_mouse_x = None
        self.prev_mouse_y = None

        body_rect = self.body_orig.get_rect(center=self.pos)
        self.body_rect = body_rect

        self.mouth_offset = pygame.Vector2(
            0,
            -body_rect.height * 0.5 + 12,
        )

        self.cap_on_top = True
        self.cap_rect = self.cap_orig.get_rect()
        self.cap_offset = pygame.Vector2(
            0,
            -body_rect.height * 0.5 - self.cap_rect.height * 0.3,
        )
        self.cap_side_pos = pygame.Vector2(
            screen_width * 0.45,
            self.pos.y - body_rect.height * 0.3,
        )

        self.volume = MAX_SHAKER_VOLUME
        self.rotated_body = self.body_orig

    # -------- 업데이트 --------
    def update(self, events, dt: float):
        if self.mode == Shaker.MODE_SHAKING:
            self._update_shaking(events, dt)
        elif self.mode == Shaker.MODE_MOVING:
            self._update_moving(events, dt)
        elif self.mode == Shaker.MODE_POURING:
            self._update_pouring(events, dt)

        self.rotated_body = pygame.transform.rotozoom(
            self.body_orig, self.angle, 1.0
        )
        self.body_rect = self.rotated_body.get_rect(center=self.pos)

    # SHAKE 모드
    def _update_shaking(self, events, dt: float):
        self.shake_timer += dt
        self.shake_power *= 0.90
        if self.shake_power < 0.01:
            self.shake_power = 0.0

        self.pos = self.base_pos.copy()

        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                self.mouse_dragging = True
                self.prev_mouse_x = e.pos[0]

            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                self.mouse_dragging = False
                self.prev_mouse_x = None

                if self.shake_power >= SHAKE_THRESHOLD:
                    self.mode = Shaker.MODE_MOVING
                    self.base_pos = self.pos.copy()
                    self.angle = 0.0
                else:
                    self.shake_power = 0.0

            elif e.type == pygame.MOUSEMOTION and self.mouse_dragging:
                mx = e.pos[0]
                if self.prev_mouse_x is not None:
                    dx = mx - self.prev_mouse_x
                    self.pos.x = self.base_pos.x + dx
                    self.shake_power += abs(dx) * 0.06
                    self.prev_mouse_x = mx

        shake_offset_y = math.sin(self.shake_timer * 40) * self.shake_power * 0.5
        self.pos.y += shake_offset_y

        self.angle = math.sin(self.shake_timer * 25) * self.shake_power * 2

    # MOVING 모드
    def _update_moving(self, events, dt: float):
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                self.mouse_dragging = True

            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                self.mouse_dragging = False
                self.mode = Shaker.MODE_POURING
                self.cap_on_top = False

            elif e.type == pygame.MOUSEMOTION and self.mouse_dragging:
                mx, my = e.pos
                self.pos.x = mx
                self.pos.y = my

    # POURING 모드
    def _update_pouring(self, events, dt: float):
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                self.mouse_dragging = True
                self.prev_mouse_y = e.pos[1]

            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                self.mouse_dragging = False
                self.prev_mouse_y = None

            elif e.type == pygame.MOUSEMOTION and self.mouse_dragging:
                my = e.pos[1]
                if self.prev_mouse_y is not None:
                    dy = my - self.prev_mouse_y
                    self.angle += dy * 0.4
                    self.prev_mouse_y = my
                    self.angle = max(POUR_MAX_ANGLE, min(30.0, self.angle))

    # -------- 헬퍼 / 렌더 --------
    def get_mouth_pos(self) -> pygame.Vector2:
        offset = self.mouth_offset.rotate(-self.angle)
        return self.pos + offset

    def draw(self, screen: pygame.Surface):
        screen.blit(self.rotated_body, self.body_rect)

        if self.cap_on_top:
            rotated_cap = pygame.transform.rotozoom(
                self.cap_orig, self.angle, 1.0
            )
            rotated_cap_offset = self.cap_offset.rotate(-self.angle)
            cap_center = self.pos + rotated_cap_offset
            cap_rect = rotated_cap.get_rect(center=cap_center)
            screen.blit(rotated_cap, cap_rect)
        else:
            cap_rect = self.cap_orig.get_rect(center=self.cap_side_pos)
            screen.blit(self.cap_orig, cap_rect)

    # -------- 볼륨/붓기 --------
    def is_pouring_now(self) -> bool:
        return (
            self.mode == Shaker.MODE_POURING
            and self.volume > 0
            and self.angle < POUR_START_ANGLE
        )

    def get_pour_factor(self) -> float:
        """
        0~1: 얼마나 많이 기울였는지 (기울수록 1에 가까움)
        """
        if not self.is_pouring_now():
            return 0.0

        over = (abs(self.angle) - abs(POUR_START_ANGLE)) / \
               (abs(POUR_MAX_ANGLE) - abs(POUR_START_ANGLE))
        return max(0.0, min(1.0, over))

    def update_volume(self, dt: float, pour_factor: float) -> float:
        """
        dt 동안 붓기 세기(pour_factor)에 따라 실제로 빠져나간 양을 반환.
        """
        if not self.is_pouring_now():
            return 0.0
        if pour_factor <= 0.0:
            return 0.0

        desired = pour_factor * POUR_RATE * dt
        if desired <= 0.0:
            return 0.0

        used = min(desired, self.volume)
        self.volume -= used
        return used
