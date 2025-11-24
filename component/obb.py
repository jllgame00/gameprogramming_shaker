# obb.py
# 잔 옆면 같은 기울어진 벽을 OBB(Oriented Bounding Box)로 다루기 위한 유틸

from dataclasses import dataclass
import math

@dataclass
class OBB:
    center: tuple[float, float]   # (cx, cy)
    axis1: tuple[float, float]    # 길이 방향 단위벡터
    axis2: tuple[float, float]    # 두께 방향 단위벡터( axis1에 수직 )
    half_w: float                 # 두께/2
    half_h: float                 # 길이/2


def point_in_obb(px: float, py: float, obb: OBB) -> bool:
    """
    점(px, py)가 OBB 안에 들어있는지 판정.
    수업에서 배운 방식 그대로:
      1) p - center → local
      2) axis1, axis2에 투영
      3) 각 투영의 절댓값이 half_h, half_w 안이면 inside
    """
    rx = px - obb.center[0]
    ry = py - obb.center[1]

    dot1 = rx * obb.axis1[0] + ry * obb.axis1[1]
    dot2 = rx * obb.axis2[0] + ry * obb.axis2[1]

    return (abs(dot1) <= obb.half_h) and (abs(dot2) <= obb.half_w)


def _make_wall_obb(a: tuple[float, float],
                   b: tuple[float, float],
                   thickness: float) -> OBB:
    """
    양 끝점 a-b로 이루어진 기울어진 벽을 OBB 하나로 만든다.
    a, b : (x, y)
    thickness : 벽 두께(픽셀 단위)
    """
    ax, ay = a
    bx, by = b

    dx = bx - ax
    dy = by - ay
    length = math.hypot(dx, dy)
    if length == 0:
        # 혹시라도 degenerate 한 경우를 대비
        length = 1.0

    # axis1 : 벽을 따라 내려가는 방향(단위벡터)
    ux = dx / length
    uy = dy / length

    # axis2 : axis1에 수직인 방향 (두께 방향)
    vx = -uy
    vy = ux

    cx = (ax + bx) * 0.5
    cy = (ay + by) * 0.5

    half_h = length * 0.5
    half_w = thickness * 0.5

    return OBB(
        center=(cx, cy),
        axis1=(ux, uy),
        axis2=(vx, vy),
        half_w=half_w,
        half_h=half_h,
    )


def create_wall_obbs_from_triangle(tri: dict,
                                   thickness: float = 8.0) -> tuple[OBB, OBB]:
    """
    잔 내부 삼각형 tri(dict: top_left, top_right, bottom) 를 받아서
    왼쪽 벽 / 오른쪽 벽을 각각 OBB 두 개로 만들어 돌려준다.
    """
    tl = tri["top_left"]
    tr = tri["top_right"]
    bt = tri["bottom"]

    left_obb = _make_wall_obb(tl, bt, thickness)
    right_obb = _make_wall_obb(tr, bt, thickness)

    return left_obb, right_obb
