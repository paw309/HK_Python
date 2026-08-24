"""
gunkan_controller.py

Game controller for Gunkan: a two-player battleship-inspired game.
Each player owns a hidden set of shapes.  Players race to land on every
square of their opponent's shapes before the opponent finds all of theirs.

Based on duelomino_controller.py, sharing the same UI layout and bot logic.
"""

import os
import math
import random
import time
from typing import Optional, List, Tuple, Set, Dict, Any

import pygame

# sharedlib imports (BASE_DIR must already be on sys.path)
import piecekeeper as pk
import polyomino_data as pd
import polyomino_ratings as pr
from gameboard import BoardModel, BoardRenderer
from uipanel import UIPanel
from puzzle_codec import encode_params, decode_params
from widgets import Button
from base_game_controller import BaseGameController, GameState
from move_system import get_legal_moves_for_board
from move_hint import calculate_hint_degrees
from common_utils import format_time as _format_time

from pyversion.polyominoes.duelomino_bot import BotLevel, make_bot_move

# --- constants ---

BOARD_MIN = 8
BOARD_MAX = 16
BOARD_DEFAULT = 14
FPS = 60
UI_SPACE = 10
BTW = int(UI_SPACE * 15)
BTH = int(UI_SPACE * 3)

SHAPES_CHOICES = ["classic", "mixed"]
PLAYER_ONE_CHOICES = ["human", "bot"]
OPPONENT_LEVEL_CHOICES = ["1", "2", "3", "4", "5"]
CLOCK_MODES = ["game", "move"]
#MAX_CLOCK_SECONDS = 330

# Board colours
LT_SQUARE = (255, 255, 240)
DK_SQUARE = (232, 200, 150)
GRID_COLOR = (107, 70, 51)
BACK_COLOR = (244, 228, 195)

# Player colours
PLAYER_LABELS = {1: "blue", 2: "red"}
PLAYER_MSG_COLORS = {1: (0, 0, 192), 2: (192, 0, 0)}

# Player 1 (Blue) visited squares
P1_LT_VISITED = (192, 220, 248)
P1_DK_VISITED = (128, 160, 225)

# Player 2 (Red) visited squares
P2_LT_VISITED = (255, 192, 192)
P2_DK_VISITED = (225, 128, 128)

# Gray (no polyomino)
LT_VISITED = (224, 224, 224)
DK_VISITED = (192, 192, 192)

# Shape colors per owner
SHAPE_P1_COLOR = (100, 149, 237)   # cornflower blue — P1's unvisited shape squares
SHAPE_P2_COLOR = (220, 100, 100)   # soft red         — P2's unvisited shape squares

# Bot move delay range (ms)
BOT_MOVE_DELAY_MIN = 500
BOT_MOVE_DELAY_MAX = 800

# Classic shape set: dom-001 (2), tri-001 (3), tri-001 (3), tet-001 (4), pen-001 (5)
CLASSIC_SHAPE_NAMES = ["02-001", "03-001", "03-001", "04-001", "05-001"]

# Maximum combined density for mixed shapes (both sets together)
MIXED_MAX_DENSITY = 0.34

# Excluded pieces (even-parity pieces, same as duelomino)
EXCLUDED_PIECES = {"bishop", "ferz", "dabbaba", "alfil", "threeleaper", "tripper", "camel"}

# Maximum attempts when trying to place a single shape on the board
MAX_PLACEMENT_ATTEMPTS = 2000
# Maximum attempts per shape during mixed layout generation
MIXED_PER_PIECE_ATTEMPTS = 400

# Gunkan schema for puzzle codes: board, shapes
gunkan_schema = [
    ("board",  4, lambda v: int(v) - BOARD_MIN),
    ("shapes", 1, {"classic": 0, "mixed": 1}),
]


# ──────────────────────────────────────────────
#  Module-level utility functions
# ──────────────────────────────────────────────

def get_globally_valid_pieces() -> List[str]:
    """Return piece names valid for any board size (excluding even-parity pieces)."""
    return [p for p in pk.PIECE_LIST if p not in EXCLUDED_PIECES]


def _format_clock(clock_value: int) -> str:
    """Format a clock value (seconds) for display in the menu."""
    if clock_value == 0:
        return "infinity"
    m, s = divmod(clock_value, 60)
    return f"{m}:{s:02d}"


def normalize(units: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Normalize polyomino units so min x/y is (0, 0)."""
    if not units:
        return units
    minx = min(c[0] for c in units)
    miny = min(c[1] for c in units)
    return [(x - minx, y - miny) for (x, y) in units]


def rotate90(units: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    return normalize([(y, -x) for (x, y) in units])


def flip_horizontal(units: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    return normalize([(-x, y) for (x, y) in units])


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
        self.name = name or "poly"
        self.color = color or (128, 128, 128)

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
            owner: int = 1,
    ):
        self.id = shape_id
        self.name = name
        self.puzzle_units = set(puzzle_units)
        self.color = color
        self.origin = origin
        self.owner = owner          # 1 = player 1, 2 = player 2
        self.found_units: Set[Tuple[int, int]] = set()


# ──────────────────────────────────────────────
#  Classic shape placement
# ──────────────────────────────────────────────

def _place_classic_set(
        cols: int, rows: int,
        owner: int,
        rng: random.Random,
        occupancy: Set[Tuple[int, int]],
        shape_id_start: int,
) -> Tuple[List[PuzzleShape], int]:
    """
    Place the classic set of shapes (dom-001, tri-001×2, tet-001, pen-001)
    for *owner* on the board.  *occupancy* is the union of already-placed
    cells (updated in-place).  Returns (shapes, next_shape_id).
    """
    owner_color = SHAPE_P1_COLOR if owner == 1 else SHAPE_P2_COLOR
    shapes: List[PuzzleShape] = []
    shape_id = shape_id_start

    for name in CLASSIC_SHAPE_NAMES:
        raw_units = pd.SAMPLE_POLYOMINOES[name]
        p = Polyomino(raw_units, color=owner_color, name=name)

        # Random rotation / flip
        for _ in range(rng.randint(0, 3)):
            p = p.rotated()
        if rng.choice([True, False]):
            p = p.flipped()

        bw, bh = p.bounding()
        max_gx = cols - bw
        max_gy = rows - bh
        if max_gx < 0 or max_gy < 0:
            continue

        placed = False
        for _ in range(MAX_PLACEMENT_ATTEMPTS):
            gx = rng.randint(0, max_gx)
            gy = rng.randint(0, max_gy)
            abs_units = {(gx + x, gy + y) for x, y in p.units}
            if abs_units & occupancy:
                continue
            occupancy.update(abs_units)
            shapes.append(PuzzleShape(shape_id, name, abs_units, owner_color, (gx, gy), owner=owner))
            shape_id += 1
            placed = True
            break

        if not placed:
            # Try without rotation to maximise placement chance
            p2 = Polyomino(raw_units, color=owner_color, name=name)
            bw2, bh2 = p2.bounding()
            mgx = cols - bw2
            mgy = rows - bh2
            if mgx >= 0 and mgy >= 0:
                for _ in range(MAX_PLACEMENT_ATTEMPTS):
                    gx = rng.randint(0, mgx)
                    gy = rng.randint(0, mgy)
                    abs_units = {(gx + x, gy + y) for x, y in p2.units}
                    if abs_units & occupancy:
                        continue
                    occupancy.update(abs_units)
                    shapes.append(PuzzleShape(shape_id, name, abs_units, owner_color, (gx, gy), owner=owner))
                    shape_id += 1
                    break

    return shapes, shape_id


def place_classic_layout(
        cols: int, rows: int,
        seed: Optional[int] = None,
) -> Tuple[List[PuzzleShape], List[PuzzleShape], int]:
    """
    Place classic shape sets for both players.

    Returns (player1_shapes, player2_shapes, used_seed).
    """
    used_seed = seed if seed is not None else random.randint(0, 2 ** 63 - 1)
    rng = random.Random(used_seed)

    occupancy: Set[Tuple[int, int]] = set()
    p1_shapes, next_id = _place_classic_set(cols, rows, 1, rng, occupancy, 1)
    p2_shapes, _ = _place_classic_set(cols, rows, 2, rng, occupancy, next_id)
    return p1_shapes, p2_shapes, used_seed


# ──────────────────────────────────────────────
#  Mixed shape placement
# ──────────────────────────────────────────────

def _place_mixed_set(
        cols: int, rows: int,
        owner: int,
        rng: random.Random,
        occupancy: Set[Tuple[int, int]],
        max_squares: int,
        shape_id_start: int,
) -> Tuple[List[PuzzleShape], int]:
    """
    Place random shapes for *owner* until *max_squares* are used or no more fit.
    Returns (shapes, next_shape_id).
    """
    owner_color = SHAPE_P1_COLOR if owner == 1 else SHAPE_P2_COLOR
    chosen = list(pd.SAMPLE_POLYOMINOES.items())
    group_sizes = {"01": 1, "02": 1, "03": 2, "04": 5, "05": 12,
                   "06": 35, "07": 108, "08": 369}
    type_weights = {"01": 11, "02": 11, "03": 11, "04": 10, "05": 9,
                    "06": 6, "07": 6, "08": 2}
    weights = [
        type_weights.get(n.split("-")[0], 1) / group_sizes.get(n.split("-")[0], 1)
        for n, _ in chosen
    ]

    shapes: List[PuzzleShape] = []
    shape_id = shape_id_start
    occupied_count = 0
    total_attempts = 0
    max_total_attempts = 6000
    per_piece_attempts = 500 #MIXED_PER_PIECE_ATTEMPTS

    while occupied_count < max_squares and total_attempts < max_total_attempts:
        total_attempts += 1
        name, raw_units = rng.choices(chosen, weights=weights, k=1)[0]
        p = Polyomino(raw_units, color=owner_color, name=name)
        for _ in range(rng.randint(0, 3)):
            p = p.rotated()
        if rng.choice([True, False]):
            p = p.flipped()

        bw, bh = p.bounding()
        max_gx = cols - bw
        max_gy = rows - bh
        if max_gx < 0 or max_gy < 0:
            continue

        for _ in range(per_piece_attempts):
            gx = rng.randint(0, max_gx)
            gy = rng.randint(0, max_gy)
            abs_units = {(gx + x, gy + y) for x, y in p.units}
            if abs_units & occupancy:
                continue
            if occupied_count + len(abs_units) > max_squares:
                continue
            occupancy.update(abs_units)
            shapes.append(PuzzleShape(shape_id, name, abs_units, owner_color, (gx, gy), owner=owner))
            shape_id += 1
            occupied_count += len(abs_units)
            break

    return shapes, shape_id


def place_mixed_layout(
        cols: int, rows: int,
        seed: Optional[int] = None,
) -> Tuple[List[PuzzleShape], List[PuzzleShape], int]:
    """
    Place mixed shape sets for both players.
    Combined total squares ≤ 34% of total board squares.

    Returns (player1_shapes, player2_shapes, used_seed).
    """
    used_seed = seed if seed is not None else random.randint(0, 2 ** 63 - 1)
    rng = random.Random(used_seed)

    total_cells = cols * rows
    max_combined = math.floor(total_cells * MIXED_MAX_DENSITY)
    max_per_player = max_combined // 2

    occupancy: Set[Tuple[int, int]] = set()
    p1_shapes, next_id = _place_mixed_set(cols, rows, 1, rng, occupancy, max_per_player, 1)
    p2_shapes, _ = _place_mixed_set(cols, rows, 2, rng, occupancy, max_per_player, next_id)
    return p1_shapes, p2_shapes, used_seed


def place_gunkan_layout(
        cols: int, rows: int,
        shapes_token: str,
        seed: Optional[int] = None,
) -> Tuple[List[PuzzleShape], List[PuzzleShape], int]:
    """
    Generate both players' shape layouts for Gunkan.

    Returns (player1_shapes, player2_shapes, used_seed).
    """
    if shapes_token == "classic":
        return place_classic_layout(cols, rows, seed)
    return place_mixed_layout(cols, rows, seed)


# ──────────────────────────────────────────────
#  GunkanController
# ──────────────────────────────────────────────

class GunkanController(BaseGameController):
    """
    Game controller for Gunkan.

    Each player owns a hidden set of polyomino shapes.  Both players take
    turns navigating the board with a chess piece.  A unit is *found* when
    any player lands on it — it is always counted against the OWNER.
    The first player to have all of their owned units found loses.
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
            font, font_large, base_dir, gunkan_schema,
        )

        # Default modes
        self.guide_mode_active = True
        self.track_mode_active = True
        self.hint_mode_active = False

        # Two-player positional state
        self.player1_pos: Optional[Tuple[int, int]] = None
        self.player2_pos: Optional[Tuple[int, int]] = None
        self.player1_visited: Set[Tuple[int, int]] = set()
        self.player2_visited: Set[Tuple[int, int]] = set()
        self.player1_visited_moves: Dict[Tuple[int, int], int] = {}
        self.player2_visited_moves: Dict[Tuple[int, int], int] = {}
        self.player1_legal_moves: List[Tuple[int, int]] = []
        self.player2_legal_moves: List[Tuple[int, int]] = []
        self.current_player: int = 1

        # Per-player layouts (each player owns one set)
        self.player1_layout: Optional[List[PuzzleShape]] = None   # P1's shapes (blue)
        self.player2_layout: Optional[List[PuzzleShape]] = None   # P2's shapes (red)

        # Pre-computed unit sets for fast lookup
        self.player1_all_units: Set[Tuple[int, int]] = set()
        self.player2_all_units: Set[Tuple[int, int]] = set()

        # Found units: cells from each player's OWNED shapes that have been landed on
        self.player1_found_units: Set[Tuple[int, int]] = set()   # P1's found (against P1)
        self.player2_found_units: Set[Tuple[int, int]] = set()   # P2's found (against P2)

        # Seed and generation state
        self.used_seed: Optional[int] = None

        # Bot scheduling
        self.bot_move_pending: bool = False
        self.bot_move_timer: int = 0

        # Bot resignation offer
        self.bot_offers_resignation: bool = False

        # Per-move clock tracking
        self.move_start_time: Optional[float] = None

        # Preview layout for MENU state
        self.preview_p1: Optional[List[PuzzleShape]] = None
        self.preview_p2: Optional[List[PuzzleShape]] = None

        # Endgame state
        self.endgame_reason: Optional[str] = None
        self.blind_draw_active: bool = False
        self.previous_game_codec: Optional[str] = None
        self.is_piece_playable: bool = True

        # Initial menu board preview position
        c = (self.board_model.cols - 1) // 2
        self.player_pos = (c, c)
        self.generate_menu_preview()

        # Ring marker images
        markers_dir = os.path.join(base_dir, "assets", "markers")
        self.flag2_blue_img = pygame.image.load(
            os.path.join(markers_dir, "flag2_blue.png")).convert_alpha()
        self.flag2_red_img = pygame.image.load(
            os.path.join(markers_dir, "flag2_red.png")).convert_alpha()
        self._scaled_ring_cache: Dict[Tuple[int, str], pygame.Surface] = {}

    # ================================================================== #
    #  Abstract method implementations                                    #
    # ================================================================== #

    def _get_min_board_size(self, piece_name: str) -> int:
        return BOARD_MIN

    def _get_encode_params(self) -> Dict[str, Any]:
        return {
            "board": self.get_selection("board"),
            "shapes": self.get_selection("shapes"),
        }

    def _validate_codec(self, codec_text: str) -> Tuple[bool, Optional[Dict]]:
        try:
            params = decode_params(codec_text, gunkan_schema)
            board_val = params.get("board", 0) + BOARD_MIN
            if not (BOARD_MIN <= board_val <= BOARD_MAX):
                return False, None

            for label in ("board", "shapes"):
                idx = self.label_to_index.get(label)
                if idx is None:
                    continue
                vals = self.menu_items[idx][1]
                val = params.get(label)
                real_val = int(val) + BOARD_MIN if label == "board" else val
                if real_val in vals:
                    self.menu_items[idx] = (self.menu_items[idx][0], vals, vals.index(real_val))

            return True, params
        except (KeyError, ValueError, IndexError):
            return False, None

    def _game_specific_start_setup(self, seed: Optional[int] = None) -> bool:
        """Generate two shape layouts and initialise two-player state."""
        sel = self.get_current_selections()
        board_size = int(sel["board"])
        shapes_choice = sel["shapes"]

        p1_layout, p2_layout, used_seed = place_gunkan_layout(
            board_size, board_size, shapes_choice, seed)

        if not p1_layout and not p2_layout:
            return False

        self.player1_layout = p1_layout
        self.player2_layout = p2_layout
        self.used_seed = used_seed

        self.player1_all_units = {u for s in p1_layout for u in s.puzzle_units}
        self.player2_all_units = {u for s in p2_layout for u in s.puzzle_units}

        self.player1_found_units = set()
        self.player2_found_units = set()

        self.player1_visited = set()
        self.player2_visited = set()
        self.player1_visited_moves = {}
        self.player2_visited_moves = {}
        self.current_player = 1
        self.bot_move_pending = False
        self.bot_move_timer = 0

        self.player1_pos = None
        self.player2_pos = None
        self.move_count = 0

        self._update_all_legal_moves()
        self._sync_base_state()
        return True

    def _game_specific_make_move(self, target: Tuple[int, int]) -> bool:
        """Not used directly; logic is in make_move() override."""
        return True

    def _validate_move(self, target: Tuple[int, int]) -> bool:
        if self.current_player == 1:
            return target in self.player1_legal_moves
        return target in self.player2_legal_moves

    def _check_endgame_conditions(self) -> Optional[str]:
        """Check if all units of a player have been found, or neither can move."""
        # Win/loss via unit discovery
        p1_total = len(self.player1_all_units)
        p2_total = len(self.player2_all_units)

        p1_found = len(self.player1_found_units)
        p2_found = len(self.player2_found_units)

        # A player loses when ALL of their owned units are found
        p1_eliminated = p1_total > 0 and p1_found >= p1_total
        p2_eliminated = p2_total > 0 and p2_found >= p2_total

        if p1_eliminated and p2_eliminated:
            return "draw"
        if p1_eliminated:
            return "player2_wins"
        if p2_eliminated:
            return "player1_wins"

        # No legal moves
        p1_stuck = not self.player1_legal_moves
        p2_stuck = not self.player2_legal_moves

        if p1_stuck and p2_stuck:
            # Player with FEWEST owned units found wins
            if p1_found < p2_found:
                return "player1_wins"
            elif p2_found < p1_found:
                return "player2_wins"
            else:
                return "draw"

        return None

    def _check_bot_resignation_condition(self) -> bool:
        """Return True if the bot's position is hopeless.

        Bot resigns when:
        1. ALL of its owned units have already been found (already lost), or
        2. The bot has no legal moves, the human still has legal moves, and
           more of the bot's units have been found than the player's units —
           the bot is losing and cannot improve its position.
        """
        player_one = self.get_selection("first move")
        bot_player = 2 if player_one == "human" else 1

        bot_all = self.player1_all_units if bot_player == 1 else self.player2_all_units
        if not bot_all:
            return False

        bot_found = self.player1_found_units if bot_player == 1 else self.player2_found_units
        human_found = self.player2_found_units if bot_player == 1 else self.player1_found_units
        bot_legal = self.player1_legal_moves if bot_player == 1 else self.player2_legal_moves
        human_legal = self.player2_legal_moves if bot_player == 1 else self.player1_legal_moves

        # Already lost: all bot units have been found
        if len(bot_found) >= len(bot_all):
            return True

        # Unwinnable: bot is stuck and losing — human can only widen the gap
        if not bot_legal and human_legal and len(bot_found) > len(human_found):
            return True

        return False

    def _render_game_specific_board(self, screen: pygame.Surface) -> None:
        """Board rendering handled by _render_board_area()."""
        pass

    def _render_game_specific_stats(
            self, screen: pygame.Surface, stats_panel: UIPanel
    ) -> None:
        """Stats rendered by _render_right_panel()."""
        pass

    def _capture_game_state(self) -> Dict[str, Any]:
        return {
            "current_player": self.current_player,
            "player1_pos": self.player1_pos,
            "player2_pos": self.player2_pos,
            "player1_visited": self.player1_visited.copy(),
            "player2_visited": self.player2_visited.copy(),
            "player1_visited_moves": self.player1_visited_moves.copy(),
            "player2_visited_moves": self.player2_visited_moves.copy(),
            "player1_found_units": self.player1_found_units.copy(),
            "player2_found_units": self.player2_found_units.copy(),
            "visited": self.visited.copy(),
            "visited_moves": self.visited_moves.copy(),
            "move_count": self.move_count,
        }

    def _restore_game_state(self, state: Dict[str, Any]) -> None:
        self.current_player = state.get("current_player", 1)
        self.player1_pos = state.get("player1_pos")
        self.player2_pos = state.get("player2_pos")
        self.player1_visited = state.get("player1_visited", set()).copy()
        self.player2_visited = state.get("player2_visited", set()).copy()
        self.player1_visited_moves = state.get("player1_visited_moves", {}).copy()
        self.player2_visited_moves = state.get("player2_visited_moves", {}).copy()
        self.player1_found_units = state.get("player1_found_units", set()).copy()
        self.player2_found_units = state.get("player2_found_units", set()).copy()
        self.visited = state.get("visited", set()).copy()
        self.visited_moves = state.get("visited_moves", {}).copy()
        self.move_count = state.get("move_count", 0)
        self._update_all_legal_moves()
        self._sync_base_state()
        if self.hint_mode_active:
            self._calculate_hint_degrees()
        else:
            self.hint_degrees = {}

    def _update_legal_moves(self) -> None:
        self._update_all_legal_moves()

    def _calculate_hint_degrees(self) -> None:
        piece_name = self.get_selection("piece")
        cur_pos = self.player1_pos if self.current_player == 1 else self.player2_pos
        if cur_pos is None:
            self.hint_degrees = {}
            return
        n = self.board_model.cols
        all_visited = self.player1_visited | self.player2_visited
        self.hint_degrees = calculate_hint_degrees(piece_name, cur_pos, n, n, all_visited)

    # ================================================================== #
    #  Clock helpers                                                      #
    # ================================================================== #

    def _is_per_move_mode(self) -> bool:
        """Return True when the clock is in per-move countdown mode."""
        clock_sel = self.get_selection("clock")
        time_per  = self.get_selection("time per")
        return clock_sel > 0 and time_per == "move"

    def _remaining_time(self) -> Optional[int]:
        """Return seconds remaining, or None for infinity display."""
        clock_sel = self.get_selection("clock")
        if clock_sel == 0:
            return None
        if self._is_per_move_mode():
            if self.move_start_time is None:
                return int(clock_sel)
            elapsed = time.time() - self.move_start_time
            return max(0, math.ceil(clock_sel - elapsed))
        # Per-game mode: delegate to standard elapsed tracking
        elapsed = self.final_elapsed if self.game_state == GameState.ENDGAME else self.clock_elapsed
        return max(0, int(clock_sel) - int(elapsed))

    # ================================================================== #
    #  Two-player move logic                                              #
    # ================================================================== #

    def _update_all_legal_moves(self) -> None:
        piece_name = self.get_selection("piece")
        n = self.board_model.cols
        all_visited = self.player1_visited | self.player2_visited

        if self.player1_pos:
            self.player1_legal_moves = get_legal_moves_for_board(
                piece_name, *self.player1_pos, n, n, all_visited)
        else:
            self.player1_legal_moves = []

        if self.player2_pos:
            self.player2_legal_moves = get_legal_moves_for_board(
                piece_name, *self.player2_pos, n, n, all_visited)
        else:
            self.player2_legal_moves = []

        if self.current_player == 1:
            self.legal_moves = self.player1_legal_moves
        else:
            self.legal_moves = self.player2_legal_moves

    def _sync_base_state(self) -> None:
        if self.current_player == 1:
            self.player_pos = self.player1_pos
            self.visited = self.player1_visited
            self.visited_moves = self.player1_visited_moves
            self.legal_moves = self.player1_legal_moves
        else:
            self.player_pos = self.player2_pos
            self.visited = self.player2_visited
            self.visited_moves = self.player2_visited_moves
            self.legal_moves = self.player2_legal_moves

    def _apply_move(self, player: int, target: Tuple[int, int]) -> None:
        """Apply move for *player*; discover any units at *target*."""
        if player == 1:
            self.player1_pos = target
            self.player1_visited.add(target)
            self.player1_visited_moves[target] = len(self.player1_visited)
        else:
            self.player2_pos = target
            self.player2_visited.add(target)
            self.player2_visited_moves[target] = len(self.player2_visited)

        # Mark ownership-based unit discovery for the landing cell
        self._check_unit_discovery(target)

        self.move_count += 1
        self._update_all_legal_moves()

    def make_move(self, target_pos: Tuple[int, int]) -> None:
        """Two-player move logic."""
        if self.game_state != GameState.INGAME:
            return
        if not self._validate_move(target_pos):
            return
        if self.bot_move_pending:
            return

        if not self._is_per_move_mode() and self.clock_start_time is None:
            self.clock_start_time = time.time()
        self._apply_move(self.current_player, target_pos)
        self.replay_states.append(self._capture_game_state())

        end_condition = self._check_endgame_conditions()
        if end_condition:
            self._go_to_endgame(end_condition)
            return

        # Switch player (respecting continuation rule)
        other = 3 - self.current_player
        other_moves = self.player1_legal_moves if other == 1 else self.player2_legal_moves
        if other_moves:
            self.current_player = other

        self._sync_base_state()

        # Reset per-move clock after a valid move
        if self._is_per_move_mode():
            self.move_start_time = time.time()

        if self._check_bot_resignation_condition():
            self.bot_offers_resignation = True

        if self.hint_mode_active:
            self._calculate_hint_degrees()
        else:
            self.hint_degrees = {}

        if self._is_bot_turn():
            self._schedule_bot_move()

    def commit_start_square(self, start_pos: Tuple[int, int]) -> None:
        """Commit first square for current player in WAITING state."""
        if self.game_state != GameState.WAITING:
            return

        player_one = self.get_selection("first move")

        if self.player1_pos is None:
            self.player1_pos = start_pos
            self.player1_visited.add(start_pos)
            self.player1_visited_moves[start_pos] = 1
            self._check_unit_discovery(start_pos)

            if self.player2_pos is None:
                if player_one == "human":
                    # P2 is bot → auto-commit P2's start
                    n = self.board_model.cols
                    rng = random.Random(self.last_puzzle_seed)
                    candidates = [(x, y) for x in range(n) for y in range(n)
                                  if (x, y) not in self.player1_visited]
                    if candidates:
                        bot_start = rng.choice(candidates)
                        self.player2_pos = bot_start
                        self.player2_visited.add(bot_start)
                        self.player2_visited_moves[bot_start] = 1
                        self._check_unit_discovery(bot_start)
                    else:
                        self.player2_pos = start_pos
                else:
                    # P1 is bot, P2 (human) still needs to select
                    self._update_all_legal_moves()
                    return

        elif self.player2_pos is None:
            if start_pos in self.player1_visited:
                return
            self.player2_pos = start_pos
            self.player2_visited.add(start_pos)
            self.player2_visited_moves[start_pos] = 1
            self._check_unit_discovery(start_pos)

        self.move_count = len(self.player1_visited) + len(self.player2_visited)
        self._update_all_legal_moves()
        self._sync_base_state()

        self.game_state = GameState.INGAME
        if self._is_per_move_mode():
            self.clock_start_time = None
            self.move_start_time  = time.time()
        else:
            self.clock_start_time = time.time()
            self.move_start_time  = None
        self.replay_states = [self._capture_game_state()]
        self.replay_index = 0

        if self.hint_mode_active:
            self._calculate_hint_degrees()

        if self._is_bot_turn():
            self._schedule_bot_move()

    # ================================================================== #
    #  Unit discovery logic                                               #
    # ================================================================== #

    def _check_unit_discovery(self, pos: Tuple[int, int]) -> None:
        """
        Mark *pos* as found within whichever player's layout it belongs to.
        Landing on your own units counts against you (rule 9).
        """
        if pos in self.player1_all_units and pos not in self.player1_found_units:
            self.player1_found_units.add(pos)
        if pos in self.player2_all_units and pos not in self.player2_found_units:
            self.player2_found_units.add(pos)

    # ================================================================== #
    #  Bot support                                                        #
    # ================================================================== #

    def _is_bot_turn(self) -> bool:
        player_one = self.get_selection("first move")
        if player_one == "human":
            return self.current_player == 2
        return self.current_player == 1

    def _schedule_bot_move(self) -> None:
        delay = random.randint(BOT_MOVE_DELAY_MIN, BOT_MOVE_DELAY_MAX)
        self.bot_move_timer = pygame.time.get_ticks() + delay
        self.bot_move_pending = True

    def _execute_bot_move(self) -> None:
        self.bot_move_pending = False
        if self.game_state != GameState.INGAME:
            return

        bot_player = self.current_player
        bot_pos = self.player1_pos if bot_player == 1 else self.player2_pos
        if bot_pos is None:
            return

        level_str = self.get_selection("level")
        try:
            level = BotLevel(level_str)
        except ValueError:
            level = BotLevel.LEVEL_1

        piece_name = self.get_selection("piece")
        board_size = self.board_model.cols
        all_visited = self.player1_visited | self.player2_visited

        # The bot's goal is to land on the OPPONENT's units
        opponent_layout = self.player2_layout if bot_player == 1 else self.player1_layout
        bot_found_opponent = (self.player2_found_units if bot_player == 1
                              else self.player1_found_units)
        opponent_pos = self.player2_pos if bot_player == 1 else self.player1_pos

        domain_data = (opponent_layout, bot_found_opponent)

        chosen = make_bot_move(
            level, piece_name, bot_pos, board_size, all_visited,
            domain_data, opponent_pos
        )
        if chosen is not None:
            self.make_move(chosen)

    # ================================================================== #
    #  Frame update                                                       #
    # ================================================================== #

    def update(self, dt):
        was_ingame = self.game_state == GameState.INGAME
        current_player_before = self.current_player
        super().update(dt)

        if was_ingame and self.game_state == GameState.ENDGAME and self.end_state == "timeout":
            if self.endgame_reason is None:
                self.endgame_reason = f"player{current_player_before}_timeout"
            self.bot_move_pending = False
            return

        if self.game_state == GameState.INGAME:
            # Per-move timeout check
            if self._is_per_move_mode() and self.move_start_time is not None:
                clock_sel = self.get_selection("clock")
                now = time.time()
                if now - self.move_start_time >= clock_sel:
                    self.endgame_reason = f"player{self.current_player}_timeout"
                    self.bot_move_pending = False
                    self.end_state  = "timeout"
                    self.game_state = GameState.ENDGAME
                    self.final_elapsed = self._calculate_final_elapsed()
                    return

            if self.bot_move_pending and pygame.time.get_ticks() >= self.bot_move_timer:
                self._execute_bot_move()

    # ================================================================== #
    #  Start game override                                                #
    # ================================================================== #

    def start_game(self, use_seed: Optional[int] = None) -> None:
        board_size = self.get_selection("board")
        piece_name = self.get_selection("piece")

        min_board = self._get_min_board_size(piece_name)
        if board_size < min_board:
            self.error_message = f"{piece_name} needs board >= {min_board}"
            self.error_timer = pygame.time.get_ticks() + 3000
            return

        if use_seed is not None:
            seed = use_seed
        elif self.seed_mode_active:
            code_text = self.codec_input.get_text()
            ok, params = self._validate_codec(code_text)
            if ok and params:
                seed = params["seed"]
            else:
                self.error_message = "Invalid share code"
                self.error_timer = pygame.time.get_ticks() + 3000
                return
        else:
            seed = random.randint(0, 2 ** 63 - 1)

        self.last_puzzle_seed = seed

        if not self._game_specific_start_setup(seed):
            self.error_message = "Failed to initialise game"
            self.error_timer = pygame.time.get_ticks() + 3000
            return

        n = self.get_selection("board")
        self.board_model.cols = n
        self.board_model.rows = n
        self.board_model.clear()

        try:
            self.puzzle_code = encode_params(self._get_encode_params(), self.schema, seed)
        except Exception:
            self.puzzle_code = ""

        self.previous_game_codec = self.puzzle_code

        # Pre-commit bot player's starting square so WAITING is only for the human
        player_one = self.get_selection("first move")
        if player_one == "bot":
            rng = random.Random(seed)
            n_sel = self.get_selection("board")
            bot_start = (rng.randint(0, n_sel - 1), rng.randint(0, n_sel - 1))
            self.player1_pos = bot_start
            self.player1_visited.add(bot_start)
            self.player1_visited_moves[bot_start] = 1
            self._check_unit_discovery(bot_start)

        self.player1_legal_moves = []
        self.player2_legal_moves = []
        self.legal_moves = []
        self.replay_states = []
        self.game_state = GameState.WAITING

    # ================================================================== #
    #  Helper flows                                                       #
    # ================================================================== #

    def start_flow(self) -> None:
        self.start_game()

    def start_blind_draw_flow(self) -> None:
        self.blind_draw_active = True
        self.copy_clicked = False
        piece_name = self.get_current_selections()["piece"]
        for i, (label, blind_values, _) in enumerate(self.menu_items):
            if label == "board":
                max_attempts = len(blind_values) * 2
                attempts = 0
                while attempts < max_attempts:
                    attempts += 1
                    new_idx = random.randint(0, len(blind_values) - 1)
                    if pr.assess_piece_playability(
                            piece_name, blind_values[new_idx]) != "choose a larger board":
                        self.menu_items[i] = (label, blind_values, new_idx)
                        break
            elif label == "shapes":
                self.menu_items[i] = (label, blind_values,
                                      random.randint(0, len(blind_values) - 1))
        self.start_game()

    def new_game_flow(self) -> None:
        self.new_game()

    def retry_game(self) -> None:
        if self.used_seed is not None:
            self.start_game(use_seed=self.used_seed)

    # ================================================================== #
    #  Game control overrides                                             #
    # ================================================================== #

    def toggle_replay_mode(self) -> None:
        if self.game_state != GameState.ENDGAME:
            return
        if not self.replay_mode_active:
            self.replay_mode_active = True
            self.board_model.clear()
            self.replay_index = 0
            if self.replay_states:
                self._restore_game_state(self.replay_states[0])
        else:
            self.replay_mode_active = False
            if self.replay_states:
                self._restore_game_state(self.replay_states[-1])
        self.game_state = GameState.ENDGAME

    def undo_move(self) -> None:
        if self.game_state != GameState.INGAME:
            return
        self.bot_move_pending = False
        self.bot_offers_resignation = False

        # replay_states[0] is the initial board state; each move appends one entry.
        # Undoing a "full round" removes both players' most recent moves (two pops).
        # When only one move has been made (2 states: initial + 1 move), remove that
        # single move to return to the starting position.
        if len(self.replay_states) >= 3:
            self.replay_states.pop()
            self.replay_states.pop()
        elif len(self.replay_states) == 2:
            self.replay_states.pop()
        else:
            return

        self._restore_game_state(self.replay_states[-1])

        if self._is_bot_turn():
            self._schedule_bot_move()

    def resign_game(self) -> None:
        if self.game_state != GameState.INGAME:
            return
        self.bot_move_pending = False
        self.final_elapsed = self._calculate_final_elapsed()
        self._go_to_endgame(f"player{self.current_player}_resignation")

    def accept_bot_resignation(self) -> None:
        if self.game_state != GameState.INGAME or not self.bot_offers_resignation:
            return
        self.bot_move_pending = False
        self.final_elapsed = self._calculate_final_elapsed()
        player_one = self.get_selection("first move")
        bot_player = 2 if player_one == "human" else 1
        self.bot_offers_resignation = False
        self._go_to_endgame(f"player{bot_player}_resignation")

    def new_game(self) -> None:
        super().new_game()
        self.blind_draw_active = False
        self.bot_offers_resignation = False
        self.player1_pos = None
        self.player2_pos = None
        self.player1_visited = set()
        self.player2_visited = set()
        self.player1_visited_moves = {}
        self.player2_visited_moves = {}
        self.player1_legal_moves = []
        self.player2_legal_moves = []
        self.player1_found_units = set()
        self.player2_found_units = set()
        self.player1_layout = None
        self.player2_layout = None
        self.player1_all_units = set()
        self.player2_all_units = set()
        self.current_player = 1
        self.bot_move_pending = False
        self.used_seed = None
        self.endgame_reason = None
        self.hint_degrees = {}
        self.move_start_time = None
        self.board_model.clear()

    def toggle_hint_mode(self) -> None:
        self.hint_mode_active = not self.hint_mode_active
        if self.hint_mode_active:
            if self.game_state == GameState.INGAME:
                self._calculate_hint_degrees()
        else:
            self.hint_degrees = {}

    def toggle_guide_mode(self) -> None:
        self.guide_mode_active = not self.guide_mode_active

    def toggle_reveal_all_shapes(self) -> None:
        if self.game_state == GameState.ENDGAME:
            self.reveal_mode_active = not self.reveal_mode_active

    def go_to_menu(self) -> None:
        self.new_game()

    def toggle_codec_input(self) -> None:
        super().toggle_codec_input()
        ci = self.codec_input
        if ci:
            ci.text = ""
            ci.cursor_pos = 0
            ci.active = self.seed_mode_active

    # ================================================================== #
    #  Utility helpers                                                    #
    # ================================================================== #

    def _go_to_endgame(self, reason: str) -> None:
        self.game_state = GameState.ENDGAME
        self.endgame_reason = reason
        self.bot_move_pending = False
        self.bot_offers_resignation = False
        self.final_elapsed = self._calculate_final_elapsed()

    def _calculate_final_elapsed(self) -> int:
        if self.clock_start_time is not None:
            return int(self.paused_elapsed + (time.time() - self.clock_start_time))
        return 0

    def get_current_selections(self) -> Dict[str, Any]:
        return {label: vals[cur] for label, vals, cur in self.menu_items}

    def generate_menu_preview(self) -> None:
        sel = self.get_current_selections()
        board_size = int(sel["board"])
        shapes_choice = sel["shapes"]
        try:
            p1, p2, _ = place_gunkan_layout(board_size, board_size, shapes_choice)
            self.preview_p1 = p1
            self.preview_p2 = p2
        except Exception:
            self.preview_p1 = []
            self.preview_p2 = []

    def resize_board_if_needed(self) -> None:
        new_size = int(self.get_current_selections()["board"])
        if self.board_model.cols != new_size or self.board_model.rows != new_size:
            self.board_model.cols = new_size
            self.board_model.rows = new_size
            self.board_model.clear()
            c = (new_size - 1) // 2
            self.player_pos = (c, c)

    def _draw_tinted_piece(self, screen: pygame.Surface, rect: pygame.Rect,
                            tint: Tuple[int, int, int]) -> None:
        piece_name = self.get_selection("piece")
        try:
            icon = pk.get_image(piece_name)
        except Exception:
            pygame.draw.ellipse(screen, tint, rect)
            return
        scaled = pygame.transform.smoothscale(icon, (rect.width, rect.height))
        tinted = scaled.copy()
        tint_surf = pygame.Surface(tinted.get_size(), pygame.SRCALPHA)
        tint_surf.fill((*tint, 255))
        tinted.blit(tint_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(tinted, rect)

    # ================================================================== #
    #  Event handling                                                     #
    # ================================================================== #

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not super().handle_event(event):
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_h and self.game_state == GameState.INGAME:
                self.toggle_hint_mode()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            for key, rect in self.widget_rects.items():
                if rect.collidepoint(mx, my):
                    action, item_idx = key
                    lbl, vals, cur = self.menu_items[item_idx]
                    if action == "plus":
                        self.menu_items[item_idx] = (lbl, vals, (cur + 1) % len(vals))
                    elif action == "minus":
                        self.menu_items[item_idx] = (lbl, vals, (cur - 1) % len(vals))
                    if lbl == "board":
                        self.resize_board_if_needed()
                    if lbl in ("board", "shapes"):
                        self.generate_menu_preview()
                    break

            if self.game_state == GameState.WAITING:
                grid_pos = self.board_renderer.to_grid(mx, my)
                if grid_pos is not None:
                    self.commit_start_square(grid_pos)

            elif self.game_state == GameState.INGAME:
                if not self._is_bot_turn():
                    grid_pos = self.board_renderer.to_grid(mx, my)
                    if grid_pos is not None:
                        self.make_move(grid_pos)

        return True

    # ================================================================== #
    #  Buttons                                                            #
    # ================================================================== #

    def _build_buttons(self) -> None:
        f = self.font
        self.buttons: Dict[str, Button] = {
            "start": Button(pygame.Rect(0, 0, 0, 0), "start", f,
                            (255, 255, 255), (92, 192, 92), self.start_flow),
            "blind_draw": Button(pygame.Rect(0, 0, 0, 0), "blind draw", f,
                                 (255, 255, 255), (128, 32, 64), self.start_blind_draw_flow),
            "enter_code": Button(pygame.Rect(0, 0, 0, 0), "enter share code", f,
                                 (255, 255, 255), (224, 0, 96), self.toggle_codec_input),
            "copy_code": Button(pygame.Rect(0, 0, 0, 0), "copy share code", f,
                                (255, 255, 255), (224, 0, 96), self.copy_code_to_clipboard),
            "guide_mode": Button(pygame.Rect(0, 0, 0, 0), "show move guide", f,
                                 (255, 255, 255), (128, 64, 255), self.toggle_guide_mode),
            "track_mode": Button(pygame.Rect(0, 0, 0, 0), "show move track", f,
                                 (255, 255, 255), (255, 92, 128), self.toggle_track_mode),
            "hint_mode": Button(pygame.Rect(0, 0, 0, 0), "show move degrees", f,
                                (255, 255, 255), (255, 128, 96), self.toggle_hint_mode),
            "undo_mode": Button(pygame.Rect(0, 0, 0, 0), "undo last move", f,
                                (255, 255, 255), (64, 128, 255), self.undo_move),
            "resign": Button(pygame.Rect(0, 0, 0, 0), "resign", f,
                             (255, 255, 255), (107, 70, 51), self.resign_game),
            "retry": Button(pygame.Rect(0, 0, 0, 0), "retry", f,
                            (255, 255, 255), (92, 192, 92), self.retry_game),
            "replay_mode": Button(pygame.Rect(0, 0, 0, 0), "start replay", f,
                                  (255, 255, 255), (64, 128, 255), self.toggle_replay_mode),
            "replay_prev": Button(pygame.Rect(0, 0, 0, 0), "-", f,
                                  (255, 255, 240), (64, 128, 255),
                                  lambda: self.navigate_replay(-1)),
            "replay_next": Button(pygame.Rect(0, 0, 0, 0), "+", f,
                                  (255, 255, 240), (64, 128, 255),
                                  lambda: self.navigate_replay(1)),
            "reveal": Button(pygame.Rect(0, 0, 0, 0), "show all units", f,
                             (255, 255, 255), (255, 128, 96), self.toggle_reveal_all_shapes),
            "new_game": Button(pygame.Rect(0, 0, 0, 0), "new game", f,
                               (255, 255, 255), (32, 128, 96), self.new_game_flow),
            "peek_mode": Button(pygame.Rect(0, 0, 0, 0), "peek", f,
                                (255, 255, 240), DK_SQUARE, self.toggle_peek),
            "accept_resignation": Button(pygame.Rect(0, 0, 0, 0), "accept", f,
                                         (255, 255, 255), (107, 70, 51),
                                         self.accept_bot_resignation),
            "exit": Button(pygame.Rect(0, 0, 0, 0), "exit", f,
                           (255, 255, 255), (220, 40, 40), self.quit_game),
        }

    # ================================================================== #
    #  Rendering helpers                                                  #
    # ================================================================== #

    def _draw_rings(
            self, screen: pygame.Surface,
            found_units: Set[Tuple[int, int]],
            ring_img: pygame.Surface,
    ) -> None:
        cs = self.board_renderer.cell_size
        ring_key = "blue" if ring_img is self.flag2_blue_img else "red"
        cache_key = (cs, ring_key)
        if cache_key not in self._scaled_ring_cache:
            self._scaled_ring_cache[cache_key] = pygame.transform.smoothscale(
                ring_img, (cs, cs))
        scaled_ring = self._scaled_ring_cache[cache_key]
        for px_pos in found_units:
            px, py = self.board_renderer.to_pixel(*px_pos)
            screen.blit(scaled_ring, (px + 3, py + 3))

    def _draw_peek_thumbnail(self, screen, left_panel, line_height):
        if not self.peek_mode_visible:
            return
        p1 = self.player1_layout or self.preview_p1 or []
        p2 = self.player2_layout or self.preview_p2 or []
        if not p1 and not p2:
            return
        cols, rows = self.board_model.cols, self.board_model.rows
        if cols < 1 or rows < 1:
            return
        button_bounds = left_panel.get_bounds("BUTTON_PANEL")
        thumb_area_y = left_panel.get_line_y("BUTTON_PANEL", 0, line_height)
        thumb_area = pygame.Rect(
            button_bounds["left"] + UI_SPACE,
            thumb_area_y,
            button_bounds["width"] - UI_SPACE * 2,
            button_bounds["bottom"] - (thumb_area_y + UI_SPACE * 3),
        )
        max_cell = min(
            thumb_area.width // cols if cols else 1,
            thumb_area.height // rows if rows else 1,
        )
        if max_cell < 2:
            return
        tw = cols * max_cell
        th = rows * max_cell
        tx = thumb_area.left + (thumb_area.width - tw) // 2
        ty = thumb_area.top + (thumb_area.height - th) // 2
        pygame.draw.rect(screen, DK_SQUARE, (tx - 2, ty - 2, tw + 4, th + 4))
        for shape in p1:
            for gx, gy in shape.puzzle_units:
                pygame.draw.rect(screen, SHAPE_P1_COLOR,
                                 (tx + gx * max_cell + 1,
                                  ty + gy * max_cell + 1,
                                  max_cell - 1, max_cell - 1))
        for shape in p2:
            for gx, gy in shape.puzzle_units:
                pygame.draw.rect(screen, SHAPE_P2_COLOR,
                                 (tx + gx * max_cell + 1,
                                  ty + gy * max_cell + 1,
                                  max_cell - 1, max_cell - 1))

    def _render_board_area(self, screen: pygame.Surface) -> None:
        cs = self.current_cell_size

        # MENU: show preview layouts
        if self.game_state == GameState.MENU:
            for shape in (self.preview_p1 or []):
                for gx, gy in shape.puzzle_units:
                    px, py = self.board_renderer.to_pixel(gx, gy)
                    pygame.draw.rect(screen, SHAPE_P1_COLOR,
                                     (px + 1, py + 1, cs - 1, cs - 1))
            for shape in (self.preview_p2 or []):
                for gx, gy in shape.puzzle_units:
                    px, py = self.board_renderer.to_pixel(gx, gy)
                    pygame.draw.rect(screen, SHAPE_P2_COLOR,
                                     (px + 1, py + 1, cs - 1, cs - 1))

        self.board_renderer.draw_cells(screen)
        self.board_renderer.draw_grid_lines(screen)

        # MENU: guide arrows + piece preview
        if self.game_state == GameState.MENU:
            if self.player_pos and self.guide_mode_active and self.arrows:
                piece = self.get_selection("piece")
                n = self.board_model.cols
                menu_moves = get_legal_moves_for_board(
                    piece, *self.player_pos, n, n, set())
                self._draw_arrows(screen, menu_moves, self.player_pos)
            if self.player_pos and cs > 0:
                px, py = self.board_renderer.to_pixel(*self.player_pos)
                cell_rect = pygame.Rect(px + 1, py + 1, cs - 2, cs - 2)
                try:
                    pk.draw_piece(screen, cell_rect, self.get_selection("piece"))
                except (KeyError, ValueError):
                    pygame.draw.ellipse(screen, (0, 0, 0), cell_rect)
            return

        if self.game_state not in (GameState.INGAME, GameState.ENDGAME, GameState.WAITING):
            return

        nf = pygame.font.SysFont("arial", max(6, cs // 4))

        # Use replay snapshot when replaying
        if self.game_state == GameState.ENDGAME and self.replay_mode_active and self.replay_states:
            snap = self.replay_states[self.replay_index]
            disp_p1_pos = snap.get("player1_pos")
            disp_p2_pos = snap.get("player2_pos")
            disp_p1_vis = snap.get("player1_visited", set())
            disp_p2_vis = snap.get("player2_visited", set())
            disp_p1_vm = snap.get("player1_visited_moves", {})
            disp_p2_vm = snap.get("player2_visited_moves", {})
            disp_cur = snap.get("current_player", 1)
            disp_p1_found = snap.get("player1_found_units", set())
            disp_p2_found = snap.get("player2_found_units", set())
        else:
            disp_p1_pos = self.player1_pos
            disp_p2_pos = self.player2_pos
            disp_p1_vis = self.player1_visited
            disp_p2_vis = self.player2_visited
            disp_p1_vm = self.player1_visited_moves
            disp_p2_vm = self.player2_visited_moves
            disp_cur = self.current_player
            disp_p1_found = self.player1_found_units
            disp_p2_found = self.player2_found_units

        # Draw all shape squares (both players' — always visible as owner's color)
        all_vis = disp_p1_vis | disp_p2_vis
        current_pos_set = {p for p in (disp_p1_pos, disp_p2_pos) if p is not None}

        # Determine which player is the bot so their shapes can be hidden during play.
        # "first move" == "human" means human is player 1 and the bot is player 2;
        # "first move" == "bot" means the bot is player 1 and the human is player 2.
        player_one = self.get_selection("first move")
        bot_player = 2 if player_one == "human" else 1
        hide_bot_shapes = self.game_state in (GameState.INGAME, GameState.WAITING)

        def _unit_color(gx, gy):
            """Return background color for a visited non-current-pos square."""
            pos = (gx, gy)
            if pos in self.player1_all_units:
                return P1_DK_VISITED if (gx + gy) % 2 else P1_LT_VISITED
            if pos in self.player2_all_units:
                return P2_DK_VISITED if (gx + gy) % 2 else P2_LT_VISITED
            parity = (gx + gy) % 2 == 0
            return LT_VISITED if parity else DK_VISITED

        # Draw unvisited shape squares; during play the bot's shapes are hidden
        if not self.reveal_mode_active:
            for shape in (self.player1_layout or []):
                for gx, gy in shape.puzzle_units:
                    pos = (gx, gy)
                    if pos not in all_vis:
                        if hide_bot_shapes and bot_player == 1:
                            continue  # bot's unvisited shapes are hidden
                        px, py = self.board_renderer.to_pixel(gx, gy)
                        pygame.draw.rect(screen, SHAPE_P1_COLOR,
                                         (px + 2, py + 2, cs - 3, cs - 3))
            for shape in (self.player2_layout or []):
                for gx, gy in shape.puzzle_units:
                    pos = (gx, gy)
                    if pos not in all_vis:
                        if hide_bot_shapes and bot_player == 2:
                            continue  # bot's unvisited shapes are hidden
                        px, py = self.board_renderer.to_pixel(gx, gy)
                        pygame.draw.rect(screen, SHAPE_P2_COLOR,
                                         (px + 2, py + 2, cs - 3, cs - 3))

        # Reveal mode: show all (replaces above unvisited drawing)
        if self.reveal_mode_active:
            for shape in (self.player1_layout or []):
                for gx, gy in shape.puzzle_units:
                    px, py = self.board_renderer.to_pixel(gx, gy)
                    pygame.draw.rect(screen, SHAPE_P1_COLOR,
                                     (px + 1, py + 1, cs - 1, cs - 1))
            for shape in (self.player2_layout or []):
                for gx, gy in shape.puzzle_units:
                    px, py = self.board_renderer.to_pixel(gx, gy)
                    pygame.draw.rect(screen, SHAPE_P2_COLOR,
                                     (px + 1, py + 1, cs - 1, cs - 1))

        # Player 1 visited squares
        for vx, vy in disp_p1_vis:
            if (vx, vy) in current_pos_set:
                continue
            px, py = self.board_renderer.to_pixel(vx, vy)
            # Reveal found bot units in full shape color so the player can see the shape forming
            if hide_bot_shapes and bot_player == 1 and (vx, vy) in disp_p1_found:
                vcolor = SHAPE_P1_COLOR
            else:
                vcolor = _unit_color(vx, vy)
            pygame.draw.rect(screen, vcolor, (px + 3, py + 3, cs - 4, cs - 4))

            if self.track_mode_active and (vx, vy) in disp_p1_vm:
                is_poly = (vx, vy) in self.player1_all_units or (vx, vy) in self.player2_all_units
                if is_poly:
                    luma = vcolor[0] * 0.299 + vcolor[1] * 0.587 + vcolor[2] * 0.114
                    nc = (0, 0, 0) if luma > 128 else (255, 255, 255)
                else:
                    nc = (0, 0, 192)
                ns = nf.render(str(disp_p1_vm[(vx, vy)]), True, nc)
                screen.blit(ns, ns.get_rect(center=(px + (cs // 6), py + cs // 6)))

        # Player 2 visited squares
        for vx, vy in disp_p2_vis:
            if (vx, vy) in current_pos_set:
                continue
            px, py = self.board_renderer.to_pixel(vx, vy)
            # Reveal found bot units in full shape color so the player can see the shape forming
            if hide_bot_shapes and bot_player == 2 and (vx, vy) in disp_p2_found:
                vcolor = SHAPE_P2_COLOR
            else:
                vcolor = _unit_color(vx, vy)
            pygame.draw.rect(screen, vcolor, (px + 3, py + 3, cs - 4, cs - 4))

            if self.track_mode_active and (vx, vy) in disp_p2_vm:
                is_poly = (vx, vy) in self.player1_all_units or (vx, vy) in self.player2_all_units
                if is_poly:
                    luma = vcolor[0] * 0.299 + vcolor[1] * 0.587 + vcolor[2] * 0.114
                    nc = (0, 0, 0) if luma > 128 else (255, 255, 255)
                else:
                    nc = (192, 0, 0)
                ns = nf.render(str(disp_p2_vm[(vx, vy)]), True, nc)
                screen.blit(ns, ns.get_rect(center=(px + (cs // 6), py + cs // 6)))

        # Guide arrows
        if self.guide_mode_active and self.arrows:
            if self.game_state == GameState.ENDGAME and self.replay_mode_active:
                disp_pos = disp_p1_pos if disp_cur == 1 else disp_p2_pos
                if disp_pos:
                    piece = self.get_selection("piece")
                    n = self.board_model.cols
                    rp_moves = get_legal_moves_for_board(
                        piece, *disp_pos, n, n, all_vis)
                    self._draw_arrows(screen, rp_moves, disp_pos)
            elif self.game_state in (GameState.INGAME, GameState.WAITING):
                cur_pos = disp_p1_pos if disp_cur == 1 else disp_p2_pos
                cur_mvs = (self.player1_legal_moves if disp_cur == 1
                           else self.player2_legal_moves)
                if cur_pos and cur_mvs:
                    self._draw_arrows(screen, cur_mvs, cur_pos)

        # Hint degrees
        if self.hint_mode_active and self.hint_degrees and self.game_state == GameState.INGAME:
            for (hx, hy), deg in self.hint_degrees.items():
                px, py = self.board_renderer.to_pixel(hx, hy)
                hs = nf.render(str(deg), True, (107, 50, 71))
                screen.blit(hs, hs.get_rect(center=(px + cs - (cs // 6), py + cs // 6)))

        # Rings: P1's found units use blue ring, P2's found units use red ring
        self._draw_rings(screen, disp_p1_found, self.flag2_red_img)
        self._draw_rings(screen, disp_p2_found, self.flag2_blue_img)

        # Draw current piece positions on top of shape colors
        for pos, color in [(disp_p2_pos, P2_DK_VISITED), (disp_p1_pos, P1_DK_VISITED)]:
            if pos and cs > 0:
                ppx, ppy = self.board_renderer.to_pixel(*pos)
                # If on own/opponent shape, show shape color underneath
                if pos in self.player1_all_units:
                    pygame.draw.rect(screen, P1_DK_VISITED,
                                     (ppx + 3, ppy + 3, cs - 4, cs - 4))
                elif pos in self.player2_all_units:
                    pygame.draw.rect(screen, P2_DK_VISITED,
                                     (ppx + 3, ppy + 3, cs - 4, cs - 4))
                self._draw_tinted_piece(screen,
                                        pygame.Rect(ppx + 1, ppy + 1, cs - 2, cs - 2),
                                        color)

    def _render_left_panel(self, screen, left_panel, msg_left, msg_right, msg_bottom) -> None:
        btn_w = UI_SPACE
        line_height = self.font.get_linesize() + UI_SPACE

        # ---- MENU_PANEL ----
        menu_bounds = left_panel.get_bounds("MENU_PANEL")
        text_x = menu_bounds["left"] + UI_SPACE
        menu_panel_items = [(i, item) for i, item in enumerate(self.menu_items)
                            if item[0] != 'piece']

        max_label_w = max(
            self.font.render(l, True, (0, 0, 0)).get_width()
            for l, _, _ in self.menu_items if l != 'piece')
        minus_x = text_x + max_label_w + UI_SPACE
        plus_x = menu_bounds["left"] + menu_bounds["width"] - UI_SPACE * 4

        for list_idx, (item_idx, (label, values, cur_idx)) in enumerate(menu_panel_items):
            panel_y = left_panel.get_line_y("MENU_PANEL", list_idx, line_height)
            row_cy = panel_y + btn_w // 2
            lbl_surf = self.font.render(f"{label}", True, (0, 0, 0))
            screen.blit(lbl_surf, lbl_surf.get_rect(midleft=(text_x, row_cy)))

            show_text = not self.blind_draw_active or self.game_state == GameState.ENDGAME
            if show_text:
                val = values[cur_idx]
                display_val = _format_clock(val) if label == "clock" else str(val)
                sel_surf = self.font.render(display_val, True, (0, 0, 0))
                sel_cx = (minus_x + btn_w / 2 + plus_x + btn_w / 2) / 2
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

        # blind draw (MENU only)
        self.buttons["blind_draw"].active = (self.game_state == GameState.MENU
                                              and not self.seed_mode_active)
        self.buttons["blind_draw"].rect = left_panel.get_widget_rect("MENU_PANEL", 7, BTW, BTH)
        if self.buttons["blind_draw"].active:
            self.buttons["blind_draw"].draw(screen)

        # retry (ENDGAME)
        self.buttons["retry"].active = self.game_state == GameState.ENDGAME
        self.buttons["retry"].rect = left_panel.get_widget_rect("MENU_PANEL", 7, BTW, BTH)
        if self.buttons["retry"].active:
            self.buttons["retry"].draw(screen)

        # enter/cancel share code (MENU)
        self.buttons["enter_code"].active = self.game_state == GameState.MENU
        self.buttons["enter_code"].bg_color = ((224, 64, 128) if self.seed_mode_active
                                                else (224, 0, 96))
        self.buttons["enter_code"].text = ("cancel code input" if self.seed_mode_active
                                            else "enter share code")
        self.buttons["enter_code"].rect = left_panel.get_widget_rect("MENU_PANEL", 9, BTW, BTH)
        self.buttons["enter_code"].draw(screen)

        if self.game_state == GameState.MENU and self.seed_mode_active:
            codec_y = left_panel.get_line_y("MENU_PANEL", 10, line_height)
            input_w = 192
            input_x = menu_bounds["left"] + (menu_bounds["width"] - input_w) // 2
            self.codec_input.rect = pygame.Rect(input_x, codec_y, input_w, BTH)
            self.codec_input.draw(screen)

        if (self.puzzle_code
                and self.game_state in (GameState.WAITING, GameState.INGAME, GameState.ENDGAME)):
            code_y = left_panel.get_line_y("MENU_PANEL", 10, line_height)
            code_cx = menu_bounds["left"] + menu_bounds["width"] // 2
            code_s = self.font.render(self.puzzle_code, True, (0, 0, 0))
            screen.blit(code_s, code_s.get_rect(center=(code_cx, code_y + btn_w)))

        self.buttons["copy_code"].active = self.game_state in (
            GameState.WAITING, GameState.INGAME, GameState.ENDGAME)
        self.buttons["copy_code"].bg_color = ((224, 64, 128) if self.copy_clicked
                                               else (224, 0, 96))
        self.buttons["copy_code"].text = ("share code copied" if self.copy_clicked
                                           else "copy share code")
        self.buttons["copy_code"].rect = left_panel.get_widget_rect("MENU_PANEL", 9, BTW, BTH)
        if self.buttons["copy_code"].active:
            self.buttons["copy_code"].draw(screen)

        # ---- BUTTON_PANEL ----
        button_bounds = left_panel.get_bounds("BUTTON_PANEL")

        if self.game_state == GameState.WAITING:
            player_one = self.get_selection("first move")
            if player_one == "bot" and self.player1_pos is None:
                waiting_msg = "choose a starting square"
            else:
                waiting_msg = "click a starting square"
            choose_s = self.font.render(waiting_msg, True, (255, 0, 0))
            choose_y = left_panel.get_line_y("BUTTON_PANEL", 0, line_height)
            screen.blit(choose_s, choose_s.get_rect(
                centerx=button_bounds["center_x"], centery=choose_y + btn_w // 2))

        self.buttons["start"].active = self.is_piece_playable and self.game_state == GameState.MENU
        self.buttons["start"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        if self.buttons["start"].active:
            self.buttons["start"].draw(screen)

        self.buttons["reveal"].active = self.game_state == GameState.ENDGAME
        self.buttons["reveal"].text = ("hide missed units" if self.reveal_mode_active
                                        else "show all units")
        self.buttons["reveal"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        if self.buttons["reveal"].active:
            self.buttons["reveal"].draw(screen)

        self.buttons["hint_mode"].active = self.game_state == GameState.INGAME
        self.buttons["hint_mode"].text = ("hide move degrees" if self.hint_mode_active
                                           else "show move degrees")
        self.buttons["hint_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        if self.buttons["hint_mode"].active:
            self.buttons["hint_mode"].draw(screen)

        self.buttons["guide_mode"].active = self.game_state in (
            GameState.MENU, GameState.INGAME, GameState.ENDGAME)
        self.buttons["guide_mode"].text = ("hide move guide" if self.guide_mode_active
                                            else "show move guide")
        self.buttons["guide_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 2, BTW, BTH)
        if self.buttons["guide_mode"].active:
            self.buttons["guide_mode"].draw(screen)

        self.buttons["track_mode"].active = True
        self.buttons["track_mode"].text = ("hide move track" if self.track_mode_active
                                            else "show move track")
        self.buttons["track_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 4, BTW, BTH)
        self.buttons["track_mode"].draw(screen)

        self.buttons["undo_mode"].active = (self.game_state == GameState.INGAME
                                             and len(self.replay_states) > 1)
        self.buttons["undo_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 6, BTW, BTH)
        if self.buttons["undo_mode"].active:
            self.buttons["undo_mode"].draw(screen)

        self.buttons["replay_mode"].active = self.game_state == GameState.ENDGAME
        self.buttons["replay_mode"].text = ("end replay" if self.replay_mode_active
                                             else "start replay")
        self.buttons["replay_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 6, BTW, BTH)
        if self.buttons["replay_mode"].active:
            self.buttons["replay_mode"].draw(screen)

        self.buttons["replay_prev"].active = False
        self.buttons["replay_next"].active = False
        if self.replay_mode_active and self.replay_states:
            rm_rect = self.buttons["replay_mode"].rect
            nav_w = BTW // 4
            if self.replay_index > 0:
                self.buttons["replay_prev"].active = True
                self.buttons["replay_prev"].rect = pygame.Rect(
                    rm_rect.left - nav_w - 4, rm_rect.top, nav_w, BTH)
                self.buttons["replay_prev"].draw(screen)
            if self.replay_index < len(self.replay_states) - 1:
                self.buttons["replay_next"].active = True
                self.buttons["replay_next"].rect = pygame.Rect(
                    rm_rect.right + 4, rm_rect.top, nav_w, BTH)
                self.buttons["replay_next"].draw(screen)

        self.buttons["resign"].active = self.game_state == GameState.INGAME
        self.buttons["resign"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 8, BTW, BTH)
        if self.buttons["resign"].active:
            self.buttons["resign"].draw(screen)

        self.buttons["new_game"].active = self.game_state in (
            GameState.WAITING, GameState.ENDGAME)
        self.buttons["new_game"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 8, BTW, BTH)
        if self.buttons["new_game"].active:
            self.buttons["new_game"].draw(screen)

        self.buttons["peek_mode"].active = self.game_state in (
            GameState.INGAME, GameState.ENDGAME)
        self.buttons["peek_mode"].text = "hide" if self.peek_mode_visible else "peek"
        self.buttons["peek_mode"].rect = pygame.Rect(
            msg_left + UI_SPACE * 3, msg_bottom - UI_SPACE * 5, BTW // 2, BTH)
        if self.buttons["peek_mode"].active:
            self.buttons["peek_mode"].draw(screen)

        self.buttons["exit"].rect = pygame.Rect(
            msg_right - UI_SPACE * 11, msg_bottom - UI_SPACE * 5, BTW // 2, BTH)
        self.buttons["exit"].draw(screen)

        self._draw_peek_thumbnail(screen, left_panel, line_height)

    def _render_right_panel(self, screen, right_panel) -> None:
        line_height = self.font.get_linesize() + UI_SPACE
        btn_w = UI_SPACE

        # ---- PIECE_PANEL ----
        piece_bounds = right_panel.get_bounds("PIECE_PANEL")
        right_tx = piece_bounds["left"] + UI_SPACE

        piece_idx = self.label_to_index["piece"]
        _, piece_values, piece_cur = self.menu_items[piece_idx]
        piece_name = piece_values[piece_cur] if piece_values else ""

        p_line_y = right_panel.get_line_y("PIECE_PANEL", 0, line_height)
        lbl_s = self.font.render("piece:", True, (0, 0, 0))
        lbl_rect = lbl_s.get_rect(midleft=(right_tx, p_line_y))
        p_minus_x = lbl_rect.right + UI_SPACE
        p_plus_x = piece_bounds["left"] + piece_bounds["width"] - UI_SPACE - btn_w * 3

        sel_s = self.font_large.render(piece_name, True, (0, 0, 0))
        screen.blit(sel_s, sel_s.get_rect(center=(piece_bounds["center_x"], p_line_y + 8)))

        move_set_text = pk.get_piece_move_sets_text(piece_name)
        mst_s = self.font.render(move_set_text, True, (0, 0, 0))
        screen.blit(mst_s, mst_s.get_rect(
            centerx=piece_bounds["center_x"],
            top=p_line_y + sel_s.get_height() + self.font.get_linesize()))

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

        # ---- STATS_PANEL ----
        stats_bounds = right_panel.get_bounds("STATS_PANEL")
        stats_w = stats_bounds["width"]
        stats_left = stats_bounds["left"]
        col1_cx = stats_left + stats_w // 4
        col2_cx = stats_left + 3 * stats_w // 4
        mid_cx = stats_bounds["center_x"]

        if self.game_state in (GameState.WAITING, GameState.INGAME, GameState.ENDGAME):
            if (self.game_state == GameState.ENDGAME
                    and self.replay_mode_active and self.replay_states):
                snap = self.replay_states[self.replay_index]
                p1_found = len(snap.get("player1_found_units", set()))
                p2_found = len(snap.get("player2_found_units", set()))
                disp_cur = snap.get("current_player", 1)
                p1_vis = snap.get("player1_visited", set())
                p2_vis = snap.get("player2_visited", set())
            else:
                p1_found = len(self.player1_found_units)
                p2_found = len(self.player2_found_units)
                disp_cur = self.current_player
                p1_vis = self.player1_visited
                p2_vis = self.player2_visited

            p1_total = len(self.player1_all_units)
            p2_total = len(self.player2_all_units)
            p1_moves = len(p1_vis)
            p2_moves = len(p2_vis)

            # Row 0: column headers
            y0 = right_panel.get_line_y("STATS_PANEL", 0, line_height)
            p1_h = self.font.render("blue", True, (0, 0, 192))
            p2_h = self.font.render("red", True, (192, 0, 0))
            screen.blit(p1_h, p1_h.get_rect(centerx=col1_cx, top=y0))
            screen.blit(p2_h, p2_h.get_rect(centerx=col2_cx, top=y0))

            if self.blind_draw_active and self.game_state in (GameState.WAITING,
                                                               GameState.INGAME):
                lbl = self.font.render("    ", True, (0, 0, 0))
            else:
                lbl = self.font.render(f"{p1_total} ", True, (0, 0, 0))


            # Row 1: owned units found (the key metric — fewest found is better)
            y1 = right_panel.get_line_y("STATS_PANEL", 1, line_height)
            p1_units_s = self.font.render(str(p2_found), True, (0, 0, 192))
            screen.blit(p1_units_s, p1_units_s.get_rect(centerx=col1_cx, top=y1))

            screen.blit(lbl, lbl.get_rect(centerx=mid_cx, top=y1))
            p2_units_s = self.font.render(str(p1_found), True, (192, 0, 0))
            screen.blit(p2_units_s, p2_units_s.get_rect(centerx=col2_cx, top=y1))

            # Row 2: moves
            y2 = right_panel.get_line_y("STATS_PANEL", 2, line_height)
            screen.blit(self.font.render(str(p1_moves), True, (0, 0, 192)),
                        self.font.render(str(p1_moves), True,
                                         (0, 0, 192)).get_rect(centerx=col1_cx, top=y2))
            lbl = self.font.render("moves", True, (0, 0, 0))
            screen.blit(lbl, lbl.get_rect(centerx=mid_cx, top=y2))
            screen.blit(self.font.render(str(p2_moves), True, (192, 0, 0)),
                        self.font.render(str(p2_moves), True,
                                         (192, 0, 0)).get_rect(centerx=col2_cx, top=y2))

            # Bot resignation offer
            player_one = self.get_selection("first move")
            if player_one == "human":
                offer_color = (192, 0, 0)
                offer_text = "red offers to resign"
            else:
                offer_color = (0, 0, 192)
                offer_text = "blue offers to resign"

            if self.game_state == GameState.INGAME and self.bot_offers_resignation:
                y_resign_msg = right_panel.get_line_y("STATS_PANEL", 5, line_height)
                resign_msg = self.font_large.render(offer_text, True, offer_color)
                screen.blit(resign_msg, resign_msg.get_rect(centerx=mid_cx, top=y_resign_msg))
                y_accept_btn = right_panel.get_line_y("STATS_PANEL", 7, line_height)
                self.buttons["accept_resignation"].active = True
                self.buttons["accept_resignation"].rect = pygame.Rect(
                    mid_cx - BTW // 2, y_accept_btn, BTW, BTH)
                self.buttons["accept_resignation"].draw(screen)
            else:
                self.buttons["accept_resignation"].active = False

            # Clock display: countdown when a limit is set, elapsed otherwise
            abs_clk_y = stats_bounds["bottom"] - line_height * 1.5
            remaining = self._remaining_time()
            if remaining is not None:
                time_str = _format_time(remaining)
                clk_color = (192, 0, 0) if remaining < 30 else (0, 0, 0)
            else:
                time_str = _format_time(self.clock_elapsed)
                clk_color = (0, 0, 0)
            clk_s = self.font.render(time_str, True, clk_color)
            screen.blit(clk_s, clk_s.get_rect(
                centerx=mid_cx, centery=int(abs_clk_y + line_height // 2)))

        # Endgame result
        if self.game_state == GameState.ENDGAME and self.endgame_reason is not None:
            endgame_messages = {
                "player1_wins":        "blue wins",
                "player2_wins":        "red wins",
                "draw":                "draw",
                "player1_resignation": "blue resigned",
                "player2_resignation": "red resigned",
                "player1_timeout":     "blue is out of time",
                "player2_timeout":     "red is out of time",
            }
            endgame_colors = {
                "player1_wins":        (0, 0, 192),
                "player2_wins":        (192, 0, 0),
                "draw":                (96, 0, 96),
                "player1_resignation": (0, 0, 192),
                "player2_resignation": (192, 0, 0),
                "player1_timeout":     (0, 0, 192),
                "player2_timeout":     (192, 0, 0),
            }
            reason = str(self.endgame_reason)
            msg_text = endgame_messages.get(reason, "game over")
            msg_color = endgame_colors.get(reason, (0, 0, 0))
            stats_top_y = right_panel.get_line_y("STATS_PANEL", 5, line_height)
            end_s = self.font_large.render(msg_text, True, msg_color)
            screen.blit(end_s, end_s.get_rect(centerx=mid_cx, top=stats_top_y))

    # ================================================================== #
    #  Main render entry point                                            #
    # ================================================================== #

    def render(self, screen) -> None:
        win_width, win_height = screen.get_size()
        screen.fill(BACK_COLOR)

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

        left_panel.draw_panel(screen, "MENU_PANEL",   LT_SQUARE, GRID_COLOR)
        left_panel.draw_panel(screen, "BUTTON_PANEL", LT_SQUARE, GRID_COLOR)
        right_panel.draw_panel(screen, "PIECE_PANEL", LT_SQUARE, GRID_COLOR)
        right_panel.draw_panel(screen, "STATS_PANEL", LT_SQUARE, GRID_COLOR)

        area_left   = msg_right + margin
        area_top    = margin
        area_right  = right_left - margin
        area_bottom = win_height - margin

        if self.game_state == GameState.MENU:
            brd = int(self.get_current_selections()["board"])
            if self.board_model.cols != brd or self.board_model.rows != brd:
                self.board_model.cols = brd
                self.board_model.rows = brd
                self.board_model.clear()

        self._update_cell_size(
            area_left, area_top,
            area_right - area_left, area_bottom - area_top)

        self.board_renderer.draw_background(screen)
        self.widget_rects.clear()

        # Error overlay
        if self.error_message and pygame.time.get_ticks() < self.error_timer:
            ef = pygame.font.SysFont("arial", 18)
            es = ef.render(self.error_message, True, (200, 0, 0))
            aw = area_right - area_left
            ah = area_bottom - area_top
            ex = area_left + (aw - es.get_width()) // 2
            ey = area_top + (ah - es.get_height()) // 2
            pygame.draw.rect(screen, (255, 240, 240),
                             (ex - 8, ey - 6, es.get_width() + 16, es.get_height() + 12))
            screen.blit(es, (ex, ey))
        elif self.error_message and pygame.time.get_ticks() >= self.error_timer:
            self.error_message = ""

        self._render_board_area(screen)
        self._render_left_panel(screen, left_panel, msg_left, msg_right, msg_bottom)
        self._render_right_panel(screen, right_panel)