# polyomino_v16.py
#
# Requirements:
#  - packages
#       pygame
#       pyperclip
#  - sharedlib contains
#       gameboard.py
#       piecekeeper.py
#       puzzle_code.py
#  - assets subdirectory
#       piece images
#       arrow images
#       marker images
#  - polyomino utilities
#       polyomino_data.py
#       polyomino_ratings.py
#       piece_mobility_ratings.csv
#       piece_agility_ratings.csv

import sys
import os
import math
import random
from typing import Optional, List, Tuple, Set, Dict, Callable, Any, TypedDict

import pygame
import polyomino_data as pd
import polyomino_ratings as pr
import piecekeeper as pk
from gameboard import BoardModel, BoardRenderer
from puzzle_codec import decode_params, polyomino_schema  # encode_params
from text_input import TextInput
from game_controller import GameController, GameState
from uipanel import UIPanel

# --- constants and global config ---

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
image_dir_path = os.path.join(BASE_DIR, "assets")
pieces_dir = os.path.join(BASE_DIR, "assets", "pieces")
arrows_dir = os.path.join(BASE_DIR, "assets", "arrows")
markers_dir = os.path.join(BASE_DIR, "assets", "markers")

FPS = 60
UI_SPACE = 16
BTW = int(UI_SPACE * 9)
BTH = int(UI_SPACE * 2)
DEFAULT_GRID_COLS = 8
LT_SQUARE = (255, 255, 240)
DK_SQUARE = (232, 200, 150)
LT_VISITED = (192, 192, 192)
DK_VISITED = (128, 128, 128)
GRID_COLOR = (107, 70, 51)
BACK_COLOR = (244, 228, 195)

PALETTE = [
    (0, 0, 128), (0, 0, 255), (0, 64, 64), (0, 64, 192), (0, 128, 0),
    (0, 128, 128), (0, 128, 192), (0, 128, 255), (0, 192, 0), (0, 192, 192),
    (0, 192, 255), (0, 255, 0), (0, 255, 128), (0, 255, 255), (128, 0, 0),
    (128, 0, 128), (128, 0, 192), (128, 0, 255), (128, 64, 192), (128, 192, 64),
    (128, 192, 192), (128, 128, 0), (128, 128, 255), (128, 255, 0), (128, 255, 192),
    (128, 255, 255), (255, 0, 0), (255, 0, 128), (255, 0, 255), (255, 64, 64),
    (255, 64, 192), (255, 128, 0), (255, 128, 128), (255, 128, 255), (255, 255, 0),
]

# piece filtering
ALLOWED_PIECES = None  # none = all pieces
EXCLUDED_PIECES = {"bishop", "delta", "theta", "lambda", "xi"}
SLIDING_PIECES = {"rook", "bishop", "queen"}

previous_game_codec = None


# --- stateless utility functions ---

def pick_contrast_font_color(rgb_tuple):
    """Returns (0,0,0)=black for light backgrounds, (255,255,255)=white for dark."""
    r, g, b = rgb_tuple
    luma = r * 0.299 + g * 0.587 + b * 0.114  # perceptual brightness formula
    return (0, 0, 0) if luma > 192 else (255, 255, 255)


def clamp(n: float, a: float, b: float) -> float:
    return max(a, min(b, n))


def normalize(units: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Normalizes a set of (x, y) polyomino units so that min x/y is (0, 0)."""
    if not units:
        return units
    minx = min(c[0] for c in units)
    miny = min(c[1] for c in units)
    return [(x - minx, y - miny) for (x, y) in units]


def rotate90(units: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Rotates a polyomino 90 degrees."""
    rotated = [(y, -x) for (x, y) in units]
    return normalize(rotated)


def flip_horizontal(units: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Flips a polyomino horizontally."""
    flipped = [(-x, y) for (x, y) in units]
    return normalize(flipped)


def format_time(total_seconds: int) -> str:
    total_seconds = max(0, total_seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"


def get_globally_valid_pieces() -> List[str]:
    """Return a list of piece names valid for the provided board size."""
    valid_pieces = []
    for piece in pk.PIECE_LIST:
        if ALLOWED_PIECES is not None and piece not in ALLOWED_PIECES:
            continue
        if EXCLUDED_PIECES and piece in EXCLUDED_PIECES:
            continue
        valid_pieces.append(piece)
    return valid_pieces


def compute_density_from_setting(density_setting: str) -> float:
    density_map = {"high": 0.3, "medium": 0.2, "low": 0.1}
    return density_map.get(density_setting, 0.2)


def draw_peek_thumbnail(
        screen,
        board_model,
        puzzle_layout,
        peek_mode_visible,
        left_panel,
        line_height
):
    """Draws a peek thumbnail of the puzzle layout inside the button panel."""
    if not (puzzle_layout and peek_mode_visible):
        return

    cols, rows = board_model.cols, board_model.rows
    if cols < 1 or rows < 1:
        return

    button_bounds = left_panel.get_bounds("BUTTON_PANEL")
    peek_line = 0
    thumb_area_y = left_panel.get_line_y("BUTTON_PANEL", peek_line, line_height)
    thumb_area = pygame.Rect(
        button_bounds['left'] + UI_SPACE * 1,
        thumb_area_y,
        button_bounds['width'] - (UI_SPACE * 2),
        button_bounds['bottom'] - (thumb_area_y + UI_SPACE * 3)
    )

    max_cell = min(
        thumb_area.width // cols if cols else 1,
        thumb_area.height // rows if rows else 1
    )
    if max_cell < 2:
        return  # Too small to show thumbnail

    tw, th = cols * max_cell, rows * max_cell
    tx = thumb_area.left + (thumb_area.width - tw) // 2
    ty = thumb_area.top + (thumb_area.height - th) // 2

    # Draw background border for thumbnail
    pygame.draw.rect(screen, (232, 200, 150), (tx - 2, ty - 2, tw + 4, th + 4))

    # Draw each shape
    for shape in puzzle_layout:
        for gx, gy in shape.puzzle_units:
            rpx = tx + gx * max_cell
            rpy = ty + gy * max_cell
            pygame.draw.rect(screen, shape.color, (rpx + 1, rpy + 1, max_cell - 1, max_cell - 1))


# --- data classes ---

class Polyomino:
    def __init__(
            self,
            units: List[Tuple[int, int]],
            color: Optional[Tuple[int, int, int]] = None,
            name: Optional[str] = None,
    ):
        self.units = normalize(units)
        self.name = name or "poly"
        self.color = color or random.choice(PALETTE)

    def rotated(self) -> "Polyomino":
        return Polyomino(rotate90(self.units), color=self.color, name=self.name)

    def flipped(self) -> "Polyomino":
        return Polyomino(flip_horizontal(self.units), color=self.color, name=self.name)

    def bounding(self) -> Tuple[int, int]:
        if not self.units:
            return 0, 0
        maxx = max(x for x, _ in self.units)
        maxy = max(y for _, y in self.units)
        return maxx + 1, maxy + 1


class PuzzleShape:
    def __init__(
            self,
            shape_id: int,
            name: str,
            puzzle_units: Set[Tuple[int, int]],
            color: Tuple[int, int, int],
            origin: Tuple[int, int],
            orientation: str = "",
    ):
        self.id = shape_id
        self.name = name
        self.puzzle_units = set(puzzle_units)
        self.color = color
        self.origin = origin
        self.orientation = orientation
        self.found_units: Set[Tuple[int, int]] = set()


class Button:
    def __init__(
            self,
            rect: pygame.Rect,
            text: str,
            text_color: Tuple[int, int, int],
            bg_color: Tuple[int, int, int],
            font: pygame.font.Font,
            function: Optional[Callable[[], None]] = None,
    ):
        self.rect = rect
        self.text = text
        self.text_color = text_color
        self.bg_color = bg_color
        self.font = font
        self.function = function
        self.active = True
        self.disabled_color = (128, 128, 128)
        self.disabled_text_color = (180, 180, 180)

    class Effect(TypedDict):
        units: List[Tuple[int, int]]
        color: Tuple[int, int, int]
        center_pos: Tuple[float, float]
        size: float
        expires: int

    def draw(self, surface: pygame.Surface) -> None:
        if not self.active:
            return

        color = self.bg_color
        text_color = self.text_color

        pygame.draw.rect(surface, color, self.rect)
        label = self.font.render(self.text, True, text_color)
        surface.blit(label, label.get_rect(center=self.rect.center))

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.active:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.function:
                    self.function()


# --- game logic helper functions ---

def get_legal_moves_for_board(
        piece_name: str,
        x: int,
        y: int,
        cols: int,
        rows: int,
        visited: Set[Tuple[int, int]],
        forbidden: Optional[Set[Tuple[int, int]]] = None,
) -> List[Tuple[int, int]]:
    if forbidden is None:
        forbidden = set()
    legal = []
    max_n = max(cols, rows)
    lower_name = piece_name.lower()
    if lower_name in SLIDING_PIECES:
        dirs: List[Tuple[int, int]] = []
        if lower_name == "rook":
            dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        elif lower_name == "bishop":
            dirs = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        elif lower_name == "queen":
            dirs = [
                (1, 0), (-1, 0), (0, 1), (0, -1),
                (1, 1), (1, -1), (-1, 1), (-1, -1)
            ]
        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            while 0 <= nx < cols and 0 <= ny < rows:
                if (nx, ny) not in visited and (nx, ny) not in forbidden:
                    legal.append((nx, ny))
                nx += dx
                ny += dy
    else:
        move_func = pk.get_move_func(piece_name)
        raw = move_func(x, y, max_n)
        for mx, my in raw:
            if (0 <= mx < cols and 0 <= my < rows and
                    (mx, my) not in visited and (mx, my) not in forbidden):
                legal.append((mx, my))
    return legal


def validate_and_apply_codec(codec_text: str, menu_items: list, label_to_index: dict) -> tuple:
    """
    Validate codec and update menu items if valid.
    Returns (is_valid, decoded_params_or_none).
    """
    try:
        params = decode_params(codec_text, polyomino_schema)

        # update menu items with decoded values
        board_idx = label_to_index["board"]
        board_values = menu_items[board_idx][1]
        if params["board"] in board_values:
            board_pos = board_values.index(params["board"])
            menu_items[board_idx] = (menu_items[board_idx][0], board_values, board_pos)

        shapes_idx = label_to_index["shapes"]
        shapes_values = menu_items[shapes_idx][1]
        if params["shapes"] in shapes_values:
            shapes_pos = shapes_values.index(params["shapes"])
            menu_items[shapes_idx] = (menu_items[shapes_idx][0], shapes_values, shapes_pos)

        density_idx = label_to_index["density"]
        density_values = menu_items[density_idx][1]
        if params["density"] in density_values:
            density_pos = density_values.index(params["density"])
            menu_items[density_idx] = (menu_items[density_idx][0], density_values, density_pos)

        colors_idx = label_to_index["colors"]
        colors_values = menu_items[colors_idx][1]
        if params["colors"] in colors_values:
            colors_pos = colors_values.index(params["colors"])
            menu_items[colors_idx] = (menu_items[colors_idx][0], colors_values, colors_pos)

        return True, params

    except (KeyError, ValueError):
        return False, None


def place_puzzle_layout(
        cols: int,
        rows: int,
        shapes_token: str,
        density: float,
        color_mode: str,
        seed: Optional[int] = None,
) -> Tuple[List[PuzzleShape], int]:
    """Deterministic polyomino shape placement using seeded RNG."""
    rng = random.Random(seed)
    used_seed = rng.getrandbits(64) if seed is None else seed
    rng = random.Random(used_seed)
    weights = None

    shape_prefix_map = {"monomino": "mon", "domino": "dom", "triomino": "tri", "tetromino": "tet",
                        "pentomino": "pen", "hexomino": "hex", "heptomino": "hep", "octomino": "oct"}
    prefix = shape_prefix_map.get(shapes_token)

    if prefix:
        chosen = [(name, units) for name, units in pd.SAMPLE_POLYOMINOES.items() if name.startswith(prefix)]
    else:  # handles 'mixed' or other cases
        chosen = list(pd.SAMPLE_POLYOMINOES.items())
        group_sizes = {"mon": 1, "dom": 1, "tri": 2, "tet": 5, "pen": 12, "hex": 35, "hep": 108, "oct": 369}
        type_weights = {
            "mon": 11, "dom": 11, "tri": 11, "tet": 10, "pen": 9, "hex": 6, "hep": 6, "oct": 2,
        }
        weights = [
            type_weights.get(name.split('-')[0], 1) / group_sizes.get(name.split('-')[0], 1)
            for name, _ in chosen
        ]

    if not chosen:
        chosen = list(pd.SAMPLE_POLYOMINOES.items())

    unique_color_map: Dict[str, Tuple[int, int, int]] = {}
    color_pool = None
    shared_color = None
    if color_mode == "unique":
        color_pool = PALETTE[:]
        rng.shuffle(color_pool)
    elif color_mode == "same":
        shared_color = rng.choice(PALETTE)

    target_board_units = math.ceil(cols * rows * density)
    occupancy: Set[Tuple[int, int]] = set()
    puzzle_layout: List[PuzzleShape] = []
    shape_id: int = 1
    max_total_attempts = 8000
    total_attempts = 0
    per_piece_attempts = 500
    occupied_unit_count = 0

    while occupied_unit_count < target_board_units and total_attempts < max_total_attempts:
        total_attempts += 1

        if weights:
            name, units = rng.choices(chosen, weights=weights, k=1)[0]
        else:
            name, units = rng.choice(chosen)

        if color_mode == "unique":
            color = unique_color_map.get(name)
            if color is None:
                if not color_pool:
                    color_pool = PALETTE[:]
                    rng.shuffle(color_pool)
                color = color_pool.pop()
                unique_color_map[name] = color
        elif color_mode == "random":
            color = rng.choice(PALETTE)
        else:
            color = shared_color

        p = Polyomino(units, color=color, name=name)
        rotates = rng.randint(0, 3)
        for _ in range(rotates):
            p = p.rotated()
        if rng.choice([True, False]):
            p = p.flipped()

        bw, bh = p.bounding()
        max_gx = cols - bw
        max_gy = rows - bh
        if max_gx < 0 or max_gy < 0:
            continue

        for _ in range(per_piece_attempts):
            try_gx = rng.randint(0, max_gx)
            try_gy = rng.randint(0, max_gy)
            abs_units = {(try_gx + x, try_gy + y) for (x, y) in p.units}
            if abs_units & occupancy:
                continue
            occupancy.update(abs_units)
            shape = PuzzleShape(
                shape_id, name, abs_units, color, (try_gx, try_gy),
                orientation=f"rot={rotates},flip={p.units != normalize(units)}"
            )
            puzzle_layout.append(shape)
            shape_id += 1
            occupied_unit_count += len(abs_units)
            break
    return puzzle_layout, used_seed


def preview_puzzle_layout(board_model: BoardModel, puzzle_layout: List[PuzzleShape]) -> None:
    board_model.clear()
    for shape in puzzle_layout:
        for gx, gy in shape.puzzle_units:
            board_model.set_cell(gx, gy, shape.color)


def reveal_unit(
        board_model: BoardModel,
        puzzle_layout: List[PuzzleShape],
        gx: int,
        gy: int,
) -> Tuple[bool, Optional[int]]:
    """Checks if a board cell contains a puzzle unit. If it's a newly found unit, returns True and the shape's ID."""
    for shape in puzzle_layout:
        if (gx, gy) in shape.puzzle_units and (gx, gy) not in shape.found_units:
            shape.found_units.add((gx, gy))
            board_model.set_cell(gx, gy, shape.color)
            return True, shape.id
    return False, None


# --- MAIN ---

def main():
    pygame.init()

    info = pygame.display.Info()
    screen_width, screen_height = info.current_w, info.current_h
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)

    pygame.display.set_caption("polyominoes (polyomino_v16)")

    try:
        import ctypes  # noqa: SIM115
        hwnd = pygame.display.get_wm_info()['window']
        ctypes.windll.user32.ShowWindow(hwnd, 3)
    except (KeyError, AttributeError, OSError):
        pass

    clock = pygame.time.Clock()

    font = pygame.font.SysFont("arial", 18)
    font_large = pygame.font.SysFont("arial", 20)
    # font_small = pygame.font.SysFont("arial", 16)

    star_size = 22  # in pixels
    try:
        star_filled_path = os.path.join(markers_dir, "star_filled.png")
        star_empty_path = os.path.join(markers_dir, "star_empty.png")

        star_filled = pygame.image.load(star_filled_path).convert_alpha()
        star_empty = pygame.image.load(star_empty_path).convert_alpha()

        star_filled = pygame.transform.smoothscale(star_filled, (star_size, star_size))
        star_empty = pygame.transform.smoothscale(star_empty, (star_size, star_size))

    except (pygame.error, FileNotFoundError) as e:
        print(f"Warning: Could not load star images: {e}")
        print(f"Looked in: {image_dir_path}")
        star_filled = None
        star_empty = None

    grid_cols = DEFAULT_GRID_COLS
    grid_rows = DEFAULT_GRID_COLS

    globally_valid_pieces = get_globally_valid_pieces()

    board_model = BoardModel(grid_cols, grid_rows)
    board_renderer = BoardRenderer(board_model, 10, (32, 32))
    current_cell_size = 0

    menu_items = [
        ("board", [i for i in range(5, 21)], 3),
        ("piece", globally_valid_pieces, 0),
        ("shapes", ["monomino", "domino", "triomino", "tetromino",
                    "pentomino", "hexomino", "heptomino", "octomino", "mixed"], 4),
        ("density", ["low", "medium", "high"], 1),
        ("colors", ["unique", "random", "same"], 0),
        # ("clock", ["infinity", "per game", "per move"], 0),
    ]

    label_to_index = {label: idx for idx, (label, _, _) in enumerate(menu_items)}

    board_idx = label_to_index["board"]
    for opt_idx, v in enumerate(menu_items[board_idx][1]):
        if v == DEFAULT_GRID_COLS:
            menu_items[board_idx] = (
                menu_items[board_idx][0],
                menu_items[board_idx][1],
                opt_idx
            )
            break

    widget_rects: Dict[Any, pygame.Rect] = {}
    arrows: Dict[Tuple[int, int], pygame.Surface] = {}

    # codec_input rect is temporary; it will be repositioned each frame in the render loop
    codec_input = TextInput(pygame.Rect(0, 0, 100, UI_SPACE), font, max_length=19)

    gamecon = GameController(board_model, board_renderer, menu_items, label_to_index, codec_input)

    gamecon.go_to_menu()
    gamecon.update_playability()
    gamecon.update_challenge_rating()

    buttons = {
        "start": Button(pygame.Rect(0, 0, 0, 0), "start", (255, 255, 255),
                        (92, 192, 92), font, gamecon.start_flow),

        "blind_draw": Button(pygame.Rect(0, 0, 0, 0), "blind draw", (255, 255, 255),
                             (128, 32, 64), font, gamecon.start_blind_draw_flow),

        "guide_mode": Button(pygame.Rect(0, 0, 0, 0), "show move guide", (255, 255, 255),
                             (128, 64, 255), font, gamecon.toggle_guide_mode),

        "track_mode": Button(pygame.Rect(0, 0, 0, 0), "show move #'s", (255, 255, 255),
                             (255, 92, 128), font, gamecon.toggle_track_mode),

        "hint_mode": Button(pygame.Rect(0, 0, 0, 0), "show move hint", (255, 255, 255),
                            (255, 128, 96), font, gamecon.toggle_hint_mode),

        "enter_code": Button(pygame.Rect(0, 0, 0, 0), "enter share code", (255, 255, 255),
                             (255, 0, 255), font, gamecon.toggle_codec_input),

        "copy_code": Button(pygame.Rect(0, 0, 0, 0), "copy share code", (255, 255, 255),
                            (255, 0, 255), font, gamecon.copy_puzzle_code_to_clipboard),

        "peek_mode": Button(pygame.Rect(0, 0, 0, 0), "peek", (255, 255, 240),
                            LT_SQUARE, font, gamecon.toggle_peek),

        "undo_mode": Button(pygame.Rect(0, 0, 0, 0), "undo last move", (255, 255, 255),
                            (64, 128, 255), font, gamecon.undo_last_move),

        "resign": Button(pygame.Rect(0, 0, 0, 0), "resign", (255, 255, 255),
                         DK_VISITED, font, gamecon.resign_game),

        "retry": Button(pygame.Rect(0, 0, 0, 0), "retry", (255, 255, 255),
                        (92, 192, 92), font, gamecon.retry_last_game),

        "replay_mode": Button(pygame.Rect(0, 0, 0, 0), "show replay", (255, 255, 255),
                              (64, 128, 255), font, gamecon.toggle_replay_mode),

        "replay_prev": Button(pygame.Rect(0, 0, 0, 0), "-", (255, 255, 240),
                              (64, 128, 255), font, lambda: gamecon.navigate_replay(-1)),

        "replay_next": Button(pygame.Rect(0, 0, 0, 0), "+", (255, 255, 240),
                              (64, 128, 255), font, lambda: gamecon.navigate_replay(1)),

        "reveal": Button(pygame.Rect(0, 0, 0, 0), "reveal", (255, 255, 255),
                         (255, 128, 96), font, gamecon.toggle_reveal_all_shapes),

        "new_game": Button(pygame.Rect(0, 0, 0, 0), "new game", (255, 255, 255),
                           (32, 128, 96), font, gamecon.new_game_flow),

        "exit": Button(pygame.Rect(0, 0, 0, 0), "exit", (255, 255, 255),
                       (255, 0, 0), font, gamecon.quit_game),
    }

    # main loop
    while True:
        clock.tick(FPS)

        dt = clock.get_time()
        if codec_input:
            codec_input.update(dt)

        # update game timer
        if gamecon.game_state == GameState.INGAME and gamecon.start_time is not None:
            elapsed_ms = pygame.time.get_ticks() - gamecon.start_time
            gamecon.game_time_seconds = elapsed_ms // 1000
        win_width, win_height = screen.get_size()
        screen.fill(BACK_COLOR)

        margin = UI_SPACE
        msg_left = margin
        msg_top = margin
        msg_width = UI_SPACE * 18
        msg_right = msg_left + msg_width
        msg_bottom = win_height - margin
        msg_height = msg_bottom - msg_top

        right_msg_left = win_width - msg_width - margin * 1

        left_panel_rect = pygame.Rect(msg_left, msg_top, msg_width, msg_height)
        right_panel_rect = pygame.Rect(right_msg_left, msg_top, msg_width, msg_height)

        left_panel = UIPanel(left_panel_rect, gap=2)  # 2px gap between stacked panels
        right_panel = UIPanel(right_panel_rect, gap=2)  # 2px gap between stacked panels

        left_panel.draw_panel(screen, "MENU_PANEL", LT_SQUARE, GRID_COLOR)
        left_panel.draw_panel(screen, "BUTTON_PANEL", LT_SQUARE, GRID_COLOR)
        right_panel.draw_panel(screen, "PIECE_PANEL", LT_SQUARE, GRID_COLOR)
        right_panel.draw_panel(screen, "STATS_PANEL", LT_SQUARE, GRID_COLOR)

        area_left = msg_right + margin
        area_top = margin
        area_right = right_msg_left - margin
        area_bottom = win_height - margin
        area_width = area_right - area_left
        area_height = area_bottom - area_top

        new_cell_size = 0
        if gamecon.board_model.cols > 0 and gamecon.board_model.rows > 0:
            cell_w = area_width // gamecon.board_model.cols
            cell_h = area_height // gamecon.board_model.rows
            new_cell_size = max(12, min(cell_w, cell_h))

        if new_cell_size != current_cell_size:
            current_cell_size = new_cell_size
            board_renderer.cell_size = new_cell_size
            try:
                pk.load_images(pieces_dir, max(12, new_cell_size - 4))

                arrow_images = {
                    (0, -1): "arrow_n.png", (1, -1): "arrow_ne.png", (1, 0): "arrow_e.png",
                    (1, 1): "arrow_se.png", (0, 1): "arrow_s.png", (-1, 1): "arrow_sw.png",
                    (-1, 0): "arrow_w.png", (-1, -1): "arrow_nw.png",
                }

                arrows = {}

                arrow_size = current_cell_size // 2

                # Diagonal arrows need to be scaled smaller to appear same visual size
                diagonal_scale_factor = 0.75  # Approximately 1/√2

                for direction, filename in arrow_images.items():
                    path = os.path.join(arrows_dir, filename)
                    try:
                        img = pygame.image.load(path).convert_alpha()

                        # Use smaller size for diagonal arrows
                        dx, dy = direction
                        if dx != 0 and dy != 0:  # Diagonal direction
                            scaled_size = int(arrow_size * diagonal_scale_factor)
                        else:  # Cardinal direction
                            scaled_size = arrow_size

                        scaled_img = pygame.transform.smoothscale(img, (scaled_size, scaled_size))
                        arrows[direction] = scaled_img
                    except Exception as e:
                        print(f"Failed to load arrow image: {filename} from {path} ({e})")
            except Exception as e:
                print(f"Error loading images: {e}")

        board_pixel_w = gamecon.board_model.cols * current_cell_size
        board_pixel_h = gamecon.board_model.rows * current_cell_size

        origin_x = area_left + (area_width - board_pixel_w) // 2
        origin_y = area_top + (area_height - board_pixel_h) // 2
        board_renderer.origin = (origin_x, origin_y)

        if gamecon.game_state == GameState.MENU and gamecon.player_pos:
            current_piece = gamecon.get_current_selections()["piece"]
            gamecon.legal_moves = get_legal_moves_for_board(
                piece_name=current_piece,
                x=gamecon.player_pos[0],
                y=gamecon.player_pos[1],
                cols=gamecon.board_model.cols,
                rows=gamecon.board_model.rows,
                visited=set()
            )

        if gamecon.legal_moves:
            gamecon.last_nonempty_legal_moves = list(gamecon.legal_moves)

        board_renderer.draw_background(screen)

        if gamecon.game_state == GameState.MENU and gamecon.preview_layout:
            for shape in gamecon.preview_layout:
                for gx, gy in shape.puzzle_units:
                    px, py = board_renderer.to_pixel(gx, gy)
                    rect = pygame.Rect(px + 1, py + 1, current_cell_size - 1, current_cell_size - 1)
                    pygame.draw.rect(screen, shape.color, rect)

        if gamecon.reveal_mode_active and gamecon.puzzle_layout:
            for shape in gamecon.puzzle_layout:
                for gx, gy in shape.puzzle_units:
                    px, py = board_renderer.to_pixel(gx, gy)
                    rect = pygame.Rect(px + 1, py + 1, current_cell_size - 1, current_cell_size - 1)
                    pygame.draw.rect(screen, shape.color, rect)

        board_renderer.draw_cells(screen)
        board_renderer.draw_grid_lines(screen)

        if gamecon.active_effect:
            if pygame.time.get_ticks() < gamecon.active_effect["expires"]:
                size = gamecon.active_effect["size"]
                color = gamecon.active_effect["color"]
                center_x, center_y = gamecon.active_effect["center_pos"]
                for x, y in gamecon.active_effect["units"]:
                    rect = pygame.Rect(center_x - size / 2 + x * size, center_y - size / 2 + y * size, size - 2,
                                       size - 2)
                    pygame.draw.rect(screen, color, rect)
            else:
                gamecon.active_effect = None

        cs = current_cell_size
        for (vx, vy) in gamecon.visited:
            if (vx, vy) != gamecon.player_pos:
                px, py = board_renderer.to_pixel(vx, vy)
                in_found = (vx, vy) in gamecon.board_model.grid
                if not in_found:
                    parity = (vx + (gamecon.board_model.rows - 1 - vy)) % 2
                    vcolor = DK_VISITED if parity == 0 else LT_VISITED
                    rect = pygame.Rect(px + 3, py + 3, cs - 4, cs - 4)
                    pygame.draw.rect(screen, vcolor, rect)
                if gamecon.track_mode_active and (vx, vy) in gamecon.visited_moves:
                    if in_found:
                        background_color = gamecon.board_model.grid[(vx, vy)]
                        luma = (background_color[0] * 0.299 + background_color[1] * 0.587 + background_color[2] * 0.114)
                        num_color = (0, 0, 0) if luma > 128 else (255, 255, 255)
                    else:
                        vcolor = DK_VISITED if ((vx + (gamecon.board_model.rows - 1 - vy)) % 2) == 0 else LT_VISITED
                        num_color = (0, 0, 0) if vcolor == LT_VISITED else (255, 255, 255)
                    move_font = pygame.font.SysFont("arial", max(12, cs // 3))
                    num_str = str(gamecon.visited_moves[(vx, vy)])
                    num_surf = move_font.render(num_str, True, num_color)
                    num_rect = num_surf.get_rect(center=(px + cs // 2, py + cs // 2))
                    screen.blit(num_surf, num_rect)

        if gamecon.guide_mode_active and cs > 0 and gamecon.player_pos and arrows:
            # Determine which moves to display
            moves_to_display = []

            if gamecon.game_state in [GameState.INGAME, GameState.MENU]:
                moves_to_display = gamecon.legal_moves
            elif gamecon.game_state == GameState.ENDGAME:
                if gamecon.replay_mode_active:
                    moves_to_display = gamecon.legal_moves  # Uses restored legal_moves from board state
                else:
                    moves_to_display = gamecon.final_legal_moves  # Uses saved final position moves

            # Draw arrows for available moves
            if moves_to_display:
                px_pos, py_pos = gamecon.player_pos
                for mx, my in moves_to_display:
                    dx, dy = mx - px_pos, my - py_pos
                    norm_dx = int(clamp(float(dx), -1.0, 1.0))
                    norm_dy = int(clamp(float(dy), -1.0, 1.0))
                    direction_key = (norm_dx, norm_dy)
                    arrow_surface = arrows.get(direction_key)
                    if arrow_surface:
                        grid_px, grid_py = board_renderer.to_pixel(mx, my)
                        arrow_rect = arrow_surface.get_rect(center=(grid_px + cs // 2, grid_py + cs // 2))
                        screen.blit(arrow_surface, arrow_rect)

        if gamecon.hint_mode_active and cs > 0 and gamecon.hint_degrees:
            hint_font = pygame.font.SysFont("arial", max(12, cs // 3))
            for (hx, hy), degree in gamecon.hint_degrees.items():
                hpx, hpy = board_renderer.to_pixel(hx, hy)
                if (hx, hy) in gamecon.board_model.grid:
                    bg_color = gamecon.board_model.grid[(hx, hy)]
                else:
                    bg_color = LT_SQUARE if (hx + hy) % 2 == 0 else DK_SQUARE
                luma = bg_color[0] * 0.299 + bg_color[1] * 0.587 + bg_color[2] * 0.114
                hint_color = (0, 0, 0) if luma > 128 else (255, 255, 255)
                hint_surf = hint_font.render(str(degree), True, hint_color)
                hint_rect = hint_surf.get_rect(center=(hpx + cs // 2, hpy + cs // 2))
                screen.blit(hint_surf, hint_rect)

        if gamecon.player_pos and cs > 0:
            px, py = board_renderer.to_pixel(*gamecon.player_pos)
            cell_rect = pygame.Rect(px + 1, py + 1, cs - 2, cs - 2)
            try:
                pk.draw_piece(screen, cell_rect, gamecon.get_current_selections()["piece"])
            except (KeyError, ValueError):
                pygame.draw.ellipse(screen, (0, 0, 0), cell_rect)

        widget_rects.clear()

        # define common UI element properties
        btn_w = UI_SPACE
        line_height = font.get_linesize() + UI_SPACE

        widget_rects.clear()

        # --- MENU_PANEL (upper left) ---
        menu_bounds = left_panel.get_bounds("MENU_PANEL")

        text_x = menu_bounds['left'] + UI_SPACE
        max_label_width = max(
            font.render(l + ":", True,
                        (0, 0, 0)).get_width() for l, _, _ in gamecon.menu_items if l != 'piece'
        )
        minus_x = text_x + max_label_width + UI_SPACE
        plus_x = menu_bounds['left'] + menu_bounds['width'] - UI_SPACE * 4

        menu_panel_items = [(i, item) for i, item in enumerate(gamecon.menu_items) if item[0] != 'piece']

        # codec_is_valid = False

        for list_idx, (item_idx, (label, values, cur_idx)) in enumerate(menu_panel_items):
            panel_y = left_panel.get_line_y("MENU_PANEL", list_idx, line_height)
            row_center_y = panel_y + btn_w // 2

            # draw label
            lbl_surf = font.render(f"{label}", True, (0, 0, 0))
            screen.blit(lbl_surf, lbl_surf.get_rect(midleft=(text_x, row_center_y)))

            # show selection text
            show_text = not gamecon.blind_draw_active or gamecon.game_state == GameState.ENDGAME

            if show_text:
                sel_text = str(values[cur_idx])
                sel_surf = font.render(sel_text, True, (0, 0, 0))
                minus_center = minus_x + btn_w / 2
                plus_center = plus_x + btn_w / 2
                sel_center_x = (minus_center + plus_center) / 2
                screen.blit(sel_surf, sel_surf.get_rect(center=(sel_center_x, row_center_y)))

            # draw plus/minus buttons
            if gamecon.game_state == GameState.MENU:
                minus_rect = pygame.Rect(minus_x, panel_y, btn_w * 1.5, btn_w * 1.5)
                pygame.draw.rect(screen, DK_SQUARE, minus_rect)
                lt_color = (0, 160, 0)
                lt = font.render("<", True, lt_color)
                screen.blit(lt, lt.get_rect(center=minus_rect.center))
                widget_rects[("minus", item_idx)] = minus_rect

                plus_rect = pygame.Rect(plus_x, panel_y, btn_w * 1.5, btn_w * 1.5)
                pygame.draw.rect(screen, DK_SQUARE, plus_rect)
                gt_color = (255, 0, 0)
                gt = font.render(">", True, gt_color)
                screen.blit(gt, gt.get_rect(center=plus_rect.center))
                widget_rects[("plus", item_idx)] = plus_rect

        # blind draw button
        buttons["blind_draw"].active = gamecon.game_state == GameState.MENU and not gamecon.seed_mode_active
        buttons["blind_draw"].rect = left_panel.get_widget_rect("MENU_PANEL", 6, BTW, BTH)
        buttons["blind_draw"].draw(screen)

        # retry button
        buttons["retry"].active = gamecon.game_state == GameState.ENDGAME
        buttons["retry"].rect = left_panel.get_widget_rect("MENU_PANEL", 6, BTW, BTH)
        buttons["retry"].draw(screen)

        # enter share code button
        buttons["enter_code"].active = gamecon.game_state == GameState.MENU

        if gamecon.seed_mode_active:
            buttons["enter_code"].bg_color = (224, 64, 128)
            buttons["enter_code"].text = "cancel code input"
        else:
            buttons["enter_code"].bg_color = (224, 0, 96)
            buttons["enter_code"].text = "enter share code"

        buttons["enter_code"].rect = left_panel.get_widget_rect("MENU_PANEL", 8, BTW, BTH)
        buttons["enter_code"].draw(screen)

        # codec input box
        if gamecon.game_state == GameState.MENU and gamecon.seed_mode_active:
            codec_panel_line = 8
            codec_panel_y = left_panel.get_line_y("MENU_PANEL", codec_panel_line, line_height)
            input_box_width = 192
            input_box_x = menu_bounds['left'] + (menu_bounds['width'] - input_box_width) // 2
            codec_input.rect = pygame.Rect(input_box_x, codec_panel_y, input_box_width, BTH)
            codec_input.draw(screen)

        # display codec
        if gamecon.puzzle_code and gamecon.game_state in [GameState.WAITING, GameState.INGAME, GameState.ENDGAME]:
            codec_display_line = 8
            codec_display_y = left_panel.get_line_y("MENU_PANEL", codec_display_line, line_height)
            codec_row_center_y = codec_display_y + btn_w

            # draw codec
            codec_value_surf = font.render(gamecon.puzzle_code, True, (0, 0, 0))
            sel_center_x = (menu_bounds['left'] + menu_bounds['left'] + menu_bounds['width']) / 2
            screen.blit(codec_value_surf, codec_value_surf.get_rect(center=(sel_center_x, codec_row_center_y)))

        # copy share code button
        buttons["copy_code"].active = gamecon.game_state in (GameState.WAITING, GameState.INGAME, GameState.ENDGAME)

        if gamecon.copy_button_clicked:
            buttons["copy_code"].active = True
            buttons["copy_code"].bg_color = (224, 64, 128)
            buttons["copy_code"].text = "share code copied"
        else:
            buttons["copy_code"].bg_color = (224, 0, 96)
            buttons["copy_code"].text = "copy share code"

        buttons["copy_code"].rect = left_panel.get_widget_rect("MENU_PANEL", 8, BTW, BTH)
        buttons["copy_code"].draw(screen)

        # --- BUTTON PANEL (lower left) ---

        button_bounds = left_panel.get_bounds("BUTTON_PANEL")

        # click a starting square message
        if gamecon.game_state == GameState.WAITING:
            choose_y = left_panel.get_line_y("BUTTON_PANEL", 0, line_height)
            choose_text = "click a starting square"
            choose_surf = font.render(choose_text, True, (255, 0, 0))
            choose_rect = choose_surf.get_rect(centerx=button_bounds['center_x'], centery=choose_y + btn_w / 2)
            screen.blit(choose_surf, choose_rect)

        # start button
        if gamecon.seed_mode_active:
            code_entered = codec_input.get_text()
            start_button_enabled = len(code_entered) == 16 and \
                                   validate_and_apply_codec(code_entered, gamecon.menu_items, gamecon.label_to_index)[0]
            buttons["start"].active = start_button_enabled and gamecon.game_state == GameState.MENU
        else:
            buttons["start"].active = gamecon.is_piece_playable and gamecon.game_state == GameState.MENU

        buttons["start"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        buttons["start"].draw(screen)

        # reveal button
        buttons["reveal"].active = gamecon.game_state == GameState.ENDGAME
        buttons["reveal"].text = 'hide missed units' if gamecon.reveal_mode_active else 'show all units'
        buttons["reveal"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        buttons["reveal"].draw(screen)

        # move guide button (grayed out when hint mode is active)
        buttons["guide_mode"].active = not gamecon.hint_mode_active
        buttons["guide_mode"].text = 'hide move guide' if gamecon.guide_mode_active else 'show move guide'
        buttons["guide_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 2, BTW, BTH)
        buttons["guide_mode"].draw(screen)

        # move track button
        buttons["track_mode"].active = gamecon.game_state in (GameState.MENU, GameState.INGAME, GameState.ENDGAME)
        buttons["track_mode"].text = 'hide move numbers' if gamecon.track_mode_active else 'show move numbers'
        buttons["track_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 4, BTW, BTH)
        buttons["track_mode"].draw(screen)

        # hint mode button (active only in INGAME)
        buttons["hint_mode"].active = gamecon.game_state == GameState.INGAME
        buttons["hint_mode"].text = 'hide move hints' if gamecon.hint_mode_active else 'show move hints'
        buttons["hint_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        buttons["hint_mode"].draw(screen)

        # undo button
        buttons["undo_mode"].active = gamecon.game_state == GameState.INGAME
        buttons["undo_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 6, BTW, BTH)
        buttons["undo_mode"].draw(screen)

        # resign button
        buttons["resign"].active = gamecon.game_state == GameState.INGAME
        buttons["resign"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 8, BTW, BTH)
        buttons["resign"].draw(screen)

        # replay button
        buttons["replay_mode"].active = gamecon.game_state == GameState.ENDGAME

        if gamecon.replay_mode_active:
            buttons["replay_mode"].text = 'end replay'
        else:
            buttons["replay_mode"].text = 'start replay'

        buttons["replay_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 6, BTW, BTH)
        buttons["replay_mode"].draw(screen)

        # replay navigation buttons
        buttons["replay_prev"].active = False
        buttons["replay_next"].active = False

        if gamecon.replay_mode_active and hasattr(gamecon, 'replay_index') and hasattr(gamecon, 'move_history'):
            # Left button (previous move)
            if gamecon.replay_index > 0:  # Not at first move
                buttons["replay_prev"].active = True
                buttons["replay_prev"].rect = pygame.Rect(
                    buttons["replay_mode"].rect.left - UI_SPACE * 3,  # BTW // 2,
                    buttons["replay_mode"].rect.top,
                    BTW // 4,
                    BTH
                )
                buttons["replay_prev"].draw(screen)

            # Right button (next move)
            if gamecon.replay_index < len(gamecon.move_history) - 1:  # Not at last move
                buttons["replay_next"].active = True
                buttons["replay_next"].rect = pygame.Rect(
                    buttons["replay_mode"].rect.right + 12,
                    buttons["replay_mode"].rect.top,
                    BTW // 4,
                    BTH
                )
                buttons["replay_next"].draw(screen)

        # new game button
        buttons["new_game"].active = gamecon.game_state in (GameState.WAITING, GameState.ENDGAME)
        buttons["new_game"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 8, BTW, BTH)
        buttons["new_game"].draw(screen)

        # peek button
        buttons["peek_mode"].active = gamecon.game_state in (GameState.WAITING, GameState.INGAME, GameState.ENDGAME)
        buttons["peek_mode"].rect = pygame.Rect(msg_left + UI_SPACE * 2, msg_bottom - UI_SPACE * 3, BTW // 2, BTH)
        buttons["peek_mode"].text = 'hide' if gamecon.peek_mode_visible else 'peek'
        buttons["peek_mode"].draw(screen)

        # exit button
        buttons["exit"].rect = pygame.Rect(msg_right - UI_SPACE * 5, msg_bottom - UI_SPACE * 2, BTW // 3, BTH / 1.5)
        buttons["exit"].draw(screen)

        # peek mode thumbnail
        draw_peek_thumbnail(
            screen, gamecon.board_model, gamecon.puzzle_layout, gamecon.peek_mode_visible,
            left_panel, line_height
        )

        # --- PIECE_PANEL (upper right) ---

        piece_bounds = right_panel.get_bounds("PIECE_PANEL")

        right_text_x = piece_bounds['left'] + UI_SPACE
        piece_idx = gamecon.label_to_index["piece"]
        _, piece_values, piece_cur_idx = gamecon.menu_items[piece_idx]

        piece_line = 0
        panel_y = right_panel.get_line_y("PIECE_PANEL", piece_line, line_height)
        row_center_y = panel_y

        lbl_surf = font.render("piece:", True, (0, 0, 0))
        lbl_rect = lbl_surf.get_rect(midleft=(right_text_x, row_center_y))
        right_minus_x = lbl_rect.right + UI_SPACE
        right_plus_x = piece_bounds['left'] + piece_bounds['width'] - UI_SPACE - btn_w * 3
        sel_center_x = piece_bounds['center_x']

        sel_text = str(piece_values[piece_cur_idx]) if piece_values else ""
        sel_surf = font_large.render(sel_text, True, (0, 0, 0))
        screen.blit(sel_surf, sel_surf.get_rect(center=(sel_center_x, row_center_y + 8)))

        move_set_text = pk.get_piece_move_sets_text(sel_text)
        move_set_surf = font.render(move_set_text, True, (0, 0, 0))
        move_set_rect = move_set_surf.get_rect(centerx=sel_center_x,
                                               top=row_center_y + sel_surf.get_height() + font.get_linesize())
        screen.blit(move_set_surf, move_set_rect)

        # minus/plus piece buttons
        if gamecon.game_state == GameState.MENU:
            minus_rect_right = pygame.Rect(right_minus_x - btn_w, panel_y, btn_w * 1.5, btn_w * 1.5)
            pygame.draw.rect(screen, DK_SQUARE, minus_rect_right)
            lt = font.render("<", True, (0, 160, 0))
            screen.blit(lt, lt.get_rect(center=minus_rect_right.center))
            widget_rects[("minus", piece_idx)] = minus_rect_right

            plus_rect_right = pygame.Rect(right_plus_x - btn_w, panel_y, btn_w * 1.5, btn_w * 1.5)
            pygame.draw.rect(screen, DK_SQUARE, plus_rect_right)
            gt = font.render(">", True, (255, 0, 0))
            screen.blit(gt, gt.get_rect(center=plus_rect_right.center))
            widget_rects[("plus", piece_idx)] = plus_rect_right

        # draw mobility and agility ratings
        piece_line = 3
        piece_bounds = right_panel.get_bounds("PIECE_PANEL")

        selections = gamecon.get_current_selections()
        current_ratings = pr.get_piece_ratings(selections["piece"], selections["board"], selections["shapes"])
        mobility_rating = current_ratings.get('mobility_rating', 0)
        agility_rating = current_ratings.get('agility_rating', 0)

        star_spacing = 3

        # --- MOBILITY RATING ---
        if gamecon.is_piece_playable:
            y_pos = right_panel.get_line_y("PIECE_PANEL", piece_line, line_height)
            label_surf = font.render("mobility ", True, (0, 0, 0))
            label_width = label_surf.get_width()

            if star_filled and star_empty:
                # Calculate total width: label + spacing + stars
                stars_width = 5 * star_size + 4 * star_spacing
                total_width = label_width + 8 + stars_width
                start_x = piece_bounds['center_x'] - total_width // 2

                # Draw label
                screen.blit(label_surf, (start_x, y_pos))

                # Draw stars
                star_x = start_x + label_width + 8
                star_y = y_pos + (font.get_linesize() - star_size) // 2
                for i in range(mobility_rating):
                    screen.blit(star_filled, (star_x + i * (star_size + star_spacing), star_y))
                for i in range(5 - mobility_rating):
                    offset_x = star_x + (mobility_rating + i) * (star_size + star_spacing)
                    screen.blit(star_empty, (offset_x, star_y))
            else:
                # Fallback: render entire string and center it
                stars = "★" * mobility_rating + "☆" * (5 - mobility_rating)
                full_text = f"mobility {stars}"
                fallback_surf = font.render(full_text, True, (0, 0, 0))
                fallback_rect = fallback_surf.get_rect(centerx=piece_bounds['center_x'], top=y_pos)
                screen.blit(fallback_surf, fallback_rect)

            # --- AGILITY RATING ---
            piece_line += 1
            y_pos = right_panel.get_line_y("PIECE_PANEL", piece_line, line_height)
            agility_label_surf = font.render("agility    ", True, (0, 0, 0))
            label_width = agility_label_surf.get_width()

            if star_filled and star_empty:
                if agility_rating > 0:
                    # Calculate total width: label + spacing + stars
                    stars_width = 5 * star_size + 4 * star_spacing
                    total_width = label_width + 8 + stars_width
                    start_x = piece_bounds['center_x'] - total_width // 2

                    # Draw label
                    screen.blit(agility_label_surf, (start_x, y_pos))

                    # Draw stars
                    star_x = start_x + label_width + 8
                    star_y = y_pos + (font.get_linesize() - star_size) // 2
                    for i in range(agility_rating):
                        screen.blit(star_filled, (star_x + i * (star_size + star_spacing), star_y))
                    for i in range(5 - agility_rating):
                        offset_x = star_x + (agility_rating + i) * (star_size + star_spacing)
                        screen.blit(star_empty, (offset_x, star_y))
            else:
                # Fallback: render entire string and center it
                if agility_rating > 0:
                    stars = "★" * agility_rating + "☆" * (5 - agility_rating)
                    full_text = f"agility{stars}"
                    text_color = (0, 0, 0)
                else:
                    full_text = "agility --"
                    text_color = (128, 128, 128)

                fallback_surf = font.render(full_text, True, text_color)
                fallback_rect = fallback_surf.get_rect(centerx=piece_bounds['center_x'], top=y_pos)
                screen.blit(fallback_surf, fallback_rect)

            # draw challenge rating
            challenge_line = 8
            challenge_y = right_panel.get_line_y("PIECE_PANEL", challenge_line, line_height)
            piece_bounds = right_panel.get_bounds("PIECE_PANEL")
            challenge_stars = max(0, min(5, round(gamecon.challenge_rating)))

            # Calculate total width of the entire element
            challenge_label_surf = font.render("challenge ", True, (0, 0, 0))
            label_width = challenge_label_surf.get_width()

            if star_filled and star_empty:
                # Width calculation: label + spacing + 5 stars + gaps between stars
                star_spacing = 3
                stars_width = 5 * star_size + 4 * star_spacing
                total_width = label_width + 8 + stars_width  # 8 is spacing between label and stars

                # Center the entire element
                start_x = piece_bounds['center_x'] - total_width // 2

                # Draw label
                screen.blit(challenge_label_surf, (start_x, challenge_y))

                # Draw stars
                star_x = start_x + label_width + 8
                star_y = challenge_y + (font.get_linesize() - star_size) // 2
                for i in range(challenge_stars):
                    screen.blit(star_filled, (star_x + i * (star_size + star_spacing), star_y))
                for i in range(5 - challenge_stars):
                    offset_x = star_x + (challenge_stars + i) * (star_size + star_spacing)
                    screen.blit(star_empty, (offset_x, star_y))
            else:
                # Fallback: render entire string as text and center it
                stars = "★" * challenge_stars + "☆" * (5 - challenge_stars)
                full_text = f"challenge {stars}"
                fallback_surf = font.render(full_text, True, (0, 0, 0))
                fallback_rect = fallback_surf.get_rect(centerx=piece_bounds['center_x'], top=challenge_y)
                screen.blit(fallback_surf, fallback_rect)

        # piece too big for board
        piece_line = 3
        y_pos = right_panel.get_line_y("PIECE_PANEL", piece_line, line_height)

        if gamecon.game_state == GameState.MENU:
            if not gamecon.is_piece_playable:
                warning_text = "use a larger board for this piece"
                warn_surf = font.render(warning_text, True, (128, 0, 0))
                warn_rect = warn_surf.get_rect(centerx=piece_bounds['center_x'], top=y_pos)
                screen.blit(warn_surf, warn_rect)

        # --- STATS_PANEL (lower right) ---

        stats_bounds = right_panel.get_bounds("STATS_PANEL")

        # stats lines: moves, units found, shapes found, scores
        if gamecon.game_state in (GameState.WAITING, GameState.INGAME, GameState.ENDGAME):
            stats_line = 1
            stat_y = right_panel.get_line_y("STATS_PANEL", stats_line, line_height)

            if len(gamecon.visited) == 1:
                moves_surf = font.render(f"{len(gamecon.visited)} move", True, (0, 0, 0))
            else:
                moves_surf = font.render(f"{len(gamecon.visited)} moves", True, (0, 0, 0))

            moves_rect = moves_surf.get_rect(centerx=stats_bounds['center_x'], top=stat_y)
            screen.blit(moves_surf, moves_rect)

            stats_line += 1
            stat_y = right_panel.get_line_y("STATS_PANEL", stats_line, line_height)

            found_units_surf = font.render(f"{gamecon.found_puzzle_units} of {gamecon.total_puzzle_units} units found",
                                           True, (0, 0, 0))
            found_units_rect = found_units_surf.get_rect(centerx=stats_bounds['center_x'], top=stat_y)
            screen.blit(found_units_surf, found_units_rect)

            stats_line += 1
            stat_y = right_panel.get_line_y("STATS_PANEL", stats_line, line_height)

            targets_found_surf = font.render(f"{gamecon.completed_shape_count} of "
                                             f"{len(gamecon.puzzle_layout or [])} shapes found", True, (0, 0, 0))
            targets_found_rect = targets_found_surf.get_rect(centerx=stats_bounds['center_x'], top=stat_y)
            screen.blit(targets_found_surf, targets_found_rect)

            # stats_line += 1
            # stat_y = right_panel.get_line_y("STATS_PANEL", stats_line, line_height)

            # max_score = gamecon.unit_factor + gamecon.shape_factor
            # completion_score_surf = font.render(f"{gamecon.completion_score} of {max_score} points",
            #                         True, (0, 0, 0))
            # completion_score_rect = completion_score_surf.get_rect(centerx=stats_bounds['center_x'], top=stat_y)
            # screen.blit(completion_score_surf, completion_score_rect)
            stats_line += 1

            # if gamecon.game_state == GameState.ENDGAME and gamecon.endgame_scores:
            #    scores = gamecon.endgame_scores
            #    stat_y = right_panel.get_line_y("STATS_PANEL", stats_line, line_height)
            #    final_score_text = f"final score: {scores.get('final_score', 0)}"
            #    final_score_surf = font.render(final_score_text, True, (0, 0, 0))
            #    final_score_rect = completion_score_surf.get_rect(centerx=stats_bounds['center_x'], top=stat_y)
            # screen.blit(final_score_surf, final_score_rect)

            # draw clock
            time_str = format_time(gamecon.game_time_seconds) \
                if gamecon.game_state != GameState.WAITING else "0:00"
            absolute_clock_y = stats_bounds['bottom'] - line_height * 1.5
            clock_surf = font.render(time_str, True, (0, 0, 0))
            clock_rect = clock_surf.get_rect(centerx=stats_bounds['center_x'],
                                             centery=absolute_clock_y + line_height // 2)
            screen.blit(clock_surf, clock_rect)

        # endgame detection logic
        if gamecon.puzzle_layout is not None and gamecon.game_state == GameState.INGAME and gamecon.found_puzzle_units >= gamecon.total_puzzle_units:
            gamecon.go_to_endgame('all shapes found')
        if gamecon.game_state == GameState.INGAME and not gamecon.legal_moves:
            gamecon.go_to_endgame('no legal moves')

        # endgame reason
        if gamecon.game_state == GameState.ENDGAME and gamecon.endgame_reason is not None:
            stats_y = stats_bounds['top'] + UI_SPACE * 2
            endgame_messages = {
                'resigned': 'resigned',
                'no legal moves': 'no legal moves',
                'all shapes found': 'all shapes found',
                "time's up": "time's up"
            }
            endgame_colors = {
                'resigned': (255, 0, 0),
                'no legal moves': (255, 0, 0),
                'all shapes found': (0, 128, 0),
                "time's up": (0, 0, 255)
            }
            reason = str(gamecon.endgame_reason)
            msg_text = endgame_messages.get(reason, 'game over')
            endgame_color = endgame_colors.get(reason, (255, 0, 0))
            end_surf = font.render(msg_text, True, endgame_color)
            end_rect = end_surf.get_rect(centerx=stats_bounds['center_x'], top=stats_y)
            screen.blit(end_surf, end_rect)

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                gamecon.go_to_menu()

            # handle replay navigation with arrow keys
            if event.type == pygame.KEYDOWN and gamecon.replay_mode_active:
                if event.key == pygame.K_LEFT:
                    gamecon.navigate_replay(-1)
                elif event.key == pygame.K_RIGHT:
                    gamecon.navigate_replay(1)

            for button in buttons.values():
                button.handle_event(event)

            # handle codec input
            if gamecon.game_state == GameState.MENU and gamecon.seed_mode_active:
                if codec_input and codec_input.handle_event(event):
                    # Text changed, revalidate
                    if len(codec_input.get_text()) >= 16:
                        is_valid, decoded_params = validate_and_apply_codec(codec_input.get_text(), gamecon.menu_items,
                                                                            gamecon.label_to_index)
                        if is_valid:
                            gamecon.decoded_seed = decoded_params["seed"]  # store the seed
                            gamecon.resize_board_if_needed()
                            gamecon.update_playability()
                            gamecon.update_challenge_rating()
                            gamecon.generate_menu_preview()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                clicked_on_ui = False

                if gamecon.game_state == GameState.MENU:
                    for key, rect in widget_rects.items():
                        if rect.collidepoint(mx, my):
                            clicked_on_ui = True
                            action, idx = key
                            label, values, cur_idx = gamecon.menu_items[idx]

                            if action == "minus":
                                gamecon.menu_items[idx] = (label, values, (cur_idx - 1) % len(values))
                            elif action == "plus":
                                gamecon.menu_items[idx] = (label, values, (cur_idx + 1) % len(values))

                            if gamecon.seed_mode_active:

                                # check if switched to seed mode with existing codec
                                if gamecon.seed_mode_active and codec_input and len(codec_input.get_text()) >= 16:
                                    is_valid, decoded_params = validate_and_apply_codec(
                                        codec_input.get_text(), gamecon.menu_items, gamecon.label_to_index
                                    )
                                    if is_valid:
                                        gamecon.decoded_seed = decoded_params["seed"]
                                        gamecon.resize_board_if_needed()
                                        gamecon.update_playability()
                                        gamecon.update_challenge_rating()
                                        gamecon.generate_menu_preview()
                                        break

                            if label == "board":
                                gamecon.resize_board_if_needed()
                                gamecon.update_playability()
                                gamecon.update_challenge_rating()
                                gamecon.generate_menu_preview()
                            else:
                                gamecon.update_playability()
                                gamecon.update_challenge_rating()
                                if label != "piece":
                                    gamecon.generate_menu_preview()
                            break

                if clicked_on_ui:
                    continue

                if gamecon.game_state == GameState.MENU:
                    grid_pos = board_renderer.to_grid(*event.pos)
                    if grid_pos:
                        gamecon.player_pos = grid_pos
                elif gamecon.game_state == GameState.WAITING:
                    grid_pos = board_renderer.to_grid(*event.pos)
                    if grid_pos: gamecon.commit_start_square(*grid_pos)
                elif gamecon.game_state == GameState.INGAME:
                    grid_pos = board_renderer.to_grid(*event.pos)
                    if grid_pos and grid_pos in gamecon.legal_moves:
                        if gamecon.player_pos is not None:
                            gamecon.visited_moves[gamecon.player_pos] = len(gamecon.visited)
                        gamecon.player_pos = grid_pos
                        gamecon.visited.add(gamecon.player_pos)
                        revealed, revealed_shape_id = reveal_unit(gamecon.board_model, gamecon.puzzle_layout,
                                                                  *gamecon.player_pos)
                        if revealed and revealed_shape_id is not None:
                            gamecon.process_found_unit(revealed_shape_id, grid_pos)
                        elif not revealed:
                            parity = (gamecon.player_pos[0] + (
                                        gamecon.board_model.rows - 1 - gamecon.player_pos[1])) % 2
                            vcolor = DK_VISITED if parity == 0 else LT_VISITED
                            gamecon.board_model.set_cell(gamecon.player_pos[0], gamecon.player_pos[1], vcolor)
                        current_piece = gamecon.get_current_selections()["piece"]
                        px, py = gamecon.player_pos
                        gamecon.legal_moves = get_legal_moves_for_board(
                            current_piece,
                            px,
                            py,
                            gamecon.board_model.cols,
                            gamecon.board_model.rows,
                            gamecon.visited,
                        )
                        # Capture board state after the move for undo/replay history
                        gamecon.move_history.append(gamecon.player_pos)
                        gamecon.board_state_history.append(gamecon.capture_board_state())
                        gamecon.update_hint_degrees_if_active()

        pygame.display.flip()


if __name__ == "__main__":
    main()