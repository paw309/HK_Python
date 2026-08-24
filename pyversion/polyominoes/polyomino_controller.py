"""
polyomino_controller.py

Game controller for Polyominoes v02.
Manages game state, move validation, polyomino placement, scoring, and rendering.
Inherits common functionality from BaseGameController.
"""

import os
import sys
import csv
import math
import random
import time
from typing import Optional, List, Tuple, Set, Dict, Any

import pygame

# --- path setup ---
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_DIR  = os.path.dirname(os.path.abspath(__file__))
SHAREDLIB = os.path.join(BASE_DIR, "sharedlib")
for _p in (BASE_DIR, SHAREDLIB, GAME_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# sharedlib imports
import piecekeeper as pk
import polyomino_data as pd
import polyomino_ratings as pr
from gameboard import BoardModel, BoardRenderer
from uipanel import UIPanel
from puzzle_codec import encode_params, decode_params, polyomino_schema
from widgets import Button, TextInput
from base_game_controller import BaseGameController, GameState

# --- constants ---

BOARD_MIN     = 5
BOARD_MAX     = 16
BOARD_DEFAULT = 8
FPS           = 60
UI_SPACE      = 10
BTW           = int(UI_SPACE * 15)
BTH           = int(UI_SPACE * 3)
MAX_CLOCK_SECONDS = 330

SHAPES_CHOICES  = ["monomino", "domino", "triomino", "tetromino",
                   "pentomino", "hexomino", "heptomino", "octomino", "mixed"]
DENSITY_CHOICES = ["low", "medium", "high"]
COLORS_CHOICES  = ["unique", "random", "same"]
CLOCK_MODES     = ["game", "move"]

LT_SQUARE  = (255, 255, 240)
DK_SQUARE  = (232, 200, 150)
LT_VISITED = (192, 192, 192)
DK_VISITED = (128, 128, 128)
GRID_COLOR = (107, 70, 51)
BACK_COLOR = (244, 228, 195)

PALETTE = [
    (0, 0, 128),   (0, 0, 255),   (0, 64, 64),   (0, 64, 192),  (0, 128, 0),
    (0, 128, 128), (0, 128, 192), (0, 128, 255),  (0, 192, 0),   (0, 192, 192),
    (0, 192, 255), (0, 255, 0),   (0, 255, 128),  (0, 255, 255), (128, 0, 0),
    (128, 0, 128), (128, 0, 192), (128, 0, 255),  (128, 64, 192),(128, 192, 64),
    (128, 192, 192),(128, 128, 0),(128, 128, 255),(128, 255, 0), (128, 255, 192),
    (128, 255, 255),(255, 0, 0),  (255, 0, 128),  (255, 0, 255), (255, 64, 64),
    (255, 64, 192),(255, 128, 0), (255, 128, 128),(255, 128, 255),(255, 255, 0),
]

ALLOWED_PIECES  = None
EXCLUDED_PIECES = {"bishop", "ferz", "dabbaba", "camel", "alfil", "threeleaper", "tripper"}
SLIDING_PIECES  = {"rook", "bishop", "queen"}


# ──────────────────────────────────────────────
#  Module-level utility functions
# ──────────────────────────────────────────────

def clamp(n: float, a: float, b: float) -> float:
    return max(a, min(b, n))


def normalize(units: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Normalize polyomino units so min x/y is (0, 0)."""
    if not units:
        return units
    minx = min(c[0] for c in units)
    miny = min(c[1] for c in units)
    return [(x - minx, y - miny) for (x, y) in units]


def rotate90(units: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Rotate a polyomino 90 degrees."""
    return normalize([(y, -x) for (x, y) in units])


def flip_horizontal(units: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Flip a polyomino horizontally."""
    return normalize([(-x, y) for (x, y) in units])


def format_time(total_seconds: int) -> str:
    total_seconds = max(0, total_seconds)
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _format_clock_seconds(seconds) -> str:
    if seconds is None:
        seconds = 0
    seconds = max(0, int(seconds))
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins}:{secs:02d}"


def _display_for_clock(clock_selected) -> str:
    if clock_selected == 0:
        return "infinity"
    return _format_clock_seconds(clock_selected)


def pick_contrast_font_color(rgb_tuple: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Black for light backgrounds, white for dark."""
    r, g, b = rgb_tuple
    luma = r * 0.299 + g * 0.587 + b * 0.114
    return (0, 0, 0) if luma > 192 else (255, 255, 255)


def get_globally_valid_pieces() -> List[str]:
    """Return piece names valid for any board size."""
    valid = []
    for piece in pk.PIECE_LIST:
        if ALLOWED_PIECES is not None and piece not in ALLOWED_PIECES:
            continue
        if EXCLUDED_PIECES and piece in EXCLUDED_PIECES:
            continue
        valid.append(piece)
    return valid


def compute_density_from_setting(density_setting: str) -> float:
    return {"high": 0.3, "medium": 0.2, "low": 0.1}.get(density_setting, 0.2)


def get_legal_moves_for_board(
        piece_name: str,
        x: int, y: int,
        cols: int, rows: int,
        visited: Set[Tuple[int, int]],
        forbidden: Optional[Set[Tuple[int, int]]] = None,
) -> List[Tuple[int, int]]:
    if forbidden is None:
        forbidden = set()
    legal: List[Tuple[int, int]] = []
    max_n = max(cols, rows)
    lower = piece_name.lower()
    if lower in SLIDING_PIECES:
        dirs: List[Tuple[int, int]] = []
        if lower == "rook":
            dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        elif lower == "bishop":
            dirs = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        elif lower == "queen":
            dirs = [(1, 0), (-1, 0), (0, 1), (0, -1),
                    (1, 1), (1, -1), (-1, 1), (-1, -1)]
        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            while 0 <= nx < cols and 0 <= ny < rows:
                if (nx, ny) not in visited and (nx, ny) not in forbidden:
                    legal.append((nx, ny))
                nx += dx
                ny += dy
    else:
        move_func = pk.get_move_func(piece_name)
        for mx, my in move_func(x, y, max_n):
            if (0 <= mx < cols and 0 <= my < rows
                    and (mx, my) not in visited and (mx, my) not in forbidden):
                legal.append((mx, my))
    return legal


def reveal_unit(
        board_model: BoardModel,
        puzzle_layout: List,
        gx: int, gy: int,
) -> Tuple[bool, Optional[int]]:
    """Check if a cell contains a puzzle unit. Mark as found and return (True, shape_id) if so."""
    for shape in puzzle_layout:
        if (gx, gy) in shape.puzzle_units and (gx, gy) not in shape.found_units:
            shape.found_units.add((gx, gy))
            board_model.set_cell(gx, gy, shape.color)
            return True, shape.id
    return False, None


def place_puzzle_layout(
        cols: int, rows: int,
        shapes_token: str,
        density: float,
        color_mode: str,
        seed: Optional[int] = None,
) -> Tuple[List, int]:
    """Deterministic polyomino shape placement using seeded RNG."""
    rng = random.Random(seed)
    used_seed = rng.getrandbits(64) if seed is None else seed
    rng = random.Random(used_seed)

    shape_prefix_map = {
        "monomino": "01", "domino": "02", "triomino": "03", "tetromino": "04",
        "pentomino": "05", "hexomino": "06", "heptomino": "07", "octomino": "08",
    }
    prefix = shape_prefix_map.get(shapes_token)

    if prefix:
        chosen = [(n, u) for n, u in pd.SAMPLE_POLYOMINOES.items() if n.startswith(prefix)]
        weights = None
    else:
        chosen = list(pd.SAMPLE_POLYOMINOES.items())
        group_sizes = {"01": 1, "02": 1, "03": 2, "04": 5, "05": 12, "06": 35, "07": 108, "08": 369}
        type_weights = {"01": 11, "02": 11, "03": 11, "04": 10, "05": 9, "05": 6, "07": 6, "08": 2}
        weights = [
            type_weights.get(n.split('-')[0], 1) / group_sizes.get(n.split('-')[0], 1)
            for n, _ in chosen
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

    target = math.ceil(cols * rows * density)
    occupancy: Set[Tuple[int, int]] = set()
    puzzle_layout: List[PuzzleShape] = []
    shape_id = 1
    max_total_attempts = 8000
    total_attempts = 0
    per_piece_attempts = 500
    occupied_count = 0

    while occupied_count < target and total_attempts < max_total_attempts:
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
            abs_units = {(try_gx + x, try_gy + y) for x, y in p.units}
            if abs_units & occupancy:
                continue
            occupancy.update(abs_units)
            shape = PuzzleShape(
                shape_id, name, abs_units, color, (try_gx, try_gy),
                orientation=f"rot={rotates},flip={p.units != normalize(units)}"
            )
            puzzle_layout.append(shape)
            shape_id += 1
            occupied_count += len(abs_units)
            break

    return puzzle_layout, used_seed


def validate_and_apply_codec(
        codec_text: str,
        menu_items: list,
        label_to_index: dict,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Validate codec and update menu items if valid. Returns (is_valid, params_or_none)."""
    try:
        params = decode_params(codec_text, polyomino_schema)
        for label in ("board", "shapes", "density", "colors"):
            idx = label_to_index.get(label)
            if idx is None:
                continue
            vals = menu_items[idx][1]
            val = params.get(label)
            if val in vals:
                menu_items[idx] = (menu_items[idx][0], vals, vals.index(val))
        return True, params
    except (KeyError, ValueError):
        return False, None


# ──────────────────────────────────────────────
#  Data classes
# ──────────────────────────────────────────────

class Polyomino:
    def __init__(
            self,
            units: List[Tuple[int, int]],
            color: Optional[Tuple[int, int, int]] = None,
            name: Optional[str] = None,
    ):
        self.units = normalize(units)
        self.name  = name or "poly"
        self.color = color or random.choice(PALETTE)

    def rotated(self) -> "Polyomino":
        return Polyomino(rotate90(self.units), color=self.color, name=self.name)

    def flipped(self) -> "Polyomino":
        return Polyomino(flip_horizontal(self.units), color=self.color, name=self.name)

    def bounding(self) -> Tuple[int, int]:
        if not self.units:
            return 0, 0
        return max(x for x, _ in self.units) + 1, max(y for _, y in self.units) + 1


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
        self.id            = shape_id
        self.name          = name
        self.puzzle_units  = set(puzzle_units)
        self.color         = color
        self.origin        = origin
        self.orientation   = orientation
        self.found_units: Set[Tuple[int, int]] = set()


# ──────────────────────────────────────────────
#  PolyominoController
# ──────────────────────────────────────────────

class PolyominoController(BaseGameController):
    """
    Game controller for Polyominoes v0.2.
    Manages game state, move validation, scoring, and rendering.
    Inherits common functionality from BaseGameController.
    """

    def __init__(
            self,
            board_model: BoardModel,
            board_renderer: BoardRenderer,
            menu_items: list,
            label_to_index: dict,
            font: pygame.font.Font,
            font_large: pygame.font.Font,
            base_dir: str,
    ):
        super().__init__(
            board_model, board_renderer, menu_items, label_to_index,
            font, font_large, base_dir, polyomino_schema,
        )

        self.markers_dir = os.path.join(base_dir, "assets", "markers")

        # Puzzle layout state
        self.puzzle_layout: Optional[List[PuzzleShape]] = None
        self.used_seed:     Optional[int]               = None
        self.total_puzzle_units   = 0
        self.found_puzzle_units   = 0
        self.completed_shape_count = 0

        # Mode flags (override base defaults where needed)
        self.guide_mode_active = True
        self.track_mode_active = True

        # Clock compatibility (for CSV; uses base class clock_elapsed)
        self.game_time_seconds: int = 0

        # Per-move clock tracking
        self.move_start_time: Optional[float] = None

        # Visual effects
        self.active_effect: Optional[Dict[str, Any]] = None

        # Scoring
        self.endgame_reason:    Optional[str]      = None
        self.endgame_scores:    Dict[str, Any]     = {}
        self.challenge_rating:  float              = 1.0
        self.completion_score:  int                = 0
        self.is_piece_playable: bool               = True
        self.min_board_size:    Optional[int]      = None
        self.mobility_rating:   int                = 0
        self.agility_rating:    int                = 0
        self.unit_factor:       int                = 1000
        self.shape_factor:      int                = 1000

        # Endgame display
        self.final_legal_moves:       List[Tuple[int, int]] = []
        self.last_nonempty_legal_moves: List[Tuple[int, int]] = []

        # Menu preview
        self.preview_layout: Optional[List[PuzzleShape]] = None

        # Blind draw / retry
        self.blind_draw_active:   bool           = False
        self.previous_game_codec: Optional[str]  = None

        # Star images
        self.star_filled:  Optional[pygame.Surface] = None
        self.star_empty:   Optional[pygame.Surface] = None

        # Menu preview cache
        self.menu_preview_cache = None

        self._load_star_images()

        # Initial menu state
        self.update_playability()
        self.update_challenge_rating()
        c = (self.board_model.cols - 1) // 2
        self.player_pos = (c, c)
        self.generate_menu_preview()

    #  Abstract method implementations                                    #

    def _is_per_move_mode(self) -> bool:
        """Return True when the clock is in per-move countdown mode."""
        clock_sel = self.get_selection("clock") if "clock" in self.label_to_index else 0
        time_per  = self.get_selection("time per") if "time per" in self.label_to_index else "game"
        return clock_sel > 0 and time_per == "move"

    def _remaining_time(self) -> Optional[int]:
        """Return seconds remaining, or None for infinity display."""
        clock_sel = self.get_selection("clock") if "clock" in self.label_to_index else 0
        if clock_sel == 0:
            return None
        if self._is_per_move_mode():
            if self.move_start_time is None:
                return int(clock_sel)
            elapsed = time.time() - self.move_start_time
            return max(0, math.ceil(clock_sel - elapsed))
        elapsed = self.final_elapsed if self.game_state == GameState.ENDGAME else self.clock_elapsed
        return max(0, int(clock_sel) - int(elapsed))

    def _get_min_board_size(self, piece_name: str) -> int:
        return BOARD_MIN  # Polyomino doesn't have piece-specific minimums

    def _get_encode_params(self) -> Dict[str, Any]:
        return {
            "board":   self.get_selection("board"),
            "shapes":  self.get_selection("shapes"),
            "density": self.get_selection("density"),
            "colors":  self.get_selection("colors"),
        }

    def _validate_codec(self, codec_text: str) -> Tuple[bool, Optional[Dict]]:
        return validate_and_apply_codec(codec_text, self.menu_items, self.label_to_index)

    def _game_specific_start_setup(self, seed: Optional[int] = None) -> bool:
        """Generate puzzle layout; player_pos stays None until commit_start_square()."""
        import polyomino_difficulty as pd_diff

        sel           = self.get_current_selections()
        board_size    = int(sel["board"])
        density       = compute_density_from_setting(sel["density"])
        color_mode    = sel["colors"]
        shapes_choice = sel["shapes"]
        piece_name    = sel["piece"]

        ratings = pr.get_piece_ratings(piece_name, board_size, shapes_choice)
        self.mobility_rating = ratings['mobility_rating']
        self.agility_rating  = ratings['agility_rating']
        self.challenge_rating = pd_diff.calculate_challenge_rating(
            sel, self.mobility_rating, self.agility_rating,
            blind_mode=self.blind_draw_active)

        self.puzzle_layout, self.used_seed = place_puzzle_layout(
            board_size, board_size, shapes_choice, density, color_mode, seed=seed)

        if not self.puzzle_layout:
            return False

        self.total_puzzle_units    = sum(len(s.puzzle_units) for s in self.puzzle_layout)
        self.found_puzzle_units    = 0
        self.completed_shape_count = 0
        self.completion_score      = 0
        self.endgame_scores        = {}
        self.endgame_reason        = None
        self.final_legal_moves     = []
        self.last_nonempty_legal_moves = []

        # player_pos stays None — set in commit_start_square()
        self.player_pos = None
        self.move_count = 0
        return True

    def _validate_move(self, target: Tuple[int, int]) -> bool:
        return target in self.legal_moves

    def _game_specific_make_move(self, target: Tuple[int, int]) -> bool:
        self.move_count += 1
        gx, gy = target

        is_new_unit, shape_id = reveal_unit(
            self.board_model, self.puzzle_layout, gx, gy)
        if is_new_unit and shape_id is not None:
            self.process_found_unit(shape_id, (gx, gy))
        elif not is_new_unit:
            parity = (gx + (self.board_model.rows - 1 - gy)) % 2
            vcolor = DK_VISITED if parity == 0 else LT_VISITED
            self.board_model.set_cell(gx, gy, vcolor)

        # Reset per-move clock after each successful move
        if self._is_per_move_mode():
            self.move_start_time = time.time()

        return True

    def _check_endgame_conditions(self) -> Optional[str]:
        # Endgame detected in update() via go_to_endgame() for CSV/scoring
        return None

    def _capture_game_state(self) -> Dict[str, Any]:
        return {
            "pos":          self.player_pos,
            "visited":      self.visited.copy(),
            "visited_moves": self.visited_moves.copy(),
            "move_count":   self.move_count,
            "legal_moves":  list(self.legal_moves),
            "grid":         dict(self.board_model.grid),
            "found_units_per_shape": {
                s.id: set(s.found_units) for s in (self.puzzle_layout or [])
            },
            "found_puzzle_units":    self.found_puzzle_units,
            "completed_shape_count": self.completed_shape_count,
            "completion_score":      self.completion_score,
        }

    def _restore_game_state(self, state: Dict[str, Any]) -> None:
        self.player_pos    = state["pos"]
        self.visited       = state["visited"].copy()
        self.visited_moves = state["visited_moves"].copy()
        self.move_count    = state.get("move_count", len(state["visited_moves"]))
        self.legal_moves   = list(state.get("legal_moves", []))

        self.board_model.grid.clear()
        self.board_model.grid.update(state["grid"])
        if self.puzzle_layout:
            for shape in self.puzzle_layout:
                shape.found_units = set(
                    state["found_units_per_shape"].get(shape.id, set()))

        self.found_puzzle_units    = state.get("found_puzzle_units", 0)
        self.completed_shape_count = state.get("completed_shape_count", 0)
        self.completion_score      = state.get("completion_score", 0)

        # Recalculate legal moves and hint degrees
        self._update_legal_moves()
        if self.hint_mode_active:
            self._calculate_hint_degrees()
        else:
            self.hint_degrees = {}

    def _update_legal_moves(self) -> None:
        if not self.player_pos:
            self.legal_moves = []
            return
        piece_name = self.get_selection("piece")
        cols, rows = self.board_model.cols, self.board_model.rows
        self.legal_moves = get_legal_moves_for_board(
            piece_name, *self.player_pos, cols, rows, self.visited)

    def _calculate_hint_degrees(self) -> None:
        if not self.player_pos or self.game_state != GameState.INGAME:
            self.hint_degrees = {}
            return

        piece = self.get_current_selections()["piece"]
        cols, rows = self.board_model.cols, self.board_model.rows

        reachable = get_legal_moves_for_board(
            piece, self.player_pos[0], self.player_pos[1], cols, rows, self.visited)

        raw: Dict[Tuple[int, int], int] = {}
        for sq in reachable:
            onward = get_legal_moves_for_board(
                piece, sq[0], sq[1], cols, rows, self.visited | {sq})
            deg = len(onward)
            if deg >= 0:
                raw[sq] = deg

        lower = piece.lower()
        if lower in SLIDING_PIECES and raw:
            sorted_vals = sorted(set(raw.values()))
            cutoff      = set(sorted_vals[:2])
            self.hint_degrees = {sq: d for sq, d in raw.items() if d in cutoff}
        else:
            self.hint_degrees = dict(raw)

        if not self.hint_degrees:
            self.hint_mode_active  = False

    def _render_game_specific_board(self, screen: pygame.Surface) -> None:
        """Draw board overlays: shapes, visited, arrows, hints, player piece."""
        pass  # All drawing is handled in _render_board_area() below

    def _render_game_specific_stats(
        self, screen: pygame.Surface, stats_panel: UIPanel
    ) -> None:
        """Stats are rendered in _render_right_panel() for this game."""
        pass

    def _build_buttons(self) -> None:
        f = self.font
        self.buttons: Dict[str, Button] = {
            "start":       Button(pygame.Rect(0,0,0,0), "start",
                                  f, (255,255,255), (92,192,92),   self.start_flow),
            "blind_draw":  Button(pygame.Rect(0,0,0,0), "blind draw",
                                  f, (255,255,255), (128,32,64),   self.start_blind_draw_flow),
            "enter_code":  Button(pygame.Rect(0,0,0,0), "enter share code",
                                  f, (255,255,255), (224,0,96),    self.toggle_codec_input),
            "copy_code":   Button(pygame.Rect(0,0,0,0), "copy share code",
                                  f, (255,255,255), (224,0,96),    self.copy_code_to_clipboard),
            "guide_mode":  Button(pygame.Rect(0,0,0,0), "show move guide",
                                  f, (255,255,255), (128,64,255),  self.toggle_guide_mode),
            "track_mode":  Button(pygame.Rect(0,0,0,0), "show move track",
                                f, (255,255,255), (255,92,128),  self.toggle_track_mode),
            "hint_mode":   Button(pygame.Rect(0,0,0,0), "show move degrees",
                                  f, (255,255,255), (255,128,96),  self.toggle_hint_mode),
            "undo_mode":   Button(pygame.Rect(0,0,0,0), "undo last move",
                                  f, (255,255,255), (64,128,255),  self.undo_move),
            "resign":      Button(pygame.Rect(0,0,0,0), "resign",
                                  f, (255,255,255), (107,70,51),    self.resign_game),
            "retry":       Button(pygame.Rect(0,0,0,0), "retry",
                                  f, (255,255,255), (92,192,92),   self.retry_last_game),
            "replay_mode": Button(pygame.Rect(0,0,0,0), "show replay",
                                  f, (255,255,255), (64,128,255),  self.toggle_replay_mode),
            "replay_prev": Button(pygame.Rect(0,0,0,0), "-",
                                  f, (255,255,240), (64,128,255),  lambda: self.navigate_replay(-1)),
            "replay_next": Button(pygame.Rect(0,0,0,0), "+",
                                  f, (255,255,240), (64,128,255),  lambda: self.navigate_replay(1)),
            "reveal":      Button(pygame.Rect(0,0,0,0), "show all units",
                                  f, (255,255,255), (255,128,96),  self.toggle_reveal_all_shapes),
            "new_game":    Button(pygame.Rect(0,0,0,0), "new game",
                                  f, (255,255,255), (32,128,96),   self.new_game_flow),
            "peek_mode":   Button(pygame.Rect(0,0,0,0), "peek",
                                  f, (255,255,240), DK_SQUARE,     self.toggle_peek),
            "exit":        Button(pygame.Rect(0,0,0,0), "exit",
                                  f, (255,255,255), (255,0,0),     self.quit_game),
        }

    #  Override start_game() for two-phase start (WAITING state)         #

    def start_game(self, use_seed: Optional[int] = None) -> None:
        """Override to handle two-phase start: generate puzzle → WAITING for start square."""
        piece      = self.get_selection("piece")
        board_size = self.get_selection("board")

        min_board = self._get_min_board_size(piece)
        if board_size < min_board:
            self.error_message = f"{piece} needs board >= {min_board}"
            self.error_timer   = pygame.time.get_ticks() + 3000
            return

        # Resolve seed
        if use_seed is not None:
            seed = use_seed
        elif self.seed_mode_active:
            code_text = self.codec_input.get_text()
            ok, params = self._validate_codec(code_text)
            if ok and params:
                seed = params["seed"]
            else:
                self.error_message = "Invalid share code"
                self.error_timer   = pygame.time.get_ticks() + 3000
                return
        else:
            seed = random.randint(0, 2 ** 63 - 1)

        self.last_puzzle_seed = seed

        # Delegate game-specific setup
        if not self._game_specific_start_setup(seed):
            self.error_message = "Failed to generate – try different settings"
            self.error_timer   = pygame.time.get_ticks() + 3000
            return

        # Sync board model
        n = self.get_selection("board")
        self.board_model.cols = n
        self.board_model.rows = n
        self.board_model.clear()

        # Encode puzzle code using seed stored in used_seed (from place_puzzle_layout)
        try:
            self.puzzle_code = encode_params(self._get_encode_params(), self.schema, self.used_seed)
        except Exception:
            self.puzzle_code = ""

        self.previous_game_codec = self.puzzle_code

        # Reset common game state
        self.end_state          = None
        self.clock_start_time   = None
        self.paused_elapsed     = 0.0
        self.clock_elapsed      = 0
        self.final_elapsed      = 0
        self.game_time_seconds  = 0
        self.move_start_time    = None
        self.replay_states      = []  # Empty until commit_start_square()
        self.replay_index       = 0
        self.replay_mode_active = False
        self.peek_mode_visible  = False
        self.reveal_mode_active = False
        self.hint_degrees       = {}
        self.hint_mode_active   = False

        # Clear visited squares from previous game (prevents gray squares in WAITING state)
        self.visited.clear()
        self.visited_moves.clear()
        self.legal_moves.clear()

        # Transition to WAITING (not INGAME — player must choose start square)
        self.game_state = GameState.WAITING

    #  Phase 2: commit the starting square → INGAME                      #

    def commit_start_square(self, pos_gx: int, pos_gy: int) -> None:
        """Player selected starting square; finalise setup and enter INGAME."""
        self.player_pos  = (pos_gx, pos_gy)
        self.visited     = {(pos_gx, pos_gy)}
        self.visited_moves = {(pos_gx, pos_gy): 0}
        self.move_count  = 0

        # Process any polyomino shape at starting position
        is_new_unit, shape_id = reveal_unit(
            self.board_model, self.puzzle_layout, pos_gx, pos_gy)
        if is_new_unit and shape_id is not None:
            self.process_found_unit(shape_id, (pos_gx, pos_gy))
        elif not is_new_unit:
            parity = (pos_gx + (self.board_model.rows - 1 - pos_gy)) % 2
            vcolor = DK_VISITED if parity == 0 else LT_VISITED
            self.board_model.set_cell(pos_gx, pos_gy, vcolor)

        self._update_legal_moves()
        if self.legal_moves:
            self.last_nonempty_legal_moves = list(self.legal_moves)
        if self.hint_mode_active:
            self._calculate_hint_degrees()

        # Capture initial state for replay / undo
        self.replay_states = [self._capture_game_state()]

        # In per-move mode, start the per-move countdown now
        if self._is_per_move_mode():
            self.move_start_time = time.time()

        # Transition to INGAME (clock starts on first move via make_move())
        self.game_state = GameState.INGAME

    #  Overrides with polyomino-specific behaviour                        #

    def toggle_codec_input(self) -> None:
        super().toggle_codec_input()
        ci = self.codec_input
        if ci:
            ci.text       = ""
            ci.cursor_pos = 0
            ci.active     = self.seed_mode_active

    def resign_game(self) -> None:
        self.go_to_endgame('resignation')

    def new_game(self) -> None:
        super().new_game()
        self.blind_draw_active = False
        self.puzzle_layout     = None
        self.total_puzzle_units   = 0
        self.found_puzzle_units   = 0
        self.completed_shape_count = 0
        self.endgame_reason       = None
        self.endgame_scores       = {}
        self.preview_layout       = None
        self.menu_preview_cache   = None
        self.final_legal_moves    = []
        self.last_nonempty_legal_moves = []
        self.game_time_seconds    = 0
        self.move_start_time      = None

        # Clear board and game state (player position, visited squares, found units)
        self.player_pos = None
        self.board_model.clear()
        self.visited.clear()
        self.visited_moves.clear()
        self.legal_moves.clear()

        # Set preview piece to center for menu mode preview
        c = (self.board_model.cols - 1) // 2
        self.player_pos = (c, c)
        self.legal_moves = get_legal_moves_for_board(
            self.get_current_selections()["piece"],
            self.player_pos[0], self.player_pos[1],
            self.board_model.cols, self.board_model.rows,
            set()
        )

        self.generate_menu_preview()

    #  Wrappers that preserve the old API for buttons / external callers  #

    def copy_puzzle_code_to_clipboard(self) -> None:
        self.copy_code_to_clipboard()

    def new_game_flow(self) -> None:
        self.new_game()

    def retry_last_game(self) -> None:
        if self.previous_game_codec:
            self._retry_from_codec(self.previous_game_codec)
        elif self.last_puzzle_seed is not None:
            self.start_game(use_seed=self.last_puzzle_seed)

    #  Per-frame update                                                    #

    def update(self, dt: int) -> None:
        """Call once per frame with milliseconds elapsed."""
        # Base class handles codec_input, copy_clicked, clock_elapsed
        # BUT we intercept clock timeout to use go_to_endgame() instead
        self.codec_input.update(dt)

        if self.copy_clicked and pygame.time.get_ticks() > self.copy_timer:
            self.copy_clicked = False

        if self.game_state == GameState.INGAME:
            if self.clock_start_time is not None:
                self.clock_elapsed = int(
                    self.paused_elapsed + (time.time() - self.clock_start_time))
            self.game_time_seconds = self.clock_elapsed

            # Per-move timeout check
            if self._is_per_move_mode() and self.move_start_time is not None:
                clock_sel = self.get_selection("clock") if "clock" in self.label_to_index else 0
                if time.time() - self.move_start_time >= clock_sel:
                    self.go_to_endgame("time's up")
                    return

            # Per-game clock timeout → endgame
            elif self._clock_has_expired():
                self.final_elapsed = self.clock_elapsed
                self.go_to_endgame("time's up")
                return

            # All shapes found
            if (self.puzzle_layout is not None
                    and self.found_puzzle_units >= self.total_puzzle_units):
                self.go_to_endgame('all shapes found')

            # No legal moves
            elif not self.legal_moves:
                self.go_to_endgame('no legal moves')

    #  Event handling                                                      #

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Process one pygame event.
        Returns False if the game should quit.
        """
        if event.type == pygame.QUIT:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.game_state == GameState.INGAME:
                    self.resign_game()
                elif self.game_state == GameState.ENDGAME:
                    self.new_game_flow()
                elif self.game_state == GameState.WAITING:
                    self.new_game_flow()
                else:
                    return False


        # Replay navigation with arrow keys
        if event.type == pygame.KEYDOWN and self.replay_mode_active:
            if event.key == pygame.K_LEFT:
                self.navigate_replay(-1)
            elif event.key == pygame.K_RIGHT:
                self.navigate_replay(1)

        # Window focus (clock pause/resume)
        if event.type == pygame.ACTIVEEVENT:
            self.handle_window_focus(
                getattr(event, "state", 0),
                getattr(event, "gain",  0),
            )

        # Codec text input
        if self.game_state == GameState.MENU and self.seed_mode_active:
            if self.codec_input.handle_event(event):
                code = self.codec_input.get_text()
                if len(code.replace("-", "")) >= 16:
                    is_valid, decoded_params = validate_and_apply_codec(
                        code, self.menu_items, self.label_to_index)
                    if is_valid:
                        self.resize_board_if_needed()
                        self.update_playability()
                        self.update_challenge_rating()
                        self.generate_menu_preview()

        # Dispatch to all buttons
        for btn in self.buttons.values():
            btn.handle_event(event)

        # Mouse click
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            clicked_on_ui = False

            if self.game_state == GameState.MENU:
                for key, rect in self.widget_rects.items():
                    if rect.collidepoint(mx, my):
                        clicked_on_ui = True
                        action, idx = key
                        label, values, cur_idx = self.menu_items[idx]

                        if action == "minus":
                            self.menu_items[idx] = (label, values, (cur_idx - 1) % len(values))
                        elif action == "plus":
                            self.menu_items[idx] = (label, values, (cur_idx + 1) % len(values))

                        if self.seed_mode_active and len(self.codec_input.get_text().replace("-", "")) >= 16:
                            is_valid, decoded_params = validate_and_apply_codec(
                                self.codec_input.get_text(), self.menu_items, self.label_to_index)
                            if is_valid:
                                self.resize_board_if_needed()
                                self.update_playability()
                                self.update_challenge_rating()
                                self.generate_menu_preview()
                                break

                        if label == "board":
                            self.resize_board_if_needed()
                            self.update_playability()
                            self.update_challenge_rating()
                            self.generate_menu_preview()
                        elif label not in ("piece", "clock", "time per"):
#                        elif label != "piece":
                            self.update_playability()
                            self.update_challenge_rating()
                            self.generate_menu_preview()
                        else:
                            self.update_playability()
                            self.update_challenge_rating()
                        break

            if clicked_on_ui:
                return True

            if self.game_state == GameState.MENU:
                grid_pos = self.board_renderer.to_grid(mx, my)
                if grid_pos:
                    self.player_pos = grid_pos

            elif self.game_state == GameState.WAITING:
                grid_pos = self.board_renderer.to_grid(mx, my)
                if grid_pos:
                    self.commit_start_square(*grid_pos)

            elif self.game_state == GameState.INGAME:
                grid_pos = self.board_renderer.to_grid(mx, my)
                if grid_pos:
                    self.make_move(grid_pos)

        return True

    #  Helpers                                                             #

    def get_current_selections(self) -> Dict[str, Any]:
        return {label: vals[cur] for label, vals, cur in self.menu_items}

    def update_hint_degrees_if_active(self) -> None:
        if self.hint_mode_active and self.player_pos and self.game_state == GameState.INGAME:
            self._calculate_hint_degrees()


    #  Game actions

    def generate_menu_preview(self) -> None:
        """Generate preview layout for menu screen."""
        sel           = self.get_current_selections()
        board_size    = int(sel["board"])
        density       = compute_density_from_setting(sel["density"])
        color_mode    = sel["colors"]
        shapes_choice = sel["shapes"]
        self.preview_layout, _ = place_puzzle_layout(
            board_size, board_size, shapes_choice, density, color_mode)

    def resize_board_if_needed(self) -> None:
        """Resize board model if board size setting changed."""
        new_size = int(self.get_current_selections()["board"])
        if self.board_model.cols != new_size or self.board_model.rows != new_size:
            old_pos  = self.player_pos
            old_cols = self.board_model.cols
            old_rows = self.board_model.rows
            self.board_model = BoardModel(new_size, new_size)
            self.board_renderer.model = self.board_model
            if old_pos and old_cols > 1 and old_rows > 1:
                nx = int(round(old_pos[0] / (old_cols - 1) * (new_size - 1)))
                ny = int(round(old_pos[1] / (old_rows - 1) * (new_size - 1)))
                self.player_pos = (max(0, min(nx, new_size - 1)),
                                   max(0, min(ny, new_size - 1)))
            else:
                c = (new_size - 1) // 2
                self.player_pos = (c, c)

    def update_challenge_rating(self) -> None:
        """Update challenge rating based on current selections."""
        import polyomino_difficulty as pd_diff
        if self.blind_draw_active:
            self.challenge_rating = 1.0
            return
        if not self.is_piece_playable:
            self.challenge_rating = 0.0
            return
        sel = self.get_current_selections()
        ratings = pr.get_piece_ratings(sel.get("piece"), sel.get("board"), sel.get("shapes"))
        self.challenge_rating = pd_diff.calculate_challenge_rating(
            sel, ratings['mobility_rating'], ratings['agility_rating'])

    def update_playability(self) -> None:
        """Check if current piece is playable on current board size."""
        sel = self.get_current_selections()
        status = pr.assess_piece_playability(sel["piece"], sel["board"])
        self.is_piece_playable = (status != 'choose a larger board')
        if not self.is_piece_playable:
            self.min_board_size = next(
                (n for n in range(sel["board"] + 1, BOARD_MAX + 1)
                 if pr.assess_piece_playability(sel["piece"], n) != 'choose a larger board'),
                None,
            )
        else:
            self.min_board_size = None

    def go_to_menu(self) -> None:
        """Reset to menu state."""
        self.blind_draw_active = False
        self.copy_clicked      = False
        self.game_state        = GameState.MENU
        self.puzzle_layout     = None
        self.total_puzzle_units   = 0
        self.found_puzzle_units   = 0
        self.completed_shape_count = 0
        self.completion_score     = 0
        self.clock_start_time     = None
        self.clock_elapsed        = 0
        self.game_time_seconds    = 0
        self.move_start_time      = None
        self.endgame_scores       = {}
        self.visited_moves.clear()
        self.replay_states        = []
        self.replay_mode_active   = False
        self.visited.clear()
        self.legal_moves.clear()
        self.final_legal_moves.clear()
        self.last_nonempty_legal_moves.clear()
        self.peek_mode_visible    = False
        self.reveal_mode_active   = False
        self.hint_mode_active     = False
        self.hint_degrees         = {}

        sel           = self.get_current_selections()
        current_board = int(sel["board"])
        valid_pieces  = get_globally_valid_pieces()
        current_piece = sel["piece"]

        piece_idx = self.label_to_index["piece"]
        piece_pos = valid_pieces.index(current_piece) if current_piece in valid_pieces else 0
        self.menu_items[piece_idx] = (self.menu_items[piece_idx][0], valid_pieces, piece_pos)

        self.update_playability()
        self.update_challenge_rating()

        old_pos  = self.player_pos
        old_cols = self.board_model.cols
        old_rows = self.board_model.rows
        self.board_model = BoardModel(current_board, current_board)
        self.board_renderer.model = self.board_model

        if old_pos and old_cols and old_rows and old_cols > 1 and old_rows > 1:
            nx = int(round(old_pos[0] / (old_cols - 1) * (self.board_model.cols - 1)))
            ny = int(round(old_pos[1] / (old_rows - 1) * (self.board_model.rows - 1)))
            self.player_pos = (
                max(0, min(nx, self.board_model.cols - 1)),
                max(0, min(ny, self.board_model.rows - 1)),
            )
        else:
            c = (self.board_model.cols - 1) // 2
            self.player_pos = (c, c)

        self.puzzle_code      = ""
        self.seed_mode_active = False

        ci = self.codec_input
        if ci:
            ci.text       = ""
            ci.cursor_pos = 0
            ci.active     = False

        self.generate_menu_preview()

    def update_completion_counters(self) -> None:
        if self.puzzle_layout is None:
            self.found_puzzle_units    = 0
            self.completed_shape_count = 0
        else:
            self.found_puzzle_units    = sum(len(s.found_units) for s in self.puzzle_layout)
            self.completed_shape_count = sum(
                1 for s in self.puzzle_layout if len(s.found_units) == len(s.puzzle_units))

    def start_flow(self, force_seed: Optional[int] = None) -> None:
        """Start a new game with current settings (calls start_game)."""
        if force_seed is not None:
            self.start_game(use_seed=force_seed)
        else:
            self.start_game()

    def start_blind_draw_flow(self) -> None:
        """Start a game with randomised settings."""
        self.blind_draw_active = True
        self.copy_clicked      = False
        piece_name = self.get_current_selections()["piece"]
        for i, (label, blind_values, _) in enumerate(self.menu_items):
            if label in ("board", "shapes", "density", "colors"):
                if label == "board":
                    while True:
                        new_idx = random.randint(0, len(blind_values) - 1)
                        if pr.assess_piece_playability(
                                piece_name, blind_values[new_idx]) != 'choose a larger board':
                            self.menu_items[i] = (label, blind_values, new_idx)
                            break
                else:
                    self.menu_items[i] = (label, blind_values, random.randint(0, len(blind_values) - 1))
        self.start_game()

    def process_found_unit(
            self, shape_id: int, found_grid_pos: Tuple[int, int]) -> None:
        """Process a found puzzle unit and update shape completion."""
        self.update_completion_counters()
        total_shapes = len(self.puzzle_layout) if self.puzzle_layout else 0
        self.completion_score = self._calculate_completion_score(
            self.found_puzzle_units, self.total_puzzle_units,
            self.completed_shape_count, total_shapes)

        shape_obj = next((s for s in self.puzzle_layout if s.id == shape_id), None)
        if shape_obj:
            center_px, center_py = self.board_renderer.to_pixel(*found_grid_pos)
            cs = self.board_renderer.cell_size
            self.active_effect = {
                "units":      [(0, 0)],
                "color":      shape_obj.color,
                "center_pos": (center_px + cs // 2, center_py + cs // 2),
                "size":       cs * 1.5,
                "expires":    pygame.time.get_ticks() + 500,
            }

    def _calculate_completion_score(
            self, found_units: int, total_units: int,
            completed_shapes: int, total_shapes: int) -> int:
        if total_units <= 0 or total_shapes <= 0:
            return 0
        return round(
            (found_units / total_units) * self.unit_factor
            + (completed_shapes / total_shapes) * self.shape_factor)

    def calculate_endgame_scores(self) -> None:
        final = round(self.completion_score * self.challenge_rating)
        self.endgame_scores = {
            "completion_score":            self.completion_score,
            "challenge_rating_multiplier": self.challenge_rating,
            "final_score":                 final,
        }

    def write_endgame_stats_to_csv(self, stats_reason: str) -> None:
        stats_filename = os.path.join(self.base_dir, "polyominoes", "polyomino_stats.csv")
        sel          = self.get_current_selections()
        game_mode    = "blind draw" if self.blind_draw_active else "regular"
        total_shapes = len(self.puzzle_layout) if self.puzzle_layout else 0
        total_moves  = len(self.visited)

        data = {
            "puzzle_code":   self.puzzle_code or "",
            "game_mode":     game_mode,
            "piece_name":    sel["piece"],
            "board_size":    sel["board"],
            "shape_type":    sel["shapes"],
            "density":       sel["density"],
            "colors":        sel["colors"],
            "mobility_rating":  self.mobility_rating,
            "agility_rating":   self.agility_rating,
            "challenge_rating": self.challenge_rating,
            "endgame_reason":   stats_reason,
            "units_found":      self.found_puzzle_units,
            "total_units":      self.total_puzzle_units,
            "unit_completion_ratio": (
                self.found_puzzle_units / self.total_puzzle_units
                if self.total_puzzle_units > 0 else 0.0),
            "shapes_completed": self.completed_shape_count,
            "total_shapes":     total_shapes,
            "shape_completion_ratio": (
                self.completed_shape_count / total_shapes
                if total_shapes > 0 else 0.0),
            "total_moves":      total_moves,
            "completion_score": self.endgame_scores.get("completion_score", 0),
            "final_score":      self.endgame_scores.get("final_score", 0),
            "elapsed_time_seconds": self.final_elapsed,
        }

        file_exists = os.path.isfile(stats_filename)
        fieldnames  = list(data.keys())

        try:
            with open(stats_filename, 'r+', newline='') as f:
                reader = csv.reader(f)
                try:
                    header = next(reader)
                    for field in fieldnames:
                        if field not in header:
                            header.append(field)
                    fieldnames = header
                except StopIteration:
                    pass
        except FileNotFoundError:
            pass

        with open(stats_filename, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists or os.path.getsize(stats_filename) == 0:
                writer.writeheader()
            writer.writerow(data)

    def go_to_endgame(self, end_reason: str) -> None:
        """Transition to ENDGAME state."""
        import polyomino_difficulty as pd_diff

        if self.game_state != GameState.INGAME:
            return

        if end_reason == 'no legal moves':
            self.final_legal_moves = list(self.last_nonempty_legal_moves)
        else:
            self.final_legal_moves = list(self.legal_moves)

        if self.clock_start_time is not None:
            self.final_elapsed = int(
                self.paused_elapsed + (time.time() - self.clock_start_time))
        else:
            self.final_elapsed = self.clock_elapsed

        self.game_state        = GameState.ENDGAME
        self.endgame_reason    = end_reason
        self.peek_mode_visible = False

        if self.blind_draw_active:
            self.challenge_rating = pd_diff.calculate_challenge_rating(
                self.get_current_selections(),
                self.mobility_rating, self.agility_rating, blind_mode=False)

        self.calculate_endgame_scores()
        self.write_endgame_stats_to_csv(end_reason)

        self.hint_mode_active  = False
        self.hint_degrees      = {}

    def toggle_reveal_all_shapes(self) -> None:
        if self.game_state == GameState.ENDGAME:
            self.reveal_mode_active = not self.reveal_mode_active

    def _retry_from_codec(self, codec: str) -> None:
        try:
            params = decode_params(codec, polyomino_schema)
        except (KeyError, ValueError):
            print("Error: Invalid previous game codec, retry not possible.")
            self.go_to_menu()
            return
        for label, idx in self.label_to_index.items():
            vals = self.menu_items[idx][1]
            if label in params and params[label] in vals:
                self.menu_items[idx] = (label, vals, vals.index(params[label]))
        self.start_game(use_seed=params["seed"])

    #  rendering helpers                                                   #

    def _draw_peek_thumbnail(
            self, screen: pygame.Surface,
            left_panel: UIPanel, line_height: int) -> None:
        """Draw peek-mode puzzle thumbnail inside BUTTON_PANEL."""
        if not (self.puzzle_layout and self.peek_mode_visible):
            return
        cols, rows = self.board_model.cols, self.board_model.rows
        if cols < 1 or rows < 1:
            return

        button_bounds = left_panel.get_bounds("BUTTON_PANEL")
        thumb_area_y  = left_panel.get_line_y("BUTTON_PANEL", 0, line_height)
        thumb_area    = pygame.Rect(
            button_bounds['left'] + UI_SPACE,
            thumb_area_y,
            button_bounds['width'] - UI_SPACE * 2,
            button_bounds['bottom'] - (thumb_area_y + UI_SPACE * 3),
        )

        max_cell = min(
            thumb_area.width  // cols if cols else 1,
            thumb_area.height // rows if rows else 1,
        )
        if max_cell < 2:
            return

        tw = cols * max_cell
        th = rows * max_cell
        tx = thumb_area.left + (thumb_area.width  - tw) // 2
        ty = thumb_area.top  + (thumb_area.height - th) // 2

        pygame.draw.rect(screen, DK_SQUARE, (tx - 2, ty - 2, tw + 4, th + 4))
        for shape in self.puzzle_layout:
            for gx, gy in shape.puzzle_units:
                pygame.draw.rect(screen, shape.color,
                                 (tx + gx * max_cell + 1,
                                  ty + gy * max_cell + 1,
                                  max_cell - 1, max_cell - 1))

    def _render_board_area(self, screen: pygame.Surface) -> None:
        """Draw board contents (preview, cells, visited squares, arrows, piece)."""
        cs = self.current_cell_size

        # MENU: show preview layout
        if self.game_state == GameState.MENU and self.preview_layout:
            for shape in self.preview_layout:
                for gx, gy in shape.puzzle_units:
                    px, py = self.board_renderer.to_pixel(gx, gy)
                    pygame.draw.rect(screen, shape.color,
                                     (px + 1, py + 1, cs - 1, cs - 1))

        # Reveal mode: show all puzzle shapes
        if self.reveal_mode_active and self.puzzle_layout:
            for shape in self.puzzle_layout:
                for gx, gy in shape.puzzle_units:
                    px, py = self.board_renderer.to_pixel(gx, gy)
                    pygame.draw.rect(screen, shape.color,
                                     (px + 1, py + 1, cs - 1, cs - 1))

        self.board_renderer.draw_cells(screen)
        self.board_renderer.draw_grid_lines(screen)

        # Flash effect for newly found units
        if self.active_effect:
            if pygame.time.get_ticks() < self.active_effect["expires"]:
                size   = self.active_effect["size"]
                color  = self.active_effect["color"]
                cx, cy = self.active_effect["center_pos"]
                for x, y in self.active_effect["units"]:
                    pygame.draw.rect(screen, color, (
                        cx - size / 2 + x * size,
                        cy - size / 2 + y * size,
                        size - 2, size - 2))
            else:
                self.active_effect = None

        # Determine display state (use replay snapshot when replaying)
        if (self.game_state == GameState.ENDGAME
                and self.replay_mode_active and self.replay_states):
            snap           = self.replay_states[self.replay_index]
            disp_pos       = snap["pos"]
            disp_visited   = snap["visited"]
            disp_vis_moves = snap["visited_moves"]
        else:
            disp_pos       = self.player_pos
            disp_visited   = self.visited
            disp_vis_moves = self.visited_moves

        # Draw visited squares with optional move numbers
        move_num_font = pygame.font.SysFont("arial", max(6, cs // 4))
        for (vx, vy) in disp_visited:
            if (vx, vy) == disp_pos:
                continue
            px, py   = self.board_renderer.to_pixel(vx, vy)
            in_found = (vx, vy) in self.board_model.grid
            if not in_found:
                parity = (vx + (self.board_model.rows - 1 - vy)) % 2
                vcolor = DK_VISITED if parity == 0 else LT_VISITED
                pygame.draw.rect(screen, vcolor, (px + 3, py + 3, cs - 4, cs - 4))
            if self.track_mode_active and (vx, vy) in disp_vis_moves:
                if in_found:
                    bg   = self.board_model.grid[(vx, vy)]
                    luma = bg[0] * 0.299 + bg[1] * 0.587 + bg[2] * 0.114
                    nc   = (0, 0, 0) if luma > 128 else (255, 255, 255)
                else:
                    vc   = DK_VISITED if ((vx + (self.board_model.rows - 1 - vy)) % 2) == 0 else LT_VISITED
                    nc   = (0, 0, 0) if vc == LT_VISITED else (255, 255, 255)
                # visited_moves is 0-indexed; display as 1-indexed
                ns  = move_num_font.render(str(disp_vis_moves[(vx, vy)] + 1), True, nc)
                screen.blit(ns, ns.get_rect(center=(px + cs // 6, py + cs // 4)))

        # Guide arrows
        if self.guide_mode_active and cs > 0 and disp_pos and self.arrows:
            if self.game_state in (GameState.INGAME, GameState.MENU, GameState.WAITING):
                moves_to_display = self.legal_moves
            elif self.game_state == GameState.ENDGAME:
                moves_to_display = (self.legal_moves if self.replay_mode_active
                                    else self.final_legal_moves)
            else:
                moves_to_display = []
            self._draw_arrows(screen, moves_to_display, disp_pos)

        # Hint degrees (Warnsdorff numbers)
        if self.hint_mode_active and cs > 0 and self.hint_degrees:
            hf = pygame.font.SysFont("arial", max(6, cs // 4))
            for (hx, hy), degree in self.hint_degrees.items():
                hpx, hpy = self.board_renderer.to_pixel(hx, hy)
                if (hx, hy) in self.board_model.grid:
                    bg = self.board_model.grid[(hx, hy)]
                else:
                    bg = LT_SQUARE if (hx + hy) % 2 == 0 else DK_SQUARE
                luma = bg[0] * 0.299 + bg[1] * 0.587 + bg[2] * 0.114
                hc   = (107, 50, 71) if luma > 128 else (107, 50, 71)
                hs   = hf.render(str(degree), True, hc)
#                screen.blit(hs, hs.get_rect(center=(hpx + cs // 2, hpy + cs // 2)))
                screen.blit(hs, hs.get_rect(center=(hpx + cs - (cs // 5), hpy + (cs // 5))))

        # Player piece
        if disp_pos and cs > 0:
            px, py    = self.board_renderer.to_pixel(*disp_pos)
            cell_rect = pygame.Rect(px + 1, py + 1, cs - 2, cs - 2)
            try:
                pk.draw_piece(screen, cell_rect, self.get_current_selections()["piece"])
            except (KeyError, ValueError):
                pygame.draw.ellipse(screen, (0, 0, 0), cell_rect)

    def _render_left_panel(
            self, screen: pygame.Surface,
            left_panel: UIPanel,
            msg_left: int, msg_right: int, msg_bottom: int) -> None:
        """Render MENU_PANEL and BUTTON_PANEL."""
        btn_w       = UI_SPACE
        line_height = self.font.get_linesize() + UI_SPACE

        # ---- MENU_PANEL: selector rows ----
        menu_bounds      = left_panel.get_bounds("MENU_PANEL")
        text_x           = menu_bounds['left'] + UI_SPACE
        menu_panel_items = [(i, item) for i, item in enumerate(self.menu_items)
                            if item[0] != 'piece']

        max_label_w = max(
            self.font.render(l + ":", True, (0, 0, 0)).get_width()
            for l, _, _ in self.menu_items if l != 'piece')
        minus_x = text_x + max_label_w + UI_SPACE
        plus_x  = menu_bounds['left'] + menu_bounds['width'] - UI_SPACE * 4

        for list_idx, (item_idx, (label, values, cur_idx)) in enumerate(menu_panel_items):
            panel_y  = left_panel.get_line_y("MENU_PANEL", list_idx, line_height)
            row_cy   = panel_y + btn_w // 2
            lbl_surf = self.font.render(f"{label}", True, (0, 0, 0))
            screen.blit(lbl_surf, lbl_surf.get_rect(midleft=(text_x, row_cy)))

            show_text = not self.blind_draw_active or self.game_state == GameState.ENDGAME
            if show_text:
                val = values[cur_idx]
                if label == "clock":
                    sel_text = _display_for_clock(val)
                else:
                    sel_text = str(val)
                sel_surf = self.font.render(sel_text, True, (0, 0, 0))
                sel_cx   = (minus_x + btn_w / 2 + plus_x + btn_w / 2) / 2
                screen.blit(sel_surf, sel_surf.get_rect(center=(sel_cx, row_cy)))

            if self.game_state == GameState.MENU:
                mr = pygame.Rect(minus_x, panel_y, int(btn_w * 1.5), int(btn_w * 1.5))
                pygame.draw.rect(screen, DK_SQUARE, mr)
                screen.blit(self.font.render("<", True, (0, 160, 0)),
                            self.font.render("<", True, (0, 160, 0)).get_rect(center=mr.center))
                self.widget_rects[("minus", item_idx)] = mr

                pr_rect = pygame.Rect(plus_x, panel_y, int(btn_w * 1.5), int(btn_w * 1.5))
                pygame.draw.rect(screen, DK_SQUARE, pr_rect)
                screen.blit(self.font.render(">", True, (255, 0, 0)),
                            self.font.render(">", True, (255, 0, 0)).get_rect(center=pr_rect.center))
                self.widget_rects[("plus", item_idx)] = pr_rect

        # blind draw button (MENU only, not in seed mode)
        self.buttons["blind_draw"].active = (self.game_state == GameState.MENU
                                             and not self.seed_mode_active)
        self.buttons["blind_draw"].rect = left_panel.get_widget_rect("MENU_PANEL", 7, BTW, BTH)
        if self.buttons["blind_draw"].active:
            self.buttons["blind_draw"].draw(screen)

        # retry button (ENDGAME only, at same slot)
        self.buttons["retry"].active = self.game_state == GameState.ENDGAME
        self.buttons["retry"].rect   = left_panel.get_widget_rect("MENU_PANEL", 7, BTW, BTH)
        if self.buttons["retry"].active:
            self.buttons["retry"].draw(screen)

        # enter/cancel share code button (MENU only)
        self.buttons["enter_code"].active   = self.game_state == GameState.MENU
        self.buttons["enter_code"].bg_color = (224, 64, 128) if self.seed_mode_active else (224, 0, 96)
        self.buttons["enter_code"].text = ("cancel code input" if self.seed_mode_active
                                               else "enter share code")
        self.buttons["enter_code"].rect = left_panel.get_widget_rect("MENU_PANEL", 9, BTW, BTH)
        self.buttons["enter_code"].draw(screen)

        # Codec input box (MENU + seed_mode_active)
        if self.game_state == GameState.MENU and self.seed_mode_active:
            codec_y = left_panel.get_line_y("MENU_PANEL", 10, line_height)
            input_w = 192
            input_x = menu_bounds['left'] + (menu_bounds['width'] - input_w) // 2
            self.codec_input.rect = pygame.Rect(input_x, codec_y, input_w, BTH)
            self.codec_input.draw(screen)

        # Share code display (WAITING/INGAME/ENDGAME)
        if (self.puzzle_code
                and self.game_state in (GameState.WAITING, GameState.INGAME, GameState.ENDGAME)):
            code_y  = left_panel.get_line_y("MENU_PANEL", 10, line_height)
            code_cx = (menu_bounds['left'] + menu_bounds['left'] + menu_bounds['width']) / 2
            code_s  = self.font.render(self.puzzle_code, True, (0, 0, 0))
            screen.blit(code_s, code_s.get_rect(center=(code_cx, code_y + btn_w)))

        # copy share code button (WAITING/INGAME/ENDGAME)
        self.buttons["copy_code"].active    = self.game_state in (
            GameState.WAITING, GameState.INGAME, GameState.ENDGAME)
        self.buttons["copy_code"].bg_color  = (224, 64, 128) if self.copy_clicked else (224, 0, 96)
        self.buttons["copy_code"].text = ("share code copied" if self.copy_clicked
                                               else "copy share code")
        self.buttons["copy_code"].rect = left_panel.get_widget_rect("MENU_PANEL", 9, BTW, BTH)
        if self.buttons["copy_code"].active:
            self.buttons["copy_code"].draw(screen)

        # ---- BUTTON_PANEL ----
        button_bounds = left_panel.get_bounds("BUTTON_PANEL")

        # "click a starting square" message (WAITING)
        if self.game_state == GameState.WAITING:
            choose_y = left_panel.get_line_y("BUTTON_PANEL", 0, line_height)
            cs_surf  = self.font.render("click a starting square", True, (255, 0, 0))
            screen.blit(cs_surf, cs_surf.get_rect(
                centerx=button_bounds['center_x'], centery=choose_y + btn_w // 2))

        # start (MENU), reveal (ENDGAME), hint_mode (INGAME)
        if self.seed_mode_active:
            start_ok = self.game_state == GameState.MENU and self._is_valid_codec_length()
        else:
            start_ok = self.is_piece_playable and self.game_state == GameState.MENU
        self.buttons["start"].active = start_ok
        self.buttons["start"].rect   = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        if self.buttons["start"].active:
            self.buttons["start"].draw(screen)

        self.buttons["reveal"].active = self.game_state == GameState.ENDGAME
        self.buttons["reveal"].text   = ('hide missed units' if self.reveal_mode_active
                                         else 'show all units')
        self.buttons["reveal"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        if self.buttons["reveal"].active:
            self.buttons["reveal"].draw(screen)

        # hint mode
        self.buttons["hint_mode"].active = self.game_state == GameState.INGAME
                                            #or self.game_state == GameState.ENDGAME)
        self.buttons["hint_mode"].text  = ('hide move degrees' if self.hint_mode_active
                                            else 'show move degrees')
        self.buttons["hint_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        if self.buttons["hint_mode"].active:
            self.buttons["hint_mode"].draw(screen)

        # guide mode
        self.buttons["guide_mode"].active = self.game_state in (
                GameState.MENU, GameState.INGAME, GameState.ENDGAME)
        self.buttons["guide_mode"].text   = ('hide move guide' if self.guide_mode_active
                                             else 'show move guide')
        self.buttons["guide_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 2, BTW, BTH)
        if self.buttons["guide_mode"].active:
            self.buttons["guide_mode"].draw(screen)

        # track mode
        self.buttons["track_mode"].active = self.game_state in (
            GameState.MENU, GameState.WAITING, GameState.INGAME, GameState.ENDGAME)
        self.buttons["track_mode"].text   = ('hide move track' if self.track_mode_active
                                             else 'show move track')
        self.buttons["track_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 4, BTW, BTH)
        self.buttons["track_mode"].draw(screen)

        # undo (INGAME), replay_mode (ENDGAME)
        self.buttons["undo_mode"].active = (self.game_state == GameState.INGAME
                                            and len(self.replay_states) > 1)
        self.buttons["undo_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 6, BTW, BTH)
        if self.buttons["undo_mode"].active:
            self.buttons["undo_mode"].draw(screen)

        self.buttons["replay_mode"].active = self.game_state == GameState.ENDGAME
        self.buttons["replay_mode"].text   = 'end replay' if self.replay_mode_active else 'start replay'
        self.buttons["replay_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 6, BTW, BTH)
        if self.buttons["replay_mode"].active:
            self.buttons["replay_mode"].draw(screen)

        # Replay nav buttons
        self.buttons["replay_prev"].active = False
        self.buttons["replay_next"].active = False
        if self.replay_mode_active and self.replay_states:
            rm_rect = self.buttons["replay_mode"].rect
            nav_w   = BTW // 4
            if self.replay_index > 0:
                self.buttons["replay_prev"].active = True
                self.buttons["replay_prev"].rect   = pygame.Rect(
                    rm_rect.left - nav_w - 4, rm_rect.top, nav_w, BTH)
                self.buttons["replay_prev"].draw(screen)
            if self.replay_index < len(self.replay_states) - 1:
                self.buttons["replay_next"].active = True
                self.buttons["replay_next"].rect   = pygame.Rect(
                    rm_rect.right + 4, rm_rect.top, nav_w, BTH)
                self.buttons["replay_next"].draw(screen)

        # resign (INGAME), new_game (WAITING/ENDGAME)
        self.buttons["resign"].active = self.game_state == GameState.INGAME
        self.buttons["resign"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 8, BTW, BTH)
        if self.buttons["resign"].active:
            self.buttons["resign"].draw(screen)

        self.buttons["new_game"].active = self.game_state in (GameState.WAITING, GameState.ENDGAME)
        self.buttons["new_game"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 8, BTW, BTH)
        if self.buttons["new_game"].active:
            self.buttons["new_game"].draw(screen)

        # peek button (WAITING/INGAME/ENDGAME, fixed bottom-left)
        self.buttons["peek_mode"].active = self.game_state in (
            GameState.WAITING, GameState.INGAME, GameState.ENDGAME)
        self.buttons["peek_mode"].text = 'hide' if self.peek_mode_visible else 'peek'
        self.buttons["peek_mode"].rect = pygame.Rect(
            msg_left + UI_SPACE * 3, msg_bottom - UI_SPACE * 5, BTW // 2, BTH)
        if self.buttons["peek_mode"].active:
            self.buttons["peek_mode"].draw(screen)

        # Exit button (always, fixed bottom-right)
        self.buttons["exit"].rect = pygame.Rect(
            msg_right - UI_SPACE * 11, msg_bottom - UI_SPACE * 5, BTW // 2, BTH)
        self.buttons["exit"].draw(screen)

        # Peek thumbnail
        self._draw_peek_thumbnail(screen, left_panel, line_height)

    def _render_right_panel(
            self, screen: pygame.Surface,
            right_panel: UIPanel) -> None:
        """Render PIECE_PANEL and STATS_PANEL."""
        btn_w       = UI_SPACE
        line_height = self.font.get_linesize() + UI_SPACE
        star_size   = 22

        # ---- PIECE_PANEL ----
        piece_bounds = right_panel.get_bounds("PIECE_PANEL")
        right_tx     = piece_bounds['left'] + UI_SPACE

        piece_idx                  = self.label_to_index["piece"]
        _, piece_values, piece_cur = self.menu_items[piece_idx]
        piece_name                 = piece_values[piece_cur] if piece_values else ""

        p_line_y = right_panel.get_line_y("PIECE_PANEL", 0, line_height)
        p_row_cy = p_line_y
        lbl_s    = self.font.render("piece:", True, (0, 0, 0))
        lbl_rect = lbl_s.get_rect(midleft=(right_tx, p_row_cy))
        p_minus_x = lbl_rect.right + UI_SPACE
        p_plus_x  = piece_bounds['left'] + piece_bounds['width'] - UI_SPACE - btn_w * 3

        sel_s = self.font_large.render(piece_name, True, (0, 0, 0))
        screen.blit(sel_s, sel_s.get_rect(center=(piece_bounds['center_x'], p_row_cy + 8)))

        move_set_text = pk.get_piece_move_sets_text(piece_name)
        mst_s = self.font.render(move_set_text, True, (0, 0, 0))
        screen.blit(mst_s, mst_s.get_rect(
            centerx=piece_bounds['center_x'],
            top=p_row_cy + sel_s.get_height() + self.font.get_linesize()))

        if self.game_state == GameState.MENU:
            pm_r = pygame.Rect(p_minus_x - btn_w, p_line_y, int(btn_w * 1.5), int(btn_w * 1.5))
            pygame.draw.rect(screen, DK_SQUARE, pm_r)
            screen.blit(self.font.render("<", True, (0, 160, 0)),
                        self.font.render("<", True, (0, 160, 0)).get_rect(center=pm_r.center))
            self.widget_rects[("minus", piece_idx)] = pm_r

            pp_r = pygame.Rect(p_plus_x - btn_w, p_line_y, int(btn_w * 1.5), int(btn_w * 1.5))
            pygame.draw.rect(screen, DK_SQUARE, pp_r)
            screen.blit(self.font.render(">", True, (255, 0, 0)),
                        self.font.render(">", True, (255, 0, 0)).get_rect(center=pp_r.center))
            self.widget_rects[("plus", piece_idx)] = pp_r

        # Ratings
        sel          = self.get_current_selections()
        cur_ratings  = pr.get_piece_ratings(sel["piece"], sel["board"], sel["shapes"])
        mob_rating   = cur_ratings.get('mobility_rating', 0)
        agil_rating  = cur_ratings.get('agility_rating', 0)
        star_spacing = 3

        if self.is_piece_playable:
            # Mobility
            piece_line = 3
            y_pos = right_panel.get_line_y("PIECE_PANEL", piece_line, line_height)
            if self.star_filled and self.star_empty:
                mob_lbl_s  = self.font.render("mobility ", True, (0, 0, 0))
                lw         = mob_lbl_s.get_width()
                stars_w    = 5 * star_size + 4 * star_spacing
                start_x    = piece_bounds['center_x'] - (lw + 8 + stars_w) // 2
                screen.blit(mob_lbl_s, (start_x, y_pos))
                sx = start_x + lw + 8
                sy = y_pos + (self.font.get_linesize() - star_size) // 2
                for i in range(mob_rating):
                    screen.blit(self.star_filled, (sx + i * (star_size + star_spacing), sy))
                for i in range(5 - mob_rating):
                    screen.blit(self.star_empty,
                                (sx + (mob_rating + i) * (star_size + star_spacing), sy))
            else:
                stars = "★" * mob_rating + "☆" * (5 - mob_rating)
                fs = self.font.render(f"mobility {stars}", True, (0, 0, 0))
                screen.blit(fs, fs.get_rect(centerx=piece_bounds['center_x'], top=y_pos))

            # Agility
            piece_line += 1
            y_pos = right_panel.get_line_y("PIECE_PANEL", piece_line, line_height)
            if self.star_filled and self.star_empty:
                if agil_rating > 0:
                    agil_lbl_s = self.font.render("agility    ", True, (0, 0, 0))
                    lw         = agil_lbl_s.get_width()
                    stars_w    = 5 * star_size + 4 * star_spacing
                    start_x    = piece_bounds['center_x'] - (lw + 8 + stars_w) // 2
                    screen.blit(agil_lbl_s, (start_x, y_pos))
                    sx = start_x + lw + 8
                    sy = y_pos + (self.font.get_linesize() - star_size) // 2
                    for i in range(agil_rating):
                        screen.blit(self.star_filled, (sx + i * (star_size + star_spacing), sy))
                    for i in range(5 - agil_rating):
                        screen.blit(self.star_empty,
                                    (sx + (agil_rating + i) * (star_size + star_spacing), sy))
            else:
                if agil_rating > 0:
                    stars = "★" * agil_rating + "☆" * (5 - agil_rating)
                    fs = self.font.render(f"agility {stars}", True, (0, 0, 0))
                else:
                    fs = self.font.render("agility --", True, (128, 128, 128))
                screen.blit(fs, fs.get_rect(centerx=piece_bounds['center_x'], top=y_pos))

            # Challenge rating
            challenge_line = 8
            ch_y           = right_panel.get_line_y("PIECE_PANEL", challenge_line, line_height)
            piece_bounds   = right_panel.get_bounds("PIECE_PANEL")
            ch_stars       = max(0, min(5, round(self.challenge_rating)))
            ch_lbl_s       = self.font.render("challenge ", True, (0, 0, 0))
            lw             = ch_lbl_s.get_width()
            if self.star_filled and self.star_empty:
                stars_w  = 5 * star_size + 4 * star_spacing
                start_x  = piece_bounds['center_x'] - (lw + 8 + stars_w) // 2
                #screen.blit(ch_lbl_s, (start_x, ch_y))
                sx = start_x + lw + 8
                sy = ch_y + (self.font.get_linesize() - star_size) // 2
                #for i in range(ch_stars):
                #    screen.blit(self.star_filled, (sx + i * (star_size + star_spacing), sy))
                #for i in range(5 - ch_stars):
                #    screen.blit(self.star_empty,
                #                (sx + (ch_stars + i) * (star_size + star_spacing), sy))
            #else:
            #    stars = "★" * ch_stars + "☆" * (5 - ch_stars)
                #fs = self.font.render(f"challenge {stars}", True, (0, 0, 0))
                #screen.blit(fs, fs.get_rect(centerx=piece_bounds['center_x'], top=ch_y))

        # Piece too big warning
        if self.game_state == GameState.MENU and not self.is_piece_playable:
            warn_y = right_panel.get_line_y("PIECE_PANEL", 3, line_height)
            min_n = self.min_board_size
            warn_text = f"minimum {min_n} x {min_n} board for this piece" if min_n is not None else "use a larger board for this piece"
            ws = self.font.render(warn_text, True, (128, 0, 0))
            screen.blit(ws, ws.get_rect(centerx=piece_bounds['center_x'], top=warn_y))

        # ---- STATS_PANEL ----
        stats_bounds = right_panel.get_bounds("STATS_PANEL")

        # Clock display
        clock_val = self.get_selection("clock") if "clock" in self.label_to_index else 0
        clock_color = (0, 0, 0)
        if self.game_state == GameState.WAITING:
            time_str = "0:00"
        elif clock_val == 0:
            time_str = format_time(self.clock_elapsed)
        else:
            rem = self._remaining_time()
            if rem is not None:
                time_str = _format_clock_seconds(rem)
                clock_color = (200, 0, 0) if rem < 30 else (0, 0, 0)
            else:
                time_str = format_time(self.clock_elapsed)

        abs_clk_y = stats_bounds['bottom'] - line_height * 1.5
        clk_s = self.font.render(time_str, True, clock_color)
        screen.blit(clk_s, clk_s.get_rect(
            centerx=stats_bounds['center_x'],
            centery=int(abs_clk_y + line_height // 2)))


        if self.game_state == GameState.MENU:
            preview_shapes = len(self.preview_layout or [])
            sf_y = right_panel.get_line_y("STATS_PANEL", 2, line_height)
            sf_s = self.font.render(
                f"{len(self.preview_layout or [])} shapes",
                True, (0, 0, 0))
            screen.blit(sf_s, sf_s.get_rect(centerx=stats_bounds['center_x'], top=sf_y))

            self.preview_units = sum(len(s.puzzle_units) for s in self.preview_layout or[])
            tu_y = right_panel.get_line_y("STATS_PANEL", 3, line_height)
            tu_s = self.font.render(
                f"{self.preview_units} units",
                True, (0, 0, 0))
            screen.blit(tu_s, tu_s.get_rect(centerx=stats_bounds['center_x'], top=tu_y))

        if self.game_state in (GameState.WAITING, GameState.INGAME, GameState.ENDGAME):
            mv_count = len(self.visited)
            mv_label = "move" if mv_count == 1 else "moves"
            ms = self.font.render(f"{mv_count} {mv_label}", True, (0, 0, 0))
            mv_y = right_panel.get_line_y("STATS_PANEL", 1, line_height)
            screen.blit(ms, ms.get_rect(centerx=stats_bounds['center_x'], top=mv_y))


            sf_y = right_panel.get_line_y("STATS_PANEL", 2, line_height)
            sf_s = self.font.render(
                f"{self.completed_shape_count} of {len(self.puzzle_layout or [])} shapes found",
                True, (0, 0, 0))
            screen.blit(sf_s, sf_s.get_rect(centerx=stats_bounds['center_x'], top=sf_y))


            fu_y = right_panel.get_line_y("STATS_PANEL", 3, line_height)
            fu_s = self.font.render(
                f"{self.found_puzzle_units} of {self.total_puzzle_units} units found",
                True, (0, 0, 0))
            screen.blit(fu_s, fu_s.get_rect(centerx=stats_bounds['center_x'], top=fu_y))





        # Endgame reason
        if self.game_state == GameState.ENDGAME and self.endgame_reason is not None:
            stats_y = stats_bounds['top'] + UI_SPACE * 2
            endgame_messages = {
                'resignation':         'resigned',
                'no legal moves':   'no legal moves',
                'all shapes found': 'all shapes found',
                "time's up":        "time's up",
            }
            endgame_colors = {
                'resignation':         (255, 0, 0),
                'no legal moves':   (255, 0, 0),
                'all shapes found': (0, 128, 0),
                "time's up":        (0, 0, 255),
            }
            reason    = str(self.endgame_reason)
            msg_text  = endgame_messages.get(reason, 'game over')
            msg_color = endgame_colors.get(reason, (255, 0, 0))
            end_s     = self.font.render(msg_text, True, msg_color)
            screen.blit(end_s, end_s.get_rect(
                centerx=stats_bounds['center_x'], top=stats_y))

    #  render (public)                                                     #

    def render(self, screen: pygame.Surface) -> None:
        """Render the full game frame."""
        win_width, win_height = screen.get_size()
        screen.fill(BACK_COLOR)

        margin      = UI_SPACE
        panel_width = UI_SPACE * 28
        msg_left    = margin
        msg_top     = margin
        msg_bottom  = win_height - margin
        msg_right   = msg_left + panel_width
        right_left  = win_width - panel_width - margin

        left_panel_rect  = pygame.Rect(msg_left,   msg_top, panel_width, msg_bottom - msg_top)
        right_panel_rect = pygame.Rect(right_left, msg_top, panel_width, msg_bottom - msg_top)

        left_panel  = UIPanel(left_panel_rect,  gap=0)
        right_panel = UIPanel(right_panel_rect, gap=0)

        left_panel.draw_panel(screen,  "MENU_PANEL",   LT_SQUARE, GRID_COLOR)
        left_panel.draw_panel(screen,  "BUTTON_PANEL", LT_SQUARE, GRID_COLOR)
        right_panel.draw_panel(screen, "PIECE_PANEL",  LT_SQUARE, GRID_COLOR)
        right_panel.draw_panel(screen, "STATS_PANEL",  LT_SQUARE, GRID_COLOR)

        area_left   = msg_right  + margin
        area_top    = margin
        area_right  = right_left - margin
        area_bottom = win_height - margin

        # Sync board model dimensions in MENU
        if self.game_state == GameState.MENU:
            brd = int(self.get_current_selections()["board"])
            if self.board_model.cols != brd or self.board_model.rows != brd:
                self.board_model.cols = brd
                self.board_model.rows = brd
                self.board_model.clear()

        self._update_cell_size(
            area_left, area_top,
            area_right - area_left, area_bottom - area_top)

        # MENU: update legal moves for guide preview
        if self.game_state == GameState.MENU and self.player_pos:
            current_piece = self.get_current_selections()["piece"]
            self.legal_moves = get_legal_moves_for_board(
                current_piece,
                self.player_pos[0], self.player_pos[1],
                self.board_model.cols, self.board_model.rows,
                set())

        if self.legal_moves:
            self.last_nonempty_legal_moves = list(self.legal_moves)

        self.board_renderer.draw_background(screen)
        self.widget_rects.clear()

        # Error overlay
        if self.error_message and pygame.time.get_ticks() < self.error_timer:
            ef = pygame.font.SysFont("arial", 22)
            es = ef.render(self.error_message, True, (200, 0, 0))
            aw = area_right - area_left
            ah = area_bottom - area_top
            ex = area_left + (aw - es.get_width())  // 2
            ey = area_top  + (ah - es.get_height()) // 2
            pygame.draw.rect(screen, (255, 240, 240),
                             (ex - 8, ey - 6, es.get_width() + 16, es.get_height() + 12))
            screen.blit(es, (ex, ey))
        elif self.error_message and pygame.time.get_ticks() >= self.error_timer:
            self.error_message = ""

        self._render_board_area(screen)
        self._render_left_panel(screen, left_panel, msg_left, msg_right, msg_bottom)
        self._render_right_panel(screen, right_panel)