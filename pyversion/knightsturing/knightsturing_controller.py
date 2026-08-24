"""
knightsturing_controller.py

Game controller for the Knight's Turing Machine ("knightsturing") game.

The player moves a single token across a rectangular grid.  After every move
the active piece transforms according to a fixed rule set (simple cycle or
colour-based transitions).  The goal is a self-avoiding Hamiltonian path
(visit every square exactly once).

UI follows knightstour_controller.py as a template.
"""

import base64
import math
import random
import sys
import time
from collections import deque
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import os
import pygame

# --- path setup ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_DIR = os.path.dirname(os.path.abspath(__file__))
SHAREDLIB = os.path.join(BASE_DIR, "sharedlib")
for _p in (BASE_DIR, SHAREDLIB, GAME_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import piecekeeper as pk
from gameboard import BoardModel, BoardRenderer
from uipanel import UIPanel
from widgets import Button
from move_system import get_legal_moves_for_board
from move_hint import calculate_hint_degrees
from base_game_controller import BaseGameController, GameState

from pyversion.knightsturing.turing_engine import build_ruleset1, build_ruleset2, build_flip_flop_ruleset, RuleSet
from pyversion.knightsturing.knightsturing_generator import TURING_PIECES, generate_puzzle

# ------------------------------------------------------------------ #
#  Constants                                                           #
# ------------------------------------------------------------------ #

BOARD_MIN = 5
BOARD_MAX = 6
BOARD_DEFAULT = 6
FPS = 60
UI_SPACE = 10
BTW = int(UI_SPACE * 15)
BTH = int(UI_SPACE * 3)
MAX_CLOCK_SECONDS = 330
SOLUTION_SEARCH_TIMEOUT_S = 5.0   # seconds budget for post-select path search

RULESET_NAMES = ["2-cycle", "3-cycle", "4-cycle"]
CLOCK_MODES = ["game", "move"]
CLOCK_VALUES = [0] + list(range(30, MAX_CLOCK_SECONDS, 30))  # 12 values

# Number of pieces required for each named rule set
_RULESET_NUM_PIECES: Dict[str, int] = {
    "2-cycle":  2,
    "3-cycle":  3,
    "4-cycle": 3,
}

# Internal ruleset_id used by the generator / engine
_RULESET_ID: Dict[str, int] = {
    "2-cycle":  1,
    "3-cycle":  1,
    "4-cycle": 3,
}

LT_SQUARE = (255, 255, 240)
DK_SQUARE = (232, 200, 150)
LT_VISITED = (192, 230, 192)
DK_VISITED = (128, 180, 128)
GRID_COLOR = (107, 70, 51)
BACK_COLOR = (244, 228, 195)
WARN_COLOR = (128, 0, 0)

ACTIVE_PIECE_COLOR = (34, 139, 34)    # highlight for active piece in panel
INACTIVE_PIECE_COLOR = (80, 80, 80)

# Colour used to tint the start square
#START_SQ_COLOR = (255, 220, 60)

# ------------------------------------------------------------------ #
#  Module-level helpers                                                #
# ------------------------------------------------------------------ #

@lru_cache(maxsize=None)
def _piece_min_board_size(piece_name: str) -> int:
    """Smallest board on which *piece_name* can reach every square via BFS."""
    move_func = pk.get_move_func(piece_name)
    for n in range(BOARD_MIN, BOARD_MAX + 1):
        reachable = {(0, 0)}
        queue = deque([(0, 0)])
        while queue:
            cx, cy = queue.popleft()
            for mv in move_func(cx, cy, n):
                if mv not in reachable:
                    reachable.add(mv)
                    queue.append(mv)
        if len(reachable) == n * n:
            return n
    return BOARD_MAX + 1


@lru_cache(maxsize=None)
def _piece_min_any_move(piece_name: str) -> int:
    """Smallest board on which *piece_name* has at least one legal move.

    Returns ``BOARD_MAX + 1`` when the piece cannot move on any supported
    board size; the caller's ``board_size >= min_b`` check will then always
    be False, keeping the start button disabled for that configuration.
    """
    move_func = pk.get_move_func(piece_name)
    for n in range(BOARD_MIN, BOARD_MAX + 1):
        for r in range(n):
            for c in range(n):
                if move_func(r, c, n):
                    return n
    return BOARD_MAX + 1


def _format_clock_seconds(seconds: Any) -> str:
    if seconds is None:
        seconds = 0
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def _display_for_selection(clock_selected: Any) -> str:
    if clock_selected == 0:
        return "infinity"
    return _format_clock_seconds(clock_selected)


# ------------------------------------------------------------------ #
#  Codec helpers (custom 10-byte / 80-bit codec)                      #
# ------------------------------------------------------------------ #
#
# Version 2 bit layout (MSB first):
#   [79:76] version (4)       = 2
#   [75:72] board − BOARD_MIN (4)
#   [71:70] ruleset_idx (2)   0='cycle 2', 1='cycle 3', 2='flip-flop'
#   [69:66] clock_idx (4)     index into CLOCK_VALUES
#   [65]    time_per (1)      0=game 1=move
#   [64:61] piece0_idx (4)
#   [60:57] piece1_idx (4)
#   [56:53] piece2_idx (4)
#   [52:0]  seed (53)
#
# 10 bytes → base-32 → 16 chars (no padding) → 4 groups of 4 = "XXXX-XXXX-XXXX-XXXX"
# ------------------------------------------------------------------ #

CODEC_TEXT_LENGTH = 16  # chars (excluding dashes)
_CODEC_VERSION = 2


def _encode_puzzle_code(
    board_size: int,
    ruleset_name: str,
    clock_idx: int,
    time_per: str,
    piece_idxs: List[int],
    seed: int,
) -> str:
    ruleset_idx = RULESET_NAMES.index(ruleset_name) if ruleset_name in RULESET_NAMES else 0
    bits = ""
    bits += format(_CODEC_VERSION, "04b")          # [79:76]
    bits += format(board_size - BOARD_MIN, "04b")  # [75:72]
    bits += format(ruleset_idx, "02b")             # [71:70]
    bits += format(clock_idx, "04b")               # [69:66]
    bits += "1" if time_per == "move" else "0"     # [65]
    for i in range(3):
        idx = piece_idxs[i] if i < len(piece_idxs) else 0
        bits += format(idx & 0xF, "04b")           # [64:53]
    remaining = 80 - len(bits)                     # = 53
    bits += format(int(seed) % (1 << remaining), f"0{remaining}b")

    val = int(bits, 2)
    data = val.to_bytes(10, "big")
    encoded = base64.b32encode(data).decode("ascii").rstrip("=")
    return "-".join(encoded[i: i + 4] for i in range(0, 16, 4))


def _decode_puzzle_code(code: str) -> Optional[Dict[str, Any]]:
    """Decode a 16-char share code. Returns a param dict or None on error."""
    try:
        raw = code.replace("-", "").replace(" ", "").upper()
        if len(raw) != CODEC_TEXT_LENGTH:
            return None
        padding = (8 - len(raw) % 8) % 8
        data = base64.b32decode(raw + "=" * padding)
        if len(data) < 10:
            return None
        val = int.from_bytes(data[:10], "big")
        bits = format(val, "080b")

        version = int(bits[0:4], 2)
        if version != _CODEC_VERSION:
            return None
        board       = int(bits[4:8],   2) + BOARD_MIN
        ruleset_idx = int(bits[8:10],  2)
        clk_idx     = int(bits[10:14], 2)
        time_per    = "move" if bits[14] == "1" else "game"
        p_idxs      = [int(bits[15 + i*4: 19 + i*4], 2) for i in range(3)]
        seed        = int(bits[27:80], 2)

        if not (BOARD_MIN <= board <= BOARD_MAX):
            return None
        if not (0 <= clk_idx < len(CLOCK_VALUES)):
            return None
        if not (0 <= ruleset_idx < len(RULESET_NAMES)):
            return None
        if any(idx >= len(TURING_PIECES) for idx in p_idxs):
            return None
        ruleset_name = RULESET_NAMES[ruleset_idx]
        num_pieces   = _RULESET_NUM_PIECES[ruleset_name]
        pieces = [TURING_PIECES[idx] for idx in p_idxs]

        return {
            "board":        board,
            "ruleset_name": ruleset_name,
            "num_pieces":   num_pieces,
            "clock_idx":    clk_idx,
            "clock":        CLOCK_VALUES[clk_idx],
            "time_per":     time_per,
            "pieces":       pieces,
            "seed":         seed,
        }
    except Exception:
        return None


# ------------------------------------------------------------------ #
#  Controller                                                          #
# ------------------------------------------------------------------ #

class KnightsTuringController(BaseGameController):
    """
    Game controller for Knight's Turing Machine.

    Inherits common game-loop infrastructure from BaseGameController and adds
    the cycling-leaper logic specific to this game.
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
    ) -> None:
        # Pass an empty schema – we use a custom codec, not the generic one.
        super().__init__(
            board_model, board_renderer, menu_items, label_to_index,
            font, font_large, base_dir, schema=[],
        )

        # Piece selector state (up to 4 slots, each starts as "knight")
        self.piece_selections: List[str] = ["threeleaper", "camel", "ferz"]

        # Active piece during gameplay
        self.current_piece: str = "knight"

        # Rule set object (set when a game starts)
        self.ruleset: Optional[RuleSet] = None

        # Solution path found by the generator (for peek / reveal)
        # Each entry: (row, col, piece_to_use_next)
        self.solution_path: Optional[List[Tuple[int, int, str]]] = None

        # Win flag
        self.hamiltonian_complete: bool = False

        # Per-move clock tracking (mirrors knightstour_controller)
        self.move_start_time: Optional[float] = None

        # Menu-board preview position
        self.preview_pos: Optional[Tuple[int, int]] = None

        # Peek mode (show solution thumbnail)
        self.peek_mode_visible: bool = False

        # Override base-class defaults
        self.guide_mode_active = True
        self.track_mode_active = True

    # ================================================================== #
    #  Abstract implementations                                           #
    # ================================================================== #

    def _get_min_board_size(self, piece_name: str) -> int:
        """Return the minimum board size required for the current piece selection.

        For a single piece the board must be large enough for that piece to
        reach every square (solo-tour check).  For multi-piece combinations
        each piece only needs to be able to make at least one legal move;
        color-bound pieces (dabbaba, ferz, alfil, …) are valid in a cycle
        even though they can never solo-tour.
        """
        num = self._num_active_pieces()
        pieces = self.piece_selections[:num]
        if num == 1:
            return _piece_min_board_size(pieces[0])
        return max(_piece_min_any_move(p) for p in pieces)

    def _num_active_pieces(self) -> int:
        """Return the number of pieces required by the selected rule set."""
        ruleset_name = self.get_selection("rule set")
        return _RULESET_NUM_PIECES.get(ruleset_name, 2)

    def _get_encode_params(self) -> Dict[str, Any]:
        # Not used – we override the codec directly.
        return {}

    def _validate_codec(self, codec_text: str) -> Tuple[bool, Optional[Dict]]:
        """Decode a share code and apply settings to menu_items."""
        params = _decode_puzzle_code(codec_text)
        if params is None:
            return False, None

        def _apply(label: str, value: Any) -> None:
            idx = self.label_to_index.get(label)
            if idx is None:
                return
            lbl, vals, _ = self.menu_items[idx]
            if value in vals:
                self.menu_items[idx] = (lbl, vals, vals.index(value))

        _apply("board",    params["board"])
        _apply("rule set", params["ruleset_name"])
        _apply("clock",    params["clock"])
        _apply("time per", params["time_per"])

        # Restore piece selections
        n = params["num_pieces"]
        for i in range(3):
            self.piece_selections[i] = params["pieces"][i] if i < n else "knight"

        return True, params

    def _game_specific_start_setup(self, seed: Optional[int] = None) -> bool:
        """Generate puzzle and place first piece at path[0]."""
        board_size   = self.get_selection("board")
        ruleset_name = self.get_selection("rule set")
        num_pieces   = self._num_active_pieces()
        ruleset_id   = _RULESET_ID[ruleset_name]
        pieces       = self.piece_selections[:num_pieces]

        # Build rule set object
        if ruleset_id == 1:
            self.ruleset = build_ruleset1(pieces)
        elif ruleset_id == 3:
            self.ruleset = build_flip_flop_ruleset(pieces)
        else:
            self.ruleset = build_ruleset2(pieces)

        self.hamiltonian_complete = False
        self.solution_path = None

        # Always generate a puzzle; start at the zeroth square of the path.
        path = generate_puzzle(
            board_size, pieces, ruleset_id,
            seed=seed if seed is not None else 0,
            time_limit=10.0,
        )
        if path is None:
            return False

        self.solution_path = path
        start_row, start_col, _start_piece = path[0]
        self.player_pos = (start_row, start_col)

        self.current_piece = pieces[0]
        self.visited = {self.player_pos}
        self.visited_moves = {self.player_pos: 0}
        self.move_count = 0

        self.guide_mode_active  = True
        self.track_mode_active  = True
        self.hint_mode_active   = False
        self.reveal_mode_active = False

        self._update_legal_moves()
        return True

    def _game_specific_make_move(self, target: Tuple[int, int]) -> bool:
        """Apply the Turing-machine rule to advance to *target*."""
        self.move_count += 1
        # Transform piece upon landing on the new square.
        self.current_piece = self.ruleset.apply(
            self.current_piece, target[0], target[1], self.move_count
        )
        return True

    def _validate_move(self, target: Tuple[int, int]) -> bool:
        return target in self.legal_moves

    def _check_endgame_conditions(self) -> Optional[str]:
        board_size = self.get_selection("board")
        if len(self.visited) == board_size * board_size:
            self.hamiltonian_complete = True
            return "hamiltonian_complete"
        if not self.legal_moves:
            return "no_moves"
        return None

    def _capture_game_state(self) -> Dict[str, Any]:
        return {
            "pos":           self.player_pos,
            "visited":       self.visited.copy(),
            "visited_moves": self.visited_moves.copy(),
            "move_count":    self.move_count,
            "current_piece": self.current_piece,
        }

    def _restore_game_state(self, state: Dict[str, Any]) -> None:
        self.player_pos    = state["pos"]
        self.visited       = state["visited"].copy()
        self.visited_moves = state["visited_moves"].copy()
        self.move_count    = state.get("move_count", 0)
        self.current_piece = state.get("current_piece", self.piece_selections[0])
        self._update_legal_moves()
        if self.hint_mode_active:
            self._calculate_hint_degrees()
        else:
            self.hint_degrees = {}

    def _update_legal_moves(self) -> None:
        if not self.player_pos:
            self.legal_moves = []
            return
        cols = self.board_model.cols
        rows = self.board_model.rows
        self.legal_moves = get_legal_moves_for_board(
            self.current_piece, *self.player_pos, cols, rows, self.visited
        )

    def _calculate_hint_degrees(self) -> None:
        if not self.player_pos:
            self.hint_degrees = {}
            return
        next_move_count = self.move_count + 1
        self.hint_degrees = calculate_hint_degrees(
            self.current_piece, self.player_pos,
            self.board_model.cols, self.board_model.rows, self.visited,
            next_piece_func=lambda mx, my: self.ruleset.apply(
                self.current_piece, mx, my, next_move_count
            ),
        )

    def _build_buttons(self) -> None:
        f = self.font
        self.buttons: Dict[str, Button] = {
            "start":        Button(pygame.Rect(0,0,0,0), "start",
                                   f, (255,255,255), (92,192,92),   self.start_game),
            "guide_mode":   Button(pygame.Rect(0,0,0,0), "show move guide",
                                   f, (255,255,255), (128,64,255),  self.toggle_guide_mode),
            "track_mode":   Button(pygame.Rect(0,0,0,0), "show move numbers",
                                   f, (255,255,255), (255,92,128),  self.toggle_track_mode),
            "hint_mode":    Button(pygame.Rect(0,0,0,0), "show degrees",
                                   f, (255,255,255), (255,128,96),  self.toggle_hint_mode),
            "undo_mode":    Button(pygame.Rect(0,0,0,0), "undo last move",
                                   f, (255,255,255), (64,128,255),  self.undo_move),
            "resign":       Button(pygame.Rect(0,0,0,0), "resign",
                                   f, (255,255,255), (107,70,51),   self.resign_game),
            "retry":        Button(pygame.Rect(0,0,0,0), "retry",
                                   f, (255,255,255), (92,192,92),   self.retry_game),
            "replay_mode":  Button(pygame.Rect(0,0,0,0), "start replay",
                                   f, (255,255,255), (64,128,255),  self.toggle_replay_mode),
            "replay_prev":  Button(pygame.Rect(0,0,0,0), "-",
                                   f, (255,255,240), (64,128,255),  lambda: self.navigate_replay(-1)),
            "replay_next":  Button(pygame.Rect(0,0,0,0), "+",
                                   f, (255,255,240), (64,128,255),  lambda: self.navigate_replay(1)),
            "peek_mode":    Button(pygame.Rect(0,0,0,0), "peek",
                                   f, (255,255,240), DK_SQUARE,     self.toggle_peek),
            "reveal_mode":  Button(pygame.Rect(0,0,0,0), "reveal path",
                                   f, (255,255,255), (255,128,96),  self.toggle_reveal_mode),
            "new_game":     Button(pygame.Rect(0,0,0,0), "new game",
                                   f, (255,255,255), (32,128,96),   self.new_game),
            "share_code":   Button(pygame.Rect(0,0,0,0), "copy share code",
                                   f, (255,255,255), (0,128,192),   self.copy_code_to_clipboard),
            "enter_code":   Button(pygame.Rect(0,0,0,0), "enter share code",
                                   f, (255,255,255), (0,128,192),   self.toggle_codec_input),
            "exit":         Button(pygame.Rect(0,0,0,0), "exit",
                                   f, (255,255,255), (220,40,40),   self.quit_game),
        }

    # ================================================================== #
    #  Clock helpers                                                       #
    # ================================================================== #

    def _is_per_move_mode(self) -> bool:
        clock_sel = self.get_selection("clock")
        time_per  = self.get_selection("time per")
        return clock_sel > 0 and time_per == "move"

    def _remaining_time(self) -> Optional[int]:
        clock_sel = self.get_selection("clock")
        if clock_sel == 0:
            return None
        if self._is_per_move_mode():
            if self.move_start_time is None:
                return int(clock_sel)
            return max(0, math.ceil(clock_sel - (time.time() - self.move_start_time)))
        elapsed = (
            self.final_elapsed
            if self.game_state == GameState.ENDGAME
            else self.clock_elapsed
        )
        return max(0, int(clock_sel) - int(elapsed))

    # ================================================================== #
    #  Derived helpers                                                     #
    # ================================================================== #

    def _active_pieces(self) -> List[str]:
        """Return the slice of piece_selections that is actually in use."""
        return self.piece_selections[: self._num_active_pieces()]

    def _has_duplicate_pieces(self) -> bool:
        active = self._active_pieces()
        return len(active) != len(set(active))

    def _piece_cycle_index(self) -> int:
        """Return the index in the cycle for the current step (rule-set 1 only)."""
        if self.ruleset is None:
            return 0
        active = self._active_pieces()
        try:
            return active.index(self.current_piece)
        except ValueError:
            return 0

    def _encode_current_puzzle(self) -> str:
        board_size   = self.get_selection("board")
        ruleset_name = self.get_selection("rule set")
        clock_val    = self.get_selection("clock")
        time_per     = self.get_selection("time per")

        clock_idx  = CLOCK_VALUES.index(clock_val) if clock_val in CLOCK_VALUES else 0
        piece_idxs = [
            TURING_PIECES.index(self.piece_selections[i]) if self.piece_selections[i] in TURING_PIECES else 0
            for i in range(3)
        ]
        seed = self.last_puzzle_seed or 0

        return _encode_puzzle_code(
            board_size, ruleset_name,
            clock_idx, time_per,
            piece_idxs, seed,
        )

    # ================================================================== #
    #  Game actions (overrides / extensions)                              #
    # ================================================================== #

    def toggle_peek(self) -> None:
        """Toggle peek mode (show solution path on board).

        Deactivates hint mode first so the two number overlays do not
        occupy the same board-square position simultaneously.
        """
        self.hint_mode_active = False
        self.hint_degrees = {}
        self.toggle_reveal_mode()

    def toggle_reveal_mode(self) -> None:
        """Toggle reveal mode (show solution path on board)."""
        if self.solution_path and self.game_state in (GameState.INGAME, GameState.ENDGAME):
            self.reveal_mode_active = not self.reveal_mode_active
        else:
            self.reveal_mode_active = False

    def toggle_hint_mode(self) -> None:
        """Toggle Warnsdorff degree hint overlay.

        Deactivates peek (reveal) mode first so the two number overlays
        do not occupy the same board-square position simultaneously.
        """
        self.reveal_mode_active = False
        self.hint_mode_active = not self.hint_mode_active
        if self.hint_mode_active and self.player_pos:
            self._calculate_hint_degrees()
        else:
            self.hint_degrees = {}

    def toggle_guide_mode(self) -> None:
        self.guide_mode_active = not self.guide_mode_active

    def start_game(self, use_seed: Optional[int] = None) -> None:
        """Override: validate duplicate pieces, then start."""
        if self._has_duplicate_pieces():
            self.error_message = "All pieces in the cycle must be different"
            self.error_timer   = pygame.time.get_ticks() + 3000
            return

        board_size = self.get_selection("board")
        min_board  = self._get_min_board_size("")
        if board_size < min_board:
            self.error_message = f"Need board ≥ {min_board} for selected pieces"
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
            seed = random.randint(0, 2 ** 39 - 1)

        self.last_puzzle_seed = seed

        if not self._game_specific_start_setup(seed):
            self.error_message = "No puzzle found – try different pieces or larger board"
            self.error_timer   = pygame.time.get_ticks() + 3000
            return

        n = self.get_selection("board")
        self.board_model.cols = n
        self.board_model.rows = n
        self.board_model.clear()

        # Encode puzzle code now that player_pos is known.
        self.puzzle_code = self._encode_current_puzzle()

        # Always start at the zeroth square of the generated path.
        self.end_state = None
        if self._is_per_move_mode():
            self.clock_start_time = None
            self.move_start_time  = time.time()
        else:
            self.clock_start_time = time.time()
            self.move_start_time  = None
        self.paused_elapsed     = 0.0
        self.clock_elapsed      = 0
        self.final_elapsed      = 0
        self.replay_states      = [self._capture_game_state()]
        self.replay_index       = 0
        self.replay_mode_active = False
        self.reveal_mode_active = False
        self.hint_degrees       = {}
        self.game_state         = GameState.INGAME

    def make_move(self, target_pos: Tuple[int, int]) -> None:
        """Override to also reset per-move clock."""
        if self.game_state != GameState.INGAME:
            return
        if not self._validate_move(target_pos):
            return
        super().make_move(target_pos)
        if self._is_per_move_mode() and self.game_state == GameState.INGAME:
            self.clock_start_time = None
            self.move_start_time  = time.time()

    def new_game(self) -> None:
        super().new_game()
        self.preview_pos          = None
        self.hamiltonian_complete = False
        self.solution_path        = None
        self.ruleset              = None
        self.current_piece        = self.piece_selections[0]
        self.player_pos           = None
        self.visited.clear()
        self.visited_moves.clear()
        self.legal_moves.clear()
        self.move_count     = 0
        self.clock_elapsed  = 0
        self.final_elapsed  = 0
        self.move_start_time = None
        self.reveal_mode_active = False
        self.peek_mode_visible = False
        self.codec_input.set_text("")

    def update(self, dt: int) -> None:
        super().update(dt)
        if self.game_state == GameState.INGAME:
            if self._is_per_move_mode() and self.move_start_time is not None:
                clock_sel = self.get_selection("clock")
                if time.time() - self.move_start_time >= clock_sel:
                    self.final_elapsed = int(time.time() - self.move_start_time)
                    self.end_state     = "timeout"
                    self.game_state    = GameState.ENDGAME

    # ================================================================== #
    #  Rendering                                                           #
    # ================================================================== #

    def _render_game_specific_board(self, screen: pygame.Surface) -> None:
        """Draw board overlays for INGAME / ENDGAME."""
        if self.game_state not in (GameState.INGAME, GameState.ENDGAME):
            return

        cs = self.current_cell_size

        # Choose display state (replay vs live).
        if (self.game_state == GameState.ENDGAME
                and self.replay_mode_active
                and self.replay_states):
            snap = self.replay_states[self.replay_index]
            disp_pos     = snap["pos"]
            disp_visited = snap["visited"]
            disp_vm      = snap["visited_moves"]
            disp_piece   = snap.get("current_piece", self.current_piece)
        else:
            disp_pos     = self.player_pos
            disp_visited = self.visited
            disp_vm      = self.visited_moves
            disp_piece   = self.current_piece

        # ---- Visited squares ----
        nf = pygame.font.SysFont("arial", max(6, cs // 5))
        for vx, vy in disp_visited:
            px, py = self.board_renderer.to_pixel(vx, vy)
            par = (vx + vy) % 2
            vc  = LT_VISITED if par == 0 else DK_VISITED
            pygame.draw.rect(screen, vc, (px + 3, py + 3, cs - 4, cs - 4))
            if self.track_mode_active and (vx, vy) in disp_vm:
                luma = vc[0]*0.299 + vc[1]*0.587 + vc[2]*0.114
                nc   = (0, 0, 0) if luma > 128 else (255, 255, 255)
                ns   = nf.render(str(disp_vm[(vx, vy)]), True, nc)
                screen.blit(ns, ns.get_rect(center=(px + cs//6, py + cs//6)))

        # ---- Last move: draw current position as visited green (Hamiltonian win) ----
        if self.hamiltonian_complete and disp_pos and disp_pos in disp_vm:
            px, py = self.board_renderer.to_pixel(*disp_pos)
            par = (disp_pos[0] + disp_pos[1]) % 2
            vc  = LT_VISITED if par == 0 else DK_VISITED
            pygame.draw.rect(screen, vc, (px + 3, py + 3, cs - 4, cs - 4))
            if self.track_mode_active:
                luma = vc[0]*0.299 + vc[1]*0.587 + vc[2]*0.114
                nc   = (0, 0, 0) if luma > 128 else (255, 255, 255)
                ns   = nf.render(str(disp_vm[disp_pos]), True, nc)
                screen.blit(ns, ns.get_rect(center=(px + cs//6, py + cs//6)))

        # ---- Reveal mode: draw full solution path ----
        if self.reveal_mode_active and self.solution_path:
            rev_font = pygame.font.SysFont("arial", max(6, cs // 5))
            for step_i, (rr, rc, _) in enumerate(self.solution_path):
                px, py = self.board_renderer.to_pixel(rr, rc)
                ns = rev_font.render(str(step_i), True, (180, 80, 0))
                screen.blit(ns, ns.get_rect(center=(px + cs - cs // 6, py + cs // 6)))

        # ---- Guide arrows ----
        if self.guide_mode_active and self.arrows and disp_pos:
            if self.replay_mode_active and self.game_state == GameState.ENDGAME:
                lm = get_legal_moves_for_board(
                    disp_piece, *disp_pos,
                    self.board_model.cols, self.board_model.rows, disp_visited,
                )
            else:
                lm = self.legal_moves
            self._draw_arrows(screen, lm, disp_pos)

        # ---- Start square highlight ----
        if disp_visited:
            start_sq = min(disp_vm, key=lambda k: disp_vm[k]) if disp_vm else None
            if start_sq:
                sx, sy = self.board_renderer.to_pixel(*start_sq)
#                pygame.draw.rect(screen, START_SQ_COLOR,
#                                 (sx + 1, sy + 1, cs - 2, cs - 2), 3)

        # ---- Player token (not drawn when Hamiltonian path is complete) ----
        if disp_pos: #and not self.hamiltonian_complete:
            ppx, ppy = self.board_renderer.to_pixel(*disp_pos)
            pr = pygame.Rect(ppx + 1, ppy + 1, cs - 2, cs - 2)
            try:
                pk.draw_piece(screen, pr, disp_piece)
            except Exception:
                pygame.draw.ellipse(screen, (30, 30, 120), pr)
            # Active piece label below token
            lbl = pygame.font.SysFont("arial", max(7, cs // 5))
            ls  = lbl.render(disp_piece[:4], True, ACTIVE_PIECE_COLOR)
#            screen.blit(ls, ls.get_rect(centerx=ppx + cs//2, top=ppy + cs - max(8, cs//5)))

        # ---- Hint degrees (drawn on top of all squares and token) ----
        if self.hint_mode_active and self.hint_degrees:
            hnf = pygame.font.SysFont("arial", max(6, cs // 5))
            for (hx, hy), deg in self.hint_degrees.items():
                px, py = self.board_renderer.to_pixel(hx, hy)
                hs = hnf.render(str(deg), True, (107, 50, 71))
                screen.blit(hs, hs.get_rect(center=(px + cs - cs//6, py + cs//6)))

    def _render_game_specific_stats(
        self, screen: pygame.Surface, stats_panel: UIPanel
    ) -> None:
        """Render stats: progress, current piece, clock, endgame message."""
        bounds      = stats_panel.get_bounds("STATS_PANEL")
        line_height = self.font.get_linesize() + UI_SPACE

        board_size    = self.get_selection("board")
        total_squares = board_size * board_size

        # Snapshot for replay
        if (self.game_state == GameState.ENDGAME
                and self.replay_mode_active
                and self.replay_states):
            snap     = self.replay_states[self.replay_index]
            disp_vis = snap["visited"]
            disp_pc  = snap.get("current_piece", self.current_piece)
        else:
            disp_vis = self.visited
            disp_pc  = self.current_piece

        cx = bounds["center_x"]

        # Line 0: progress
        if self.game_state != GameState.MENU:
            y0 = stats_panel.get_line_y("STATS_PANEL", 0, line_height)
            prog = self.font.render(
                f"move {len(disp_vis) - 1} of {total_squares - 1}", True, (0, 0, 0))
            screen.blit(prog, prog.get_rect(centerx=cx, top=y0))

        # Line 1: active piece
        y1 = stats_panel.get_line_y("STATS_PANEL", 1, line_height)
        ap = self.font.render(f"active: {disp_pc}", True, ACTIVE_PIECE_COLOR)
        #screen.blit(ap, ap.get_rect(centerx=cx, top=y1))

        # Clock
        if self.game_state != GameState.MENU:
            remaining = self._remaining_time()
            if remaining is not None:
                clock_disp  = _format_clock_seconds(remaining)
                clock_color = (200, 0, 0) if remaining < 30 else (0, 0, 0)
            else:
                clock_disp  = _format_clock_seconds(self.clock_elapsed)
                clock_color = (0, 0, 0)
            cy = stats_panel.get_line_y("STATS_PANEL", 9, line_height)
            cs = self.font.render(clock_disp, True, clock_color)
            screen.blit(cs, cs.get_rect(centerx=cx, top=cy))

        # Endgame message
        if self.game_state == GameState.ENDGAME and self.end_state:
            if self.end_state == "hamiltonian_complete":
                msg, mc = "Hamiltonian path complete!", (34, 177, 76)
            else:
                msg, mc = {
                    "no_moves":   ("no legal moves",  (192, 0, 0)),
                    "resignation": ("resigned",         (107, 70, 51)),
                    "timeout":    ("time's up",        (0, 0, 0)),
                }.get(self.end_state, ("game over", (0, 0, 0)))
            em = self.font_large.render(msg, True, mc)
            ey = stats_panel.get_line_y("STATS_PANEL", 5, line_height)
            screen.blit(em, em.get_rect(centerx=cx, top=ey))

    def _draw_peek_thumbnail(
        self, screen: pygame.Surface, left_panel: UIPanel, line_height: int
    ) -> None:
        """Peek-mode: draw solution path as a small thumbnail in BUTTON_PANEL."""
        if not (self.peek_mode_visible and self.solution_path):
            return
        cols = self.board_model.cols
        rows = self.board_model.rows
        if cols < 1 or rows < 1:
            return

        bb = left_panel.get_bounds("BUTTON_PANEL")
        thumb_y  = left_panel.get_line_y("BUTTON_PANEL", 0, line_height)
        thumb    = pygame.Rect(
            bb["left"] + UI_SPACE, thumb_y,
            bb["width"] - UI_SPACE * 2,
            bb["bottom"] - thumb_y - UI_SPACE * 4,
        )

        mc = min(
            thumb.width  // cols if cols else 1,
            thumb.height // rows if rows else 1,
        )
        if mc < 2:
            return

        tw = cols * mc
        th = rows * mc
        tx = thumb.left + (thumb.width  - tw) // 2
        ty = thumb.top  + (thumb.height - th) // 2

        for gy in range(rows):
            for gx in range(cols):
                color = LT_SQUARE if (gx + gy) % 2 == 0 else DK_SQUARE
                pygame.draw.rect(screen, color,
                                 (tx + gx * mc, ty + gy * mc, mc, mc))

        nf = pygame.font.SysFont("arial", 16) #max(6, mc - 2))
        for idx, (rr, rc, _) in enumerate(self.solution_path):
            ns = nf.render(str(idx), True, (0, 0, 0))
            screen.blit(ns, ns.get_rect(center=(
                tx + rc * mc + mc // 2,
                ty + rr * mc + mc // 2,
            )))

        pygame.draw.rect(screen, GRID_COLOR, (tx-1, ty-1, tw+2, th+2), 1)

    def _render_menu_preview(self, screen: pygame.Surface) -> None:
        """Menu board: show first selected piece's moves from preview position."""
        cs         = self.current_cell_size
        prev_board = self.get_selection("board")
        piece_name = self.piece_selections[0]

        if (self.board_model.cols != prev_board
                or self.board_model.rows != prev_board):
            self.board_model.cols = prev_board
            self.board_model.rows = prev_board
            self.board_model.clear()
            self.preview_pos = None

        if (self.preview_pos is None
                or not (0 <= self.preview_pos[0] < prev_board
                        and 0 <= self.preview_pos[1] < prev_board)):
            self.preview_pos = (prev_board // 2, prev_board // 2)

        prev_legal = get_legal_moves_for_board(
            piece_name, *self.preview_pos, prev_board, prev_board, set()
        )

        ppx, ppy = self.board_renderer.to_pixel(*self.preview_pos)
        pr = pygame.Rect(ppx + 1, ppy + 1, cs - 2, cs - 2)
        try:
            pk.draw_piece(screen, pr, piece_name)
        except Exception:
            pygame.draw.ellipse(screen, (0, 0, 0), pr)

        if self.guide_mode_active and self.arrows:
            self._draw_arrows(screen, prev_legal, self.preview_pos)

    # ------------------------------------------------------------------ #
    #  Left panel (menu + buttons)                                         #
    # ------------------------------------------------------------------ #

    def _render_left_panel(
        self,
        screen: pygame.Surface,
        left_panel: UIPanel,
        msg_left: int,
        msg_right: int,
        msg_bottom: int,
    ) -> None:
        btn_w      = int(UI_SPACE * 1.5)
        line_height = self.font.get_linesize() + UI_SPACE

        # ---- MENU_PANEL: selector rows ----
        menu_bounds = left_panel.get_bounds("MENU_PANEL")
        text_x      = menu_bounds["left"] + UI_SPACE

        max_lbl_w = max(
            (self.font.render(lbl + ":", True, (0, 0, 0)).get_width()
             for lbl, _, _ in self.menu_items),
            default=60,
        )
        minus_x = text_x + max_lbl_w + UI_SPACE
        plus_x  = menu_bounds["right"] - UI_SPACE * 4

        for list_idx, (item_idx, (label, values, cur_idx)) in enumerate(
            (i, t) for i, t in enumerate(self.menu_items)
        ):
            panel_y = left_panel.get_line_y("MENU_PANEL", list_idx, line_height)
            row_cy  = panel_y + btn_w // 2
            lbl_s   = self.font.render(f"{label}", True, (0, 0, 0))
            screen.blit(lbl_s, lbl_s.get_rect(midleft=(text_x, row_cy)))

            val      = values[cur_idx]
            sel_text = _display_for_selection(val) if label == "clock" else str(val)
            sel_s    = self.font.render(sel_text, True, (0, 0, 0))
            sel_cx   = (minus_x + btn_w + plus_x) / 2
            screen.blit(sel_s, sel_s.get_rect(center=(sel_cx, row_cy)))

            if self.game_state == GameState.MENU:
                mr = pygame.Rect(minus_x, panel_y, btn_w, btn_w)
                pygame.draw.rect(screen, DK_SQUARE, mr)
                lt = self.font.render("<", True, (0, 160, 0))
                screen.blit(lt, lt.get_rect(center=mr.center))
                self.widget_rects[("minus", item_idx)] = mr

                pr = pygame.Rect(plus_x, panel_y, btn_w, btn_w)
                pygame.draw.rect(screen, DK_SQUARE, pr)
                gt = self.font.render(">", True, (220, 0, 0))
                screen.blit(gt, gt.get_rect(center=pr.center))
                self.widget_rects[("plus", item_idx)] = pr

        # ---- Codec text input (below menu items, MENU state) ----
        if self.seed_mode_active and self.game_state == GameState.MENU:
            ci_y = left_panel.get_line_y("MENU_PANEL", len(self.menu_items) + 1, line_height)
            self.codec_input.rect = pygame.Rect(
                menu_bounds["left"] + UI_SPACE, ci_y,
                menu_bounds["width"] - UI_SPACE * 2, BTH,
            )
            self.codec_input.draw(screen)

        # ---- BUTTON_PANEL ----
        has_dups   = self._has_duplicate_pieces()
        board_size = self.get_selection("board")
        min_b      = self._get_min_board_size("")
        is_playable = board_size >= min_b and not has_dups

        # Start (MENU only) - slot 0
        if self.seed_mode_active:
            self.buttons["start"].active = (
                self.game_state == GameState.MENU
                and self._is_valid_codec_length()
            )
        else:
            self.buttons["start"].active = (
                self.game_state == GameState.MENU and is_playable
            )
        self.buttons["start"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        if self.buttons["start"].active:
            self.buttons["start"].draw(screen)

        # Hint mode (INGAME / ENDGAME) - slot 0 (shared with start)
        self.buttons["hint_mode"].active = self.game_state == GameState.INGAME
        self.buttons["hint_mode"].text = (
            "hide degrees" if self.hint_mode_active else "show degrees"
        )
        self.buttons["hint_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        if self.buttons["hint_mode"].active:
            self.buttons["hint_mode"].draw(screen)

        # Guide mode (all states) - slot 2
        self.buttons["guide_mode"].active = True
        self.buttons["guide_mode"].text   = (
            "hide move guide" if self.guide_mode_active else "show move guide"
        )
        self.buttons["guide_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 2, BTW, BTH)
        self.buttons["guide_mode"].draw(screen)

        # Track mode (all states) - slot 4
        self.buttons["track_mode"].active = True
        self.buttons["track_mode"].text   = (
            "hide move #'s" if self.track_mode_active else "show move #'s"
        )
        self.buttons["track_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 4, BTW, BTH)
        self.buttons["track_mode"].draw(screen)

        # Enter code toggle (MENU only) - slot 6
#        self.buttons["enter_code"].active = self.game_state == GameState.MENU
#        self.buttons["enter_code"].text   = (
#            "cancel share code" if self.seed_mode_active else "enter share code"
#        )
#        self.buttons["enter_code"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 6, BTW, BTH)
#        if self.buttons["enter_code"].active:
#            self.buttons["enter_code"].draw(screen)

        # Undo (INGAME, history exists) - slot 6
        self.buttons["undo_mode"].active = (
            self.game_state == GameState.INGAME
            and len(self.replay_states) > 1
        )
        self.buttons["undo_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 6, BTW, BTH)
        if self.buttons["undo_mode"].active:
            self.buttons["undo_mode"].draw(screen)

        # Resign (INGAME) - slot 8
        self.buttons["resign"].active = self.game_state == GameState.INGAME
        self.buttons["resign"].rect   = left_panel.get_widget_rect("BUTTON_PANEL", 8, BTW, BTH)
        if self.buttons["resign"].active:
            self.buttons["resign"].draw(screen)

        # Peek (INGAME / ENDGAME, solution exists) - same vertical row as exit
        self.buttons["peek_mode"].active = (
            self.game_state in (GameState.INGAME, GameState.ENDGAME)
            and bool(self.solution_path)
        )
        self.buttons["peek_mode"].text = "hide" if self.reveal_mode_active else "peek"
        self.buttons["peek_mode"].rect = pygame.Rect(
            msg_left + UI_SPACE * 3,
            msg_bottom - int(UI_SPACE * 5),
            BTW / 3, BTH * 0.75,
        )
        if self.buttons["peek_mode"].active:
            self.buttons["peek_mode"].draw(screen)

        # Reveal (INGAME / ENDGAME, solution exists) - slot 12
        self.buttons["reveal_mode"].active = (
            self.game_state == GameState.ENDGAME
            and bool(self.solution_path)
        )
        self.buttons["reveal_mode"].text = (
            "hide path" if self.reveal_mode_active else "show path"
        )
        self.buttons["reveal_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        if self.buttons["reveal_mode"].active:
            self.buttons["reveal_mode"].draw(screen)

        # ---- ENDGAME buttons ----
        # Retry (ENDGAME) - MENU_PANEL slot 7
        self.buttons["retry"].active = (
            self.game_state == GameState.ENDGAME
            and self.last_puzzle_seed is not None
        )
        self.buttons["retry"].rect = left_panel.get_widget_rect("MENU_PANEL", 7, BTW, BTH)
        if self.buttons["retry"].active:
            self.buttons["retry"].draw(screen)

        # Replay (ENDGAME) - slot 6
        self.buttons["replay_mode"].active = self.game_state == GameState.ENDGAME
        self.buttons["replay_mode"].text   = (
            "end replay" if self.replay_mode_active else "start replay"
        )
        self.buttons["replay_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 6, BTW, BTH)
        if self.buttons["replay_mode"].active:
            self.buttons["replay_mode"].draw(screen)

        # Replay navigation
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

        # New game (ENDGAME) - slot 8
        self.buttons["new_game"].active = self.game_state == GameState.ENDGAME
        self.buttons["new_game"].rect   = left_panel.get_widget_rect("BUTTON_PANEL", 8, BTW, BTH)
        if self.buttons["new_game"].active:
            self.buttons["new_game"].draw(screen)

        # Share code (ENDGAME) - slot 14
        self.buttons["share_code"].active = (
            self.game_state == GameState.ENDGAME and bool(self.puzzle_code)
        )
        self.buttons["share_code"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 14, BTW, BTH)
        if self.buttons["share_code"].active:
            self.buttons["share_code"].draw(screen)

        # Show peek thumbnail in BUTTON_PANEL if active
        if self.peek_mode_visible and self.solution_path:
            self._draw_peek_thumbnail(screen, left_panel, line_height)

        # Duplicate-piece warning
        if has_dups and self.game_state == GameState.MENU:
            wy  = left_panel.get_line_y("BUTTON_PANEL", 1, line_height)
            ws  = self.font.render("pieces must be unique", True, WARN_COLOR)
            screen.blit(ws, ws.get_rect(
                centerx=menu_bounds["center_x"], top=wy))

        # Exit (always)
        self.buttons["exit"].rect = pygame.Rect(
            msg_right - UI_SPACE * 8,
            msg_bottom - int(UI_SPACE * 5),
            BTW // 3, int(BTH * 0.75),
        )
        self.buttons["exit"].draw(screen)

    # ------------------------------------------------------------------ #
    #  Right panel (piece selectors + stats)                              #
    # ------------------------------------------------------------------ #

    def _render_right_panel(self, screen: pygame.Surface, right_panel: UIPanel) -> None:
        """Render N piece selectors in PIECE_PANEL and stats in STATS_PANEL."""
        line_height  = self.font.get_linesize() + UI_SPACE
        piece_bounds = right_panel.get_bounds("PIECE_PANEL")

        num_pieces   = self._num_active_pieces()
        panel_h      = piece_bounds["height"]
        ruleset_name = self.get_selection("rule set")
        is_flip_flop = (ruleset_name == "4-cycle") and (num_pieces == 3)

        btn_sz = int(UI_SPACE * 1.5)
        pl     = piece_bounds["left"]
        pt     = piece_bounds["top"]
        pw     = piece_bounds["width"]

        # Build per-slot rects.
        # For flip-flop: piece 0 on top (full width), pieces 1+2 side-by-side below.
        # For all other rule sets: equal-height stacked slots.
        if is_flip_flop:
            top_h  = (panel_h - 20) // 2
            bot_h  = panel_h - top_h - 20
            half_w = pw // 2
            slot_rects = [
                pygame.Rect(pl,             pt + 20,          pw,      top_h),
                pygame.Rect(pl,             pt + 20 + top_h,  half_w,  bot_h),
                pygame.Rect(pl + half_w,    pt + 20 + top_h,  pw - half_w, bot_h),
            ]
        else:
            slot_h = max(1, panel_h // num_pieces - 5)
            slot_rects = [
                pygame.Rect(pl, pt + i * slot_h + 20, pw, slot_h)
                for i in range(num_pieces)
            ]

        for i in range(num_pieces):
            sr   = slot_rects[i]
            name = self.piece_selections[i]

            # Highlight if this is the active piece during gameplay
            is_active = (
                self.game_state in (GameState.INGAME, GameState.ENDGAME)
                and name == self.current_piece
            )

            # Background tint for active slot
            if is_active:
                tint = pygame.Rect(sr.left + 2, sr.top + 1, sr.width - 4, sr.height - 2)
                pygame.draw.rect(screen, (200, 240, 200), tint)

            # Piece name
            name_color = ACTIVE_PIECE_COLOR if is_active else (0, 0, 0)
            name_font  = self.font_large if is_active else self.font
            ns         = name_font.render(name, True, name_color)
            screen.blit(ns, ns.get_rect(centerx=sr.centerx, top=sr.top + 2))

            # Move-set text
            ms_text = pk.get_piece_move_sets_text(name)
            mst_col = (60, 100, 60) if is_active else (80, 80, 80)
            mst_s   = self.font.render(ms_text, True, mst_col)
            screen.blit(mst_s, mst_s.get_rect(
                centerx=sr.centerx, top=sr.top + ns.get_height() + 4,
            ))

            # Arrow buttons (MENU state only)
            if self.game_state == GameState.MENU:
                btn_y = sr.top + 2
                mm_r  = pygame.Rect(sr.left + UI_SPACE, btn_y, btn_sz, btn_sz)
                pygame.draw.rect(screen, DK_SQUARE, mm_r)
                lt = self.font.render("<", True, (0, 160, 0))
                screen.blit(lt, lt.get_rect(center=mm_r.center))
                self.widget_rects[("piece_minus", i)] = mm_r

                pm_r = pygame.Rect(sr.right - UI_SPACE - btn_sz, btn_y, btn_sz, btn_sz)
                pygame.draw.rect(screen, DK_SQUARE, pm_r)
                gt = self.font.render(">", True, (220, 0, 0))
                screen.blit(gt, gt.get_rect(center=pm_r.center))
                self.widget_rects[("piece_plus", i)] = pm_r

            # Separator between slots
            if i < num_pieces - 1:
                if is_flip_flop and i == 1:
                    # vertical separator between pieces 1 and 2 (side-by-side)
                    vx = sr.right
                    pygame.draw.line(
                        screen, GRID_COLOR,
                        (vx, sr.top + 4), (vx, sr.bottom - 4), 1,
                    )
                else:
                    # horizontal separator below this slot
                    sep_y = sr.bottom - 1
                    pygame.draw.line(
                        screen, GRID_COLOR,
                        (sr.left + 4, sep_y), (sr.right - 4, sep_y), 1,
                    )

        # ---- STATS_PANEL ----
        self._render_game_specific_stats(screen, right_panel)

    # ------------------------------------------------------------------ #
    #  Main render                                                         #
    # ------------------------------------------------------------------ #

    def render(self, screen: pygame.Surface) -> None:
        win_w, win_h = screen.get_size()
        screen.fill(BACK_COLOR)

        margin      = UI_SPACE
        panel_width = UI_SPACE * 28
        msg_left    = margin
        msg_top     = margin
        msg_bottom  = win_h - margin
        msg_right   = msg_left + panel_width
        right_left  = win_w - panel_width - margin

        lp_rect = pygame.Rect(msg_left,   msg_top, panel_width, msg_bottom - msg_top)
        rp_rect = pygame.Rect(right_left, msg_top, panel_width, msg_bottom - msg_top)

        left_panel  = UIPanel(lp_rect, gap=0)
        right_panel = UIPanel(rp_rect, gap=0)

        left_panel.draw_panel(screen,  "MENU_PANEL",   LT_SQUARE, GRID_COLOR)
        left_panel.draw_panel(screen,  "BUTTON_PANEL", LT_SQUARE, GRID_COLOR)
        right_panel.draw_panel(screen, "PIECE_PANEL",  LT_SQUARE, GRID_COLOR)
        right_panel.draw_panel(screen, "STATS_PANEL",  LT_SQUARE, GRID_COLOR)

        area_left   = msg_right + margin
        area_top    = margin
        area_right  = right_left - margin
        area_bottom = win_h - margin

        # Sync board model in MENU
        if self.game_state == GameState.MENU:
            brd = self.get_selection("board")
            if self.board_model.cols != brd or self.board_model.rows != brd:
                self.board_model.cols = brd
                self.board_model.rows = brd
                self.board_model.clear()

        self._update_cell_size(area_left, area_top,
                               area_right - area_left, area_bottom - area_top)

        self.board_renderer.draw_background(screen)
        self.widget_rects.clear()

        cs = self.current_cell_size
        if cs > 0:
            if self.game_state == GameState.MENU:
                self._render_menu_preview(screen)
            elif self.game_state in (GameState.INGAME, GameState.ENDGAME):
                self._render_game_specific_board(screen)

        self.board_renderer.draw_grid_lines(screen)

        # Error overlay
        if self.error_message and pygame.time.get_ticks() < self.error_timer:
            ef = pygame.font.SysFont("arial", 18)
            es = ef.render(self.error_message, True, (200, 0, 0))
            aw = area_right - area_left
            ah = area_bottom - area_top
            ex = area_left + (aw - es.get_width()) // 2
            ey = area_top  + (ah - es.get_height()) // 2
            pygame.draw.rect(screen, (255, 240, 240),
                             (ex-8, ey-6, es.get_width()+16, es.get_height()+12))
            screen.blit(es, (ex, ey))
        elif self.error_message and pygame.time.get_ticks() >= self.error_timer:
            self.error_message = ""

        self._render_left_panel(screen, left_panel, msg_left, msg_right, msg_bottom)
        self._render_right_panel(screen, right_panel)

    # ------------------------------------------------------------------ #
    #  Event handling                                                      #
    # ------------------------------------------------------------------ #

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not super().handle_event(event):
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_h and self.game_state == GameState.INGAME:
                self.toggle_hint_mode()
            elif event.key == pygame.K_r and self.game_state in (
                GameState.INGAME, GameState.ENDGAME
            ):
                self.toggle_reveal_mode()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            for key, rect in list(self.widget_rects.items()):
                if rect.collidepoint(mx, my):
                    kind = key[0]

                    if kind in ("minus", "plus"):
                        # Standard menu item navigation
                        _, item_idx = key
                        lbl, vals, cur = self.menu_items[item_idx]
                        if kind == "plus":
                            self.menu_items[item_idx] = (lbl, vals, (cur + 1) % len(vals))
                        else:
                            self.menu_items[item_idx] = (lbl, vals, (cur - 1) % len(vals))
                        if lbl == "board":
                            nb = self.menu_items[item_idx][1][self.menu_items[item_idx][2]]
                            self.board_model.cols = nb
                            self.board_model.rows = nb
                            self.board_model.clear()
                            self.preview_pos = None

                    elif kind == "piece_minus":
                        slot_i = key[1]
                        ci     = TURING_PIECES.index(self.piece_selections[slot_i]) \
                                 if self.piece_selections[slot_i] in TURING_PIECES else 0
                        self.piece_selections[slot_i] = TURING_PIECES[(ci - 1) % len(TURING_PIECES)]

                    elif kind == "piece_plus":
                        slot_i = key[1]
                        ci     = TURING_PIECES.index(self.piece_selections[slot_i]) \
                                 if self.piece_selections[slot_i] in TURING_PIECES else 0
                        self.piece_selections[slot_i] = TURING_PIECES[(ci + 1) % len(TURING_PIECES)]

                    break  # only one widget per click

            # Board clicks
            if self.game_state == GameState.INGAME:
                grid_pos = self.board_renderer.to_grid(mx, my)
                if grid_pos is not None:
                    self.make_move(grid_pos)

            elif self.game_state == GameState.MENU:
                grid_pos = self.board_renderer.to_grid(mx, my)
                if grid_pos is not None:
                    self.preview_pos = grid_pos

        return True

    def _get_visible_button_names(self) -> List[str]:
        if self.game_state == GameState.MENU:
            return ["start", "guide_mode", "track_mode", "enter_code", "exit"]
        elif self.game_state == GameState.INGAME:
            return ["hint_mode", "guide_mode", "track_mode", "undo_mode",
                    "resign", "peek_mode", "reveal_mode"]
        elif self.game_state == GameState.ENDGAME:
            base = ["hint_mode", "guide_mode", "track_mode",
                    "replay_mode", "new_game", "peek_mode", "reveal_mode",
                    "share_code", "retry", "exit"]
            if self.replay_mode_active:
                base = ["replay_prev", "replay_next"] + base
            return base
        return []