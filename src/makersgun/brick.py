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
        inner = rect.inflate(-max(2, scaling.to_screen_length(3)), -max(2, scaling.to_screen_length(3)))
        pygame.draw.rect(surf, self.color, inner)
