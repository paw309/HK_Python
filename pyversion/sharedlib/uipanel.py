import pygame
from typing import Dict, Tuple

class UIPanel:
    """
    Defines four UI panels (MENU, BUTTON, PIECE, STATS) independently.
    The vertical gap is inserted between top and bottom; it shifts lower panels down
    without shrinking any panel.
    """

    def __init__(
            self,
            rect: pygame.Rect,
            quadrant_names: Tuple[str, ...] = ("MENU_PANEL", "BUTTON_PANEL", "PIECE_PANEL", "STATS_PANEL"),
            gap: int = 0):
        self.rect = rect
        self.quadrant_names = quadrant_names
        self.gap = gap  # vertical pixel gap between stacked panels
        self.bounds: Dict[str, Dict[str, int]] = self._compute_quadrants()

    def _compute_quadrants(self) -> Dict[str, Dict[str, int]]:
        qbounds = {}
        left = self.rect.left
        top = self.rect.top
        width = self.rect.width
        height = self.rect.height

        # Panels are each half the panel rect height, with lower panels offset downward by self.gap.
        panel_height = height // 2

        # Left column
        menu_top = top
        menu_bottom = menu_top + panel_height

        button_top = menu_bottom + self.gap
        button_bottom = button_top + panel_height

        qbounds["MENU_PANEL"] = {
            'left': left,
            'top': menu_top,
            'right': left + width,
            'bottom': menu_bottom,
            'width': width,
            'height': panel_height,
            'center_x': left + width // 2,
            'center_y': menu_top + panel_height // 2,
        }
        qbounds["BUTTON_PANEL"] = {
            'left': left,
            'top': button_top,
            'right': left + width,
            'bottom': button_bottom,
            'width': width,
            'height': panel_height,
            'center_x': left + width // 2,
            'center_y': button_top + panel_height // 2,
        }
        # Right column (same logic)
        piece_top = top
        piece_bottom = piece_top + panel_height

        stats_top = piece_bottom + self.gap
        stats_bottom = stats_top + panel_height

        qbounds["PIECE_PANEL"] = {
            'left': left,
            'top': piece_top,
            'right': left + width,
            'bottom': piece_bottom,
            'width': width,
            'height': panel_height,
            'center_x': left + width // 2,
            'center_y': piece_top + panel_height // 2,
        }
        qbounds["STATS_PANEL"] = {
            'left': left,
            'top': stats_top,
            'right': left + width,
            'bottom': stats_bottom,
            'width': width,
            'height': panel_height,
            'center_x': left + width // 2,
            'center_y': stats_top + panel_height // 2,
        }

        return qbounds

    def get_bounds(self, quadrant_name: str) -> Dict[str, int]:
        """Retrieve boundary dict for panel/quadrant."""
        bounds = self.bounds.get(quadrant_name)
        if bounds is None:
            raise ValueError(f"Unknown quadrant name: {quadrant_name}")
        return bounds

    def get_line_y(self, quadrant_name: str, line_number: float, line_height: int) -> int:
        """
        Returns the y-coordinate of the Nth line in a quadrant (0-indexed).
        Supports float line_number to allow positioning between lines.
        """
        bounds = self.get_bounds(quadrant_name)
        # UI_SPACING logic is now external; here we just use line_height
        # Starts line 0 at top + line_height (padding above first line)
        return int(bounds['top'] + line_height + (line_number * line_height))

    def get_center(self, quadrant_name: str) -> Tuple[int, int]:
        """Return center (x, y) of the given quadrant."""
        b = self.get_bounds(quadrant_name)
        return b['center_x'], b['center_y']

    def get_rect(self, quadrant_name: str) -> pygame.Rect:
        """Return pygame.Rect for the quadrant."""
        b = self.get_bounds(quadrant_name)
        return pygame.Rect(b['left'], b['top'], b['width'], b['height'])

    def draw_panel(self, surface: pygame.Surface, quadrant_name: str, bg_color: Tuple[int, int, int],
                   border_color: Tuple[int, int, int], border_w: int = 2):
        """Draws the panel background and border."""
        rect = self.get_rect(quadrant_name)
        pygame.draw.rect(surface, bg_color, rect)
        pygame.draw.rect(surface, border_color, rect, border_w)

    def draw_line(self, surface: pygame.Surface, quadrant_name: str, line_number: int, line_height: int,
                  color: Tuple[int, int, int] = (0, 0, 0), thickness: int = 1):
        """
        Optionally draws a horizontal line at the given line within a quadrant.
        """
        y = self.get_line_y(quadrant_name, line_number, line_height)
        b = self.get_bounds(quadrant_name)

    def align_text(self, surface: pygame.Surface, text: str, font: pygame.font.Font, quadrant_name: str,
                   line_number: int, line_height: int, color=(0, 0, 0), align='center'):
        """
        Renders text aligned (center, left, right) at given line of panel.
        """
        b = self.get_bounds(quadrant_name)
        y = self.get_line_y(quadrant_name, line_number, line_height) + line_height // 2
        surf = font.render(text, True, color)
        rect = surf.get_rect()
        if align == 'center':
            rect.centerx = b['center_x']
        elif align == 'left':
            rect.left = b['left'] + line_height
        elif align == 'right':
            rect.right = b['right'] - line_height
        rect.centery = y
        surface.blit(surf, rect)

    def get_widget_rect(self, quadrant_name: str, line_number: int, widget_width: int,
                        widget_height: int, align: str = "center") -> pygame.Rect:
        """
        Returns a rect for a widget in the given line of the panel.
        align: "center" (default), "left", or "right".
        """
        b = self.get_bounds(quadrant_name)
        y = self.get_line_y(quadrant_name, line_number, widget_height)
        if align == "center":
            x = b['center_x'] - widget_width // 2
        elif align == "left":
            x = b['left']
        elif align == "right":
            x = b['right'] - widget_width
        else:
            raise ValueError(f"Unknown align: {align}")
        return pygame.Rect(x, y, widget_width, widget_height)