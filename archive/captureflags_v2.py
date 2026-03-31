# captureflags_v2.py

import sys
import os
import time
import random
from enum import Enum, auto
from typing import Optional, List, Tuple, Set, Dict

import pygame

# --- sharedlib path setup ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SHAREDLIB = os.path.join(BASE_DIR, "sharedlib")
if _SHAREDLIB not in sys.path:
    sys.path.insert(0, _SHAREDLIB)

import piecekeeper as pk
from gameboard import BoardModel, BoardRenderer
from uipanel import UIPanel
from text_input import TextInput
from puzzle_codec import encode_params, decode_params
from move_hint import calculate_hint_degrees

# --- directory paths ---
pieces_dir = os.path.join(BASE_DIR, "assets", "pieces")
arrows_dir = os.path.join(BASE_DIR, "assets", "arrows")
markers_dir = os.path.join(BASE_DIR, "assets", "markers")
flags_dir = os.path.join(BASE_DIR, "assets", "flags")

# --- constants ---
FPS = 60
UI_SPACE = 16
BTW = int(UI_SPACE * 9)
BTH = int(UI_SPACE * 2)

BOARD_MIN = 5
BOARD_MAX = 16
BOARD_DEFAULT = 8
CLOCK_DEFAULT = 0
MAX_CLOCK_MINUTES = 30     # maximum clock setting in minutes

PATH_LENGTH_CHOICES = ["short", "medium", "long", "super"]
PATH_LENGTH_MAP = {"short": 2, "medium": 3, "long": 4, "super": 5}

FLAG_DENSITY_CHOICES = ["low", "medium", "high"]
FLAG_DENSITY_MAP = {"low": 0.2, "medium": 0.3, "high": 0.4}

FLAG_ORDER_CHOICES = ["any", "next", "only"]

PIECE_MIN_BOARD_SIZE_FOR_MAZE = {
    "knight": 5, "king": 5, "queen": 5, "rook": 5, "bishop": 5,
    "gamma": 5, "delta": 5, "theta": 5, "lambda": 8, "xi": 5,
    "pi": 5, "sigma": 5, "phi": 8, "psi": 8, "omega": 8,
    "mercury": 5, "venus": 5, "earth": 5, "mars": 5,
    "jupiter": 5, "saturn": 5, "uranus": 5, "neptune": 5,
    "ceres": 5, "pallas": 8, "pluto": 16,
    "leo": 5, "virgo": 5, "libra": 5,
    "scorpio": 6, "sagittarius": 5, "capricorn": 5,
    "fibonacci": 5, "gunkan": 5,
}

# --- colors ---
LT_SQUARE = (255, 255, 240)
DK_SQUARE = (232, 200, 150)
LT_VISITED = (192, 192, 192)
DK_VISITED = (128, 128, 128)
GRID_COLOR = (107, 70, 51)
BACK_COLOR = (244, 228, 195)
FLAG_SQ_DK = (189, 135, 249)
FLAG_SQ_LT = (220, 195, 248)


# --- flag image fallback colors ---
FLAG_IMG_FALLBACK_COLORS = {
    "blue": (30, 100, 220),
    "green": (50, 180, 50),
    "purple": (140, 70, 210),
    "red": (220, 40, 40),
    "ivory": (200, 175, 130),
    "tan": (170, 140, 95),
}

# --- codec schema ---
# Board is stored as (board_size - BOARD_MIN) so values 0-11 fit in 4 bits (supports 5-16).
captureflags_schema = [
    ("board", 4, lambda v: int(v) - BOARD_MIN),
    ("path_length", 2, {"short": 0, "medium": 1, "long": 2}),
    ("flag_density", 2, {"low": 0, "medium": 1, "high": 2}),
    ("flag_order", 2, {"any": 0, "only": 1, "next": 2}),
]


# --- GameState ---
class GameState(Enum):
    MENU = auto()
    INGAME = auto()
    ENDGAME = auto()


# --- Button ---
class Button:
    def __init__(self, rect, text, text_color, bg_color, font, function=None):
        self.rect = rect
        self.text = text
        self.text_color = text_color
        self.bg_color = bg_color
        self.font = font
        self.function = function
        self.active = True

    def draw(self, surface):
        if not self.active:
            return
        pygame.draw.rect(surface, self.bg_color, self.rect)
        label = self.font.render(self.text, True, self.text_color)
        surface.blit(label, label.get_rect(center=self.rect.center))

    def handle_event(self, event):
        if not self.active:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.function:
                    self.function()


# --- utility functions ---

def clamp(n, a, b):
    return max(a, min(b, n))


def format_time(total_seconds):
    total_seconds = max(0, int(total_seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def format_clock_seconds(seconds):
    if seconds is None:
        seconds = 0
    seconds = max(0, int(seconds))
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins}:{secs:02d}"


def display_for_selection(clock_selected):
    if clock_selected == 0:
        return "infinity"
    return format_clock_seconds(clock_selected)


def remaining_for(clock_selected, clock_elapsed):
    if clock_selected == 0:
        return None
    return max(0, int(clock_selected) - int(clock_elapsed or 0))


def clock_has_expired(clock_selected, clock_elapsed):
    if clock_selected == 0:
        return False
    return int(clock_elapsed or 0) >= int(clock_selected)


def get_min_board_size(piece_name):
    return PIECE_MIN_BOARD_SIZE_FOR_MAZE.get(piece_name, 5)


# --- game logic ---

def get_legal_moves_for_board(piece_name, x, y, cols, rows, visited, forbidden=None):
    if forbidden is None:
        forbidden = set()
    move_func = pk.get_move_func(piece_name)
    n = max(cols, rows)
    raw = move_func(x, y, n)
    return [
        (mx, my) for mx, my in raw
        if 0 <= mx < cols and 0 <= my < rows
        and (mx, my) not in visited
        and (mx, my) not in forbidden
    ]


def generate_open_path_with_flags(
        board_size,
        min_length=None,
        max_length=None,
        move_func=None,
        max_attempts=1000,
        time_budget=None,
        flag_density_choice="low",
        seed=None,
):
    rng = random.Random(seed)
    if move_func is None:
        move_func = pk.get_move_func("knight")
    if min_length is None:
        min_length = board_size + 1
    if max_length is None:
        max_length = board_size * 2

    squares = [(x, y) for x in range(board_size) for y in range(board_size)]
    start_time = time.time() if time_budget is not None else None

    for _ in range(max_attempts or 1000):
        if time_budget is not None and (time.time() - start_time) > time_budget:
            break
        start = rng.choice(squares)
        path = [start]
        path_set = {start}
        while len(path) < max_length:
            current = path[-1]
            moves = [m for m in move_func(*current, board_size) if m not in path_set]
            if not moves:
                break
            path.append(rng.choice(moves))
            path_set.add(path[-1])
        if len(path) >= min_length:
            num_flags = max(1, int(len(path) * FLAG_DENSITY_MAP[flag_density_choice]))
            last_idx = len(path) - 1
            num_random = num_flags - 1
            pool = list(range(len(path) - 1))
            k = min(num_random, len(pool))
            random_indices = rng.sample(pool, k=k)
            flags_idx = sorted(random_indices + [last_idx])
            return path, [path[i] for i in flags_idx]
    return None, None


def validate_and_apply_codec(codec_text, menu_items, label_to_index):
    try:
        params = decode_params(codec_text, captureflags_schema)
        # Decode stores (board_size - BOARD_MIN); add BOARD_MIN back to get the actual size.
        board_val = params.get("board", 0) + BOARD_MIN
        if not (BOARD_MIN <= board_val <= BOARD_MAX):
            return False, None
        path_len = params.get("path_length")
        if path_len not in PATH_LENGTH_CHOICES:
            return False, None
        flag_den = params.get("flag_density")
        if flag_den not in FLAG_DENSITY_CHOICES:
            return False, None
        flag_ord = params.get("flag_order")
        if flag_ord not in FLAG_ORDER_CHOICES:
            return False, None

        board_idx = label_to_index["board"]
        board_values = menu_items[board_idx][1]
        if board_val in board_values:
            menu_items[board_idx] = (menu_items[board_idx][0], board_values, board_values.index(board_val))

        pl_idx = label_to_index["path length"]
        pl_values = menu_items[pl_idx][1]
        menu_items[pl_idx] = (menu_items[pl_idx][0], pl_values, pl_values.index(path_len))

        fd_idx = label_to_index["flag density"]
        fd_values = menu_items[fd_idx][1]
        menu_items[fd_idx] = (menu_items[fd_idx][0], fd_values, fd_values.index(flag_den))

        fo_idx = label_to_index["flag order"]
        fo_values = menu_items[fo_idx][1]
        menu_items[fo_idx] = (menu_items[fo_idx][0], fo_values, fo_values.index(flag_ord))

        return True, {**params, "board": board_val}  # expose corrected board size
    except Exception:
        return False, None


def draw_peek_flags_thumbnail(screen, cols, rows, path, flags,
                               peek_mode_visible, left_panel, line_height):
    if not (path and peek_mode_visible):
        return
    if cols < 1 or rows < 1:
        return

    button_bounds = left_panel.get_bounds("BUTTON_PANEL")
    peek_line = 0
    thumb_area_y = left_panel.get_line_y("BUTTON_PANEL", peek_line, line_height)
    thumb_area = pygame.Rect(
        button_bounds['left'] + UI_SPACE,
        thumb_area_y,
        button_bounds['width'] - UI_SPACE * 2,
        button_bounds['bottom'] - thumb_area_y - UI_SPACE * 4,
    )

    max_cell = min(
        thumb_area.width // cols if cols else 1,
        thumb_area.height // rows if rows else 1,
    )
    if max_cell < 2:
        return

    tw, th = cols * max_cell, rows * max_cell
    tx = thumb_area.left + (thumb_area.width - tw) // 2
    ty = thumb_area.top + (thumb_area.height - th) // 2

    # Create a set of flag positions for quick lookup
    flag_positions = set(flags)

    # Draw checkerboard background with color for flag squares
    for gy in range(rows):
        for gx in range(cols):
            if (gx, gy) in flag_positions:
                # Use FLAG_SQ_LT for dark squares, keep light squares as LT_SQUARE
                if (gx + gy) % 2 == 0:
                    color = FLAG_SQ_LT  # Light square with flag
                else:
                    color = FLAG_SQ_DK  # Dark square with flag
            else:
                color = LT_SQUARE if (gx + gy) % 2 == 0 else DK_SQUARE
            pygame.draw.rect(screen, color, (tx + gx * max_cell, ty + gy * max_cell, max_cell, max_cell))

    # Draw path numbers (1-indexed)
    font_size = max(6, int(max_cell * 0.6))
    num_font = pygame.font.SysFont("arial", font_size)

    for path_idx, (gx, gy) in enumerate(path):
        if 0 <= gx < cols and 0 <= gy < rows:
            path_number = path_idx + 1
            num_surf = num_font.render(str(path_number), True, (0, 0, 0))
            cell_center_x = tx + gx * max_cell + max_cell // 2
            cell_center_y = ty + gy * max_cell + max_cell // 2
            num_rect = num_surf.get_rect(center=(cell_center_x, cell_center_y))
            screen.blit(num_surf, num_rect)

    # Border
    pygame.draw.rect(screen, GRID_COLOR, (tx - 1, ty - 1, tw + 2, th + 2), 1)


# --- main ---

def main():
    pygame.init()

    info = pygame.display.Info()
    screen_width, screen_height = info.current_w, info.current_h
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)

    pygame.display.set_caption("Capture the Flags v2")

    try:
        import ctypes
        _SW_MAXIMIZE = 3
        hwnd = pygame.display.get_wm_info()['window']
        ctypes.windll.user32.ShowWindow(hwnd, _SW_MAXIMIZE)
    except (KeyError, AttributeError, OSError, ImportError):
        pass

    clock_ticker = pygame.time.Clock()

    font = pygame.font.SysFont("arial", 18)
    font_large = pygame.font.SysFont("arial", 20)

    menu_items = [
        ("board", list(range(BOARD_MIN, BOARD_MAX + 1)), 3),
        ("piece", pk.PIECE_LIST[:], 0),
        ("path length", PATH_LENGTH_CHOICES[:], 0),
        ("flag density", FLAG_DENSITY_CHOICES[:], 0),
        ("flag order", FLAG_ORDER_CHOICES[:], 0),
        ("clock", [0] + list(range(60, (MAX_CLOCK_MINUTES + 1) * 60, 60)), 0),
    ]
    label_to_index = {label: idx for idx, (label, _, _) in enumerate(menu_items)}

    def get_selection(label):
        idx = label_to_index[label]
        _, values, cur = menu_items[idx]
        return values[cur]

    def cycle_menu(label, delta):
        idx = label_to_index[label]
        lbl, values, cur = menu_items[idx]
        menu_items[idx] = (lbl, values, (cur + delta) % len(values))

    # Board model / renderer (will be resized on start)
    board_model = BoardModel(BOARD_DEFAULT, BOARD_DEFAULT)
    board_renderer = BoardRenderer(board_model, 10, (0, 0))
    current_cell_size = 0

    # --- game state ---
    game_state = GameState.MENU
    player_pos = None
    visited: Set[Tuple[int, int]] = set()
    visited_moves: Dict[Tuple[int, int], int] = {}
    flags: List[Tuple[int, int]] = []
    path: List[Tuple[int, int]] = []
    flags_set: Set[Tuple[int, int]] = set()
    flags_index: Dict[Tuple[int, int], int] = {}   # pos -> 0-based index in flags list
    flags_reached: Set[Tuple[int, int]] = set()
    flags_reached_in_order: Set[Tuple[int, int]] = set()
    flags_reached_out_of_order: Set[Tuple[int, int]] = set()
    end_state: Optional[str] = None

    flag_images: Dict[str, Optional[pygame.Surface]] = {}

    clock_elapsed = 0
    clock_start_time = None
    paused_elapsed = 0.0

    legal_moves: List[Tuple[int, int]] = []
    hint_degrees: Dict[Tuple[int, int], int] = {}

    guide_mode_active = False
    track_mode_active = False
    hint_mode_active = False
    peek_mode_visible = False
    seed_mode_active = False
    puzzle_code = ""
    copy_button_clicked = False
    copy_button_timer = 0

    replay_states: List[Dict] = []
    replay_index = 0
    replay_mode_active = False

    last_puzzle_seed = None
    error_message = ""
    error_timer = 0

    widget_rects: Dict = {}
    arrows: Dict[Tuple[int, int], pygame.Surface] = {}
    menu_preview_cache = None  # (cache_key, flags_list) for MENU flag preview
    preview_pos: Optional[Tuple[int, int]] = None  # MENU preview piece position

    codec_input = TextInput(pygame.Rect(0, 0, 200, BTH), font, max_length=19)

    # ---------- helpers ----------

    def _capture_replay_state():
        replay_states.append({
            "pos": player_pos,
            "visited": visited.copy(),
            "flags_reached": flags_reached.copy(),
            "flags_reached_in_order": flags_reached_in_order.copy(),
            "flags_reached_out_of_order": flags_reached_out_of_order.copy(),
            "visited_moves": visited_moves.copy(),
        })

    def _restore_state(state):
        nonlocal player_pos, visited, visited_moves, flags_reached, legal_moves, hint_degrees
        nonlocal flags_reached_in_order, flags_reached_out_of_order
        player_pos = state["pos"]
        visited = state["visited"].copy()
        visited_moves = state["visited_moves"].copy()
        flags_reached = state["flags_reached"].copy()
        flags_reached_in_order = state.get("flags_reached_in_order", set()).copy()
        flags_reached_out_of_order = state.get("flags_reached_out_of_order", set()).copy()
        restore_cols = board_model.cols
        restore_rows = board_model.rows
        piece_name = get_selection("piece")
        legal_moves = get_legal_moves_for_board(piece_name, *player_pos, restore_cols, restore_rows, visited)
        if hint_mode_active:
            hint_degrees = calculate_hint_degrees(piece_name, player_pos, restore_cols, restore_rows, visited)
        else:
            hint_degrees = {}

    def start_game(use_seed=None):
        nonlocal game_state, player_pos, visited, visited_moves
        nonlocal flags, flags_set, flags_index, path
        nonlocal flags_reached, flags_reached_in_order, flags_reached_out_of_order
        nonlocal end_state
        nonlocal clock_elapsed, clock_start_time, paused_elapsed
        nonlocal legal_moves, hint_degrees, replay_states, replay_index, replay_mode_active
        nonlocal puzzle_code, last_puzzle_seed, error_message, error_timer
        nonlocal guide_mode_active, hint_mode_active, peek_mode_visible

        board_size = get_selection("board")
        piece_name = get_selection("piece")
        path_length = get_selection("path length")
        flag_density = get_selection("flag density")
        flag_order_val = get_selection("flag order")

        min_board = get_min_board_size(piece_name)
        if board_size < min_board:
            error_message = f"{piece_name} needs board >= {min_board}"
            error_timer = pygame.time.get_ticks() + 3000
            return

        if use_seed is not None:
            seed = use_seed
        elif seed_mode_active:
            code_text = codec_input.get_text()
            ok, params = validate_and_apply_codec(code_text, menu_items, label_to_index)
            if ok and params:
                seed = params["seed"]
                board_size = get_selection("board")
                path_length = get_selection("path length")
                flag_density = get_selection("flag density")
                flag_order_val = get_selection("flag order")
                piece_name = get_selection("piece")
            else:
                error_message = "Invalid share code"
                error_timer = pygame.time.get_ticks() + 3000
                return
        else:
            seed = random.randint(0, 2 ** 63 - 1)

        last_puzzle_seed = seed

        move_func = pk.get_move_func(piece_name)
        multiplier = PATH_LENGTH_MAP[path_length]
        min_length = max(board_size, int(board_size * multiplier))
        max_length = min(board_size * board_size, int(board_size * multiplier * 2))

        path, flags_list = generate_open_path_with_flags(
            board_size, min_length, max_length, move_func,
            max_attempts=500, time_budget=2.0,
            flag_density_choice=flag_density, seed=seed,
        )

        if not path or len(path) < 4:
            error_message = "Failed to generate puzzle – try different settings"
            error_timer = pygame.time.get_ticks() + 3000
            return

        start = path[0]
        flags_list = [f for f in flags_list if f != start]

        params_enc = {
            "board": board_size,
            "path_length": path_length,
            "flag_density": flag_density,
            "flag_order": flag_order_val,
        }
        try:
            puzzle_code = encode_params(params_enc, captureflags_schema, seed)
        except Exception:
            puzzle_code = ""

        # Update board model
        board_model.cols = board_size
        board_model.rows = board_size
        board_model.clear()

        flags = flags_list
        flags_set = set(flags)
        flags_index = {pos: i for i, pos in enumerate(flags)}
        flags_reached = set()
        flags_reached_in_order = set()
        flags_reached_out_of_order = set()

        player_pos = start
        visited = {start}
        visited_moves = {start: 0}
        end_state = None

        legal_moves = get_legal_moves_for_board(piece_name, *start, board_size, board_size, visited)
        hint_degrees = {}

        replay_states = [{
            "pos": start,
            "visited": visited.copy(),
            "flags_reached": flags_reached.copy(),
            "flags_reached_in_order": flags_reached_in_order.copy(),
            "flags_reached_out_of_order": flags_reached_out_of_order.copy(),
            "visited_moves": visited_moves.copy(),
        }]
        replay_index = 0
        replay_mode_active = False

        clock_start_time = None
        paused_elapsed = 0.0
        clock_elapsed = 0

        guide_mode_active = False
        hint_mode_active = False
        peek_mode_visible = False

        game_state = GameState.INGAME

    def make_move(target):
        nonlocal player_pos, visited, visited_moves, flags_reached
        nonlocal flags_reached_in_order, flags_reached_out_of_order
        nonlocal legal_moves, hint_degrees, end_state, game_state
        nonlocal clock_start_time, clock_elapsed, paused_elapsed

        if game_state != GameState.INGAME:
            return
        if target not in legal_moves:
            return

        if clock_start_time is None:
            clock_start_time = time.time()

        player_pos = target
        move_num = len(visited_moves)
        visited.add(target)
        visited_moves[target] = move_num

        if target in flags_set and target not in flags_reached:
            flag_order_mode = get_selection("flag order")
            if flag_order_mode == "next":
                # Determine next target (lowest cardinal index not yet reached) before updating
                next_target_idx = next(
                    (i for i in range(len(flags)) if flags[i] not in flags_reached),
                    -1
                )
                flags_reached.add(target)
                if flags_index[target] == next_target_idx:
                    flags_reached_in_order.add(target)
                else:
                    flags_reached_out_of_order.add(target)
            else:
                ordinal = len(flags_reached) + 1         # which flag reached (1-indexed)
                cardinal = flags_index[target] + 1       # flag's assigned number (1-indexed)
                flags_reached.add(target)
                if ordinal == cardinal:
                    flags_reached_in_order.add(target)
                else:
                    flags_reached_out_of_order.add(target)

        piece_name = get_selection("piece")
        hint_cols, hint_rows = board_model.cols, board_model.rows
        legal_moves = get_legal_moves_for_board(piece_name, *player_pos, hint_cols, hint_rows, visited)

        if hint_mode_active:
            hint_degrees = calculate_hint_degrees(piece_name, player_pos, hint_cols, hint_rows, visited)
        else:
            hint_degrees = {}

        _capture_replay_state()

        # Check endgame
        end_clock_sel = get_selection("clock")
        if len(flags_reached) == len(flags):
            end_state = "all_flags_reached"
            game_state = GameState.ENDGAME
        elif not legal_moves:
            end_state = "no_moves"
            game_state = GameState.ENDGAME
        elif clock_has_expired(end_clock_sel, clock_elapsed):
            end_state = "timeout"
            game_state = GameState.ENDGAME

    def undo_move():
        nonlocal player_pos, visited, visited_moves, flags_reached
        nonlocal legal_moves, hint_degrees, replay_states

        if game_state != GameState.INGAME:
            return
        if len(replay_states) <= 1:
            return
        replay_states.pop()
        _restore_state(replay_states[-1])

    def resign_game():
        nonlocal end_state, game_state
        if game_state != GameState.INGAME:
            return
        end_state = "resignation"
        game_state = GameState.ENDGAME

    def toggle_guide_mode():
        nonlocal guide_mode_active, hint_mode_active
        guide_mode_active = not guide_mode_active
        if guide_mode_active:
            hint_mode_active = False
            hint_degrees.clear()

    def toggle_track_mode():
        nonlocal track_mode_active
        track_mode_active = not track_mode_active

    def toggle_hint_mode():
        nonlocal hint_mode_active, guide_mode_active, hint_degrees
        hint_mode_active = not hint_mode_active
        if hint_mode_active:
            guide_mode_active = False
            if player_pos:
                piece_name = get_selection("piece")
                hint_degrees = calculate_hint_degrees(
                    piece_name, player_pos, board_model.cols, board_model.rows, visited)
        else:
            hint_degrees = {}

    def toggle_peek():
        nonlocal peek_mode_visible
        peek_mode_visible = not peek_mode_visible

    def toggle_codec_input():
        nonlocal seed_mode_active
        seed_mode_active = not seed_mode_active

    def toggle_replay_mode():
        nonlocal replay_mode_active, replay_index
        replay_mode_active = not replay_mode_active
        if replay_mode_active:
            replay_index = 0
        else:
            # Restore final state
            if replay_states:
                _restore_state(replay_states[-1])

    def navigate_replay(delta):
        nonlocal replay_index
        if not replay_mode_active or not replay_states:
            return
        replay_index = clamp(replay_index + delta, 0, len(replay_states) - 1)
        _restore_state(replay_states[replay_index])

    def retry_game():
        if last_puzzle_seed is not None:
            start_game(use_seed=last_puzzle_seed)

    def new_game():
        nonlocal game_state, end_state, peek_mode_visible
        nonlocal seed_mode_active, replay_mode_active, puzzle_code, preview_pos
        nonlocal path
        end_state = None
        peek_mode_visible = False
        seed_mode_active = False
        replay_mode_active = False
        puzzle_code = ""
        preview_pos = None
        path = []
        game_state = GameState.MENU

    def copy_code_to_clipboard():
        nonlocal copy_button_clicked, copy_button_timer
        if not puzzle_code:
            return
        try:
            import pyperclip
            pyperclip.copy(puzzle_code)
        except Exception:
            try:
                import subprocess
                subprocess.run(["xclip", "-selection", "clipboard"],
                               input=puzzle_code.encode(), check=False)
            except Exception:
                pass
        copy_button_clicked = True
        copy_button_timer = pygame.time.get_ticks() + 2000

    def quit_game():
        pygame.quit()
        sys.exit()

    # ---------- buttons ----------

    buttons = {
        "start": Button(pygame.Rect(0, 0, 0, 0), "start", (255, 255, 255),
                        (92, 192, 92), font, start_game),
        "enter_code": Button(pygame.Rect(0, 0, 0, 0), "enter share code", (255, 255, 255),
                             (224, 0, 96), font, toggle_codec_input),
        "copy_code": Button(pygame.Rect(0, 0, 0, 0), "copy share code", (255, 255, 255),
                            (224, 0, 96), font, copy_code_to_clipboard),
        "guide_mode": Button(pygame.Rect(0, 0, 0, 0), "show move guide", (255, 255, 255),
                             (128, 64, 255), font, toggle_guide_mode),
        "track_mode": Button(pygame.Rect(0, 0, 0, 0), "show move numbers", (255, 255, 255),
                             (255, 92, 128), font, toggle_track_mode),
        "hint_mode": Button(pygame.Rect(0, 0, 0, 0), "show hints", (255, 255, 255),
                            (255, 128, 96), font, toggle_hint_mode),
        "undo_mode": Button(pygame.Rect(0, 0, 0, 0), "undo last move", (255, 255, 255),
                            (64, 128, 255), font, undo_move),
        "resign": Button(pygame.Rect(0, 0, 0, 0), "resign", (255, 255, 255),
                         DK_VISITED, font, resign_game),
        "retry": Button(pygame.Rect(0, 0, 0, 0), "retry", (255, 255, 255),
                        (92, 192, 92), font, retry_game),
        "replay_mode": Button(pygame.Rect(0, 0, 0, 0), "start replay", (255, 255, 255),
                              (64, 128, 255), font, toggle_replay_mode),
        "replay_prev": Button(pygame.Rect(0, 0, 0, 0), "-", (255, 255, 240),
                              (64, 128, 255), font, lambda: navigate_replay(-1)),
        "replay_next": Button(pygame.Rect(0, 0, 0, 0), "+", (255, 255, 240),
                              (64, 128, 255), font, lambda: navigate_replay(1)),
        "peek_mode": Button(pygame.Rect(0, 0, 0, 0), "peek", (255, 255, 240),
                            LT_SQUARE, font, toggle_peek),
        "new_game": Button(pygame.Rect(0, 0, 0, 0), "new game", (255, 255, 255),
                           (32, 128, 96), font, new_game),
        "exit": Button(pygame.Rect(0, 0, 0, 0), "exit", (255, 255, 255),
                       (220, 40, 40), font, quit_game),
    }

    # Initialize board size in menu items
    board_vals = menu_items[label_to_index["board"]][1]
    for i, v in enumerate(board_vals):
        if v == BOARD_DEFAULT:
            menu_items[label_to_index["board"]] = ("board", board_vals, i)
            break

    # ---------- load pieces ----------
    try:
        pk.load_images(pieces_dir, 36)
    except Exception as e:
        print(f"Warning: could not load piece images: {e}")

    # ========== MAIN LOOP ==========
    while True:
        clock_ticker.tick(FPS)
        dt = clock_ticker.get_time()
        codec_input.update(dt)

        # Copy button feedback timeout
        if copy_button_clicked and pygame.time.get_ticks() > copy_button_timer:
            copy_button_clicked = False

        # Update clock
        if game_state == GameState.INGAME and clock_start_time is not None:
            clock_elapsed = int(paused_elapsed + (time.time() - clock_start_time))

        # Check timeout while in game
        if game_state == GameState.INGAME:
            clock_sel = get_selection("clock")
            if clock_has_expired(clock_sel, clock_elapsed):
                end_state = "timeout"
                game_state = GameState.ENDGAME

        win_width, win_height = screen.get_size()
        screen.fill(BACK_COLOR)

        # --- layout ---
        margin = UI_SPACE
        panel_width = UI_SPACE * 18
        msg_left = margin
        msg_top = margin
        msg_bottom = win_height - margin
        msg_height = msg_bottom - msg_top
        msg_right = msg_left + panel_width

        right_msg_left = win_width - panel_width - margin

        left_panel_rect = pygame.Rect(msg_left, msg_top, panel_width, msg_height)
        right_panel_rect = pygame.Rect(right_msg_left, msg_top, panel_width, msg_height)

        left_panel = UIPanel(left_panel_rect, gap=2)
        right_panel = UIPanel(right_panel_rect, gap=2)

        left_panel.draw_panel(screen, "MENU_PANEL", LT_SQUARE, GRID_COLOR)
        left_panel.draw_panel(screen, "BUTTON_PANEL", LT_SQUARE, GRID_COLOR)
        right_panel.draw_panel(screen, "PIECE_PANEL", LT_SQUARE, GRID_COLOR)
        right_panel.draw_panel(screen, "STATS_PANEL", LT_SQUARE, GRID_COLOR)

        # --- board layout ---
        area_left = msg_right + margin
        area_top = margin
        area_right = right_msg_left - margin
        area_bottom = win_height - margin
        area_width = area_right - area_left
        area_height = area_bottom - area_top

        cols = board_model.cols
        rows = board_model.rows

        new_cell_size = 0
        if cols > 0 and rows > 0:
            cell_w = area_width // cols
            cell_h = area_height // rows
            new_cell_size = max(12, min(cell_w, cell_h))

        if new_cell_size != current_cell_size and new_cell_size > 0:
            current_cell_size = new_cell_size
            board_renderer.cell_size = new_cell_size
            try:
                pk.load_images(pieces_dir, max(12, new_cell_size - 4))
                arrow_names = {
                    (0, -1): "arrow_n.png", (1, -1): "arrow_ne.png",
                    (1, 0): "arrow_e.png", (1, 1): "arrow_se.png",
                    (0, 1): "arrow_s.png", (-1, 1): "arrow_sw.png",
                    (-1, 0): "arrow_w.png", (-1, -1): "arrow_nw.png",
                }
                arrows.clear()
                arrow_size = max(8, current_cell_size // 2)
                diag_size = max(6, int(arrow_size * 0.75))
                for direction, fname in arrow_names.items():
                    path = os.path.join(arrows_dir, fname)
                    try:
                        img = pygame.image.load(path).convert_alpha()
                        dx, dy = direction
                        sz = diag_size if (dx != 0 and dy != 0) else arrow_size
                        arrows[direction] = pygame.transform.smoothscale(img, (sz, sz))
                    except Exception:
                        pass
            except Exception as e:
                print(f"Warning: image reload error: {e}")

            # Load flag images for "only" mode
            flag_img_size = max(8, int(new_cell_size * 0.68))
            _flag_img_names = {
                "black": "flag_black.png",
                "blue": "flag_blue.png",
                "green": "flag_green.png",
                "ivory": "flag_ivory.png", #
                "orange": "flag_orange.png",
                "purple": "flag_purple.png",
                "red": "flag_red.png",
                "tan": "flag_tan.png",
                "white": "flag_white.png",
                "yellow": "flag_yellow.png",
            }
            flag_images.clear()
            for key, fname in _flag_img_names.items():
                fpath = os.path.join(flags_dir, fname)
                try:
                    fimg = pygame.image.load(fpath).convert_alpha()
                    flag_images[key] = pygame.transform.smoothscale(fimg, (flag_img_size, flag_img_size))
                except Exception:
                    flag_images[key] = None

        board_pixel_w = cols * current_cell_size
        board_pixel_h = rows * current_cell_size
        origin_x = area_left + (area_width - board_pixel_w) // 2
        origin_y = area_top + (area_height - board_pixel_h) // 2
        board_renderer.origin = (origin_x, origin_y)

        cs = current_cell_size

        # --- compute display state ---
        if game_state == GameState.ENDGAME and replay_mode_active and replay_states:
            disp = replay_states[replay_index]
            disp_pos = disp["pos"]
            disp_visited = disp["visited"]
            disp_visited_moves = disp["visited_moves"]
            disp_flags_reached = disp["flags_reached"]
            disp_flags_reached_in_order = disp.get("flags_reached_in_order", set())
            disp_flags_reached_out_of_order = disp.get("flags_reached_out_of_order", set())
        else:
            disp_pos = player_pos
            disp_visited = visited
            disp_visited_moves = visited_moves
            disp_flags_reached = flags_reached
            disp_flags_reached_in_order = flags_reached_in_order
            disp_flags_reached_out_of_order = flags_reached_out_of_order

        # --- compute MENU preview piece pos ---
        if game_state == GameState.MENU:
            prev_board = get_selection("board")
            prev_piece = get_selection("piece")
            if board_model.cols != prev_board or board_model.rows != prev_board:
                board_model.cols = prev_board
                board_model.rows = prev_board
                board_model.clear()
                preview_pos = None
            if preview_pos is None or not (0 <= preview_pos[0] < prev_board and 0 <= preview_pos[1] < prev_board):
                preview_pos = (prev_board // 2, prev_board // 2)
            prev_cx, prev_cy = preview_pos
            prev_legal = get_legal_moves_for_board(
                prev_piece, prev_cx, prev_cy, prev_board, prev_board, set()
            )
        else:
            prev_cx = prev_cy = 0
            prev_legal = []

        # ---- draw board background ----
        board_renderer.draw_background(screen)

        fo_val = get_selection("flag order")

        if cs > 0:
            # Draw flag squares
            if game_state == GameState.MENU:
                # Realistic flag preview using cached path generation
                demo_b = get_selection("board")
                demo_piece = get_selection("piece")
                demo_pl = get_selection("path length")
                demo_fd = get_selection("flag density")
                cache_key = (demo_b, demo_piece, demo_pl, demo_fd)
                if menu_preview_cache is None or menu_preview_cache[0] != cache_key:
                    demo_move_func = pk.get_move_func(demo_piece)
                    demo_mult = PATH_LENGTH_MAP[demo_pl]
                    demo_min = max(demo_b, int(demo_b * demo_mult))
                    demo_max = min(demo_b * demo_b, int(demo_b * demo_mult * 2))
                    _, preview_flags = generate_open_path_with_flags(
                        demo_b, demo_min, demo_max, demo_move_func,
                        max_attempts=100, time_budget=0.1,
                        flag_density_choice=demo_fd, seed=42,
                    )
                    menu_preview_cache = (cache_key, preview_flags or [])
                demo_flags = menu_preview_cache[1]
                # Both modes: flag images (ivory/tan), no purple squares, no cardinal numbers
                for (fx, fy) in demo_flags:
                    if 0 <= fx < demo_b and 0 <= fy < demo_b:
                        px, py = board_renderer.to_pixel(fx, fy)
                        parity = (fx + fy) % 2
                        img_key = "tan" if parity == 0 else "ivory"
                        fimg = flag_images.get(img_key)
                        if fimg:
                            screen.blit(fimg, fimg.get_rect(center=(px + cs // 2, py + cs // 2)))
                        else:
                            fb_color = FLAG_IMG_FALLBACK_COLORS.get(img_key, (128, 128, 128))
                            fb_sz = max(6, int(cs * 0.68))
                            pygame.draw.rect(screen, fb_color,
                                (px + (cs - fb_sz) // 2, py + (cs - fb_sz) // 2, fb_sz, fb_sz))

            elif game_state in (GameState.INGAME, GameState.ENDGAME):
                pass  # flag images drawn in dedicated pass below

            # Draw visited squares (both modes: normal visited colors, skip flag squares)
            if game_state in (GameState.INGAME, GameState.ENDGAME):
                nf_move_vis = pygame.font.SysFont("arial", max(8, cs // 3))
                for (vx, vy) in disp_visited:
                    if (vx, vy) == disp_pos:
                        continue
                    if (vx, vy) in flags_set:
                        # In "next" mode, draw visited background for flags reached out of order
                        if fo_val != "next" or (vx, vy) not in disp_flags_reached_out_of_order:
                            continue  # flag squares handled in dedicated flag pass below
                    px, py = board_renderer.to_pixel(vx, vy)
                    parity = (vx + vy) % 2
                    vcolor = LT_VISITED if parity == 0 else DK_VISITED
                    pygame.draw.rect(screen, vcolor, (px + 3, py + 3, cs - 4, cs - 4))
                    # Track mode: move number on non-flag visited squares
                    if track_mode_active and (vx, vy) in disp_visited_moves:
                        luma = vcolor[0] * 0.299 + vcolor[1] * 0.587 + vcolor[2] * 0.114
                        num_color = (0, 0, 0) if luma > 128 else (255, 255, 255)
                        ns = nf_move_vis.render(str(disp_visited_moves[(vx, vy)] + 1), True, num_color)
                        screen.blit(ns, ns.get_rect(center=(px + cs // 2, py + cs // 2)))

            # Draw flag images for all flag positions ("any", "only", and "next" modes)
            if cs > 0 and game_state in (GameState.INGAME, GameState.ENDGAME):
                nf_card = pygame.font.SysFont("arial", max(7, cs // 4))
                nf_move = pygame.font.SysFont("arial", max(8, cs // 3))
                if fo_val == "next":
                    # Wrap-around: find the lowest cardinal index not yet reached.
                    # Default -1 (all reached) never matches a valid flag_idx.
                    next_target_idx = next(
                        (i for i in range(len(flags)) if flags[i] not in disp_flags_reached),
                        -1
                    )
                else:
                    next_target_idx = len(disp_flags_reached)
                for flag_idx, flag_pos in enumerate(flags):
                    fx, fy = flag_pos
                    px, py = board_renderer.to_pixel(fx, fy)

                    # Choose image key based on mode and reach status
                    if fo_val == "only":
                        is_next_flag = (flag_idx == next_target_idx)
                        if flag_pos in disp_flags_reached_in_order:
                            img_key = "blue"
                        elif flag_pos in disp_flags_reached_out_of_order:
                            img_key = "red"
                        elif is_next_flag:
                            img_key = "green"
                        else:
                            img_key = "tan" if (fx + fy) % 2 == 0 else "ivory"
                    elif fo_val == "next":
                        if flag_pos in disp_flags_reached_in_order:
                            img_key = "blue"   # reached when it was the next target
                        elif flag_pos in disp_flags_reached_out_of_order:
                            img_key = "red"    # reached when it was not the next target
                        elif flag_idx == next_target_idx:
                            img_key = "green"  # current next target
                        else:
                            # Future flags beyond current target: invisible
                            continue
                    else:
                        # "any" mode: purple when reached, ivory/tan when unreached
                        if flag_pos in disp_flags_reached:
                            img_key = "purple"
                        else:
                            img_key = "tan" if (fx + fy) % 2 == 0 else "ivory"

                    fimg = flag_images.get(img_key)
                    if fimg:
                        screen.blit(fimg, fimg.get_rect(center=(px + cs // 2, py + cs // 2)))
                    else:
                        fb_color = FLAG_IMG_FALLBACK_COLORS.get(img_key, (128, 128, 128))
                        fb_sz = max(6, int(cs * 0.68))
                        pygame.draw.rect(screen, fb_color,
                            (px + (cs - fb_sz) // 2, py + (cs - fb_sz) // 2, fb_sz, fb_sz))

                    # Track mode: move number on top of flag image
                    if track_mode_active and flag_pos in disp_visited_moves:
                        ns = nf_move.render(str(disp_visited_moves[flag_pos] + 1), True, (0, 0, 0))
                        screen.blit(ns, ns.get_rect(center=(px + cs // 2, py + cs // 2)))

                    # "only" mode: cardinal number in upper right corner
                    if fo_val == "only":
                        card_surf = nf_card.render(str(flag_idx + 1), True, (0, 0, 0))
                        screen.blit(card_surf, (px + cs - card_surf.get_width() - 2, py + 2))

            # Draw guide arrows
            if guide_mode_active and arrows:
                if game_state == GameState.MENU and prev_legal:
                    for (mx, my) in prev_legal:
                        dx = int(clamp(mx - prev_cx, -1, 1))
                        dy = int(clamp(my - prev_cy, -1, 1))
                        arrow_surf = arrows.get((dx, dy))
                        if arrow_surf:
                            gpx, gpy = board_renderer.to_pixel(mx, my)
                            ar = arrow_surf.get_rect(center=(gpx + cs // 2, gpy + cs // 2))
                            screen.blit(arrow_surf, ar)
                elif disp_pos and game_state in (GameState.INGAME, GameState.ENDGAME):
                    moves_for_arrows = legal_moves if not replay_mode_active else \
                        get_legal_moves_for_board(get_selection("piece"), *disp_pos,
                                                 board_model.cols, board_model.rows, disp_visited)
                    for (mx, my) in moves_for_arrows:
                        dx = int(clamp(mx - disp_pos[0], -1, 1))
                        dy = int(clamp(my - disp_pos[1], -1, 1))
                        arrow_surf = arrows.get((dx, dy))
                        if arrow_surf:
                            gpx, gpy = board_renderer.to_pixel(mx, my)
                            ar = arrow_surf.get_rect(center=(gpx + cs // 2, gpy + cs // 2))
                            screen.blit(arrow_surf, ar)

            # Draw hint degrees
            if hint_mode_active and hint_degrees:
                hf = pygame.font.SysFont("arial", max(10, cs // 3))
                for (hx, hy), degree in hint_degrees.items():
                    hpx, hpy = board_renderer.to_pixel(hx, hy)
                    bg = LT_SQUARE if (hx + hy) % 2 == 0 else DK_SQUARE
                    luma = bg[0] * 0.299 + bg[1] * 0.587 + bg[2] * 0.114
                    hc = (0, 0, 0) if luma > 128 else (255, 255, 255)
                    hs = hf.render(str(degree), True, hc)
                    screen.blit(hs, hs.get_rect(center=(hpx + cs // 2, hpy + cs // 2)))

            # Draw player piece
            if disp_pos and cs > 0:
                ppx, ppy = board_renderer.to_pixel(*disp_pos)
                piece_rect = pygame.Rect(ppx + 1, ppy + 1, cs - 2, cs - 2)
                try:
                    pk.draw_piece(screen, piece_rect, get_selection("piece"))
                except Exception:
                    pygame.draw.ellipse(screen, (0, 0, 0), piece_rect)

            elif game_state == GameState.MENU and cs > 0:
                ppx, ppy = board_renderer.to_pixel(prev_cx, prev_cy)
                piece_rect = pygame.Rect(ppx + 1, ppy + 1, cs - 2, cs - 2)
                try:
                    pk.draw_piece(screen, piece_rect, get_selection("piece"))
                except Exception:
                    pygame.draw.ellipse(screen, (0, 0, 0), piece_rect)

        board_renderer.draw_grid_lines(screen)

        # ---- error message overlay ----
        if error_message and pygame.time.get_ticks() < error_timer:
            ef = pygame.font.SysFont("arial", 22)
            es = ef.render(error_message, True, (200, 0, 0))
            ex = area_left + (area_width - es.get_width()) // 2
            ey = area_top + area_height // 2 - es.get_height() // 2
            pygame.draw.rect(screen, (255, 240, 240),
                             (ex - 8, ey - 6, es.get_width() + 16, es.get_height() + 12))
            screen.blit(es, (ex, ey))
        elif error_message and pygame.time.get_ticks() >= error_timer:
            error_message = ""

        # ===================== UI PANELS =====================

        widget_rects.clear()
        btn_w = UI_SPACE
        line_height = font.get_linesize() + UI_SPACE

        # --- MENU_PANEL: selector rows ---
        menu_bounds = left_panel.get_bounds("MENU_PANEL")
        text_x = menu_bounds['left'] + UI_SPACE

        menu_panel_items = [(i, (lbl, vals, cur)) for i, (lbl, vals, cur) in enumerate(menu_items) if lbl != "piece"]

        max_lbl_w = max(font.render(lbl + ":", True, (0, 0, 0)).get_width()
                        for lbl, _, _ in menu_items if lbl != "piece")
        minus_x = text_x + max_lbl_w + UI_SPACE
        plus_x = menu_bounds['right'] - UI_SPACE * 4

        for list_idx, (item_idx, (label, values, cur_idx)) in enumerate(menu_panel_items):
            panel_y = left_panel.get_line_y("MENU_PANEL", list_idx, line_height)
            row_cy = panel_y + btn_w // 2

            lbl_surf = font.render(f"{label}:", True, (0, 0, 0))
            screen.blit(lbl_surf, lbl_surf.get_rect(midleft=(text_x, row_cy)))

            # Show selected value
            val = values[cur_idx]
            if label == "clock":
                sel_text = display_for_selection(val)
            else:
                sel_text = str(val)
            sel_surf = font.render(sel_text, True, (0, 0, 0))
            sel_cx = (minus_x + btn_w + plus_x + btn_w) / 2
            screen.blit(sel_surf, sel_surf.get_rect(center=(sel_cx, row_cy)))

            if game_state == GameState.MENU:
                mr = pygame.Rect(minus_x, panel_y, int(btn_w * 1.5), int(btn_w * 1.5))
                pygame.draw.rect(screen, DK_SQUARE, mr)
                lt = font.render("<", True, (0, 160, 0))
                screen.blit(lt, lt.get_rect(center=mr.center))
                widget_rects[("minus", item_idx)] = mr

                pr = pygame.Rect(plus_x, panel_y, int(btn_w * 1.5), int(btn_w * 1.5))
                pygame.draw.rect(screen, DK_SQUARE, pr)
                gt = font.render(">", True, (220, 0, 0))
                screen.blit(gt, gt.get_rect(center=pr.center))
                widget_rects[("plus", item_idx)] = pr

        # Codec entry / display
        codec_line = len(menu_panel_items) + 3

        buttons["enter_code"].active = game_state == GameState.MENU
        if seed_mode_active:
            buttons["enter_code"].bg_color = (224, 64, 128)
            buttons["enter_code"].text = "cancel code input"
        else:
            buttons["enter_code"].bg_color = (224, 0, 96)
            buttons["enter_code"].text = "enter share code"
        buttons["enter_code"].rect = left_panel.get_widget_rect("MENU_PANEL", codec_line, BTW, BTH)
        buttons["enter_code"].draw(screen)

        if game_state == GameState.MENU and seed_mode_active:
            input_y = left_panel.get_line_y("MENU_PANEL", codec_line, line_height)
            input_x = menu_bounds['left'] + (menu_bounds['width'] - BTW) // 2
            codec_input.rect = pygame.Rect(input_x, input_y, BTW, BTH)
            codec_input.draw(screen)

        # Share code display + copy button
        if puzzle_code and game_state in (GameState.INGAME, GameState.ENDGAME):
            code_line = codec_line
            code_y = left_panel.get_line_y("MENU_PANEL", code_line, line_height)
            code_surf = font.render(puzzle_code, True, (0, 0, 0))
            screen.blit(code_surf, code_surf.get_rect(
                center=(menu_bounds['center_x'], code_y + line_height // 2)))

            buttons["copy_code"].active = True
            if copy_button_clicked:
                buttons["copy_code"].bg_color = (224, 64, 128)
                buttons["copy_code"].text = "code copied!"
            else:
                buttons["copy_code"].bg_color = (224, 0, 96)
                buttons["copy_code"].text = "copy share code"
            buttons["copy_code"].rect = left_panel.get_widget_rect("MENU_PANEL", code_line, BTW, BTH)
            buttons["copy_code"].draw(screen)
        else:
            buttons["copy_code"].active = False

        # --- BUTTON_PANEL ---
        button_bounds = left_panel.get_bounds("BUTTON_PANEL")

        # start button
        is_playable = (get_selection("board") >= get_min_board_size(get_selection("piece")))
        if seed_mode_active:
            # Only check length here; full validation happens in start_game()
            code_valid = len(codec_input.get_text()) == 16
            buttons["start"].active = game_state == GameState.MENU and code_valid
        else:
            buttons["start"].active = game_state == GameState.MENU and is_playable
        buttons["start"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        buttons["start"].draw(screen)


        # hint mode button (INGAME only)
        buttons["hint_mode"].active = game_state == GameState.INGAME and not guide_mode_active
        buttons["hint_mode"].text = "hide hints" if hint_mode_active else "show hints"
        buttons["hint_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        buttons["hint_mode"].draw(screen)

        # guide mode button
        buttons["guide_mode"].active = (game_state in (GameState.MENU, GameState.INGAME, GameState.ENDGAME)
                                        and not hint_mode_active)
        buttons["guide_mode"].text = "hide move guide" if guide_mode_active else "show move guide"
        buttons["guide_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 2, BTW, BTH)
        buttons["guide_mode"].draw(screen)

        # track mode button
        buttons["track_mode"].active = game_state in (GameState.MENU, GameState.INGAME, GameState.ENDGAME)
        buttons["track_mode"].text = "hide move numbers" if track_mode_active else "show move numbers"
        buttons["track_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 4, BTW, BTH)
        buttons["track_mode"].draw(screen)

        # undo button
        can_undo = game_state == GameState.INGAME and len(replay_states) > 1
        buttons["undo_mode"].active = can_undo
        buttons["undo_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 6, BTW, BTH)
        buttons["undo_mode"].draw(screen)

        # resign button
        buttons["resign"].active = game_state == GameState.INGAME
        buttons["resign"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 8, BTW, BTH)
        buttons["resign"].draw(screen)

        # retry button (ENDGAME only)
        buttons["retry"].active = game_state == GameState.ENDGAME and last_puzzle_seed is not None
        buttons["retry"].rect = left_panel.get_widget_rect("MENU_PANEL", 6, BTW, BTH)
        buttons["retry"].draw(screen)

        # replay mode toggle (ENDGAME only)
        buttons["replay_mode"].active = game_state == GameState.ENDGAME
        buttons["replay_mode"].text = "end replay" if replay_mode_active else "start replay"
        buttons["replay_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 6, BTW, BTH)
        buttons["replay_mode"].draw(screen)

        # replay navigation
        buttons["replay_prev"].active = False
        buttons["replay_next"].active = False
        if replay_mode_active and replay_states:
            rm_rect = buttons["replay_mode"].rect
            nav_w = BTW // 4
            if replay_index > 0:
                buttons["replay_prev"].active = True
                buttons["replay_prev"].rect = pygame.Rect(
                    rm_rect.left - nav_w - 4, rm_rect.top, nav_w, BTH)
                buttons["replay_prev"].draw(screen)
            if replay_index < len(replay_states) - 1:
                buttons["replay_next"].active = True
                buttons["replay_next"].rect = pygame.Rect(
                    rm_rect.right + 4, rm_rect.top, nav_w, BTH)
                buttons["replay_next"].draw(screen)

        # new game button (ENDGAME)
        buttons["new_game"].active = game_state == GameState.ENDGAME
        buttons["new_game"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 8, BTW, BTH)
        buttons["new_game"].draw(screen)

        # peek button (lower part of button panel)
        buttons["peek_mode"].active = game_state in (GameState.INGAME, GameState.ENDGAME) and bool(flags)
        buttons["peek_mode"].text = "hide" if peek_mode_visible else "peek"
        buttons["peek_mode"].rect = pygame.Rect(
            msg_left + UI_SPACE * 2, msg_bottom - UI_SPACE * 3, BTW // 2, BTH)
        buttons["peek_mode"].bg_color = LT_SQUARE
        buttons["peek_mode"].text_color = (255, 255, 240)
        buttons["peek_mode"].draw(screen)

        # exit button
        buttons["exit"].rect = pygame.Rect(
            msg_right - UI_SPACE * 5, msg_bottom - int(UI_SPACE * 2), BTW // 3, int(BTH * 0.75))
        buttons["exit"].draw(screen)

        # peek thumbnail
        draw_peek_flags_thumbnail(
            screen, board_model.cols, board_model.rows,
            path, flags, peek_mode_visible,
            left_panel, line_height,
        )

        # --- PIECE_PANEL (upper right) ---
        piece_bounds = right_panel.get_bounds("PIECE_PANEL")
        right_tx = piece_bounds['left'] + UI_SPACE

        piece_idx = label_to_index["piece"]
        _, piece_values, piece_cur = menu_items[piece_idx]
        piece_name_cur = piece_values[piece_cur]

        # Piece name row
        p_line_y = right_panel.get_line_y("PIECE_PANEL", 0, line_height)
        p_row_cy = p_line_y + btn_w // 2
        lbl_s = font.render("piece:", True, (0, 0, 0))
        #screen.blit(lbl_s, lbl_s.get_rect(midleft=(right_tx, p_row_cy)))

        p_minus_x = lbl_s.get_rect(midleft=(right_tx, p_row_cy)).right + UI_SPACE
        p_plus_x = piece_bounds['right'] - UI_SPACE * 4

        sel_s = font_large.render(piece_name_cur, True, (0, 0, 0))
        sel_cx = piece_bounds['center_x']
        screen.blit(sel_s, sel_s.get_rect(center=(sel_cx, p_row_cy + 8)))

        if game_state == GameState.MENU:
            pm_r = pygame.Rect(p_minus_x - btn_w, p_line_y, int(btn_w * 1.5), int(btn_w * 1.5))
            pygame.draw.rect(screen, DK_SQUARE, pm_r)
            pm_s = font.render("<", True, (0, 160, 0))
            screen.blit(pm_s, pm_s.get_rect(center=pm_r.center))
            widget_rects[("minus", piece_idx)] = pm_r

            pp_r = pygame.Rect(p_plus_x - btn_w, p_line_y, int(btn_w * 1.5), int(btn_w * 1.5))
            pygame.draw.rect(screen, DK_SQUARE, pp_r)
            pp_s = font.render(">", True, (220, 0, 0))
            screen.blit(pp_s, pp_s.get_rect(center=pp_r.center))
            widget_rects[("plus", piece_idx)] = pp_r

        # Move set text
        move_text = pk.get_piece_move_sets_text(piece_name_cur)
        info_y = p_line_y + sel_s.get_height() + line_height
        if move_text:
            mt_s = font.render(move_text, True, (80, 80, 80))
            screen.blit(mt_s, mt_s.get_rect(centerx=sel_cx, top=info_y))
            info_y += font.get_linesize() + UI_SPACE

        if game_state == GameState.MENU and not is_playable and not seed_mode_active:
            min_b = get_min_board_size(get_selection("piece"))
            warn_surf = font.render(f"board must be at least {min_b} x {min_b}", True, (200, 0, 0))
            warn_y = piece_bounds['top'] + 4 * line_height
            screen.blit(warn_surf, warn_surf.get_rect(centerx=piece_bounds['center_x'], top=warn_y))






        # --- STATS_PANEL (lower right) ---
        stats_bounds = right_panel.get_bounds("STATS_PANEL")

        s_line = 0

        # Clock
        clock_sel = get_selection("clock")
        if game_state == GameState.MENU:
            clock_disp = display_for_selection(clock_sel)
        else:
            rem = remaining_for(clock_sel, clock_elapsed)
            if rem is not None:
                clock_disp = format_clock_seconds(rem)
                clock_color = (200, 0, 0) if rem < 30 else (0, 0, 0)
            else:
                clock_disp = format_clock_seconds(clock_elapsed)
                clock_color = (0, 0, 0)
            clock_label_s = font.render("time: " + clock_disp, True,
                                        clock_color if game_state != GameState.MENU else (0, 0, 0))
            clock_y = right_panel.get_line_y("STATS_PANEL", s_line, line_height)
            screen.blit(clock_label_s, clock_label_s.get_rect(
                centerx=stats_bounds['center_x'], top=clock_y))
            s_line += 1

        if game_state in (GameState.INGAME, GameState.ENDGAME):
            # Move count
            move_count = max(disp_visited_moves.values(), default=0)
            moves_label = "move" if move_count == 1 else "moves"
            mc_s = font.render(f"{move_count} {moves_label}", True, (0, 0, 0))
            mc_y = right_panel.get_line_y("STATS_PANEL", s_line, line_height)
            screen.blit(mc_s, mc_s.get_rect(centerx=stats_bounds['center_x'], top=mc_y))
            s_line += 1

            # Flags captured
            n_flags = len(flags)
            n_reached = len(disp_flags_reached)
            fl_label = "flag" if n_flags == 1 else "flags"
            fl_text = f"{n_reached} of {n_flags} {fl_label}"
            fl_s = font.render(fl_text, True, (0, 0, 0))
            fl_y = right_panel.get_line_y("STATS_PANEL", s_line, line_height)
            screen.blit(fl_s, fl_s.get_rect(centerx=stats_bounds['center_x'], top=fl_y))
            s_line += 1

            # Flag order setting display
            if fo_val == "only":
                n_in_order = len(disp_flags_reached_in_order)
                n_out_of_order = len(disp_flags_reached_out_of_order)
                in_s = font.render(f"flags in order: {n_in_order}", True, (0, 0, 255))
                in_y = right_panel.get_line_y("STATS_PANEL", s_line, line_height)
                screen.blit(in_s, in_s.get_rect(centerx=stats_bounds['center_x'], top=in_y))
                s_line += 1
                out_s = font.render(f"flags out of order: {n_out_of_order}", True, (255, 0, 0))
                out_y = right_panel.get_line_y("STATS_PANEL", s_line, line_height)
                screen.blit(out_s, out_s.get_rect(centerx=stats_bounds['center_x'], top=out_y))
                s_line += 1
            elif fo_val == "next":
                n_next_found = len(disp_flags_reached_in_order)
                nf_s = font.render(f"next flags found: {n_next_found}", True, (0, 0, 255))
                nf_y = right_panel.get_line_y("STATS_PANEL", s_line, line_height)
                screen.blit(nf_s, nf_s.get_rect(centerx=stats_bounds['center_x'], top=nf_y))
                s_line += 1

        if game_state == GameState.ENDGAME and end_state:
            end_messages = {
                "all_flags_reached": ("all flags captured", (34, 177, 76)),
                "no_moves": ("no legal moves", (200, 0, 0)),
                "resignation": ("resigned", (180, 0, 0)),
                "timeout": ("time's up", (0, 0, 200)),
            }
            msg, msg_color = end_messages.get(end_state, ("game over", (0, 0, 0)))
            em_s = font_large.render(msg, True, msg_color)
            em_y = right_panel.get_line_y("STATS_PANEL", s_line + 1, line_height)
            screen.blit(em_s, em_s.get_rect(centerx=stats_bounds['center_x'], top=em_y))







        pygame.display.flip()

        # ===================== EVENT HANDLING =====================
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game_state == GameState.INGAME:
                        resign_game()
                    elif game_state == GameState.ENDGAME:
                        new_game()
                elif event.key == pygame.K_m:
                    pygame.display.iconify()
                elif event.key == pygame.K_u and game_state == GameState.INGAME:
                    undo_move()
                elif event.key == pygame.K_g:
                    toggle_guide_mode()
                elif event.key == pygame.K_t:
                    toggle_track_mode()
                elif event.key == pygame.K_h and game_state == GameState.INGAME:
                    toggle_hint_mode()
                elif event.key == pygame.K_p:
                    toggle_peek()

            if event.type == pygame.ACTIVEEVENT:
                state_attr = getattr(event, "state", 0)
                gain_attr = getattr(event, "gain", 0)
                if state_attr & 4:
                    if gain_attr == 0:
                        if clock_start_time is not None and game_state == GameState.INGAME:
                            paused_elapsed += time.time() - clock_start_time
                            clock_start_time = None
                    elif gain_attr == 1:
                        if game_state == GameState.INGAME and clock_start_time is None and \
                                len(visited_moves) > 1:
                            clock_start_time = time.time()

            # Codec input
            if game_state == GameState.MENU and seed_mode_active:
                codec_input.handle_event(event)

            # Button events
            for btn in buttons.values():
                btn.handle_event(event)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                # Widget (menu selector) clicks
                for key, rect in widget_rects.items():
                    if rect.collidepoint(mx, my):
                        action, item_idx = key
                        lbl, vals, cur = menu_items[item_idx]
                        if action == "plus":
                            menu_items[item_idx] = (lbl, vals, (cur + 1) % len(vals))
                        elif action == "minus":
                            menu_items[item_idx] = (lbl, vals, (cur - 1) % len(vals))
                        # Update board model size for preview
                        if lbl == "board":
                            new_b = menu_items[item_idx][1][menu_items[item_idx][2]]
                            board_model.cols = new_b
                            board_model.rows = new_b
                            board_model.clear()

                # Board click (making a move or moving preview piece)
                if game_state == GameState.INGAME:
                    grid_pos = board_renderer.to_grid(mx, my)
                    if grid_pos is not None:
                        make_move(grid_pos)
                elif game_state == GameState.MENU:
                    grid_pos = board_renderer.to_grid(mx, my)
                    if grid_pos is not None:
                        preview_pos = grid_pos

        pygame.time.wait(5)


if __name__ == "__main__":
    main()