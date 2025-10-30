import math
import os
import random
import pygame
from src import scaling
from src.npc import Particle


class Car:
	"""A simple car-like drivable object.

	Mirrors the `Bike` interface so it can be mounted by NPCs and driven by
	player controllers. Exposes `p` and `size` and implements `mount`,
	`unmount`, `drive`, `apply_force`, `update`, and `draw`.
	"""

	def __init__(self, pos, size=220, color=None):
		try:
			base = pygame.math.Vector2(pos)
		except Exception:
			base = pygame.math.Vector2((0, 0))

		self.size = size
		# choose color randomly red or blue if not provided
		if color is None:
			self.color = random.choice([(180, 30, 30), (30, 120, 200)])
		else:
			self.color = color
		# outline/dark variant
		self.outline = tuple(max(0, c - 40) for c in self.color)

		# root particle representing vehicle center
		self.p = Particle(base, mass=4.0)

		# offsets for parts relative to root
		seat_off = pygame.math.Vector2(0, -size * 0.06)
		fw_off = pygame.math.Vector2(size * 0.42, size * 0.22)
		bw_off = pygame.math.Vector2(-size * 0.42, size * 0.22)
		roof_off = pygame.math.Vector2(0, -size * 0.25)

		self.seat = Particle(base + seat_off, mass=1.2)
		self.front_wheel = Particle(base + fw_off, mass=1.0)
		self.back_wheel = Particle(base + bw_off, mass=1.0)
		self.roof = Particle(base + roof_off, mass=1.0)

		# rest offsets for posing
		try:
			self._rest_offsets = {
				self.seat: seat_off,
				self.front_wheel: fw_off,
				self.back_wheel: bw_off,
				self.roof: roof_off,
			}
		except Exception:
			self._rest_offsets = {}

		self.parts = [self.p, self.seat, self.front_wheel, self.back_wheel, self.roof]

		# constraints between parts: (index_a, index_b, rest_length)
		self.constraints = []

		def add_conn(a, b, slack=0.0):
			pa = self.parts[a]
			pb = self.parts[b]
			dist = (pa.pos - pb.pos).length() * (1.0 + slack)
			self.constraints.append((a, b, dist))

		# connect body frame
		add_conn(0, 1)
		add_conn(0, 2)
		add_conn(0, 3)
		add_conn(0, 4)
		add_conn(4, 2)
		add_conn(4, 3)

		# occupant reference (single rider for now)
		self.rider = None
		self._time = 0.0

		# visual wheel rotation
		self.front_angle = 0.0
		self.back_angle = 0.0

		# driving state - cars heavier, slower acceleration but higher momentum
		self.drive_vel = 0.0
		self.drive_accel = 900.0
		self.drive_max = 360.0

		# optional sprite for exact car artwork (place `car.png` in
		# `src/vehicles/assets/car.png`). If present we will blit and
		# scale it to match `size`. Otherwise we use procedural drawing.
		self.sprite = None
		self._sprite_orig_size = None
		try:
			base = os.path.join(os.path.dirname(__file__), 'assets')
			path = os.path.join(base, 'car.png')
			if os.path.exists(path):
				self.sprite = pygame.image.load(path).convert_alpha()
				try:
					self._sprite_orig_size = self.sprite.get_size()
				except Exception:
					self._sprite_orig_size = None
		except Exception:
			self.sprite = None

	def mount(self, npc):
		try:
			self.rider = npc
			try:
				npc.stand_enabled = False
			except Exception:
				pass

			try:
				setattr(npc, 'mounted_car', self)
			except Exception:
				pass

			# snap torso to seat
			try:
				torso_idx = 2
				rt = npc.particles[torso_idx]
				target = self.seat.pos + pygame.math.Vector2(0, -max(6, self.size * 0.05))
				rt.pos = target
				rt.prev = rt.pos.copy()
			except Exception:
				pass

			# head above torso
			try:
				head_idx = 0
				hp = npc.particles[head_idx]
				hp.pos = rt.pos + pygame.math.Vector2(0, -max(18, self.size * 0.06))
				hp.prev = hp.pos.copy()
			except Exception:
				pass

			# arms toward dashboard (approx roof/front)
			try:
				facing = 1 if self.front_wheel.pos.x >= self.back_wheel.pos.x else -1
				npc.facing = facing
			except Exception:
				pass

			try:
				l_arm_idx = 5
				r_arm_idx = 6
				hb = self.roof.pos + pygame.math.Vector2(-self.size * 0.06, self.size * 0.06)
				npc.particles[l_arm_idx].pos = rt.pos + (hb - rt.pos) * 0.5 + pygame.math.Vector2(-8 * getattr(npc, 'facing', 1), -6)
				npc.particles[l_arm_idx].prev = npc.particles[l_arm_idx].pos.copy()
				npc.particles[r_arm_idx].pos = rt.pos + (hb - rt.pos) * 0.5 + pygame.math.Vector2(8 * getattr(npc, 'facing', 1), -6)
				npc.particles[r_arm_idx].prev = npc.particles[r_arm_idx].pos.copy()
			except Exception:
				pass

		except Exception:
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
			try:
				if self.rider is not None and hasattr(self.rider, 'mounted_car'):
					try:
						delattr(self.rider, 'mounted_car')
					except Exception:
						try:
							setattr(self.rider, 'mounted_car', None)
						except Exception:
							pass
			except Exception:
				pass
		except Exception:
			pass
		self.rider = None

	def drive(self, vx, dt):
		try:
			if abs(vx) > 1e-3:
				target = self.drive_max * (1 if vx > 0 else -1)
			else:
				target = 0.0

			if abs(target) > 1e-3:
				if self.drive_vel < target:
					self.drive_vel += self.drive_accel * dt
					if self.drive_vel > target:
						self.drive_vel = target
				elif self.drive_vel > target:
					self.drive_vel -= self.drive_accel * dt
					if self.drive_vel < target:
						self.drive_vel = target
			else:
				# decay
				if self.drive_vel > 0:
					self.drive_vel -= self.drive_accel * 1.2 * dt
					if self.drive_vel < 0:
						self.drive_vel = 0.0
				elif self.drive_vel < 0:
					self.drive_vel += self.drive_accel * 1.2 * dt
					if self.drive_vel > 0:
						self.drive_vel = 0.0

			try:
				self.p.prev.x = self.p.pos.x - self.drive_vel * dt
			except Exception:
				pass

			for part in self.parts:
				if part is self.p:
					continue
				try:
					part.pos.x += self.drive_vel * dt * 0.12
				except Exception:
					pass

			try:
				self.front_angle += self.drive_vel * 0.015
				self.back_angle += self.drive_vel * 0.015
			except Exception:
				pass
		except Exception:
			pass

	def apply_force(self, f):
		try:
			self.p.apply_force(f)
		except Exception:
			pass

	def update(self, dt, floor_y=None, other_bricks=None):
		self._time += dt
		gravity = pygame.math.Vector2(0, 900)
		for p in self.parts:
			p.apply_force(gravity * getattr(p, 'mass', 1.0))
			p.update(dt)

		for _ in range(10):
			for ia, ib, rest in list(self.constraints):
				pa = self.parts[ia]
				pb = self.parts[ib]
				delta = pb.pos - pa.pos
				d = delta.length()
				if d == 0:
					continue
				diff = (d - rest) / d
				ma = max(1e-6, getattr(pa, 'mass', 1.0))
				mb = max(1e-6, getattr(pb, 'mass', 1.0))
				total = ma + mb
				pa.pos += delta * 0.5 * diff * (mb / total)
				pb.pos -= delta * 0.5 * diff * (ma / total)

		try:
			k = 8.0
			corr = min(1.0, k * dt)
			root_pos = self.p.pos
			for part, offset in list(self._rest_offsets.items()):
				try:
					target = root_pos + offset
					delta = target - part.pos
					part.pos += delta * corr
					part.prev = part.pos - (part.pos - part.prev) * 0.5
				except Exception:
					continue
		except Exception:
			pass

		if floor_y is not None:
			if hasattr(floor_y, 'get_floor_y'):
				fy = floor_y.get_floor_y()
			else:
				fy = floor_y
			if fy is not None:
				for p in self.parts:
					# use a smaller collision radius for wheels so they sit on the
					# ground consistently with the reduced visual tire size
					if p is self.front_wheel or p is self.back_wheel:
						r = self.size * 0.15
					elif p is self.seat:
						r = self.size * 0.09
					else:
						r = self.size * 0.12

					if p.pos.y > fy - r:
						p.pos.y = fy - r
						vel = p.pos - p.prev
						vel.y = 0
						vel.x *= 0.35
						p.prev = p.pos - vel

		# lock rider to seat if mounted
		if self.rider is not None:
			try:
				rider = self.rider
				try:
					rider.stand_enabled = False
				except Exception:
					pass

				try:
					torso_idx = 2
					rt = rider.particles[torso_idx]
					target = self.seat.pos + pygame.math.Vector2(0, -max(6, self.size * 0.05))
					rt.pos = target
					rt.prev = target.copy()
				except Exception:
					pass

				try:
					head_idx = 0
					hp = rider.particles[head_idx]
					hp.pos = rt.pos + pygame.math.Vector2(0, -max(18, self.size * 0.06))
					hp.prev = hp.pos.copy()
				except Exception:
					pass

				try:
					facing = getattr(rider, 'facing', 1)
					hb = self.roof.pos + pygame.math.Vector2(-self.size * 0.06 * (1 if facing >= 0 else -1), -self.size * 0.02)
				except Exception:
					hb = self.roof.pos

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

			except Exception:
				pass

	def draw(self, surf):
		# more detailed car side profile
		try:
			sw = scaling.to_screen_vec(self.p.pos)
			# Increase body width/height so the car body and cabin read larger
			# relative to the wheels. Wheels will be scaled down separately.
			w = scaling.to_screen_length(self.size * 1.15)
			h = scaling.to_screen_length(self.size * 0.52)

			# base coordinates for body
			cx = int(sw.x)
			cy = int(sw.y + scaling.to_screen_length(self.size * 0.02))

			# main lower body rect (long skirt)
			lower = pygame.Rect(0, 0, int(w * 0.9), int(h * 0.55))
			lower.center = (cx, cy + int(h * 0.18))

			# roof/top polygon with slight hood and trunk slopes
			roof_w = int(w * 0.78)
			roof_h = int(h * 0.55)
			roof_left = cx - roof_w // 2
			roof_right = cx + roof_w // 2
			roof_top = cy - int(h * 0.28)
			roof_bottom = roof_top + roof_h

			# Points: hood slope, windshield, roof, rear window, trunk slope
			roof_pts = [
				(roof_left + int(roof_w * 0.06), roof_bottom),  # front lower
				(roof_left + int(roof_w * 0.18), roof_top + int(roof_h * 0.06)),  # windshield base
				(roof_left + int(roof_w * 0.42), roof_top),  # roof front
				(roof_left + int(roof_w * 0.58), roof_top),  # roof rear
				(roof_left + int(roof_w * 0.82), roof_top + int(roof_h * 0.06)),  # rear window base
				(roof_left + int(roof_w * 0.94), roof_bottom),  # trunk lower
			]

			# main body rectangle (long sedan skirt)
			body_w = int(w * 0.95)
			body_h = int(h * 0.42)
			body_rect = pygame.Rect(0, 0, body_w, body_h)
			body_rect.center = (cx, cy + int(h * 0.12))

			# draw body outline then fill (slight corner radius)
			rad = max(2, scaling.to_screen_length(6))
			pygame.draw.rect(surf, self.outline, body_rect, border_radius=rad)
			inner_body = body_rect.inflate(-max(6, scaling.to_screen_length(12)), -max(6, scaling.to_screen_length(8)))
			pygame.draw.rect(surf, self.color, inner_body, border_radius=rad)

			# roof and cabin: polygon to make hood and trunk slopes
			roof_w = int(w * 0.72)
			roof_h = int(h * 0.46)
			roof_left = cx - roof_w // 2
			roof_top = cy - int(h * 0.28)
			pts = [
				(roof_left + int(roof_w * 0.05), roof_top + int(roof_h * 0.62)),  # hood lower
				(roof_left + int(roof_w * 0.20), roof_top + int(roof_h * 0.08)),  # windshield base
				(roof_left + int(roof_w * 0.45), roof_top),  # roof front
				(roof_left + int(roof_w * 0.65), roof_top),  # roof rear
				(roof_left + int(roof_w * 0.85), roof_top + int(roof_h * 0.62)),  # trunk lower
			]
			pygame.draw.polygon(surf, self.outline, pts)
			inset_pts = [(x, y + max(1, int(h * 0.02))) for (x, y) in pts]
			pygame.draw.polygon(surf, self.color, inset_pts)

			# windows: two-panel (front/rear) dark glass
			win_color = (40, 40, 45)
			try:
				fw_x = roof_left + int(roof_w * 0.22)
				fw_y = roof_top + int(roof_h * 0.10)
				rw_x = roof_left + int(roof_w * 0.62)
				rw_y = fw_y
				window_rect = pygame.Rect(fw_x, fw_y, max(2, rw_x - fw_x), max(2, int(roof_h * 0.28)))
				pygame.draw.rect(surf, win_color, window_rect, border_radius=max(1, scaling.to_screen_length(3)))
				# small separator between windows
				sep_x = fw_x + (window_rect.w // 2)
				pygame.draw.line(surf, tuple(min(255, c + 30) for c in self.outline), (sep_x, window_rect.y + 2), (sep_x, window_rect.y + window_rect.h - 2), max(1, scaling.to_screen_length(2)))
			except Exception:
				pass

			# door seam and handles (central vertical seam near middle)
			try:
				seam_x = cx - int(body_w * 0.06)
				seam_top = roof_top + int(roof_h * 0.12)
				seam_bot = body_rect.bottom - int(h * 0.02)
				pygame.draw.line(surf, tuple(max(0, c - 30) for c in self.outline), (seam_x, seam_top), (seam_x, seam_bot), max(1, scaling.to_screen_length(2)))
				# handles - small white L-shaped markers
				hh = max(1, scaling.to_screen_length(4))
				pygame.draw.rect(surf, (230, 230, 230), pygame.Rect(seam_x - hh * 5, seam_top + int((seam_bot - seam_top) * 0.48), hh * 3, hh))
				pygame.draw.rect(surf, (230, 230, 230), pygame.Rect(seam_x + hh * 2, seam_top + int((seam_bot - seam_top) * 0.48), hh * 3, hh))
			except Exception:
				pass

			# side mirror near front window
			try:
				mirror_x = roof_left + int(roof_w * 0.78)
				mirror_y = roof_top + int(roof_h * 0.18)
				pygame.draw.rect(surf, tuple(max(0, c - 30) for c in self.outline), pygame.Rect(mirror_x, mirror_y, max(2, scaling.to_screen_length(6)), max(2, scaling.to_screen_length(4))))
			except Exception:
				pass

			# gas flap at rear quarter
			try:
				gf_w = max(2, scaling.to_screen_length(6))
				gas_x = body_rect.right - int(body_w * 0.10)
				gas_y = body_rect.y + int(body_h * 0.28)
				pygame.draw.rect(surf, tuple(max(0, c - 30) for c in self.outline), pygame.Rect(gas_x, gas_y, gf_w, gf_w))
			except Exception:
				pass

			# wheel-arches: draw dark inset above tires to mimic the cutout
			try:
				fw_scr = scaling.to_screen_vec(self.front_wheel.pos)
				bw_scr = scaling.to_screen_vec(self.back_wheel.pos)
				# slightly narrower arches so they don't dominate the silhouette
				# reduced to match the smaller tire sizing below
				arch_w = int(scaling.to_screen_length(self.size * 0.20))
				arch_h = int(arch_w * 0.6)
				pygame.draw.ellipse(surf, tuple(max(0, c - 30) for c in self.outline), pygame.Rect(int(fw_scr.x - arch_w/2), int(fw_scr.y - arch_h/2), arch_w, arch_h))
				pygame.draw.ellipse(surf, tuple(max(0, c - 30) for c in self.outline), pygame.Rect(int(bw_scr.x - arch_w/2), int(bw_scr.y - arch_h/2), arch_w, arch_h))
			except Exception:
				pass

			# prepare screen-space wheel coords and radius (used by sprite alignment
			# and by procedural wheel drawing)
			try:
				fw = scaling.to_screen_vec(self.front_wheel.pos)
				bw = scaling.to_screen_vec(self.back_wheel.pos)
				# reduce tire size a bit further so wheels are less dominant
				r_w = max(2, scaling.to_screen_length(self.size * 0.14))
			except Exception:
				fw = pygame.math.Vector2(cx + body_w // 3, cy)
				bw = pygame.math.Vector2(cx - body_w // 3, cy)
				r_w = max(2, scaling.to_screen_length(self.size * 0.14))

			# If a sprite is available, draw it scaled and anchored to the
			# vehicle position so the art matches exactly. Otherwise fall back
			# to procedural wheels/hubcap drawing.
			if self.sprite is not None and self._sprite_orig_size is not None:
				try:
					orig_w, orig_h = self._sprite_orig_size
					# target width in screen pixels aligned to world `size`
					target_w = max(2, scaling.to_screen_length(self.size * 0.9))
					scale = target_w / float(orig_w)
					target_h = max(2, int(orig_h * scale))
					scaled = pygame.transform.smoothscale(self.sprite, (int(target_w), int(target_h)))
					sw = scaling.to_screen_vec(self.p.pos)
					# anchor: horizontally center on p, and vertically place so
					# wheels line up with wheel particles (estimate offset)
					try:
						fw_y = fw.y
						bw_y = bw.y
						wheels_y = int((fw_y + bw_y) * 0.5)
						dest_x = int(sw.x - scaled.get_width() // 2)
						dest_y = int(wheels_y - scaled.get_height() + max(0, scaling.to_screen_length(6)))
					except Exception:
						dest_x = int(sw.x - scaled.get_width() // 2)
						dest_y = int(sw.y - scaled.get_height() // 2)
					surf.blit(scaled, (dest_x, dest_y))
					return
				except Exception:
					# fallback to procedural wheels if sprite blit fails
					pass

			# tire
			pygame.draw.circle(surf, (20, 20, 20), (int(fw.x), int(fw.y)), int(r_w))
			pygame.draw.circle(surf, (20, 20, 20), (int(bw.x), int(bw.y)), int(r_w))

			# hubcap (scaled down proportionally)
			rim_r = int(max(1, r_w * 0.46))
			pygame.draw.circle(surf, self.outline, (int(fw.x), int(fw.y)), rim_r)
			pygame.draw.circle(surf, self.outline, (int(bw.x), int(bw.y)), rim_r)

			# small center
			pygame.draw.circle(surf, (40, 40, 40), (int(fw.x), int(fw.y)), max(1, int(r_w * 0.12)))
			pygame.draw.circle(surf, (40, 40, 40), (int(bw.x), int(bw.y)), max(1, int(r_w * 0.12)))

			# simple spoke lines
			try:
				for a in range(6):
					ang = a * (math.pi * 2 / 6) + self.front_angle * 0.01
					fx = int(fw.x + math.cos(ang) * rim_r * 0.6)
					fy = int(fw.y + math.sin(ang) * rim_r * 0.6)
					pygame.draw.line(surf, (80, 80, 80), (int(fw.x), int(fw.y)), (fx, fy), max(1, scaling.to_screen_length(1)))
					bx = int(bw.x + math.cos(ang) * rim_r * 0.6)
					by = int(bw.y + math.sin(ang) * rim_r * 0.6)
					pygame.draw.line(surf, (80, 80, 80), (int(bw.x), int(bw.y)), (bx, by), max(1, scaling.to_screen_length(1)))
			except Exception:
				pass
		except Exception:
			pass

