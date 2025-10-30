import math
import pygame
from src import scaling
from src.npc import Particle


class Bike:
    """A simple bike-like object composed of a few particles.

    Structure (rough):
      - p : root particle (frame center)
      - seat : seat particle (where NPC can sit)
      - pedal : pedal center particle
      - back_wheel, front_wheel : wheel particles

    The object exposes a `p` attribute and `size` so it can be used in
    collision code that expects Brick-like objects. It supports being
    dragged by MakersGun (which moves `p`) and will keep child parts
    positioned relative to `p` using simple constraint solves.
    """

    def __init__(self, pos, size=140, color=(30, 120, 200)):
        try:
            base = pygame.math.Vector2(pos)
        except Exception:
            base = pygame.math.Vector2((0, 0))

        self.size = size
        self.color = color
        # representative root particle (used by MakersGun collision/picking)
        self.p = Particle(base, mass=2.0)

        # build parts relative to root
        # use larger separations for a taller frame relative to NPC
        s_off = pygame.math.Vector2(0, -size * 0.22)
        fw_off = pygame.math.Vector2(size * 0.45, size * 0.30)
        bw_off = pygame.math.Vector2(-size * 0.45, size * 0.30)
        ped_off = pygame.math.Vector2(0, size * 0.09)

        self.seat = Particle(base + s_off, mass=1.0)
        self.front_wheel = Particle(base + fw_off, mass=0.8)
        self.back_wheel = Particle(base + bw_off, mass=0.8)
        self.pedal = Particle(base + ped_off, mass=0.6)

        # store rest local offsets so we can gently spring parts back into
        # an upright pose (prevents frame collapse and keeps handlebars up)
        try:
            self._rest_offsets = {
                self.seat: s_off,
                self.front_wheel: fw_off,
                self.back_wheel: bw_off,
                self.pedal: ped_off,
            }
        except Exception:
            self._rest_offsets = {}

        # convenience list and constraints
        self.parts = [self.p, self.seat, self.front_wheel, self.back_wheel, self.pedal]
        # constraints: (index_a, index_b, rest_length)
        self.constraints = []
        def add_conn(a, b, slack=0.0):
            pa = self.parts[a]
            pb = self.parts[b]
            dist = (pa.pos - pb.pos).length() * (1.0 + slack)
            self.constraints.append((a, b, dist))

        # frame connections
        add_conn(0, 1)  # root <-> seat
        add_conn(0, 2)  # root <-> front wheel
        add_conn(0, 3)  # root <-> back wheel
        add_conn(0, 4)  # root <-> pedal
        add_conn(4, 2)  # pedal <-> front wheel (crank link)
        add_conn(4, 3)  # pedal <-> back wheel (chain-ish link)

        # rider reference
        self.rider = None
        self._time = 0.0

        # visual rotation states
        self.front_angle = 0.0
        self.back_angle = 0.0
        # driving state
        self.drive_vel = 0.0        # current horizontal driving velocity (px/s)
        self.drive_accel = 800.0    # acceleration when input applied (px/s^2)
        self.drive_max = 480.0      # maximum horizontal speed (px/s)

    def mount(self, npc):
        """Attach an NPC to this bike and immediately snap them into a
        riding pose: torso on the seat, head above seat, arms toward
        handlebars, legs to pedals. This is an immediate snap (no slow
        interpolation) to make the NPC appear to mount the bike the
        moment they touch the seat.
        """
        try:
            self.rider = npc
            try:
                npc.stand_enabled = False
            except Exception:
                pass

            # determine facing based on wheel positions
            try:
                facing = 1 if self.front_wheel.pos.x >= self.back_wheel.pos.x else -1
                npc.facing = facing
            except Exception:
                pass

            # mark npc as mounted on this bike so controllers can route input
            try:
                setattr(npc, 'mounted_bike', self)
            except Exception:
                pass

            # torso (index 2) to seat
            try:
                torso_idx = 2
                rt = npc.particles[torso_idx]
                target = self.seat.pos + pygame.math.Vector2(0, -max(6, self.size * 0.06))
                rt.pos = target
                rt.prev = rt.pos.copy()
            except Exception:
                pass

            # head slightly above torso
            try:
                head_idx = 0
                hp = npc.particles[head_idx]
                hp.pos = rt.pos + pygame.math.Vector2(0, -max(18, self.size * 0.08))
                hp.prev = hp.pos.copy()
            except Exception:
                pass

            # handlebars position (approx front of bike)
            try:
                hb = self.front_wheel.pos + pygame.math.Vector2(-self.size * 0.08 * (1 if facing >= 0 else -1), -self.size * 0.22)
            except Exception:
                hb = self.front_wheel.pos

            # arms (indices 5 = left, 6 = right) reach to handlebars
            try:
                l_arm_idx = 5
                r_arm_idx = 6
                npc.particles[l_arm_idx].pos = rt.pos + (hb - rt.pos) * 0.5 + pygame.math.Vector2(-8 * facing, -6)
                npc.particles[l_arm_idx].prev = npc.particles[l_arm_idx].pos.copy()
                npc.particles[r_arm_idx].pos = rt.pos + (hb - rt.pos) * 0.5 + pygame.math.Vector2(8 * facing, -6)
                npc.particles[r_arm_idx].prev = npc.particles[r_arm_idx].pos.copy()
            except Exception:
                pass

            # legs to pedals (indices 7 and 8)
            try:
                ang = (self._time * 8.0) % (math.pi * 2)
                pedal_center = self.pedal.pos
                leg_x = max(8, self.size * 0.06)
                leg_y = max(4, self.size * 0.03)
                left_pos = pedal_center + pygame.math.Vector2(math.cos(ang) * leg_x, math.sin(ang) * leg_y)
                right_pos = pedal_center + pygame.math.Vector2(math.cos(ang + math.pi) * leg_x, math.sin(ang + math.pi) * leg_y)
                try:
                    npc.particles[7].pos = left_pos
                    npc.particles[7].prev = left_pos.copy()
                except Exception:
                    pass
                try:
                    npc.particles[8].pos = right_pos
                    npc.particles[8].prev = right_pos.copy()
                except Exception:
                    pass
            except Exception:
                pass

        except Exception:
            # best-effort; if anything fails keep rider variable set
            try:
                self.rider = npc
            except Exception:
                pass

    def unmount(self):
        try:
            if self.rider is not None:
                try:
                    self.rider.stand_enabled = True
                except Exception:
                    pass
            # clear mounted reference on npc if present
            try:
                if self.rider is not None and hasattr(self.rider, 'mounted_bike'):
                    try:
                        delattr(self.rider, 'mounted_bike')
                    except Exception:
                        try:
                            setattr(self.rider, 'mounted_bike', None)
                        except Exception:
                            pass
            except Exception:
                pass
            self.rider = None
        except Exception:
            self.rider = None

    def drive(self, vx, dt):
        """Apply a simple horizontal drive command to the bike.

        This method is intentionally simple: it applies a velocity-like
        translation to the bike's root particle and nudges child parts so
        the whole assembly moves. The rider remains locked to the seat in
        update(), so driving will move both bike and rider.
        """
        try:
            # vx is the raw input passed from controllers (positive/negative).
            # If any input is present we accelerate toward `drive_max` in the
            # input direction so holding the key longer increases speed.
            if abs(vx) > 1e-3:
                target = self.drive_max * (1 if vx > 0 else -1)
            else:
                target = 0.0

            if abs(target) > 1e-3:
                # accelerate toward target
                if self.drive_vel < target:
                    self.drive_vel += self.drive_accel * dt
                    if self.drive_vel > target:
                        self.drive_vel = target
                elif self.drive_vel > target:
                    self.drive_vel -= self.drive_accel * dt
                    if self.drive_vel < target:
                        self.drive_vel = target
            else:
                # no input: decay toward zero (coast/brake)
                if self.drive_vel > 0:
                    self.drive_vel -= self.drive_accel * 1.5 * dt
                    if self.drive_vel < 0:
                        self.drive_vel = 0.0
                elif self.drive_vel < 0:
                    self.drive_vel += self.drive_accel * 1.5 * dt
                    if self.drive_vel > 0:
                        self.drive_vel = 0.0

            # apply the integrated drive velocity into the verlet integration
            try:
                self.p.prev.x = self.p.pos.x - self.drive_vel * dt
            except Exception:
                pass

            # gently nudge other parts to follow root for stability
            for part in self.parts:
                if part is self.p:
                    continue
                try:
                    part.pos.x += self.drive_vel * dt * 0.15
                except Exception:
                    pass

            # visual wheel rotation scaled by actual drive velocity
            try:
                self.front_angle += self.drive_vel * 0.02
                self.back_angle += self.drive_vel * 0.02
            except Exception:
                pass
        except Exception:
            pass

    def apply_force(self, f):
        # apply to main root
        try:
            self.p.apply_force(f)
        except Exception:
            pass

    def update(self, dt, floor_y=None, other_bricks=None):
        # integrate parts
        self._time += dt
        gravity = pygame.math.Vector2(0, 900)
        for p in self.parts:
            p.apply_force(gravity * getattr(p, 'mass', 1.0))
            p.update(dt)

        # constraint solve (iterative) - increase iterations for stability
        for _ in range(12):
            for ia, ib, rest in list(self.constraints):
                pa = self.parts[ia]
                pb = self.parts[ib]
                delta = pb.pos - pa.pos
                d = delta.length()
                if d == 0:
                    continue
                diff = (d - rest) / d
                # move each particle proportionally to their mass
                ma = max(1e-6, getattr(pa, 'mass', 1.0))
                mb = max(1e-6, getattr(pb, 'mass', 1.0))
                total = ma + mb
                pa.pos += delta * 0.5 * diff * (mb / total)
                pb.pos -= delta * 0.5 * diff * (ma / total)

        # Positional spring: gently pull parts back to their rest offsets
        # relative to the root particle to keep the frame standing tall.
        try:
            k = 8.0  # spring strength
            corr = min(1.0, k * dt)
            root_pos = self.p.pos
            for part, offset in list(self._rest_offsets.items()):
                try:
                    target = root_pos + offset
                    # small nudge toward target (preserve prev to avoid popping)
                    delta = target - part.pos
                    part.pos += delta * corr
                    # damp previous to match new position gently
                    part.prev = part.pos - (part.pos - part.prev) * 0.5
                except Exception:
                    continue
        except Exception:
            pass

        # floor collision for parts - use per-part effective radius so wheels rest on the floor
        if floor_y is not None:
            if hasattr(floor_y, 'get_floor_y'):
                fy = floor_y.get_floor_y()
            else:
                fy = floor_y
            if fy is not None:
                for p in self.parts:
                    # choose an appropriate collision radius per part
                    if p is self.front_wheel or p is self.back_wheel:
                        r = self.size * 0.28
                    elif p is self.pedal:
                        r = self.size * 0.06
                    elif p is self.seat:
                        r = self.size * 0.08
                    else:
                        r = self.size * 0.10

                    if p.pos.y > fy - r:
                        p.pos.y = fy - r
                        vel = p.pos - p.prev
                        vel.y = 0
                        # apply friction (grounded) and damping
                        vel.x *= 0.35
                        p.prev = p.pos - vel

        # If a rider is mounted, immediately lock key NPC particles into
        # riding pose each update so the NPC appears seated/controlling the
        # bike without delay.
        if self.rider is not None:
            try:
                rider = self.rider
                # ensure standing corrections are disabled
                try:
                    rider.stand_enabled = False
                except Exception:
                    pass

                # torso center -> seat (hard set)
                try:
                    torso_idx = 2
                    rt = rider.particles[torso_idx]
                    target = self.seat.pos + pygame.math.Vector2(0, -max(6, self.size * 0.06))
                    rt.pos = target
                    rt.prev = target.copy()
                except Exception:
                    pass

                # head above torso
                try:
                    head_idx = 0
                    hp = rider.particles[head_idx]
                    hp.pos = rt.pos + pygame.math.Vector2(0, -max(18, self.size * 0.08))
                    hp.prev = hp.pos.copy()
                except Exception:
                    pass

                # handlebars target
                try:
                    facing = getattr(rider, 'facing', 1)
                    hb = self.front_wheel.pos + pygame.math.Vector2(-self.size * 0.08 * (1 if facing >= 0 else -1), -self.size * 0.22)
                except Exception:
                    hb = self.front_wheel.pos

                # arms reach toward handlebars (hard set)
                try:
                    l_arm_idx = 5
                    r_arm_idx = 6
                    la_pos = rt.pos + (hb - rt.pos) * 0.5 + pygame.math.Vector2(-max(8, self.size * 0.04), -6)
                    ra_pos = rt.pos + (hb - rt.pos) * 0.5 + pygame.math.Vector2(max(8, self.size * 0.04), -6)
                    rider.particles[l_arm_idx].pos = la_pos
                    rider.particles[l_arm_idx].prev = la_pos.copy()
                    rider.particles[r_arm_idx].pos = ra_pos
                    rider.particles[r_arm_idx].prev = ra_pos.copy()
                except Exception:
                    pass

                # legs to pedals (hard set, animated)
                try:
                    ang = (self._time * 8.0) % (math.pi * 2)
                    pedal_center = self.pedal.pos
                    leg_x = max(8, self.size * 0.06)
                    leg_y = max(4, self.size * 0.03)
                    left_pos = pedal_center + pygame.math.Vector2(math.cos(ang) * leg_x, math.sin(ang) * leg_y)
                    right_pos = pedal_center + pygame.math.Vector2(math.cos(ang + math.pi) * leg_x, math.sin(ang + math.pi) * leg_y)
                    try:
                        rider.particles[7].pos = left_pos
                        rider.particles[7].prev = left_pos.copy()
                    except Exception:
                        pass
                    try:
                        rider.particles[8].pos = right_pos
                        rider.particles[8].prev = right_pos.copy()
                    except Exception:
                        pass
                except Exception:
                    pass

            except Exception:
                # if mounting fails for any reason, clear rider
                try:
                    self.rider = None
                except Exception:
                    self.rider = None

        # approximate wheel rotation by using horizontal velocity
        try:
            v_front = self.front_wheel.pos - self.front_wheel.prev
            v_back = self.back_wheel.pos - self.back_wheel.prev
            self.front_angle += v_front.x * 0.02
            self.back_angle += v_back.x * 0.02
        except Exception:
            pass

    def draw(self, surf):
        # detailed bicycle rendering (frame, fork, handlebars, saddle, rims, spokes, chainring)
        try:
            p0 = scaling.to_screen_vec(self.p.pos)
            pseat = scaling.to_screen_vec(self.seat.pos)
            pf = scaling.to_screen_vec(self.front_wheel.pos)
            pb = scaling.to_screen_vec(self.back_wheel.pos)
            pp = scaling.to_screen_vec(self.pedal.pos)

            # parameters scaled to bike size
            rim_r = max(8, int(scaling.to_screen_length(self.size * 0.28)))
            rim_thickness = max(2, int(scaling.to_screen_length(3)))
            frame_w = max(2, int(scaling.to_screen_length(3)))
            small_w = max(1, int(scaling.to_screen_length(1)))

            # colors
            frame_col = self.color  # typically blue
            metal_col = (40, 40, 40)
            rim_col = (10, 10, 10)
            spoke_col = (180, 180, 180)
            saddle_col = (120, 70, 30)
            chain_col = (90, 90, 90)

            # Draw rims (outer black rim + inner highlight)
            pygame.draw.circle(surf, rim_col, (int(pb.x), int(pb.y)), rim_r + rim_thickness)
            pygame.draw.circle(surf, rim_col, (int(pf.x), int(pf.y)), rim_r + rim_thickness)
            pygame.draw.circle(surf, (30, 30, 30), (int(pb.x), int(pb.y)), rim_r)
            pygame.draw.circle(surf, (30, 30, 30), (int(pf.x), int(pf.y)), rim_r)

            # spokes: more spokes for the pixel-art look
            spoke_count = max(10, int(self.size // 9))
            for i in range(spoke_count):
                a = self.back_angle + (i / float(spoke_count)) * math.tau
                sx = int(pb.x + math.cos(a) * rim_r * 0.82)
                sy = int(pb.y + math.sin(a) * rim_r * 0.82)
                pygame.draw.line(surf, spoke_col, (pb.x, pb.y), (sx, sy), small_w)
            for i in range(spoke_count):
                a = self.front_angle + (i / float(spoke_count)) * math.tau
                sx = int(pf.x + math.cos(a) * rim_r * 0.82)
                sy = int(pf.y + math.sin(a) * rim_r * 0.82)
                pygame.draw.line(surf, spoke_col, (pf.x, pf.y), (sx, sy), small_w)

            # chainring / pedals: draw center square + chainring circle
            cr_x = int(pp.x)
            cr_y = int(pp.y)
            cr_r = max(6, int(scaling.to_screen_length(self.size * 0.06)))
            pygame.draw.circle(surf, metal_col, (cr_x, cr_y), cr_r + 2)
            pygame.draw.circle(surf, (120, 120, 120), (cr_x, cr_y), cr_r)

            # chain: simple line from chainring to rear hub
            try:
                pygame.draw.line(surf, chain_col, (cr_x + 4, cr_y), (int(pb.x - rim_r * 0.25), int(pb.y)), max(2, small_w))
            except Exception:
                pass

            # Frame: draw main tubes (top tube, down tube, seat tube, chainstay, seatstay, fork)
            # coordinates in screen space for readability
            top = (pseat.x, pseat.y - max(2, scaling.to_screen_length(2)))
            root = (p0.x, p0.y)
            rear = (pb.x, pb.y)
            front = (pf.x, pf.y)
            pedal = (pp.x, pp.y)

            # top tube (slightly offset to look like pixel frame)
            pygame.draw.line(surf, frame_col, top, front, frame_w)
            pygame.draw.line(surf, frame_col, top, root, frame_w)
            # down tube
            pygame.draw.line(surf, frame_col, root, pedal, frame_w)
            # chainstay and seatstay to rear hub
            pygame.draw.line(surf, frame_col, pedal, rear, frame_w)
            pygame.draw.line(surf, frame_col, top, rear, frame_w)
            # fork to front hub
            fork_mid = (root[0] + (front[0] - root[0]) * 0.6, root[1] + (front[1] - root[1]) * 0.4)
            pygame.draw.line(surf, frame_col, fork_mid, front, frame_w)

            # handlebars
            hb_x = front[0] - max(6, scaling.to_screen_length(6))
            hb_y = front[1] - max(20, scaling.to_screen_length(18))
            pygame.draw.line(surf, metal_col, (front[0] - 2, front[1] - 12), (hb_x, hb_y), frame_w)
            pygame.draw.rect(surf, saddle_col, pygame.Rect(int(pseat.x - scaling.to_screen_length(8)), int(pseat.y - scaling.to_screen_length(6)), int(scaling.to_screen_length(16)), int(scaling.to_screen_length(6))))

            # handlebars grip and stem
            pygame.draw.line(surf, (80, 80, 80), (hb_x - 8, hb_y), (hb_x + 8, hb_y), max(2, small_w))

            # highlight on frame (thin lighter line)
            try:
                hl = (min(255, frame_col[0] + 40), min(255, frame_col[1] + 40), min(255, frame_col[2] + 40))
                pygame.draw.line(surf, hl, (top[0] + 1, top[1] - 1), (front[0] + 1, front[1] - 1), max(1, small_w))
                pygame.draw.line(surf, hl, (root[0] + 1, root[1] - 1), (pedal[0] + 1, pedal[1] - 1), max(1, small_w))
            except Exception:
                pass

            # small details: hub dots
            pygame.draw.circle(surf, (60, 60, 60), (int(pb.x), int(pb.y)), max(3, int(scaling.to_screen_length(3))))
            pygame.draw.circle(surf, (60, 60, 60), (int(pf.x), int(pf.y)), max(3, int(scaling.to_screen_length(3))))

        except Exception:
            pass

    def draw_debug(self, surf):
        # optional: draw particle positions
        try:
            for p in self.parts:
                pos = scaling.to_screen_vec(p.pos)
                pygame.draw.circle(surf, (255, 0, 0), (int(pos.x), int(pos.y)), 3)
        except Exception:
            pass
