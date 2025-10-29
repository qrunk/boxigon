import pygame
from src import scaling
from src.npc import Particle
from .brick import Brick


class Crate(Brick):
    """A crate styled like a wooden warehouse crate.

    Crates reuse the Brick physics/behaviour but draw a different visual
    (wooden slats + metal bands).
    """

    def __init__(self, pos, size=48, mass=1.0, color=(170, 110, 60)):
        # Use Brick's particle and welding behaviour
        super().__init__(pos, size=size, mass=mass, color=color)
        # crate outline darker wood / metal
        self.outline = (60, 40, 20)

    def draw(self, surf):
        # similar to Brick.draw but use crate visual
        center = scaling.to_screen_vec(self.p.pos)
        s = scaling.to_screen_length(self.size)
        rect = pygame.Rect(0, 0, int(s), int(s))
        rect.center = (int(center.x), int(center.y))

        # draw crate pattern into rect
        try:
            draw_crate_pattern(surf, rect, color=self.color, outline=self.outline, border_radius=6)
        except Exception:
            try:
                pygame.draw.rect(surf, self.outline, rect)
                inner = rect.inflate(-max(2, int(scaling.to_screen_length(3))), -max(2, int(scaling.to_screen_length(3))))
                pygame.draw.rect(surf, self.color, inner)
            except Exception:
                pass


def draw_crate_pattern(surf, rect, color=None, outline=None, border_radius=4):
    """Draw a wooden crate pattern into rect.

    Simple, low-dependency rendering: outer outline, wooden fill, horizontal
    slats and two darker metal bands.
    """
    try:
        if color is None:
            color = (170, 110, 60)
        if outline is None:
            outline = (60, 40, 20)

        # Outline
        pygame.draw.rect(surf, outline, rect, border_radius=border_radius)

        # inner wood area
        inner = rect.inflate(-max(2, int(scaling.to_screen_length(3))), -max(2, int(scaling.to_screen_length(3))))
        pygame.draw.rect(surf, color, inner, border_radius=max(0, border_radius - 1))

        # slat color (slightly darker than base)
        slat_color = (max(0, color[0] - 20), max(0, color[1] - 20), max(0, color[2] - 20))
        slat_thickness = max(1, int(scaling.to_screen_length(3)))

        # draw 3 horizontal slats evenly spaced
        pw = max(2, inner.width)
        ph = max(2, inner.height)
        slat_count = 3
        for i in range(1, slat_count + 1):
            y = inner.top + int(round(i * (ph / (slat_count + 1))))
            pygame.draw.rect(surf, slat_color, pygame.Rect(inner.left, y - slat_thickness // 2, inner.width, slat_thickness))

        # draw two vertical metal bands (slightly darker / grey)
        band_color = (50, 50, 50)
        band_w = max(2, int(scaling.to_screen_length(3)))
        # left band and right band positions
        left_x = inner.left + int(inner.width * 0.18)
        right_x = inner.left + int(inner.width * 0.82)
        pygame.draw.rect(surf, band_color, pygame.Rect(left_x - band_w // 2, inner.top, band_w, inner.height))
        pygame.draw.rect(surf, band_color, pygame.Rect(right_x - band_w // 2, inner.top, band_w, inner.height))

        # small metal rivets along bands (d ots)
        rivet_color = (200, 200, 200)
        rivet_r = max(1, int(scaling.to_screen_length(1)))
        for bx in (left_x, right_x):
            for j in range(3):
                ry = inner.top + int((j + 1) * (ph / 4))
                pygame.draw.circle(surf, rivet_color, (bx, ry), rivet_r)
    except Exception:
        try:
            # fallback to simple rect
            if color is None:
                color = (170, 110, 60)
            pygame.draw.rect(surf, color, rect)
        except Exception:
            pass
