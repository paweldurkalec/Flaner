import pygame
import json

class Rectangle:
    def __init__(self, p1, p2, color=(255,200,50), width=2):
        # p1,p2 are in original image coordinates
        self.p1 = tuple(p1)
        self.p2 = tuple(p2)
        self.color = color
        self.width = width
        self.type = 'rect'

    def draw(self, surface, image_rect, image_scale, font=None, pixels_per_meter=None, label_scale=1.0):
        # convert to screen coords
        x1 = int(image_rect.x + self.p1[0] * image_scale)
        y1 = int(image_rect.y + self.p1[1] * image_scale)
        x2 = int(image_rect.x + self.p2[0] * image_scale)
        y2 = int(image_rect.y + self.p2[1] * image_scale)
        rx = min(x1, x2)
        ry = min(y1, y2)
        rw = abs(x2 - x1)
        rh = abs(y2 - y1)
        try:
            pygame.draw.rect(surface, self.color, (rx, ry, rw, rh), self.width)
        except Exception:
            pygame.draw.rect(surface, self.color, (rx, ry, rw, rh), self.width)
        # draw dimensions (width on top edge, height on left edge)
        if font is not None:
            # Compute original-image pixel dimensions directly to avoid rounding shifts
            orig_w = abs(self.p2[0] - self.p1[0])
            orig_h = abs(self.p2[1] - self.p1[1])
            # compute display text: prefer meters if pixels_per_meter provided, else show pixels
            if pixels_per_meter:
                width_txt = f"{(orig_w / pixels_per_meter):.2f} m"
                height_txt = f"{(orig_h / pixels_per_meter):.2f} m"
            else:
                width_txt = f"{int(round(orig_w))} px"
                height_txt = f"{int(round(orig_h))} px"

            # width label at midpoint of top edge
            wx = rx + rw // 2
            wy = ry - max(12, font.get_linesize())
            try:
                base_wshadow = font.render(width_txt, True, (10,10,10))
                base_wimg = font.render(width_txt, True, (255,220,80))
                s = max(0.01, float(label_scale))
                tw = max(1, int(base_wimg.get_width() * s))
                th = max(1, int(base_wimg.get_height() * s))
                try:
                    wshadow = pygame.transform.smoothscale(base_wshadow, (tw, th))
                    wimg = pygame.transform.smoothscale(base_wimg, (tw, th))
                except Exception:
                    wshadow = pygame.transform.scale(base_wshadow, (tw, th))
                    wimg = pygame.transform.scale(base_wimg, (tw, th))
                # position so nearest edge is base_offset from rect
                base_offset = max(4, self.width * 3)
                padding = 4
                wy = int(ry - (wimg.get_height() // 2 + base_offset + padding))
                surface.blit(wshadow, (wx - wshadow.get_width()//2 + 1, wy + 1))
                surface.blit(wimg, (wx - wimg.get_width()//2, wy))
            except Exception:
                pass

            # height label at midpoint of left edge (draw vertically by rendering normally and positioning)
            hx = rx - max(30, font.get_linesize() + 6)
            hy = ry + rh // 2
            try:
                base_hshadow = font.render(height_txt, True, (10,10,10))
                base_himg = font.render(height_txt, True, (255,220,80))
                s2 = max(0.01, float(label_scale))
                tw2 = max(1, int(base_himg.get_width() * s2))
                th2 = max(1, int(base_himg.get_height() * s2))
                try:
                    hshadow = pygame.transform.smoothscale(base_hshadow, (tw2, th2))
                    himg = pygame.transform.smoothscale(base_himg, (tw2, th2))
                except Exception:
                    hshadow = pygame.transform.scale(base_hshadow, (tw2, th2))
                    himg = pygame.transform.scale(base_himg, (tw2, th2))
                base_offset_h = max(4, self.width * 3)
                padding_h = 4
                # left label midpoint; shift horizontally so nearest edge is base_offset_h from rect
                hx = int(rx - (himg.get_width() // 2 + base_offset_h + padding_h))
                hy = int(ry + rh // 2)
                surface.blit(hshadow, (hx + 1, hy - hshadow.get_height()//2 + 1))
                surface.blit(himg, (hx, hy - himg.get_height()//2))
            except Exception:
                pass

    def to_dict(self):
        return {
            'type': self.type,
            'p1': [self.p1[0], self.p1[1]],
            'p2': [self.p2[0], self.p2[1]],
            'color': list(self.color),
            'width': self.width
        }

    @classmethod
    def from_dict(cls, d):
        p1 = tuple(d.get('p1', (0,0)))
        p2 = tuple(d.get('p2', (0,0)))
        color = tuple(d.get('color', (255,200,50)))
        width = d.get('width', 2)
        return cls(p1, p2, color=color, width=width)

    def hit_test(self, sx, sy, image_rect, image_scale, tol=8):
        # screen rect
        x1 = int(image_rect.x + self.p1[0] * image_scale)
        y1 = int(image_rect.y + self.p1[1] * image_scale)
        x2 = int(image_rect.x + self.p2[0] * image_scale)
        y2 = int(image_rect.y + self.p2[1] * image_scale)
        rx = min(x1, x2)
        ry = min(y1, y2)
        rw = abs(x2 - x1)
        rh = abs(y2 - y1)
        # inside rect
        if rx - tol <= sx <= rx + rw + tol and ry - tol <= sy <= ry + rh + tol:
            return True
        return False

    def move_by(self, dx_orig, dy_orig):
        self.p1 = (self.p1[0] + dx_orig, self.p1[1] + dy_orig)
        self.p2 = (self.p2[0] + dx_orig, self.p2[1] + dy_orig)

    def hit_test_handle(self, sx, sy, image_rect, image_scale, tol=8):
        # corners: 0=(x1,y1),1=(x2,y1),2=(x1,y2),3=(x2,y2)
        x1 = int(image_rect.x + self.p1[0] * image_scale)
        y1 = int(image_rect.y + self.p1[1] * image_scale)
        x2 = int(image_rect.x + self.p2[0] * image_scale)
        y2 = int(image_rect.y + self.p2[1] * image_scale)
        rx = min(x1, x2)
        ry = min(y1, y2)
        rw = abs(x2 - x1)
        rh = abs(y2 - y1)
        corners = [(rx, ry), (rx + rw, ry), (rx, ry + rh), (rx + rw, ry + rh)]
        for i, (cx, cy) in enumerate(corners):
            if (sx - cx) ** 2 + (sy - cy) ** 2 <= tol * tol:
                return i
        return None

    def move_handle(self, idx, dx_orig, dy_orig):
        # move the corner indicated by idx; dx_orig/dy_orig are in original-image pixels
        x1, y1 = self.p1
        x2, y2 = self.p2
        # compute canonical min/max for rectangle
        xmin = min(x1, x2)
        xmax = max(x1, x2)
        ymin = min(y1, y2)
        ymax = max(y1, y2)

        # idx mapping: 0=(xmin,ymin)=top-left, 1=(xmax,ymin)=top-right,
        # 2=(xmin,ymax)=bottom-left, 3=(xmax,ymax)=bottom-right
        new_xmin = xmin
        new_xmax = xmax
        new_ymin = ymin
        new_ymax = ymax

        # horizontal: idx 0 or 2 -> move xmin; idx 1 or 3 -> move xmax
        if idx in (0, 2):
            new_xmin = xmin + dx_orig
        else:
            new_xmax = xmax + dx_orig

        # vertical: idx 0 or 1 -> move ymin; idx 2 or 3 -> move ymax
        if idx in (0, 1):
            new_ymin = ymin + dy_orig
        else:
            new_ymax = ymax + dy_orig

        # assign back to p1/p2 in arbitrary order (canonicalize)
        self.p1 = (new_xmin, new_ymin)
        self.p2 = (new_xmax, new_ymax)
