import math
import random
import pygame
from src import scaling

try:
    # BloodManager is defined in src/guns/pistol.py
    from src.guns.pistol import BloodManager
except Exception:
    BloodManager = None


class Axe:
    """Simple axe tool used by the MakersGun.

    Behavior:
    - When held and moved, chops anything it touches (removes bricks).
    - When it touches an NPC it applies a heavy hit (calls apply_bullet_hit)
      and removes the NPC from the world (destroy).
    """

    def __init__(self, pos, icon=None):
        self.pos = pygame.math.Vector2(pos)
        self.held = False
        self.icon = icon

        # radius in world space for detecting chops
        self.radius = 36
        # local blood manager for hit effects (optional)
        self.blood = BloodManager() if BloodManager is not None else None

    def draw(self, surf):
        center = scaling.to_screen_vec(self.pos)
        if self.icon is not None:
            ps = max(24, scaling.to_screen_length(36))
            try:
                img = pygame.transform.scale(self.icon, (ps, ps))
                surf.blit(img, (int(center.x - ps // 2), int(center.y - ps // 2)))
                return
            except Exception:
                pass

        r = max(6, int(scaling.to_screen_length(self.radius)))
        pygame.draw.circle(surf, (200, 30, 30), (int(center.x), int(center.y)), r)
        pygame.draw.circle(surf, (120, 10, 10), (int(center.x), int(center.y)), r, 2)

        # draw blood effects (if any)
        try:
            if self.blood is not None:
                self.blood.draw(surf)
        except Exception:
            pass

    def update(self, npcs, bricks, floor=None):
        # Follow mouse when held
        if self.held:
            try:
                self.pos = pygame.math.Vector2(scaling.to_world(pygame.mouse.get_pos()))
            except Exception:
                self.pos = pygame.math.Vector2(pygame.mouse.get_pos())

        # Chop bricks: remove any brick whose center is within radius
        if bricks:
            to_remove = []
            for b in list(bricks):
                try:
                    if (b.p.pos - self.pos).length() < self.radius:
                        to_remove.append(b)
                except Exception:
                    continue
            for b in to_remove:
                try:
                    bricks.remove(b)
                except Exception:
                    pass

        # Hit NPCs: apply a hit (like pistol) and spawn blood effects, but do not
        # instantly remove the NPC (allow apply_bullet_hit to modify particles).
        if npcs:
            for npc in list(npcs):
                # find nearest particle
                try:
                    idx = npc.nearest_particle_index(self.pos, max_dist=self.radius)
                except Exception:
                    idx = None
                if idx is not None:
                    try:
                        hit_pos = npc.particles[idx].pos.copy()
                        try:
                            npc.apply_bullet_hit(hit_pos)
                        except Exception:
                            pass

                        # spawn blood particles similar to pistol.Bullet
                        if self.blood is not None:
                            # emit several pixel blood particles
                            for _ in range(10):
                                ang = random.uniform(-math.pi, math.pi)
                                spd = random.uniform(120, 420)
                                vel = pygame.math.Vector2(math.cos(ang) * spd, math.sin(ang) * spd * 0.6)
                                try:
                                    self.blood.emit_pixel(hit_pos + pygame.math.Vector2(random.uniform(-4, 4), random.uniform(-4, 4)), vel, color=(160, 10, 10))
                                except Exception:
                                    continue
                            # splash (puddle) if floor is known
                            fy_local = None
                            if floor is not None:
                                if hasattr(floor, 'get_floor_y'):
                                    fy_local = floor.get_floor_y()
                                else:
                                    fy_local = floor
                            try:
                                self.blood.splash(hit_pos, amount=6, floor_y=fy_local)
                            except Exception:
                                pass
                    except Exception:
                        continue

        # update blood effects
        try:
            f_y = None
            if floor is not None:
                if hasattr(floor, 'get_floor_y'):
                    f_y = floor.get_floor_y()
                else:
                    f_y = floor
            if self.blood is not None:
                # step the blood simulation with a modest dt; MakersGun.update
                # calls this frequently so small fixed dt is acceptable
                self.blood.update(0.016, floor_y=f_y)
        except Exception:
            pass
