# knightsmaze_v01.py

import sys
import os
import time
import random
from collections import deque
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

# --- directory paths ---
pieces_dir  = os.path.join(BASE_DIR, "assets", "pieces")
arrows_dir  = os.path.join(BASE_DIR, "assets", "arrows")

# --- constants ---
FPS = 60
UI_SPACE = 16
BTW = int(UI_SPACE * 9)
BTH = int(UI_SPACE * 2)

BOARD_MIN     = 5
BOARD_MAX     = 20
BOARD_DEFAULT = 8

INFINITY_SYMBOL     = "\u221e"
MAZE_TYPE_CHOICES   = ["walled", "open"]
PATH_LENGTH_CHOICES = ["short", "medium", "long"]
PATH_LENGTH_MAP     = {"short": 1, "medium": 2, "long": 4}

# --- colors ---
LT_SQUARE  = (255, 255, 240)
DK_SQUARE  = (232, 200, 150)
LT_MOVE    = (148, 220, 248)
DK_MOVE    = (100, 145, 225)
LT_BLOCK   = (255, 192, 192)
DK_BLOCK   = (255, 128, 128)
PURPLE     = (189, 135, 249)
GRID_COLOR = (107, 70, 51)
BACK_COLOR = (244, 228, 195)

MENU_PREVIEW_SEED = 42    # fixed seed for stable MENU board preview
CODEC_TEXT_LENGTH = 16    # expected raw length (no dashes) of a valid share code

# --- minimum board sizes for maze generation ---
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

# --- codec schema ---
# Settings: 4(version) + 4(board) + 1(type) + 2(length) + 1(blocks) + 1(bounce) = 13 bits in 16 bits.
# Data: 2 bytes settings + 8 bytes seed = 10 bytes -> 16 base32 chars.
knightsmaze_schema = [
    ("board",   4, lambda v: int(v) - BOARD_MIN),
    ("type",    1, {"walled": 0, "open": 1}),
    ("length",  2, {"short": 0, "medium": 1, "long": 2}),
    ("blocks",  1, {"show": 0, "hide": 1}),
    ("bounce",  1, {"stay": 0, "bounce": 1}),
]


# --- GameState ---
class GameState(Enum):
    MENU    = auto()
    INGAME  = auto()
    ENDGAME = auto()


# --- Button ---
class Button:
    def __init__(self, rect, text, text_color, bg_color, font, function=None):
        self.rect       = rect
        self.text       = text
        self.text_color = text_color
        self.bg_color   = bg_color
        self.font       = font
        self.function   = function
        self.active     = True

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
    hours   = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def display_clock(clock_selected):
    """Display string for a clock setting (in seconds). 0 means infinity."""
    if clock_selected == 0:
        return INFINITY_SYMBOL
    mins = clock_selected // 60
    return f"{mins}:00"


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


# --- seeded maze generation ---

def _make_rng(seed=None):
    if seed is not None:
        return random.Random(seed)
    return random.Random()


def generate_path_and_obstacles(n, min_length, max_length, move_func,
                                 obstacles=None, start=None, rng=None):
    if rng is None:
        rng = random
    squares  = [(x, y) for x in range(n) for y in range(n)]
    if start is None:
        start = rng.choice(squares)
    path     = [start]
    path_set = {start}
    obstacles = set(obstacles) if obstacles else set()

    while len(path) < max_length:
        current = path[-1]
        moves   = [m for m in move_func(*current, n)
                   if m not in path_set and m not in obstacles]
        if not moves:
            break
        nxt = rng.choice(moves)
        path.append(nxt)
        path_set.add(nxt)
        obstacles.update(
            sq for sq in moves
            if sq != nxt and sq not in obstacles and sq not in path_set
        )

    if min_length <= len(path) <= max_length:
        return path, obstacles
    return None, None


def generate_maze_path_and_obstacles(n, min_length, max_length, move_func,
                                      max_attempts=200, time_budget=1.0, rng=None):
    if rng is None:
        rng = random
    squares        = [(x, y) for x in range(n) for y in range(n)]
    lowest_min_len = max(2, n // 2)

    for attempt_min_len in range(min_length, lowest_min_len - 1, -1):
        attempts   = 0
        start_time = time.time() if time_budget is not None else None
        while True:
            if max_attempts is not None and attempts >= max_attempts:
                break
            if time_budget is not None and (time.time() - start_time) > time_budget:
                break
            attempts += 1
            start = rng.choice(squares)
            path, obs = generate_path_and_obstacles(
                n, attempt_min_len, max_length, move_func, start=start, rng=rng
            )
            if path:
                return path, obs

    return None, None


def min_moves_between(start, target, move_func, n):
    visited = set()
    queue   = deque([(start, 0)])
    while queue:
        current, dist = queue.popleft()
        if current == target:
            return dist
        for m in move_func(*current, n):
            if m not in visited:
                visited.add(m)
                queue.append((m, dist + 1))
    return float("inf")


def generate_open_maze_path_and_obstacles(n, min_length, max_length, move_func,
                                           max_attempts=200, time_budget=1.0, rng=None):
    if rng is None:
        rng = random
    squares    = [(x, y) for x in range(n) for y in range(n)]
    start_time = time.time() if time_budget is not None else None

    for _ in range(max_attempts or 1000):
        if time_budget is not None and (time.time() - start_time) > time_budget:
            break
        target     = rng.choice(squares)
        far_starts = [
            sq for sq in squares
            if min_moves_between(sq, target, move_func, n) >= 3
        ]
        if not far_starts:
            continue
        start    = rng.choice(far_starts)
        path     = [start]
        path_set = {start}
        while len(path) < max_length:
            current = path[-1]
            moves   = [m for m in move_func(*current, n) if m not in path_set]
            if target in move_func(*current, n) and target not in path_set:
                path.append(target)
                path_set.add(target)
                break
            if not moves:
                break
            nxt = rng.choice(moves)
            path.append(nxt)
            path_set.add(nxt)
        if (
            len(path) >= min_length
            and path[-1] == target
            and start in path_set
            and target in path_set
        ):
            obstacles = set(squares) - set(path)
            return path, obstacles

    return None, None


# --- codec helpers ---

def validate_and_apply_codec(codec_text, menu_items, label_to_index):
    try:
        params    = decode_params(codec_text, knightsmaze_schema)
        board_val = params.get("board", 0) + BOARD_MIN
        if not (BOARD_MIN <= board_val <= BOARD_MAX):
            return False, None
        type_val   = params.get("type")
        length_val = params.get("length")
        blocks_val = params.get("blocks")
        bounce_val = params.get("bounce")
        if type_val   not in MAZE_TYPE_CHOICES:   return False, None
        if length_val not in PATH_LENGTH_CHOICES: return False, None
        if blocks_val not in ("show", "hide"):    return False, None
        if bounce_val not in ("stay", "bounce"):  return False, None

        def _apply(label, value):
            idx = label_to_index[label]
            lbl, vals, _ = menu_items[idx]
            if value in vals:
                menu_items[idx] = (lbl, vals, vals.index(value))

        _apply("board",  board_val)
        _apply("type",   type_val)
        _apply("length", length_val)
        _apply("blocks", blocks_val)
        _apply("bounce", bounce_val)

        return True, {**params, "board": board_val}
    except Exception:
        return False, None


# --- main ---

def main():
    pygame.init()

    info   = pygame.display.Info()
    screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.RESIZABLE)
    pygame.display.set_caption("Knight's Maze")

    try:
        import ctypes
        hwnd = pygame.display.get_wm_info()["window"]
        ctypes.windll.user32.ShowWindow(hwnd, 3)
    except (KeyError, AttributeError, OSError, ImportError):
        pass

    clock_ticker = pygame.time.Clock()
    font         = pygame.font.SysFont("arial", 18)
    font_large   = pygame.font.SysFont("arial", 20)

    # --- menu items ---
    menu_items = [
        ("board",  list(range(BOARD_MIN, BOARD_MAX + 1)),   3),  # idx 3 -> 8
        ("type",   MAZE_TYPE_CHOICES[:],                    0),
        ("length", PATH_LENGTH_CHOICES[:],                  0),
        ("blocks", ["show", "hide"],                        0),
        ("bounce", ["stay", "bounce"],                      0),
        ("clock",  [0] + list(range(60, 30 * 60 + 1, 60)), 0),  # 0 = infinity
        ("piece",  pk.PIECE_LIST[:],                        0),
    ]
    label_to_index = {lbl: i for i, (lbl, _, _) in enumerate(menu_items)}

    def get_selection(label):
        i = label_to_index[label]
        _, vals, cur = menu_items[i]
        return vals[cur]

    # --- board model / renderer ---
    board_model    = BoardModel(BOARD_DEFAULT, BOARD_DEFAULT)
    board_renderer = BoardRenderer(board_model, 10, (0, 0))
    current_cell_size = 0

    # --- game state ---
    game_state: GameState = GameState.MENU
    end_state: Optional[str] = None

    maze_path:     Optional[List[Tuple[int, int]]] = None
    maze_path_set: Set[Tuple[int, int]] = set()
    obstacles:     Set[Tuple[int, int]] = set()

    knight_pos:    Optional[Tuple[int, int]] = None
    move_nums:     Dict[Tuple[int, int], int] = {}
    move_count:    int = 0
    attempt_count: int = 0

    obstacle_flash_list:    List[Tuple[Tuple[int, int], float]] = []
    obstacle_permanent_red: Set[Tuple[int, int]] = set()

    clock_start_time:  Optional[float] = None
    paused_elapsed:    float = 0.0
    clock_elapsed:     int   = 0
    final_elapsed:     int   = 0

    guide_mode_active:  bool = True
    track_mode_active:  bool = True
    peek_mode_visible:  bool = False
    reveal_mode_active: bool = False

    replay_states:      List[Dict] = []
    replay_index:       int  = 0
    replay_mode_active: bool = False

    puzzle_code:         str  = ""
    last_puzzle_seed:    Optional[int] = None
    seed_mode_active:    bool = False
    copy_button_clicked: bool = False
    copy_button_timer:   int  = 0

    menu_preview_cache = None   # (cache_key, path, obstacles) or None
    menu_preview_pos: Optional[Tuple[int, int]] = None  # current piece pos in MENU preview
    prev_legal: List[Tuple[int, int]] = []

    error_message: str = ""
    error_timer:   int = 0

    widget_rects: Dict = {}
    arrows: Dict[Tuple[int, int], pygame.Surface] = {}

    codec_input = TextInput(pygame.Rect(0, 0, BTW, BTH), font, max_length=19)

    # -------- helpers --------

    def _capture_state():
        return {
            "pos":        knight_pos,
            "move_nums":  dict(move_nums),
            "move_count": move_count,
        }

    def _restore_state(state):
        nonlocal knight_pos, move_count
        knight_pos = state["pos"]
        move_nums.clear()
        move_nums.update(state["move_nums"])
        move_count = state["move_count"]

    def get_legal_moves(pos, n, piece, excluded):
        raw = pk.get_move_func(piece)(*pos, n)
        return [(x, y) for (x, y) in raw if (x, y) not in excluded]

    def get_path_legal_moves(pos, n, piece, path_set, visited):
        raw = pk.get_move_func(piece)(*pos, n)
        return [(x, y) for (x, y) in raw
                if (x, y) in path_set and (x, y) not in visited]

    def start_game(use_seed=None):
        nonlocal game_state, end_state
        nonlocal maze_path, maze_path_set, obstacles
        nonlocal knight_pos, move_nums, move_count, attempt_count
        nonlocal obstacle_flash_list, obstacle_permanent_red
        nonlocal clock_start_time, paused_elapsed, clock_elapsed, final_elapsed
        nonlocal replay_states, replay_index, replay_mode_active
        nonlocal puzzle_code, last_puzzle_seed, error_message, error_timer
        nonlocal peek_mode_visible, reveal_mode_active

        board_size  = get_selection("board")
        piece       = get_selection("piece")
        maze_type   = get_selection("type")
        path_length = get_selection("length")

        min_board = get_min_board_size(piece)
        if board_size < min_board:
            error_message = f"{piece} needs board >= {min_board}"
            error_timer   = pygame.time.get_ticks() + 3000
            return

        if use_seed is not None:
            seed = use_seed
        elif seed_mode_active:
            code_text = codec_input.get_text()
            ok, params = validate_and_apply_codec(code_text, menu_items, label_to_index)
            if ok and params:
                seed        = params["seed"]
                board_size  = get_selection("board")
                maze_type   = get_selection("type")
                path_length = get_selection("length")
                piece       = get_selection("piece")
            else:
                error_message = "Invalid share code"
                error_timer   = pygame.time.get_ticks() + 3000
                return
        else:
            seed = random.randint(0, 2 ** 63 - 1)

        last_puzzle_seed = seed

        n          = board_size
        multiplier = PATH_LENGTH_MAP[path_length]
        min_len    = n * multiplier + 1
        max_len    = n * n if path_length == "long" else n * 2 * multiplier

        move_func = pk.get_move_func(piece)
        rng       = _make_rng(seed)

        if maze_type == "open":
            path, obs = generate_open_maze_path_and_obstacles(
                n, min_len, max_len, move_func,
                max_attempts=200, time_budget=1.0, rng=rng
            )
        else:
            path, obs = generate_maze_path_and_obstacles(
                n, min_len, max_len, move_func,
                max_attempts=200, time_budget=1.0, rng=rng
            )

        if not path or len(path) <= 4 or obs is None:
            error_message = "Failed to generate maze – try different settings"
            error_timer   = pygame.time.get_ticks() + 3000
            return

        params_enc = {
            "board":  board_size,
            "type":   maze_type,
            "length": path_length,
            "blocks": get_selection("blocks"),
            "bounce": get_selection("bounce"),
        }
        try:
            puzzle_code = encode_params(params_enc, knightsmaze_schema, seed)
        except Exception:
            puzzle_code = ""

        board_model.cols = n
        board_model.rows = n
        board_model.clear()

        maze_path     = path
        maze_path_set = set(path)
        obstacles     = set(obs)

        knight_pos             = maze_path[0]
        move_nums              = {knight_pos: 0}
        move_count             = 0
        attempt_count          = 0
        obstacle_flash_list    = []
        obstacle_permanent_red = set()
        end_state              = None

        clock_start_time = None
        paused_elapsed   = 0.0
        clock_elapsed    = 0
        final_elapsed    = 0

        replay_states      = [_capture_state()]
        replay_index       = 0
        replay_mode_active = False
        peek_mode_visible  = False
        reveal_mode_active = False

        game_state = GameState.INGAME

    def make_move(target_pos):
        nonlocal knight_pos, move_count, attempt_count, clock_start_time
        nonlocal end_state, game_state, final_elapsed

        if game_state != GameState.INGAME:
            return

        n         = board_model.cols
        piece     = get_selection("piece")
        reachable = pk.get_move_func(piece)(*knight_pos, n)
        if target_pos not in reachable:
            return

        if clock_start_time is None:
            clock_start_time = time.time()

        blocks_show = get_selection("blocks") == "show"
        bounce      = get_selection("bounce") == "bounce"

        if target_pos in obstacles:
            attempt_count += 1
            if blocks_show:
                # "show" mode: block stays visible permanently once hit
                obstacle_permanent_red.add(target_pos)
            else:
                # "hide" mode: block flashes briefly then disappears
                obstacle_flash_list.append((target_pos, time.time()))
            if bounce:
                knight_pos = maze_path[0]
                move_nums.clear()
                move_nums[knight_pos] = 0
                move_count = 0
                replay_states.clear()
                replay_states.append(_capture_state())
            return

        if target_pos not in maze_path_set or target_pos in move_nums:
            return

        move_count += 1
        knight_pos  = target_pos
        move_nums[knight_pos] = move_count
        replay_states.append(_capture_state())

        if knight_pos == maze_path[-1]:
            final_elapsed = int(paused_elapsed + (
                (time.time() - clock_start_time) if clock_start_time else 0))
            end_state  = "maze_complete"
            game_state = GameState.ENDGAME
            return

        path_legal = get_path_legal_moves(knight_pos, n, piece, maze_path_set, move_nums)
        if not path_legal:
            final_elapsed = int(paused_elapsed + (
                (time.time() - clock_start_time) if clock_start_time else 0))
            end_state  = "no_moves"
            game_state = GameState.ENDGAME

    def undo_move():
        nonlocal knight_pos, move_count, replay_states
        if game_state != GameState.INGAME or len(replay_states) <= 1:
            return
        replay_states.pop()
        _restore_state(replay_states[-1])

    def resign_game():
        nonlocal end_state, game_state, final_elapsed
        if game_state != GameState.INGAME:
            return
        final_elapsed = int(paused_elapsed + (
            (time.time() - clock_start_time) if clock_start_time else 0))
        end_state  = "resignation"
        game_state = GameState.ENDGAME

    def toggle_guide_mode():
        nonlocal guide_mode_active
        guide_mode_active = not guide_mode_active

    def toggle_track_mode():
        nonlocal track_mode_active
        track_mode_active = not track_mode_active

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
            replay_index = len(replay_states) - 1
        else:
            _restore_state(replay_states[-1])

    def navigate_replay(delta):
        nonlocal replay_index
        if not replay_mode_active or not replay_states:
            return
        replay_index = int(clamp(replay_index + delta, 0, len(replay_states) - 1))
        _restore_state(replay_states[replay_index])

    def toggle_reveal():
        nonlocal reveal_mode_active
        if game_state == GameState.ENDGAME:
            reveal_mode_active = not reveal_mode_active

    def retry_game():
        if last_puzzle_seed is not None:
            start_game(use_seed=last_puzzle_seed)

    def new_game():
        nonlocal game_state, end_state, seed_mode_active
        nonlocal replay_mode_active, puzzle_code
        nonlocal peek_mode_visible, reveal_mode_active
        end_state          = None
        peek_mode_visible  = False
        reveal_mode_active = False
        seed_mode_active   = False
        replay_mode_active = False
        puzzle_code        = ""
        game_state         = GameState.MENU

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
        copy_button_timer   = pygame.time.get_ticks() + 2000

    def quit_game():
        pygame.quit()
        sys.exit()

    # -------- buttons --------
    buttons = {
        "start":       Button(pygame.Rect(0,0,0,0), "start",
                              (255,255,255), (92,192,92),  font, start_game),
        "enter_code":  Button(pygame.Rect(0,0,0,0), "enter share code",
                              (255,255,255), (224,0,96),   font, toggle_codec_input),
        "copy_code":   Button(pygame.Rect(0,0,0,0), "copy share code",
                              (255,255,255), (224,0,96),   font, copy_code_to_clipboard),
        "guide_mode":  Button(pygame.Rect(0,0,0,0), "show move guide",
                              (255,255,255), (128,64,255), font, toggle_guide_mode),
        "track_mode":  Button(pygame.Rect(0,0,0,0), "show move numbers",
                              (255,255,255), (255,92,128), font, toggle_track_mode),
        "undo_mode":   Button(pygame.Rect(0,0,0,0), "undo last move",
                              (255,255,255), (64,128,255), font, undo_move),
        "resign":      Button(pygame.Rect(0,0,0,0), "resign",
                              (255,255,255), (128,128,128),   font, resign_game),
        "reveal":      Button(pygame.Rect(0,0,0,0), "show maze solution",
                              (255,255,255), (255,128,96), font, toggle_reveal),
        "replay_mode": Button(pygame.Rect(0,0,0,0), "start replay",
                              (255,255,255), (64,128,255), font, toggle_replay_mode),
        "replay_prev": Button(pygame.Rect(0,0,0,0), "-",
                              (255,255,240), (64,128,255), font, lambda: navigate_replay(-1)),
        "replay_next": Button(pygame.Rect(0,0,0,0), "+",
                              (255,255,240), (64,128,255), font, lambda: navigate_replay(1)),
        "retry":       Button(pygame.Rect(0,0,0,0), "retry",
                              (255,255,255), (92,192,92),  font, retry_game),
        "new_game":    Button(pygame.Rect(0,0,0,0), "new game",
                              (255,255,255), (32,128,96),  font, new_game),
        "peek_mode":   Button(pygame.Rect(0,0,0,0), "peek",
                              (255,255,240),       LT_SQUARE,    font, toggle_peek),
        "exit":        Button(pygame.Rect(0,0,0,0), "exit",
                              (255,255,255), (220,40,40),  font, quit_game),
    }

    try:
        pk.load_images(pieces_dir, 36)
    except Exception as e:
        print(f"Warning: could not load piece images: {e}")

    # ========== MAIN LOOP ==========
    while True:
        clock_ticker.tick(FPS)
        dt = clock_ticker.get_time()
        codec_input.update(dt)

        if copy_button_clicked and pygame.time.get_ticks() > copy_button_timer:
            copy_button_clicked = False

        if game_state == GameState.INGAME:
            if clock_start_time is not None:
                clock_elapsed = int(paused_elapsed + (time.time() - clock_start_time))
            if clock_has_expired(get_selection("clock"), clock_elapsed):
                final_elapsed = clock_elapsed
                end_state  = "timeout"
                game_state = GameState.ENDGAME

        now = time.time()
        obstacle_flash_list = [(sq, ts) for sq, ts in obstacle_flash_list if now - ts < 2.0]

        win_width, win_height = screen.get_size()
        screen.fill(BACK_COLOR)

        # --- layout ---
        margin      = UI_SPACE
        panel_width = UI_SPACE * 18
        msg_left    = margin
        msg_top     = margin
        msg_bottom  = win_height - margin
        msg_right   = msg_left + panel_width
        right_left  = win_width - panel_width - margin

        left_panel_rect  = pygame.Rect(msg_left,   msg_top, panel_width, msg_bottom - msg_top)
        right_panel_rect = pygame.Rect(right_left, msg_top, panel_width, msg_bottom - msg_top)

        left_panel  = UIPanel(left_panel_rect,  gap=2)
        right_panel = UIPanel(right_panel_rect, gap=2)

        left_panel.draw_panel(screen,  "MENU_PANEL",   LT_SQUARE, GRID_COLOR)
        left_panel.draw_panel(screen,  "BUTTON_PANEL", LT_SQUARE, GRID_COLOR)
        right_panel.draw_panel(screen, "PIECE_PANEL",  LT_SQUARE, GRID_COLOR)
        right_panel.draw_panel(screen, "STATS_PANEL",  LT_SQUARE, GRID_COLOR)

        area_left   = msg_right  + margin
        area_top    = margin
        area_right  = right_left - margin
        area_bottom = win_height - margin
        area_width  = area_right  - area_left
        area_height = area_bottom - area_top

        # Sync board model size to current setting
        brd = get_selection("board")
        if game_state == GameState.MENU:
            if board_model.cols != brd or board_model.rows != brd:
                board_model.cols = brd
                board_model.rows = brd
                board_model.clear()

        cols, rows = board_model.cols, board_model.rows
        new_cell_size = 0
        if cols > 0 and rows > 0:
            new_cell_size = max(12, min(area_width // cols, area_height // rows))

        if new_cell_size != current_cell_size and new_cell_size > 0:
            current_cell_size = new_cell_size
            board_renderer.cell_size = new_cell_size
            try:
                pk.load_images(pieces_dir, max(12, new_cell_size - 4))
                arrow_names = {
                    (0, -1): "arrow_n.png",  (1, -1): "arrow_ne.png",
                    (1,  0): "arrow_e.png",  (1,  1): "arrow_se.png",
                    (0,  1): "arrow_s.png",  (-1, 1): "arrow_sw.png",
                    (-1, 0): "arrow_w.png",  (-1,-1): "arrow_nw.png",
                }
                arrows.clear()
                arrow_size = max(8, current_cell_size // 2)
                diag_size  = max(6, int(arrow_size * 0.75))
                for direction, fname in arrow_names.items():
                    fpath = os.path.join(arrows_dir, fname)
                    try:
                        img = pygame.image.load(fpath).convert_alpha()
                        dx, dy = direction
                        sz = diag_size if (dx != 0 and dy != 0) else arrow_size
                        arrows[direction] = pygame.transform.smoothscale(img, (sz, sz))
                    except Exception:
                        pass
            except Exception as e:
                print(f"Warning: image reload: {e}")

        board_pixel_w = cols * current_cell_size
        board_pixel_h = rows * current_cell_size
        origin_x = area_left + (area_width  - board_pixel_w) // 2
        origin_y = area_top  + (area_height - board_pixel_h) // 2
        board_renderer.origin = (origin_x, origin_y)

        cs = current_cell_size

        # --- display state (normal or replay) ---
        if game_state == GameState.ENDGAME and replay_mode_active and replay_states:
            disp = replay_states[replay_index]
            disp_pos        = disp["pos"]
            disp_move_nums  = disp["move_nums"]
            disp_move_count = disp["move_count"]
        else:
            disp_pos        = knight_pos
            disp_move_nums  = move_nums
            disp_move_count = move_count

        # --- MENU preview ---
        if game_state == GameState.MENU:
            prev_board  = get_selection("board")
            prev_length = get_selection("length")
            prev_type   = get_selection("type")
            # Only board and length trigger preview regeneration (per spec)
            cache_key = (prev_board, prev_length)
            if menu_preview_cache is None or menu_preview_cache[0] != cache_key:
                prev_piece     = get_selection("piece")
                prev_move_func = pk.get_move_func(prev_piece)
                n_prev = prev_board
                mult   = PATH_LENGTH_MAP[prev_length]
                mn_len = n_prev * mult + 1
                mx_len = n_prev * n_prev if prev_length == "long" else n_prev * 2 * mult
                prev_rng = _make_rng(MENU_PREVIEW_SEED)
                if prev_type == "open":
                    pp, po = generate_open_maze_path_and_obstacles(
                        n_prev, mn_len, mx_len, prev_move_func,
                        max_attempts=100, time_budget=0.5, rng=prev_rng)
                else:
                    pp, po = generate_maze_path_and_obstacles(
                        n_prev, mn_len, mx_len, prev_move_func,
                        max_attempts=100, time_budget=0.5, rng=prev_rng)
                menu_preview_cache = (cache_key, pp, po or set())
                # Reset piece position to path start when preview changes
                menu_preview_pos = menu_preview_cache[1][0] if menu_preview_cache[1] else None

            _, prev_path, prev_obs = menu_preview_cache

            # Ensure preview pos is always valid for the current board
            if menu_preview_pos is None or not (0 <= menu_preview_pos[0] < prev_board
                                                and 0 <= menu_preview_pos[1] < prev_board):
                menu_preview_pos = prev_path[0] if prev_path else None

            # Compute guide arrows from current preview piece position
            if guide_mode_active and prev_path and cs > 0 and menu_preview_pos:
                raw_g    = pk.get_move_func(get_selection("piece"))(*menu_preview_pos, prev_board)
                prev_legal = [(x, y) for (x, y) in raw_g
                              if 0 <= x < prev_board and 0 <= y < prev_board]
            else:
                prev_legal = []

        # ---------- draw board ----------
        board_renderer.draw_background(screen)

        if cs > 0:
            # MENU preview overlay
            if game_state == GameState.MENU:
                _, prev_path, prev_obs = menu_preview_cache if menu_preview_cache else (None, None, set())
                if prev_path:
                    # Path squares (except target)
                    for gx, gy in prev_path[:-1]:
                        px, py = board_renderer.to_pixel(gx, gy)
                        color  = LT_MOVE if (gx + gy) % 2 == 0 else DK_MOVE
                        pygame.draw.rect(screen, color, (px+1, py+1, cs-1, cs-1))
                    # Target
                    tx, ty = prev_path[-1]
                    px, py = board_renderer.to_pixel(tx, ty)
                    pygame.draw.rect(screen, PURPLE, (px+1, py+1, cs-1, cs-1))
                    # Obstacles (always shown in preview)
                    for gx, gy in prev_obs:
                        if 0 <= gx < prev_board and 0 <= gy < prev_board:
                            px, py = board_renderer.to_pixel(gx, gy)
                            color  = LT_BLOCK if (gx + gy) % 2 == 0 else DK_BLOCK
                            pygame.draw.rect(screen, color, (px+1, py+1, cs-1, cs-1))
                    # Piece — always visible in MENU regardless of guide mode
                    if menu_preview_pos:
                        px, py  = board_renderer.to_pixel(*menu_preview_pos)
                        pr_rect = pygame.Rect(px+1, py+1, cs-2, cs-2)
                        try:
                            pk.draw_piece(screen, pr_rect, get_selection("piece"))
                        except Exception:
                            pygame.draw.ellipse(screen, (0,0,0), pr_rect)
                    # Guide arrows — only when guide mode active
                    if guide_mode_active and arrows and prev_legal and menu_preview_pos:
                        for mx, my in prev_legal:
                            dx = int(clamp(mx - menu_preview_pos[0], -1, 1))
                            dy = int(clamp(my - menu_preview_pos[1], -1, 1))
                            a  = arrows.get((dx, dy))
                            if a:
                                gpx, gpy = board_renderer.to_pixel(mx, my)
                                screen.blit(a, a.get_rect(center=(gpx+cs//2, gpy+cs//2)))

            # INGAME / ENDGAME overlay
            if game_state in (GameState.INGAME, GameState.ENDGAME):
                show_full_path = (
                    (game_state == GameState.INGAME  and peek_mode_visible) or
                    (game_state == GameState.ENDGAME and reveal_mode_active)
                )

                # Full path (peek / reveal)
                if show_full_path and maze_path:
                    for gx, gy in maze_path:
                        if (gx, gy) != maze_path[-1] and (gx, gy) not in disp_move_nums:
                            px, py = board_renderer.to_pixel(gx, gy)
                            color  = LT_MOVE if (gx + gy) % 2 == 0 else DK_MOVE
                            pygame.draw.rect(screen, color, (px+1, py+1, cs-1, cs-1))

                # Target
                if maze_path:
                    tx, ty = maze_path[-1]
                    px, py = board_renderer.to_pixel(tx, ty)
                    pygame.draw.rect(screen, PURPLE, (px+1, py+1, cs-1, cs-1))

                # Revealed obstacle squares:
                # "show" mode: obstacle_permanent_red (hit once → stays visible forever)
                # "hide" mode: obstacle_flash_list (hit → visible briefly, then hidden)
                for gx, gy in obstacle_permanent_red:
                    px, py = board_renderer.to_pixel(gx, gy)
                    color  = LT_BLOCK if (gx + gy) % 2 == 0 else DK_BLOCK
                    pygame.draw.rect(screen, color, (px+1, py+1, cs-1, cs-1))

                # Flash recently-hit obstacles (shown for ~2 s then hidden)
                flash_now = time.time()
                for sq, ts in obstacle_flash_list:
                    if flash_now - ts < 2.0:
                        gx, gy = sq
                        px, py = board_renderer.to_pixel(gx, gy)
                        pygame.draw.rect(screen, (255,0,0), (px+1, py+1, cs-1, cs-1))

                # Visited squares
                for vx, vy in disp_move_nums:
                    if (vx, vy) == disp_pos:
                        continue
                    px, py = board_renderer.to_pixel(vx, vy)
                    vc     = LT_MOVE if (vx + vy) % 2 == 0 else DK_MOVE
                    pygame.draw.rect(screen, vc, (px+3, py+3, cs-4, cs-4))
                    if track_mode_active and (vx, vy) in disp_move_nums:
                        luma = vc[0]*0.299 + vc[1]*0.587 + vc[2]*0.114
                        nc   = (0,0,0) if luma > 128 else (255,255,255)
                        nf   = pygame.font.SysFont("arial", max(8, cs//3))
                        ns   = nf.render(str(disp_move_nums[(vx, vy)]), True, nc)
                        screen.blit(ns, ns.get_rect(center=(px+cs//2, py+cs//2)))

                # Guide arrows
                if guide_mode_active and arrows and disp_pos:
                    n_brd = board_model.cols
                    piece = get_selection("piece")
                    if replay_mode_active and game_state == GameState.ENDGAME:
                        guide_moves = get_legal_moves(disp_pos, n_brd, piece, disp_move_nums)
                    else:
                        guide_moves = get_legal_moves(knight_pos, n_brd, piece, move_nums)
                    for mx, my in guide_moves:
                        dx = int(clamp(mx - disp_pos[0], -1, 1))
                        dy = int(clamp(my - disp_pos[1], -1, 1))
                        a  = arrows.get((dx, dy))
                        if a:
                            gpx, gpy = board_renderer.to_pixel(mx, my)
                            screen.blit(a, a.get_rect(center=(gpx+cs//2, gpy+cs//2)))

                # Piece at current/replay position
                if disp_pos:
                    ppx, ppy = board_renderer.to_pixel(*disp_pos)
                    pr_rect  = pygame.Rect(ppx+1, ppy+1, cs-2, cs-2)
                    try:
                        pk.draw_piece(screen, pr_rect, get_selection("piece"))
                    except Exception:
                        pygame.draw.ellipse(screen, (0,0,0), pr_rect)

        board_renderer.draw_grid_lines(screen)

        # Error overlay
        if error_message and pygame.time.get_ticks() < error_timer:
            ef = pygame.font.SysFont("arial", 22)
            es = ef.render(error_message, True, (200,0,0))
            ex = area_left + (area_width  - es.get_width())  // 2
            ey = area_top  + (area_height - es.get_height()) // 2
            pygame.draw.rect(screen, (255,240,240),
                             (ex-8, ey-6, es.get_width()+16, es.get_height()+12))
            screen.blit(es, (ex, ey))
        elif error_message and pygame.time.get_ticks() >= error_timer:
            error_message = ""

        # ===================== UI PANELS =====================

        widget_rects.clear()
        btn_w       = UI_SPACE
        line_height = font.get_linesize() + UI_SPACE

        # ---- MENU_PANEL ----
        menu_bounds = left_panel.get_bounds("MENU_PANEL")
        text_x      = menu_bounds["left"] + UI_SPACE

        menu_panel_items = [
            (i, (lbl, vals, cur))
            for i, (lbl, vals, cur) in enumerate(menu_items)
            if lbl != "piece"
        ]

        max_lbl_w = max(
            font.render(lbl + ":", True, (0,0,0)).get_width()
            for lbl, _, _ in menu_items if lbl != "piece"
        )
        minus_x = text_x + max_lbl_w + UI_SPACE
        plus_x  = menu_bounds["right"] - UI_SPACE * 4

        for list_idx, (item_idx, (label, values, cur_idx)) in enumerate(menu_panel_items):
            panel_y = left_panel.get_line_y("MENU_PANEL", list_idx, line_height)
            row_cy  = panel_y + btn_w // 2

            lbl_surf = font.render(f"{label}:", True, (0,0,0))
            screen.blit(lbl_surf, lbl_surf.get_rect(midleft=(text_x, row_cy)))

            val      = values[cur_idx]
            sel_text = display_clock(val) if label == "clock" else str(val)
            sel_surf = font.render(sel_text, True, (0,0,0))
            sel_cx   = (minus_x + btn_w + plus_x + btn_w) / 2
            screen.blit(sel_surf, sel_surf.get_rect(center=(sel_cx, row_cy)))

            if game_state == GameState.MENU:
                mr = pygame.Rect(minus_x, panel_y, int(btn_w*1.5), int(btn_w*1.5))
                pygame.draw.rect(screen, DK_SQUARE, mr)
                lt = font.render("<", True, (0,160,0))
                screen.blit(lt, lt.get_rect(center=mr.center))
                widget_rects[("minus", item_idx)] = mr

                pr = pygame.Rect(plus_x, panel_y, int(btn_w*1.5), int(btn_w*1.5))
                pygame.draw.rect(screen, DK_SQUARE, pr)
                gt = font.render(">", True, (220,0,0))
                screen.blit(gt, gt.get_rect(center=pr.center))
                widget_rects[("plus", item_idx)] = pr

        # Codec / share code section
        codec_line = len(menu_panel_items) + 2

        buttons["enter_code"].active = game_state == GameState.MENU
        if seed_mode_active:
            buttons["enter_code"].bg_color = (224, 64, 128)
            buttons["enter_code"].text     = "cancel code input"
        else:
            buttons["enter_code"].bg_color = (224, 0, 96)
            buttons["enter_code"].text     = "enter share code"
        buttons["enter_code"].rect = left_panel.get_widget_rect("MENU_PANEL", codec_line, BTW, BTH)
        buttons["enter_code"].draw(screen)

        if game_state == GameState.MENU and seed_mode_active:
            input_y = left_panel.get_line_y("MENU_PANEL", codec_line, line_height)
            input_x = menu_bounds["left"] + (menu_bounds["width"] - BTW) // 2
            codec_input.rect = pygame.Rect(input_x, input_y, BTW, BTH)
            codec_input.draw(screen)

        if puzzle_code and game_state in (GameState.INGAME, GameState.ENDGAME):
            code_y   = left_panel.get_line_y("MENU_PANEL", codec_line, line_height)
            cs2_surf = font.render(puzzle_code, True, (0,0,0))
            screen.blit(cs2_surf, cs2_surf.get_rect(
                center=(menu_bounds["center_x"], code_y + line_height // 2)))

            buttons["copy_code"].active = True
            if copy_button_clicked:
                buttons["copy_code"].bg_color = (224, 64, 128)
                buttons["copy_code"].text     = "code copied!"
            else:
                buttons["copy_code"].bg_color = (224, 0, 96)
                buttons["copy_code"].text     = "copy share code"
            buttons["copy_code"].rect = left_panel.get_widget_rect("MENU_PANEL", codec_line, BTW, BTH)
            buttons["copy_code"].draw(screen)
        else:
            buttons["copy_code"].active = False

        # ---- BUTTON_PANEL ----
        button_bounds = left_panel.get_bounds("BUTTON_PANEL")
        is_playable   = (get_selection("board") >= get_min_board_size(get_selection("piece")))

        # start
        if seed_mode_active:
            code_ok = len(codec_input.get_text()) == CODEC_TEXT_LENGTH
            buttons["start"].active = game_state == GameState.MENU and code_ok
        else:
            buttons["start"].active = game_state == GameState.MENU and is_playable
        buttons["start"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        buttons["start"].draw(screen)

        if game_state == GameState.MENU and not is_playable and not seed_mode_active:
            mb  = get_min_board_size(get_selection("piece"))
            ws  = font.render(f"board must be >= {mb}", True, (200,0,0))
            wby = buttons["start"].rect.bottom + 4
            screen.blit(ws, ws.get_rect(centerx=button_bounds["center_x"], top=wby))

        # reveal (ENDGAME only)
        buttons["reveal"].active = game_state == GameState.ENDGAME
        buttons["reveal"].text   = ("hide maze solution" if reveal_mode_active
                                    else "show maze solution")
        buttons["reveal"].rect   = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        buttons["reveal"].draw(screen)

        # guide mode (all states)
        buttons["guide_mode"].active = game_state in (GameState.MENU, GameState.INGAME, GameState.ENDGAME)
        buttons["guide_mode"].text   = ("hide move guide" if guide_mode_active else "show move guide")
        buttons["guide_mode"].rect   = left_panel.get_widget_rect("BUTTON_PANEL", 2, BTW, BTH)
        buttons["guide_mode"].draw(screen)

        # track mode (all states)
        buttons["track_mode"].active = game_state in (GameState.MENU, GameState.INGAME, GameState.ENDGAME)
        buttons["track_mode"].text   = ("hide move numbers" if track_mode_active else "show move numbers")
        buttons["track_mode"].rect   = left_panel.get_widget_rect("BUTTON_PANEL", 4, BTW, BTH)
        buttons["track_mode"].draw(screen)

        # undo (INGAME only, when there is a move to undo)
        can_undo = game_state == GameState.INGAME and len(replay_states) > 1
        buttons["undo_mode"].active = can_undo
        buttons["undo_mode"].rect   = left_panel.get_widget_rect("BUTTON_PANEL", 6, BTW, BTH)
        buttons["undo_mode"].draw(screen)

        # resign (INGAME)
        buttons["resign"].active = game_state == GameState.INGAME
        buttons["resign"].rect   = left_panel.get_widget_rect("BUTTON_PANEL", 8, BTW, BTH)
        buttons["resign"].draw(screen)

        # retry (ENDGAME)
        buttons["retry"].active = game_state == GameState.ENDGAME and last_puzzle_seed is not None
        buttons["retry"].rect   = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        buttons["retry"].draw(screen)

        # replay toggle (ENDGAME)
        buttons["replay_mode"].active = game_state == GameState.ENDGAME
        buttons["replay_mode"].text   = "end replay" if replay_mode_active else "start replay"
        buttons["replay_mode"].rect   = left_panel.get_widget_rect("BUTTON_PANEL", 6, BTW, BTH)
        buttons["replay_mode"].draw(screen)

        # replay navigation
        buttons["replay_prev"].active = False
        buttons["replay_next"].active = False
        if replay_mode_active and replay_states:
            rm_rect = buttons["replay_mode"].rect
            nav_w   = BTW // 4
            if replay_index > 0:
                buttons["replay_prev"].active = True
                buttons["replay_prev"].rect   = pygame.Rect(
                    rm_rect.left - nav_w - 4, rm_rect.top, nav_w, BTH)
                buttons["replay_prev"].draw(screen)
            if replay_index < len(replay_states) - 1:
                buttons["replay_next"].active = True
                buttons["replay_next"].rect   = pygame.Rect(
                    rm_rect.right + 4, rm_rect.top, nav_w, BTH)
                buttons["replay_next"].draw(screen)

        # new game (ENDGAME)
        buttons["new_game"].active = game_state == GameState.ENDGAME
        buttons["new_game"].rect   = left_panel.get_widget_rect("BUTTON_PANEL", 8, BTW, BTH)
        buttons["new_game"].draw(screen)

        # peek (INGAME / ENDGAME)
        buttons["peek_mode"].active = (game_state in (GameState.INGAME, GameState.ENDGAME)
                                       and maze_path is not None)
        buttons["peek_mode"].text   = "hide" if peek_mode_visible else "peek"
        buttons["peek_mode"].rect   = pygame.Rect(
            msg_left + UI_SPACE*2, msg_bottom - UI_SPACE*3, BTW//2, BTH)
        buttons["peek_mode"].draw(screen)

        # exit (always)
        buttons["exit"].rect = pygame.Rect(
            msg_right - UI_SPACE*5, msg_bottom - int(UI_SPACE*3), BTW//3, int(BTH*0.75))
        buttons["exit"].draw(screen)

        # ---- PIECE_PANEL ----
        piece_bounds = right_panel.get_bounds("PIECE_PANEL")
        right_tx     = piece_bounds["left"] + UI_SPACE

        piece_idx  = label_to_index["piece"]
        _, piece_vals, piece_cur = menu_items[piece_idx]
        piece_name = piece_vals[piece_cur]

        p_line_y = right_panel.get_line_y("PIECE_PANEL", 0, line_height)
        p_row_cy = p_line_y + btn_w // 2

        lbl_s     = font.render("piece:", True, (0,0,0))
        p_minus_x = lbl_s.get_rect(midleft=(right_tx, p_row_cy)).right + UI_SPACE
        p_plus_x  = piece_bounds["right"] - UI_SPACE * 4

        sel_s = font_large.render(piece_name, True, (0,0,0))
        screen.blit(sel_s, sel_s.get_rect(center=(piece_bounds["center_x"], p_row_cy + 8)))

        if game_state == GameState.MENU:
            pm_r = pygame.Rect(p_minus_x - btn_w, p_line_y, int(btn_w*1.5), int(btn_w*1.5))
            pygame.draw.rect(screen, DK_SQUARE, pm_r)
            screen.blit(font.render("<", True, (0,160,0)),
                        font.render("<", True, (0,160,0)).get_rect(center=pm_r.center))
            widget_rects[("minus", piece_idx)] = pm_r

            pp_r = pygame.Rect(p_plus_x - btn_w, p_line_y, int(btn_w*1.5), int(btn_w*1.5))
            pygame.draw.rect(screen, DK_SQUARE, pp_r)
            screen.blit(font.render(">", True, (220,0,0)),
                        font.render(">", True, (220,0,0)).get_rect(center=pp_r.center))
            widget_rects[("plus", piece_idx)] = pp_r

        move_text = pk.get_piece_move_sets_text(piece_name)
        info_y    = p_line_y + sel_s.get_height() + line_height
        if move_text:
            mt_s = font.render(move_text, True, (80,80,80))
            screen.blit(mt_s, mt_s.get_rect(centerx=piece_bounds["center_x"], top=info_y))
            info_y += font.get_linesize() + UI_SPACE

        if game_state == GameState.MENU and not is_playable:
            mb     = get_min_board_size(piece_name)
            warn_s = font.render("use a larger board for this piece", True, (160,0,0))
            screen.blit(warn_s, warn_s.get_rect(centerx=piece_bounds["center_x"], top=info_y))

        # ---- STATS_PANEL ----
        stats_bounds = right_panel.get_bounds("STATS_PANEL")
        s_line = 0

        if game_state in (GameState.INGAME, GameState.ENDGAME):
            # Clock
            clock_sel = get_selection("clock")
            elapsed   = final_elapsed if game_state == GameState.ENDGAME else clock_elapsed
            rem       = remaining_for(clock_sel, elapsed)
            if rem is not None:
                time_str    = format_time(rem)
                clock_color = (200,0,0) if rem < 30 else (0,0,0)
            else:
                time_str    = format_time(elapsed)
                clock_color = (0,0,0)
            clk_s = font.render("time: " + time_str, True, clock_color)
            clk_y = right_panel.get_line_y("STATS_PANEL", s_line, line_height)
            screen.blit(clk_s, clk_s.get_rect(centerx=stats_bounds["center_x"], top=clk_y))
            s_line += 1

            # Move count
            mc_label = "move" if disp_move_count == 1 else "moves"
            mc_s     = font.render(f"{disp_move_count} {mc_label}", True, (0,0,0))
            mc_y     = right_panel.get_line_y("STATS_PANEL", s_line, line_height)
            screen.blit(mc_s, mc_s.get_rect(centerx=stats_bounds["center_x"], top=mc_y))
            s_line += 1

            # Blocks hit
            bl_label = "block" if attempt_count == 1 else "blocks"
            bl_s     = font.render(f"{attempt_count} {bl_label}", True, (0,0,0))
            bl_y     = right_panel.get_line_y("STATS_PANEL", s_line, line_height)
            screen.blit(bl_s, bl_s.get_rect(centerx=stats_bounds["center_x"], top=bl_y))
            s_line += 1

        # Endgame reason
        if game_state == GameState.ENDGAME and end_state:
            end_messages = {
                "maze_complete": ("maze completed", (0,160,0)),
                "no_moves":      ("no legal moves", (200,0,0)),
                "resignation":   ("resigned",       (180,0,0)),
                "timeout":       ("time's up",      (0,0,200)),
            }
            msg, msg_color = end_messages.get(end_state, ("game over", (0,0,0)))
            em_s = font_large.render(msg, True, msg_color)
            em_y = right_panel.get_line_y("STATS_PANEL", s_line + 1, line_height)
            screen.blit(em_s, em_s.get_rect(centerx=stats_bounds["center_x"], top=em_y))

        pygame.display.flip()

        # ===================== EVENTS =====================
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
                elif event.key == pygame.K_p:
                    toggle_peek()

            if event.type == pygame.KEYDOWN and replay_mode_active:
                if event.key == pygame.K_LEFT:
                    navigate_replay(-1)
                elif event.key == pygame.K_RIGHT:
                    navigate_replay(1)

            if event.type == pygame.ACTIVEEVENT:
                state_attr = getattr(event, "state", 0)
                gain_attr  = getattr(event, "gain",  0)
                if state_attr & 4:
                    if gain_attr == 0:
                        if clock_start_time is not None and game_state == GameState.INGAME:
                            paused_elapsed  += time.time() - clock_start_time
                            clock_start_time = None
                    elif gain_attr == 1:
                        if (game_state == GameState.INGAME
                                and clock_start_time is None
                                and move_count > 0):
                            clock_start_time = time.time()

            if game_state == GameState.MENU and seed_mode_active:
                codec_input.handle_event(event)

            for btn in buttons.values():
                btn.handle_event(event)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                # Menu selector clicks
                for key, rect in widget_rects.items():
                    if rect.collidepoint(mx, my):
                        action, item_idx = key
                        lbl, vals, cur = menu_items[item_idx]
                        if action == "plus":
                            menu_items[item_idx] = (lbl, vals, (cur + 1) % len(vals))
                        elif action == "minus":
                            menu_items[item_idx] = (lbl, vals, (cur - 1) % len(vals))
                        # Invalidate preview when board or length changes
                        if lbl in ("board", "length"):
                            menu_preview_cache = None
                        break

                # Board click (making a move)
                if game_state == GameState.INGAME:
                    grid_pos = board_renderer.to_grid(mx, my)
                    if grid_pos is not None:
                        make_move(grid_pos)

                # Board click in MENU — move preview piece to any clicked square
                if game_state == GameState.MENU:
                    grid_pos = board_renderer.to_grid(mx, my)
                    if grid_pos is not None:
                        menu_preview_pos = grid_pos

        pygame.time.wait(5)


if __name__ == "__main__":
    main()