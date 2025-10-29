import os
import pygame
from src import scaling
from src.npc import NPC
from src.worldman import get_world_manager
from src import colison
from .brick import Brick, draw_brick_pattern


class MakersGun:
    """Attach to mouse cursor, show spawn menu, spawn bricks on left click,
    pick up/move objects on right click.

    Methods:
        handle_event(event, npcs) -> bool: returns True if event consumed
        update(dt, floor=None)
        draw(surf)
    """

    def __init__(self):
        self.target = None
        self.offset = pygame.math.Vector2(0, 0)
        self.dragging = False

        self.equipped = False

        self.menu_open = False

        self.menu_selected = None

        try:
            self._prev_cursor_visible = pygame.mouse.get_visible()
        except Exception:
            self._prev_cursor_visible = True
        self.bricks = []
        self.welding_tool = None
        self.pistol = None
        self.thruster_icon = None
        self.axe = None
        self.axe_icon = None

        self.icon = None
        self.welding_icon = None
        self.pistol_icon = None
        try:
            base = os.path.join(os.path.dirname(__file__), 'assets')

            path = os.path.join(base, 'makergun.png')
            if os.path.exists(path):
                self.icon = pygame.image.load(path).convert_alpha()
            weld_path = os.path.join(base, 'weldingtool.png')
            if os.path.exists(weld_path):
                self.welding_icon = pygame.image.load(weld_path).convert_alpha()
            pistol_path = os.path.join(base, 'pistol.png')
            if os.path.exists(pistol_path):
                self.pistol_icon = pygame.image.load(pistol_path).convert_alpha()
            thruster_path = os.path.join(base, 'thruster.png')
            if os.path.exists(thruster_path):
                self.thruster_icon = pygame.image.load(thruster_path).convert_alpha()
            axe_path = os.path.join(base, 'axe.png')
            if os.path.exists(axe_path):
                self.axe_icon = pygame.image.load(axe_path).convert_alpha()
        except Exception:
            self.icon = None
            self.welding_icon = None


        self.menu_w = 96
        self.menu_h = 40
        # Tabs for spawn menu
        self.menu_tabs = ['Objects', 'Weapons', 'Items']
        self.menu_tab_items = {
            'Objects': ['Brick', 'NPC'],
            'Weapons': ['Wielding Tool', 'Pistol', 'Axe'],
            'Items': ['Thruster']
        }
        self.menu_tab_selected = 0
        self.menu_tab_h = 28
        # menu animation state (0.0 closed -> 1.0 open)
        self.menu_anim = 0.0
        self.menu_anim_target = 0.0
        self.menu_anim_speed = 6.0
        # small hover progress variable (used to modulate hover lift)
        self._hover_progress = 0.0

    def pickup_welding_tool(self):
        if self.welding_tool:
            self.welding_tool['held'] = True

    def drop_welding_tool(self):
        if self.welding_tool:
            self.welding_tool['held'] = False
        return

    def equip(self):
        if not self.equipped:
            self.equipped = True
            try:
                self._prev_cursor_visible = pygame.mouse.get_visible()
                pygame.mouse.set_visible(False)
            except Exception:
                pass

    def drop(self):
        if self.equipped:
            self.equipped = False
            self.dragging = False
            self.target = None
            try:
                pygame.mouse.set_visible(self._prev_cursor_visible)
            except Exception:
                pass

    def spawn_brick(self, world_pos):
        b = Brick(world_pos, size=40)
        self.bricks.append(b)
        try:
            mgr = get_world_manager()
            if mgr.current_name:
                mgr.add_brick({"type": "brick", "x": float(world_pos[0]) if isinstance(world_pos, (list, tuple)) else float(world_pos.x), "y": float(world_pos[1]) if isinstance(world_pos, (list, tuple)) else float(world_pos.y), "size": 40})
                mgr.save_now()
        except Exception:
            pass

    def spawn_welding_tool(self, world_pos):
        self.welding_tool = {'pos': pygame.math.Vector2(world_pos), 'held': False}

    def spawn_pistol(self, world_pos, auto_equip=False):
        try:
            self.pistol = {'pos': pygame.math.Vector2(world_pos), 'held': bool(auto_equip)}
        except Exception:
            self.pistol = {'pos': pygame.math.Vector2((0, 0)), 'held': bool(auto_equip)}

    def spawn_thruster(self, world_pos):
        try:
            from src.thruster import Thruster
            t = Thruster(world_pos, icon=self.thruster_icon)
            self.bricks.append(t)
            try:
                mgr = get_world_manager()
                if mgr.current_name:
                    mgr.add_brick({"type": "thruster", "x": float(world_pos[0]) if isinstance(world_pos, (list, tuple)) else float(world_pos.x), "y": float(world_pos[1]) if isinstance(world_pos, (list, tuple)) else float(world_pos.y), "size": getattr(t, 'size', 32)})
                    mgr.save_now()
            except Exception:
                pass
        except Exception:
            pass

    def spawn_axe(self, world_pos, auto_equip=False):
        try:
            self.axe = {'pos': pygame.math.Vector2(world_pos), 'held': bool(auto_equip)}
        except Exception:
            self.axe = {'pos': pygame.math.Vector2((0, 0)), 'held': bool(auto_equip)}

    def pickup_axe(self):
        if self.axe:
            self.axe['held'] = True

    def drop_axe(self):
        if self.axe:
            self.axe['held'] = False
        return

    def pickup_pistol(self):
        if self.pistol:
            self.pistol['held'] = True

    def drop_pistol(self):
        if self.pistol:
            self.pistol['held'] = False

    def open_menu(self):
        if not self.menu_open:
            try:
                self._prev_cursor_visible = pygame.mouse.get_visible()
                pygame.mouse.set_visible(True)
            except Exception:
                pass
        self.menu_open = True
        # start opening animation
        self.menu_anim_target = 1.0

    def close_menu(self):
        if self.menu_open:
            self.menu_open = False
            try:
                pygame.mouse.set_visible(self._prev_cursor_visible)
            except Exception:
                pass
        # start closing animation (we keep menu_open False but allow anim to fade)
        self.menu_anim_target = 0.0

    def clear_selection(self):
        self.menu_selected = None

    def toggle_menu(self):
        if self.menu_open:
            self.close_menu()
        else:
            self.open_menu()

    def find_nearest_moveable(self, world_pos, npcs, max_dist=80):
        best = None
        best_d = max_dist
        v = pygame.math.Vector2(world_pos)

        for b in self.bricks:
            d = (b.p.pos - v).length()
            if d < best_d:
                best_d = d
                best = ('brick', b)

        if best_d > max_dist * 0.5:
            for npc in npcs:
                try:
                    p = npc.particles[2].pos
                except Exception:
                    try:
                        p = npc.particles[0].pos
                    except Exception:
                        continue
                d = (p - v).length()
                if d < best_d:
                    best_d = d
                    best = ('npc', npc)

        return best

    def handle_event(self, event, npcs):
        consumed = False

        if self.menu_open:
            # (menu handling — identical logic to original)
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mx, my = event.pos
                    try:
                        surf = pygame.display.get_surface()
                        sw, sh = surf.get_size()
                    except Exception:
                        sw, sh = 800, 600

                    # Use same geometry as draw(): wider menu and internal tabs
                    menu_w = max(340, int(sw * 0.7))
                    menu_h = max(220, int(sh * 0.6))
                    menu_w = min(menu_w, sw - 80)
                    menu_h = min(menu_h, sh - 120)
                    menu_x = (sw - menu_w) // 2
                    menu_y = (sh - menu_h) // 2

                    # Check tab clicks (tabs are inside menu at y = menu_y + 48)
                    try:
                        tabs = self.menu_tabs
                        tab_count = max(1, len(tabs))
                        tab_w = (menu_w - 40) // tab_count
                        tabs_y = menu_y + 48
                        for i in range(tab_count):
                            tx = menu_x + 20 + i * tab_w
                            tab_rect = pygame.Rect(tx, tabs_y, tab_w - 8, self.menu_tab_h)
                            if tab_rect.collidepoint(mx, my):
                                self.menu_tab_selected = i
                                consumed = True
                                return consumed
                    except Exception:
                        pass

                    # Otherwise check grid cells (grid starts below tabs)
                    try:
                        items = self.menu_tab_items.get(self.menu_tabs[self.menu_tab_selected], [])

                        available_w = menu_w - 48
                        cols = max(1, available_w // 120)
                        cell_w = available_w // cols
                        cell_size = max(48, min(140, cell_w))
                        pad = 12
                        start_x = menu_x + 24
                        start_y = menu_y + 48 + self.menu_tab_h + 12

                        for idx, name in enumerate(items):
                            col = idx % cols
                            row = idx // cols
                            x = start_x + col * cell_size
                            y = start_y + row * (cell_size + 18)
                            r = pygame.Rect(x, y, cell_size - pad, cell_size - pad)
                            if r.collidepoint(mx, my):
                                # spawn immediately for some types
                                if name in ('Wielding Tool', 'Pistol', 'Axe', 'NPC'):
                                    try:
                                        world_pos = scaling.to_world((mx, my))
                                        if name == 'Wielding Tool':
                                            self.spawn_welding_tool(world_pos)
                                        elif name == 'Pistol':
                                            self.spawn_pistol(world_pos, auto_equip=True)
                                        elif name == 'Axe':
                                            self.spawn_axe(world_pos, auto_equip=True)
                                        else:
                                            try:
                                                wx, wy = world_pos
                                                npcs.append(NPC(wx, wy))
                                                try:
                                                    mgr = get_world_manager()
                                                    if mgr.current_name:
                                                        mgr.add_npc({'x': float(wx), 'y': float(wy)})
                                                        mgr.save_now()
                                                except Exception:
                                                    pass
                                            except Exception:
                                                try:
                                                    nx, ny = world_pos.x, world_pos.y
                                                    npcs.append(NPC(nx, ny))
                                                    try:
                                                        mgr = get_world_manager()
                                                        if mgr.current_name:
                                                            mgr.add_npc({'x': float(nx), 'y': float(ny)})
                                                            mgr.save_now()
                                                    except Exception:
                                                        pass
                                                except Exception:
                                                    pass
                                    except Exception:
                                        pass

                                    self.menu_selected = None
                                else:
                                    self.menu_selected = name
                                self.close_menu()
                                consumed = True
                                return consumed
                    except Exception:
                        pass

                elif event.button == 3:
                    self.close_menu()
                    consumed = True

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    self.close_menu()
                    consumed = True

            return consumed

        # Global key handling when menu is not open: allow quick unequip
        try:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                unequipped = False
                try:
                    if self.pistol and self.pistol.get('held', False):
                        self.pistol = None
                        try:
                            self._pistol_obj = None
                        except Exception:
                            pass
                        unequipped = True
                except Exception:
                    pass
                try:
                    if self.axe and self.axe.get('held', False):
                        self.axe = None
                        try:
                            self._axe_obj = None
                        except Exception:
                            pass
                        unequipped = True
                except Exception:
                    pass
                if unequipped:
                    consumed = True
                    return consumed
        except Exception:
            pass

        if self.menu_selected is not None:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                pos = scaling.to_world(event.pos)
                if self.menu_selected == 'Brick':
                    self.spawn_brick(pos)
                    consumed = True
                    return consumed
                elif self.menu_selected == 'Wielding Tool':
                    self.spawn_welding_tool(pos)
                    consumed = True
                    return consumed
                elif self.menu_selected == 'Pistol':
                    self.spawn_pistol(pos)
                    consumed = True
                    return consumed
                elif self.menu_selected == 'Axe':
                    self.spawn_axe(pos)
                    consumed = True
                    return consumed
                elif self.menu_selected == 'Thruster':
                    self.spawn_thruster(pos)
                    consumed = True
                    return consumed
                elif self.menu_selected == 'NPC':
                    try:
                        px, py = pos
                        npcs.append(NPC(px, py))
                        try:
                            mgr = get_world_manager()
                            if mgr.current_name:
                                mgr.add_npc({"x": float(px), "y": float(py)})
                                mgr.save_now()
                        except Exception:
                            pass
                    except Exception:
                        try:
                            nx, ny = pos.x, pos.y
                            npcs.append(NPC(nx, ny))
                            try:
                                mgr = get_world_manager()
                                if mgr.current_name:
                                    mgr.add_npc({"x": float(nx), "y": float(ny)})
                                    mgr.save_now()
                            except Exception:
                                pass
                        except Exception:
                            pass
                    consumed = True
                    return consumed

            if self.menu_selected == 'Wielding Tool' and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.welding_tool and not self.welding_tool['held']:
                    mouse_pos = pygame.math.Vector2(scaling.to_world(event.pos))
                    if (mouse_pos - self.welding_tool['pos']).length() < 48:
                        self.pickup_welding_tool()
                        consumed = True
                        return consumed
            if self.menu_selected == 'Axe' and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.axe and not self.axe.get('held', False):
                    mouse_pos = pygame.math.Vector2(scaling.to_world(event.pos))
                    try:
                        if (mouse_pos - self.axe['pos']).length() < 48:
                            self.pickup_axe()
                            consumed = True
                            return consumed
                    except Exception:
                        pass

        if event.type == pygame.MOUSEBUTTONDOWN:

            if event.button == 3 and self.pistol and self.pistol.get('held', False):
                try:
                    from src.guns.pistol import Pistol
                    if not hasattr(self, '_pistol_obj') or self._pistol_obj is None:
                        self._pistol_obj = Pistol(self.pistol['pos'], icon=self.pistol_icon)

                    self._pistol_obj.pos = self.pistol['pos']
                    self._pistol_obj.held = self.pistol['held']
                    target = scaling.to_world(event.pos)
                    self._pistol_obj.shoot(target)
                    consumed = True
                    return consumed
                except Exception:
                    pass
            pos = scaling.to_world(event.pos)

            if event.button == 3:
                if self.menu_selected == 'Wielding Tool':
                    self.spawn_welding_tool(pos)
                elif self.menu_selected == 'Pistol':
                    self.spawn_pistol(pos)
                elif self.menu_selected == 'Axe':
                    self.spawn_axe(pos)
                elif self.menu_selected == 'Thruster':
                    self.spawn_thruster(pos)
                else:
                    self.spawn_brick(pos)
                consumed = True
                return consumed

            elif event.button == 1:

                if self.welding_tool and not self.welding_tool.get('held', False):
                    try:
                        if (pos - self.welding_tool['pos']).length() < 48:
                            self.welding_tool['held'] = True
                            consumed = True
                            return consumed
                    except Exception:
                        pass

                if self.pistol and not self.pistol.get('held', False):
                    try:
                        if (pos - self.pistol['pos']).length() < 96:
                            self.pistol['held'] = True
                            consumed = True
                            return consumed
                    except Exception:
                        pass

                if self.axe and not self.axe.get('held', False):
                    try:
                        if (pos - self.axe['pos']).length() < 48:
                            self.axe['held'] = True
                            consumed = True
                            return consumed
                    except Exception:
                        pass

                found = self.find_nearest_moveable(pos, npcs, max_dist=80)
                if found is not None:
                    self.dragging = True
                    self.target = found
                    if found[0] == 'brick':
                        brick = found[1]
                        try:
                            root = brick.get_root()
                        except Exception:
                            root = brick
                        self.target = ('brick_group', (root, brick))
                        try:
                            self.offset = root.p.pos - brick.p.pos
                        except Exception:
                            self.offset = pygame.math.Vector2(0, 0)
                        consumed = True
                    else:
                        npc = found[1]
                        try:
                            p = npc.particles[2]
                            self.offset = p.pos - pygame.math.Vector2(pos)
                            consumed = True
                        except Exception:
                            self.dragging = False
                            self.target = None
                return consumed

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self.dragging:

                self.dragging = False
                if self.target and self.target[0] == 'brick':

                    ttype = self.target[0]
                    if ttype == 'brick':
                        brick = self.target[1]
                        old_pos = brick.p.prev
                        brick.p.prev = brick.p.pos - (brick.p.pos - old_pos) * 0.5
                    elif ttype == 'brick_group':
                        try:
                            root, selected = self.target[1]
                        except Exception:
                            root = self.target[1]
                        old_prev = root.p.prev
                        old_vel = root.p.pos - old_prev
                        root.p.prev = root.p.pos - (old_vel * 0.5)
                        try:
                            damp_vel = root.p.pos - root.p.prev
                            queue = [root]
                            while queue:
                                parent = queue.pop(0)
                                for child in getattr(parent, 'welded_children', []):
                                    child.p.prev = child.p.pos - damp_vel
                                    queue.append(child)
                        except Exception:
                            pass
                self.target = None
                consumed = True
                return consumed


            if self.welding_tool and self.welding_tool.get('held', False) and event.button == 1:
                self.welding_tool['held'] = False
                consumed = True
                return consumed

            if self.axe and self.axe.get('held', False) and event.button == 1:
                self.axe['held'] = False
                consumed = True
                return consumed

        return consumed

    def update(self, dt, npcs=None, floor=None):
        # menu animation progress (advances even while menu_open/closed)
        try:
            target = self.menu_anim_target
            # simple lerp towards target controlled by speed
            step = min(1.0, dt * self.menu_anim_speed)
            self.menu_anim += (target - self.menu_anim) * step
            # clamp
            if self.menu_anim < 1e-4:
                self.menu_anim = 0.0
            if self.menu_anim > 1.0 - 1e-4:
                self.menu_anim = 1.0
        except Exception:
            pass

        for b in self.bricks:
            b.update(dt, floor_y=floor, other_bricks=self.bricks)

        if npcs and self.bricks:
            try:
                for npc in npcs:
                    colison.collide_particles_with_bricks(npc.particles, self.bricks, iterations=2)
            except Exception:
                pass

        if self.welding_tool:
            from src.wield import WeldingTool
            if not hasattr(self, '_welding_tool_obj') or self._welding_tool_obj is None:
                self._welding_tool_obj = WeldingTool(self.welding_tool['pos'], icon=self.welding_icon)
            self._welding_tool_obj.pos = self.welding_tool['pos']
            self._welding_tool_obj.held = self.welding_tool['held']
            self._welding_tool_obj.update(npcs or [], self.bricks)

            if self.welding_tool['held']:
                try:
                    self.welding_tool['pos'] = pygame.math.Vector2(scaling.to_world(pygame.mouse.get_pos()))
                except Exception:
                    self.welding_tool['pos'] = pygame.math.Vector2(pygame.mouse.get_pos())

            try:
                if hasattr(self, '_welding_tool_obj') and self._welding_tool_obj is not None:
                    for b in list(self.bricks):
                        try:
                            if hasattr(b, 'apply_thrust'):
                                b.apply_thrust(dt, welding_tool=self._welding_tool_obj, npcs=npcs, bricks=self.bricks)
                        except Exception:
                            pass
            except Exception:
                pass

        if self.pistol:
            try:
                from src.guns.pistol import Pistol
                if not hasattr(self, '_pistol_obj') or self._pistol_obj is None:
                    self._pistol_obj = Pistol(self.pistol['pos'], icon=self.pistol_icon)
                self._pistol_obj.pos = self.pistol['pos']
                self._pistol_obj.held = self.pistol['held']

                try:
                    self._pistol_obj.update(dt, npcs or [], floor)
                except Exception:
                    self._pistol_obj.update(dt)

                if self.pistol['held']:
                    try:
                        self.pistol['pos'] = pygame.math.Vector2(scaling.to_world(pygame.mouse.get_pos()))
                    except Exception:
                        self.pistol['pos'] = pygame.math.Vector2(pygame.mouse.get_pos())
            except Exception:
                pass

        if self.axe:
            try:
                from src.axe import Axe
                if not hasattr(self, '_axe_obj') or self._axe_obj is None:
                    self._axe_obj = Axe(self.axe['pos'], icon=self.axe_icon)
                self._axe_obj.pos = self.axe['pos']
                self._axe_obj.held = self.axe['held']
                try:
                    self._axe_obj.update(npcs or [], self.bricks, floor)
                except Exception:
                    try:
                        self._axe_obj.update(npcs or [], self.bricks, floor)
                    except Exception:
                        pass

                if self.axe['held']:
                    try:
                        self.axe['pos'] = pygame.math.Vector2(scaling.to_world(pygame.mouse.get_pos()))
                    except Exception:
                        self.axe['pos'] = pygame.math.Vector2(pygame.mouse.get_pos())
            except Exception:
                pass

        if self.dragging and self.target is not None:
            mpos = pygame.math.Vector2(scaling.to_world(pygame.mouse.get_pos()))
            desired = mpos + self.offset
            ttype, obj = self.target

            if ttype == 'brick':

                old_pos = obj.p.pos.copy()
                old_vel = obj.p.pos - obj.p.prev
                obj.p.pos = desired

                obj.p.prev = obj.p.pos - (old_vel * 0.2)
            elif ttype == 'brick_group':
                try:
                    root, selected = obj
                except Exception:
                    root = obj
                    selected = obj

                old_pos = root.p.pos.copy()
                old_vel = root.p.pos - root.p.prev
                root.p.pos = desired
                root.p.prev = root.p.pos - (old_vel * 0.2)

                try:
                    root_vel = root.p.pos - root.p.prev
                    queue = [root]
                    while queue:
                        parent = queue.pop(0)
                        for child in getattr(parent, 'welded_children', []):
                            child.p.pos = parent.p.pos + child.welded_offset
                            child.p.prev = child.p.pos - root_vel
                            queue.append(child)
                except Exception:
                    pass
            else:
                try:
                    idx = 2
                    center = obj.particles[idx].pos
                except Exception:
                    idx = 0
                    center = obj.particles[0].pos
                delta = desired - center
                for p in obj.particles:
                    p.pos += delta

    def draw(self, surf):

        for b in self.bricks:
            b.draw(surf)

        if self.welding_tool:
            if not hasattr(self, '_welding_tool_obj') or self._welding_tool_obj is None:
                from src.wield import WeldingTool
                self._welding_tool_obj = WeldingTool(self.welding_tool['pos'], icon=self.welding_icon)
            self._welding_tool_obj.pos = self.welding_tool['pos']
            self._welding_tool_obj.held = self.welding_tool['held']
            self._welding_tool_obj.draw(surf)

        if self.pistol:
            if not hasattr(self, '_pistol_obj') or self._pistol_obj is None:
                try:
                    from src.guns.pistol import Pistol
                    self._pistol_obj = Pistol(self.pistol['pos'], icon=self.pistol_icon)
                except Exception:
                    self._pistol_obj = None
            if self._pistol_obj is not None:
                self._pistol_obj.pos = self.pistol['pos']
                self._pistol_obj.held = self.pistol['held']
                self._pistol_obj.draw(surf)

        if self.axe:
            if not hasattr(self, '_axe_obj') or self._axe_obj is None:
                try:
                    from src.axe import Axe
                    self._axe_obj = Axe(self.axe['pos'], icon=self.axe_icon)
                except Exception:
                    self._axe_obj = None
            if self._axe_obj is not None:
                self._axe_obj.pos = self.axe['pos']
                self._axe_obj.held = self.axe['held']
                self._axe_obj.draw(surf)

        m = pygame.mouse.get_pos()

        # Render menu when open or animating
        if self.menu_open or self.menu_anim > 0.0:
            try:
                sw, sh = surf.get_size()
            except Exception:
                sw, sh = 800, 600

            menu_w = max(340, int(sw * 0.7))
            menu_h = max(220, int(sh * 0.6))
            menu_w = min(menu_w, sw - 80)
            menu_h = min(menu_h, sh - 120)
            menu_x = (sw - menu_w) // 2
            menu_y = (sh - menu_h) // 2

            # dim background with 50% black at full open, scaled by menu_anim
            try:
                overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
                overlay_alpha = int(128 * self.menu_anim)
                overlay.fill((0, 0, 0, overlay_alpha))
                surf.blit(overlay, (0, 0))
            except Exception:
                pass

            # draw UI onto its own surface so we can apply fade/scale easily
            try:
                ui = pygame.Surface((menu_w, menu_h), pygame.SRCALPHA)
                ui_rect = ui.get_rect()

                # rounded background
                bg_color = (28, 30, 34, 230)
                border_color = (80, 88, 100)
                pygame.draw.rect(ui, bg_color, ui_rect, border_radius=10)
                pygame.draw.rect(ui, border_color, ui_rect, 2, border_radius=10)

                # header
                try:
                    font = pygame.font.SysFont('Segoe UI', max(18, scaling.to_screen_length(20)))
                except Exception:
                    font = pygame.font.SysFont('Arial', max(18, scaling.to_screen_length(20)))
                header = font.render('Select Item to Spawn', True, (235, 235, 235))
                ui.blit(header, (24, 12))

                # tabs (pill style)
                try:
                    tabs = self.menu_tabs
                    tab_count = max(1, len(tabs))
                    tab_w = (menu_w - 40) // tab_count
                    tabs_y = 48
                    for i, tname in enumerate(tabs):
                        tx = 20 + i * tab_w
                        tab_rect = pygame.Rect(tx, tabs_y, tab_w - 8, self.menu_tab_h)
                        if i == self.menu_tab_selected:
                            # Selected tab: white background, black text per user request
                            pygame.draw.rect(ui, (255, 255, 255), tab_rect, border_radius=8)
                            pygame.draw.rect(ui, (220, 220, 220), tab_rect, 2, border_radius=8)
                            txt_col = (20, 20, 20)
                        else:
                            pygame.draw.rect(ui, (40, 44, 50), tab_rect, border_radius=8)
                            pygame.draw.rect(ui, (70, 76, 86), tab_rect, 1, border_radius=8)
                            txt_col = (200, 200, 200)
                        try:
                            tfont = pygame.font.SysFont('Segoe UI', max(13, scaling.to_screen_length(14)))
                        except Exception:
                            tfont = pygame.font.SysFont('Arial', max(12, scaling.to_screen_length(14)))
                        txt = tfont.render(tname, True, txt_col)
                        ui.blit(txt, (tx + (tab_rect.w - txt.get_width()) // 2, tabs_y + (self.menu_tab_h - txt.get_height()) // 2))
                except Exception:
                    pass

                # items grid
                try:
                    items = self.menu_tab_items.get(self.menu_tabs[self.menu_tab_selected], [])
                    available_w = menu_w - 48
                    cols = max(1, available_w // 120)
                    cell_w = available_w // cols
                    cell_size = max(48, min(140, cell_w))
                    pad = 12
                    start_x = 24
                    start_y = 48 + self.menu_tab_h + 12

                    mx, my = m
                    rel_mx = mx - menu_x
                    rel_my = my - menu_y

                    for idx, name in enumerate(items):
                        col = idx % cols
                        row = idx // cols
                        x = start_x + col * cell_size
                        y = start_y + row * (cell_size + 18)
                        r = pygame.Rect(x, y, cell_size - pad, cell_size - pad)

                        # base cell
                        cell_bg = (38, 42, 48)
                        cell_border = (70, 76, 86)
                        pygame.draw.rect(ui, cell_bg, r, border_radius=8)
                        pygame.draw.rect(ui, cell_border, r, 1, border_radius=8)

                        # hover detection using relative mouse coords
                        hovered = r.collidepoint(rel_mx, rel_my)
                        lift = -6 if hovered else 0
                        lift = int(lift * self.menu_anim)
                        inner_rect = r.move(0, lift)

                        # preview
                        preview_size = max(20, inner_rect.h - 16)
                        preview_rect = pygame.Rect(inner_rect.x + (inner_rect.w - preview_size) // 2, inner_rect.y + 8, preview_size, preview_size)
                        try:
                            if name == 'Wielding Tool' and self.welding_icon is not None:
                                ui.blit(pygame.transform.scale(self.welding_icon, (preview_size, preview_size)), preview_rect)
                            elif name == 'Pistol' and self.pistol_icon is not None:
                                ui.blit(pygame.transform.scale(self.pistol_icon, (preview_size, preview_size)), preview_rect)
                            elif name == 'Axe' and self.axe_icon is not None:
                                ui.blit(pygame.transform.scale(self.axe_icon, (preview_size, preview_size)), preview_rect)
                            elif name == 'Thruster' and self.thruster_icon is not None:
                                ui.blit(pygame.transform.scale(self.thruster_icon, (preview_size, preview_size)), preview_rect)
                            elif name == 'NPC':
                                # Draw the NPC head as the preview (outline, fill, eye)
                                try:
                                    cx = preview_rect.centerx
                                    cy = preview_rect.centery
                                    hs = max(8, preview_size)
                                    head_rect = pygame.Rect(0, 0, hs, hs)
                                    head_rect.center = (cx, cy)
                                    outline_col = (16, 40, 18)
                                    fill_col = (54, 160, 60)
                                    pygame.draw.rect(ui, outline_col, head_rect, border_radius=4)
                                    inner = head_rect.inflate(-max(2, scaling.to_screen_length(3)), -max(2, scaling.to_screen_length(3)))
                                    pygame.draw.rect(ui, fill_col, inner, border_radius=3)
                                    # simple eye (left)
                                    eye_w = max(1, scaling.to_screen_length(4))
                                    eye_x = int(cx - hs * 0.16)
                                    eye_y = int(cy - hs * 0.12)
                                    pygame.draw.rect(ui, (10, 10, 10), pygame.Rect(eye_x, eye_y, eye_w, eye_w))
                                except Exception:
                                    # fallback to older simplistic icon if something goes wrong
                                    cx = preview_rect.centerx
                                    cy = preview_rect.centery
                                    head_r = max(3, int(preview_size * 0.18))
                                    torso_w = max(6, int(preview_size * 0.32))
                                    torso_h = max(8, int(preview_size * 0.38))
                                    head_center = (cx, cy - head_r)
                                    torso_rect = pygame.Rect(0, 0, torso_w, torso_h)
                                    torso_rect.center = (cx, cy + torso_h // 6)
                                    pygame.draw.circle(ui, (16, 40, 18), head_center, head_r)
                                    pygame.draw.circle(ui, (54, 160, 60), head_center, max(1, head_r - 2))
                                    pygame.draw.rect(ui, (16, 40, 18), torso_rect)
                                    inner = torso_rect.inflate(-max(2, scaling.to_screen_length(1)), -max(2, scaling.to_screen_length(1)))
                                    pygame.draw.rect(ui, (54, 160, 60), inner)
                            else:
                                # draw brick preview using shared pattern renderer
                                try:
                                    draw_brick_pattern(ui, preview_rect, color=(150, 30, 30), outline=(30, 10, 10), border_radius=6)
                                except Exception:
                                    # fallback simple rect
                                    pygame.draw.rect(ui, (150, 30, 30), preview_rect, border_radius=6)
                                    inner = preview_rect.inflate(-max(4, scaling.to_screen_length(6)), -max(4, scaling.to_screen_length(6)))
                                    pygame.draw.rect(ui, (200, 60, 60), inner, border_radius=4)
                        except Exception:
                            pass

                        # label
                        try:
                            label_font = pygame.font.SysFont('Segoe UI', max(13, scaling.to_screen_length(14)))
                        except Exception:
                            label_font = pygame.font.SysFont('Arial', max(12, scaling.to_screen_length(14)))
                        lbl = label_font.render(name, True, (220, 220, 220))
                        ui.blit(lbl, (inner_rect.x + (inner_rect.w - lbl.get_width()) // 2, inner_rect.y + preview_size + 12))

                    # hint
                    try:
                        hint_font = pygame.font.SysFont('Segoe UI', max(11, scaling.to_screen_length(12)))
                    except Exception:
                        hint_font = pygame.font.SysFont('Arial', max(11, scaling.to_screen_length(12)))
                    hint = hint_font.render('Left-click to select. After selection: Right-click to spawn repeatedly. Q/Esc to close.', True, (170, 170, 170))
                    ui.blit(hint, (24, menu_h - 36))
                except Exception:
                    pass

                # apply overall UI alpha based on menu_anim and blit
                try:
                    ui.set_alpha(int(255 * self.menu_anim))
                    surf.blit(ui, (menu_x, menu_y))
                except Exception:
                    surf.blit(ui, (menu_x, menu_y))
            except Exception:
                pass

            return

        if not self.equipped:
            for b in self.bricks:
                b.draw(surf)
            return

        if self.icon is not None:
            w, h = self.icon.get_size()
            surf.blit(self.icon, (m[0] - w // 2, m[1] - h // 2))
        else:
            pygame.draw.circle(surf, (220, 200, 20), m, 10)

        menu_rect = pygame.Rect(m[0] + 16, m[1] - self.menu_h // 2, self.menu_w, self.menu_h)
        pygame.draw.rect(surf, (30, 30, 30), menu_rect)
        pygame.draw.rect(surf, (200, 200, 200), menu_rect, 1)

        icon_rect = pygame.Rect(menu_rect.x + 8, menu_rect.y + 6, 28, 28)
        pygame.draw.rect(surf, (150, 40, 40), icon_rect)
        pygame.draw.rect(surf, (20, 10, 10), icon_rect, 1)

        try:
            font = pygame.font.SysFont('Arial', max(10, scaling.to_screen_length(12)))
            txt = font.render('Brick', True, (220, 220, 220))
            surf.blit(txt, (icon_rect.right + 8, menu_rect.y + 8))
        except Exception:
            pass

        if self.menu_selected is not None:
            try:
                ps = 14
                pr = pygame.Rect(m[0] + 16, m[1] - self.menu_h // 2 - ps - 8, ps, ps)
                if self.menu_selected == 'Pistol' and self.pistol_icon is not None:
                    try:
                        img = pygame.transform.scale(self.pistol_icon, (ps, ps))
                        surf.blit(img, (pr.x, pr.y))
                    except Exception:
                        pygame.draw.rect(surf, (30, 10, 10), pr)
                        inner = pr.inflate(-2, -2)
                        pygame.draw.rect(surf, (180, 30, 30), inner)
                elif self.menu_selected == 'Axe' and self.axe_icon is not None:
                    try:
                        img = pygame.transform.scale(self.axe_icon, (ps, ps))
                        surf.blit(img, (pr.x, pr.y))
                    except Exception:
                        pygame.draw.rect(surf, (30, 10, 10), pr)
                        inner = pr.inflate(-2, -2)
                        pygame.draw.rect(surf, (180, 30, 30), inner)
                elif self.menu_selected == 'NPC':
                    try:
                        cx = pr.centerx
                        cy = pr.centery
                        hs = max(6, ps)
                        head_rect = pygame.Rect(0, 0, hs, hs)
                        head_rect.center = (cx, cy)
                        outline_col = (16, 40, 18)
                        fill_col = (54, 160, 60)
                        pygame.draw.rect(surf, outline_col, head_rect, border_radius=3)
                        inner = head_rect.inflate(-max(1, scaling.to_screen_length(2)), -max(1, scaling.to_screen_length(2)))
                        pygame.draw.rect(surf, fill_col, inner, border_radius=2)
                        eye_w = max(1, scaling.to_screen_length(3))
                        eye_x = int(cx - hs * 0.16)
                        eye_y = int(cy - hs * 0.12)
                        pygame.draw.rect(surf, (10, 10, 10), pygame.Rect(eye_x, eye_y, eye_w, eye_w))
                    except Exception:
                        pygame.draw.rect(surf, (30, 10, 10), pr)
                        inner = pr.inflate(-2, -2)
                        pygame.draw.rect(surf, (180, 30, 30), inner)
                elif self.menu_selected == 'Thruster' and self.thruster_icon is not None:
                    try:
                        img = pygame.transform.scale(self.thruster_icon, (ps, ps))
                        surf.blit(img, (pr.x, pr.y))
                    except Exception:
                        pygame.draw.rect(surf, (30, 10, 10), pr)
                        inner = pr.inflate(-2, -2)
                        pygame.draw.rect(surf, (180, 30, 30), inner)
                else:
                    try:
                        draw_brick_pattern(surf, pr, color=(180, 30, 30), outline=(30, 10, 10), border_radius=4)
                    except Exception:
                        pygame.draw.rect(surf, (30, 10, 10), pr)
                        inner = pr.inflate(-2, -2)
                        pygame.draw.rect(surf, (180, 30, 30), inner)
            except Exception:
                pass
