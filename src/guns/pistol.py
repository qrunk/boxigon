import math
import os
import random
import pygame
from src import scaling
from src.guns.core import register_gun, Gun


class Bullet:
    def __init__(self, pos, vel, size=6, color=(250, 220, 30)):
        self.pos = pygame.math.Vector2(pos)
        self.vel = pygame.math.Vector2(vel)
        self.size = size
        self.color = color
        self.alive = True
        self.life = 3.0

    def update(self, dt, npcs=None, floor=None, blood_mgr=None):
        gravity = pygame.math.Vector2(0, 240)
        self.vel += gravity * dt
        self.pos += self.vel * dt
        self.life -= dt
        if self.life <= 0:
            self.alive = False

        if floor is not None:
            if hasattr(floor, 'get_floor_y'):
                fy = floor.get_floor_y()
            else:
                fy = floor
            if fy is not None and self.pos.y > fy:
                if blood_mgr is not None:
                    blood_mgr.splash(self.pos, amount=3, floor_y=fy)
                self.alive = False
                return

        if npcs:
            for npc in npcs:
                idx = npc.nearest_particle_index(self.pos, max_dist=24)
                if idx is not None:
                    hit_pos = npc.particles[idx].pos.copy()
                    npc.apply_bullet_hit(hit_pos)

                    if blood_mgr is not None:
                        for _ in range(10):
                            ang = random.uniform(-math.pi, math.pi)
                            spd = random.uniform(120, 420)
                            vel = pygame.math.Vector2(math.cos(ang) * spd, math.sin(ang) * spd * 0.6)
                            blood_mgr.emit_pixel(
                                self.pos + pygame.math.Vector2(random.uniform(-4, 4), random.uniform(-4, 4)),
                                vel,
                                color=(160, 10, 10),
                            )
                        fy_local = None
                        if floor is not None:
                            if hasattr(floor, 'get_floor_y'):
                                fy_local = floor.get_floor_y()
                            else:
                                fy_local = floor
                        blood_mgr.splash(self.pos, amount=6, floor_y=fy_local)
                    self.alive = False
                    return

    def draw(self, surf):
        try:
            center = scaling.to_screen_vec(self.pos)
            w = max(1, scaling.to_screen_length(self.size))
            h = max(1, scaling.to_screen_length(int(self.size * 0.5)))
            rect = pygame.Rect(0, 0, w, h)
            rect.center = (int(center.x), int(center.y))
            pygame.draw.rect(surf, self.color, rect)
        except Exception:
            pass


class BloodParticle:
    def __init__(self, pos, vel, color=(140, 0, 0), pixel=False):
        self.pos = pygame.math.Vector2(pos)
        self.vel = pygame.math.Vector2(vel)
        if pixel:
            self.radius = random.uniform(2.6, 6.0)
            self.life = random.uniform(2.0, 4.0)
        else:
            self.radius = random.uniform(1.2, 3.6)
            self.life = random.uniform(1.2, 3.0)
        self.color = color
        self.grounded = False
        self.pixel = pixel

    def update(self, dt, floor_y=None):
        if self.grounded:
            self.life -= dt * 0.2
            return
        self.vel += pygame.math.Vector2(0, 1200) * dt
        self.pos += self.vel * dt
        # Grounding: only set grounded when the particle is contacting the floor
        # and either moving downward (vel.y > 0) or is very close to the floor.
        # This avoids particles becoming 'stuck' mid-air due to numeric or
        # coordinate mismatches when spawned inside geometry.
        # Prefer the provided floor_y (e.g. Baseplate.get_floor_y()). If not
        # provided, fall back to the global design floor. This ensures blood
        # falls to the bottom of the baseplate when available rather than to
        # the entire window height.
        try:
            from src import scaling as _scaling
            global_floor = getattr(_scaling, 'DESIGN_H', None)
        except Exception:
            global_floor = None

        effective_floor = floor_y if floor_y is not None else global_floor

        if effective_floor is not None and self.pos.y >= effective_floor:
            # small tolerance to allow particles to pass near the floor when
            # they are still moving upward
            close_eps = 4.0
            if self.vel.y > 0 or (self.pos.y - effective_floor) < close_eps:
                self.pos.y = effective_floor
                self.grounded = True
                self.radius *= 0.6
                # remove downward velocity and damp horizontal
                self.vel.y = 0
                self.vel.x *= 0.3
                # debug
                try:
                    import os
                    if os.environ.get('BOXIGON_DEBUG_BLOOD', '0') == '1':
                        print(f"[BloodParticle.ground] pos={self.pos} vel={self.vel} floor={effective_floor}")
                except Exception:
                    pass

    def draw(self, surf):
        try:
            p = scaling.to_screen_vec(self.pos)
            # don't draw grounded pixels (they form puddles) to avoid
            # large visible clusters composed of many small rects
            if self.grounded:
                return
            if not self.pixel:
                return
            size = max(1, int(scaling.to_screen_length(self.radius * 2.0)))
            rect = pygame.Rect(int(p.x - size // 2), int(p.y - size // 2), size, size)
            pygame.draw.rect(surf, self.color, rect)
        except Exception:
            pass


class Puddle:
    def __init__(self, pos):
        self.pos = pygame.math.Vector2(pos)
        self.amount = 1.0

    def add(self, amt):
        self.amount += amt

    def draw(self, surf):
        # intentionally do not draw large puddle circles (visuals removed)
        return


class BloodManager:
    def __init__(self):
        self.particles = []
        self.puddles = []
        # debug flag (set env BOXIGON_DEBUG_BLOOD=1 to enable)
        try:
            self._debug = bool(int(os.environ.get('BOXIGON_DEBUG_BLOOD', '0')))
        except Exception:
            self._debug = False

    def emit(self, pos, vel):
        self.particles.append(BloodParticle(pos, vel, pixel=True))

    def emit_pixel(self, pos, vel, color=(160, 10, 10)):
        self.particles.append(BloodParticle(pos, vel, color=color, pixel=True))

    def splash(self, pos, amount=4, floor_y=None):
        try:
            target_pos = pygame.math.Vector2(pos)
        except Exception:
            target_pos = pygame.math.Vector2(pos)
        # default to global design floor to ensure puddles appear on the
        # main ground surface rather than on intermediate objects
        try:
            from src import scaling as _scaling
            if floor_y is None:
                floor_y = getattr(_scaling, 'DESIGN_H', floor_y)
        except Exception:
            pass

        if floor_y is not None and target_pos.y < floor_y:
            target_pos.y = floor_y
        if self._debug:
            print(f"[BloodManager.splash] pos={pos} -> target_pos={target_pos} floor_y={floor_y} amount={amount}")
        if not self.puddles:
            self.puddles.append(Puddle(target_pos))
        else:
            best = None
            bd = 9999
            for p in self.puddles:
                d = (p.pos - target_pos).length()
                if d < bd:
                    bd = d
                    best = p
            if bd < 48:
                best.add(amount * 0.5)
            else:
                self.puddles.append(Puddle(target_pos))

    def update(self, dt, floor_y=None):
        for bp in list(self.particles):
            bp.update(dt, floor_y=floor_y)
            if bp.life <= 0:
                self.splash(bp.pos, amount=1.0, floor_y=floor_y)
                try:
                    self.particles.remove(bp)
                except Exception:
                    pass
        if self._debug:
            print(f"[BloodManager.update] particles={len(self.particles)} puddles={len(self.puddles)}")

    def draw(self, surf):
        for p in self.puddles:
            p.draw(surf)
        for bp in self.particles:
            bp.draw(surf)


@register_gun('Pistol')
class Pistol(Gun):
    def __init__(self, pos, icon=None):
        super().__init__(pos, icon)
        self.bullets = []
        self.blood = BloodManager()
        self._cooldown = 0.0
        self.fire_rate = 8.0
        # default flip behavior (matches previous behavior)
        self.flip = True

    def shoot(self, target_world_pos):
        if self._cooldown > 0:
            return
        self._cooldown = 1.0 / max(1e-6, self.fire_rate)
        dir = pygame.math.Vector2(target_world_pos) - self.pos
        if dir.length() == 0:
            dir = pygame.math.Vector2(1, 0)
        dir = dir.normalize()
        if getattr(self, 'flip', True):
            dir = -dir

        spread = math.radians(6.0)
        ang = math.atan2(dir.y, dir.x) + random.uniform(-spread, spread)
        speed = random.uniform(900, 1400)
        vel = pygame.math.Vector2(math.cos(ang) * speed, math.sin(ang) * speed)

        spawn = self.pos + dir * 12
        b = Bullet(spawn, vel)
        self.bullets.append(b)

        for _ in range(6):
            ang2 = ang + random.uniform(-0.35, 0.35)
            spd2 = random.uniform(180, 520)
            vel2 = pygame.math.Vector2(math.cos(ang2) * spd2, math.sin(ang2) * spd2 * 0.3)
            self.blood.emit_pixel(
                spawn + pygame.math.Vector2(random.uniform(-2, 2), random.uniform(-2, 2)), vel2, color=(255, 200, 60)
            )

    def update(self, dt, npcs=None, floor=None):
        if self._cooldown > 0:
            self._cooldown -= dt

        if self.held:
            try:
                self.pos = pygame.math.Vector2(scaling.to_world(pygame.mouse.get_pos()))
            except Exception:
                self.pos = pygame.math.Vector2(pygame.mouse.get_pos())

        for b in list(self.bullets):
            b.update(dt, npcs=npcs, floor=floor, blood_mgr=self.blood)
            if not b.alive:
                try:
                    self.bullets.remove(b)
                except Exception:
                    pass

        f_y = None
        if floor is not None:
            if hasattr(floor, 'get_floor_y'):
                f_y = floor.get_floor_y()
            else:
                f_y = floor
        self.blood.update(dt, floor_y=f_y)

    def draw(self, surf):
        for b in self.bullets:
            b.draw(surf)
        self.blood.draw(surf)

        try:
            center = scaling.to_screen_vec(self.pos)
            if self.icon is not None:
                ps = max(12, scaling.to_screen_length(20))
                img = pygame.transform.scale(self.icon, (ps, ps))
                surf.blit(img, (int(center.x - ps // 2), int(center.y - ps // 2)))
            else:
                pygame.draw.circle(
                    surf, (200, 200, 40), (int(center.x), int(center.y)), max(6, scaling.to_screen_length(8))
                )
        except Exception:
            pass
                            # Removed stray line
