import os
import sys
import pygame
from typing import List
from src import scaling
from src.worldman import get_world_manager


class Menu:
    """Animated main menu.

    - Draws a simple baseplate + grid background (design-space) that slowly
      zooms out.
    - Options are vertically stacked on the left, slide in on show, and can
      be controlled by mouse or arrow keys + Enter.
    - When Play is chosen, set `start_requested=True` and deactivate menu.
    """

    def __init__(self, design_w: int, design_h: int):
        self.design_w = design_w
        self.design_h = design_h
        # Main options (kept separately so we can switch into the worlds UI)
        self.main_options: List[str] = ["Play", "Plugins", "Options", "Credits", "Exit"]
        # Current visible options (can be main or worlds list)
        self.options: List[str] = list(self.main_options)
        self.selected = 0

        # Animation state
        self.active = True
        self.start_requested = False

        # Slide-in: offset in design pixels (negative -> offscreen left)
        # Slide-in: offset in design pixels (negative -> offscreen left)
        self._slide_x = -int(self.design_w * 0.6)
        # Move menu to a middle-left position when settled
        self._slide_target = int(self.design_w * 0.08)
        self._slide_speed = 10.0  # higher = faster

        # Zoom: 1.15 -> 1.0 slowly
        self.zoom = 1.15
        self.zoom_target = 1.0
        self.zoom_speed = 0.5

        # Underline animation progress per option (0.0..1.0)
        self.underline_progress = [0.0 for _ in self.options]

        # World management
        self.world_manager = get_world_manager()
        # Menu modes: 'main' (default), 'worlds' (show world list), 'create' (typing a new world)
        self.menu_mode = 'main'
        self.world_options: List[str] = []

        # Create-world input state
        self.create_input = ''
        self._create_mouse_down = False
        # Horizontal scroll offset (in pixels) for the create input box when text is wider than box
        self._create_scroll_x = 0

        # Style
        self.font_name = None  # system default; let pygame pick
        self.font_size = 64
        self._font = pygame.font.SysFont(self.font_name, self.font_size)
        # Button font (smaller so labels fit buttons)
        self._button_font = pygame.font.SysFont(self.font_name, max(12, int(self.font_size * 0.7)))

        # Precompute layout in design coords (we compute vertical start dynamically
        # during drawing so the menu is vertically centered regardless of number
        # of options)
        self._option_spacing = int(self.font_size * 1.4)
        self._opt_start_y = int(self.design_h * 0.22)  # fallback / initial

        # Mouse tracking
        self._mouse_down = False

        # Small cached surface for design rendering (re-used each draw)
        self._design_surf = pygame.Surface((int(self.design_w), int(self.design_h)), pygame.SRCALPHA)

    def handle_event(self, event) -> bool:
        """Return True if event consumed by menu."""
        if not self.active:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # exit immediately
                pygame.quit()
                sys.exit()
            # If we're typing a world name, handle text input here
            if self.menu_mode == 'create':
                if event.key == pygame.K_BACKSPACE:
                    self.create_input = self.create_input[:-1]
                    # update scroll so the end of text remains visible
                    self._update_create_scroll()
                    return True
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    # Attempt create
                    self._attempt_create()
                    return True
                else:
                    # Accept printable characters from event.unicode
                    ch = event.unicode
                    if ch and len(ch) == 1 and (32 <= ord(ch) <= 126):
                        self.create_input += ch
                        # update scroll so the end of text remains visible
                        self._update_create_scroll()
                        return True
                # fall through for other keys if not handled

            elif event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.options)
                return True
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.options)
                return True
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._activate_selected()
                return True

        elif event.type == pygame.MOUSEMOTION:
            mx, my = scaling.to_world(event.pos)
            # If in create mode, we don't change selection by hover over options
            if self.menu_mode == 'create':
                return True
            # check option hit in design coords (main/worlds list)
            ox = int(self._slide_x)
            # center vertically based on number of options
            center_y = self.design_h * 0.5
            start_y = int(center_y - ((len(self.options) - 1) * self._option_spacing) / 2)
            for i, _ in enumerate(self.options):
                ty = start_y + i * self._option_spacing
                text_rect = pygame.Rect(ox, ty - self.font_size // 2, self.design_w - ox, self.font_size)
                if text_rect.collidepoint(mx, my):
                    self.selected = i
                    break
            return True

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._mouse_down = True
                self._create_mouse_down = True
                return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self._mouse_down:
                self._mouse_down = False
                mx, my = scaling.to_world(event.pos)

                # If in create mode handle clicks for the create/cancel buttons
                if self.menu_mode == 'create':
                    # compute input and button rects in design coords using current slide x
                    ix = int(self._slide_x)
                    center_y = self.design_h * 0.5
                    iy = int(center_y - ((len(self.options) - 1) * self._option_spacing) / 2)
                    iw = int(self.design_w * 0.6)
                    ih = int(self.font_size + 12)
                    input_rect = pygame.Rect(ix, iy, iw, ih)

                    # compute button sizes matching draw() (use button font metrics)
                    create_w = max(140, self._button_font.size("Create")[0] + 24)
                    cancel_w = max(80, self._button_font.size("Cancel")[0] + 24)
                    btn_w = create_w
                    btn_h = ih
                    btn_x = ix
                    btn_y = iy + ih + 12
                    create_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

                    cancel_rect = pygame.Rect(btn_x + btn_w + 12, btn_y, cancel_w, btn_h)

                    if create_rect.collidepoint(mx, my):
                        self._attempt_create()
                        return True
                    elif cancel_rect.collidepoint(mx, my):
                        # go back to worlds list
                        self._enter_worlds()
                        return True
                    else:
                        # clicking input focuses it; we keep focus always for keyboard
                        return True

                # Otherwise we are in a list (main or worlds)
                ox = int(self._slide_x)
                center_y = self.design_h * 0.5
                start_y = int(center_y - ((len(self.options) - 1) * self._option_spacing) / 2)
                for i, _ in enumerate(self.options):
                    ty = start_y + i * self._option_spacing
                    text_rect = pygame.Rect(ox, ty - self.font_size // 2, self.design_w - ox, self.font_size)
                    if text_rect.collidepoint(mx, my):
                        self.selected = i
                        self._activate_selected()
                        return True
                return True

        return False

    def _activate_selected(self):
        choice = self.options[self.selected]
        # Behavior depends on current menu mode
        if self.menu_mode == 'main':
            if choice == "Play":
                # Enter worlds list instead of immediately starting
                self._enter_worlds()
            elif choice == "Exit":
                pygame.quit()
                sys.exit()
            else:
                print(f"Menu: selected {choice}")

        elif self.menu_mode == 'worlds':
            if choice == "Create A World":
                self._enter_create()
            elif choice == "Back":
                # Return to main menu
                self._enter_main()
            else:
                # Attempt to load the chosen world and start
                ok = self.world_manager.load_world(choice)
                if ok:
                    self.start_requested = True
                    self.active = False
                else:
                    print(f"Failed to load world: {choice}")

        elif self.menu_mode == 'create':
            # In create mode, Enter attempts create
            self._attempt_create()

    def update(self, dt: float):
        if not self.active:
            # still allow zoom to settle a bit if needed
            self.zoom += (self.zoom_target - self.zoom) * min(1.0, self.zoom_speed * dt)
            return

        # Slide animation: ease towards target
        self._slide_x += (self._slide_target - self._slide_x) * min(1.0, self._slide_speed * dt)

        # Zoom out towards target
        self.zoom += (self.zoom_target - self.zoom) * min(1.0, self.zoom_speed * dt)

        # Underline animation: selected grows to 1, others shrink to 0
        for i in range(len(self.underline_progress)):
            target = 1.0 if i == self.selected else 0.0
            self.underline_progress[i] += (target - self.underline_progress[i]) * min(1.0, 10.0 * dt)

    # --- menu mode helpers ---
    def _enter_worlds(self):
        # Gather world names from world manager and present them
        names = self.world_manager.list_worlds()
        # Add create option at end
        names.append("Create A World")
        # Add a Back option so the player can return to the main menu
        names.append("Back")
        self.world_options = names
        self.options = list(self.world_options)
        self.menu_mode = 'worlds'
        self.selected = 0
        self.underline_progress = [0.0 for _ in self.options]

    def _enter_main(self):
        self.options = list(self.main_options)
        self.menu_mode = 'main'
        self.selected = 0
        self.underline_progress = [0.0 for _ in self.options]

    def _enter_create(self):
        # Show only a minimal set while creating
        self.menu_mode = 'create'
        self.options = ["Create A World"]
        self.selected = 0
        self.create_input = ''
        self.underline_progress = [0.0 for _ in self.options]
        self._update_create_scroll()

    def _attempt_create(self):
        name = self.create_input.strip()
        if not name:
            print("Create world: name required")
            return
        # Basic safety: no path separators
        if any(c in name for c in '/\\'):
            print("Invalid world name")
            return
        ok = self.world_manager.create_world(name)
        if ok:
            # World created and loaded — start the game
            self.start_requested = True
            self.active = False
        else:
            print(f"Failed to create world: {name}")

    def _update_create_scroll(self):
        """Update horizontal scroll so the end of create_input remains visible.

        Uses the same input width formula as draw().
        """
        iw = int(self.design_w * 0.6)
        padding = 16  # left+right padding (8 each)
        available = max(10, iw - padding)
        if not self.create_input:
            self._create_scroll_x = 0
            return
        text_w = self._font.size(self.create_input)[0]
        self._create_scroll_x = max(0, text_w - available)

    def draw(self, surf):
        """Draw the menu to the provided actual-screen surface."""
        # Design surface
        s = self._design_surf
        s.fill((10, 18, 12))

        # Draw a central slightly different rect and grid (like background)
        center_rect = pygame.Rect(self.design_w * 0.05, self.design_h * 0.1, self.design_w * 0.9, self.design_h * 0.7)
        pygame.draw.rect(s, (6, 10, 8), center_rect)

        grid_color = (38, 180, 85)
        g = 40
        x = 0
        while x <= int(self.design_w) + g:
            pygame.draw.line(s, grid_color, (x, 0), (x, int(self.design_h)), 1)
            x += g
        y = 0
        while y <= int(self.design_h) + g:
            pygame.draw.line(s, grid_color, (0, y), (int(self.design_w), y), 1)
            y += g

        # Draw a baseplate-like floor
        floor_y = int(self.design_h * 0.75)
        floor_rect = pygame.Rect(0, floor_y, self.design_w, self.design_h - floor_y)
        pygame.draw.rect(s, (80, 80, 90), floor_rect)

        # Draw options or create UI on design surface with slide offset applied
        ox = int(self._slide_x)
        font = self._font

        # compute vertical start so options are vertically centered
        center_y = self.design_h * 0.5
        start_y = int(center_y - ((len(self.options) - 1) * self._option_spacing) / 2)

        if self.menu_mode == 'create':
            # Draw a single-row input area and buttons using current slide x
            ix = ox
            iy = start_y
            iw = int(self.design_w * 0.6)
            ih = int(self.font_size + 12)

            # background for input (draw on main surface)
            input_rect = pygame.Rect(ix, iy, iw, ih)
            pygame.draw.rect(s, (30, 30, 30), input_rect)
            # Create a clipped input surface so long text doesn't draw outside
            input_surf = pygame.Surface((iw, ih), pygame.SRCALPHA)
            input_surf.fill((30, 30, 30))

            # Render input text — blit onto input_surf with scroll so the end is visible
            if self.create_input:
                txt = font.render(self.create_input, True, (230, 230, 230))
                input_surf.blit(txt, (8 - int(self._create_scroll_x), (ih - txt.get_height()) // 2))
            else:
                placeholder = "Enter world name..."
                txt = font.render(placeholder, True, (160, 160, 160))
                input_surf.blit(txt, (8, (ih - txt.get_height()) // 2))

            # Blit the clipped input surface onto the design surface
            s.blit(input_surf, (ix, iy))
            # Draw input border on top
            pygame.draw.rect(s, (120, 120, 120), input_rect, 2)

            # Create button
            # Create and Cancel buttons — use smaller button font and size buttons to fit text
            button_font = self._button_font
            create_txt = button_font.render("Create", True, (255, 255, 255))
            cancel_txt = button_font.render("Cancel", True, (255, 255, 255))

            btn_w = max(140, create_txt.get_width() + 24)
            btn_h = ih
            btn_x = ix
            btn_y = iy + ih + 12
            create_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
            pygame.draw.rect(s, (50, 120, 60), create_rect)
            s.blit(create_txt, (btn_x + (btn_w - create_txt.get_width()) // 2, btn_y + (btn_h - create_txt.get_height()) // 2))

            # Cancel button width based on text
            cancel_w = max(80, cancel_txt.get_width() + 24)
            cancel_rect = pygame.Rect(btn_x + btn_w + 12, btn_y, cancel_w, btn_h)
            pygame.draw.rect(s, (100, 100, 100), cancel_rect)
            s.blit(cancel_txt, (cancel_rect.x + (cancel_rect.w - cancel_txt.get_width()) // 2, cancel_rect.y + (cancel_rect.h - cancel_txt.get_height()) // 2))

        else:
            for i, txt in enumerate(self.options):
                ty = start_y + i * self._option_spacing
                color = (240, 240, 240) if i == self.selected else (200, 200, 200)
                rendered = font.render(txt, True, color)
                s.blit(rendered, (ox, ty - rendered.get_height() // 2))

                # underline
                tw = rendered.get_width()
                underline_h = 6
                prog = self.underline_progress[i]
                if prog > 0.001:
                    uw = int(tw * prog)
                    ux = ox
                    uy = ty + rendered.get_height() // 2 + 6
                    underline_rect = pygame.Rect(ux, uy, uw, underline_h)
                    # white underline for selected option
                    pygame.draw.rect(s, (255, 255, 255), underline_rect)

        # Scale the design surface to screen with additional zoom
        # Compute combined scale (base scale * zoom)
        base_scale = scaling.get_scale()
        combined = base_scale * self.zoom
        sw = max(1, int(round(self.design_w * combined)))
        sh = max(1, int(round(self.design_h * combined)))
        try:
            scaled = pygame.transform.smoothscale(s, (sw, sh))
        except Exception:
            scaled = pygame.transform.scale(s, (sw, sh))

        # Center scaled surface on screen
        aw = surf.get_width()
        ah = surf.get_height()
        ox = (aw - sw) // 2
        oy = (ah - sh) // 2

        surf.fill((10, 18, 12))
        surf.blit(scaled, (ox, oy))

        # Slight full-screen tint to darken the background subtly for
        # readability without a hard rectangle behind the options.
        tint = pygame.Surface((aw, ah), pygame.SRCALPHA)
        tint.fill((0, 0, 0, 64))
        surf.blit(tint, (0, 0))
