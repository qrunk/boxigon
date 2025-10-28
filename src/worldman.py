import os
import json
import atexit
from typing import List, Optional, Dict, Any, Callable, MutableMapping, MutableSequence


class WorldManager:
    """Simple world manager.

    Responsibilities:
    - Keep worlds in project-root `worlds/` directory (create if missing).
    - List available worlds (filenames without .json).
    - Create new world JSON files with basic default content.
    - Load and save world data (dict) in memory.

    This is intentionally small and synchronous — suitable for the menu
    and simple autosave calls from the game.
    """

    def __init__(self, project_root: Optional[str] = None, autosave: bool = True):
        # Derive project root if not provided: two levels up from this file
        if project_root is None:
            here = os.path.dirname(__file__)
            project_root = os.path.abspath(os.path.join(here, '..'))

        self.project_root = project_root
        self.worlds_dir = os.path.join(self.project_root, 'worlds')
        os.makedirs(self.worlds_dir, exist_ok=True)

        self.current_name: Optional[str] = None
        # current_data will be a plain dict wrapped by AutoSaving* wrappers when loaded
        self.current_data: Optional[Dict[str, Any]] = None
        # whether modifications should be persisted automatically
        self.autosave = bool(autosave)

    # --- autosave helpers -------------------------------------------------

    def _save_callback(self) -> None:
        """Callback passed into autosaving containers to persist changes.

        It's a no-op when autosave is disabled.
        """
        if self.autosave:
            # ignore return value here; callers can still call save_world explicitly
            self.save_world()

    # --- world file operations --------------------------------------------

    def _world_path(self, name: str) -> str:
        safe = f"{name}.json"
        return os.path.join(self.worlds_dir, safe)

    def list_worlds(self) -> List[str]:
        files = []
        try:
            for fn in os.listdir(self.worlds_dir):
                if fn.lower().endswith('.json'):
                    files.append(fn[:-5])
        except Exception:
            # On error, return empty list — caller can handle.
            return []
        files.sort()
        return files

    def create_world(self, name: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Create a new world file with `name` and optional `data`.

        Returns True on success, False otherwise.
        """
        if not name or any(c in name for c in '/\\'):
            return False
        path = self._world_path(name)
        if os.path.exists(path):
            # don't overwrite existing world
            return False

        if data is None:
            # Minimal default world data — can be expanded later
            data = {
                "name": name,
                "npcs": [],
                "meta": {"created": None},
            }

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception:
            return False

        # Load the newly created world into memory (this will wrap data)
        return self.load_world(name)

    def load_world(self, name: str) -> bool:
        path = self._world_path(name)
        if not os.path.exists(path):
            return False
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            return False
        self.current_name = name
        # Wrap the loaded data so mutations autosave
        if isinstance(data, dict):
            self.current_data = AutoSavingDict(data, self._save_callback)
        else:
            # for non-dict root objects keep as-is
            self.current_data = data
        return True

    def save_world(self) -> bool:
        """Save current in-memory world data back to file.

        Returns True on success, False otherwise.
        """
        if not self.current_name or self.current_data is None:
            return False
        path = self._world_path(self.current_name)
        try:
            # convert any AutoSaving* wrappers back into plain structures
            plain = _to_plain(self.current_data)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(plain, f, indent=2)
        except Exception:
            return False
        return True

    def save_now(self) -> bool:
        """Explicitly persist the current world immediately."""
        return self.save_world()

    def close(self) -> bool:
        """Save and disable autosave (useful for clean shutdown)."""
        ok = self.save_world()
        self.autosave = False
        return ok

    # --- convenience mutation helpers -------------------------------------

    def add_npc(self, npc: Dict[str, Any]) -> bool:
        """Append an NPC dict to the world's `npcs` list (creates the list if missing).

        Returns True on success.
        """
        if self.current_data is None:
            return False
        # Ensure top-level 'npcs' list exists
        if 'npcs' not in self.current_data or not isinstance(self.current_data['npcs'], list):
            # use AutoSavingList when creating new list
            self.current_data['npcs'] = AutoSavingList([], self._save_callback)
        self.current_data['npcs'].append(npc)
        # append triggers autosave; return True
        return True

    def add_brick(self, brick: Dict[str, Any]) -> bool:
        """Append a brick-like dict to the world's `bricks` list (creates the list if missing).

        The `brick` argument should be a plain-serializable mapping describing
        the brick (for example: {"type":"brick","x":..,"y":..,"size":..}).
        Returns True on success.
        """
        if self.current_data is None:
            return False
        if 'bricks' not in self.current_data or not isinstance(self.current_data['bricks'], list):
            self.current_data['bricks'] = AutoSavingList([], self._save_callback)
        self.current_data['bricks'].append(brick)
        return True

    def remove_brick(self, predicate) -> bool:
        """Remove the first brick matching predicate(brick) and return True if removed."""
        if self.current_data is None:
            return False
        bricks = self.current_data.get('bricks')
        if not isinstance(bricks, list):
            return False
        for i, b in enumerate(bricks):
            try:
                if predicate(b):
                    del bricks[i]
                    return True
            except Exception:
                continue
        return False

    def remove_npc(self, predicate) -> bool:
        """Remove the first NPC matching predicate(npc) and return True if removed."""
        if self.current_data is None:
            return False
        npcs = self.current_data.get('npcs')
        if not isinstance(npcs, list):
            return False
        for i, npc in enumerate(npcs):
            try:
                if predicate(npc):
                    del npcs[i]
                    return True
            except Exception:
                continue
        return False

    def set_field(self, key: str, value: Any) -> bool:
        """Set a top-level field in the current world and persist it."""
        if self.current_data is None:
            return False
        self.current_data[key] = value
        # assignment triggers autosave via wrappers
        return True

def _wrap_value(value, save_cb: Callable[[], None]):
    """Wrap dicts/lists with autosaving wrappers recursively."""
    if isinstance(value, dict):
        return AutoSavingDict(value, save_cb)
    if isinstance(value, list):
        return AutoSavingList(value, save_cb)
    return value


def _to_plain(value):
    """Convert AutoSaving containers back into plain python structures for JSON dumping."""
    if isinstance(value, AutoSavingDict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, AutoSavingList):
        return [_to_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_plain(v) for v in value]
    return value


class AutoSavingDict(dict):
    """A dict-like wrapper that calls a save callback on mutation and wraps nested containers."""

    def __init__(self, initial: dict, save_cb: Callable[[], None]):
        super().__init__()
        self._save_cb = save_cb
        for k, v in initial.items():
            super().__setitem__(k, _wrap_value(v, save_cb))

    def __setitem__(self, key, value):
        super().__setitem__(key, _wrap_value(value, self._save_cb))
        self._save_cb()

    def __delitem__(self, key):
        super().__delitem__(key)
        self._save_cb()

    def clear(self):
        super().clear()
        self._save_cb()

    def pop(self, k, *args):
        result = super().pop(k, *args)
        self._save_cb()
        return result

    def popitem(self):
        item = super().popitem()
        self._save_cb()
        return item

    def setdefault(self, k, default=None):
        if k in self:
            return self[k]
        self[k] = default
        return self[k]

    def update(self, *args, **kwargs):
        for mapping in args:
            if isinstance(mapping, dict):
                for k, v in mapping.items():
                    super().__setitem__(k, _wrap_value(v, self._save_cb))
        for k, v in kwargs.items():
            super().__setitem__(k, _wrap_value(v, self._save_cb))
        self._save_cb()


class AutoSavingList(list):
    """A list-like wrapper that calls a save callback on mutation and wraps nested containers."""

    def __init__(self, initial: list, save_cb: Callable[[], None]):
        super().__init__(_wrap_value(v, save_cb) for v in initial)
        self._save_cb = save_cb

    def __setitem__(self, index, value):
        super().__setitem__(index, _wrap_value(value, self._save_cb))
        self._save_cb()

    def __delitem__(self, index):
        super().__delitem__(index)
        self._save_cb()

    def append(self, value):
        super().append(_wrap_value(value, self._save_cb))
        self._save_cb()

    def extend(self, iterable):
        super().extend(_wrap_value(v, self._save_cb) for v in iterable)
        self._save_cb()

    def insert(self, index, value):
        super().insert(index, _wrap_value(value, self._save_cb))
        self._save_cb()

    def pop(self, index=-1):
        v = super().pop(index)
        self._save_cb()
        return v

    def remove(self, value):
        super().remove(value)
        self._save_cb()

    def clear(self):
        super().clear()
        self._save_cb()

    def sort(self, *args, **kwargs):
        super().sort(*args, **kwargs)
        self._save_cb()

    def reverse(self):
        super().reverse()
        self._save_cb()



world_manager_singleton: Optional[WorldManager] = None

def get_world_manager() -> WorldManager:
    global world_manager_singleton
    if world_manager_singleton is None:
        world_manager_singleton = WorldManager()
        # Ensure the active world is saved on process exit
        try:
            atexit.register(world_manager_singleton.save_world)
        except Exception:
            # If registration fails for any reason, ignore — it's non-fatal
            pass
    return world_manager_singleton
