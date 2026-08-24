import pygame
from typing import Tuple, Any, Dict, Optional, List, Set

class BoardModel:
    """
    Generic model for a 2D board/grid.
    Each cell at (x, y) can store any value (e.g., color, piece code, or tuple).
    """

    def __init__(self, cols: int, rows: int):
        self.cols = cols
        self.rows = rows
        self.grid: Dict[Tuple[int, int], Any] = {}

    def clear(self) -> None:
        self.grid.clear()

    def set_cell(self, x: int, y: int, value: Any) -> None:
        if 0 <= x < self.cols and 0 <= y < self.rows:
            self.grid[(x, y)] = value

    def get_cell(self, x: int, y: int) -> Optional[Any]:
        return self.grid.get((x, y))

    def remove_cell(self, x: int, y: int) -> None:
        if (x, y) in self.grid:
            del self.grid[(x, y)]

    def iter_cells(self):
        for y in range(self.rows):
            for x in range(self.cols):
                yield x, y, self.grid.get((x, y), None)

class BoardRenderer:
    """
    Generic 2D Board renderer.

    - Handles pixel-grid conversion and basic background/grid drawing.
    - Custom cell rendering is supported via a callback.
    """

    def __init__(
        self,
        model: BoardModel,
        cell_size: int,
        origin: Tuple[int, int],
        light_color: Tuple[int, int, int] = (255, 255, 240),
        dark_color: Tuple[int, int, int] = (232, 200, 150),
        grid_color: Tuple[int, int, int] = (107, 70, 51)
    ):
        self.model = model
        self.cell_size = cell_size
        self.origin = origin
        self.light_color = light_color
        self.dark_color = dark_color
        self.grid_color = grid_color

    def to_pixel(self, gx: int, gy: int) -> Tuple[int, int]:
        ox, oy = self.origin
        return ox + gx * self.cell_size, oy + gy * self.cell_size

    def to_grid(self, px: int, py: int) -> Optional[Tuple[int, int]]:
        ox, oy = self.origin
        gx = (px - ox) // self.cell_size
        gy = (py - oy) // self.cell_size
        if 0 <= gx < self.model.cols and 0 <= gy < self.model.rows:
            return int(gx), int(gy)
        return None

    def draw_background(self, surface: pygame.Surface) -> None:
        """
        Draws the checkered or solid background.
        """
        ox, oy = self.origin
        cs = self.cell_size
        for gx in range(self.model.cols):
            for gy in range(self.model.rows):
                color = self.light_color if (gx + gy) % 2 == 0 else self.dark_color
                px, py = ox + gx * cs, oy + gy * cs
                rect = pygame.Rect(px, py, cs, cs)
                pygame.draw.rect(surface, color, rect)

    def draw_grid_lines(self, surface: pygame.Surface, line_width: int = 2) -> None:
        """
        Draws vertical and horizontal grid lines over the board.
        """
        ox, oy = self.origin
        cs = self.cell_size
        for x in range(self.model.cols + 1):
            start = (ox + x * cs, oy)
            end = (ox + x * cs, oy + self.model.rows * cs)
            pygame.draw.line(surface, self.grid_color, start, end, line_width)
        for y in range(self.model.rows + 1):
            start = (ox, oy + y * cs)
            end = (ox + self.model.cols * cs, oy + y * cs)
            pygame.draw.line(surface, self.grid_color, start, end, line_width)

    def draw_cells(self, surface: pygame.Surface, render_cell_fn=None):
        """
        Calls `render_cell_fn(surface, rect, x, y, cell_value)` for each cell containing a value.
        If no render_cell_fn is given, draws a filled rect with the cell value (if it's a color).
        """
        cs = self.cell_size
        for (x, y), value in self.model.grid.items():
            px, py = self.to_pixel(x, y)
            rect = pygame.Rect(px, py, cs, cs)
            if render_cell_fn:
                render_cell_fn(surface, rect, x, y, value)
            else:
                # Assume value is a color
                pygame.draw.rect(surface, value, rect)

    def draw_legal_moves_overlay(
        self,
        surface: pygame.Surface,
        legal_moves: List[Tuple[int, int]],
        color: Tuple[int, int, int] = (100, 145, 225),
        alpha: int = 128
    ) -> None:
        """Draw semi-transparent overlay on legal move squares."""
        cs = self.cell_size
        overlay = pygame.Surface((cs, cs), pygame.SRCALPHA)
        overlay.fill((*color, alpha))
        for gx, gy in legal_moves:
            px, py = self.to_pixel(gx, gy)
            surface.blit(overlay, (px, py))

    def draw_player_position(
        self,
        surface: pygame.Surface,
        pos: Tuple[int, int],
        piece_image: pygame.Surface
    ) -> None:
        """Draw player piece at position."""
        px, py = self.to_pixel(*pos)
        cs = self.cell_size
        img_rect = piece_image.get_rect(center=(px + cs // 2, py + cs // 2))
        surface.blit(piece_image, img_rect)

    def draw_visited_overlay(
        self,
        surface: pygame.Surface,
        visited: Set[Tuple[int, int]],
        light_color: Optional[Tuple[int, int, int]] = None,
        dark_color: Optional[Tuple[int, int, int]] = None
    ) -> None:
        """Draw visited squares with alternating colors."""
        if light_color is None:
            light_color = (192, 192, 192)
        if dark_color is None:
            dark_color = (128, 128, 128)
        cs = self.cell_size
        for gx, gy in visited:
            parity = (gx + (self.model.rows - 1 - gy)) % 2
            color = dark_color if parity == 0 else light_color
            px, py = self.to_pixel(gx, gy)
            rect = pygame.Rect(px, py, cs, cs)
            pygame.draw.rect(surface, color, rect)


def get_board_layout(
    area_left: int,
    area_top: int,
    area_width: int,
    area_height: int,
    cols: int,
    rows: int,
    min_cell_size: int = 12
) -> dict:
    """
    Given a rectangular area (pixel coords/dimensions) and board grid size,
    returns standard layout info for rendering a centered board:
        - cell_size: pixels for each cell (auto-scaled to fit area)
        - origin: (x, y) pixels for top-left cell (centered)
        - board_pixel_w, board_pixel_h

    Usage (in main game code):
        layout = get_board_layout( ... )
        renderer.cell_size = layout['cell_size']
        renderer.origin = layout['origin']
    """
    # Compute max cell size
    cell_w = area_width // cols
    cell_h = area_height // rows
    cell_size = max(min_cell_size, min(cell_w, cell_h))
    board_pixel_w = cols * cell_size
    board_pixel_h = rows * cell_size
    origin_x = area_left + (area_width - board_pixel_w) // 2
    origin_y = area_top + (area_height - board_pixel_h) // 2
    return {
        'cell_size': cell_size,
        'origin': (origin_x, origin_y),
        'board_pixel_w': board_pixel_w,
        'board_pixel_h': board_pixel_h
    }