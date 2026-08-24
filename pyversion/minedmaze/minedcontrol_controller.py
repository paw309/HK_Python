"""
minedcontrol_controller.py

Game controller for Mined Control – a two-player competitive version of the
single-player Mined Maze.  Both players share the same generated maze and race
to reach the target square first.

Uses minedmaze_controller.py as its structural template and borrows two-player
patterns from knightstrap_controller.py.
"""

import os
import sys
import time
import math
import random

import pygame
from typing import Optional, List, Tuple, Set, Dict, Any

# Add sharedlib/parent/game-dir to path when run directly
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_DIR  = os.path.dirname(os.path.abspath(__file__))
SHAREDLIB = os.path.join(BASE_DIR, "sharedlib")
for _p in (BASE_DIR, SHAREDLIB, GAME_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import piecekeeper as pk
from gameboard import BoardModel, BoardRenderer
from uipanel import UIPanel
from puzzle_codec import encode_params, decode_params
from widgets import Button
from common_utils import format_time as _format_time
from base_game_controller import BaseGameController, GameState

from pyversion.minedmaze.maze_generator import (
    generate_maze_path_and_obstacles,
    adaptive_path_lengths,
    _make_rng,
)
from pyversion.minedmaze.minedcontrol_bot import BotLevel, make_bot_move

# ------------------------------------------------------------------ #
#  Module-level constants                                             #
# ------------------------------------------------------------------ #

BOARD_MIN     = 5
BOARD_MAX     = 16
BOARD_DEFAULT = 8
FPS           = 60
UI_SPACE      = 10
BTW           = int(UI_SPACE * 15)
BTH           = int(UI_SPACE * 3)

PATH_LENGTH_CHOICES  = ["short", "long"]
DENSITY_CHOICES      = ["sparse", "dense", "random"]
CLOCK_MODES          = ["game", "move"]
OPPONENT_LEVEL_CHOICES = ["1", "2", "3", "4", "5"]
PLAYER_ONE_CHOICES   = ["human", "bot"]

# Colors – board
LT_SQUARE  = (255, 255, 240)
DK_SQUARE  = (232, 200, 150)
GRID_COLOR = (107, 70,  51)
BACK_COLOR = (244, 228, 195)

# Colors – maze path
LT_MOVE = (192, 128, 255) #(148, 220, 248)
DK_MOVE = (160, 96, 255)

# Colors – player 1 (blue)
P1_LT_VISITED = (192, 220, 248)
P1_DK_VISITED = (128, 160, 225)

# Colors – player 2 (red)
P2_LT_VISITED = (255, 192, 192)
P2_DK_VISITED = (255, 128, 128)

# Bot move delay
BOT_MOVE_DELAY_MIN = 500
BOT_MOVE_DELAY_MAX = 800

# Minimum board sizes per piece (same as single-player maze)
PIECE_MIN_BOARD_SIZE = {
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

# Puzzle-code schema — encodes maze-determining parameters only.
# Clock and player_one are player preferences and do not affect the generated maze.
minedmaze2_schema = [
    ("board",   4, lambda v: int(v) - BOARD_MIN),
    ("length",  1, {"short": 0, "long": 1}),
    ("density", 2, {"sparse": 0, "dense": 1, "random": 2}),
    ("blocks",  1, {"show": 0, "hide": 1}),
    ("bounce",  1, {"stay": 0, "bounce": 1}),
]

__all__ = [
    "MinedMaze2Controller", "GameState",
    "BOARD_MIN", "BOARD_MAX", "BOARD_DEFAULT", "FPS",
    "PATH_LENGTH_CHOICES", "DENSITY_CHOICES", "CLOCK_MODES",
    "OPPONENT_LEVEL_CHOICES", "PLAYER_ONE_CHOICES",
    "minedmaze2_schema",
]


def _display_clock(clock_selected) -> str:
    if clock_selected == 0:
        return "infinity"
    secs = int(clock_selected)
    return f"{secs // 60}:{secs % 60:02d}"


def get_globally_valid_pieces() -> List[str]:
    """All pieces valid on at least a 5×5 board (no excluded pieces for maze)."""
    return pk.PIECE_LIST[:]


# ------------------------------------------------------------------ #
#  MinedMaze2Controller                                               #
# ------------------------------------------------------------------ #

class MinedMaze2Controller(BaseGameController):
    """
    Two-player competitive Mined Maze controller.

    Both players share the same generated maze (odd-length path).
    Player 1 (Blue) starts at path[0] and counts up toward the middle square.
    Player 2 (Red) starts at path[-1] and counts down toward the middle square.
    The first to reach path[mid] wins.  Mines behave per the 'bounce' setting:
    stay keeps the player in place, bounce resets them to their own start square.
    """

    # Override visited-square colours (player-specific rendering below)
    VISITED_LT = P1_LT_VISITED
    VISITED_DK = P1_DK_VISITED

    def __init__(
        self,
        board_model:    BoardModel,
        board_renderer: BoardRenderer,
        menu_items:     list,
        label_to_index: dict,
        font:           pygame.font.Font,
        font_large:     pygame.font.Font,
        base_dir:       str,
    ) -> None:
        super().__init__(
            board_model, board_renderer, menu_items, label_to_index,
            font, font_large, base_dir, minedmaze2_schema,
        )

        # Load maze marker images
        markers_dir = os.path.join(base_dir, "assets", "markers")
        self.target_img     = pygame.image.load(
            os.path.join(markers_dir, "target.png")).convert_alpha()
        self.mine_blue_img  = pygame.image.load(
            os.path.join(markers_dir, "mine_blue.png")).convert_alpha()
        self.mine_red_img   = pygame.image.load(
            os.path.join(markers_dir, "mine_red.png")).convert_alpha()

        # ---- Shared maze state ----
        self.maze_path:     Optional[List[Tuple[int, int]]] = None
        self.maze_path_set: Set[Tuple[int, int]]            = set()
        self.maze_target:   Optional[Tuple[int, int]]       = None  # middle square
        self.maze_mid_idx:  int                             = 0
        self.obstacles:     Set[Tuple[int, int]]            = set()
        self.path_index:    Dict[Tuple[int, int], int]      = {}

        # ---- Two-player state ----
        self.player1_pos:           Optional[Tuple[int, int]] = None
        self.player2_pos:           Optional[Tuple[int, int]] = None
        self.player1_start:         Optional[Tuple[int, int]] = None
        self.player2_start:         Optional[Tuple[int, int]] = None
        self.player1_visited:       Set[Tuple[int, int]]      = set()
        self.player2_visited:       Set[Tuple[int, int]]      = set()
        self.player1_visited_moves: Dict[Tuple[int, int], int] = {}
        self.player2_visited_moves: Dict[Tuple[int, int], int] = {}
        self.player1_legal_moves:   List[Tuple[int, int]]    = []
        self.player2_legal_moves:   List[Tuple[int, int]]    = []
        self.player1_known_mines:   Set[Tuple[int, int]]     = set()
        self.player2_known_mines:   Set[Tuple[int, int]]     = set()
        # flash lists: [(square, timestamp)]
        self.player1_flash_list: List[Tuple[Tuple[int, int], float]] = []
        self.player2_flash_list: List[Tuple[Tuple[int, int], float]] = []
        # permanent mine markers (show mode)
        self.player1_perm_mines: Set[Tuple[int, int]] = set()
        self.player2_perm_mines: Set[Tuple[int, int]] = set()
        self.player1_attempt_count: int = 0
        self.player2_attempt_count: int = 0
        self.current_player: int = 1  # 1 or 2

        # ---- Bot state ----
        self.bot_move_pending: bool = False
        self.bot_move_timer:   int  = 0
        self.bot_offers_resignation: bool = False

        # ---- Preview ----
        self.menu_preview_cache = None
        self.menu_preview_pos:  Optional[Tuple[int, int]] = None

        # ---- Per-move clock tracking ----
        self.move_start_time: Optional[float] = None

    # ================================================================== #
    #  Abstract method implementations                                    #
    # ================================================================== #

    def _get_min_board_size(self, piece_name: str) -> int:
        return PIECE_MIN_BOARD_SIZE.get(piece_name, 5)

    def _get_encode_params(self) -> Dict[str, Any]:
        return {
            "board":   self.get_selection("board"),
            "length":  self.get_selection("length"),
            "density": self.get_selection("density"),
            "blocks":  self.get_selection("blocks"),
            "bounce":  self.get_selection("bounce"),
        }

    def _validate_codec(self, codec_text: str) -> Tuple[bool, Optional[Dict]]:
        try:
            params    = decode_params(codec_text, minedmaze2_schema)
            board_val = params.get("board", 0) + BOARD_MIN
            if not (BOARD_MIN <= board_val <= BOARD_MAX):
                return False, None
            if params.get("length")  not in PATH_LENGTH_CHOICES: return False, None
            if params.get("density") not in DENSITY_CHOICES:     return False, None
            if params.get("blocks")  not in ("show", "hide"):    return False, None
            if params.get("bounce")  not in ("stay", "bounce"):  return False, None

            def _apply(label, value):
                idx = self.label_to_index[label]
                lbl, vals, _ = self.menu_items[idx]
                if value in vals:
                    self.menu_items[idx] = (lbl, vals, vals.index(value))

            _apply("board",   board_val)
            _apply("length",  params["length"])
            _apply("density", params["density"])
            _apply("blocks",  params["blocks"])
            _apply("bounce",  params["bounce"])
            return True, {**params, "board": board_val}
        except Exception:
            return False, None

    def _game_specific_start_setup(self, seed: Optional[int] = None) -> bool:
        """Generate the shared maze and place players at fixed start positions."""
        board_size   = self.get_selection("board")
        piece        = self.get_selection("piece")
        path_length  = self.get_selection("length")
        density      = self.get_selection("density")

        n         = board_size
        move_func = pk.get_move_func(piece)
        rng       = _make_rng(seed)

        min_len, max_len = adaptive_path_lengths(n, move_func, path_length, rng=rng)

        path, obs = generate_maze_path_and_obstacles(
            n, min_len, max_len, move_func,
            max_attempts=200, time_budget=1.0, rng=rng, density=density)

        if not path or obs is None:
            return False

        # Force path length to be ODD so there is an exact middle square.
        if len(path) % 2 == 0:
            path = path[:-1]

        if len(path) < 3:
            return False

        self.maze_path     = path
        self.maze_path_set = set(path)
        self.obstacles     = set(obs)
        self.path_index    = {sq: i for i, sq in enumerate(path)}

        # Target is the exact middle of the (odd-length) path.
        self.maze_mid_idx = len(path) // 2
        self.maze_target  = path[self.maze_mid_idx]

        self._clear_two_player_state()
        self.current_player = 1

        # P1 (Blue) always starts at path[0], P2 (Red) at path[-1].
        self._place_player(1, path[0])
        self._place_player(2, path[-1])

        self._update_all_legal_moves()
        self._sync_base_state()
        return True

    def _game_specific_make_move(self, target: Tuple[int, int]) -> bool:
        """Not used directly – logic is handled in make_move()."""
        return True

    def _validate_move(self, target: Tuple[int, int]) -> bool:
        if self.current_player == 1:
            return target in self.player1_legal_moves
        return target in self.player2_legal_moves

    def _check_endgame_conditions(self) -> Optional[str]:
        """Check if either player has reached the middle target or both are stuck."""
        if self.maze_path is None or self.maze_target is None:
            return None

        if self.player1_pos == self.maze_target:
            return "player1_wins"
        if self.player2_pos == self.maze_target:
            return "player2_wins"

        p1_stuck = not self.player1_legal_moves
        p2_stuck = not self.player2_legal_moves
        if p1_stuck and p2_stuck:
            mid = self.maze_mid_idx
            p1_idx = self.path_index.get(self.player1_pos, 0)
            p2_idx = self.path_index.get(self.player2_pos, len(self.maze_path) - 1)
            # Distance to middle: smaller is better
            p1_dist = abs(mid - p1_idx)
            p2_dist = abs(mid - p2_idx)
            if p1_dist < p2_dist:
                return "player1_wins"
            elif p2_dist < p1_dist:
                return "player2_wins"
            else:
                return "draw"
        return None

    def _update_legal_moves(self) -> None:
        """Base-class hook – delegates to full two-player update."""
        self._update_all_legal_moves()

    def _calculate_hint_degrees(self) -> None:
        """Warnsdorff degrees along the path for the current player."""
        if not self.maze_path:
            self.hint_degrees = {}
            return
        piece = self.get_selection("piece")
        n     = self.board_model.cols
        if self.current_player == 1:
            cur_pos    = self.player1_pos
            player_vis = self.player1_visited
        else:
            cur_pos    = self.player2_pos
            player_vis = self.player2_visited
        if not cur_pos:
            self.hint_degrees = {}
            return
        reachable = self._get_player_path_legal_moves(
            self.current_player, cur_pos, n, piece)
        degrees: Dict[Tuple[int, int], int] = {}
        for sq in reachable:
            onward = self._get_player_path_legal_moves(self.current_player, sq, n, piece)
            if onward:
                degrees[sq] = len(onward)
        self.hint_degrees = degrees

    def _capture_game_state(self) -> Dict[str, Any]:
        return {
            "current_player":      self.current_player,
            "pos":                 self.player_pos,
            "player1_pos":         self.player1_pos,
            "player2_pos":         self.player2_pos,
            "player1_visited":     self.player1_visited.copy(),
            "player2_visited":     self.player2_visited.copy(),
            "player1_visited_moves": self.player1_visited_moves.copy(),
            "player2_visited_moves": self.player2_visited_moves.copy(),
            "player1_known_mines": self.player1_known_mines.copy(),
            "player2_known_mines": self.player2_known_mines.copy(),
            "player1_perm_mines":  self.player1_perm_mines.copy(),
            "player2_perm_mines":  self.player2_perm_mines.copy(),
            "player1_attempt_count": self.player1_attempt_count,
            "player2_attempt_count": self.player2_attempt_count,
            "visited":             self.visited.copy(),
            "visited_moves":       self.visited_moves.copy(),
            "move_count":          self.move_count,
        }

    def _restore_game_state(self, state: Dict[str, Any]) -> None:
        self.current_player        = state.get("current_player", 1)
        self.player1_pos           = state.get("player1_pos")
        self.player2_pos           = state.get("player2_pos")
        self.player1_visited       = state.get("player1_visited", set()).copy()
        self.player2_visited       = state.get("player2_visited", set()).copy()
        self.player1_visited_moves = state.get("player1_visited_moves", {}).copy()
        self.player2_visited_moves = state.get("player2_visited_moves", {}).copy()
        self.player1_known_mines   = state.get("player1_known_mines", set()).copy()
        self.player2_known_mines   = state.get("player2_known_mines", set()).copy()
        self.player1_perm_mines    = state.get("player1_perm_mines", set()).copy()
        self.player2_perm_mines    = state.get("player2_perm_mines", set()).copy()
        self.player1_attempt_count = state.get("player1_attempt_count", 0)
        self.player2_attempt_count = state.get("player2_attempt_count", 0)
        self.visited               = state.get("visited", set()).copy()
        self.visited_moves         = state.get("visited_moves", {}).copy()
        self.move_count            = state.get("move_count", 0)
        self.player_pos            = state.get("pos")
        self._update_all_legal_moves()
        self._sync_base_state()
        if self.hint_mode_active:
            self._calculate_hint_degrees()
        else:
            self.hint_degrees = {}

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
    #  Button building                                                    #
    # ================================================================== #

    def _build_buttons(self) -> None:
        f = self.font
        self.buttons: Dict[str, Button] = {
            "start":       Button(pygame.Rect(0, 0, 0, 0), "start", f,
                                  (255, 255, 255), (92, 192, 92),   self.start_game),
            "blind_draw":  Button(pygame.Rect(0, 0, 0, 0), "blind draw", f,
                                  (255, 255, 255), (128, 32, 64),   self.start_blind_draw),
            "enter_code":  Button(pygame.Rect(0, 0, 0, 0), "enter share code", f,
                                  (255, 255, 255), (224, 0, 96),    self.toggle_codec_input),
            "copy_code":   Button(pygame.Rect(0, 0, 0, 0), "copy share code", f,
                                  (255, 255, 255), (224, 0, 96),    self.copy_code_to_clipboard),
            "guide_mode":  Button(pygame.Rect(0, 0, 0, 0), "show move guide", f,
                                  (255, 255, 255), (128, 64, 255),  self.toggle_guide_mode),
            "track_mode":  Button(pygame.Rect(0, 0, 0, 0), "show move track", f,
                                  (255, 255, 255), (255, 92, 128),  self.toggle_track_mode),
            "undo_mode":   Button(pygame.Rect(0, 0, 0, 0), "undo last move", f,
                                  (255, 255, 255), (64, 128, 255),  self.undo_move),
            "resign":      Button(pygame.Rect(0, 0, 0, 0), "resign", f,
                                  (255, 255, 255), (107, 50, 71),   self.resign_game),
            "accept_resignation": Button(pygame.Rect(0, 0, 0, 0), "accept", f,
                                         (255, 255, 255), (107, 70, 51),
                                         self.accept_bot_resignation),
            "replay_mode": Button(pygame.Rect(0, 0, 0, 0), "start replay", f,
                                  (255, 255, 255), (64, 128, 255),  self.toggle_replay_mode),
            "replay_prev": Button(pygame.Rect(0, 0, 0, 0), "-", f,
                                  (255, 255, 240), (64, 128, 255),
                                  lambda: self.navigate_replay(-1)),
            "replay_next": Button(pygame.Rect(0, 0, 0, 0), "+", f,
                                  (255, 255, 240), (64, 128, 255),
                                  lambda: self.navigate_replay(1)),
            "retry":       Button(pygame.Rect(0, 0, 0, 0), "retry", f,
                                  (255, 255, 255), (92, 192, 92),   self.retry_game),
            "new_game":    Button(pygame.Rect(0, 0, 0, 0), "new game", f,
                                  (255, 255, 255), (32, 128, 96),   self.new_game),
            "peek_mode":   Button(pygame.Rect(0, 0, 0, 0), "peek", f,
                                  (255, 255, 240), DK_SQUARE,       self.toggle_peek),
            "exit":        Button(pygame.Rect(0, 0, 0, 0), "exit", f,
                                  (255, 255, 255), (220, 40, 40),   self.quit_game),
        }

    # ================================================================== #
    #  Game start override                                                #
    # ================================================================== #

    def start_game(self, use_seed: Optional[int] = None) -> None:
        """Start a new game: generate maze and place players at fixed positions."""
        board_size = self.get_selection("board")
        piece_name = self.get_selection("piece")

        min_board = self._get_min_board_size(piece_name)
        if board_size < min_board:
            self.error_message = f"{piece_name} needs board >= {min_board}"
            self.error_timer   = pygame.time.get_ticks() + 3000
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
                self.error_timer   = pygame.time.get_ticks() + 3000
                return
        else:
            seed = random.randint(0, 2 ** 63 - 1)

        self.last_puzzle_seed = seed

        if not self._game_specific_start_setup(seed):
            self.error_message = "Failed to generate maze"
            self.error_timer   = pygame.time.get_ticks() + 3000
            return

        n = self.get_selection("board")
        self.board_model.cols = n
        self.board_model.rows = n
        self.board_model.clear()

        try:
            self.puzzle_code = encode_params(self._get_encode_params(), self.schema, seed)
        except Exception:
            self.puzzle_code = ""

        # Players are always placed at fixed positions – start immediately.
        self._common_ingame_start()
        if self._is_bot_turn():
            self._schedule_bot_move()

    def _common_ingame_start(self) -> None:
        self.end_state           = None
        self.paused_elapsed      = 0.0
        self.clock_elapsed       = 0
        self.final_elapsed       = 0
        self.replay_states       = [self._capture_game_state()]
        self.replay_index        = 0
        self.replay_mode_active  = False
        self.peek_mode_visible   = False
        self.reveal_mode_active  = False
        self.hint_degrees        = {}
        self.bot_move_pending    = False
        self.game_state          = GameState.INGAME
        if self._is_per_move_mode():
            self.clock_start_time = None
            self.move_start_time  = time.time()
        else:
            self.clock_start_time = time.time()
            self.move_start_time  = None

    # ================================================================== #
    #  Per-frame update                                                   #
    # ================================================================== #

    def update(self, dt: int) -> None:
        super().update(dt)
        now = time.time()
        # Expire flash lists
        self.player1_flash_list = [
            (sq, ts) for sq, ts in self.player1_flash_list if now - ts < 2.0]
        self.player2_flash_list = [
            (sq, ts) for sq, ts in self.player2_flash_list if now - ts < 2.0]
        # Per-move timeout check
        if self.game_state == GameState.INGAME:
            if self._is_per_move_mode() and self.move_start_time is not None:
                clock_sel = self.get_selection("clock")
                if now - self.move_start_time >= clock_sel:
                    self.final_elapsed = int(now - self.move_start_time)
                    self.end_state  = "timeout"
                    self.game_state = GameState.ENDGAME
                    self.bot_move_pending = False
                    return
        # Execute pending bot move
        if (self.game_state == GameState.INGAME
                and self.bot_move_pending
                and pygame.time.get_ticks() >= self.bot_move_timer):
            self._execute_bot_move()

    # ================================================================== #
    #  Move logic                                                         #
    # ================================================================== #

    def make_move(self, target: Tuple[int, int]) -> None:
        """Attempt a move for the current player."""
        if self.game_state != GameState.INGAME:
            return
        if self.bot_move_pending:
            return
        # Start per-game clock on first human move (not needed for per-move mode)
        if not self._is_per_move_mode() and self.clock_start_time is None:
            self.clock_start_time = time.time()

        player       = self.current_player
        pos          = self.player1_pos if player == 1 else self.player2_pos
        piece        = self.get_selection("piece")
        n            = self.board_model.cols
        blocks_show  = self.get_selection("blocks") == "show"
        bounce       = self.get_selection("bounce") == "bounce"

        # Piece must be able to reach the target from current position
        reachable = pk.get_move_func(piece)(*pos, n)
        if target not in reachable:
            return

        if target in self.obstacles:
            # Mine hit – record the hit then switch turn to the other player.
            self._record_mine_hit(player, target, blocks_show, bounce)
            self._update_all_legal_moves()
            # Switch turn (with continuation rule: if other player has no moves,
            # the current player keeps their turn).
            other       = 3 - self.current_player
            other_moves = self.player1_legal_moves if other == 1 else self.player2_legal_moves
            if other_moves:
                self.current_player = other
            self._sync_base_state()
            # Reset per-move clock on mine hit (turn changes)
            if self._is_per_move_mode() and self.game_state == GameState.INGAME:
                self.move_start_time = time.time()
            # Check end conditions (being stuck after bounce)
            end = self._check_endgame_conditions()
            if end:
                self._go_to_endgame(end)
                return
            if self._is_bot_turn():
                self._schedule_bot_move()
            return

        if target not in self.maze_path_set:
            # Off-path move – silently ignore
            return
        if player == 1 and target in self.player1_visited:
            return
        if player == 2 and target in self.player2_visited:
            return

        # Valid path move
        self._apply_move(player, target)

        end = self._check_endgame_conditions()
        if end:
            self._go_to_endgame(end)
            return

        # Switch player (with continuation rule)
        other       = 3 - self.current_player
        other_moves = self.player1_legal_moves if other == 1 else self.player2_legal_moves
        if other_moves:
            self.current_player = other
        # else: current player continues (opponent is stuck)

        self._sync_base_state()

        # Reset per-move clock after a valid path move
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

    def _record_mine_hit(
        self,
        player: int,
        target: Tuple[int, int],
        blocks_show: bool,
        bounce: bool,
    ) -> None:
        """Record a mine hit and apply bounce/stay logic."""
        if player == 1:
            self.player1_attempt_count += 1
            self.player1_known_mines.add(target)
            if blocks_show:
                self.player1_perm_mines.add(target)
            else:
                self.player1_flash_list.append((target, time.time()))
            if bounce:
                # P1 bounces back to its own start (path[0])
                start = self.player1_start or (self.maze_path[0] if self.maze_path else target)
                self.player1_pos = start
                self.player1_visited       = {start}
                self.player1_visited_moves = {start: 1}
        else:
            self.player2_attempt_count += 1
            self.player2_known_mines.add(target)
            if blocks_show:
                self.player2_perm_mines.add(target)
            else:
                self.player2_flash_list.append((target, time.time()))
            if bounce:
                # P2 bounces back to its own start (path[-1])
                start = self.player2_start or (self.maze_path[-1] if self.maze_path else target)
                self.player2_pos = start
                self.player2_visited       = {start}
                self.player2_visited_moves = {start: 1}

        self.move_count += 1

    def _apply_move(self, player: int, pos: Tuple[int, int]) -> None:
        """Apply a valid path move and update replay states."""
        if player == 1:
            self.player1_pos = pos
            self.player1_visited.add(pos)
            self.player1_visited_moves[pos] = len(self.player1_visited)
        else:
            self.player2_pos = pos
            self.player2_visited.add(pos)
            self.player2_visited_moves[pos] = len(self.player2_visited)

        self.move_count += 1
        # Keep the base-class visited union up to date so base rendering helpers work.
        self.visited = self.player1_visited | self.player2_visited
        self._update_all_legal_moves()
        self.replay_states.append(self._capture_game_state())

    def undo_move(self) -> None:
        """Undo the last move pair."""
        if self.game_state != GameState.INGAME:
            return
        self.bot_move_pending = False
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
        """Human player resigns."""
        if self.game_state != GameState.INGAME:
            return
        self.bot_move_pending = False
        self.final_elapsed = int(self.paused_elapsed + (
            (time.time() - self.clock_start_time) if self.clock_start_time else 0))
        human  = self._human_player_num()
        reason = f"player{human}_resignation"
        self.end_state  = reason
        self.game_state = GameState.ENDGAME

    def accept_bot_resignation(self) -> None:
        """Human accepts the bot's resignation offer."""
        if self.game_state != GameState.INGAME or not self.bot_offers_resignation:
            return
        self.bot_move_pending = False
        self.final_elapsed = int(self.paused_elapsed + (
            (time.time() - self.clock_start_time) if self.clock_start_time else 0))
        bot    = 3 - self._human_player_num()
        reason = f"player{bot}_resignation"
        self.bot_offers_resignation = False
        self._go_to_endgame(reason)

    def new_game(self) -> None:
        super().new_game()
        self._clear_two_player_state()
        self.menu_preview_cache  = None
        self.menu_preview_pos    = None
        self.bot_move_pending    = False
        self.bot_offers_resignation = False
        self.hint_degrees        = {}
        self.move_start_time     = None
        self.maze_path           = None
        self.maze_path_set       = set()
        self.maze_target         = None
        self.maze_mid_idx        = 0
        self.obstacles           = set()
        self.path_index          = {}

    # ================================================================== #
    #  Blind draw                                                         #
    # ================================================================== #

    def start_blind_draw(self) -> None:
        """Randomize settings then start."""
        piece_name = self.get_selection("piece")
        for i, (label, values, _) in enumerate(self.menu_items):
            if label == "board":
                while True:
                    idx = random.randint(0, len(values) - 1)
                    if values[idx] >= self._get_min_board_size(piece_name):
                        self.menu_items[i] = (label, values, idx)
                        break
            elif label in ("player one", "level", "clock", "time per", "length", "density", "blocks", "bounce"):
                self.menu_items[i] = (label, values, random.randint(0, len(values) - 1))
        self.start_game()

    # ================================================================== #
    #  Bot helpers                                                        #
    # ================================================================== #

    def _human_player_num(self) -> int:
        return 1 if self.get_selection("player one") == "human" else 2

    def _is_bot_turn(self) -> bool:
        return self.current_player != self._human_player_num()

    def _schedule_bot_move(self) -> None:
        delay = random.randint(BOT_MOVE_DELAY_MIN, BOT_MOVE_DELAY_MAX)
        self.bot_move_timer   = pygame.time.get_ticks() + delay
        self.bot_move_pending = True

    def _execute_bot_move(self) -> None:
        self.bot_move_pending = False
        if self.game_state != GameState.INGAME:
            return

        bot_player   = self.current_player
        bot_pos      = self.player1_pos if bot_player == 1 else self.player2_pos
        if bot_pos is None:
            return

        level_str = self.get_selection("level")
        try:
            level = BotLevel(level_str)
        except ValueError:
            level = BotLevel.LEVEL_1

        piece_name   = self.get_selection("piece")
        board_size   = self.board_model.cols
        blocks_show  = self.get_selection("blocks") == "show"
        player_vis   = self.player1_visited if bot_player == 1 else self.player2_visited
        known_mines  = self.player1_known_mines if bot_player == 1 else self.player2_known_mines
        opponent_pos = self.player2_pos if bot_player == 1 else self.player1_pos

        domain_data = {
            "maze_path_set":  self.maze_path_set,
            "path_index":     self.path_index,
            "target_idx":     self.maze_mid_idx,
            "bot_player_num": bot_player,
            "known_mines":    known_mines,
            "blocks_show":    blocks_show,
            "obstacles":      self.obstacles,
            "bounce_mode":    self.get_selection("bounce") == "bounce",
            "player_visited": player_vis,
            "player_start":   self.player1_start if bot_player == 1 else self.player2_start,
        }

        chosen = make_bot_move(
            level, piece_name, bot_pos, board_size,
            all_visited=player_vis,
            domain_data=domain_data,
            opponent_pos=opponent_pos,
        )
        if chosen is not None:
            self.make_move(chosen)
        else:
            # Bot has no move – try to advance the game state
            end = self._check_endgame_conditions()
            if end:
                self._go_to_endgame(end)

    def _check_bot_resignation_condition(self) -> bool:
        """Bot offers to resign when it's stuck and opponent is closer to middle."""
        player_one = self.get_selection("player one")
        bot_player   = 2 if player_one == "human" else 1
        human_player = 3 - bot_player

        bot_moves   = self.player1_legal_moves if bot_player == 1 else self.player2_legal_moves
        human_moves = self.player1_legal_moves if human_player == 1 else self.player2_legal_moves
        bot_pos     = self.player1_pos if bot_player == 1 else self.player2_pos
        human_pos   = self.player1_pos if human_player == 1 else self.player2_pos
        mid         = self.maze_mid_idx

        bot_dist   = abs(mid - self.path_index.get(bot_pos, 0))   if bot_pos   else mid
        human_dist = abs(mid - self.path_index.get(human_pos, 0)) if human_pos else mid

        return (not bot_moves) and bool(human_moves) and human_dist < bot_dist

    # ================================================================== #
    #  Internal helpers                                                   #
    # ================================================================== #

    def _clear_two_player_state(self) -> None:
        self.player1_pos           = None
        self.player2_pos           = None
        self.player1_start         = None
        self.player2_start         = None
        self.player1_visited       = set()
        self.player2_visited       = set()
        self.player1_visited_moves = {}
        self.player2_visited_moves = {}
        self.player1_legal_moves   = []
        self.player2_legal_moves   = []
        self.player1_known_mines   = set()
        self.player2_known_mines   = set()
        self.player1_flash_list    = []
        self.player2_flash_list    = []
        self.player1_perm_mines    = set()
        self.player2_perm_mines    = set()
        self.player1_attempt_count = 0
        self.player2_attempt_count = 0
        self.current_player        = 1
        self.visited               = set()
        self.visited_moves         = {}
        self.player_pos            = None
        self.legal_moves           = []
        self.move_count            = 0
        self.clock_elapsed         = 0
        self.final_elapsed         = 0
        self.bot_offers_resignation = False

    def _place_player(self, player: int, pos: Tuple[int, int]) -> None:
        """Set a player's starting position."""
        if player == 1:
            self.player1_pos           = pos
            self.player1_start         = pos
            self.player1_visited       = {pos}
            self.player1_visited_moves = {pos: 1}
        else:
            self.player2_pos           = pos
            self.player2_start         = pos
            self.player2_visited       = {pos}
            self.player2_visited_moves = {pos: 1}

    def _get_all_legal_moves(
        self,
        pos:      Tuple[int, int],
        n:        int,
        piece:    str,
        excluded: Set[Tuple[int, int]],
    ) -> List[Tuple[int, int]]:
        """All on-board moves from *pos*, excluding *excluded* squares."""
        raw = pk.get_move_func(piece)(*pos, n)
        return [(x, y) for (x, y) in raw if (x, y) not in excluded]

    def _get_excluded_for_guide_arrows_for_player(
        self,
        player: int,
        visited: Set[Tuple[int, int]],
    ) -> Set[Tuple[int, int]]:
        """
        Get squares to exclude from guide arrows for a given player.

        Excludes:
        1. Visited squares that are NOT obstacles (visited but not mines)
        2. Known mines (if blocks are hidden) or all obstacles (if blocks are shown)
        """
        blocks_show = self.get_selection("blocks") == "show"
        known = self.player1_known_mines if player == 1 else self.player2_known_mines
        perm  = self.player1_perm_mines  if player == 1 else self.player2_perm_mines
        excluded = set()
        # Exclude visited squares that are not obstacles
        for sq in visited:
            if sq not in self.obstacles:
                excluded.add(sq)
        # Exclude revealed mines
        if blocks_show:
            excluded.update(perm)
        else:
            excluded.update(known)
        return excluded

    def _get_player_path_legal_moves(
        self,
        player: int,
        pos: Tuple[int, int],
        n: int,
        piece: str,
    ) -> List[Tuple[int, int]]:
        """
        Legal path moves for player from pos.

        P1 (Blue) counts up: can only move to path squares with higher index.
        P2 (Red) counts down: can only move to path squares with lower index.
        Excludes visited squares and effective mines.
        """
        raw     = pk.get_move_func(piece)(*pos, n)
        visited = self.player1_visited if player == 1 else self.player2_visited
        known   = self.player1_known_mines if player == 1 else self.player2_known_mines
        blocks_show = self.get_selection("blocks") == "show"
        effective_mines = self.obstacles if blocks_show else known
        current_idx = self.path_index.get(pos, -1)

        if player == 1:
            # P1 counts up: only squares with higher path index
            return [
                (x, y) for (x, y) in raw
                if (x, y) in self.maze_path_set
                and (x, y) not in visited
                and (x, y) not in effective_mines
                and self.path_index.get((x, y), -1) > current_idx
            ]
        else:
            # P2 counts down: only squares with lower path index
            return [
                (x, y) for (x, y) in raw
                if (x, y) in self.maze_path_set
                and (x, y) not in visited
                and (x, y) not in effective_mines
                and self.path_index.get((x, y), len(self.maze_path)) < current_idx
            ]

    def _update_all_legal_moves(self) -> None:
        """Recompute legal path moves for both players."""
        if not self.maze_path:
            self.player1_legal_moves = []
            self.player2_legal_moves = []
            return
        piece = self.get_selection("piece")
        n     = self.board_model.cols

        if self.player1_pos:
            self.player1_legal_moves = self._get_player_path_legal_moves(
                1, self.player1_pos, n, piece)
        else:
            self.player1_legal_moves = []

        if self.player2_pos:
            self.player2_legal_moves = self._get_player_path_legal_moves(
                2, self.player2_pos, n, piece)
        else:
            self.player2_legal_moves = []

    def _sync_base_state(self) -> None:
        """Sync base-class fields to the current player's data."""
        if self.current_player == 1:
            self.player_pos    = self.player1_pos
            self.legal_moves   = self.player1_legal_moves
            self.visited_moves = self.player1_visited_moves
        else:
            self.player_pos    = self.player2_pos
            self.legal_moves   = self.player2_legal_moves
            self.visited_moves = self.player2_visited_moves

    def _go_to_endgame(self, end_condition: str) -> None:
        self.final_elapsed = int(self.paused_elapsed + (
            (time.time() - self.clock_start_time) if self.clock_start_time else 0))
        self.end_state      = end_condition
        self.game_state     = GameState.ENDGAME
        self.bot_move_pending = False

    def _draw_tinted_piece(
        self,
        screen: pygame.Surface,
        piece_rect: pygame.Rect,
        tint_color: Tuple[int, int, int],
    ) -> None:
        piece_name = self.get_selection("piece")
        try:
            pk.draw_piece(screen, piece_rect, piece_name)
        except Exception:
            pygame.draw.ellipse(screen, tint_color, piece_rect)

    # ================================================================== #
    #  Board rendering                                                    #
    # ================================================================== #

    def _render_game_specific_board(self, screen: pygame.Surface) -> None:
        """Draw maze, obstacles, players, and guide arrows."""
        cs  = self.current_cell_size
        gs  = self.game_state
        nf  = pygame.font.SysFont("arial", max(8, cs // 3))
        now = time.time()

        # ---- determine display state (replay vs live) ----
        if gs == GameState.ENDGAME and self.replay_mode_active and self.replay_states:
            snap = self.replay_states[self.replay_index]
            d_p1_pos = snap.get("player1_pos")
            d_p2_pos = snap.get("player2_pos")
            d_p1_vis = snap.get("player1_visited", set())
            d_p2_vis = snap.get("player2_visited", set())
            d_p1_vm  = snap.get("player1_visited_moves", {})
            d_p2_vm  = snap.get("player2_visited_moves", {})
            d_cur    = snap.get("current_player", 1)
            d_p1_pm  = snap.get("player1_perm_mines", set())
            d_p2_pm  = snap.get("player2_perm_mines", set())
        else:
            d_p1_pos = self.player1_pos
            d_p2_pos = self.player2_pos
            d_p1_vis = self.player1_visited
            d_p2_vis = self.player2_visited
            d_p1_vm  = self.player1_visited_moves
            d_p2_vm  = self.player2_visited_moves
            d_cur    = self.current_player
            d_p1_pm  = self.player1_perm_mines
            d_p2_pm  = self.player2_perm_mines

        # ---- maze path (dim background) – only visible when peeking or revealed ----
        show_full_path = (
            (gs == GameState.INGAME  and self.peek_mode_visible) or
            (gs == GameState.ENDGAME and self.reveal_mode_active)
        )

        if show_full_path and self.maze_path:
            for gx, gy in self.maze_path:
                if (gx, gy) == self.maze_target:
                    continue
                if (gx, gy) not in d_p1_vis and (gx, gy) not in d_p2_vis:
                    px, py = self.board_renderer.to_pixel(gx, gy)
                    color  = LT_MOVE if (gx + gy) % 2 == 0 else DK_MOVE
                    pygame.draw.rect(screen, color, (px + 1, py + 1, cs - 1, cs - 1))

        # ---- target (middle square) ----
        if self.maze_target and cs > 0:
            tx, ty   = self.maze_target
            px, py   = self.board_renderer.to_pixel(tx, ty)
            scaled_t = pygame.transform.smoothscale(self.target_img, (cs, cs))
            screen.blit(scaled_t, (px, py))

        # ---- player 1 visited squares (blue) ----
        for vx, vy in d_p1_vis:
            px, py  = self.board_renderer.to_pixel(vx, vy)
            vcolor  = P1_LT_VISITED if (vx + vy) % 2 == 0 else P1_DK_VISITED
            pygame.draw.rect(screen, vcolor, (px + 3, py + 3, cs - 4, cs - 4))
            if self.track_mode_active and (vx, vy) in d_p1_vm:
                luma = vcolor[0] * 0.299 + vcolor[1] * 0.587 + vcolor[2] * 0.114
                nc   = (0, 0, 0) if luma > 128 else (255, 255, 240)
                ns   = nf.render(str(d_p1_vm[(vx, vy)]), True, nc)
                screen.blit(ns, ns.get_rect(center=(px + (cs // 6), py + cs // 6)))

        # ---- player 2 visited squares (red) ----
        for vx, vy in d_p2_vis:
            px, py  = self.board_renderer.to_pixel(vx, vy)
            vcolor  = P2_LT_VISITED if (vx + vy) % 2 == 0 else P2_DK_VISITED
            pygame.draw.rect(screen, vcolor, (px + 3, py + 3, cs - 4, cs - 4))
            if self.track_mode_active and (vx, vy) in d_p2_vm:
                luma = vcolor[0] * 0.299 + vcolor[1] * 0.587 + vcolor[2] * 0.114
                nc   = (0, 0, 0) if luma > 128 else (255, 255, 240)
                ns   = nf.render(str(d_p2_vm[(vx, vy)]), True, nc)
                screen.blit(ns, ns.get_rect(center=(px + (cs // 6), py + cs // 6)))

        # ---- permanent mine markers ----
        for gx, gy in d_p1_pm:
            px, py   = self.board_renderer.to_pixel(gx, gy)
            if cs > 0:
                img_size    = max(1, int(cs * 0.6))
                scaled_mine = pygame.transform.smoothscale(self.mine_blue_img, (img_size, img_size))
                offset      = (cs - img_size) // 2
                screen.blit(scaled_mine, (px + offset, py + offset))
        for gx, gy in d_p2_pm:
            px, py   = self.board_renderer.to_pixel(gx, gy)
            if cs > 0:
                img_size    = max(1, int(cs * 0.6))
                scaled_mine = pygame.transform.smoothscale(self.mine_red_img, (img_size, img_size))
                offset      = (cs - img_size) // 2
                screen.blit(scaled_mine, (px + offset, py + offset))

        # ---- flashing mine markers ----
        for sq, ts in self.player1_flash_list:
            if now - ts < 1.5:
                gx, gy   = sq
                px, py   = self.board_renderer.to_pixel(gx, gy)
                if cs > 0:
                    img_size    = max(1, int(cs * 0.6))
                    scaled_mine = pygame.transform.smoothscale(self.mine_blue_img, (img_size, img_size))
                    offset      = (cs - img_size) // 2
                    screen.blit(scaled_mine, (px + offset, py + offset))
        for sq, ts in self.player2_flash_list:
            if now - ts < 1.5:
                gx, gy   = sq
                px, py   = self.board_renderer.to_pixel(gx, gy)
                if cs > 0:
                    img_size    = max(1, int(cs * 0.6))
                    scaled_mine = pygame.transform.smoothscale(self.mine_red_img, (img_size, img_size))
                    offset      = (cs - img_size) // 2
                    screen.blit(scaled_mine, (px + offset, py + offset))

        # ---- guide arrows ----
        if self.guide_mode_active and self.arrows and gs == GameState.INGAME:
            cur_pos   = d_p1_pos if d_cur == 1 else d_p2_pos
            cur_vis   = d_p1_vis if d_cur == 1 else d_p2_vis
            if cur_pos:
                piece     = self.get_selection("piece")
                n_brd     = self.board_model.cols
                valid_squares = self.maze_path_set | self.obstacles
                excluded  = self._get_excluded_for_guide_arrows_for_player(d_cur, cur_vis)
                guide_moves = self._get_all_legal_moves(cur_pos, n_brd, piece, excluded)
                guide_moves = [sq for sq in guide_moves if sq in valid_squares]
                if guide_moves:
                    self._draw_arrows(screen, guide_moves, cur_pos)

        # ---- hint degrees ----
        if self.hint_mode_active and self.hint_degrees and gs == GameState.INGAME:
            for (hx, hy), deg in self.hint_degrees.items():
                px, py = self.board_renderer.to_pixel(hx, hy)
                color  = (0, 0, 192) if self.current_player == 1 else (192, 0, 0)
                hs     = nf.render(str(deg), True, color)
                screen.blit(hs, hs.get_rect(center=(px + cs // 2, py + cs // 2)))

        # ---- player 2 piece (red) ----
        if d_p2_pos:
            ppx, ppy = self.board_renderer.to_pixel(*d_p2_pos)
            pr       = pygame.Rect(ppx + 1, ppy + 1, cs - 2, cs - 2)
            self._draw_tinted_piece(screen, pr, P2_DK_VISITED)

        # ---- player 1 piece (blue) ----
        if d_p1_pos:
            ppx, ppy = self.board_renderer.to_pixel(*d_p1_pos)
            pr       = pygame.Rect(ppx + 1, ppy + 1, cs - 2, cs - 2)
            self._draw_tinted_piece(screen, pr, P1_DK_VISITED)

    def _render_game_specific_stats(
        self, screen: pygame.Surface, stats_panel: UIPanel
    ) -> None:
        """Render player progress scores, turn indicator, and end message."""
        bounds      = stats_panel.get_bounds("STATS_PANEL")
        line_height = self.font.get_linesize() + UI_SPACE
        stats_w     = bounds["width"]
        stats_left  = bounds["left"]
        col1_cx     = stats_left + stats_w // 4
        col2_cx     = stats_left + 3 * stats_w // 4
        mid_cx      = bounds["center_x"]

        if (self.game_state == GameState.ENDGAME
                and self.replay_mode_active and self.replay_states):
            snap    = self.replay_states[self.replay_index]
            p1_pos  = snap.get("player1_pos")
            p2_pos  = snap.get("player2_pos")
            disp_cur = snap.get("current_player", 1)
            p1_atm  = snap.get("player1_attempt_count", 0)
            p2_atm  = snap.get("player2_attempt_count", 0)
        else:
            p1_pos  = self.player1_pos
            p2_pos  = self.player2_pos
            disp_cur = self.current_player
            p1_atm  = self.player1_attempt_count
            p2_atm  = self.player2_attempt_count

        p1_path_idx = self.path_index.get(p1_pos, 0) if p1_pos else 0
        p2_path_idx = self.path_index.get(p2_pos, len(self.maze_path) - 1 if self.maze_path else 0) if p2_pos else 0
        mid_idx     = self.maze_mid_idx
        path_len    = len(self.maze_path) if self.maze_path else 1

        # P1 progress: how far from path[0] toward middle (0 → mid_idx)
        p1_progress = p1_path_idx
        p1_total    = mid_idx
        # P2 progress: how far from path[-1] toward middle (0 → path_len-1-mid_idx)
        p2_progress = (path_len - 1) - p2_path_idx
        p2_total    = (path_len - 1) - mid_idx

        # Row 0: column headers
        p1_color = (0, 0, 192)
        p2_color = (192, 0, 0)
        y0 = stats_panel.get_line_y("STATS_PANEL", 0, line_height)
        screen.blit(self.font.render("blue", True, p1_color),
                    self.font.render("blue", True, p1_color).get_rect(centerx=col1_cx, top=y0))
        screen.blit(self.font.render("red", True, p2_color),
                    self.font.render("red", True, p2_color).get_rect(centerx=col2_cx, top=y0))

        # Row 1: progress toward middle
        y1 = stats_panel.get_line_y("STATS_PANEL", 1, line_height)
        p1_s = self.font.render(f"{p1_progress}/{p1_total}", True, p1_color)
        p2_s = self.font.render(f"{p2_progress}/{p2_total}", True, p2_color)
        screen.blit(p1_s, p1_s.get_rect(centerx=col1_cx, top=y1))
        screen.blit(p2_s, p2_s.get_rect(centerx=col2_cx, top=y1))
        prog_s = self.font.render("progress", True, (0, 0, 0))
        screen.blit(prog_s, prog_s.get_rect(centerx=mid_cx, top=y1))

        # Row 2: mine hits
        y2 = stats_panel.get_line_y("STATS_PANEL", 2, line_height)
        for cx, atm, col in ((col1_cx, p1_atm, p1_color),
                              (col2_cx, p2_atm, p2_color)):
            s = self.font.render(str(atm), True, col)
            screen.blit(s, s.get_rect(centerx=cx, top=y2))
        mines_s = self.font.render("mine hits", True, (0, 0, 0))
        screen.blit(mines_s, mines_s.get_rect(centerx=mid_cx, top=y2))

        # Row 3: whose turn
        if self.game_state == GameState.INGAME:
            turn_color = p1_color if disp_cur == 1 else p2_color
            turn_text  = "blue's turn" if disp_cur == 1 else "red's turn"
            turn_s     = self.font.render(turn_text, True, turn_color)
            y3         = stats_panel.get_line_y("STATS_PANEL", 3, line_height)
            screen.blit(turn_s, turn_s.get_rect(centerx=mid_cx, top=y3))

        # Bot resignation offer
        if self.game_state == GameState.INGAME and self.bot_offers_resignation:
            player_one = self.get_selection("player one")
            if player_one == "bot":
                offer_color = p1_color
                offer_text  = "blue offers to resign"
            else:
                offer_color = p2_color
                offer_text  = "red offers to resign"
            y5 = stats_panel.get_line_y("STATS_PANEL", 5, line_height)
            rm = self.font_large.render(offer_text, True, offer_color)
            screen.blit(rm, rm.get_rect(centerx=mid_cx, top=y5))
            y7 = stats_panel.get_line_y("STATS_PANEL", 7, line_height)
            self.buttons["accept_resignation"].active = True
            self.buttons["accept_resignation"].rect   = pygame.Rect(
                mid_cx - BTW // 2, y7, BTW, BTH)
            self.buttons["accept_resignation"].draw(screen)
        else:
            self.buttons["accept_resignation"].active = False

        # Clock (row 9)
        if self.game_state in (GameState.INGAME, GameState.ENDGAME):
            rem     = self._remaining_time()
            elapsed = (self.final_elapsed
                       if self.game_state == GameState.ENDGAME
                       else self.clock_elapsed)
            if rem is not None:
                time_str    = _format_time(rem)
                clock_color = (200, 0, 0) if rem < 30 else (0, 0, 0)
            else:
                time_str    = _format_time(elapsed)
                clock_color = (0, 0, 0)
            clk_s = self.font.render(time_str, True, clock_color)
            clk_y = stats_panel.get_line_y("STATS_PANEL", 9, line_height)
            screen.blit(clk_s, clk_s.get_rect(
                centerx=bounds["center_x"], top=clk_y))

        # End message
        if self.game_state == GameState.ENDGAME and self.end_state:
            end_messages = {
                "player1_wins":         ("blue wins",     (0, 0, 192)),
                "player2_wins":         ("red wins",      (192, 0, 0)),
                "player1_resignation":  ("blue resigned", (0, 0, 192)),
                "player2_resignation":  ("red resigned",  (192, 0, 0)),
                "draw":                 ("draw",          (96, 0, 96)),
                "timeout":              ("time's up",     (64, 0, 64)),
            }
            msg, msg_color = end_messages.get(self.end_state, ("game over", (0, 0, 0)))
            em_s = self.font_large.render(msg, True, msg_color)
            em_y = stats_panel.get_line_y("STATS_PANEL", 6, line_height)
            screen.blit(em_s, em_s.get_rect(centerx=bounds["center_x"], top=em_y))

    # ================================================================== #
    #  Menu preview                                                       #
    # ================================================================== #

    def _render_menu_preview(self, screen: pygame.Surface) -> None:
        cs  = self.current_cell_size
        brd = self.get_selection("board")

        cache_key = (brd, self.get_selection("piece"), self.get_selection("length"),
                     self.get_selection("density"))

        if self.menu_preview_cache is None or self.menu_preview_cache[0] != cache_key:
            piece    = self.get_selection("piece")
            length   = self.get_selection("length")
            density  = self.get_selection("density")
            move_func = pk.get_move_func(piece)
            prev_rng  = _make_rng(None)
            mn_len, mx_len = adaptive_path_lengths(brd, move_func, length, rng=prev_rng)
            pp, po   = generate_maze_path_and_obstacles(
                brd, mn_len, mx_len, move_func,
                max_attempts=100, time_budget=0.5, rng=prev_rng, density=density)
            self.menu_preview_cache = (cache_key, pp, po or set())
            self.menu_preview_pos   = pp[0] if pp else None

        _, prev_path, _ = self.menu_preview_cache
        if not prev_path:
            return

        if (self.menu_preview_pos is None
                or not (0 <= self.menu_preview_pos[0] < brd
                        and 0 <= self.menu_preview_pos[1] < brd)):
            self.menu_preview_pos = prev_path[0]

        pf = pygame.font.SysFont("arial", max(8, cs // 3))
        for i, (gx, gy) in enumerate(prev_path):
            px, py = self.board_renderer.to_pixel(gx, gy)
            mid_i  = len(prev_path) // 2
            if i == mid_i:
                # Show target marker at middle in preview
                if cs > 0:
                    scaled_t = pygame.transform.smoothscale(self.target_img, (cs, cs))
                    screen.blit(scaled_t, (px, py))
            else:
                color = LT_MOVE if (gx + gy) % 2 == 0 else DK_MOVE
                pygame.draw.rect(screen, color, (px + 1, py + 1, cs - 1, cs - 1))
                luma = color[0] * 0.299 + color[1] * 0.587 + color[2] * 0.114
                nc   = (0, 0, 0) if luma > 128 else (255, 255, 255)
                ns   = pf.render(str(i), True, nc)
                screen.blit(ns, ns.get_rect(center=(px + (cs // 6), py + cs // 6)))

        mpos     = self.menu_preview_pos
        ppx, ppy = self.board_renderer.to_pixel(*mpos)
        pr_rect  = pygame.Rect(ppx + 1, ppy + 1, cs - 2, cs - 2)
        try:
            pk.draw_piece(screen, pr_rect, self.get_selection("piece"))
        except Exception:
            pygame.draw.ellipse(screen, (0, 0, 0), pr_rect)

        if self.guide_mode_active and self.arrows:
            raw_g   = pk.get_move_func(self.get_selection("piece"))(*mpos, brd)
            legal_g = [(x, y) for (x, y) in raw_g if 0 <= x < brd and 0 <= y < brd]
            self._draw_arrows(screen, legal_g, mpos)

    # ================================================================== #
    #  Left-panel rendering                                               #
    # ================================================================== #

    def _render_left_panel(
        self, screen: pygame.Surface, left_panel: UIPanel,
        msg_left: int, msg_right: int, msg_bottom: int,
    ) -> None:
        btn_w       = int(UI_SPACE * 1.5)
        line_height = self.font.get_linesize() + UI_SPACE

        # ---- MENU_PANEL ----
        menu_bounds      = left_panel.get_bounds("MENU_PANEL")
        text_x           = menu_bounds["left"] + UI_SPACE
        menu_panel_items = [(i, (lbl, vals, cur))
                            for i, (lbl, vals, cur) in enumerate(self.menu_items)
                            if lbl != "piece"]

        max_lbl_w = max(
            self.font.render(lbl + ":", True, (0, 0, 0)).get_width()
            for lbl, _, _ in self.menu_items if lbl != "piece")
        minus_x = text_x + max_lbl_w + UI_SPACE
        plus_x  = menu_bounds["right"] - UI_SPACE * 4

        for list_idx, (item_idx, (label, values, cur_idx)) in enumerate(menu_panel_items):
            panel_y = left_panel.get_line_y("MENU_PANEL", list_idx, line_height)
            row_cy  = panel_y + btn_w // 2
            lbl_surf = self.font.render(f"{label}:", True, (0, 0, 0))
            screen.blit(lbl_surf, lbl_surf.get_rect(midleft=(text_x, row_cy)))
            val      = values[cur_idx]
            sel_text = _display_clock(val) if label == "clock" else str(val)
            sel_surf = self.font.render(sel_text, True, (0, 0, 0))
            sel_cx   = (minus_x + btn_w + plus_x + btn_w) / 2
            screen.blit(sel_surf, sel_surf.get_rect(center=(sel_cx, row_cy)))

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

        is_playable = self.get_selection("board") >= self._get_min_board_size(
            self.get_selection("piece"))

        # Enter / cancel share code
        self.buttons["enter_code"].active    = self.game_state == GameState.MENU
        self.buttons["enter_code"].text      = ("cancel code input" if self.seed_mode_active
                                                else "enter share code")
        self.buttons["enter_code"].bg_color  = ((224, 64, 128) if self.seed_mode_active
                                                else (224, 0, 96))
        self.buttons["enter_code"].rect      = left_panel.get_widget_rect(
            "MENU_PANEL", len(menu_panel_items) + 3, BTW, BTH)
        #self.buttons["enter_code"].draw(screen)

        if self.game_state == GameState.MENU and self.seed_mode_active:
            input_y = left_panel.get_line_y("MENU_PANEL", len(menu_panel_items), line_height)
            input_x = menu_bounds["left"] + (menu_bounds["width"] // 2) - BTW * .75
            self.codec_input.rect = pygame.Rect(input_x, input_y + 24, BTW * 1.5, BTH)
            self.codec_input.draw(screen)

        if (self.puzzle_code and self.game_state in (
                GameState.INGAME, GameState.ENDGAME)):
            code_y   = left_panel.get_line_y("MENU_PANEL", len(menu_panel_items), line_height)
            cs2_surf = self.font.render(self.puzzle_code, True, (0, 0, 0))
            screen.blit(cs2_surf, cs2_surf.get_rect(
                center=(menu_bounds["center_x"], code_y + line_height // 2)))
            self.buttons["copy_code"].active    = True
            self.buttons["copy_code"].bg_color  = ((224, 64, 128) if self.copy_clicked
                                                   else (224, 0, 96))
            self.buttons["copy_code"].text      = ("code copied!" if self.copy_clicked
                                                   else "copy share code")
            self.buttons["copy_code"].rect      = left_panel.get_widget_rect(
                "MENU_PANEL", len(menu_panel_items), BTW, BTH)
            self.buttons["copy_code"].draw(screen)
        else:
            self.buttons["copy_code"].active = False

        # ---- BUTTON_PANEL ----
        button_bounds = left_panel.get_bounds("BUTTON_PANEL")

        if self.game_state == GameState.MENU:
            # Blind draw
#            self.buttons["blind_draw"].active = not self.seed_mode_active
#            self.buttons["blind_draw"].rect   = left_panel.get_widget_rect(
#                "MENU_PANEL", len(menu_panel_items) + 1, BTW, BTH)
#            if self.buttons["blind_draw"].active:
#                self.buttons["blind_draw"].draw(screen)

            if not self.seed_mode_active:
                self.buttons["start"].active = is_playable
                self.buttons["start"].rect   = left_panel.get_widget_rect(
                    "BUTTON_PANEL", 0, BTW, BTH)
                self.buttons["start"].draw(screen)
                if not is_playable:
                    mb  = self._get_min_board_size(self.get_selection("piece"))
                    ws  = self.font.render(f"board must be >= {mb}", True, (200, 0, 0))
                    wby = self.buttons["start"].rect.bottom + 4
                    screen.blit(ws, ws.get_rect(
                        centerx=button_bounds["center_x"], top=wby))
            elif self._is_valid_codec_length():
                self.buttons["start"].active = True
                self.buttons["start"].rect   = left_panel.get_widget_rect(
                    "BUTTON_PANEL", 0, BTW, BTH)
                self.buttons["start"].draw(screen)
            else:
                self.buttons["start"].active = False

            self.buttons["guide_mode"].active = True
            self.buttons["guide_mode"].text   = ("hide move guide" if self.guide_mode_active
                                                 else "show move guide")
            self.buttons["guide_mode"].rect   = left_panel.get_widget_rect(
                "BUTTON_PANEL", 2, BTW, BTH)
            self.buttons["guide_mode"].draw(screen)

            self.buttons["track_mode"].active = True
            self.buttons["track_mode"].text   = ("hide move track" if self.track_mode_active
                                                 else "show move track")
            self.buttons["track_mode"].rect   = left_panel.get_widget_rect(
                "BUTTON_PANEL", 4, BTW, BTH)

        elif self.game_state == GameState.INGAME:
            for k in ("start", "new_game", "retry", "replay_mode",
                      "replay_prev", "replay_next"):
                self.buttons[k].active = False

            self.buttons["guide_mode"].active = True
            self.buttons["guide_mode"].text   = ("hide move guide" if self.guide_mode_active
                                                 else "show move guide")
            self.buttons["guide_mode"].rect   = left_panel.get_widget_rect(
                "BUTTON_PANEL", 2, BTW, BTH)
            self.buttons["guide_mode"].draw(screen)

            self.buttons["track_mode"].active = True
            self.buttons["track_mode"].text   = ("hide move track" if self.track_mode_active
                                                 else "show move track")
            self.buttons["track_mode"].rect   = left_panel.get_widget_rect(
                "BUTTON_PANEL", 4, BTW, BTH)
            self.buttons["track_mode"].draw(screen)

            can_undo = (self.game_state == GameState.INGAME
                        and len(self.replay_states) > 1
                        and not self.bot_move_pending)
            self.buttons["undo_mode"].active = can_undo
            self.buttons["undo_mode"].rect   = left_panel.get_widget_rect(
                "BUTTON_PANEL", 6, BTW, BTH)
            if can_undo:
                self.buttons["undo_mode"].draw(screen)

            self.buttons["resign"].active = self.game_state == GameState.INGAME
            self.buttons["resign"].rect   = left_panel.get_widget_rect(
                "BUTTON_PANEL", 8, BTW, BTH)
            if self.buttons["resign"].active:
                self.buttons["resign"].draw(screen)

        elif self.game_state == GameState.ENDGAME:
            for k in ("resign", "undo_mode"):
                self.buttons[k].active = False

            self.buttons["guide_mode"].active = True
            self.buttons["guide_mode"].text   = ("hide move guide" if self.guide_mode_active
                                                 else "show move guide")
            self.buttons["guide_mode"].rect   = left_panel.get_widget_rect(
                "BUTTON_PANEL", 2, BTW, BTH)
            self.buttons["guide_mode"].draw(screen)

            self.buttons["track_mode"].active = True
            self.buttons["track_mode"].text   = ("hide move track" if self.track_mode_active
                                                 else "show move track")
            self.buttons["track_mode"].rect   = left_panel.get_widget_rect(
                "BUTTON_PANEL", 4, BTW, BTH)
            self.buttons["track_mode"].draw(screen)

            self.buttons["replay_mode"].active = True
            self.buttons["replay_mode"].text   = ("end replay" if self.replay_mode_active
                                                  else "start replay")
            self.buttons["replay_mode"].rect   = left_panel.get_widget_rect(
                "BUTTON_PANEL", 6, BTW, BTH)
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

            self.buttons["retry"].active = self.last_puzzle_seed is not None
            self.buttons["retry"].rect   = left_panel.get_widget_rect(
                "MENU_PANEL", len(menu_panel_items) + 1, BTW, BTH)
            if self.buttons["retry"].active:
                self.buttons["retry"].draw(screen)

            self.buttons["new_game"].active = True
            self.buttons["new_game"].rect   = left_panel.get_widget_rect(
                "BUTTON_PANEL", 8, BTW, BTH)
            self.buttons["new_game"].draw(screen)

        # Peek button (INGAME or ENDGAME, bottom left)
        if self.game_state in (GameState.INGAME, GameState.ENDGAME) and self.maze_path is not None:
            self.buttons["peek_mode"].active = True
            self.buttons["peek_mode"].text   = "hide" if self.peek_mode_visible else "peek"
            self.buttons["peek_mode"].rect   = pygame.Rect(
                msg_left + UI_SPACE * 3, msg_bottom - UI_SPACE * 5, BTW // 2, BTH)
            self.buttons["peek_mode"].draw(screen)
        else:
            self.buttons["peek_mode"].active = False

        # Exit button (always)
        self.buttons["exit"].rect = pygame.Rect(
            msg_right - UI_SPACE * 10, msg_bottom - int(UI_SPACE * 5), BTW // 2, BTH)
        self.buttons["exit"].draw(screen)

    # ================================================================== #
    #  Right-panel rendering                                              #
    # ================================================================== #

    def _render_right_panel(
        self, screen: pygame.Surface, right_panel: UIPanel,
    ) -> None:
        btn_w       = UI_SPACE
        line_height = self.font.get_linesize() + UI_SPACE

        # ---- PIECE_PANEL ----
        piece_bounds = right_panel.get_bounds("PIECE_PANEL")
        right_tx     = piece_bounds["left"] + UI_SPACE

        piece_idx                = self.label_to_index["piece"]
        _, piece_vals, piece_cur = self.menu_items[piece_idx]
        piece_name               = piece_vals[piece_cur]

        p_line_y = right_panel.get_line_y("PIECE_PANEL", 0, line_height)
        p_row_cy = p_line_y + btn_w // 2
        lbl_s    = self.font.render("piece:", True, (0, 0, 0))
        p_minus_x = lbl_s.get_rect(midleft=(right_tx, p_row_cy)).right + UI_SPACE
        p_plus_x  = piece_bounds["right"] - UI_SPACE * 4

        sel_s = self.font_large.render(piece_name, True, (0, 0, 0))
        screen.blit(sel_s, sel_s.get_rect(
            center=(piece_bounds["center_x"], p_row_cy + 8)))

        if self.game_state == GameState.MENU:
            pm_r = pygame.Rect(p_minus_x - btn_w, p_line_y,
                               int(btn_w * 1.5), int(btn_w * 1.5))
            pygame.draw.rect(screen, DK_SQUARE, pm_r)
            screen.blit(self.font.render("<", True, (0, 160, 0)),
                        self.font.render("<", True, (0, 160, 0)).get_rect(center=pm_r.center))
            self.widget_rects[("minus", piece_idx)] = pm_r

            pp_r = pygame.Rect(p_plus_x - btn_w, p_line_y,
                               int(btn_w * 1.5), int(btn_w * 1.5))
            pygame.draw.rect(screen, DK_SQUARE, pp_r)
            screen.blit(self.font.render(">", True, (220, 0, 0)),
                        self.font.render(">", True, (220, 0, 0)).get_rect(center=pp_r.center))
            self.widget_rects[("plus", piece_idx)] = pp_r

        move_text = pk.get_piece_move_sets_text(piece_name)
        info_y    = p_line_y + sel_s.get_height() + line_height
        if move_text:
            mt_s = self.font.render(move_text, True, (80, 80, 80))
            screen.blit(mt_s, mt_s.get_rect(
                centerx=piece_bounds["center_x"], top=info_y))
            info_y += self.font.get_linesize() + UI_SPACE

        is_playable = self.get_selection("board") >= self._get_min_board_size(piece_name)
        if self.game_state == GameState.MENU and not is_playable:
            mb     = self._get_min_board_size(piece_name)
            warn_s = self.font.render("use a larger board for this piece", True, (160, 0, 0))
            screen.blit(warn_s, warn_s.get_rect(
                centerx=piece_bounds["center_x"], top=info_y))

        # ---- STATS_PANEL ----
        self._render_game_specific_stats(screen, right_panel)

    # ================================================================== #
    #  Full-frame render                                                  #
    # ================================================================== #

    def render(self, screen: pygame.Surface) -> None:
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

        area_left   = msg_right + margin
        area_top    = margin
        area_right  = right_left - margin
        area_bottom = win_height - margin

        brd = self.get_selection("board")
        if self.game_state == GameState.MENU:
            if self.board_model.cols != brd or self.board_model.rows != brd:
                self.board_model.cols = brd
                self.board_model.rows = brd
                self.board_model.clear()

        self._update_cell_size(area_left, area_top,
                               area_right - area_left, area_bottom - area_top)
        self.board_renderer.draw_background(screen)
        self.widget_rects.clear()

        if self.current_cell_size > 0:
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
            ex = area_left + (aw - es.get_width())  // 2
            ey = area_top  + (ah - es.get_height()) // 2
            pygame.draw.rect(screen, (255, 240, 240),
                             (ex - 8, ey - 6, es.get_width() + 16, es.get_height() + 12))
            screen.blit(es, (ex, ey))
        elif self.error_message and pygame.time.get_ticks() >= self.error_timer:
            self.error_message = ""

        self._render_left_panel(screen, left_panel, msg_left, msg_right, msg_bottom)
        self._render_right_panel(screen, right_panel)

    # ================================================================== #
    #  Event handling                                                     #
    # ================================================================== #

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not super().handle_event(event):
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            for key, rect in self.widget_rects.items():
                if rect.collidepoint(mx, my):
                    action, item_idx = key
                    lbl, vals, cur   = self.menu_items[item_idx]
                    if action == "plus":
                        self.menu_items[item_idx] = (lbl, vals, (cur + 1) % len(vals))
                    elif action == "minus":
                        self.menu_items[item_idx] = (lbl, vals, (cur - 1) % len(vals))
                    if lbl in ("board", "length"):
                        self.menu_preview_cache = None
                    elif lbl == "piece":
                        self.menu_preview_pos = None
                    break

            if self.game_state == GameState.INGAME:
                if not self._is_bot_turn():
                    grid_pos = self.board_renderer.to_grid(mx, my)
                    if grid_pos is not None:
                        self.make_move(grid_pos)

            elif self.game_state == GameState.MENU:
                grid_pos = self.board_renderer.to_grid(mx, my)
                if grid_pos is not None:
                    self.menu_preview_pos = grid_pos

        return True