# component/geometry.py
import pygame

def get_glass_triangle(glass_rect: pygame.Rect):
    """
    잔 이미지(rect) 기준으로 '액체가 차는 내부'를 이등변 삼각형으로 정의.
    위쪽은 림보다 살짝 아래, 아래쪽은 스템 시작 직전 정도.
    """
    gw, gh = glass_rect.width, glass_rect.height

    top_y = glass_rect.top + gh * 0.20     # 윗면
    bottom_y = glass_rect.top + gh * 0.55  # 바닥

    cx = glass_rect.centerx
    half_inner_w = gw * 0.35  # 림에서 실제 액체 너비 (양옆 여백 조금 남김)

    top_left = (cx - half_inner_w, top_y)
    top_right = (cx + half_inner_w, top_y)
    bottom = (cx, bottom_y)

    return {
        "top_left": top_left,
        "top_right": top_right,
        "bottom": bottom,
    }


def point_in_triangle(pt, a, b, c):
    """
    2D point가 삼각형 안에 있는지 여부 (면적 기반).
    """
    (x, y) = pt

    def area(x1, y1, x2, y2, x3, y3):
        return abs(
            (x1 * (y2 - y3) +
             x2 * (y3 - y1) +
             x3 * (y1 - y2)) / 2.0
        )

    A = area(*a, *b, *c)
    A1 = area(x, y, *b, *c)
    A2 = area(*a, x, y, *c)
    A3 = area(*a, *b, x, y)

    return abs((A1 + A2 + A3) - A) < 0.3
