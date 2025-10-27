import pygame 
from src import scaling 
from src .npc import Particle


class Thruster:
    """A simple thruster object backed by a single Verlet particle.

    Thrusters can be welded to other objects (via the WeldingTool). When
    welded they apply a continuous force to connected objects so they move
    or change direction.
    """

    def __init__ (self, pos, size=32, mass=1.0, icon=None):
        self.p = Particle(pos, mass=mass)
        self.size = size
        self.icon = icon
        self.color = (180, 140, 40)
        self.outline = (90, 60, 10)
        self.thrust_power = 1200.0

    def apply_force(self, f):
        try:
            self.p.apply_force(f)
        except Exception:
            pass

    def update(self, dt, floor_y=None, other_bricks=None):
        # simple gravity + floor collision similar to Brick
        gravity = pygame.math.Vector2(0, 900)
        try:
            self.p.apply_force(gravity * self.p.mass)
            self.p.update(dt)
        except Exception:
            pass

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

    def apply_thrust(self, dt, welding_tool=None, npcs=None, bricks=None):
        """Apply thrust forces to objects that are welded to this thruster.

        welding_tool: the WeldingTool instance (used to inspect joints).
        """
        if welding_tool is None:
            return

        try:
            for j in getattr(welding_tool, 'joints', []):
                a = j.get('a')
                b = j.get('b')
                if a is self or b is self:
                    other = b if a is self else a

                    # get other object's position (best-effort)
                    other_pos = None
                    if hasattr(other, 'p') and hasattr(other.p, 'pos'):
                        other_pos = other.p.pos
                    elif hasattr(other, 'particles'):
                        pts = [getattr(p, 'pos', None) for p in other.particles]
                        pts = [p for p in pts if p is not None]
                        if pts:
                            other_pos = sum(pts, pygame.math.Vector2(0, 0)) / len(pts)

                    if other_pos is None:
                        continue

                    diff = other_pos - self.p.pos
                    dist = diff.length()
                    if dist == 0:
                        continue
                    direction = diff / dist

                    # force applied to the other object (push away from thruster)
                    force = direction * self.thrust_power

                    try:
                        if hasattr(other, 'apply_force'):
                            other.apply_force(force)
                        elif hasattr(other, 'apply_global_force'):
                            other.apply_global_force(force)
                    except Exception:
                        pass

                    # small reaction on the thruster itself
                    try:
                        self.apply_force(-force * 0.1)
                    except Exception:
                        pass
        except Exception:
            pass

    def draw(self, surf):
        center = scaling.to_screen_vec(self.p.pos)
        if self.icon:
            ps = max(20, scaling.to_screen_length(self.size))
            try:
                img = pygame.transform.scale(self.icon, (ps, ps))
                surf.blit(img, (int(center.x - ps // 2), int(center.y - ps // 2)))
                return
            except Exception:
                pass

        s = scaling.to_screen_length(self.size)
        rect = pygame.Rect(0, 0, int(s), int(s))
        rect.center = (int(center.x), int(center.y))
        pygame.draw.rect(surf, self.outline, rect)
        inner = rect.inflate(-max(2, scaling.to_screen_length(3)), -max(2, scaling.to_screen_length(3)))
        pygame.draw.rect(surf, self.color, inner)
