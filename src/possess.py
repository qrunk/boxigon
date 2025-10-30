import pygame
from src import scaling


class PossessionManager:
    """Manages possession mode: hover highlight, click to possess, control possessed NPC.

    Controls:
    - Toggle mode outside/inside with P (handled by app and forwarded here via toggle)
    - Click an NPC while in possess mode to possess it
    - A/D to move left/right, W or SPACE to jump
    - Mouse moves the head toward the cursor while possessed
    - Press P again (from app) to exit possession mode
    """

    def __init__(self):
        self.active = False
        self.hovered = None
        self.possessed_idx = None
        self.possessed = None
        self._jump_requested = False

        # tuning
        self.hover_radius = 60.0
        self.move_speed = 220.0
        self.jump_impulse = 220.0

    def toggle(self, npcs=None):
        # Toggle possession mode. If turning off, release any possession.
        self.active = not self.active
        if not self.active:
            self.release()
        else:
            # entering possession mode; clear hover/selection
            self.hovered = None
            self.possessed_idx = None
            self.possessed = None

    def release(self):
        # clear possessed flag on NPC if present
        try:
            if self.possessed is not None:
                setattr(self.possessed, 'possessed_controlled', False)
        except Exception:
            pass
        self.possessed_idx = None
        self.possessed = None
        self._jump_requested = False

    def handle_event(self, event, npcs):
        # Handle clicks to possess and keydowns for jump
        if not self.active:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Left click: try to possess hovered npc
            if self.hovered is not None and 0 <= self.hovered < len(npcs):
                self.possess(npcs, self.hovered)
                return True

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_w, pygame.K_SPACE):
                # request a jump; applied in update once grounded
                self._jump_requested = True
                return True

        return False

    def possess(self, npcs, idx):
        try:
            self.possessed_idx = idx
            self.possessed = npcs[idx]
            # give the NPC a facing attribute so drawing can flip the head
            try:
                setattr(self.possessed, 'facing', 1)
                setattr(self.possessed, 'possessed_controlled', True)
                # ensure standing behavior is enabled so the possessed body can be controlled
                try:
                    self.possessed.stand_enabled = True
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            self.possessed_idx = None
            self.possessed = None

    def update(self, dt, npcs, floor=None):
        if not self.active:
            return

        # update hovered NPC under mouse
        mx, my = pygame.mouse.get_pos()
        world_mouse = scaling.to_world_vec((mx, my))
        self.hovered = None
        best_d = self.hover_radius
        for i, npc in enumerate(npcs):
            try:
                center = npc.particles[2].pos
            except Exception:
                continue
            d = (center - world_mouse).length()
            if d < best_d:
                best_d = d
                self.hovered = i

        if self.possessed is None and (self.possessed_idx is not None):
            # try to rebind if the index exists
            if 0 <= self.possessed_idx < len(npcs):
                self.possessed = npcs[self.possessed_idx]
            else:
                self.possessed_idx = None

        # if possessed, control movement and head tracking
        if self.possessed is not None:
            keys = pygame.key.get_pressed()
            vx = 0.0
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                vx -= self.move_speed
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                vx += self.move_speed

            # set facing for drawing flip
            try:
                if vx < 0:
                    self.possessed.facing = -1
                elif vx > 0:
                    self.possessed.facing = 1
            except Exception:
                pass

            # If the possessed NPC is mounted on a bike, route input to the
            # bike so both NPC and bike move together. Otherwise fall back to
            # the old per-particle translation behavior.
            # Route input to mounted vehicles if present. Bikes are supported
            # historically; add cars here so a possessed NPC can drive a car.
            mounted_bike = getattr(self.possessed, 'mounted_bike', None)
            mounted_car = getattr(self.possessed, 'mounted_car', None)

            vehicle = None
            if mounted_bike is not None:
                vehicle = mounted_bike
            elif mounted_car is not None:
                vehicle = mounted_car

            if vehicle is not None:
                # update facing already done above; drive the vehicle
                try:
                    if vx != 0.0:
                        vehicle.drive(vx, dt)
                except Exception:
                    # fallback to moving the NPC directly if drive fails
                    vehicle = None

            if mounted_bike is None:
                # apply horizontal translation to all particles (simple but effective)
                if vx != 0.0:
                    # Apply a velocity to the torso (particle 2) so movement feels
                    # like controlling the body rather than teleporting every part.
                    try:
                        torso = self.possessed.particles[2]
                        torso.prev.x = torso.pos.x - vx * dt
                    except Exception:
                        pass
                    # small positional nudges for other particles to keep up
                    try:
                        for i, p in enumerate(self.possessed.particles):
                            if i == 2:
                                continue
                            p.pos.x += vx * dt * 0.15
                    except Exception:
                        pass

            # Keep the head straight above the torso while possessed.
            # Use the NPC's stored rest_local offset for the head but zero
            # the horizontal offset so the head is centered over the torso.
            try:
                head = self.possessed.particles[0]
                torso = self.possessed.particles[2].pos
                try:
                    # rest_local is the head offset relative to torso center
                    head_local = self.possessed.rest_local[0]
                    desired = pygame.math.Vector2(torso.x, torso.y + head_local.y)
                except Exception:
                    # fallback: use head_size to position above torso
                    desired = pygame.math.Vector2(torso.x, torso.y - getattr(self.possessed, 'head_size', 32))
                # set head position directly so it stays upright
                head.pos.x = desired.x
                head.pos.y = desired.y
            except Exception:
                pass

            # Jump handling: only if requested and grounded
            if self._jump_requested:
                self._jump_requested = False
                # detect grounded by checking any particle near floor
                grounded = False
                fy = None
                if floor is not None:
                    if hasattr(floor, 'get_floor_y'):
                        fy = floor.get_floor_y()
                # fallback: if no floor provided, assume ground at large y
                if fy is None:
                    fy = 10000

                for p in self.possessed.particles:
                    try:
                        if p.pos.y >= fy - (getattr(self.possessed, 'size', 14) / 2.0) - 1.0:
                            grounded = True
                            break
                    except Exception:
                        continue

                if grounded:
                    # apply upward impulse by setting prev below pos so vel.y is negative
                    for p in self.possessed.particles:
                        try:
                            p.prev.y = p.pos.y + self.jump_impulse
                        except Exception:
                            pass

    def draw(self, surf):
        # draw hover/possessed highlight when active
        if not self.active:
            return

        try:
            if self.possessed is not None:
                center = self.possessed.particles[2].pos
                c = scaling.to_screen_vec(center)
                rad = scaling.to_screen_length(60)
                pygame.draw.circle(surf, (240, 220, 24), (int(c.x), int(c.y)), rad, max(2, scaling.to_screen_length(2)))
            elif self.hovered is not None:
                mx, my = pygame.mouse.get_pos()
                pygame.draw.circle(surf, (240, 220, 24), (mx, my), max(6, scaling.to_screen_length(6)), 2)
        except Exception:
            pass
