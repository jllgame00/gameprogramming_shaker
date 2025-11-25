# component/shaker.py
import pygame
import math

from component.config import (
    SHAKE_THRESHOLD,
    POUR_START_ANGLE,
    POUR_MAX_ANGLE,
    MAX_SHAKER_VOLUME,
    VOLUME_PER_PARTICLE,
    POUR_RATE,
)

from component.particles import Particle


class Shaker:
    MODE_SHAKING = 0   # 제자리에서 흔들기
    MODE_MOVING  = 1   # 잔 위로 옮기기
    MODE_POURING = 2   # 기울여서 따르기

    def __init__(self, body_img, cap_img, screen_width, screen_height):
        self.body_orig = body_img
        self.cap_orig = cap_img

        # 기본 위치 (왼쪽 아래쯤)
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

        # 바디 / 캡 배치용 정보
        body_rect = self.body_orig.get_rect(center=self.pos)
        self.body_rect = body_rect

        # 셰이커 입구 offset (중심 기준)
        self.mouth_offset = pygame.Vector2(
            0,
            -body_rect.height * 0.5 + 12
        )

        # 캡
        self.cap_on_top = True
        self.cap_rect = self.cap_orig.get_rect()
        self.cap_offset = pygame.Vector2(
            0,
            -body_rect.height * 0.5 - self.cap_rect.height * 0.3
        )
        self.cap_side_pos = pygame.Vector2(
            screen_width * 0.45,
            self.pos.y - body_rect.height * 0.3
        )

        # 셰이커 안 칵테일 양
        self.volume = MAX_SHAKER_VOLUME

        # 렌더 캐시
        self.rotated_body = self.body_orig

    # -------------------------------------------------
    # 업데이트
    # -------------------------------------------------
    def update(self, events, dt):
        if self.mode == Shaker.MODE_SHAKING:
            self._update_shaking(events, dt)
        elif self.mode == Shaker.MODE_MOVING:
            self._update_moving(events, dt)
        elif self.mode == Shaker.MODE_POURING:
            self._update_pouring(events, dt)

        # 바디 회전 적용
        self.rotated_body = pygame.transform.rotozoom(
            self.body_orig, self.angle, 1.0
        )
        self.body_rect = self.rotated_body.get_rect(center=self.pos)

    # ---------------------- SHAKE 모드 ----------------------
    def _update_shaking(self, events, dt):
        # 파워 감쇠
        self.shake_timer += dt
        self.shake_power *= 0.90
        if self.shake_power < 0.01:
            self.shake_power = 0.0

        # 기본 위치
        self.pos = self.base_pos.copy()

        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                # 왼쪽 버튼 누르면 쉐이킹 시작
                self.mouse_dragging = True
                self.prev_mouse_x = e.pos[0]

            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                # 쉐이킹 끝
                self.mouse_dragging = False
                self.prev_mouse_x = None

                # 충분히 흔들었으면 이동 단계로 전환
                if self.shake_power >= SHAKE_THRESHOLD:
                    self.mode = Shaker.MODE_MOVING
                    # 현재 위치를 새로운 base로 설정
                    self.base_pos = self.pos.copy()
                    # 각도는 똑바로 세워놓기
                    self.angle = 0.0
                else:
                    # 너무 조금 흔들었으면 파워 리셋
                    self.shake_power = 0.0

            elif e.type == pygame.MOUSEMOTION and self.mouse_dragging:
                mx = e.pos[0]
                if self.prev_mouse_x is not None:
                    dx = mx - self.prev_mouse_x

                    # 셰이커를 마우스를 따라 좌우로 직접 움직이게
                    self.pos.x = self.base_pos.x + dx

                    # 흔들어준 만큼 파워 누적
                    self.shake_power += abs(dx) * 0.06

                    self.prev_mouse_x = mx

        # 살짝 덜덜 효과 (위아래)
        shake_offset_y = math.sin(self.shake_timer * 40) * self.shake_power * 0.5
        self.pos.y += shake_offset_y

        # 각도도 살짝만 흔들리게
        self.angle = math.sin(self.shake_timer * 25) * self.shake_power * 2

    # ---------------------- MOVING 모드 ----------------------
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

    # ---------------------- POURING 모드 ----------------------
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
                    self.prev_mouse_y = my

                    # 각도 제한
                    self.angle = max(POUR_MAX_ANGLE, min(30.0, self.angle))

    # -------------------------------------------------
    # 파티클 방출
    # -------------------------------------------------
    def emit_particles(self, particles_list):
        """
        현재 각도/볼륨/모드에 따라 물방울 파티클 생성.
        """
        if self.mode != Shaker.MODE_POURING:
            return
        if self.volume <= 0:
            return
        if self.angle > POUR_START_ANGLE:
            return  # 아직 덜 기울어짐

        # 얼마나 많이 기울였는지 비율 0~1
        over = (abs(self.angle) - abs(POUR_START_ANGLE)) / \
               (abs(POUR_MAX_ANGLE) - abs(POUR_START_ANGLE))
        over = max(0.0, min(1.0, over))

        base_stream = 1
        extra_stream = int(3 * over)
        num_stream = base_stream + extra_stream

        mouth_pos = self.get_mouth_pos()

        for _ in range(num_stream):
            if self.volume <= 0:
                break
            particles_list.append(Particle(mouth_pos.x, mouth_pos.y))
            self.volume = max(0.0, self.volume - VOLUME_PER_PARTICLE)

    # -------------------------------------------------
    # 헬퍼 / 렌더
    # -------------------------------------------------
    def get_mouth_pos(self) -> pygame.Vector2:
        offset = self.mouth_offset.rotate(-self.angle)
        return self.pos + offset

    def draw(self, screen: pygame.Surface):
        # 바디
        screen.blit(self.rotated_body, self.body_rect)

        # 캡
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

    def is_pouring_now(self):
        return (
            self.mode == Shaker.MODE_POURING
            and self.volume > 0
            and self.angle < POUR_START_ANGLE
        )

    def get_pour_factor(self):
        """
        0~1: 얼마나 많이 기울였는지
        """
        if not self.is_pouring_now():
            return 0.0

        over = (abs(self.angle) - abs(POUR_START_ANGLE)) / \
               (abs(POUR_MAX_ANGLE) - abs(POUR_START_ANGLE))
        over = max(0.0, min(1.0, over))
        return over

    def is_pouring_now(self):
        return (
            self.mode == Shaker.MODE_POURING
            and self.volume > 0
            and self.angle < POUR_START_ANGLE
        )

    def get_pour_factor(self):
        """
        0~1: 얼마나 많이 기울였는지 (기울수록 1에 가까워짐)
        """
        if not self.is_pouring_now():
            return 0.0

        over = (abs(self.angle) - abs(POUR_START_ANGLE)) / \
               (abs(POUR_MAX_ANGLE) - abs(POUR_START_ANGLE))
        return max(0.0, min(1.0, over))

    def update_volume(self, dt: float, pour_factor: float) -> float:
        """
        dt 동안 pour_factor 세기로 부었을 때
        실제로 셰이커에서 빠져나간 양을 계산하고,
        그만큼 self.volume에서 빼고,
        빠진 양(used_volume)을 반환.
        """
        if not self.is_pouring_now():
            return 0.0

        if pour_factor <= 0.0:
            return 0.0

        # 이 시간동안 붓고 싶은 양
        desired = pour_factor * POUR_RATE * dt

        if desired <= 0.0:
            return 0.0

        # 남은 양보다 많이 붓지는 못함
        used = min(desired, self.volume)
        self.volume -= used
        return used
