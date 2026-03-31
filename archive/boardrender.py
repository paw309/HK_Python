import pygame

def get_panel_aware_board_area(screen_width, screen_height, panel_left, panel_right, margin=32):
    """
    Computes the pixel rectangle for the board area between panels.
    Returns (area_left, area_top, area_width, area_height)
    - margin: optional, default 32 pixels around all edges
    panel_left: width (in pixels) of left panel
    panel_right: width (in pixels) of right panel
    """
    area_left = margin + panel_left
    area_top = margin
    area_width = screen_width - (panel_left + panel_right + 2*margin)
    area_height = screen_height - 2*margin
    return area_left, area_top, area_width, area_height


def build_board_renderer_for_size(board_size, screen, panel_left=280, panel_right=280, margin=20):
    screen_width, screen_height = screen.get_size()
    area_left, area_top, area_width, area_height = get_panel_aware_board_area(
        screen_width, screen_height, panel_left, panel_right, margin
    )
    layout = get_board_layout(area_left, area_top, area_width, area_height, board_size, board_size)
    board_model = BoardModel(board_size, board_size)
    board_renderer = BoardRenderer(board_model, layout['cell_size'], layout['origin'])
    return board_renderer, layout, board_model



def get_board_layout(
    area_left, area_top, area_width, area_height,
    cols, rows,
    min_cell_size=12
):
    """
    Given a rectangular board area and grid size,
    returns the cell size and top-left origin so the board is centered and fits.
    """
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

class BoardModel:
    """
    Generic model for a 2D board/grid.
    Each cell at (x, y) can store any value (e.g., color, piece code, or tuple).
    """
    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        self.grid = {}  # {(x, y): value}

    def clear(self):
        self.grid.clear()

    def set_cell(self, x, y, value):
        if 0 <= x < self.cols and 0 <= y < self.rows:
            self.grid[(x, y)] = value

    def get_cell(self, x, y):
        return self.grid.get((x, y))

    def iter_cells(self):
        for y in range(self.rows):
            for x in range(self.cols):
                yield x, y, self.grid.get((x, y), None)

class BoardRenderer:
    """
    Handles board pixel math and drawing given an area and grid.
    Does NOT control overlays—use callback for overlays!
    """
    def __init__(
        self,
        model: BoardModel,
        cell_size: int,
        origin: tuple,
        light_color=(255, 255, 240),
        dark_color=(232, 200, 150),
        grid_color=(107, 70, 51)
    ):
        self.model = model
        self.cell_size = cell_size
        self.origin = origin
        self.light_color = light_color
        self.dark_color = dark_color
        self.grid_color = grid_color

    def to_pixel(self, gx, gy):
        ox, oy = self.origin
        return ox + gx * self.cell_size, oy + gy * self.cell_size

    def to_grid(self, px, py):
        ox, oy = self.origin
        gx = (px - ox) // self.cell_size
        gy = (py - oy) // self.cell_size
        if 0 <= gx < self.model.cols and 0 <= gy < self.model.rows:
            return int(gx), int(gy)
        return None

    def draw_background(self, surface):
        ox, oy = self.origin
        cs = self.cell_size
        for gx in range(self.model.cols):
            for gy in range(self.model.rows):
                color = self.light_color if (gx + gy) % 2 == 0 else self.dark_color
                px, py = ox + gx * cs, oy + gy * cs
                rect = pygame.Rect(px, py, cs, cs)
                pygame.draw.rect(surface, color, rect)

    def draw_grid_lines(self, surface, line_width=2):
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

    def draw_cells(self, surface, render_cell_fn=None):
        cs = self.cell_size
        for (x, y), value in self.model.grid.items():
            px, py = self.to_pixel(x, y)
            rect = pygame.Rect(px, py, cs, cs)
            if render_cell_fn:
                render_cell_fn(surface, rect, x, y, value)
            else:
                pygame.draw.rect(surface, value, rect)