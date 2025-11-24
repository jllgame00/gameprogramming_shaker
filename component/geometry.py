import pygame

def get_glass_triangle(glass_rect):
    gw, gh = glass_rect.width, glass_rect.height

    top_y = glass_rect.top + gh * 0.18
    bottom_y = glass_rect.top + gh * 0.48
    cx = glass_rect.centerx

    half_inner_w = gw * 0.40

    return {
        "top_left":  (cx - half_inner_w, top_y),
        "top_right": (cx + half_inner_w, top_y),
        "bottom":    (cx, bottom_y),
    }

def point_in_triangle(pt, a, b, c):
    (x, y) = pt
    def area(x1,y1,x2,y2,x3,y3):
        return abs((x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2)) / 2)
    A  = area(*a,*b,*c)
    A1 = area(x,y,*b,*c)
    A2 = area(*a,x,y,*c)
    A3 = area(*a,*b,x,y)
    return abs((A1+A2+A3)-A) < 0.1

def get_liquid_surface_y(tri, fill_amount):
    visible = max(0, min(1, fill_amount))
    tl = pygame.Vector2(tri["top_left"])
    bt = pygame.Vector2(tri["bottom"])
    return bt.y + (tl.y - bt.y) * visible