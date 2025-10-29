import pygame
from src import scaling
from src.npc import Particle


class Brick:
    """A simple square 'lego-like' brick backed by a single Verlet particle.

    This is a lightweight object (single particle) so it behaves like a
    point with a drawn square. It supports gravity and simple floor collision.
    """

    def __init__(self, pos, size=40, mass=1.0, color=(180, 30, 30)):
        self.p = Particle(pos, mass=mass)
        self.size = size
        self.color = color
        self.outline = (30, 10, 10)
        # If welded_to is not None this brick will follow that brick's
        # position with a fixed offset.
        self.welded_to = None
        self.welded_offset = pygame.math.Vector2(0, 0)
        # children welded to this brick (so we can move/iterate group)
        self.welded_children = []

    def get_root(self):
        """Return the top-most ancestor in the welded chain (self if none)."""
        cur = self
        seen = set()
        while getattr(cur, 'welded_to', None) is not None:
            # defensive: break cycles
            if id(cur) in seen:
                break
            seen.add(id(cur))
            cur = cur.welded_to
        return cur

    def add_weld(self, parent, offset=None):
        """Weld this brick to parent. Handles list bookkeeping."""
        try:
            if getattr(self, 'welded_to', None) is not None and self.welded_to is not parent:
                try:
                    self.welded_to.welded_children.remove(self)
                except Exception:
                    pass
        except Exception:
            pass
        self.welded_to = parent
        if offset is None:
            try:
                self.welded_offset = self.p.pos - parent.p.pos
            except Exception:
                self.welded_offset = pygame.math.Vector2(0, 0)
        else:
            self.welded_offset = offset
        try:
            if self not in parent.welded_children:
                parent.welded_children.append(self)
        except Exception:
            pass

    def remove_weld(self):
        """Unweld this brick from its parent (if any)."""
        try:
            if getattr(self, 'welded_to', None) is not None:
                try:
                    self.welded_to.welded_children.remove(self)
                except Exception:
                    pass
        except Exception:
            pass
        self.welded_to = None

    def apply_force(self, f):
        self.p.apply_force(f)

    def update(self, dt, floor_y=None, other_bricks=None):

        # If welded to another brick, follow that brick and don't simulate
        # independent physics. We'll still return early so stacked bricks
        # remain locked in place relative to their parent.
        if self.welded_to is not None:
            try:
                # If the target was removed, un-weld
                if other_bricks is not None and self.welded_to not in other_bricks:
                    self.remove_weld()
                else:
                    parent = self.welded_to
                    self.p.pos = parent.p.pos + self.welded_offset
                    parent_vel = parent.p.pos - parent.p.prev
                    self.p.prev = self.p.pos - parent_vel
            except Exception:
                self.remove_weld()

        gravity = pygame.math.Vector2(0, 900)
        self.p.apply_force(gravity * self.p.mass)
        self.p.update(dt)

        if floor_y is not None:
            if hasattr(floor_y, 'get_floor_y'):
                fy = floor_y.get_floor_y()
            else:
                fy = floor_y
            if fy is not None and self.p.pos.y > fy - (self.size / 2):
                self.p.pos.y = fy - (self.size / 2)
                if hasattr(floor_y, 'get_friction'):
                    friction = floor_y.get_friction()
                else:
                    friction = 0.35

                vel = self.p.pos - self.p.prev
                vel.y = 0
                vel.x *= friction
                self.p.prev = self.p.pos - vel

        if other_bricks:
            for other in other_bricks:
                if other != self:
                    # skip internal collisions within a welded group
                    try:
                        if hasattr(self, 'get_root') and hasattr(other, 'get_root'):
                            if self.get_root() is other.get_root():
                                continue
                    except Exception:
                        pass

                    diff = self.p.pos - other.p.pos
                    dist = diff.length()
                    min_dist = (self.size + other.size) / 2

                    if dist < min_dist and dist > 0:
                        norm = diff / dist
                        overlap = min_dist - dist
                        total_mass = self.p.mass + other.p.mass
                        self_ratio = other.p.mass / total_mass
                        other_ratio = self.p.mass / total_mass

                        self.p.pos += norm * overlap * self_ratio

                        self_vel = self.p.pos - self.p.prev
                        other_vel = other.p.pos - other.p.prev
                        rel_vel = self_vel - other_vel
                        vel_along_normal = rel_vel.dot(norm)

                        if vel_along_normal < 0:
                            restitution = 0.3
                            j = -(1 + restitution) * vel_along_normal
                            j /= 1 / self.p.mass + 1 / other.p.mass

                            impulse = norm * j

                            self.p.prev = self.p.pos - (self_vel + (impulse / self.p.mass))
                            other.p.prev = other.p.pos - (other_vel - (impulse / other.p.mass))

                        # Simple "snap/weld" behavior
                        try:
                            rel_speed = rel_vel.length()
                            vertical_indicator = norm.y
                            horiz_sep = abs(diff.x)
                            horiz_tol = (self.size + other.size) * 0.35
                            if vertical_indicator < -0.7 and rel_speed < 120 and horiz_sep < horiz_tol:
                                try:
                                    self.add_weld(other)
                                    parent_vel = other.p.pos - other.p.prev
                                    self.p.prev = self.p.pos - parent_vel
                                except Exception:
                                    self.welded_to = other
                                    self.welded_offset = self.p.pos - other.p.pos
                                    self.p.prev = self.p.pos.copy()
                        except Exception:
                            pass

    def draw(self, surf):
        center = scaling.to_screen_vec(self.p.pos)
        s = scaling.to_screen_length(self.size)
        rect = pygame.Rect(0, 0, int(s), int(s))
        rect.center = (int(center.x), int(center.y))
        pygame.draw.rect(surf, self.outline, rect)
        # inner drawing area (accounts for outline thickness)
        inner = rect.inflate(-max(2, int(scaling.to_screen_length(3))), -max(2, int(scaling.to_screen_length(3))))

        # Base brick color fill
        pygame.draw.rect(surf, self.color, inner)

        # Brick pattern: staggered rows with light mortar lines
        mortar_color = (220, 220, 220)
        mortar_thickness = max(1, int(scaling.to_screen_length(2)))

        # Determine rows/cols based on pixel size for a reasonable look
        pw = max(2, inner.width)  # pixel width
        ph = max(2, inner.height)
        rows = max(2, pw // 20)
        cols = max(2, pw // 15)

        brick_h = ph / rows
        brick_w = inner.width / cols

        # Draw horizontal mortar lines
        for r in range(rows + 1):
            y = inner.top + int(round(r * brick_h))
            pygame.draw.rect(surf, mortar_color, pygame.Rect(inner.left, y - mortar_thickness // 2, inner.width, mortar_thickness))

        # Draw vertical mortar lines for each row, staggered every other row
        for r in range(rows):
            row_top = inner.top + int(round(r * brick_h))
            row_h = int(round(brick_h))
            offset = 0 if (r % 2) == 0 else int(round(brick_w / 2))

            # start a bit left to ensure full coverage when offset is used
            start_x = inner.left - offset
            # draw vertical separators across the row
            c = 0
            while True:
                x = start_x + int(round(c * brick_w))
                if x > inner.right:
                    break
                # Draw the vertical mortar segment clipped to the row height
                seg_rect = pygame.Rect(x - mortar_thickness // 2, row_top, mortar_thickness, row_h)
                # Clip the rect to inner area to avoid drawing outside
                seg_rect.clamp_ip(inner)
                if seg_rect.width > 0 and seg_rect.height > 0:
                    pygame.draw.rect(surf, mortar_color, seg_rect)
                c += 1


def draw_brick_pattern(surf, rect, color=None, outline=None, border_radius=4):
    """Draw a brick-like pattern into the given pygame.Rect on surface.

    rect is in surface pixel coordinates. color/outline default to typical
    brick colors when not provided.
    """
    try:
        if color is None:
            color = (180, 30, 30)
        if outline is None:
            outline = (30, 10, 10)

        # Outline
        pygame.draw.rect(surf, outline, rect, border_radius=border_radius)

        # Inner area
        inner = rect.inflate(-max(2, int(scaling.to_screen_length(3))), -max(2, int(scaling.to_screen_length(3))))
        pygame.draw.rect(surf, color, inner, border_radius=max(0, border_radius - 1))

        # Brick pattern (mortar lines)
        mortar_color = (220, 220, 220)
        mortar_thickness = max(1, int(scaling.to_screen_length(2)))

        pw = max(2, inner.width)
        ph = max(2, inner.height)
        rows = max(2, pw // 20)
        cols = max(2, pw // 15)

        brick_h = ph / rows
        brick_w = inner.width / cols

        # Horizontal mortar
        for r in range(rows + 1):
            y = inner.top + int(round(r * brick_h))
            pygame.draw.rect(surf, mortar_color, pygame.Rect(inner.left, y - mortar_thickness // 2, inner.width, mortar_thickness))

        # Vertical mortar per row (staggered)
        for r in range(rows):
            row_top = inner.top + int(round(r * brick_h))
            row_h = int(round(brick_h))
            offset = 0 if (r % 2) == 0 else int(round(brick_w / 2))
            start_x = inner.left - offset
            c = 0
            while True:
                x = start_x + int(round(c * brick_w))
                if x > inner.right:
                    break
                seg_rect = pygame.Rect(x - mortar_thickness // 2, row_top, mortar_thickness, row_h)
                seg_rect.clamp_ip(inner)
                if seg_rect.width > 0 and seg_rect.height > 0:
                    pygame.draw.rect(surf, mortar_color, seg_rect)
                c += 1
    except Exception:
        # Best-effort: fallback to simple rect if pattern drawing fails
        try:
            if color is None:
                color = (180, 30, 30)
            pygame.draw.rect(surf, color, rect)
        except Exception:
            pass
