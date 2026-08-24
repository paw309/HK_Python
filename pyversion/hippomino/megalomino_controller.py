"""
megalomino_controller.py

Game controller for Megalomino game mode.
Manages game state, move validation, tour tracking on a single polyomino.
"""

import random
import csv
import os
import time
import pygame
from typing import Optional, List, Tuple, Dict, Any, Set

from gameboard import BoardModel, BoardRenderer
from uipanel import UIPanel
from text_input import TextInput
from widgets import Button
from base_game_controller import BaseGameController, GameState
from chess_clock import GameClock, ClockSettings, ClockType, format_hms

# Import tour data from Python files (much faster than parquet)
from pyversion.tourbus.megalotours.tours_heptomino import HEPTOMINO_TOURS
from pyversion.tourbus.megalotours.tours_octomino import OCTOMINO_TOURS
from pyversion.tourbus.megalotours.tours_nonomino import NONOMINO_TOURS
from pyversion.tourbus.megalotours.tours_decomino import DECOMINO_TOURS
from pyversion.tourbus.megalotours.tours_undecomino import UNDECOMINO_TOURS
from pyversion.tourbus.megalotours.tours_dodecomino import DODECOMINO_TOURS
from pyversion.tourbus.megalotours.tours_tridecomino import TRIDECOMINO_TOURS
from pyversion.tourbus.megalotours.tours_tetradecomino import TETRADECOMINO_TOURS
from pyversion.tourbus.megalotours.tours_pentadecomino import PENTADECOMINO_TOURS

# For smaller shapes (7-15), use static dictionaries
# Combine all static tour dictionaries into one using dictionary unpacking
MEGALOMINO_TOURS = {
    **HEPTOMINO_TOURS,
    **OCTOMINO_TOURS,
    **NONOMINO_TOURS,
    **DECOMINO_TOURS,
    **UNDECOMINO_TOURS,
    **DODECOMINO_TOURS,
    **TRIDECOMINO_TOURS,
    **TETRADECOMINO_TOURS,
    **PENTADECOMINO_TOURS,
}

# ---------------------------------------------------------------------------
# Megalomino (4-piece) puzzle generation helpers
# ---------------------------------------------------------------------------

# Quadrant offsets within the unseen 9x9 grid.  Each 4x4 sub-region is
# separated by a one-square gap so no two shapes are orthogonally adjacent.
_MEGA_OFFSETS: List[Tuple[int, int]] = [(0, 0), (0, 5), (5, 0), (5, 5)]

# Valid Hamiltonian traversal orders through the slot adjacency graph:
#   slot 0 (0,0) ↔ slot 1 (0,5)  [y-gap]
#   slot 0 (0,0) ↔ slot 2 (5,0)  [x-gap]
#   slot 1 (0,5) ↔ slot 3 (5,5)  [x-gap]
#   slot 2 (5,0) ↔ slot 3 (5,5)  [y-gap]
_MEGA_ORDERINGS: List[Tuple[int, int, int, int]] = [
    (0, 1, 3, 2), (0, 2, 3, 1),
    (1, 0, 2, 3), (1, 3, 2, 0),
    (2, 0, 1, 3), (2, 3, 1, 0),
    (3, 1, 0, 2), (3, 2, 0, 1),
]

# Lazily populated pool of candidate shapes (fit within 4×4)
_MEGA_CANDIDATES: Optional[Dict[str, List[Tuple[int, int]]]] = None


def _get_mega_candidates() -> Dict[str, List[Tuple[int, int]]]:
    """Return the pool of decomino / dodecomino tours that fit in a 4×4 box."""
    global _MEGA_CANDIDATES
    if _MEGA_CANDIDATES is None:
        _MEGA_CANDIDATES = {
            k: v
            for k, v in {**DECOMINO_TOURS, **DODECOMINO_TOURS}.items()
            if all(0 <= x < 4 and 0 <= y < 4 for x, y in v)
        }
    return _MEGA_CANDIDATES


def _mega_shape_variants(path: List[Tuple[int, int]]) -> List[List[Tuple[int, int]]]:
    """Return up to 8 distinct rotation / reflection variants of *path*."""
    def rotate_90(c: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        return [(y, -x) for x, y in c]

    def flip_h(c: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        return [(-x, y) for x, y in c]

    def normalize(c: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        mx = min(x for x, y in c)
        my = min(y for x, y in c)
        return [(x - mx, y - my) for x, y in c]

    unique: List[List[Tuple[int, int]]] = []
    seen: Set[Tuple[Tuple[int, int], ...]] = set()
    cur = list(path)
    for _ in range(4):
        for variant in (cur, flip_h(cur)):
            norm = normalize(variant)
            key = tuple(norm)
            if key not in seen:
                seen.add(key)
                unique.append(norm)
        cur = rotate_90(cur)
    return unique


def build_megalomino_puzzle(
    seed: Optional[int] = None,
    max_attempts: int = 200,
) -> Optional[Tuple[str, List[Tuple[int, int]], Set[Tuple[int, int]]]]:
    """
    Select 4 distinct polyomino tours from the decomino / dodecomino pools,
    place them in the four quadrants of a 9×9 grid, and chain them into a
    single Hamiltonian knight's tour.

    Returns ``(shape_code, combined_tour, all_squares)`` on success, or
    ``None`` if no valid arrangement is found within *max_attempts*.

    Constraints satisfied:
    * All shapes fit within the unseen 9×9 grid (coordinates 0–8).
    * No two shapes are orthogonally adjacent (one-square gap between quadrants).
    * The knight can leap from the last square of one shape's tour to the first
      square of the next via a standard knight move (blank squares are traversable).
    * The combined tour visits every square of every shape exactly once.
    """
    rng = random.Random(seed)
    candidates = _get_mega_candidates()
    candidate_ids = list(candidates.keys())

    for _ in range(max_attempts):
        shape_ids = rng.sample(candidate_ids, 4)
        shapes = [candidates[sid] for sid in shape_ids]
        all_variants = [_mega_shape_variants(s) for s in shapes]

        orderings = _MEGA_ORDERINGS[:]
        rng.shuffle(orderings)

        for ordering in orderings:
            # Build the list of (placed_path, placed_path_reversed) for each shape
            placed: List[List[List[Tuple[int, int]]]] = []
            for i, slot in enumerate(ordering):
                ox, oy = _MEGA_OFFSETS[slot]
                pvs: List[List[Tuple[int, int]]] = []
                for v in all_variants[i]:
                    p = [(x + ox, y + oy) for x, y in v]
                    pvs.append(p)
                    pvs.append(p[::-1])
                placed.append(pvs)

            # Greedy chain search with early termination
            for pv0 in placed[0]:
                exit0 = pv0[-1]
                for pv1 in placed[1]:
                    dx = abs(exit0[0] - pv1[0][0])
                    dy = abs(exit0[1] - pv1[0][1])
                    if not ((dx == 1 and dy == 2) or (dx == 2 and dy == 1)):
                        continue
                    exit1 = pv1[-1]
                    for pv2 in placed[2]:
                        dx = abs(exit1[0] - pv2[0][0])
                        dy = abs(exit1[1] - pv2[0][1])
                        if not ((dx == 1 and dy == 2) or (dx == 2 and dy == 1)):
                            continue
                        exit2 = pv2[-1]
                        for pv3 in placed[3]:
                            dx = abs(exit2[0] - pv3[0][0])
                            dy = abs(exit2[1] - pv3[0][1])
                            if not ((dx == 1 and dy == 2) or (dx == 2 and dy == 1)):
                                continue
                            combined = pv0 + pv1 + pv2 + pv3
                            code = "mega-" + ",".join(shape_ids)
                            return code, combined, set(combined)
    return None


# For larger shapes (16-20), use on-the-fly generation
from pyversion.hippomino.tour_builder import (
    SIZE_TO_TOURS,
    SIZE_TO_PROVIDER,
    build_tour_from_ids,
)

# Polyomino codec for dynamic shapes
from pyversion.hippomino.megalomino_codec import (
    decode as codec_decode,
    is_dynamic_code,
)

# --- Constants ---
FPS = 60
UI_SPACE = 10
BTW = int(UI_SPACE * 15)
BTH = int(UI_SPACE * 3)
MAX_CLOCK_SECONDS = 10

# Knight moves
KNIGHT_MOVES = [
    (-2, -1), (-2, 1), (-1, -2), (-1, 2),
    (1, -2), (1, 2), (2, -1), (2, 1)
]

# Colors
BKG_COLOR = (244, 228, 195)
LT_SQUARE = (255, 255, 240)
DK_SQUARE = (232, 200, 150)
GRID_COLOR = (107, 70, 51)
LT_VISITED = (192, 220, 248)
DK_VISITED = (128, 160, 224)
LT_MISSED = (255, 192, 192) # (224, 224, 224)  #(255, 192, 192)
DK_MISSED = (255, 128, 128) # (192, 192, 192,) #(255, 128, 128)

# Text rendering
TEXT_OFFSET_Y = 8  # Vertical offset for move numbers

# Polyomino classification

CLASS_INFO = {
    "heptomino": {"prefix": "07", "units": 7, "count": 2},
    "octomino": {"prefix": "08", "units": 8, "count": 10},
    "nonomino": {"prefix": "09", "units": 9, "count": 57},
    "decomino": {"prefix": "10", "units": 10, "count": 194},
    "unndecomino": {"prefix": "11", "units": 11, "count": 617},
    "dodecomino": {"prefix": "12", "units": 12, "count": 1580},
    "tridecomino": {"prefix": "13", "units": 13, "count": 4858},
    "tetradecomino": {"prefix": "14", "units": 14, "count": 13124},
    "pentadecomino": {"prefix": "15", "units": 15, "count": 43487},
    "hexadecomino": {"prefix": "16", "units": 16, "count": 0},  # Generated on-the-fly
    "heptadecomino": {"prefix": "17", "units": 17, "count": 0},  # Generated on-the-fly
    "octadecomino": {"prefix": "18", "units": 18, "count": 0},  # Generated on-the-fly
    "nonadecomino": {"prefix": "19", "units": 19, "count": 0},  # Generated on-the-fly
    "icosomino": {"prefix": "20", "units": 20, "count": 0},  # Generated on-the-fly
    "hippomino": {"prefix": "hipp", "units": 0, "count": 4},  # 4-piece tour on 9x9 grid
}

CLASS_NAMES = list(CLASS_INFO.keys())
BOARD_COLOR_CHOICES = ["chessboard", "monochrome"]

# Clock values in seconds: 0 = infinity, 60 = 1 min, 120 = 2 min, etc.
#CLOCK_CHOICES = [0] + list(range(60, (MAX_CLOCK_MINUTES + 1) * 60, 60))
CLOCK_CHOICES = [0] + list(range(30, 301, 30))  # 0 means infinity; 30s–300s by 30s
CLOCK_MODES = ["per game", "per move"]

# Schema for puzzle codes
# The polyomino codec replaces the old parameter-encoding schema.
# The shape code (e.g. "16-ABCD-EFGH" or "07-00042") is the puzzle code.
megalomino_schema = []


def _format_clock(clock_value):
    """Format clock value for display in menu selection."""
    if clock_value == 0:
        return "infinity"
    # clock_value is in seconds, format as m:ss to match clock display
    minutes = clock_value // 60
    seconds = clock_value % 60
    return f"{minutes}:{seconds:02d}"


def _format_clock_seconds(seconds) -> str:
    """Format clock seconds as MM:SS for display during gameplay."""
    if seconds is None:
        seconds = 0
    seconds = max(0, int(seconds))
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins}:{secs:02d}"


def _size_to_class_name(size: int) -> Optional[str]:
    """Return the class name for a polyomino of *size* squares, or None."""
    for name, info in CLASS_INFO.items():
        if info["units"] == size:
            return name
    return None


def get_shapes_by_class(class_name: str) -> List[str]:
    """Get all shape IDs for a given class name."""
    if class_name not in CLASS_INFO:
        return []

    prefix = CLASS_INFO[class_name]["prefix"]
    units = CLASS_INFO[class_name]["units"]

    # 4-piece megalomino mode: sentinel so callers know shapes exist.
    if class_name == "hippomino":
        return ["hippomino"]

    # For sizes 16-20 the actual shape IDs are codec strings generated
    # at runtime; return a sentinel so callers know shapes exist.
    if units >= 16:
        return ["dynamic"]

    return [shape_id for shape_id in MEGALOMINO_TOURS.keys() if shape_id.startswith(prefix)]


def get_tour_for_shape(shape_id: str, class_name: str) -> Optional[List[Tuple[int, int]]]:
    """
    Get a tour for the given shape ID.
    For small shapes (7-15), return from static dictionary.
    For large shapes (16-20), generate on-the-fly via DynamicTourProvider.
    For coded shapes ("16-ABCD-EFGH"), reconstruct deterministically.
    """
    units = CLASS_INFO[class_name]["units"]

    # Dynamic codec string: deterministic reconstruction
    if is_dynamic_code(shape_id):
        result = codec_decode(shape_id)
        if result is None:
            return None
        _, id_a, id_b = result
        return build_tour_from_ids(id_a, id_b)

    # Sizes 16-20: generate a new random tour via the provider
    if units >= 16:
        provider = SIZE_TO_PROVIDER.get(units)
        if provider is None:
            return None
        result = provider.get_random_tour()
        if result:
            _, tour_path = result
            return tour_path
        return None

    # For sizes 7-15, use static dictionary
    return MEGALOMINO_TOURS.get(shape_id)


class MegalominoController(BaseGameController):
    """Controls game logic and rendering for Megalomino game mode."""

    def __init__(self, board_model: BoardModel, board_renderer: BoardRenderer,
                 menu_items: list, label_to_index: dict,
                 font: pygame.font.Font, font_large: pygame.font.Font,
                 base_dir: str):
        super().__init__(
            board_model, board_renderer, menu_items, label_to_index,
            font, font_large, base_dir, megalomino_schema,
        )

        # Override base class defaults
        self.show_path_active = False  # show original tour path
        self.track_mode_active = True
        self.peek_mode_active = False

        # Override codec_input size/length for the megalomino shape code format
        # "NN-CCCCC-CCCCC" = 15 chars including dashes; allow a small buffer
        self.codec_input = TextInput(pygame.Rect(0, 0, BTW, BTH), font, max_length=16)

        # megalomino-specific state
        self.selected_shape_id: Optional[str] = None
        self.pending_shape_code: Optional[str] = None   # code entered by the user
        self.tour_path: List[Tuple[int, int]] = []  # original tour path
        self.transformed_tour_path: List[Tuple[int, int]] = []  # transformed tour path
        self.polyomino_squares: Set[Tuple[int, int]] = set()  # actual squares on board
        self.coord_map: Dict[Tuple[int, int], Tuple[int, int]] = {}  # board -> polyomino
        self.reverse_coord_map: Dict[Tuple[int, int], Tuple[int, int]] = {}  # polyomino -> board
        self.board_color_mode: str = "chessboard"
        self.tour_complete: bool = False
        self.is_reentrant: bool = False
        self.stats_written: bool = False

        # Chess clock for time management
        self.game_clock: Optional[GameClock] = None

        # board rendering
        self.board_size_pixels = 810
        self.square_size = 80

        # Assets
        self.knight_image: Optional[pygame.Surface] = None
        self._load_assets()

        # Menu demo animation state
#        self.demo_shape_id: Optional[str] = None
        self.demo_tour_path: List[Tuple[int, int]] = []
        self.demo_polyomino_squares: Set[Tuple[int, int]] = set()
        self.demo_path_index: int = 0
        self.demo_timer: float = 0.0
        self.demo_pause_timer: float = 0.0
        self.demo_state: str = "paused"  # "paused", "animating", "complete"
        self._init_demo()


    def get_selection(self, label: str) -> Any:
        """Override to handle 'piece' and 'board' selection for base game controller."""
        if label == "piece":
            return "knight"
        if label == "board":
            return 8  # Fixed board size for megalomino
        return super().get_selection(label)

    def _is_valid_codec_length(self) -> bool:
        """Return True when the codec input contains a plausible polyomino code."""
        # get_text() strips dashes; raw lengths:
        #   Dynamic "NN-CCCCC-CCCCC" -> 12 raw chars
        #   Static  "NN-NNN[NN...]"  -> 4+ raw chars
        raw = self.codec_input.get_text().strip()
        raw_len = len(raw)
        # Dynamic code: exactly 12 raw chars (2 size + 5 + 5)
        if raw_len == 12:
            return True
        # Static code: 2-digit size prefix + 1-7 digit index
        if 3 <= raw_len <= 9 and raw[:2].isdigit():
            return True
        return False

    def start_game(self, use_seed: Optional[int] = None) -> None:
        """Start the game and set the puzzle code to the polyomino shape code."""
        super().start_game(use_seed=use_seed)
        # Override the base-class puzzle_code with the shape code so that
        # copy_code_to_clipboard() and the on-screen display show the
        # human-readable polyomino identifier.
        if self.game_state == GameState.INGAME and self.selected_shape_id:
            self.puzzle_code = self.selected_shape_id

    def _clock_has_expired(self) -> bool:
        """Override: TIME_PER_MOVE expiry is handled by game_clock.is_expired() in update()."""
        if self.game_clock and self.game_clock.settings.clock_type == ClockType.TIME_PER_MOVE:
            return False
        return super()._clock_has_expired()

    def _get_board_color_mode(self) -> str:
        """Get the board color mode from menu (chessboard or monochrome)."""
        i = self.label_to_index["board"]
        _, vals, cur = self.menu_items[i]
        return vals[cur]

    def _load_assets(self):
        """Load game assets."""
        try:
            knight_path = os.path.join(self.base_dir, "assets", "pieces", "knight.png")
            if os.path.exists(knight_path):
                self.knight_image = pygame.image.load(knight_path).convert_alpha()
        except Exception as e:
            print(f"Warning: Could not load knight image: {e}")

    def _init_demo(self):
        """Initialize menu demo with a random polyomino."""
        self._select_random_demo_polyomino()
        self.demo_path_index = 0
        self.demo_timer = 0.0
        self.demo_pause_timer = 0.0
        self.demo_state = "paused"

    def _select_random_demo_polyomino(self):
        """Select a random polyomino from the current shape selection."""
        shape_class = self.get_selection("shape")
        units = CLASS_INFO[shape_class]["units"]

        if shape_class == "hippomino":
            result = build_megalomino_puzzle()
            if result:
                code, combined_tour, all_squares = result
                self.demo_shape_id = code
                self.demo_tour_path = combined_tour[:]
                self.demo_polyomino_squares = all_squares
                self.square_size = self._megalomino_square_size()
            else:
                self.demo_shape_id = None
            return

        if units >= 16:
            # Generate a dynamic tour and capture its codec string for display
            provider = SIZE_TO_PROVIDER.get(units)
            if provider:
                result = provider.get_random_tour()
                if result:
                    codec_str, tour_path = result
                    self.demo_shape_id = codec_str
                    self.demo_tour_path = tour_path[:]
                    self.demo_polyomino_squares = set(self.demo_tour_path)
                    return
            self.demo_shape_id = None
            return

        available_shapes = get_shapes_by_class(shape_class)

        if not available_shapes:
            # Fallback to any available shape from static tours only
            if MEGALOMINO_TOURS:
                self.demo_shape_id = random.choice(list(MEGALOMINO_TOURS.keys()))
                # Direct lookup for fallback - this is always a static tour
                self.demo_tour_path = MEGALOMINO_TOURS[self.demo_shape_id][:]
                self.demo_polyomino_squares = set(self.demo_tour_path)
            else:
                self.demo_shape_id = None
            return

        # We have available shapes - select one
        self.demo_shape_id = random.choice(available_shapes)

        # Use helper function to get tour (handles both static and dynamic)
        tour_path = get_tour_for_shape(self.demo_shape_id, shape_class)
        if tour_path:
            self.demo_tour_path = tour_path[:]
            # Build polyomino squares from tour path
            self.demo_polyomino_squares = set(self.demo_tour_path)
        else:
            self.demo_shape_id = None

    # ================================================================== #
    #  Abstract method implementations                                    #
    # ================================================================== #

    def _get_min_board_size(self, piece_name: str) -> int:
        return 7  # Not used for megalomino

    def _get_encode_params(self) -> Dict[str, Any]:
        # The polyomino shape code is the puzzle code; no extra params needed.
        return {}

    def _validate_codec(self, codec_text: str) -> Tuple[bool, Optional[Dict]]:
        """
        Validate a polyomino code and queue it for use in the next start_game().

        Accepts two formats:
        * Dynamic large-polyomino code  ``"16-CCCCC-CCCCC"``
        * Static shape ID               ``"NN-NNN"``

        *codec_text* may arrive with or without dashes (``get_text()`` strips
        them); this method normalises both representations.
        """
        codec_text = codec_text.strip().upper().replace("-", "")

        # Reconstruct dashes for the expected formats:
        #   Dynamic:  "NN-CCCCC-CCCCC"  (2 + 5 + 5 = 12 raw chars)
        #   Static:   "NN-NNN[NN...]"   (2 + variable index)
        if len(codec_text) == 12:
            # "164RH0B00017" -> "16-4RH0B-00017"
            codec_text = f"{codec_text[:2]}-{codec_text[2:7]}-{codec_text[7:]}"
        elif len(codec_text) >= 3:
            # static: "07043" -> "07-043", "09219" -> "09-219"
            codec_text = f"{codec_text[:2]}-{codec_text[2:]}"

        parts = codec_text.split("-")

        def _apply(label, value):
            idx = self.label_to_index.get(label)
            if idx is None:
                return
            lbl, vals, _ = self.menu_items[idx]
            if value in vals:
                self.menu_items[idx] = (lbl, vals, vals.index(value))

        try:
            # --- Dynamic code: "NN-CCCCC-CCCCC" --------------------------------
            if is_dynamic_code(codec_text):
                result = codec_decode(codec_text)
                if result is None:
                    return False, None
                target_size, id_a, id_b = result
                # Verify that both component IDs exist in the static dictionaries
                size_a = int(id_a.split("-")[0])
                size_b = int(id_b.split("-")[0])
                if id_a not in SIZE_TO_TOURS.get(size_a, {}):
                    return False, None
                if id_b not in SIZE_TO_TOURS.get(size_b, {}):
                    return False, None
                # Apply the matching shape class to the menu
                shape_class = _size_to_class_name(target_size)
                if shape_class:
                    _apply("shape", shape_class)
                self.pending_shape_code = codec_text
                return True, {"seed": 0}

            # --- Static shape ID: "NN-NNN[NN...]" ----------------------------
            if len(parts) == 2:
                size = int(parts[0])
                shape_class = _size_to_class_name(size)
                if shape_class is None:
                    return False, None
                if codec_text not in MEGALOMINO_TOURS:
                    return False, None
                _apply("shape", shape_class)
                self.pending_shape_code = codec_text
                return True, {"seed": 0}

        except (ValueError, IndexError):
            pass

        return False, None

    def _game_specific_start_setup(self, seed: Optional[int] = None) -> bool:
        """Select and configure a polyomino puzzle."""
        shape_class = self.get_selection("shape")
        self.board_color_mode = self._get_board_color_mode()
        units = CLASS_INFO[shape_class]["units"]

        # ------------------------------------------------------------------
        # Case 0: 4-piece megalomino mode (9×9 grid, multiple shapes)
        # ------------------------------------------------------------------
        if shape_class == "hippomino":
            result = build_megalomino_puzzle(seed=seed)
            if result is None:
                return False
            code, combined_tour, all_squares = result
            self.selected_shape_id = code
            self.tour_path = combined_tour
            self.transformed_tour_path = combined_tour[:]
            self.polyomino_squares = all_squares
            self.square_size = self._megalomino_square_size()
            # Skip _setup_polyomino() — shapes are already placed at grid coordinates
            self.player_pos = None
            self.visited = set()
            self.visited_moves = {}
            self.move_count = 0
            self.tour_complete = False
            self.is_reentrant = False
            self.stats_written = False
            self.show_path_active = False
            self.track_mode_active = True
            self._init_game_clock()
            return True

        # ------------------------------------------------------------------
        # Case 1: a specific polyomino code was entered by the user
        # ------------------------------------------------------------------
        if self.pending_shape_code:
            code = self.pending_shape_code
            self.pending_shape_code = None

            if is_dynamic_code(code):
                # Reconstruct the large polyomino deterministically
                result = codec_decode(code)
                if result is None:
                    return False
                _, id_a, id_b = result
                tour_path = build_tour_from_ids(id_a, id_b)
                if not tour_path:
                    return False
                self.selected_shape_id = code
            else:
                # Static shape ID
                tour_path = MEGALOMINO_TOURS.get(code)
                if not tour_path:
                    return False
                self.selected_shape_id = code

        # ------------------------------------------------------------------
        # Case 2: random selection
        # ------------------------------------------------------------------
        else:
            if seed is not None:
                random.seed(seed)

            if units >= 16:
                # Generate a random dynamic tour; capture the codec string
                provider = SIZE_TO_PROVIDER.get(units)
                if provider is None:
                    return False
                result = provider.get_random_tour()
                if not result:
                    return False
                codec_str, tour_path = result
                self.selected_shape_id = codec_str
            else:
                available_shapes = get_shapes_by_class(shape_class)
                if not available_shapes:
                    return False
                self.selected_shape_id = random.choice(available_shapes)
                tour_path = MEGALOMINO_TOURS.get(self.selected_shape_id)
                if not tour_path:
                    return False

        self.tour_path = tour_path[:]

        # Transform polyomino coordinates to board coordinates
        self._setup_polyomino()

        # Initialize game state
        self.player_pos = None
        self.visited = set()
        self.visited_moves = {}
        self.move_count = 0
        self.tour_complete = False
        self.is_reentrant = False
        self.stats_written = False

        # Reset modes
        self.show_path_active = False
        self.track_mode_active = True

        # Initialize game clock based on selected mode
        self._init_game_clock()

        return True

    def _megalomino_square_size(self) -> int:
        """Return the square size in pixels for the 9×9 megalomino grid."""
        grid_width = 1
        max_dim = 9
        size = min(88, (self.board_size_pixels - (max_dim + 1) * grid_width) // max_dim)
        return max(10, size)

    def _setup_polyomino(self):
        """Convert polyomino coordinates and randomly rotate/flip."""
        # Get raw coordinates from tour path
        original_path = self.tour_path[:]

        # Apply random transformations
        transforms = random.randint(0, 7)  # 8 possible transformations (4 rotations × 2 flips)

        def rotate_90(coords):
            return [(y, -x) for x, y in coords]

        def flip_h(coords):
            return [(-x, y) for x, y in coords]

        # Transform coordinates
        transformed_coords = original_path[:]
        rotations = transforms % 4
        for _ in range(rotations):
            transformed_coords = rotate_90(transformed_coords)

        if transforms >= 4:
            transformed_coords = flip_h(transformed_coords)

        # Normalize to origin (min x, min y = 0, 0)
        if transformed_coords:
            min_x = min(x for x, y in transformed_coords)
            min_y = min(y for x, y in transformed_coords)
            transformed_coords = [(x - min_x, y - min_y) for x, y in transformed_coords]

        # Store transformed path (preserves order from original tour)
        self.transformed_tour_path = transformed_coords[:]

        # Calculate dimensions and square size
        max_x = max(x for x, y in transformed_coords)
        max_y = max(y for x, y in transformed_coords)
        width = max_x + 1
        height = max_y + 1

        # Determine square size to fit in 720 x 720 board with grid
        grid_width = 1
        max_dim = max(width, height)
        # Leave space for grid lines
        self.square_size = min(90, (self.board_size_pixels - (max_dim + 1) * grid_width) // max_dim)
        self.square_size = max(10, self.square_size)  # Minimum size

        # Create set of polyomino squares (all unique coordinates)
        self.polyomino_squares = set(transformed_coords)

    def _init_game_clock(self) -> None:
        """Initialize the game clock based on selected time mode and clock value.

        Special handling for clock_value == 0 (infinity):
        - When clock is set to 0, always use infinity mode regardless of time_mode
        - This ensures infinity clock counts up from 0 instead of counting down
        - The time_mode setting ("per game" or "per move") is ignored in this case
        """
        clock_value = self.get_selection("clock")  # in seconds
        time_mode = self.get_selection("time")      # "per game", "per move"

        # If clock_value is 0, always use infinity mode (count up from 0)
        # This prevents the game from ending immediately with a 0-second timer
        if clock_value == 0:
            clock_type = ClockType.INFINITY
            settings = ClockSettings(clock_type=clock_type, initial_time_s=0.0)
        elif time_mode == "per game":
            clock_type = ClockType.TIMER
            # For timer mode, count down from clock_value
            settings = ClockSettings(clock_type=clock_type, initial_time_s=float(clock_value))
        elif time_mode == "per move":
            clock_type = ClockType.TIME_PER_MOVE
            # For time per move mode, each move gets clock_value seconds
            settings = ClockSettings(clock_type=clock_type, initial_time_s=float(clock_value))
        else:
            # Default to infinity
            clock_type = ClockType.INFINITY
            settings = ClockSettings(clock_type=clock_type, initial_time_s=0.0)

        self.game_clock = GameClock(settings)

    def _game_specific_make_move(self, target: Tuple[int, int]) -> bool:
        """Apply game-specific move logic."""
        self.move_count += 1

        # Notify game clock of move completion (for TIME_PER_MOVE mode)
        if self.game_clock:
            self.game_clock.on_move_completed()

        # Note: Base class will update player_pos, visited, visited_moves after this returns
        return True

    def _validate_move(self, target: Tuple[int, int]) -> bool:
        """Return True if target is a legal knight move on the polyomino."""
        if not self.player_pos:
            # First move - any polyomino square is valid
            return target in self.polyomino_squares and target not in self.visited

        # Check if it's a legal knight move
        dx = target[0] - self.player_pos[0]
        dy = target[1] - self.player_pos[1]

        return ((dx, dy) in KNIGHT_MOVES and
                target in self.polyomino_squares and
                target not in self.visited)

    def _check_win_condition(self) -> bool:
        """Check if the tour is complete."""
        return self.tour_complete

    def _check_lose_condition(self) -> bool:
        """Check if the player is stuck."""
        if self.game_state != GameState.INGAME:
            return False
        return not self.tour_complete and len(self.legal_moves) == 0

    def _update_legal_moves(self):
        """Update the set of legal moves for the current position."""
        self.legal_moves = set()

        if not self.player_pos:
            self.legal_moves = self.polyomino_squares - self.visited
        else:
            # In INGAME state - only knight moves
            for dx, dy in KNIGHT_MOVES:
                nx, ny = self.player_pos[0] + dx, self.player_pos[1] + dy
                target = (nx, ny)
                if target in self.polyomino_squares and target not in self.visited:
                    self.legal_moves.add(target)

    def _write_endgame_stats(self):
        """Write game results to CSV file."""
        try:
            stats_file = os.path.join(self.base_dir, "hippomino", "megalomino_stats.csv")
            file_exists = os.path.exists(stats_file)

            with open(stats_file, 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["shape_id", "squares_completed"])
                writer.writerow([self.selected_shape_id, len(self.visited)])
        except Exception as e:
            print(f"Warning: Could not write stats: {e}")

    def _format_shape_name(self, shape_id: Optional[str] = None) -> str:
        """Get the shape ID for display, using the selected shape if none provided."""
        if not shape_id:
            shape_id = self.selected_shape_id

        if not shape_id:
            return "shape"

        return shape_id

    def toggle_show_path(self) -> None:
        """Toggle showing the original tour path."""
        self.show_path_active = not self.show_path_active
        self._update_button_states()

    def toggle_track_mode(self) -> None:
        """Toggle track mode (show move numbers)."""
        self.track_mode_active = not self.track_mode_active
        self._update_button_states()

    def toggle_peek_mode(self):
        """Toggle peek mode (temporarily show the original tour path while in-game)."""
        self.peek_mode_active = not self.peek_mode_active
        self.show_path_active = self.peek_mode_active

    def _check_endgame_conditions(self) -> Optional[str]:
        """Check if game is over and return end state."""
        # Check if tour is complete
        if len(self.visited) == len(self.polyomino_squares):
            self.tour_complete = True
            self.peek_mode_active = False
            # Check if reentrant (can return to start from final position)
            if self.player_pos and self.visited_moves:
                start_pos = min(self.visited_moves.items(), key=lambda x: x[1])[0]
                dx = self.player_pos[0] - start_pos[0]
                dy = self.player_pos[1] - start_pos[1]
                if (dx, dy) in KNIGHT_MOVES:
                    self.is_reentrant = True
            return "tour_complete"
        elif self.game_state == GameState.INGAME and not self.legal_moves:
            return "no_legal_moves"
        return None

    def _capture_game_state(self) -> Dict[str, Any]:
        """Snapshot current game state for replay/undo."""
        return {
            "player_pos": self.player_pos,
            "visited": self.visited.copy(),
            "visited_moves": self.visited_moves.copy(),
            "move_count": self.move_count,
            "tour_complete": self.tour_complete,
            "is_reentrant": self.is_reentrant,
        }

    def _restore_game_state(self, state: Dict[str, Any]) -> None:
        """Restore game state from a snapshot."""
        self.player_pos = state["player_pos"]
        self.visited = state["visited"].copy()
        self.visited_moves = state["visited_moves"].copy()
        self.move_count = state["move_count"]
        self.tour_complete = state["tour_complete"]
        self.is_reentrant = state["is_reentrant"]
        self._update_legal_moves()

    def _calculate_hint_degrees(self) -> None:
        """Compute hint degrees (not used in megalomino)."""
        self.hint_degrees = {}

    # ================================================================== #
    #  Button setup                                                       #
    # ================================================================== #

    def _build_buttons(self) -> None:
        """Build game-specific buttons."""
        f = self.font
        self.buttons: Dict[str, Button] = {
            "start": Button(pygame.Rect(0, 0, 0, 0), "start",
                            f, (255, 255, 255), (92, 192, 92), self.start_game),
            "enter_code": Button(pygame.Rect(0, 0, 0, 0), "enter shape code",
                                 f, (255, 255, 255), (224, 0, 96),
                                 self.toggle_codec_input),
            "copy_code": Button(pygame.Rect(0, 0, 0, 0), "copy shape code",
                                f, (255, 255, 255), (224, 0, 96),
                                self.copy_code_to_clipboard),
            "show_path": Button(pygame.Rect(0, 0, 0, 0), "show tour path",
                                f, (255, 255, 255), (255, 128, 96),
                                self.toggle_show_path),
            "track_mode": Button(pygame.Rect(0, 0, 0, 0), "show move #'s",
                                 f, (255, 255, 255), (255, 92, 128),
                                 self.toggle_track_mode),
            "undo_mode": Button(pygame.Rect(0, 0, 0, 0), "undo last move",
                                f, (255, 255, 255), (64, 128, 255),
                                self.undo_move),
            "resign": Button(pygame.Rect(0, 0, 0, 0), "resign",
                             f, (255, 255, 255), (107, 70, 51), self.resign_game),
            "retry": Button(pygame.Rect(0, 0, 0, 0), "retry",
                            f, (255, 255, 255), (92, 192, 92), self.retry_game),
            "new_game": Button(pygame.Rect(0, 0, 0, 0), "new game",
                              f, (255, 255, 255), (92, 192, 92), self.new_game),
            "replay_mode": Button(pygame.Rect(0, 0, 0, 0), "start replay",
                                  f, (255, 255, 255), (64, 128, 255),
                                  self.toggle_replay_mode),
            "replay_prev": Button(pygame.Rect(0, 0, 0, 0), "-",
                                  f, (255, 255, 240), (64, 128, 255),
                                  lambda: self.navigate_replay(-1)),
            "replay_next": Button(pygame.Rect(0, 0, 0, 0), "+",
                                  f, (255, 255, 240), (64, 128, 255),
                                  lambda: self.navigate_replay(1)),
            "exit": Button(pygame.Rect(0, 0, 0, 0), "exit",
                          f, (255, 255, 255), (255, 0, 0), self.quit_game),
            "peek": Button(pygame.Rect(0, 0, 0, 0), "peek",
                           f, (255, 255, 240), (232, 200, 150),
                                  self.toggle_peek_mode),
        }

    def new_game(self):
        """Reset puzzle and player state, and return to menu configuration."""
        self.selected_shape_id = None
        self.pending_shape_code = None
        self.tour_path = []
        self.transformed_tour_path = []
        self.polyomino_squares = set()
        self.player_pos = None
        self.visited = set()
        self.visited_moves = {}
        self.move_count = 0
        self.tour_complete = False
        self.is_reentrant = False
        self.stats_written = False
        self.replay_states = []
        self.legal_moves = set()
        self.show_path_active = False
        self.track_mode_active = True
        self.peek_mode_active = False
        self.game_state = GameState.MENU

        # Reset game clock
        self.game_clock = None

    def _update_button_states(self):
        """Update which buttons are active/visible based on game state."""
        # Start button - in MENU: active normally, or only when a valid code
        # has been entered if codec input mode is active
        if self.seed_mode_active:
            self.buttons["start"].active = (
                self.game_state == GameState.MENU and self._is_valid_codec_length()
            )
        else:
            self.buttons["start"].active = self.game_state == GameState.MENU

        # Enter/cancel code - active in MENU
        self.buttons["enter_code"].active = self.game_state == GameState.MENU
        self.buttons["enter_code"].text = (
            "cancel code entry" if self.seed_mode_active else "enter shape code"
        )
        self.buttons["enter_code"].bg_color = (
            (224, 64, 128) if self.seed_mode_active else (224, 0, 96)
        )

        # Copy code - active in INGAME, ENDGAME when a code exists
        self.buttons["copy_code"].active = (
            self.game_state in (GameState.INGAME, GameState.ENDGAME)
            and bool(self.puzzle_code)
        )
        self.buttons["copy_code"].bg_color = (224, 64, 128) if self.copy_clicked else (224, 0, 96)
        self.buttons["copy_code"].text = (
            "code copied!" if self.copy_clicked else "copy shape code"
        )

        # Show path - active in ENDGAME only
        self.buttons["show_path"].active = (self.game_state == GameState.ENDGAME)

        # Track mode - active in INGAME, ENDGAME
        self.buttons["track_mode"].active = self.game_state in (
            GameState.INGAME, GameState.ENDGAME)

        # Undo - active in INGAME when there's history
        self.buttons["undo_mode"].active = (
            self.game_state == GameState.INGAME and len(self.replay_states) > 0)

        # Resign - active in INGAME and ENDGAME
        self.buttons["resign"].active = self.game_state == GameState.INGAME

        # Retry - active in ENDGAME
        self.buttons["retry"].active = self.game_state == GameState.ENDGAME

        # New game - active in ENDGAME
        self.buttons["new_game"].active = self.game_state == GameState.ENDGAME

        # Replay mode - active in ENDGAME
        self.buttons["replay_mode"].active = self.game_state == GameState.ENDGAME
        self.buttons["replay_mode"].text = "end replay" if self.replay_mode_active else "start replay"

        # Exit always active
        self.buttons["exit"].active = True

        # Peek mode - INGAME only
        self.buttons["peek"].active = self.game_state == GameState.INGAME


    # ================================================================== #
    #  Rendering                                                          #
    # ================================================================== #

    def _render_game_specific_board(self, screen: pygame.Surface) -> None:
        """Render the megalomino board."""
        # Get screen center
        screen_w, screen_h = screen.get_size()
        center_x = screen_w // 2
        center_y = screen_h // 2

        # Draw background board (720 x 720)
        board_rect = pygame.Rect(
            center_x - self.board_size_pixels // 2,
            center_y - self.board_size_pixels // 2,
            self.board_size_pixels,
            self.board_size_pixels
        )

        pygame.draw.rect(screen, GRID_COLOR, board_rect)

        # --- preview demo in MENU mode ---
        if self.game_state == GameState.MENU:
            self._render_demo(screen, center_x, center_y)

        # Draw polyomino squares
        if self.polyomino_squares:
            self._render_polyomino(screen, center_x, center_y)

    def _render_demo(self, screen: pygame.Surface, center_x: int, center_y: int):
        """Render the demo animation in MENU state."""
        if not self.demo_tour_path or not self.demo_polyomino_squares:
            return

        grid_width = 1

        # Calculate polyomino dimensions
        coords = list(self.demo_polyomino_squares)
        min_x = min(x for x, y in coords)
        max_x = max(x for x, y in coords)
        min_y = min(y for x, y in coords)
        max_y = max(y for x, y in coords)
        width = max_x - min_x + 1
        height = max_y - min_y + 1

        # Calculate offset to center polyomino
        board_width = width * self.square_size + (width + 1) * grid_width
        board_height = height * self.square_size + (height + 1) * grid_width
        offset_x = center_x - board_width // 2
        offset_y = center_y - board_height // 2

        # Get current demo position based on state
        current_pos = None
        visited_positions = set()
        visited_moves = {}

        if self.demo_state == "animating" or self.demo_state == "complete":
            # Show positions up to and including current index
            num_to_show = min(self.demo_path_index + 1, len(self.demo_tour_path))
            for i in range(num_to_show):
                pos = self.demo_tour_path[i]
                visited_positions.add(pos)
                visited_moves[pos] = i

            if self.demo_path_index < len(self.demo_tour_path):
                current_pos = self.demo_tour_path[self.demo_path_index]

        # Get board color mode from menu
        board_color_mode = self._get_board_color_mode()

        # Draw each square
        for poly_x, poly_y in self.demo_polyomino_squares:
            # Calculate position
            px = offset_x + (poly_x - min_x) * (self.square_size + grid_width) + grid_width
            py = offset_y + (poly_y - min_y) * (self.square_size + grid_width) + grid_width

            # Determine color
            pos = (poly_x, poly_y)
            if pos in visited_positions:
                # Visited square - use visited colors
                is_even = (poly_x + poly_y) % 2 == 0
                square_color = (DK_VISITED if is_even else LT_VISITED) if board_color_mode == "chessboard" else LT_VISITED
            else:
                # Unvisited square - use regular colors
                if board_color_mode == "chessboard":
                    is_even = (poly_x + poly_y) % 2 == 0
                    square_color = DK_SQUARE if is_even else LT_SQUARE
                else:
                    square_color = DK_SQUARE

            # Draw square
            square_rect = pygame.Rect(px, py, self.square_size, self.square_size)
            pygame.draw.rect(screen, square_color, square_rect)
            pygame.draw.rect(screen, GRID_COLOR, square_rect, grid_width)

            # Draw move number on visited squares
            if pos in visited_moves:
                move_num = visited_moves[pos] + 1  # 1-indexed for display
                text_surf = self.font.render(str(move_num), True, (0, 0, 0))
                text_rect = text_surf.get_rect(center=(px + self.square_size // 2, py + self.square_size // 2 + TEXT_OFFSET_Y))
                screen.blit(text_surf, text_rect)

        # Draw knight on current position
        if current_pos and current_pos in self.demo_polyomino_squares:
            poly_x, poly_y = current_pos
            px = offset_x + (poly_x - min_x) * (self.square_size + grid_width) + grid_width
            py = offset_y + (poly_y - min_y) * (self.square_size + grid_width) + grid_width

            if self.knight_image:
                knight_scaled = pygame.transform.scale(
                    self.knight_image,
                    (self.square_size - 4, self.square_size - 4)
                )
                knight_rect = knight_scaled.get_rect(center=(px + self.square_size // 2, py + self.square_size // 2))
                screen.blit(knight_scaled, knight_rect)

    def _render_polyomino(self, screen: pygame.Surface, center_x: int, center_y: int):
        """Render the polyomino shape."""
        grid_width = 1

        # Calculate polyomino dimensions
        if not self.polyomino_squares:
            return

        coords = list(self.polyomino_squares)
        min_x = min(x for x, y in coords)
        max_x = max(x for x, y in coords)
        min_y = min(y for x, y in coords)
        max_y = max(y for x, y in coords)
        width = max_x - min_x + 1
        height = max_y - min_y + 1

        # Calculate offset to center polyomino
        board_width = width * self.square_size + (width + 1) * grid_width
        board_height = height * self.square_size + (height + 1) * grid_width
        offset_x = center_x - board_width // 2
        offset_y = center_y - board_height // 2

        # Get display state (may differ when replaying)
        if self.game_state == GameState.ENDGAME and self.replay_mode_active and self.replay_states:
            disp = self.replay_states[self.replay_index]
            disp_pos = disp["player_pos"]
            disp_visited = disp["visited"]
            disp_visited_moves = disp["visited_moves"]
        else:
            disp_pos = self.player_pos
            disp_visited = self.visited
            disp_visited_moves = self.visited_moves

        # Draw each square
        for poly_x, poly_y in self.polyomino_squares:
            # Calculate position
            px = offset_x + (poly_x - min_x) * (self.square_size + grid_width) + grid_width
            py = offset_y + (poly_y - min_y) * (self.square_size + grid_width) + grid_width

            # Determine color
            if self.board_color_mode == "chessboard":
                # Checkerboard pattern
                is_even = (poly_x + poly_y) % 2 == 0
                square_color = DK_SQUARE if is_even else LT_SQUARE
            else:
                # monochrome color
                square_color = DK_SQUARE

            # Override with visited color if visited
            pos = (poly_x, poly_y)
            pos = (poly_x, poly_y)
            if pos in disp_visited:
                is_even = (poly_x + poly_y) % 2 == 0
                square_color = DK_VISITED if is_even and self.board_color_mode == "chessboard" else LT_VISITED
            elif self.game_state == GameState.ENDGAME:
                # Only show missed colors when not in replay mode
                if not (self.replay_mode_active and self.replay_states):
                    is_even = (poly_x + poly_y) % 2 == 0
                    square_color = DK_MISSED if is_even and self.board_color_mode == "chessboard" else LT_MISSED

            # Draw square
            square_rect = pygame.Rect(px, py, self.square_size, self.square_size)
            pygame.draw.rect(screen, square_color, square_rect)

            # Draw grid border
            pygame.draw.rect(screen, GRID_COLOR, square_rect, grid_width)

            # Draw move number or path number
            if self.track_mode_active and pos in disp_visited_moves:
                # Show actual move number (1-indexed for display)
                # visited_moves stores 0-indexed values: start=0, first=1, second=2, etc.
                # Adding 1 displays as: start=1, first=2, second=3, etc.
                move_num = disp_visited_moves[pos] + 1
                text_surf = self.font.render(str(move_num), True, (0, 0, 0))
                text_rect = text_surf.get_rect(topleft=(px + 10, py + TEXT_OFFSET_Y))
                screen.blit(text_surf, text_rect)

            if (self.show_path_active or self.peek_mode_active) and self.transformed_tour_path:
                # Show original tour path number (1-indexed for display)
                # transformed_tour_path is a list, index() returns 0-based index
                # Adding 1 makes it match the move number display (1-indexed)
                try:
                    path_idx = self.transformed_tour_path.index(pos) + 1
                    text_surf = self.font.render(str(path_idx), True, (107, 70, 51))
                    text_rect = text_surf.get_rect(topright=(px + self.square_size - 10, py + TEXT_OFFSET_Y))
                    screen.blit(text_surf, text_rect)
                except ValueError:
                    pass  # Position not in tour path

        # Draw knight piece on current position
        if disp_pos and disp_pos in self.polyomino_squares:
            poly_x, poly_y = disp_pos
            px = offset_x + (poly_x - min_x) * (self.square_size + grid_width) + grid_width
            py = offset_y + (poly_y - min_y) * (self.square_size + grid_width) + grid_width

            if self.knight_image:
                # Scale knight image to fit square
                knight_scaled = pygame.transform.scale(
                    self.knight_image,
                    (self.square_size - 4, self.square_size - 4)
                )
                knight_rect = knight_scaled.get_rect(center=(px + self.square_size // 2, py + self.square_size // 2))
                screen.blit(knight_scaled, knight_rect)

    def _render_game_specific_stats(
            self, screen: pygame.Surface, stats_panel: UIPanel
    ) -> None:
        line_height = self.font.get_linesize() + UI_SPACE
        stats_bounds = stats_panel.get_bounds("STATS_PANEL")

        # Display clock during game (INGAME, WAITING) and endgame
        if self.game_state != GameState.MENU and self.game_clock:
            # Use chess_clock formatting which takes precedence
            time_seconds = self.game_clock.get_time_seconds()
            clock_disp = format_hms(time_seconds)

            # Red color if time is low (less than 30 seconds for countdown modes)
            if self.game_clock.settings.clock_type in (ClockType.TIMER, ClockType.TIME_PER_MOVE):
                clock_color = (200, 0, 0) if time_seconds < 10 else (0, 0, 0)
            else:
                clock_color = (0, 0, 0)

            clock_y = stats_panel.get_line_y("STATS_PANEL", 9, line_height)
            clock_surf = self.font.render(clock_disp, True, clock_color)
            screen.blit(clock_surf, clock_surf.get_rect(centerx=stats_bounds["center_x"], top=clock_y))

        # Show endgame messages
        if self.game_state == GameState.ENDGAME and self.end_state:
            if self.end_state == "tour_complete" and self.tour_complete:
                tour_type = "reentrant" if self.is_reentrant else "open"
                msg = f"{tour_type} tour complete"
                msg_color = (0, 64, 128) if self.is_reentrant else (0, 128, 0)
            else:
                end_messages = {
                    "no_legal_moves": ("no legal moves", (192, 0, 0)),
                    "resignation": ("resigned", (107, 70, 51)),
                    "timeout": ("time's up", (0, 0, 0)),
                }
                msg, msg_color = end_messages.get(self.end_state, ("game over", (0, 0, 0)))

            em_s = self.font_large.render(msg, True, msg_color)
            em_y = stats_panel.get_line_y("STATS_PANEL", 5, line_height)
            screen.blit(em_s, em_s.get_rect(centerx=stats_bounds["center_x"], top=em_y))


    def render(self, screen: pygame.Surface) -> None:
        """Render the full game frame."""
        win_width, win_height = screen.get_size()
        screen.fill(BKG_COLOR)

        # Clear widget rects before rendering
        self.widget_rects.clear()

        margin = UI_SPACE
        panel_width = UI_SPACE * 28
        msg_left = margin
        msg_top = margin
        msg_bottom = win_height - margin
        msg_right = msg_left + panel_width
        right_left = win_width - panel_width - margin

        left_panel_rect = pygame.Rect(msg_left, msg_top, panel_width, msg_bottom - msg_top)
        right_panel_rect = pygame.Rect(right_left, msg_top, panel_width, msg_bottom - msg_top)

        left_panel = UIPanel(left_panel_rect, gap=0)
        right_panel = UIPanel(right_panel_rect, gap=0)

        left_panel.draw_panel(screen, "MENU_PANEL", LT_SQUARE, GRID_COLOR)
        left_panel.draw_panel(screen, "BUTTON_PANEL", LT_SQUARE, GRID_COLOR)
        right_panel.draw_panel(screen, "PIECE_PANEL", LT_SQUARE, GRID_COLOR)
        right_panel.draw_panel(screen, "STATS_PANEL", LT_SQUARE, GRID_COLOR)

        # Render game board in center
        self._render_game_specific_board(screen)

        # Render UI panels
        self._render_left_panel(screen, left_panel, msg_left, msg_right, msg_bottom)
        self._render_right_panel(screen, right_panel)

    def _render_left_panel(self, screen, left_panel, msg_left, msg_right, msg_bottom):
        """Render left panel with menu and buttons."""
        btn_w = int(UI_SPACE * 1.5)
        line_height = self.font.get_linesize() + UI_SPACE

        # Update button states based on game state
        self._update_button_states()

        # ---- MENU_PANEL: selector rows ----
        menu_bounds = left_panel.get_bounds("MENU_PANEL")
        text_x = menu_bounds["left"] + UI_SPACE

        # Calculate max label width for consistent alignment
        max_lbl_w = max(self.font.render(lbl + ":", True, (0, 0, 0)).get_width()
                        for lbl, _, _ in self.menu_items)
        minus_x = text_x + max_lbl_w + UI_SPACE * 3
        plus_x = menu_bounds["right"] - UI_SPACE * 6

        for i, (label, values, sel_idx) in enumerate(self.menu_items):
            panel_y = left_panel.get_line_y("MENU_PANEL", i, line_height)
            row_cy = panel_y + btn_w // 2

            # Render label
            lbl_surf = self.font.render(f"{label}", True, (0, 0, 0))
            screen.blit(lbl_surf, lbl_surf.get_rect(midleft=(text_x, row_cy)))

            # Format and render selection value centered between buttons
            sel_val = values[sel_idx]
            if label == "clock":
                sel_text = _format_clock(sel_val)
            else:
                sel_text = str(sel_val)
            sel_surf = self.font.render(sel_text, True, (0, 0, 0))
            sel_cx = (minus_x + btn_w + plus_x) / 2
            screen.blit(sel_surf, sel_surf.get_rect(center=(sel_cx, row_cy)))

            # Draw minus and plus buttons only in MENU state
            if self.game_state == GameState.MENU:
                # Minus button
                mr = pygame.Rect(minus_x, panel_y, btn_w, btn_w)
                pygame.draw.rect(screen, DK_SQUARE, mr)
                lt = self.font.render("<", True, (0, 160, 0))
                screen.blit(lt, lt.get_rect(center=mr.center))
                self.widget_rects[("minus", i)] = mr

                # Plus button
                pr = pygame.Rect(plus_x, panel_y, btn_w, btn_w)
                pygame.draw.rect(screen, DK_SQUARE, pr)
                gt = self.font.render(">", True, (220, 0, 0))
                screen.blit(gt, gt.get_rect(center=pr.center))
                self.widget_rects[("plus", i)] = pr

        # Retry (MENU_PANEL line 7 = index 6, ENDGAME only)
        self.buttons["retry"].rect = left_panel.get_widget_rect("MENU_PANEL", 6, BTW, BTH)
        if self.buttons["retry"].active:
            self.buttons["retry"].draw(screen)

        # Enter / cancel shape code (MENU_PANEL line 7 = index 7, MENU only)
        self.buttons["enter_code"].rect = left_panel.get_widget_rect("MENU_PANEL", 8, BTW, BTH)
        if self.buttons["enter_code"].active:
            self.buttons["enter_code"].draw(screen)

        # Codec text input (shown below enter_code button when active)
        if self.game_state == GameState.MENU and self.seed_mode_active:
            input_y = left_panel.get_line_y("MENU_PANEL", 9, line_height)
            input_x = menu_bounds["left"] + (menu_bounds["width"] - BTW) // 2
            self.codec_input.rect = pygame.Rect(input_x, input_y, BTW, BTH)
            self.codec_input.draw(screen)

        # Shape code display when in-game or at end (MENU_PANEL line 9 = index 8)
        if (self.puzzle_code and
                self.game_state in (GameState.INGAME, GameState.ENDGAME)):
            code_y = left_panel.get_line_y("MENU_PANEL", 9, line_height)
            code_surf = self.font.render(self.puzzle_code, True, (0, 0, 0))
            screen.blit(code_surf, code_surf.get_rect(
                center=(menu_bounds["center_x"], code_y + BTH // 2)))

        # Copy shape code (MENU_PANEL line 9 = index 9, INGAME, ENDGAME)
        self.buttons["copy_code"].rect = left_panel.get_widget_rect("MENU_PANEL", 8, BTW, BTH)
        if self.buttons["copy_code"].active:
            self.buttons["copy_code"].draw(screen)

        # Shape ID display (demo during MENU, selected during play)
        if self.game_state == GameState.MENU:
            shape_id = self.demo_shape_id
        else:
            shape_id = self.selected_shape_id

        if shape_id:
            shape_text = self._format_shape_name(shape_id)
            text_surf = self.font.render(shape_text, True, (0, 0, 0))
            text_x = menu_bounds["center_x"] - text_surf.get_width() // 2
            text_y = menu_bounds["top"] + UI_SPACE * 32
            #screen.blit(text_surf, (text_x, text_y))


        # ---- BUTTON_PANEL ----

        # Start button (line 1 = index 0, MENU only)
        self.buttons["start"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        if self.buttons["start"].active:
            self.buttons["start"].draw(screen)

        # Toggle tour path (line 1 = index 0, ENDGAME only)
        self.buttons["show_path"].text = "hide tour path" if self.show_path_active else "show tour path"
        self.buttons["show_path"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        if self.buttons["show_path"].active:
            self.buttons["show_path"].draw(screen)

        # Toggle move #'s mode (line 5 = index 4, INGAME, ENDGAME)
        self.buttons["track_mode"].text = "hide move #'s" if self.track_mode_active else "show move #'s"
        self.buttons["track_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 2, BTW, BTH)
        if self.buttons["track_mode"].active:
            self.buttons["track_mode"].draw(screen)

        # Undo (line 7 = index 6, INGAME)
        self.buttons["undo_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 4, BTW, BTH)
        if self.buttons["undo_mode"].active:
            self.buttons["undo_mode"].draw(screen)

        # Replay (line 7 = index 6, ENDGAME with - and +)
        self.buttons["replay_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 4, BTW, BTH)
        if self.buttons["replay_mode"].active:
            self.buttons["replay_mode"].draw(screen)

            # Replay navigation buttons
            if self.replay_mode_active and self.replay_states:
                rm_rect = self.buttons["replay_mode"].rect
                nav_w = BTW // 4
                if self.replay_index > 0:
                    self.buttons["replay_prev"].active = True
                    self.buttons["replay_prev"].rect = pygame.Rect(
                        rm_rect.left - nav_w - 4, rm_rect.top, nav_w, BTH)
                    self.buttons["replay_prev"].draw(screen)
                else:
                    self.buttons["replay_prev"].active = False

                if self.replay_index < len(self.replay_states) - 1:
                    self.buttons["replay_next"].active = True
                    self.buttons["replay_next"].rect = pygame.Rect(
                        rm_rect.right + 4, rm_rect.top, nav_w, BTH)
                    self.buttons["replay_next"].draw(screen)
                else:
                    self.buttons["replay_next"].active = False

        # Resign (line 9 = index 8, INGAME)
        self.buttons["resign"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 8, BTW, BTH)
        if self.buttons["resign"].active:
            self.buttons["resign"].draw(screen)

        # New game (line 9 = index 8, ENDGAME)
        self.buttons["new_game"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 8, BTW, BTH)
        if self.buttons["new_game"].active:
            self.buttons["new_game"].draw(screen)



        # Peek button (line 11 = index 10, left, INGAME)
        button_bounds = left_panel.get_bounds("BUTTON_PANEL")
        self.buttons["peek"].rect = pygame.Rect(
            button_bounds["left"] + 20,
            button_bounds["bottom"] - BTH - UI_SPACE,
            BTW // 2,
            BTH
        )
        if self.buttons["peek"].active:
            self.buttons["peek"].draw(screen)

        # Exit button
        self.buttons["exit"].rect = pygame.Rect(
            button_bounds["right"] - (BTW // 2) - 20,
            button_bounds["bottom"] - BTH - UI_SPACE,
            BTW // 2,
            BTH
        )
        if self.buttons["exit"].active:
            self.buttons["exit"].draw(screen)

        # Render message on button panel if needed
#        button_bounds = left_panel.get_bounds("BUTTON_PANEL")
#        if self.game_state == GameState.INGAME and not self.player_pos:
#            msg = "click a starting square"
#            text_surf = self.font.render(msg, True, (0, 0, 192))
#            text_x = button_bounds["center_x"] - text_surf.get_width() // 2
#            text_y = button_bounds["top"] + UI_SPACE * 2
            #screen.blit(text_surf, (text_x, text_y))


    def _render_right_panel(self, screen, right_panel):
        """Render right panel with piece and stats."""

        # Piece panel
        piece_bounds = right_panel.get_bounds("PIECE_PANEL")
        px_center = piece_bounds["center_x"]
        py_center = piece_bounds["center_y"]

        if self.knight_image:
            # Scale knight to fit nicely in panel
            panel_size = min(piece_bounds["width"], piece_bounds["height"])
            knight_size = int(panel_size * 0.4)
            knight_scaled = pygame.transform.scale(self.knight_image, (knight_size, knight_size))
            knight_rect = knight_scaled.get_rect(center=(px_center, py_center))
            screen.blit(knight_scaled, knight_rect)


        # Stats panel - delegate to game-specific method
        self._render_game_specific_stats(screen, right_panel)

    def update(self, dt: float) -> None:
        """Update game state. Check for endgame and write stats."""
        super().update(dt)

        # Update game clock during INGAME
        if self.game_state == GameState.INGAME and self.game_clock:
            self.game_clock.update(time.time())

            # Check if clock has expired (for TIMER and TIME_PER_MOVE modes)
            if self.game_clock.is_expired():
                self.final_elapsed = int(self.paused_elapsed + (
                    (time.time() - self.clock_start_time)
                    if self.clock_start_time else 0))
                self.end_state = "timeout"
                self.game_state = GameState.ENDGAME
                # Stop the clock when game ends
                self.game_clock.stop(time.time())

        # Update demo animation when in MENU state
        if self.game_state == GameState.MENU:
            self._update_demo(dt)

        # Write stats when transitioning to ENDGAME
        if self.game_state == GameState.ENDGAME and not self.stats_written:
            # Stop the clock if it's still running
            if self.game_clock and self.game_clock.running:
                self.game_clock.stop(time.time())
            self._write_endgame_stats()
            self.stats_written = True

    def handle_window_focus(self, state_attr: int, gain_attr: int) -> None:
        """Pause the clock on focus loss, resume on focus gain."""
        super().handle_window_focus(state_attr, gain_attr)

        # Also handle game_clock pause/resume
        # state_attr & 4 checks if the event is related to window focus (SDL_APPACTIVE)
        if state_attr & 4:
            if gain_attr == 0:  # Lost focus
                if self.game_clock and self.game_state == GameState.INGAME:
                    self.game_clock.stop(time.time())
            elif gain_attr == 1:  # Gained focus
                # Resume clock if game is in progress and clock has been started
                if self.game_clock and self.game_state == GameState.INGAME and self.clock_start_time is not None:
                    self.game_clock.start(time.time())

    def _update_demo(self, dt: float) -> None:
        """Update the menu demo animation."""
        if not self.demo_tour_path:
            return

        if self.demo_state == "paused":
            # Wait for 2 seconds before starting/restarting
            self.demo_pause_timer += dt
            if self.demo_pause_timer >= 10.0:
                self.demo_pause_timer = 0.0
                self.demo_state = "animating"
                self.demo_path_index = 0
                self.demo_timer = 0.0

        elif self.demo_state == "animating":
            # Wait 2 seconds on each square
            self.demo_timer += dt
            if self.demo_timer >= 1500.0:
                self.demo_timer = 0.0
                self.demo_path_index += 1

                # Check if we've reached the end
                if self.demo_path_index >= len(self.demo_tour_path):
                    self.demo_state = "complete"
                    self.demo_pause_timer = 0.0

        elif self.demo_state == "complete":
            # Pause for 2 seconds, then start over with a new shape
            self.demo_pause_timer += dt
            if self.demo_pause_timer >= 2.0:
                self._init_demo()

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle pygame events."""
        # Let base class handle common events
        result = super().handle_event(event)
        if not result:
            return False

        # Handle mouse clicks
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # Check for menu selector button clicks (minus/plus)
            for key, rect in self.widget_rects.items():
                if rect.collidepoint(mx, my):
                    action, item_idx = key
                    lbl, vals, cur = self.menu_items[item_idx]
                    if action == "plus":
                        self.menu_items[item_idx] = (lbl, vals, (cur + 1) % len(vals))
                        # Reset demo if shape class changed
                        if lbl == "shape":
                            self._init_demo()
                    elif action == "minus":
                        self.menu_items[item_idx] = (lbl, vals, (cur - 1) % len(vals))
                        # Reset demo if shape class changed
                        if lbl == "shape":
                            self._init_demo()
                    return True

            # Handle board clicks
            screen_size = pygame.display.get_surface().get_size()
            pos = event.pos

            if self.game_state == GameState.INGAME and not self.player_pos:
                # Click to select starting square (first move)
                clicked_square = self._get_square_at_pixel(pos, screen_size)
                if clicked_square and clicked_square in self.polyomino_squares:
                    # Start the clock on first move
                    if self.clock_start_time is None:
                        self.clock_start_time = time.time()

                    # Start the game clock
                    if self.game_clock:
                        self.game_clock.start(time.time())
                        # For TIME_PER_MOVE mode, call on_move_completed() to reset the clock
                        # so the player gets time for their first actual move
                        if self.game_clock.settings.clock_type == ClockType.TIME_PER_MOVE:
                            self.game_clock.on_move_completed()

                    self.player_pos = clicked_square
                    self.visited.add(self.player_pos)
                    self.visited_moves[self.player_pos] = 0
                    self._update_legal_moves()
                    return True
            elif self.game_state == GameState.INGAME and self.player_pos:
                # Click to move (subsequent moves)
                clicked_square = self._get_square_at_pixel(pos, screen_size)
                if clicked_square and clicked_square in self.legal_moves:
                    self.make_move(clicked_square)
                    return True

        return True

    def _get_square_at_pixel(self, pixel_pos: Tuple[int, int], screen_size: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        """Convert pixel coordinates to polyomino square coordinates."""
        screen_w, screen_h = screen_size
        center_x = screen_w // 2
        center_y = screen_h // 2

        if not self.polyomino_squares:
            return None

        coords = list(self.polyomino_squares)
        min_x = min(x for x, y in coords)
        max_x = max(x for x, y in coords)
        min_y = min(y for x, y in coords)
        max_y = max(y for x, y in coords)
        width = max_x - min_x + 1
        height = max_y - min_y + 1

        grid_width = 1
        board_width = width * self.square_size + (width + 1) * grid_width
        board_height = height * self.square_size + (height + 1) * grid_width
        offset_x = center_x - board_width // 2
        offset_y = center_y - board_height // 2

        px, py = pixel_pos

        # Check each square
        for poly_x, poly_y in self.polyomino_squares:
            sx = offset_x + (poly_x - min_x) * (self.square_size + grid_width) + grid_width
            sy = offset_y + (poly_y - min_y) * (self.square_size + grid_width) + grid_width

            if sx <= px <= sx + self.square_size and sy <= py <= sy + self.square_size:
                return poly_x, poly_y

        return None


# Export constants and functions for use in entry point
__all__ = [
    "MegalominoController",
    "GameState",
    "FPS",
    "MAX_CLOCK_SECONDS",
    "BOARD_COLOR_CHOICES",
    "CLASS_NAMES",
    "CLOCK_CHOICES",
    "CLOCK_MODES",
]