import math
from .base import CanvasObject
import pygame

class MeasureLine(CanvasObject):
    """A measurement line with arrows at the ends and a real-world distance label."""
    def __init__(self, p1_orig, p2_orig, meters=None, color=(0, 200, 200), width=1):
        self.p1 = tuple(p1_orig)
        self.p2 = tuple(p2_orig)
        self.meters = float(meters) if meters is not None else None
        self.color = color
        self.width = int(width)

    def draw_arrow(self, surface, col, a, b, size=8):
        # draw filled arrowhead at point b pointing from a->b; fallback to lines if polygon fails
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        angle = math.atan2(dy, dx)
        left = (int(b[0] - size * math.cos(angle - math.pi/6)), int(b[1] - size * math.sin(angle - math.pi/6)))
        right = (int(b[0] - size * math.cos(angle + math.pi/6)), int(b[1] - size * math.sin(angle + math.pi/6)))
        try:
            pygame.draw.polygon(surface, col, [b, left, right])
        except Exception:
            try:
                pygame.draw.line(surface, col, b, left, max(1, int(size//3)))
                pygame.draw.line(surface, col, b, right, max(1, int(size//3)))
            except Exception:
                pass

    def draw(self, surface, image_rect, image_scale, font, pixels_per_meter=None, width=None, label_scale=1.0):
        x1 = image_rect.x + int(self.p1[0] * image_scale)
        y1 = image_rect.y + int(self.p1[1] * image_scale)
        x2 = image_rect.x + int(self.p2[0] * image_scale)
        y2 = image_rect.y + int(self.p2[1] * image_scale)
        draw_w = int(self.width if width is None else width)
        # anti-aliased thin line for smoothness, otherwise regular line with width
        try:
            if draw_w <= 1:
                pygame.draw.aaline(surface, self.color, (x1, y1), (x2, y2))
            else:
                pygame.draw.line(surface, self.color, (x1, y1), (x2, y2), draw_w)
        except Exception:
            pygame.draw.line(surface, self.color, (x1, y1), (x2, y2), max(1, draw_w))
        # arrows (point outward)
        # arrows (size scales with line width)
        arrow_size = max(6, int(draw_w * 3))
        # arrow at p1 pointing away from p2
        self.draw_arrow(surface, self.color, (x2, y2), (x1, y1), size=arrow_size)
        # arrow at p2 pointing away from p1
        self.draw_arrow(surface, self.color, (x1, y1), (x2, y2), size=arrow_size)
        # text: compute lengths from original-image coordinates (stable across pan/zoom)
        midx = (x1 + x2) // 2
        midy = (y1 + y2) // 2
        dp_orig = math.hypot(self.p2[0] - self.p1[0], self.p2[1] - self.p1[1])

        if pixels_per_meter:
            txt = f"{(dp_orig / pixels_per_meter):.2f} m"
        elif self.meters is not None:
            txt = f"{self.meters:.2f} m"
        else:
            # show pixel length when no real-world scale is available
            txt = f"{int(round(dp_orig))} px"

        # offset label away from the line (perpendicular) so it doesn't sit on top of the line
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist == 0:
            px, py = 0, -1
        else:
            px = -dy / dist
            py = dx / dist
        # offset in display pixels; scale with line width so label stays readable
        base_offset = max(4, draw_w * 3)

        # render text using base font then smoothscale so the whole string scales uniformly
        try:
            base_shadow = font.render(txt, True, (10, 10, 10))
            base_img = font.render(txt, True, (255, 220, 80))
            # target scale in both axes
            s = max(0.01, float(label_scale))
            tw = max(1, int(base_img.get_width() * s))
            th = max(1, int(base_img.get_height() * s))
            try:
                shadow = pygame.transform.smoothscale(base_shadow, (tw, th))
                img_s = pygame.transform.smoothscale(base_img, (tw, th))
            except Exception:
                shadow = pygame.transform.scale(base_shadow, (tw, th))
                img_s = pygame.transform.scale(base_img, (tw, th))
            # position label so its nearest edge to the line is at base_offset from the line
            padding = 4
            center_offset = base_offset + img_s.get_height() // 2 + padding
            lx = int(midx + px * center_offset)
            ly = int(midy + py * center_offset)
            surface.blit(shadow, (lx - shadow.get_width()//2 + 1, ly - shadow.get_height()//2 + 1))
            surface.blit(img_s, (lx - img_s.get_width()//2, ly - img_s.get_height()//2))
        except Exception:
            pass

    def to_dict(self):
        return {"type": "measure", "p1": self.p1, "p2": self.p2, "meters": self.meters, "width": self.width}

    def hit_test(self, sx, sy, image_rect, image_scale, tol=8):
        # screen coords
        x1 = image_rect.x + int(self.p1[0] * image_scale)
        y1 = image_rect.y + int(self.p1[1] * image_scale)
        x2 = image_rect.x + int(self.p2[0] * image_scale)
        y2 = image_rect.y + int(self.p2[1] * image_scale)
        # compute distance from point to segment
        px = sx - x1
        py = sy - y1
        dx = x2 - x1
        dy = y2 - y1
        seg_len2 = dx*dx + dy*dy
        if seg_len2 == 0:
            d2 = px*px + py*py
            return d2 <= tol*tol
        t = (px*dx + py*dy) / seg_len2
        t = max(0.0, min(1.0, t))
        proj_x = x1 + t*dx
        proj_y = y1 + t*dy
        ddx = sx - proj_x
        ddy = sy - proj_y
        return (ddx*ddx + ddy*ddy) <= tol*tol

    def move_by(self, dx_orig, dy_orig):
        # dx_orig/dy_orig are in original-image pixels
        self.p1 = (self.p1[0] + dx_orig, self.p1[1] + dy_orig)
        self.p2 = (self.p2[0] + dx_orig, self.p2[1] + dy_orig)

    def hit_test_handle(self, sx, sy, image_rect, image_scale, tol=8):
        # return 0 if near p1, 1 if near p2, else None
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
