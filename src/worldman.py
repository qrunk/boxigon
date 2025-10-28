import os
import json
from typing import List, Optional, Dict, Any


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

    def __init__(self, project_root: Optional[str] = None):
        # Derive project root if not provided: two levels up from this file
        if project_root is None:
            here = os.path.dirname(__file__)
            project_root = os.path.abspath(os.path.join(here, '..'))

        self.project_root = project_root
        self.worlds_dir = os.path.join(self.project_root, 'worlds')
        os.makedirs(self.worlds_dir, exist_ok=True)

        self.current_name: Optional[str] = None
        self.current_data: Optional[Dict[str, Any]] = None

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

        # Load the newly created world into memory
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
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.current_data, f, indent=2)
        except Exception:
            return False
        return True


world_manager_singleton: Optional[WorldManager] = None

def get_world_manager() -> WorldManager:
    global world_manager_singleton
    if world_manager_singleton is None:
        world_manager_singleton = WorldManager()
    return world_manager_singleton
