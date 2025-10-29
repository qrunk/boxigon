import random
import pygame
from src import scaling

"""Utilities for breaking/destroying maker-gun objects into fragments.

This module provides a single high-level function `break_into_fragments`
which takes an existing brick-like object and returns a list of smaller
objects (instances of the same class) that represent debris/fragments.

The function attempts to preserve the original object's color and give
fragments an initial velocity impulse based on the parent's velocity.
"""


def break_into_fragments(obj, rows=2, cols=2, spread=0.8, impulse=220):
    """Break `obj` into (rows x cols) smaller pieces and return a list
    of new object instances.

    Args:
        obj: The original object (Brick, Crate, or compatible) with
             attributes `p.pos`, `p.prev`, `size`, `p.mass`, `color`.
        rows, cols: Grid to split into.
        spread: Multiplier controlling initial displacement from center.
        impulse: Base impulse magnitude applied randomly to fragments.

    Returns: list of new objects (same class as obj) ready to be added
             to the world. The original object is not modified here.
    """
    fragments = []

    # Defensive: ensure we have the basic attributes
    try:
        pos = obj.p.pos
        prev = obj.p.prev
        size = float(getattr(obj, 'size', 12))
        mass = float(getattr(obj.p, 'mass', 1.0))
    except Exception:
        return fragments

    parent_vel = pos - prev
    total_pieces = max(1, rows * cols)

    # Determine fragment size (keep minimum to avoid 0-size)
    frag_size = max(6, int(size / max(rows, cols)))

    cls = obj.__class__
    base_color = getattr(obj, 'color', None)

    for r in range(rows):
        for c in range(cols):
            # center offsets so pieces tile over original area
            cx = (c - (cols - 1) / 2.0) * (frag_size * spread)
            cy = (r - (rows - 1) / 2.0) * (frag_size * spread)

            try:
                spawn_pos = pygame.math.Vector2(pos.x + cx, pos.y + cy)
            except Exception:
                try:
                    spawn_pos = pygame.math.Vector2(pos[0] + cx, pos[1] + cy)
                except Exception:
                    spawn_pos = pygame.math.Vector2(0, 0)

            # instantiate a new piece using the same class where possible
            try:
                piece = cls(spawn_pos, size=frag_size, mass=max(0.01, mass / total_pieces), color=base_color)
            except Exception:
                # fallback: try importing Brick-like signature with fewer args
                try:
                    piece = cls(spawn_pos, size=frag_size)
                except Exception:
                    continue

            # give an initial velocity by setting prev position appropriately
            angle = random.uniform(0, 2 * 3.14159)
            mag = random.uniform(0.4 * impulse, 1.1 * impulse) / max(1.0, frag_size / 12.0)
            kick = pygame.math.Vector2(mag * math_cos(angle), mag * math_sin(angle))

            # add some upward bias so fragments pop upward on break
            kick.y = kick.y - abs(mag) * 0.35

            # combine parent's velocity (small contribution) with random kick
            init_vel = parent_vel * 0.45 + kick

            try:
                piece.p.pos = spawn_pos
                piece.p.prev = piece.p.pos - init_vel
            except Exception:
                pass

            fragments.append(piece)

    return fragments


# lightweight local helpers to avoid importing math full module repeatedly
def math_cos(a):
    try:
        from math import cos
        return cos(a)
    except Exception:
        return 0.0


def math_sin(a):
    try:
        from math import sin
        return sin(a)
    except Exception:
        return 0.0
