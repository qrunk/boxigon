import sys
import pygame
from typing import List
from src import scaling


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

        # Options
        self.options: List[str] = ["Play", "Plugins", "Options", "Credits", "Exit"]
        self.selected = 0

        # Animation state
        self.active = True
        self.start_requested = False

        # Slide-in: offset in design pixels (negative -> offscreen left)
        self._slide_x = -int(self.design_w * 0.6)
        self._slide_target = int(self.design_w * 0.12)
        self._slide_speed = 10.0  # higher = faster

        # Zoom: 1.15 -> 1.0 slowly
        self.zoom = 1.15
        self.zoom_target = 1.0
        self.zoom_speed = 0.5

        # Underline animation progress per option (0.0..1.0)
        self.underline_progress = [0.0 for _ in self.options]

        # Style
        self.font_name = None  # system default; let pygame pick
        self.font_size = 64
        self._font = pygame.font.SysFont(self.font_name, self.font_size)

        # Precompute layout in design coords
        self._option_spacing = int(self.font_size * 1.4)
        self._opt_start_y = int(self.design_h * 0.22)

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
            # check option hit in design coords
            ox = self._slide_target
            for i, _ in enumerate(self.options):
                ty = self._opt_start_y + i * self._option_spacing
                text_rect = pygame.Rect(ox, ty - self.font_size // 2, self.design_w - ox, self.font_size)
                if text_rect.collidepoint(mx, my):
                    self.selected = i
                    break
            return True

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._mouse_down = True
                return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self._mouse_down:
                self._mouse_down = False
                mx, my = scaling.to_world(event.pos)
                ox = self._slide_target
                for i, _ in enumerate(self.options):
                    ty = self._opt_start_y + i * self._option_spacing
                    text_rect = pygame.Rect(ox, ty - self.font_size // 2, self.design_w - ox, self.font_size)
                    if text_rect.collidepoint(mx, my):
                        self.selected = i
                        self._activate_selected()
                        return True
                return True

        return False

    def _activate_selected(self):
        choice = self.options[self.selected]
        if choice == "Play":
            self.start_requested = True
            self.active = False
        elif choice == "Exit":
            pygame.quit()
            sys.exit()
        else:
            # For now, other options just print to stdout and stay in menu.
            print(f"Menu: selected {choice}")

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

        # Draw options on design surface with slide offset applied
        ox = int(self._slide_x)
        font = self._font
        for i, txt in enumerate(self.options):
            ty = self._opt_start_y + i * self._option_spacing
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
