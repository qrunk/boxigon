import pygame

# Simple gun registry and base class for extensible guns
_GUN_REGISTRY = {}


def register_gun(name):
    """Decorator to register a gun class under a name.

    Usage:
        @register_gun('Pistol')
        class Pistol(Gun): ...
    """
    def _decorator(cls):
        _GUN_REGISTRY[name] = cls
        return cls

    return _decorator


def get_gun_class(name):
    return _GUN_REGISTRY.get(name)


def create_gun(name, pos, **kwargs):
    """Create an instance of a registered gun by name.

    Returns None if the gun name is unknown or construction fails.
    """
    cls = get_gun_class(name)
    # If not registered yet, try to import a module matching the gun name
    # e.g. name 'Pistol' -> try import 'src.guns.pistol'
    if cls is None:
        try:
            import importlib
            mod_name = 'src.guns.' + name.lower()
            importlib.import_module(mod_name)
            cls = get_gun_class(name)
        except Exception:
            cls = None
    if cls is None:
        return None
    try:
        return cls(pos, **kwargs)
    except Exception:
        try:
            # try without kwargs as a last resort
            return cls(pos)
        except Exception:
            return None


class Gun:
    """Minimal base Gun class.

    Subclasses should implement shoot()/fire(), update(dt, ...), draw(surf).
    """

    def __init__(self, pos, icon=None):
        try:
            self.pos = pygame.math.Vector2(pos)
        except Exception:
            self.pos = pygame.math.Vector2((0, 0))
        self.icon = icon
        self.held = False
        # optional convenience: bullets/blood lists and cooldown
        self.bullets = []
        self._cooldown = 0.0
        self.fire_rate = 1.0
        # flip indicates whether mouse direction should be inverted
        self.flip = False

    def shoot(self, target_world_pos):
        """Fire towards target. Default does nothing."""
        raise NotImplementedError()

    def update(self, dt, npcs=None, floor=None):
        """Default update: update bullets list if present."""
        if self._cooldown > 0:
            self._cooldown -= dt
        for b in list(getattr(self, 'bullets', [])):
            try:
                b.update(dt, npcs=npcs, floor=floor, blood_mgr=getattr(self, 'blood', None))
            except Exception:
                try:
                    b.update(dt)
                except Exception:
                    pass
            if not getattr(b, 'alive', True):
                try:
                    self.bullets.remove(b)
                except Exception:
                    pass

    def draw(self, surf):
        """Default draw: draw bullets and optional icon."""
        for b in getattr(self, 'bullets', []):
            try:
                b.draw(surf)
            except Exception:
                pass

        try:
            if self.icon is not None:
                ps = max(12, 20)
                img = pygame.transform.scale(self.icon, (ps, ps))
                center = pygame.math.Vector2(self.pos)
                surf.blit(img, (int(center.x - ps // 2), int(center.y - ps // 2)))
        except Exception:
            pass
