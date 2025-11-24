# shaker.py
import pygame
import math
import random

from config import (
    SHAKE_THRESHOLD,
    POUR_START_ANGLE,
    POUR_MAX_ANGLE,
    MAX_SHAKER_VOLUME,
    VOLUME_PER_PARTICLE,
)

from particles import Particle


class Shaker:
    MODE_SHAKING = 0   # 흔드는 단계
    MODE_MOVING  = 1   # 잔 위로 옮기는 단계
    MODE_POURING = 2   # 따르는 단계

    def __init__(self, body_img, cap_img, screen_width, screen_height):
        self.body_orig = body_img
        self.cap_orig = cap_img

        # 기본 위치
        self.base_pos = pygame.Vector2(screen_width * 0.3,
                                       screen_height * 0.55)
        self.pos = self.base_pos.copy()

        # 회전 / 흔들기
        self.angle = 0.0
        self.shake_power = 0.0
        self.shake_timer = 0.0

        # 셰이커 모드
        self.mode = Shaker.MODE_SHAKING

        # 마우스 상태
        self.mouse_dragging = False
        self.prev_mouse_x = None
        self.prev_mouse_y = None

        # 캡 관련
        body_rect = self.body_orig.get_rect(center=self.pos)
        self.cap_on_top = True
        self.cap_rect = self.cap_orig.get_rect()
        self.cap_offset = pygame.Vector2(
            0,
            -body_rect.height * 0.5 - self.cap_rect.height * 0.3
        )
        self.cap_side_pos = pygame.Vector2(
            screen_width * 0.45,
            self.pos.y + body_rect.height * 0.5 - self.cap_rect.height * 0.5
        )

        # 입구 오프셋 (body 중심 기준)
        self.mouth_offset = pygame.Vector2(
            0, -body_rect.height * 0.5 + 12
        )

        # 셰이커 안 칵테일 양
        self.volume = MAX_SHAKER_VOLUME

        # 렌더용 캐시
        self.rotated_body = self.body_orig
        self.body_rect = self.rotated_body.get_rect(center=self.pos)

    # -------------------------------------------------
    # 이벤트 / 상태 업데이트
    # -------------------------------------------------
    def update(self, events, dt):
        if self.mode == Shaker.MODE_SHAKING:
            self._update_shaking(events, dt)
        elif self.mode == Shaker.MODE_MOVING:
            self._update_moving(events, dt)
        elif self.mode == Shaker.MODE_POURING:
            self._update_pouring(events, dt)

        # 회전 적용
        self.rotated_body = pygame.transform.rotozoom(
            self.body_orig, self.angle, 1.0
        )
        self.body_rect = self.rotated_body.get_rect(center=self.pos)

    # ----------------- 모드별 내부 처리 -----------------
    def _update_shaking(self, events, dt):
        self.shake_timer += dt
        self.shake_power *= 0.9
        if self.shake_power < 0.01:
            self.shake_power = 0.0

        # 위아래 덜덜
        shake_offset_y = math.sin(self.shake_timer * 40) * self.shake_power * 5
        self.pos = pygame.Vector2(self.base_pos.x,
                                  self.base_pos.y + shake_offset_y)

        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                self.mouse_dragging = True
                self.prev_mouse_x = e.pos[0]

            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                self.mouse_dragging = False
                self.prev_mouse_x = None

                # 흔든 강도 충분하면 이동 모드로 전환
                if self.shake_power >= SHAKE_THRESHOLD:
                    self.mode = Shaker.MODE_MOVING
                    self.base_pos = self.pos.copy()

            elif e.type == pygame.MOUSEMOTION and self.mouse_dragging:
                mx = e.pos[0]
                if self.prev_mouse_x is not None:
                    dx = mx - self.prev_mouse_x
                    self.shake_power += abs(dx) * 0.02
                    self.prev_mouse_x = mx

    def _update_moving(self, events, dt):
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                self.mouse_dragging = True

            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                self.mouse_dragging = False
                # 캡 분리 + 붓기 모드로
                self.mode = Shaker.MODE_POURING
                self.cap_on_top = False

            elif e.type == pygame.MOUSEMOTION and self.mouse_dragging:
                mx, my = e.pos
                self.pos.x = mx
                self.pos.y = my

    def _update_pouring(self, events, dt):
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
                    # 각도 클램프
                    self.angle = max(-130, min(30, self.angle))
                    self.prev_mouse_y = my

    # -------------------------------------------------
    # 입자 생성 (물줄기) — main에서 particles 리스트에 append해서 씀
    # -------------------------------------------------
    def emit_particles(self, particles_list):
        """현재 상태/각도/잔량에 따라 물줄기 파티클 생성."""
        if self.mode != Shaker.MODE_POURING:
            return
        if self.volume <= 0:
            return
        if self.angle > POUR_START_ANGLE:
            return  # 아직 안 기울어짐

        # 각도에 따라 유량 결정
        over = min(1.0, max(0.0,
                (abs(self.angle) - abs(POUR_START_ANGLE)) /
                (abs(POUR_MAX_ANGLE) - abs(POUR_START_ANGLE)) ))
        base_stream = 1
        extra_stream = int(4 * over)
        num_stream = base_stream + extra_stream

        mouth_pos = self.get_mouth_pos()

        for _ in range(num_stream):
            if self.volume <= 0:
                break
            particles_list.append(Particle(mouth_pos.x, mouth_pos.y))
            self.volume = max(0.0, self.volume - VOLUME_PER_PARTICLE)

    # -------------------------------------------------
    # 헬퍼
    # -------------------------------------------------
    def get_mouth_pos(self) -> pygame.Vector2:
        """회전된 셰이커 입구의 월드 좌표 반환."""
        rotated_offset = self.mouth_offset.rotate(-self.angle)
        return self.pos + rotated_offset

    # -------------------------------------------------
    # 렌더링
    # -------------------------------------------------
    def draw(self, screen):
        # 바디
        screen.blit(self.rotated_body, self.body_rect)

        # 캡
        if self.cap_on_top:
            rotated_cap = pygame.transform.rotozoom(self.cap_orig,
                                                    self.angle, 1.0)
            rotated_cap_offset = self.cap_offset.rotate(-self.angle)
            cap_center = self.pos + rotated_cap_offset
            cap_rect = rotated_cap.get_rect(center=cap_center)
            screen.blit(rotated_cap, cap_rect)
        else:
            cap_rect = self.cap_orig.get_rect(center=self.cap_side_pos)
            screen.blit(self.cap_orig, cap_rect)
