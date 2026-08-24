"""
duelomino_controller.py

Game controller for Duelomino: a two-player competitive polyomino game.
Combines polyomino mechanics from polyominoes with two-player turn-based
mechanics from knightstrap.
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

BOARD_MIN = 5
BOARD_MAX = 16
BOARD_DEFAULT = 8
FPS = 60
UI_SPACE = 10
BTW = int(UI_SPACE * 15)
BTH = int(UI_SPACE * 3)
MAX_CLOCK_MINUTES = 31

SHAPES_CHOICES = ["monomino", "domino", "triomino", "tetromino",
                  "pentomino", "hexomino", "heptomino", "octomino", "mixed"]
DENSITY_CHOICES = ["low", "medium", "high"]
COLORS_CHOICES = ["unique", "random", "same"]
PLAYER_ONE_CHOICES = ["human", "bot"]
OPPONENT_LEVEL_CHOICES = ["1", "2", "3", "4", "5"]

# Board colours
LT_SQUARE = (255, 255, 240)
DK_SQUARE = (232, 200, 150)
GRID_COLOR = (107, 70, 51)
BACK_COLOR = (244, 228, 195)

PLAYER_LABELS = {1: "blue", 2: "red"}
PLAYER_MSG_COLORS = {1: (0, 0, 192), 2: (192, 0, 0)}


# Player 1 (Blue)
P1_LT_VISITED = (192, 220, 248)
P1_DK_VISITED = (128, 160, 225)

# Player 2 (Red)
P2_LT_VISITED = (255, 192, 192)
P2_DK_VISITED = (225, 128, 128)

# Gray (no polyomino)
LT_VISITED = (224, 224, 224)
DK_VISITED = (192, 192, 192)

# Ring marker images (loaded in __init__)

# Bot move delay range (ms)
BOT_MOVE_DELAY_MIN = 500
BOT_MOVE_DELAY_MAX = 800

PALETTE = [
    (0, 0, 128), (0, 0, 255), (0, 64, 64), (0, 64, 192), (0, 128, 0),
    (0, 128, 128), (0, 128, 192), (0, 128, 255), (0, 192, 0), (0, 192, 192),
    (0, 192, 255), (0, 255, 0), (0, 255, 128), (0, 255, 255), (128, 0, 0),
    (128, 0, 128), (128, 0, 192), (128, 0, 255), (128, 64, 192), (128, 192, 64),
    (128, 192, 192), (128, 128, 0), (128, 128, 255), (128, 255, 0), (128, 255, 192),
    (128, 255, 255), (255, 0, 0), (255, 0, 128), (255, 0, 255), (255, 64, 64),
    (255, 64, 192), (255, 128, 0), (255, 128, 128), (255, 128, 255), (255, 255, 0),
]

# Even-parity pieces that cannot complete a full Hamiltonian tour
EXCLUDED_PIECES = {"bishop", "ferz", "dabbaba", "alfil", "threeleaper", "tripper", "camel"}

# duelominoes schema for puzzle codes: board, shapes, density, colors
duelomino_schema = [
    ("board", 4, lambda v: int(v) - BOARD_MIN),  # 5-20 → 0-15
    ("shapes", 4, {"monomino": 0, "domino": 1, "triomino": 2, "tetromino": 3,
                   "pentomino": 4, "hexomino": 5, "heptomino": 6, "octomino": 7, "mixed": 8}),
    ("density", 2, {"low": 0, "medium": 1, "high": 2}),
    ("colors", 2, {"unique": 0, "random": 1, "same": 2}),
]


# ──────────────────────────────────────────────
#  Module-level utility functions
# ──────────────────────────────────────────────

def get_globally_valid_pieces() -> List[str]:
    """Return piece names valid for any board size (excluding even-parity pieces)."""
    return [p for p in pk.PIECE_LIST if p not in EXCLUDED_PIECES]


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


def _format_clock_seconds(seconds) -> str:
    if seconds is None:
        seconds = 0
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def _display_for_clock(clock_selected) -> str:
    if clock_selected == 0:
        return "infinity"
    return _format_clock_seconds(clock_selected)


def compute_density_from_setting(density_setting: str) -> float:
    return {"high": 0.3, "medium": 0.2, "low": 0.1}.get(density_setting, 0.2)


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
        self.id = shape_id
        self.name = name
        self.puzzle_units = set(puzzle_units)
        self.color = color
        self.origin = origin
        self.orientation = orientation
        self.found_units: Set[Tuple[int, int]] = set()


def place_puzzle_layout(
        cols: int, rows: int,
        shapes_token: str,
        density: float,
        color_mode: str,
        seed: Optional[int] = None,
) -> Tuple[List[PuzzleShape], int]:
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
        type_weights = {"01": 11, "02": 11, "03": 11, "04": 10, "05": 9, "06": 6, "07": 6, "08": 2}
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


# ──────────────────────────────────────────────
#  DuelominoController
# ──────────────────────────────────────────────

class DuelominoController(BaseGameController):
    """
    Game controller for Duelomino two-player competitive polyomino game.
    Manages game state, move validation, scoring, and rendering.
    Inherits common functi
    onality from BaseGameController.
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
            font, font_large, base_dir, duelomino_schema,
        )

        # Default modes
        self.guide_mode_active = True
        self.track_mode_active = True
        self.hint_mode_active = False

        # Two-player state
        self.player1_pos: Optional[Tuple[int, int]] = None
        self.player2_pos: Optional[Tuple[int, int]] = None
        self.player1_visited: Set[Tuple[int, int]] = set()
        self.player2_visited: Set[Tuple[int, int]] = set()
        self.player1_visited_moves: Dict[Tuple[int, int], int] = {}
        self.player2_visited_moves: Dict[Tuple[int, int], int] = {}
        self.player1_legal_moves: List[Tuple[int, int]] = []
        self.player2_legal_moves: List[Tuple[int, int]] = []
        self.current_player: int = 1

        # Polyomino tracking per player
        self.player1_found_units: Set[Tuple[int, int]] = set()
        self.player2_found_units: Set[Tuple[int, int]] = set()
        self.player1_completed_shapes: int = 0
        self.player2_completed_shapes: int = 0

        # Puzzle layout state
        self.puzzle_layout: Optional[List[PuzzleShape]] = None
        self.used_seed: Optional[int] = None
        self.total_puzzle_units = 0

        # Bot scheduling
        self.bot_move_pending: bool = False
        self.bot_move_timer: int = 0

        # Bot resignation offer
        self.bot_offers_resignation: bool = False

        # Preview layout for MENU state
        self.preview_layout: Optional[List[PuzzleShape]] = None

        # Visual effects
        self.active_effect: Optional[Dict[str, Any]] = None

        # Endgame / game-flow state
        self.endgame_reason: Optional[str] = None
        self.blind_draw_active: bool = False
        self.previous_game_codec: Optional[str] = None
        self.is_piece_playable: bool = True

        # Initial menu setup
        c = (self.board_model.cols - 1) // 2
        self.player_pos = (c, c)
        self.generate_menu_preview()

        # Load ring marker images
        markers_dir = os.path.join(base_dir, "assets", "markers")
        self.flag2_blue_img = pygame.image.load(os.path.join(markers_dir, "flag2_blue.png")).convert_alpha()
        self.flag2_red_img = pygame.image.load(os.path.join(markers_dir, "flag2_red.png")).convert_alpha()

        # Cache for scaled ring images (keyed by cell size)
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
            "density": self.get_selection("density"),
            "colors": self.get_selection("colors"),
        }

    def _validate_codec(self, codec_text: str) -> Tuple[bool, Optional[Dict]]:
        try:
            params = decode_params(codec_text, duelomino_schema)
            board_val = params.get("board", 0) + BOARD_MIN
            if not (BOARD_MIN <= board_val <= BOARD_MAX):
                return False, None

            for label in ("board", "shapes", "density", "colors"):
                idx = self.label_to_index.get(label)
                if idx is None:
                    continue
                vals = self.menu_items[idx][1]
                val = params.get(label)
                if label == "board":
                    # schema stores zero-based offset; menu expects board sizes as integers
                    real_val = int(val) + BOARD_MIN
                else:
                    real_val = val
                if real_val in vals:
                    self.menu_items[idx] = (self.menu_items[idx][0], vals, vals.index(real_val))

            return True, params
        except (KeyError, ValueError, IndexError):
            return False, None

    def _game_specific_start_setup(self, seed: Optional[int] = None) -> bool:
        """Generate puzzle layout and set up two-player state."""
        sel = self.get_current_selections()
        board_size = int(sel["board"])
        density = compute_density_from_setting(sel["density"])
        color_mode = sel["colors"]
        shapes_choice = sel["shapes"]
        piece_name = sel["piece"]

        self.puzzle_layout, self.used_seed = place_puzzle_layout(
            board_size, board_size, shapes_choice, density, color_mode, seed=seed)

        if not self.puzzle_layout:
            return False

        self.total_puzzle_units = sum(len(s.puzzle_units) for s in self.puzzle_layout)
        self.player1_found_units = set()
        self.player2_found_units = set()
        self.player1_completed_shapes = 0
        self.player2_completed_shapes = 0

        self.player1_visited = set()
        self.player2_visited = set()
        self.player1_visited_moves = {}
        self.player2_visited_moves = {}
        self.current_player = 1
        self.bot_move_pending = False
        self.bot_move_timer = 0

        # Positions set by commit_start_square()
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
        """Check if neither player can move."""
        p1_stuck = not self.player1_legal_moves
        p2_stuck = not self.player2_legal_moves

        if p1_stuck and p2_stuck:
            # Determine winner by units found, then completed shapes
            p1_units = len(self.player1_found_units)
            p2_units = len(self.player2_found_units)

            if p1_units > p2_units:
                return "player1_wins"
            elif p2_units > p1_units:
                return "player2_wins"
            else:
                # Tied on units, check completed shapes
                if self.player1_completed_shapes > self.player2_completed_shapes:
                    return "player1_wins"
                elif self.player2_completed_shapes > self.player1_completed_shapes:
                    return "player2_wins"
                else:
                    # Tied on units, check total moves
                    if len(self.player1_visited) > len(self.player2_visited):
                        return "player1_wins"
                    elif len(self.player2_visited) > len(self.player1_visited):
                        return "player2_wins"
                    else:
                        return "draw"
        return None

    def _check_bot_resignation_condition(self) -> bool:
        """Check if bot should offer to resign.

        Bot offers to resign if:
        - Condition 1: Bot has no legal moves and human has a better score, OR
        - Condition 2: Human's lead is too large to overcome, OR
        - Condition 3: Using tiebreaker logic (completed shapes, then move count),
                       human is guaranteed to win

        For Duelomino: human units found > (bot units found + remaining units)
        """
        player_one = self.get_selection("first move")
        if player_one == "human":
            # P1 is human, P2 is bot
            bot_player = 2
            human_player = 1
        else:
            # P1 is bot, P2 is human
            bot_player = 1
            human_player = 2

        bot_moves = self.player1_legal_moves if bot_player == 1 else self.player2_legal_moves
        human_moves = self.player1_legal_moves if human_player == 1 else self.player2_legal_moves

        bot_units = len(self.player1_found_units) if bot_player == 1 else len(self.player2_found_units)
        human_units = len(self.player1_found_units) if human_player == 1 else len(self.player2_found_units)

        # Condition 1: bot has no legal moves and human has better score
        if not bot_moves and human_moves:
            if human_units > bot_units:
                return True

        # Condition 2: human's lead is insurmountable
        # For Duelomino: human units > (bot units + remaining units)
        all_found_units = self.player1_found_units | self.player2_found_units
        remaining_units = self.total_puzzle_units - len(all_found_units)

        if human_units > (bot_units + remaining_units):
            return True

        # Condition 3: Tiebreaker logic - human guaranteed to win
        # Check if neither player can surpass each other in units found
        bot_max_units = bot_units + remaining_units
        human_max_units = human_units + remaining_units

        # Note: bot_max_units < human_units is already caught by Condition 2
        # If bot can still catch up or surpass human in units, no resignation
        if bot_max_units > human_units:
            return False

        # If tied on maximum possible units, check completed shapes tiebreaker
        bot_shapes = self.player1_completed_shapes if bot_player == 1 else self.player2_completed_shapes
        human_shapes = self.player1_completed_shapes if human_player == 1 else self.player2_completed_shapes

        if bot_max_units == human_units:
            # Units will be tied - check shapes
            if human_shapes > bot_shapes:
                # Human wins on shapes tiebreaker
                return True
            elif human_shapes == bot_shapes:
                # Shapes also tied - check move count
                # NOTE: In Duelomino, MORE moves wins (more squares visited is better)
                bot_moves_count = len(self.player1_visited) if bot_player == 1 else len(self.player2_visited)
                human_moves_count = len(self.player1_visited) if human_player == 1 else len(self.player2_visited)

                # If bot is stuck and human can still move:
                # - If human already has more moves, they win
                # - If equal moves, human will make more moves and win
                if not bot_moves and human_moves:
                    if human_moves_count >= bot_moves_count:
                        # Human has >= moves and will continue, guaranteeing a win
                        return True

        return False

    def _render_game_specific_board(self, screen: pygame.Surface) -> None:
        """Board rendering is handled by _render_board_area()."""
        pass

    def _render_game_specific_stats(
            self, screen: pygame.Surface, stats_panel: UIPanel
    ) -> None:
        """Stats are rendered in _render_right_panel() for this game."""
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
            "player1_completed_shapes": self.player1_completed_shapes,
            "player2_completed_shapes": self.player2_completed_shapes,
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
        self.player1_completed_shapes = state.get("player1_completed_shapes", 0)
        self.player2_completed_shapes = state.get("player2_completed_shapes", 0)
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
        """Update current player's legal moves (base class hook)."""
        self._update_all_legal_moves()

    def _calculate_hint_degrees(self) -> None:
        """Compute Warnsdorff hint degrees for the current player."""
        piece_name = self.get_selection("piece")
        cur_pos = self.player1_pos if self.current_player == 1 else self.player2_pos

        if cur_pos is None:
            self.hint_degrees = {}
            return

        n = self.board_model.cols
        all_visited = self.player1_visited | self.player2_visited
        cur_moves = self.player1_legal_moves if self.current_player == 1 else self.player2_legal_moves

        self.hint_degrees = calculate_hint_degrees(
            piece_name, cur_pos, n, n, all_visited
        )

    def toggle_replay_mode(self) -> None:
        """Override to rebuild board colors when replay ends."""
        if self.game_state != GameState.ENDGAME:
            return
        if not self.replay_mode_active:
            # Starting replay
            self.replay_mode_active = True
            self.board_model.clear()
            self.replay_index = 0
            if self.replay_states:
                self._restore_game_state(self.replay_states[0])
        else:
            # Ending replay - restore final state and rebuild board colors
            self.replay_mode_active = False
            if self.replay_states:
                self._restore_game_state(self.replay_states[-1])
                # Rebuild board colors for all visited squares
                all_visited = self.player1_visited | self.player2_visited
                for pos in all_visited:
                    self._set_square_color(pos)
        # Ensure we stay in ENDGAME after state restore
        self.game_state = GameState.ENDGAME

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
                           (255, 255, 255), (107,70,51), self.resign_game),
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
                                       (255, 255, 255), (107,70,51), self.accept_bot_resignation),
            "exit": Button(pygame.Rect(0, 0, 0, 0), "exit", f,
                         (255, 255, 255), (220, 40, 40), self.quit_game),
        }

    # ================================================================== #
    #  Two-player move logic                                              #
    # ================================================================== #

    def _update_all_legal_moves(self) -> None:
        """Update legal moves for both players."""
        piece_name = self.get_selection("piece")
        n = self.board_model.cols
        all_visited = self.player1_visited | self.player2_visited

        if self.player1_pos:
            self.player1_legal_moves = get_legal_moves_for_board(
                piece_name, *self.player1_pos, n, n, all_visited
            )
        else:
            self.player1_legal_moves = []

        if self.player2_pos:
            self.player2_legal_moves = get_legal_moves_for_board(
                piece_name, *self.player2_pos, n, n, all_visited
            )
        else:
            self.player2_legal_moves = []

        # Update base class legal_moves for current player
        if self.current_player == 1:
            self.legal_moves = self.player1_legal_moves
        else:
            self.legal_moves = self.player2_legal_moves

    def _sync_base_state(self) -> None:
        """Sync base class state with current player."""
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
        """Apply move to specified player."""
        if player == 1:
            self.player1_pos = target
            self.player1_visited.add(target)
            move_num = len(self.player1_visited)
            self.player1_visited_moves[target] = move_num
            self._check_polyomino_discovery(target, 1)
            # Set square color immediately when piece lands
            self._set_square_color(target)
        else:
            self.player2_pos = target
            self.player2_visited.add(target)
            move_num = len(self.player2_visited)
            self.player2_visited_moves[target] = move_num
            self._check_polyomino_discovery(target, 2)
            # Set square color immediately when piece lands
            self._set_square_color(target)

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

        if self.clock_start_time is None:
            self.clock_start_time = time.time()

        # Apply move to current player
        self._apply_move(self.current_player, target_pos)

        # Capture state for replay / undo
        self.replay_states.append(self._capture_game_state())

        # Check end condition
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

        # Check for bot resignation conditions (only if game continues)
        player_one = self.get_selection("first move")
        has_bot = (player_one == "human" or player_one == "bot")
        if has_bot and self._check_bot_resignation_condition():
            self.bot_offers_resignation = True

        if self.hint_mode_active:
            self._calculate_hint_degrees()
        else:
            self.hint_degrees = {}

        # Schedule bot move if it's the bot's turn
        if self._is_bot_turn():
            self._schedule_bot_move()

    def commit_start_square(self, start_pos: Tuple[int, int]) -> None:
        """Commit first square for current player in select mode."""
        if self.game_state != GameState.WAITING:
            return

        player_one = self.get_selection("first move")

        if self.player1_pos is None:
            # First player selecting their start square
            self.player1_pos = start_pos
            self.player1_visited.add(start_pos)
            self.player1_visited_moves[start_pos] = 1
            self._check_polyomino_discovery(start_pos, 1)
            # Set square color immediately when piece lands
            self._set_square_color(start_pos)

            # If P2 needs to select next: check if P2 is the bot → auto-select
            if self.player2_pos is None:
                if player_one == "human":
                    # P2 is bot → auto-commit P2's start (seeded for reproducibility)
                    n = self.board_model.cols
                    rng = random.Random(self.last_puzzle_seed)
                    candidates = [(x, y) for x in range(n) for y in range(n)
                                  if (x, y) not in self.player1_visited]
                    if candidates:
                        bot_start = rng.choice(candidates)
                        self.player2_pos = bot_start
                        self.player2_visited.add(bot_start)
                        self.player2_visited_moves[bot_start] = 1
                        self._check_polyomino_discovery(bot_start, 2)
                        # Set square color immediately when piece lands
                        self._set_square_color(bot_start)
                    else:
                        # Fallback
                        self.player2_pos = start_pos
                else:
                    # P1 is bot, P2 (human) still needs to select → stay WAITING
                    self._update_all_legal_moves()
                    return

        elif self.player2_pos is None:
            # P2 (human) selecting their start square
            if start_pos in self.player1_visited:
                return  # Can't select same square as P1
            self.player2_pos = start_pos
            self.player2_visited.add(start_pos)
            self.player2_visited_moves[start_pos] = 1
            self._check_polyomino_discovery(start_pos, 2)
            # Set square color immediately when piece lands
            self._set_square_color(start_pos)

        self.move_count = len(self.player1_visited) + len(self.player2_visited)
        self._update_all_legal_moves()
        self._sync_base_state()

        # Both players have start squares → enter INGAME
        self.game_state = GameState.INGAME
        self.clock_start_time = time.time()
        self.replay_states = [self._capture_game_state()]
        self.replay_index = 0

        if self.hint_mode_active:
            self._calculate_hint_degrees()

        # Schedule bot move if it's the bot's turn first
        if self._is_bot_turn():
            self._schedule_bot_move()

    # ================================================================== #
    #  Polyomino discovery logic                                          #
    # ================================================================== #

    def _check_polyomino_discovery(self, pos: Tuple[int, int], player: int) -> None:
        """Check if player discovered new polyomino units at pos."""
        if not self.puzzle_layout:
            return

        player_found = self.player1_found_units if player == 1 else self.player2_found_units

        for shape in self.puzzle_layout:
            if pos in shape.puzzle_units and pos not in player_found:
                player_found.add(pos)

                # Check if shape is now complete for this player
                if shape.puzzle_units.issubset(player_found):
                    if player == 1:
                        self.player1_completed_shapes += 1
                    else:
                        self.player2_completed_shapes += 1

    def _set_square_color(self, pos: Tuple[int, int]) -> None:
        """Set the square color based on whether it contains a polyomino.

        This matches polyomino_controller behavior: square turns color immediately
        when the piece lands, not when the piece leaves.
        """
        gx, gy = pos

        # Check if this square is part of a polyomino
        is_polyomino = False
        polyomino_color = None

        if self.puzzle_layout:
            for shape in self.puzzle_layout:
                if pos in shape.puzzle_units:
                    is_polyomino = True
                    polyomino_color = shape.color
                    break

        # Set the square color
        if is_polyomino and polyomino_color:
            # Polyomino square → use polyomino color
            self.board_model.set_cell(gx, gy, polyomino_color)
        else:
            # Empty square → use visited color based on parity
            # Match original duelominoes parity: even sum → LT, odd sum → DK
            parity = (gx + gy) % 2 == 0
            vcolor = LT_VISITED if parity else DK_VISITED
            self.board_model.set_cell(gx, gy, vcolor)

    # ================================================================== #
    #  Bot support                                                        #
    # ================================================================== #

    def _is_bot_turn(self) -> bool:
        """Return True if the current player is the bot."""
        player_one = self.get_selection("first move")
        if player_one == "human":
            # P1 is human, P2 is the bot
            return self.current_player == 2
        else:
            # P1 is the bot, P2 is human
            return self.current_player == 1

    def _schedule_bot_move(self) -> None:
        """Queue a bot move to fire after a short delay."""
        delay = random.randint(BOT_MOVE_DELAY_MIN, BOT_MOVE_DELAY_MAX)
        self.bot_move_timer = pygame.time.get_ticks() + delay
        self.bot_move_pending = True

    def _execute_bot_move(self) -> None:
        """Execute the pending bot move."""
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

        # Get bot's found units and opponent position for advanced level
        bot_found_units = self.player1_found_units if bot_player == 1 else self.player2_found_units
        opponent_pos = self.player2_pos if bot_player == 1 else self.player1_pos

        # Package domain data as tuple for unified interface
        domain_data = (self.puzzle_layout, bot_found_units)

        chosen = make_bot_move(
            level, piece_name, bot_pos, board_size, all_visited,
            domain_data, opponent_pos
        )
        if chosen is not None:
            self.make_move(chosen)

    def update(self, dt):
        """Update game state each frame."""
        was_ingame = self.game_state == GameState.INGAME
        current_player_before = self.current_player
        super().update(dt)

        # If base class triggered timeout, translate end_state to endgame_reason
        if was_ingame and self.game_state == GameState.ENDGAME and self.end_state == "timeout":
            if self.endgame_reason is None:
                # Track which player timed out
                self.endgame_reason = f"player{current_player_before}_timeout"
            self.bot_move_pending = False
            return

        if self.game_state == GameState.INGAME:
            # Execute pending bot move when timer fires
            if self.bot_move_pending and pygame.time.get_ticks() >= self.bot_move_timer:
                self._execute_bot_move()

    # ================================================================== #
    #  Start game override                                                #
    # ================================================================== #

    def start_game(self, use_seed: Optional[int] = None) -> None:
        """Override to handle two-phase start for 'select' mode."""
        board_size = self.get_selection("board")
        piece_name = self.get_selection("piece")

        min_board = self._get_min_board_size(piece_name)
        if board_size < min_board:
            self.error_message = f"{piece_name} needs board >= {min_board}"
            self.error_timer = pygame.time.get_ticks() + 3000
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
                self.error_timer = pygame.time.get_ticks() + 3000
                return
        else:
            seed = random.randint(0, 2 ** 63 - 1)

        self.last_puzzle_seed = seed

        if not self._game_specific_start_setup(seed):
            self.error_message = "Failed to initialize game"
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
            # P1 is bot → auto-commit P1's start, wait for P2 (human) to click
            rng = random.Random(seed)
            n_sel = self.get_selection("board")
            bot_start = (rng.randint(0, n_sel - 1), rng.randint(0, n_sel - 1))
            self.player1_pos = bot_start
            self.player1_visited.add(bot_start)
            self.player1_visited_moves[bot_start] = 1
            self._check_polyomino_discovery(bot_start, 1)
        # Clear legal move caches until INGAME
        self.player1_legal_moves = []
        self.player2_legal_moves = []
        self.legal_moves = []
        self.replay_states = []
        self.game_state = GameState.WAITING


    def _common_ingame_start(self) -> None:
        """Transition to INGAME state with clean common state."""
        self.end_state = None
        self.clock_start_time = time.time()
        self.paused_elapsed = 0.0
        self.clock_elapsed = 0
        self.final_elapsed = 0
        self.replay_states = [self._capture_game_state()]
        self.replay_index = 0
        self.replay_mode_active = False
        self.peek_mode_visible = False
        self.reveal_mode_active = False
        self.hint_degrees = {}
        self.bot_move_pending = False
        self.game_state = GameState.INGAME

    # ================================================================== #
    #  Helper methods for start flows                                     #
    # ================================================================== #

    def start_flow(self) -> None:
        """Start a new game with current settings."""
        self.start_game()

    def start_blind_draw_flow(self) -> None:
        """Start a game with randomised settings."""
        self.blind_draw_active = True
        self.copy_clicked = False
        piece_name = self.get_current_selections()["piece"]
        for i, (label, blind_values, _) in enumerate(self.menu_items):
            if label in ("board", "shapes", "density", "colors"):
                if label == "board":
                    max_attempts = len(blind_values) * 2
                    attempts = 0
                    while attempts < max_attempts:
                        attempts += 1
                        new_idx = random.randint(0, len(blind_values) - 1)
                        if pr.assess_piece_playability(
                                piece_name, blind_values[new_idx]) != 'choose a larger board':
                            self.menu_items[i] = (label, blind_values, new_idx)
                            break
                    # If no valid board found (shouldn't happen), keep current selection
                else:
                    self.menu_items[i] = (label, blind_values, random.randint(0, len(blind_values) - 1))
        self.start_game()

    def new_game_flow(self) -> None:
        """Return to menu."""
        self.new_game()

    def retry_game(self) -> None:
        """Retry the last game."""
        if self.used_seed is not None:
            self.start_game(use_seed=self.used_seed)

    # ================================================================== #
    #  Utility methods                                                    #
    # ================================================================== #

    def _draw_tinted_piece(self, screen: pygame.Surface, rect: pygame.Rect, tint: Tuple[int, int, int]) -> None:
        """Draw a piece with color tint."""
        piece_name = self.get_selection("piece")
        try:
            icon = pk.get_image(piece_name)
        except Exception:
            pygame.draw.ellipse(screen, tint, rect)
            return

        scaled = pygame.transform.smoothscale(icon, (rect.width, rect.height))

        # Apply tint
        tinted = scaled.copy()
        tint_surf = pygame.Surface(tinted.get_size(), pygame.SRCALPHA)
        tint_surf.fill((*tint, 255))
        tinted.blit(tint_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        screen.blit(tinted, rect)

    def _calculate_final_elapsed(self) -> int:
        """Calculate final elapsed time for endgame."""
        if self.clock_start_time is not None:
            return int(self.paused_elapsed + (time.time() - self.clock_start_time))
        return 0

    def _go_to_endgame(self, reason: str) -> None:
        """Transition to endgame state."""
        self.game_state = GameState.ENDGAME
        self.endgame_reason = reason
        self.bot_move_pending = False
        self.bot_offers_resignation = False  # Clear resignation offer
        self.final_elapsed = self._calculate_final_elapsed()

    # ================================================================== #
    #  Game control overrides                                             #
    # ================================================================== #

    def undo_move(self) -> None:
        """Undo the last move pair (both players' most recent moves)."""
        if self.game_state != GameState.INGAME:
            return

        # Cancel pending bot move and resignation offer
        self.bot_move_pending = False
        self.bot_offers_resignation = False

        # Need at least 2 moves to undo a pair (initial state + 2 moves = 3 states)
        if len(self.replay_states) >= 3:
            self.replay_states.pop()
            self.replay_states.pop()
        elif len(self.replay_states) == 2:
            self.replay_states.pop()
        else:
            return

        self._restore_game_state(self.replay_states[-1])

        # If it's now the bot's turn, schedule bot move
        if self._is_bot_turn():
            self._schedule_bot_move()

    def resign_game(self) -> None:
        """Human player resigns."""
        if self.game_state != GameState.INGAME:
            return
        self.bot_move_pending = False
        self.final_elapsed = self._calculate_final_elapsed()
        # Track which player resigned
        resignation_reason = f"player{self.current_player}_resignation"
        self._go_to_endgame(resignation_reason)

    def accept_bot_resignation(self) -> None:
        """Human accepts bot's resignation offer."""
        if self.game_state != GameState.INGAME or not self.bot_offers_resignation:
            return
        self.bot_move_pending = False
        self.final_elapsed = self._calculate_final_elapsed()

        # Determine which player is the bot
        player_one = self.get_selection("first move")
        if player_one == "human":
            # P1 is human, P2 is bot
            bot_player = 2
        else:
            # P1 is bot, P2 is human
            bot_player = 1

        resignation_reason = f"player{bot_player}_resignation"
        self.bot_offers_resignation = False
        self._go_to_endgame(resignation_reason)

    def new_game(self) -> None:
        """Reset to MENU state."""
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
        self.player1_completed_shapes = 0
        self.player2_completed_shapes = 0
        self.current_player = 1
        self.bot_move_pending = False
        self.puzzle_layout = None
        self.used_seed = None
        self.endgame_reason = None
        self.hint_degrees = {}
        self.board_model.clear()

    def toggle_hint_mode(self) -> None:
        """Toggle hint mode (mutually exclusive with guide mode)."""
        self.hint_mode_active = not self.hint_mode_active
        if self.hint_mode_active:
            if self.game_state == GameState.INGAME:
                self._calculate_hint_degrees()
        else:
            self.hint_degrees = {}

    def toggle_guide_mode(self) -> None:
        """Toggle guide mode (mutually exclusive with hint mode)."""
        self.guide_mode_active = not self.guide_mode_active

    # ================================================================== #
    #  Event handling override                                            #
    # ================================================================== #

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle pygame events."""
        if not super().handle_event(event):
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_h and self.game_state == GameState.INGAME:
                self.toggle_hint_mode()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # Handle menu widget clicks
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
                    if lbl in ("board", "shapes", "density", "colors"):
                        self.generate_menu_preview()
                    break

            # Handle board clicks
            if self.game_state == GameState.WAITING:
                grid_pos = self.board_renderer.to_grid(mx, my)
                if grid_pos is not None:
                    self.commit_start_square(grid_pos)

            elif self.game_state == GameState.INGAME:
                # Only allow human to click
                if not self._is_bot_turn():
                    grid_pos = self.board_renderer.to_grid(mx, my)
                    if grid_pos is not None:
                        self.make_move(grid_pos)

        return True

    # ================================================================== #
    #  Utility / helper methods                                           #
    # ================================================================== #

    def get_current_selections(self) -> Dict[str, Any]:
        """Return a dict of all current menu selections."""
        return {label: vals[cur] for label, vals, cur in self.menu_items}

    def generate_menu_preview(self) -> None:
        """Generate a preview polyomino layout for the MENU screen."""
        sel = self.get_current_selections()
        board_size = int(sel["board"])
        density = compute_density_from_setting(sel["density"])
        color_mode = sel["colors"]
        shapes_choice = sel["shapes"]
        self.preview_layout, _ = place_puzzle_layout(
            board_size, board_size, shapes_choice, density, color_mode)

    def resize_board_if_needed(self) -> None:
        """Resize board model when board size setting changes."""
        new_size = int(self.get_current_selections()["board"])
        if self.board_model.cols != new_size or self.board_model.rows != new_size:
            self.board_model.cols = new_size
            self.board_model.rows = new_size
            self.board_model.clear()
            c = (new_size - 1) // 2
            self.player_pos = (c, c)

    def toggle_reveal_all_shapes(self) -> None:
        """Toggle reveal-all-units mode (ENDGAME only)."""
        if self.game_state == GameState.ENDGAME:
            self.reveal_mode_active = not self.reveal_mode_active

    def go_to_menu(self) -> None:
        """Reset to MENU state, clearing in-game data."""
        self.new_game()

    def toggle_codec_input(self) -> None:
        """Override to also clear the text box."""
        super().toggle_codec_input()
        ci = self.codec_input
        if ci:
            ci.text = ""
            ci.cursor_pos = 0
            ci.active = self.seed_mode_active

    # ================================================================== #
    #  Rendering helpers                                                  #
    # ================================================================== #

    def _draw_peek_thumbnail(self, screen, left_panel, line_height):
        """Draw peek-mode puzzle thumbnail inside BUTTON_PANEL."""
        if not (self.puzzle_layout and self.peek_mode_visible):
            return
        cols, rows = self.board_model.cols, self.board_model.rows
        if cols < 1 or rows < 1:
            return
        button_bounds = left_panel.get_bounds("BUTTON_PANEL")
        thumb_area_y = left_panel.get_line_y("BUTTON_PANEL", 0, line_height)
        thumb_area = pygame.Rect(
            button_bounds['left'] + UI_SPACE,
            thumb_area_y,
            button_bounds['width'] - UI_SPACE * 2,
            button_bounds['bottom'] - (thumb_area_y + UI_SPACE * 3),
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
        for shape in self.puzzle_layout:
            for gx, gy in shape.puzzle_units:
                pygame.draw.rect(screen, shape.color,
                                 (tx + gx * max_cell + 1,
                                  ty + gy * max_cell + 1,
                                  max_cell - 1, max_cell - 1))

    def _draw_rings(
            self, screen: pygame.Surface, found_units: Set[Tuple[int, int]],
            ring_img: pygame.Surface
    ) -> None:
        """Draw ring images centered on squares where a piece has landed on a polyomino.

        Args:
            screen: The surface to draw on
            found_units: Set of (x, y) positions where the player found polyomino units
            ring_img: The ring image to draw (ring_blue or ring_red)
        """
        cs = self.board_renderer.cell_size

        # Determine cache key based on which ring is being used
        ring_key = "blue" if ring_img is self.flag2_blue_img else "red"
        cache_key = (cs, ring_key)

        # Get or create scaled ring image for current cell size
        if cache_key not in self._scaled_ring_cache:
            self._scaled_ring_cache[cache_key] = pygame.transform.smoothscale(ring_img, (cs, cs))

        scaled_ring = self._scaled_ring_cache[cache_key]

        # Draw ring on each found unit square
        for px_pos in found_units:
            px, py = self.board_renderer.to_pixel(*px_pos)
            screen.blit(scaled_ring, (px + 4, py + 4))

    def _render_board_area(self, screen):
        """Draw the board area: preview, shapes, visited squares, arrows, pieces."""
        cs = self.current_cell_size

        # MENU: show preview layout on the board
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

        # Flash effect for newly discovered units
        if self.active_effect:
            if pygame.time.get_ticks() < self.active_effect["expires"]:
                size = self.active_effect["size"]
                color = self.active_effect["color"]
                cx_fx, cy_fx = self.active_effect["center_pos"]
                for x, y in self.active_effect["units"]:
                    pygame.draw.rect(screen, color, (
                        cx_fx - size / 2 + x * size,
                        cy_fx - size / 2 + y * size,
                        size - 2, size - 2))
            else:
                self.active_effect = None

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

        # Player 1 visited squares
        for vx, vy in disp_p1_vis:
            if (vx, vy) == disp_p1_pos:
                continue
            px, py = self.board_renderer.to_pixel(vx, vy)

            # Check if this square is part of a found polyomino
            vcolor = None
            if (vx, vy) in disp_p1_found or (vx, vy) in disp_p2_found:
                # Square has a found polyomino - get color from puzzle_layout
                if self.puzzle_layout:
                    for shape in self.puzzle_layout:
                        if (vx, vy) in shape.puzzle_units:
                            vcolor = shape.color
                            break

            if not vcolor:
                # No polyomino or not found - use board model or gray fallback
                cell_color = self.board_model.get_cell(vx, vy)
                if cell_color:
                    vcolor = cell_color
                else:
                    # Fallback to gray visited color
                    parity = (vx + vy) % 2 == 0
                    vcolor = LT_VISITED if parity else DK_VISITED

            pygame.draw.rect(screen, vcolor, (px + 3, py + 3, cs - 4, cs - 4))

            if self.track_mode_active and (vx, vy) in disp_p1_vm:
                # Check if polyomino unit
                is_poly = False
                if self.puzzle_layout:
                    for shape in self.puzzle_layout:
                        if (vx, vy) in shape.puzzle_units:
                            is_poly = True
                            break
                if is_poly:
                    luma = vcolor[0] * 0.299 + vcolor[1] * 0.587 + vcolor[2] * 0.114
                    nc = (0, 0, 0) if luma > 128 else (255, 255, 255)
                else:
                    nc = (0, 0, 192)  # Blue for P1
                ns = nf.render(str(disp_p1_vm[(vx, vy)]), True, nc)
                screen.blit(ns, ns.get_rect(center=(px + cs // 6, py + cs // 6)))

        # Player 2 visited squares
        for vx, vy in disp_p2_vis:
            if (vx, vy) == disp_p2_pos:
                continue
            px, py = self.board_renderer.to_pixel(vx, vy)

            # Check if this square is part of a found polyomino
            vcolor = None
            if (vx, vy) in disp_p1_found or (vx, vy) in disp_p2_found:
                # Square has a found polyomino - get color from puzzle_layout
                if self.puzzle_layout:
                    for shape in self.puzzle_layout:
                        if (vx, vy) in shape.puzzle_units:
                            vcolor = shape.color
                            break

            if not vcolor:
                # No polyomino or not found - use board model or gray fallback
                cell_color = self.board_model.get_cell(vx, vy)
                if cell_color:
                    vcolor = cell_color
                else:
                    # Fallback to gray visited color
                    parity = (vx + vy) % 2 == 0
                    vcolor = LT_VISITED if parity else DK_VISITED

            pygame.draw.rect(screen, vcolor, (px + 3, py + 3, cs - 4, cs - 4))

            if self.track_mode_active and (vx, vy) in disp_p2_vm:
                # Check if polyomino unit
                is_poly = False
                if self.puzzle_layout:
                    for shape in self.puzzle_layout:
                        if (vx, vy) in shape.puzzle_units:
                            is_poly = True
                            break
                if is_poly:
                    luma = vcolor[0] * 0.299 + vcolor[1] * 0.587 + vcolor[2] * 0.114
                    nc = (0, 0, 0) if luma > 128 else (255, 255, 255)
                else:
                    nc = (192, 0, 0)  # red for P2
                ns = nf.render(str(disp_p2_vm[(vx, vy)]), True, nc)
                screen.blit(ns, ns.get_rect(center=(px + (cs // 6), py + cs // 6)))

        # Guide arrows for active player
        if self.guide_mode_active and self.arrows:
            if self.game_state == GameState.ENDGAME and self.replay_mode_active:
                disp_pos = disp_p1_pos if disp_cur == 1 else disp_p2_pos
                all_vis = disp_p1_vis | disp_p2_vis
                if disp_pos:
                    piece = self.get_selection("piece")
                    n = self.board_model.cols
                    rp_moves = get_legal_moves_for_board(piece, *disp_pos, n, n, all_vis)
                    self._draw_arrows(screen, rp_moves, disp_pos)
            elif self.game_state in (GameState.INGAME, GameState.WAITING):
                cur_pos = disp_p1_pos if disp_cur == 1 else disp_p2_pos
                cur_mvs = self.player1_legal_moves if disp_cur == 1 else self.player2_legal_moves
                if cur_pos and cur_mvs:
                    self._draw_arrows(screen, cur_mvs, cur_pos)

        # Hint degrees (INGAME, current player only)
        if self.hint_mode_active and self.hint_degrees and self.game_state == GameState.INGAME:
            for (hx, hy), deg in self.hint_degrees.items():
                px, py = self.board_renderer.to_pixel(hx, hy)
                hs = nf.render(str(deg), True, (107, 50, 71))
                screen.blit(hs, hs.get_rect(center=(px + cs - (cs // 6), py + cs // 6)))

        # Draw rings on polyomino squares where pieces have landed (before drawing pieces)
        self._draw_rings(screen, disp_p1_found, self.flag2_blue_img)
        self._draw_rings(screen, disp_p2_found, self.flag2_red_img)

        # Draw polyomino colors under current piece positions if on found polyomino
        for pos, found_set in [(disp_p2_pos, disp_p1_found | disp_p2_found),
                                (disp_p1_pos, disp_p1_found | disp_p2_found)]:
            if pos and pos in found_set and self.puzzle_layout:
                px, py = self.board_renderer.to_pixel(*pos)
                for shape in self.puzzle_layout:
                    if pos in shape.puzzle_units:
                        pygame.draw.rect(screen, shape.color, (px + 3, py + 3, cs - 4, cs - 4))
                        break

        # Draw P2 piece (red tint) then P1 (blue tint) on top
        if disp_p2_pos and cs > 0:
            ppx, ppy = self.board_renderer.to_pixel(*disp_p2_pos)
            self._draw_tinted_piece(screen,
                                    pygame.Rect(ppx + 1, ppy + 1, cs - 2, cs - 2),
                                    P2_DK_VISITED)
        if disp_p1_pos and cs > 0:
            ppx, ppy = self.board_renderer.to_pixel(*disp_p1_pos)
            self._draw_tinted_piece(screen,
                                    pygame.Rect(ppx + 1, ppy + 1, cs - 2, cs - 2),
                                    P1_DK_VISITED)

    def _render_left_panel(self, screen, left_panel, msg_left, msg_right, msg_bottom):
        """Render MENU_PANEL (settings) and BUTTON_PANEL (action buttons)."""
        btn_w = UI_SPACE
        line_height = self.font.get_linesize() + UI_SPACE

        # ---- MENU_PANEL: selector rows ----
        menu_bounds = left_panel.get_bounds("MENU_PANEL")
        text_x = menu_bounds['left'] + UI_SPACE
        menu_panel_items = [(i, item) for i, item in enumerate(self.menu_items)
                            if item[0] not in ('piece', 'clock')]

        max_label_w = max(
            self.font.render(l + "", True, (0, 0, 0)).get_width()
            for l, _, _ in self.menu_items if l != 'piece')
        minus_x = text_x + max_label_w + UI_SPACE
        plus_x = menu_bounds['left'] + menu_bounds['width'] - UI_SPACE * 4

        for list_idx, (item_idx, (label, values, cur_idx)) in enumerate(menu_panel_items):
            panel_y = left_panel.get_line_y("MENU_PANEL", list_idx, line_height)
            row_cy = panel_y + btn_w // 2
            lbl_surf = self.font.render(f"{label}", True, (0, 0, 0))
            screen.blit(lbl_surf, lbl_surf.get_rect(midleft=(text_x, row_cy)))

            show_text = not self.blind_draw_active or self.game_state == GameState.ENDGAME
            if show_text:
                val = values[cur_idx]
                sel_text = _display_for_clock(val) if label == "clock" else str(val)
                sel_surf = self.font.render(sel_text, True, (0, 0, 0))
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

        # retry (ENDGAME, same slot)
        self.buttons["retry"].active = self.game_state == GameState.ENDGAME
        self.buttons["retry"].rect = left_panel.get_widget_rect("MENU_PANEL", 7, BTW, BTH)
        if self.buttons["retry"].active:
            self.buttons["retry"].draw(screen)

        # enter/cancel share code (MENU only)
        self.buttons["enter_code"].active = self.game_state == GameState.MENU
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
            code_y = left_panel.get_line_y("MENU_PANEL", 10, line_height)
            code_cx = menu_bounds['left'] + menu_bounds['width'] // 2
            code_s = self.font.render(self.puzzle_code, True, (0, 0, 0))
            screen.blit(code_s, code_s.get_rect(center=(code_cx, code_y + btn_w)))

        # copy share code (WAITING/INGAME/ENDGAME)
        self.buttons["copy_code"].active = self.game_state in (
            GameState.WAITING, GameState.INGAME, GameState.ENDGAME)
        self.buttons["copy_code"].bg_color = (224, 64, 128) if self.copy_clicked else (224, 0, 96)
        self.buttons["copy_code"].text = ("share code copied" if self.copy_clicked
                                          else "copy share code")
        self.buttons["copy_code"].rect = left_panel.get_widget_rect("MENU_PANEL", 9, BTW, BTH)
        if self.buttons["copy_code"].active:
            self.buttons["copy_code"].draw(screen)

        # ---- BUTTON_PANEL ----
        button_bounds = left_panel.get_bounds("BUTTON_PANEL")

        # WAITING prompt
        if self.game_state == GameState.WAITING:
            player_one = self.get_selection("first move")
            if player_one == "bot" and self.player1_pos is None:
                waiting_msg = "choose a starting square"
            elif player_one == "human" and self.player2_pos is None:
                waiting_msg = "click a starting square"
            else:
                waiting_msg = "click a starting square"
            choose_s = self.font.render(waiting_msg, True, (255, 0, 0))
            choose_y = left_panel.get_line_y("BUTTON_PANEL", 0, line_height)
            screen.blit(choose_s, choose_s.get_rect(
                centerx=button_bounds['center_x'], centery=choose_y + btn_w // 2))

        # start (MENU)
        self.buttons["start"].active = self.is_piece_playable and self.game_state == GameState.MENU
        self.buttons["start"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        if self.buttons["start"].active:
            self.buttons["start"].draw(screen)

        # reveal (ENDGAME, same slot)
        self.buttons["reveal"].active = self.game_state == GameState.ENDGAME
        self.buttons["reveal"].text = ('hide missed units' if self.reveal_mode_active
                                       else 'show all units')
        self.buttons["reveal"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        if self.buttons["reveal"].active:
            self.buttons["reveal"].draw(screen)

        # hint mode – MENU, INGAME
        self.buttons["hint_mode"].active = self.game_state == GameState.INGAME
        self.buttons["hint_mode"].text = ('hide move degrees' if self.hint_mode_active
                                          else 'show move degrees')
        self.buttons["hint_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        if self.buttons["hint_mode"].active:
            self.buttons["hint_mode"].draw(screen)

        # guide mode – MENU, INGAME, ENDGAME
        self.buttons["guide_mode"].active = self.game_state in (
            GameState.MENU, GameState.INGAME, GameState.ENDGAME)
        self.buttons["guide_mode"].text = ('hide move guide' if self.guide_mode_active
                                           else 'show move guide')
        self.buttons["guide_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 2, BTW, BTH)
        if self.buttons["guide_mode"].active:
            self.buttons["guide_mode"].draw(screen)

        # track mode – always
        self.buttons["track_mode"].active = True
        self.buttons["track_mode"].text = ('hide move track' if self.track_mode_active
                                           else 'show move track')
        self.buttons["track_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 4, BTW, BTH)
        self.buttons["track_mode"].draw(screen)

        # undo (INGAME with history)
        self.buttons["undo_mode"].active = (self.game_state == GameState.INGAME
                                            and len(self.replay_states) > 1)
        self.buttons["undo_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 6, BTW, BTH)
        if self.buttons["undo_mode"].active:
            self.buttons["undo_mode"].draw(screen)

        # replay in ENDGAME
        self.buttons["replay_mode"].active = self.game_state == GameState.ENDGAME
        self.buttons["replay_mode"].text = ('end replay' if self.replay_mode_active
                                            else 'start replay')
        self.buttons["replay_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 6, BTW, BTH)
        if self.buttons["replay_mode"].active:
            self.buttons["replay_mode"].draw(screen)

        # Replay nav buttons
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

        # resign (INGAME)
        self.buttons["resign"].active = self.game_state == GameState.INGAME
        self.buttons["resign"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 8, BTW, BTH)
        if self.buttons["resign"].active:
            self.buttons["resign"].draw(screen)

        # new game (WAITING / ENDGAME)
        self.buttons["new_game"].active = self.game_state in (GameState.WAITING, GameState.ENDGAME)
        self.buttons["new_game"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 8, BTW, BTH)
        if self.buttons["new_game"].active:
            self.buttons["new_game"].draw(screen)

        # peek (INGAME / ENDGAME, fixed bottom)
        self.buttons["peek_mode"].active = self.game_state in (GameState.INGAME, GameState.ENDGAME)
        self.buttons["peek_mode"].text = 'hide' if self.peek_mode_visible else 'peek'
        self.buttons["peek_mode"].rect = pygame.Rect(
            msg_left + UI_SPACE * 3, msg_bottom - UI_SPACE * 5, BTW // 2, BTH)
        if self.buttons["peek_mode"].active:
            self.buttons["peek_mode"].draw(screen)

        # exit (always, bottom-right)
        self.buttons["exit"].rect = pygame.Rect(
            msg_right - UI_SPACE * 11, msg_bottom - UI_SPACE * 5, BTW // 2, BTH)
        self.buttons["exit"].draw(screen)

        self._draw_peek_thumbnail(screen, left_panel, line_height)

    def _render_right_panel(self, screen, right_panel):
        """Render PIECE_PANEL (piece selector) and STATS_PANEL (two-column stats)."""
        line_height = self.font.get_linesize() + UI_SPACE
        btn_w = UI_SPACE

        # ---- PIECE_PANEL ----
        piece_bounds = right_panel.get_bounds("PIECE_PANEL")
        right_tx = piece_bounds['left'] + UI_SPACE

        piece_idx = self.label_to_index["piece"]
        _, piece_values, piece_cur = self.menu_items[piece_idx]
        piece_name = piece_values[piece_cur] if piece_values else ""

        p_line_y = right_panel.get_line_y("PIECE_PANEL", 0, line_height)
        lbl_s = self.font.render("piece:", True, (0, 0, 0))
        lbl_rect = lbl_s.get_rect(midleft=(right_tx, p_line_y))
        p_minus_x = lbl_rect.right + UI_SPACE
        p_plus_x = piece_bounds['left'] + piece_bounds['width'] - UI_SPACE - btn_w * 3

        sel_s = self.font_large.render(piece_name, True, (0, 0, 0))
        screen.blit(sel_s, sel_s.get_rect(center=(piece_bounds['center_x'], p_line_y + 8)))

        move_set_text = pk.get_piece_move_sets_text(piece_name)
        mst_s = self.font.render(move_set_text, True, (0, 0, 0))
        screen.blit(mst_s, mst_s.get_rect(
            centerx=piece_bounds['center_x'],
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

        # ---- STATS_PANEL: two-column layout ----
        stats_bounds = right_panel.get_bounds("STATS_PANEL")
        stats_w = stats_bounds['width']
        stats_left = stats_bounds['left']
        col1_cx = stats_left + stats_w // 4      # Player 1 column centre
        col2_cx = stats_left + 3 * stats_w // 4  # Player 2 column centre
        mid_cx = stats_bounds['center_x']

        if self.game_state in (GameState.WAITING, GameState.INGAME, GameState.ENDGAME):
            # Use replay snapshot when replaying
            if (self.game_state == GameState.ENDGAME
                    and self.replay_mode_active and self.replay_states):
                snap = self.replay_states[self.replay_index]
                p1_vis = snap.get("player1_visited", set())
                p2_vis = snap.get("player2_visited", set())
                p1_units = len(snap.get("player1_found_units", set()))
                p2_units = len(snap.get("player2_found_units", set()))
                p1_shapes = snap.get("player1_completed_shapes", 0)
                p2_shapes = snap.get("player2_completed_shapes", 0)
                disp_cur = snap.get("current_player", 1)
            else:
                p1_vis = self.player1_visited
                p2_vis = self.player2_visited
                p1_units = len(self.player1_found_units)
                p2_units = len(self.player2_found_units)
                p1_shapes = self.player1_completed_shapes
                p2_shapes = self.player2_completed_shapes
                disp_cur = self.current_player

            p1_moves = len(p1_vis)
            p2_moves = len(p2_vis)

            # Row 0: column headers
            p1_hdr_color = (0, 0, 192) #if disp_cur == 1 else (0, 0, 0)
            p2_hdr_color = (192, 0, 0)  #if disp_cur == 2 else (0, 0, 0)
            y0 = right_panel.get_line_y("STATS_PANEL", 0, line_height)
            p1_h = self.font.render("blue", True, p1_hdr_color)
            p2_h = self.font.render("red", True, p2_hdr_color)
            screen.blit(p1_h, p1_h.get_rect(centerx=col1_cx, top=y0))
            screen.blit(p2_h, p2_h.get_rect(centerx=col2_cx, top=y0))

            # units
            y2 = right_panel.get_line_y("STATS_PANEL", 1, line_height)
            screen.blit(self.font.render(str(p1_units), True, (0, 0, 192)),
                        self.font.render(str(p1_units), True,
                                         (0, 0, 192)).get_rect(centerx=col1_cx, top=y2))
            # In blind draw mode (WAITING/INGAME), hide the total value but keep the label
            if self.blind_draw_active and self.game_state in (GameState.WAITING, GameState.INGAME):
                lbl = self.font.render("units", True, (0, 0, 0))
            else:
                lbl = self.font.render(f"{self.total_puzzle_units} units", True, (0, 0, 0))
            screen.blit(lbl, lbl.get_rect(centerx=mid_cx, top=y2))
            screen.blit(self.font.render(str(p2_units), True, (192, 0, 0)),
                        self.font.render(str(p2_units), True,
                                         (192, 0, 0)).get_rect(centerx=col2_cx, top=y2))

            # shapes
            y3 = right_panel.get_line_y("STATS_PANEL", 2, line_height)
            surf = self.font.render(str(p1_shapes), True, (0, 0, 192))
            screen.blit(surf, surf.get_rect(centerx=col1_cx, top=y3))
            total_shapes = len(self.puzzle_layout)
            # In blind draw mode (WAITING/INGAME), hide the total value but keep the label
            if self.blind_draw_active and self.game_state in (GameState.WAITING, GameState.INGAME):
                lbl = self.font.render("shapes", True, (0, 0, 0))
            else:
                lbl = self.font.render(f"{total_shapes} shapes", True, (0, 0, 0))
            screen.blit(lbl, lbl.get_rect(centerx=mid_cx, top=y3))
            surf = self.font.render(str(p2_shapes), True, (128, 0, 0))
            screen.blit(surf, surf.get_rect(centerx=col2_cx, top=y3))

            # moves
            y1 = right_panel.get_line_y("STATS_PANEL", 3, line_height)
            screen.blit(self.font.render(str(p1_moves), True, (0, 0, 192)),
                        self.font.render(str(p1_moves), True,
                                         (0, 0, 192)).get_rect(centerx=col1_cx, top=y1))
            lbl = self.font.render("moves", True, (0, 0, 0))
            screen.blit(lbl, lbl.get_rect(centerx=mid_cx, top=y1))
            screen.blit(self.font.render(str(p2_moves), True, (192, 0, 0)),
                        self.font.render(str(p2_moves), True,
                                         (192, 0, 0)).get_rect(centerx=col2_cx, top=y1))

            # Turn indicator (INGAME)
            #if self.game_state == GameState.INGAME:
            #    y_turn = right_panel.get_line_y("STATS_PANEL", 6, line_height)
            turn_color = (0, 0, 192) if disp_cur == 1 else (192, 0, 0)
            #    turn_s = self.font.render(f"player {disp_cur}'s turn", True, turn_color)
                #screen.blit(turn_s, turn_s.get_rect(centerx=mid_cx, top=y_turn))

            # Bot resignation offer

            # Determine human's color for message
            player_one = self.get_selection("first move")
            if player_one == "human":
                # P1 is human (blue)
                offer_color = (192, 0, 0)
                offer_text = "red offers to resign"
            else:
                # P2 is human (red)
                offer_color = (0, 0, 192)
                offer_text = "blue offers to resign"

            if self.game_state == GameState.INGAME and self.bot_offers_resignation:
                y_resign_msg = right_panel.get_line_y("STATS_PANEL", 5, line_height)
                resign_msg = self.font_large.render(offer_text, True, offer_color)
                screen.blit(resign_msg, resign_msg.get_rect(centerx=mid_cx, top=y_resign_msg))

                # Accept button
                y_accept_btn = right_panel.get_line_y("STATS_PANEL", 7, line_height)


                self.buttons["accept_resignation"].active = True
                self.buttons["accept_resignation"].rect = pygame.Rect(
                    mid_cx - BTW // 2, y_accept_btn, BTW, BTH)
                self.buttons["accept_resignation"].draw(screen)
            else:
                self.buttons["accept_resignation"].active = False

            # Clock (bottom of STATS_PANEL)
            clock_val = self.get_selection("clock") if "clock" in self.label_to_index else 0
            clock_color = (0, 0, 0)
            if self.game_state == GameState.WAITING:
                time_str = "0:00"
            elif clock_val == 0:
                time_str = _format_time(self.clock_elapsed)
            else:
                rem = self._remaining_time()
                if rem is not None:
                    time_str = _format_clock_seconds(rem)
                    clock_color = (200, 0, 0) if rem < 30 else (0, 0, 0)
                else:
                    time_str = _format_time(self.clock_elapsed)
            abs_clk_y = stats_bounds['bottom'] - line_height * 1.5
            clk_s = self.font.render(time_str, True, clock_color)
            screen.blit(clk_s, clk_s.get_rect(
                centerx=mid_cx, centery=int(abs_clk_y + line_height // 2)))

        # Endgame result message
        if self.game_state == GameState.ENDGAME and self.endgame_reason is not None:
            endgame_messages = {
                "player1_wins":         "blue wins",
                "player2_wins":         "red wins",
                "draw":                 "draw",
                "player1_resignation":  "blue resigned",
                "player2_resignation":  "red resigned",
                "player1_timeout":      " blue is out of time",
                "player2_timeout":      " red is out of time",
            }
            endgame_colors = {
                "player1_wins":         (0, 0, 192),
                "player2_wins":         (192, 0, 0),
                "draw":                 (96, 0, 96),
                "player1_resignation":  (0, 0, 192),
                "player2_resignation":  (192, 0, 0),
                "player1_timeout":      (0, 0, 192),
                "player2_timeout":      (192, 0, 0),
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
        """Render the full game frame."""
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

        left_panel.draw_panel(screen,  "MENU_PANEL",   LT_SQUARE, GRID_COLOR)
        left_panel.draw_panel(screen,  "BUTTON_PANEL", LT_SQUARE, GRID_COLOR)
        right_panel.draw_panel(screen, "PIECE_PANEL",  LT_SQUARE, GRID_COLOR)
        right_panel.draw_panel(screen, "STATS_PANEL",  LT_SQUARE, GRID_COLOR)

        area_left   = msg_right + margin
        area_top    = margin
        area_right  = right_left - margin
        area_bottom = win_height - margin

        # Sync board model in MENU
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