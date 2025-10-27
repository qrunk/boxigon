import math
import pygame

"""Simple global collision utilities used by NPC particles and bricks.

This module provides:
- Brick wrapper helpers (AABB) for MakersGun bricks
- Collision resolution between Verlet particles (point-like) and AABBs
- Floor collision helper compatible with objects that implement
  get_floor_y()/get_friction() or a plain numeric floor y value.

The resolution strategy is intentionally simple but robust:
- Treat particles as circles with a configurable radius (defaults to particle_size/2). Bricks are treated as axis-aligned squares
  (AABBs) centered on their particle position.
- When penetration is detected we compute a minimum-translation-vector
  (MTV) to push the particle out and then update the particle's
  previous position to modify its velocity according to restitution
  (bounce) and horizontal friction.

This keeps the verlet integration approach used elsewhere in the
project (particles maintain pos/prev) and is compatible with the
existing `Baseplate` and `MakersGun.Brick` logic.
"""


def _point_to_aabb_mtv(px, py, ax, ay, aw, ah):
    """Return minimum translation vector (dx,dy) to move point (px,py)
    out of the AABB defined by center (ax,ay) and size (aw,ah).

    If the point is outside the AABB already, (0,0) is returned.
    """
    # compute AABB min/max
    half_w = aw * 0.5
    half_h = ah * 0.5
    min_x = ax - half_w
    max_x = ax + half_w
    min_y = ay - half_h
    max_y = ay + half_h

    # If point outside, no MTV (for point vs AABB). Caller should use
    # distance-to-closest-point when considering particle radius.
    if px < min_x or px > max_x or py < min_y or py > max_y:
        return 0.0, 0.0

    # point inside AABB: find smallest axis penetration to push out
    left_pen = px - min_x
    right_pen = max_x - px
    top_pen = py - min_y
    bottom_pen = max_y - py

    # find smallest penetration
    m = min(left_pen, right_pen, top_pen, bottom_pen)
    if m == left_pen:
        return -left_pen, 0.0
    if m == right_pen:
        return right_pen, 0.0
    if m == top_pen:
        return 0.0, -top_pen
    return 0.0, bottom_pen


def resolve_particle_vs_aabb(particle, aabb_center, aabb_size, radius=None, bounce=0.0, friction=0.6):
    """Resolve collision between a Verlet-like particle and an AABB.

    Arguments:
        particle: object with .pos (Vector2) and .prev (Vector2) and optional .mass
        aabb_center: (x,y) center of the AABB in world coords
        aabb_size: scalar size (square) or (w,h) tuple
        radius: particle collision radius (defaults to particle_size/2 or 8)
        bounce: restitution factor for normal (0..1). 0 = no bounce.
        friction: horizontal multiplier applied to tangent velocity when grounded.

    This function mutates particle.pos and particle.prev to remove penetration
    and apply an impulse-like velocity change consistent with verlet integration.
    """
    try:
        px = float(particle.pos.x)
        py = float(particle.pos.y)
    except Exception:
        return

    if isinstance(aabb_size, (tuple, list)):
        aw, ah = aabb_size
    else:
        aw = ah = float(aabb_size)

    ax, ay = aabb_center

    # closest point on AABB to the particle
    half_w = aw * 0.5
    half_h = ah * 0.5
    min_x = ax - half_w
    max_x = ax + half_w
    min_y = ay - half_h
    max_y = ay + half_h

    closest_x = max(min_x, min(px, max_x))
    closest_y = max(min_y, min(py, max_y))

    dx = px - closest_x
    dy = py - closest_y
    dist_sq = dx * dx + dy * dy

    if radius is None:
        # default sensible radius; many calling sites use ~14 as particle size
        radius = getattr(particle, 'radius', None)
        if radius is None:
            radius = getattr(particle, 'size', None)
            if radius is not None:
                radius = float(radius) * 0.5
            else:
                radius = 8.0

    if dist_sq > (radius * radius):
        # no collision
        return

    dist = math.sqrt(dist_sq) if dist_sq > 0.0 else 0.0

    # if the particle center is exactly on the closest point (i.e. inside AABB
    # and centered), produce a fallback normal pointing up
    if dist == 0.0:
        # push upwards by default
        nx, ny = 0.0, -1.0
        penetration = radius
    else:
        nx = dx / dist
        ny = dy / dist
        penetration = radius - dist

    # Minimum translation vector to remove penetration
    mtv_x = nx * penetration
    mtv_y = ny * penetration

    # Push particle out of the AABB
    particle.pos.x += mtv_x
    particle.pos.y += mtv_y

    # Compute pre/post collision velocities via pos-prev
    vel = particle.pos - particle.prev

    # Reflect normal component according to restitution (bounce). For a
    # shallow collision we'll mainly zero the normal and optionally bounce.
    vel_n = vel.x * nx + vel.y * ny

    if vel_n < 0:  # approaching
        # remove normal component and apply restitution
        vel.x -= vel_n * nx
        vel.y -= vel_n * ny
        vel.x += -vel_n * nx * bounce
        vel.y += -vel_n * ny * bounce

    # Apply tangential (approx horizontal) friction if the collision normal is close to vertical
    # This prevents particles from endlessly sliding along surfaces.
    # When normal is mostly vertical (abs(ny) > 0.5) treat as grounded.
    if abs(ny) > 0.5:
        vel.x *= friction

    # write velocity back to prev so verlet integration uses the new velocity
    particle.prev = particle.pos - vel


def collide_particles_with_bricks(particles, bricks, particle_radius=None, bounce=0.0, friction=0.6, iterations=1):
    """Resolve collisions between a list of particles and maker bricks.

    Parameters:
        particles: iterable of objects with .pos/.prev
        bricks: iterable of objects with .p (Particle with .pos) and .size
        particle_radius: default collision radius for particles (None => infer per-particle)
        iterations: number of solver passes (higher -> more stable)
    """
    if not bricks:
        return

    for _ in range(max(1, int(iterations))):
        for p in particles:
            for b in bricks:
                try:
                    center = (b.p.pos.x, b.p.pos.y)
                    size = getattr(b, 'size', None)
                    if size is None:
                        # fallback small square
                        size = 40
                    resolve_particle_vs_aabb(p, center, size, radius=particle_radius, bounce=bounce, friction=friction)
                except Exception:
                    # be defensive — don't let a single brick/payload crash the loop
                    continue


def collide_particles_with_floor(particles, floor_obj, particle_size_attr='size'):
    """Apply simple floor collision for a collection of particles.

    floor_obj may be either a numeric y value or an object exposing
    get_floor_y() and optionally get_friction(). The function will
    clamp particles above the floor and apply friction to horizontal
    velocity similar to existing code in the project.
    """
    if floor_obj is None:
        return

    if hasattr(floor_obj, 'get_floor_y'):
        fy = floor_obj.get_floor_y()
        friction = getattr(floor_obj, 'get_friction', lambda: 0.6)()
    else:
        fy = floor_obj
        friction = 0.6

    if fy is None:
        return

    for p in particles:
        # infer particle radius from attribute if available
        size = getattr(p, particle_size_attr, None)
        if size is None:
            radius = 8.0
        else:
            radius = float(size) * 0.5

        if p.pos.y > fy - (radius):
            p.pos.y = fy - (radius)
            vel = p.pos - p.prev
            vel.y = 0
            vel.x *= max(0.0, friction)
            p.prev = p.pos - vel
            # extra damping to avoid slow horizontal drift
            try:
                p.prev.x = p.pos.x
            except Exception:
                pass


def aabb_for_brick(brick):
    """Return (center_x, center_y), (w,h) for the given makersgun Brick-like object."""
    try:
        cx = brick.p.pos.x
        cy = brick.p.pos.y
        s = getattr(brick, 'size', 40)
        return (cx, cy), (s, s)
    except Exception:
        return (0.0, 0.0), (0.0, 0.0)


def raycast_aabb(origin, direction, max_dist, aabb_center, aabb_size):
    """Raycast (origin, direction) against a square AABB centered at aabb_center.

    Returns (hit, t, hit_pos, normal) where t is distance along ray (<=max_dist)
    or (False, None, None, None) on miss.
    """
    # Convert to parametric ray p(t) = origin + dir * t
    # Use slab method on AABB
    if isinstance(aabb_size, (tuple, list)):
        aw, ah = aabb_size
    else:
        aw = ah = float(aabb_size)
    ax, ay = aabb_center
    half_w = aw * 0.5
    half_h = ah * 0.5
    min_bx = ax - half_w
    max_bx = ax + half_w
    min_by = ay - half_h
    max_by = ay + half_h

    dirx, diry = float(direction[0]), float(direction[1])
    ox, oy = float(origin[0]), float(origin[1])

    tmin = -1e9
    tmax = 1e9
    normal = None

    # X slab
    if abs(dirx) < 1e-8:
        if ox < min_bx or ox > max_bx:
            return False, None, None, None
    else:
        tx1 = (min_bx - ox) / dirx
        tx2 = (max_bx - ox) / dirx
        if tx1 > tx2:
            tx1, tx2 = tx2, tx1
        if tx1 > tmin:
            tmin = tx1
            normal = (-1.0 if dirx > 0 else 1.0, 0.0)
        if tx2 < tmax:
            tmax = tx2

    # Y slab
    if abs(diry) < 1e-8:
        if oy < min_by or oy > max_by:
            return False, None, None, None
    else:
        ty1 = (min_by - oy) / diry
        ty2 = (max_by - oy) / diry
        if ty1 > ty2:
            ty1, ty2 = ty2, ty1
        if ty1 > tmin:
            tmin = ty1
            normal = (0.0, -1.0 if diry > 0 else 1.0)
        if ty2 < tmax:
            tmax = ty2

    # Intersection exists if tmax >= max(tmin,0)
    t_hit = tmin if tmin >= 0 else tmax
    if t_hit is None or t_hit < 0 or t_hit > max_dist:
        return False, None, None, None

    hit_pos = (ox + dirx * t_hit, oy + diry * t_hit)
    return True, t_hit, hit_pos, normal
