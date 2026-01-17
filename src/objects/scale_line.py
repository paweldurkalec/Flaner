import math
from .base import CanvasObject
import pygame

class ScaleLine(CanvasObject):
    """A single scale line: two points in original-image pixel coords and a real-world length in meters."""
    def __init__(self, p1_orig, p2_orig, meters, color=(255, 100, 100), width=1):
        self.p1 = tuple(p1_orig)
        self.p2 = tuple(p2_orig)
        self.meters = float(meters)
        self.color = color
        self.width = int(width)

    @property
    def pixels_per_meter(self):
        dx = self.p2[0] - self.p1[0]
        dy = self.p2[1] - self.p1[1]
        dist = math.hypot(dx, dy)
        if self.meters <= 0:
            return None
        return dist / self.meters

    def draw(self, surface, image_rect, image_scale, font, pixels_per_meter=None, width=None, label_scale=1.0):
        # Map original-image coords to display coords
        x1 = image_rect.x + int(self.p1[0] * image_scale)
        y1 = image_rect.y + int(self.p1[1] * image_scale)
        x2 = image_rect.x + int(self.p2[0] * image_scale)
        y2 = image_rect.y + int(self.p2[1] * image_scale)
        # choose width
        draw_w = int(self.width if width is None else width)
        # anti-aliased thin line, otherwise normal line with width
        try:
            if draw_w <= 1:
                pygame.draw.aaline(surface, self.color, (x1, y1), (x2, y2))
            else:
                pygame.draw.line(surface, self.color, (x1, y1), (x2, y2), draw_w)
        except Exception:
            pygame.draw.line(surface, self.color, (x1, y1), (x2, y2), max(1, draw_w))
        # draw perpendicular end caps
        def draw_perp_cap(surf, x_a, y_a, x_b, y_b, length=10):
            dx = x_b - x_a
            dy = y_b - y_a
            dist = math.hypot(dx, dy)
            if dist == 0:
                return
            ux = dx / dist
            uy = dy / dist
            # perpendicular vector
            px = -uy
            py = ux
            cx1 = int(x_a + px * length / 2)
            cy1 = int(y_a + py * length / 2)
            cx2 = int(x_a - px * length / 2)
            cy2 = int(y_a - py * length / 2)
            try:
                if draw_w <= 1:
                    pygame.draw.aaline(surf, self.color, (cx1, cy1), (cx2, cy2))
                else:
                    pygame.draw.line(surf, self.color, (cx1, cy1), (cx2, cy2), draw_w)
            except Exception:
                pygame.draw.line(surf, self.color, (cx1, cy1), (cx2, cy2), max(1, draw_w))

        draw_perp_cap(surface, x1, y1, x2, y2, length=12)
        draw_perp_cap(surface, x2, y2, x1, y1, length=12)
        # label with meters, offset from the line so it's visible beside the cap
        midx = (x1 + x2) // 2
        midy = (y1 + y2) // 2
        txt = f"{self.meters:.2f} m"
        # compute perpendicular to offset label
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist == 0:
            px, py = 0, -1
        else:
            px = -dy / dist
            py = dx / dist
        offset = max(6, draw_w * 3)
        lx = int(midx + px * offset)
        ly = int(midy + py * offset)
        try:
            base_shadow = font.render(txt, True, (10, 10, 10))
            base_img = font.render(txt, True, (255, 220, 80))
            s = max(0.01, float(label_scale))
            tw = max(1, int(base_img.get_width() * s))
            th = max(1, int(base_img.get_height() * s))
            try:
                shadow = pygame.transform.smoothscale(base_shadow, (tw, th))
                img_s = pygame.transform.smoothscale(base_img, (tw, th))
            except Exception:
                shadow = pygame.transform.scale(base_shadow, (tw, th))
                img_s = pygame.transform.scale(base_img, (tw, th))
            # offset so nearest edge stays base_offset from the line
            base_offset = max(4, draw_w * 3)
            padding = 4
            center_offset = base_offset + img_s.get_height() // 2 + padding
            lx = int(midx + px * center_offset)
            ly = int(midy + py * center_offset)
            surface.blit(shadow, (lx - shadow.get_width()//2 + 1, ly - shadow.get_height()//2 + 1))
            surface.blit(img_s, (lx - img_s.get_width()//2, ly - img_s.get_height()//2))
        except Exception:
            pass

    def hit_test(self, sx, sy, image_rect, image_scale, tol=8):
        x1 = image_rect.x + int(self.p1[0] * image_scale)
        y1 = image_rect.y + int(self.p1[1] * image_scale)
        x2 = image_rect.x + int(self.p2[0] * image_scale)
        y2 = image_rect.y + int(self.p2[1] * image_scale)
        dx = x2 - x1
        dy = y2 - y1
        seg_len2 = dx*dx + dy*dy
        px = sx - x1
        py = sy - y1
        if seg_len2 == 0:
            return (px*px + py*py) <= tol*tol
        t = (px*dx + py*dy) / seg_len2
        t = max(0.0, min(1.0, t))
        proj_x = x1 + t*dx
        proj_y = y1 + t*dy
        ddx = sx - proj_x
        ddy = sy - proj_y
        return (ddx*ddx + ddy*ddy) <= tol*tol

    def move_by(self, dx_orig, dy_orig):
        self.p1 = (self.p1[0] + dx_orig, self.p1[1] + dy_orig)
        self.p2 = (self.p2[0] + dx_orig, self.p2[1] + dy_orig)

    def hit_test_handle(self, sx, sy, image_rect, image_scale, tol=8):
        x1 = image_rect.x + int(self.p1[0] * image_scale)
        y1 = image_rect.y + int(self.p1[1] * image_scale)
        x2 = image_rect.x + int(self.p2[0] * image_scale)
        y2 = image_rect.y + int(self.p2[1] * image_scale)
        d1 = (sx - x1) ** 2 + (sy - y1) ** 2
        d2 = (sx - x2) ** 2 + (sy - y2) ** 2
        if d1 <= tol * tol:
            return 0
        if d2 <= tol * tol:
            return 1
        return None

    def move_handle(self, idx, dx_orig, dy_orig):
        if idx == 0:
            self.p1 = (self.p1[0] + dx_orig, self.p1[1] + dy_orig)
        elif idx == 1:
            self.p2 = (self.p2[0] + dx_orig, self.p2[1] + dy_orig)

    def to_dict(self):
        return {"type": "scale", "p1": self.p1, "p2": self.p2, "meters": self.meters, "width": self.width}
