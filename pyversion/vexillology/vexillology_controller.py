"""
vexillology_controller.py

Game controller for Vexillology v0.1 – a two-player competitive flag-capture game.

Two players take alternating turns navigating a shared board.  The first
player to collect the majority of flags wins.  The game ends when neither
player can make a legal move.

The controller closely mirrors vexillum_controller.py and borrows
the two-player game-flow machinery from duelomino_controller.py.
"""

import os
import time
import math
import random
from collections import deque

import pygame
from typing import Optional, List, Tuple, Set, Dict, Any

# sharedlib imports (BASE_DIR must already be on sys.path)
import piecekeeper as pk
from gameboard import BoardModel, BoardRenderer
from uipanel import UIPanel
from puzzle_codec import encode_params, decode_params
from widgets import Button
from move_system import get_legal_moves_for_board
from move_hint import calculate_hint_degrees
from base_game_controller import BaseGameController, GameState

from pyversion.vexillology.vexillum_generator import generate_open_path_with_flags

# ------------------------------------------------------------------ #
#  Shared constants                                                    #
# ------------------------------------------------------------------ #

BOARD_MIN         = 5
BOARD_MAX         = 16
BOARD_DEFAULT     = 8
FPS               = 60
UI_SPACE          = 10
BTW               = int(UI_SPACE * 15)
BTH               = int(UI_SPACE * 3)
CODEC_TEXT_LENGTH = 16
MAX_CLOCK_SECONDS = 300
CLOCK_MODES = ["game", "move"]

PATH_LENGTH_CHOICES = ["short", "medium", "long", "super"]
PATH_LENGTH_MAP     = {"short": 2, "medium": 3, "long": 4, "super": 6}

FLAG_DENSITY_CHOICES = ["low", "medium", "high"]
FLAG_DENSITY_MAP     = {"low": 0.1, "medium": 0.25, "high": 0.6}

FLAG_ORDER_CHOICES = ["any", "only", "next"]

PLAYER_ONE_CHOICES    = ["human", "bot"]
OPPONENT_LEVEL_CHOICES = ["1", "2", "3"]

# Board colours
LT_SQUARE  = (255, 255, 240)
DK_SQUARE  = (232, 200, 150)
LT_VISITED = (224, 224, 224)
DK_VISITED = (192, 192, 192)
GRID_COLOR = (107, 70, 51)
BACK_COLOR = (244, 228, 195)
FLAG_SQ_DK = (128, 160, 225)
FLAG_SQ_LT = (192, 220, 248)
FLAG_ONLY_INORDER = (0x1e, 0x64, 0xdc)

# Player colours
P1_LT_VISITED = (192, 220, 248)   # blue – light squares
P1_DK_VISITED = (128, 160, 225)   # blue – dark squares
P2_LT_VISITED = (255, 192, 192)   # red  – light squares
P2_DK_VISITED = (225, 128, 128)   # red  – dark squares

FLAG_IMG_FALLBACK_COLORS = {
    "blue":   (30,  100, 220),
    "green":  (50,  180,  50),
    "purple": (140,  70, 210),
    "red":    (220,  40,  40),
    "ivory":  (200, 175, 130),
    "tan":    (170, 140,  95),
}

# Bot move delay range (ms)
BOT_MOVE_DELAY_MIN = 500
BOT_MOVE_DELAY_MAX = 800

# Even-parity pieces that cannot complete a full Hamiltonian tour
EXCLUDED_PIECES = {"bishop", "ferz", "dabbaba", "alfil", "threeleaper", "tripper", "camel"}

vexillology_schema = [
    ("board",        4, lambda v: int(v) - BOARD_MIN),
    ("path_length",  2, {"short": 0, "medium": 1, "long": 2}),
    ("flag_density", 2, {"low":   0, "medium": 1, "high":  2}),
    ("flag_order",   2, {"any":   0, "only":   1, "next":  2}),
]


# ------------------------------------------------------------------ #
#  Utility helpers                                                     #
# ------------------------------------------------------------------ #

def get_globally_valid_pieces() -> List[str]:
    """Return piece names valid for any board size (excluding even-parity pieces)."""
    return [p for p in pk.PIECE_LIST if p not in EXCLUDED_PIECES]


def _format_clock_seconds(seconds) -> str:
    if seconds is None:
        seconds = 0
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def _display_for_selection(clock_selected) -> str:
    if clock_selected == 0:
        return "infinity"
    return _format_clock_seconds(clock_selected)


# ------------------------------------------------------------------ #
#  VexillologyController                                              #
# ------------------------------------------------------------------ #

class VexillologyController(BaseGameController):
    """Two-player flag-capture game controller for Vexillology v0.1."""

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
            font, font_large, base_dir, vexillology_schema,
        )

        # Override base class mode defaults
        self.guide_mode_active = False
        self.track_mode_active = False

        # Shared flag state
        self.flags_dir    = os.path.join(base_dir, "assets", "flags")
        self.path:  List[Tuple[int, int]]              = []
        self.flags: List[Tuple[int, int]]              = []
        self.flags_set:   Set[Tuple[int, int]]         = set()
        self.flags_index: Dict[Tuple[int, int], int]   = {}
        self.flag_images: Dict[str, Optional[pygame.Surface]] = {}

        # Per-player state
        self.player1_pos:           Optional[Tuple[int, int]] = None
        self.player2_pos:           Optional[Tuple[int, int]] = None
        self.player1_visited:       Set[Tuple[int, int]]      = set()
        self.player2_visited:       Set[Tuple[int, int]]      = set()
        self.player1_visited_moves: Dict[Tuple[int, int], int] = {}
        self.player2_visited_moves: Dict[Tuple[int, int], int] = {}
        self.player1_legal_moves:   List[Tuple[int, int]]     = []
        self.player2_legal_moves:   List[Tuple[int, int]]     = []

        # Per-player flag capture tracking
        self.player1_flags:          Set[Tuple[int, int]] = set()
        self.player2_flags:          Set[Tuple[int, int]] = set()
        self.player1_flags_in_order: Set[Tuple[int, int]] = set()
        self.player1_flags_out_of_order: Set[Tuple[int, int]] = set()
        self.player2_flags_in_order: Set[Tuple[int, int]] = set()
        self.player2_flags_out_of_order: Set[Tuple[int, int]] = set()

        # Turn tracking
        self.current_player:   int  = 1
        self.endgame_reason:   Optional[str] = None

        # Bot scheduling
        self.bot_move_pending: bool = False
        self.bot_move_timer:   int  = 0
        self.bot_offers_resignation: bool = False

        # Per-move clock tracking
        self.move_start_time: Optional[float] = None

        # Playability state (cached, updated when board or piece changes)
        self.is_piece_playable: bool     = True
        self.min_board_size:    Optional[int] = None

        # Preview cache for MENU state
        self.menu_preview_cache = None
        self.preview_pos: Optional[Tuple[int, int]] = None

        self._load_flag_images(36)
        self.update_playability()

    # ================================================================== #
    #  Abstract method implementations                                    #
    # ================================================================== #

    def _get_min_board_size(self, piece_name: str) -> int:
        """Return the minimum board size on which piece_name can reach every square."""
        move_func = pk.get_move_func(piece_name)
        for size in range(BOARD_MIN, BOARD_MAX + 1):
            if not any(move_func(x, y, size) for y in range(size) for x in range(size)):
                continue
            q = deque([(0, 0)])
            reachable = {(0, 0)}
            while q:
                cx, cy = q.popleft()
                for mv in move_func(cx, cy, size):
                    if mv not in reachable:
                        reachable.add(mv)
                        q.append(mv)
            if len(reachable) == size * size:
                return size
        return BOARD_MAX

    def update_playability(self) -> None:
        """Check if current piece is playable on the current board size."""
        board_size = self.get_selection("board")
        piece_name = self.get_selection("piece")
        min_b = self._get_min_board_size(piece_name)
        self.is_piece_playable = (board_size >= min_b)
        self.min_board_size = min_b if not self.is_piece_playable else None

    def _get_encode_params(self) -> Dict[str, Any]:
        return {
            "board":        self.get_selection("board"),
            "path_length":  self.get_selection("path length"),
            "flag_density": self.get_selection("flag density"),
            "flag_order":   self.get_selection("flag order"),
        }

    def _validate_codec(self, codec_text: str) -> Tuple[bool, Optional[Dict]]:
        try:
            params    = decode_params(codec_text, vexillology_schema)
            board_val = params.get("board", 0) + BOARD_MIN
            if not (BOARD_MIN <= board_val <= BOARD_MAX):
                return False, None
            path_len = params.get("path_length")
            flag_den = params.get("flag_density")
            flag_ord = params.get("flag_order")
            if path_len not in PATH_LENGTH_CHOICES: return False, None
            if flag_den not in FLAG_DENSITY_CHOICES: return False, None
            if flag_ord not in FLAG_ORDER_CHOICES:   return False, None

            def _apply(label, value):
                idx = self.label_to_index[label]
                lbl, vals, _ = self.menu_items[idx]
                if value in vals:
                    self.menu_items[idx] = (lbl, vals, vals.index(value))

            _apply("board",        board_val)
            _apply("path length",  path_len)
            _apply("flag density", flag_den)
            _apply("flag order",   flag_ord)
            return True, {**params, "board": board_val}
        except Exception:
            return False, None

    def _game_specific_start_setup(self, seed: Optional[int] = None) -> bool:
        board_size   = self.get_selection("board")
        piece_name   = self.get_selection("piece")
        path_length  = self.get_selection("path length")
        flag_density = self.get_selection("flag density")

        move_func  = pk.get_move_func(piece_name)
        multiplier = PATH_LENGTH_MAP[path_length]
        min_length = max(board_size, int(board_size * multiplier))
        max_length = min(board_size * board_size, int(board_size * multiplier * 2))

        path, flags_list = generate_open_path_with_flags(
            board_size, min_length, max_length, move_func,
            max_attempts=500, time_budget=2.0,
            flag_density_choice=flag_density, seed=seed,
        )

        if not path or len(path) < 4:
            return False

        # Always enforce an odd number of flags
        rng = random.Random(seed)
        if len(flags_list) % 2 == 0:
            used_set = set(flags_list)
            extras = [p for p in path if p not in used_set]
            if extras:
                flags_list.append(rng.choice(extras))
            elif len(flags_list) > 1:
                flags_list.pop(0)

        # Final safety check: must still be odd and ≥ 1
        if len(flags_list) % 2 == 0 and len(flags_list) > 0:
            flags_list.pop(0)

        if not flags_list:
            return False

        self.path        = path
        self.flags       = flags_list
        self.flags_set   = set(flags_list)
        self.flags_index = {pos: i for i, pos in enumerate(flags_list)}

        # Reset per-player state
        self.player1_pos                = None
        self.player2_pos                = None
        self.player1_visited            = set()
        self.player2_visited            = set()
        self.player1_visited_moves      = {}
        self.player2_visited_moves      = {}
        self.player1_flags              = set()
        self.player2_flags              = set()
        self.player1_flags_in_order     = set()
        self.player1_flags_out_of_order = set()
        self.player2_flags_in_order     = set()
        self.player2_flags_out_of_order = set()
        self.current_player             = 1
        self.move_count                 = 0
        self.bot_move_pending           = False
        self.bot_offers_resignation     = False
        self.endgame_reason             = None

        # Sync base class single-player state to player 1
        self.player_pos    = None
        self.visited       = set()
        self.visited_moves = {}

        self.player1_legal_moves = []
        self.player2_legal_moves = []
        self.legal_moves         = []

        # Reset mode flags on game start
        self.guide_mode_active = False
        self.hint_mode_active  = False

        return True

    def _validate_move(self, target: Tuple[int, int]) -> bool:
        if self.current_player == 1:
            return target in self.player1_legal_moves
        return target in self.player2_legal_moves

    def _game_specific_make_move(self, target: Tuple[int, int]) -> bool:
        """Not used directly; logic is in make_move() override."""
        return True

    def _check_endgame_conditions(self) -> Optional[str]:
        p1_stuck = not self.player1_legal_moves
        p2_stuck = not self.player2_legal_moves
        if p1_stuck and p2_stuck:
            n1 = len(self.player1_flags)
            n2 = len(self.player2_flags)
            if n1 > n2:
                return "player1_wins"
            elif n2 > n1:
                return "player2_wins"
            else:
                return "draw"
        return None

    def _capture_game_state(self) -> Dict[str, Any]:
        return {
            "current_player":             self.current_player,
            "player1_pos":                self.player1_pos,
            "player2_pos":                self.player2_pos,
            "player1_visited":            self.player1_visited.copy(),
            "player2_visited":            self.player2_visited.copy(),
            "player1_visited_moves":      self.player1_visited_moves.copy(),
            "player2_visited_moves":      self.player2_visited_moves.copy(),
            "player1_flags":              self.player1_flags.copy(),
            "player2_flags":              self.player2_flags.copy(),
            "player1_flags_in_order":     self.player1_flags_in_order.copy(),
            "player1_flags_out_of_order": self.player1_flags_out_of_order.copy(),
            "player2_flags_in_order":     self.player2_flags_in_order.copy(),
            "player2_flags_out_of_order": self.player2_flags_out_of_order.copy(),
            "move_count":                 self.move_count,
        }

    def _restore_game_state(self, state: Dict[str, Any]) -> None:
        self.current_player             = state.get("current_player", 1)
        self.player1_pos                = state.get("player1_pos")
        self.player2_pos                = state.get("player2_pos")
        self.player1_visited            = state.get("player1_visited", set()).copy()
        self.player2_visited            = state.get("player2_visited", set()).copy()
        self.player1_visited_moves      = state.get("player1_visited_moves", {}).copy()
        self.player2_visited_moves      = state.get("player2_visited_moves", {}).copy()
        self.player1_flags              = state.get("player1_flags", set()).copy()
        self.player2_flags              = state.get("player2_flags", set()).copy()
        self.player1_flags_in_order     = state.get("player1_flags_in_order", set()).copy()
        self.player1_flags_out_of_order = state.get("player1_flags_out_of_order", set()).copy()
        self.player2_flags_in_order     = state.get("player2_flags_in_order", set()).copy()
        self.player2_flags_out_of_order = state.get("player2_flags_out_of_order", set()).copy()
        self.move_count                 = state.get("move_count", 0)
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
        self.hint_degrees = calculate_hint_degrees(
            piece_name, cur_pos, n, n, all_visited
        )

    def _render_game_specific_board(self, screen: pygame.Surface) -> None:
        """Delegated to _render_board_area() below."""
        pass

    def _render_game_specific_stats(
        self, screen: pygame.Surface, stats_panel: UIPanel
    ) -> None:
        """Stats are rendered inside _render_right_panel()."""
        pass

    def _build_buttons(self) -> None:
        f = self.font
        self.buttons: Dict[str, Button] = {
            "start":       Button(pygame.Rect(0,0,0,0), "start",
                                  f, (255,255,255), (92,192,92),   self.start_game),
            "enter_code":  Button(pygame.Rect(0,0,0,0), "enter share code",
                                  f, (255,255,255), (224,0,96),    self.toggle_codec_input),
            "copy_code":   Button(pygame.Rect(0,0,0,0), "copy share code",
                                  f, (255,255,255), (224,0,96),    self.copy_code_to_clipboard),
            "guide_mode":  Button(pygame.Rect(0,0,0,0), "show move guide",
                                  f, (255,255,255), (128,64,255),  self.toggle_guide_mode),
            "track_mode":  Button(pygame.Rect(0,0,0,0), "show move track",
                                  f, (255,255,255), (255,92,128),  self.toggle_track_mode),
            "hint_mode":   Button(pygame.Rect(0,0,0,0), "show degrees",
                                  f, (255,255,255), (255,128,96),  self.toggle_hint_mode),
            "undo_mode":   Button(pygame.Rect(0,0,0,0), "undo last move",
                                  f, (255,255,255), (64,128,255),  self.undo_move),
            "resign":      Button(pygame.Rect(0,0,0,0), "resign",
                                  f, (255,255,255), (107, 50, 71), self.resign_game),
            "accept_resignation": Button(pygame.Rect(0,0,0,0), "accept",
                                  f, (255,255,255), (107, 50, 71), self.accept_bot_resignation),
            "retry":       Button(pygame.Rect(0,0,0,0), "retry",
                                  f, (255,255,255), (92,192,92),   self.retry_game),
            "replay_mode": Button(pygame.Rect(0,0,0,0), "start replay",
                                  f, (255,255,255), (64,128,255),  self.toggle_replay_mode),
            "replay_prev": Button(pygame.Rect(0,0,0,0), "-",
                                  f, (255,255,240), (64,128,255),  lambda: self.navigate_replay(-1)),
            "replay_next": Button(pygame.Rect(0,0,0,0), "+",
                                  f, (255,255,240), (64,128,255),  lambda: self.navigate_replay(1)),
            "peek_mode":   Button(pygame.Rect(0,0,0,0), "peek",
                                  f, (255,255,240), LT_SQUARE,     self.toggle_peek),
            "new_game":    Button(pygame.Rect(0,0,0,0), "new game",
                                  f, (255,255,255), (32,128,96),   self.new_game),
            "exit":        Button(pygame.Rect(0,0,0,0), "exit",
                                  f, (255,255,255), (220,40,40),   self.quit_game),
        }

    # ================================================================== #
    #  Two-player move mechanics                                          #
    # ================================================================== #

    def _update_all_legal_moves(self) -> None:
        piece_name  = self.get_selection("piece")
        n           = self.board_model.cols
        all_visited = self.player1_visited | self.player2_visited

        if self.player1_pos is not None:
            self.player1_legal_moves = get_legal_moves_for_board(
                piece_name, *self.player1_pos, n, n, all_visited
            )
        else:
            self.player1_legal_moves = []

        if self.player2_pos is not None:
            self.player2_legal_moves = get_legal_moves_for_board(
                piece_name, *self.player2_pos, n, n, all_visited
            )
        else:
            self.player2_legal_moves = []

        self.legal_moves = (
            self.player1_legal_moves if self.current_player == 1
            else self.player2_legal_moves
        )

    def _sync_base_state(self) -> None:
        if self.current_player == 1:
            self.player_pos    = self.player1_pos
            self.visited       = self.player1_visited
            self.visited_moves = self.player1_visited_moves
            self.legal_moves   = self.player1_legal_moves
        else:
            self.player_pos    = self.player2_pos
            self.visited       = self.player2_visited
            self.visited_moves = self.player2_visited_moves
            self.legal_moves   = self.player2_legal_moves

    def _apply_flag_capture(self, player: int, target: Tuple[int, int]) -> None:
        """Record flag capture for a player, tracking in/out-of-order status."""
        if target not in self.flags_set:
            return
        all_flags_reached = self.player1_flags | self.player2_flags
        if target in all_flags_reached:
            return  # Already captured by someone

        flag_order_mode = self.get_selection("flag order")
        if player == 1:
            own_flags = self.player1_flags
            own_in    = self.player1_flags_in_order
            own_out   = self.player1_flags_out_of_order
        else:
            own_flags = self.player2_flags
            own_in    = self.player2_flags_in_order
            own_out   = self.player2_flags_out_of_order

        own_flags.add(target)

        if flag_order_mode == "next":
            target_idx = self.flags_index[target]
            # Determine what the global next index was before this capture
            global_next = next(
                (i for i, f in enumerate(self.flags) if f not in all_flags_reached),
                -1
            )
            if target_idx == global_next:
                own_in.add(target)
            else:
                own_out.add(target)
        elif flag_order_mode == "only":
            all_captured = self.player1_flags | self.player2_flags
            global_next = next(
                (i for i, f in enumerate(self.flags) if f not in all_captured),
                -1
            )
            if self.flags_index[target] == global_next:
                own_in.add(target)
            else:
                own_out.add(target)
        # "any" mode: no order tracking needed

    def _apply_move(self, player: int, target: Tuple[int, int]) -> None:
        if player == 1:
            self.player1_pos = target
            self.player1_visited.add(target)
            self.player1_visited_moves[target] = len(self.player1_visited)
            self._apply_flag_capture(1, target)
        else:
            self.player2_pos = target
            self.player2_visited.add(target)
            self.player2_visited_moves[target] = len(self.player2_visited)
            self._apply_flag_capture(2, target)

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

        self._apply_move(self.current_player, target_pos)

        # Per-move clock reset
        if self._is_per_move_mode():
            self.clock_start_time = None
            if self.game_state == GameState.INGAME:
                self.move_start_time = time.time()

        # Snapshot for replay/undo
        self.replay_states.append(self._capture_game_state())

        # Check win/draw
        end_condition = self._check_endgame_conditions()
        if end_condition:
            self._go_to_endgame(end_condition)
            return

        # Switch player (with continuation rule: skip if other has no moves)
        other       = 3 - self.current_player
        other_moves = (self.player1_legal_moves if other == 1
                       else self.player2_legal_moves)
        if other_moves:
            self.current_player = other

        self._sync_base_state()

        # Check bot resignation offer
        if self._check_bot_resignation_condition():
            self.bot_offers_resignation = True

        if self.hint_mode_active:
            self._calculate_hint_degrees()
        else:
            self.hint_degrees = {}

        if self._is_bot_turn():
            self._schedule_bot_move()

    def commit_start_square(self, start_pos: Tuple[int, int]) -> None:
        """Place a piece for the current player during WAITING phase."""
        if self.game_state != GameState.WAITING:
            return
        # Flags are blocked as starting squares
        if start_pos in self.flags_set:
            return

        player_one = self.get_selection("first move")

        if self.player1_pos is None:
            # Player 1 picks first
            self.player1_pos = start_pos
            self.player1_visited.add(start_pos)
            self.player1_visited_moves[start_pos] = 1

            if player_one == "human":
                # P2 is the bot – auto-commit its start square
                rng = random.Random(self.last_puzzle_seed)
                n   = self.board_model.cols
                candidates = [
                    (x, y) for x in range(n) for y in range(n)
                    if (x, y) not in self.flags_set and (x, y) != start_pos
                ]
                if candidates:
                    bot_start = rng.choice(candidates)
                    self.player2_pos = bot_start
                    self.player2_visited.add(bot_start)
                    self.player2_visited_moves[bot_start] = 1
                else:
                    self.player2_pos = start_pos  # fallback (unlikely)
            else:
                # P1 is bot, P2 (human) still needs to choose → keep WAITING
                self._update_all_legal_moves()
                return

        elif self.player2_pos is None:
            # P2 (human) selects their start square
            if start_pos in self.player1_visited:
                return  # can't share a square
            self.player2_pos = start_pos
            self.player2_visited.add(start_pos)
            self.player2_visited_moves[start_pos] = 1

        # Both squares chosen – enter INGAME
        self.move_count = len(self.player1_visited) + len(self.player2_visited)
        self._update_all_legal_moves()
        self._sync_base_state()

        self.game_state        = GameState.INGAME
        self.clock_start_time  = time.time()
        self.replay_states     = [self._capture_game_state()]
        self.replay_index      = 0
        self.move_start_time   = time.time() if self._is_per_move_mode() else None

        if self.hint_mode_active:
            self._calculate_hint_degrees()

        if self._is_bot_turn():
            self._schedule_bot_move()

    # ================================================================== #
    #  Clock helpers                                                      #
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
            elapsed = time.time() - self.move_start_time
            return max(0, math.ceil(clock_sel - elapsed))
        elapsed = self.final_elapsed if self.game_state == GameState.ENDGAME else self.clock_elapsed
        return max(0, int(clock_sel) - int(elapsed))

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
        self.bot_move_timer   = pygame.time.get_ticks() + delay
        self.bot_move_pending = True

    def _execute_bot_move(self) -> None:
        self.bot_move_pending = False
        if self.game_state != GameState.INGAME:
            return

        bot_player = self.current_player
        bot_pos    = self.player1_pos if bot_player == 1 else self.player2_pos
        if bot_pos is None:
            return

        # Lazy import to avoid circular dependency at module load time
        from pyversion.vexillology.vexillology_bot import BotLevel, make_bot_move as _bot_move

        level_str = self.get_selection("level")
        try:
            level = BotLevel(level_str)
        except ValueError:
            level = BotLevel.LEVEL_1

        piece_name   = self.get_selection("piece")
        board_size   = self.board_model.cols
        all_visited  = self.player1_visited | self.player2_visited
        all_captured = self.player1_flags | self.player2_flags
        uncaptured   = self.flags_set - all_captured
        opponent_pos = (self.player2_pos if bot_player == 1 else self.player1_pos)

        chosen = _bot_move(
            level, piece_name, bot_pos, board_size, all_visited,
            uncaptured, opponent_pos
        )
        if chosen is not None:
            self.make_move(chosen)

    def _check_bot_resignation_condition(self) -> bool:
        """Bot offers to resign when the human has already secured the majority of flags."""
        player_one = self.get_selection("first move")
        if player_one == "human":
            human_flags = len(self.player1_flags)
        else:
            human_flags = len(self.player2_flags)

        majority = len(self.flags) // 2 + 1  # strict majority (flags is odd, so this is exact)
        return human_flags >= majority

    # ================================================================== #
    #  Game control overrides                                             #
    # ================================================================== #

    def start_game(self, use_seed: Optional[int] = None) -> None:
        board_size = self.get_selection("board")
        piece_name = self.get_selection("piece")
        min_board  = self._get_min_board_size(piece_name)
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
                seed = params.get("seed", random.randint(0, 2**63 - 1))
            else:
                self.error_message = "Invalid share code"
                self.error_timer   = pygame.time.get_ticks() + 3000
                return
        else:
            seed = random.randint(0, 2**63 - 1)

        self.last_puzzle_seed = seed

        if not self._game_specific_start_setup(seed):
            self.error_message = "Failed to generate flags"
            self.error_timer   = pygame.time.get_ticks() + 3000
            return

        n = self.get_selection("board")
        self.board_model.cols = n
        self.board_model.rows = n
        self.board_model.clear()

        try:
            self.puzzle_code = encode_params(self._get_encode_params(), vexillology_schema, seed)
        except Exception:
            self.puzzle_code = ""

        # Pre-commit bot player 1's start square if P1 is the bot
        player_one = self.get_selection("first move")
        if player_one == "bot":
            rng = random.Random(seed)
            candidates = [
                (x, y) for x in range(n) for y in range(n)
                if (x, y) not in self.flags_set
            ]
            bot_start = rng.choice(candidates) if candidates else (0, 0)
            self.player1_pos = bot_start
            self.player1_visited.add(bot_start)
            self.player1_visited_moves[bot_start] = 1

        self.end_state        = None
        self.endgame_reason   = None
        self.clock_start_time = None
        self.paused_elapsed   = 0.0
        self.clock_elapsed    = 0
        self.final_elapsed    = 0
        self.replay_states    = []
        self.replay_index     = 0
        self.replay_mode_active  = False
        self.peek_mode_visible   = False
        self.hint_degrees        = {}
        self.bot_offers_resignation = False

        self.game_state = GameState.WAITING

    def update(self, dt: int) -> None:
        super().update(dt)

        if self.game_state == GameState.INGAME:
            if self._is_per_move_mode() and self.move_start_time is not None:
                clock_sel = self.get_selection("clock")
                if time.time() - self.move_start_time >= clock_sel:
                    self.final_elapsed = int(time.time() - self.move_start_time)
                    self._go_to_endgame("timeout")
                    return

            if self.bot_move_pending and pygame.time.get_ticks() >= self.bot_move_timer:
                self._execute_bot_move()

    def resign_game(self) -> None:
        if self.game_state != GameState.INGAME:
            return
        self.bot_move_pending = False
        self.final_elapsed    = self._calculate_final_elapsed()
        self._go_to_endgame(f"player{self.current_player}_resignation")

    def accept_bot_resignation(self) -> None:
        if self.game_state != GameState.INGAME or not self.bot_offers_resignation:
            return
        self.bot_move_pending = False
        self.final_elapsed    = self._calculate_final_elapsed()
        player_one = self.get_selection("first move")
        bot_player = 2 if player_one == "human" else 1
        self.bot_offers_resignation = False
        self._go_to_endgame(f"player{bot_player}_resignation")

    def new_game(self) -> None:
        super().new_game()
        self.preview_pos            = None
        self.path                   = []
        self.move_start_time        = None
        self.player1_pos            = None
        self.player2_pos            = None
        self.player1_visited        = set()
        self.player2_visited        = set()
        self.player1_visited_moves  = {}
        self.player2_visited_moves  = {}
        self.player1_legal_moves    = []
        self.player2_legal_moves    = []
        self.player1_flags          = set()
        self.player2_flags          = set()
        self.player1_flags_in_order = set()
        self.player1_flags_out_of_order = set()
        self.player2_flags_in_order = set()
        self.player2_flags_out_of_order = set()
        self.current_player         = 1
        self.bot_move_pending       = False
        self.bot_offers_resignation = False
        self.endgame_reason         = None
        self.menu_preview_cache     = None
        self.hint_degrees           = {}

    def retry_game(self) -> None:
        if self.last_puzzle_seed is not None:
            self.start_game(use_seed=self.last_puzzle_seed)

    def undo_move(self) -> None:
        if self.game_state != GameState.INGAME:
            return
        self.bot_move_pending   = False
        self.bot_offers_resignation = False

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

    def _go_to_endgame(self, reason: str) -> None:
        self.game_state       = GameState.ENDGAME
        self.endgame_reason   = reason
        self.end_state        = reason
        self.bot_move_pending = False
        self.bot_offers_resignation = False
        self.final_elapsed    = self._calculate_final_elapsed()

    def _calculate_final_elapsed(self) -> int:
        if self.clock_start_time is not None:
            return int(self.paused_elapsed + (time.time() - self.clock_start_time))
        return 0

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

    def toggle_hint_mode(self) -> None:
        self.hint_mode_active = not self.hint_mode_active
        if self.hint_mode_active:
            if self.game_state == GameState.INGAME:
                self._calculate_hint_degrees()
        else:
            self.hint_degrees = {}

    # ================================================================== #
    #  Cell size / asset loading                                          #
    # ================================================================== #

    def _update_cell_size(self, area_left, area_top, area_width, area_height) -> None:
        old_cs = self.current_cell_size
        super()._update_cell_size(area_left, area_top, area_width, area_height)
        if self.current_cell_size != old_cs and self.current_cell_size > 0:
            self._load_flag_images(self.current_cell_size)

    def _load_flag_images(self, cell_size: int) -> None:
        flag_img_size = max(8, int(cell_size * 0.68))
        _names = {
            "black":  "flag_black.png",  "blue":   "flag_blue.png",
            "green":  "flag_green.png",  "ivory":  "flag_ivory.png",
            "orange": "flag_orange.png", "purple": "flag_purple.png",
            "red":    "flag_red.png",    "tan":    "flag_tan.png",
            "white":  "flag_white.png",  "yellow": "flag_yellow.png",
        }
        self.flag_images.clear()
        for key, fname in _names.items():
            fpath = os.path.join(self.flags_dir, fname)
            try:
                img = pygame.image.load(fpath).convert_alpha()
                self.flag_images[key] = pygame.transform.smoothscale(
                    img, (flag_img_size, flag_img_size))
            except Exception:
                self.flag_images[key] = None

    def _draw_flag(self, screen: pygame.Surface,
                   img_key: str, px: int, py: int, cs: int) -> None:
        fimg = self.flag_images.get(img_key)
        if fimg:
            screen.blit(fimg, fimg.get_rect(center=(px + cs // 2, py + cs // 2)))
        else:
            fb_color = FLAG_IMG_FALLBACK_COLORS.get(img_key, (128, 128, 128))
            fb_sz    = max(6, int(cs * 0.68))
            pygame.draw.rect(screen, fb_color,
                             (px + (cs - fb_sz) // 2, py + (cs - fb_sz) // 2, fb_sz, fb_sz))

    def _draw_tinted_piece(self, screen: pygame.Surface,
                            rect: pygame.Rect,
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
    #  Board rendering                                                    #
    # ================================================================== #

    def _render_board_area(self, screen: pygame.Surface) -> None:
        """Draw flags, visited squares, arrows, pieces."""
        cs = self.current_cell_size
        if cs <= 0:
            return

        # ---- MENU: preview flags + piece ----
        if self.game_state == GameState.MENU:
            self._render_menu_preview(screen)
            return

        if self.game_state not in (GameState.INGAME, GameState.ENDGAME, GameState.WAITING):
            return

        # Determine display state (replay may differ from live state)
        if self.game_state == GameState.ENDGAME and self.replay_mode_active and self.replay_states:
            snap = self.replay_states[self.replay_index]
            disp_p1_pos    = snap.get("player1_pos")
            disp_p2_pos    = snap.get("player2_pos")
            disp_p1_vis    = snap.get("player1_visited", set())
            disp_p2_vis    = snap.get("player2_visited", set())
            disp_p1_vm     = snap.get("player1_visited_moves", {})
            disp_p2_vm     = snap.get("player2_visited_moves", {})
            disp_p1_flags  = snap.get("player1_flags", set())
            disp_p2_flags  = snap.get("player2_flags", set())
            disp_p1_in     = snap.get("player1_flags_in_order", set())
            disp_p1_out    = snap.get("player1_flags_out_of_order", set())
            disp_p2_in     = snap.get("player2_flags_in_order", set())
            disp_p2_out    = snap.get("player2_flags_out_of_order", set())
            disp_cur       = snap.get("current_player", 1)
        else:
            disp_p1_pos    = self.player1_pos
            disp_p2_pos    = self.player2_pos
            disp_p1_vis    = self.player1_visited
            disp_p2_vis    = self.player2_visited
            disp_p1_vm     = self.player1_visited_moves
            disp_p2_vm     = self.player2_visited_moves
            disp_p1_flags  = self.player1_flags
            disp_p2_flags  = self.player2_flags
            disp_p1_in     = self.player1_flags_in_order
            disp_p1_out    = self.player1_flags_out_of_order
            disp_p2_in     = self.player2_flags_in_order
            disp_p2_out    = self.player2_flags_out_of_order
            disp_cur       = self.current_player

        nf_move = pygame.font.SysFont("arial", max(8, cs // 5))
        all_captured = disp_p1_flags | disp_p2_flags

        # Player 1 visited squares (blue)
        for vx, vy in disp_p1_vis:
            if (vx, vy) == disp_p1_pos:
                continue
            if (vx, vy) in self.flags_set and (vx, vy) not in all_captured:
                continue  # active flag shown separately
            px, py  = self.board_renderer.to_pixel(vx, vy)
            parity  = (vx + vy) % 2
            vcolor  = P1_LT_VISITED if parity == 0 else P1_DK_VISITED
            pygame.draw.rect(screen, vcolor, (px + 3, py + 3, cs - 4, cs - 4))
            if self.track_mode_active and (vx, vy) in disp_p1_vm:
                ns = nf_move.render(str(disp_p1_vm[(vx, vy)]), True, (0, 0, 160))
                screen.blit(ns, ns.get_rect(center=(px + cs // 6, py + cs // 4)))

        # Player 2 visited squares (red)
        for vx, vy in disp_p2_vis:
            if (vx, vy) == disp_p2_pos:
                continue
            if (vx, vy) in self.flags_set and (vx, vy) not in all_captured:
                continue
            px, py  = self.board_renderer.to_pixel(vx, vy)
            parity  = (vx + vy) % 2
            vcolor  = P2_LT_VISITED if parity == 0 else P2_DK_VISITED
            pygame.draw.rect(screen, vcolor, (px + 3, py + 3, cs - 4, cs - 4))
            if self.track_mode_active and (vx, vy) in disp_p2_vm:
                ns = nf_move.render(str(disp_p2_vm[(vx, vy)]), True, (160, 0, 0))
                screen.blit(ns, ns.get_rect(center=(px + cs // 6, py + cs // 4)))

        # Flags
        fo_val = self.get_selection("flag order")
        nf_card = pygame.font.SysFont("arial", max(7, cs // 4))

        if fo_val == "next":
            global_next_idx = next(
                (i for i, f in enumerate(self.flags) if f not in all_captured),
                -1
            )
        else:
            global_next_idx = len(all_captured)

        for flag_idx, flag_pos in enumerate(self.flags):
            fx, fy   = flag_pos
            px, py   = self.board_renderer.to_pixel(fx, fy)
            is_p1    = flag_pos in disp_p1_flags
            is_p2    = flag_pos in disp_p2_flags
            is_next  = (flag_idx == global_next_idx)

            if fo_val == "only":
                if is_p1:
                    img_key = "blue" if flag_pos in disp_p1_in else "red"
                elif is_p2:
                    img_key = "purple" if flag_pos in disp_p2_in else "orange"
                elif is_next:
                    img_key = "green"
                else:
                    img_key = "tan" if (fx + fy) % 2 == 0 else "ivory"
            elif fo_val == "next":
                if is_p1:
                    img_key = "blue"
                elif is_p2:
                    img_key = "red"
                elif is_next:
                    img_key = "green"
                else:
                    continue  # future flags hidden
            else:  # "any"
                if is_p1:
                    img_key = "blue"
                elif is_p2:
                    img_key = "red"
                else:
                    img_key = "tan" if (fx + fy) % 2 == 0 else "ivory"

            self._draw_flag(screen, img_key, px, py, cs)

            if fo_val == "only":
                card_surf = nf_card.render(str(flag_idx + 1), True, FLAG_ONLY_INORDER)
                screen.blit(card_surf, (px + 4, py + cs - card_surf.get_height() - 4))

        # Guide arrows for active player
        if self.guide_mode_active and self.arrows:
            if self.game_state == GameState.ENDGAME and self.replay_mode_active:
                disp_pos = disp_p1_pos if disp_cur == 1 else disp_p2_pos
                all_vis  = disp_p1_vis | disp_p2_vis
                if disp_pos:
                    piece = self.get_selection("piece")
                    n     = self.board_model.cols
                    rp_mvs = get_legal_moves_for_board(piece, *disp_pos, n, n, all_vis)
                    self._draw_arrows(screen, rp_mvs, disp_pos)
            elif self.game_state in (GameState.INGAME, GameState.WAITING):
                cur_pos  = disp_p1_pos if disp_cur == 1 else disp_p2_pos
                cur_mvs  = (self.player1_legal_moves if disp_cur == 1
                             else self.player2_legal_moves)
                if cur_pos and cur_mvs:
                    self._draw_arrows(screen, cur_mvs, cur_pos)

        # Hint degrees (current player only, INGAME)
        if self.hint_mode_active and self.hint_degrees and self.game_state == GameState.INGAME:
            hf = pygame.font.SysFont("arial", max(8, cs // 5))
            for (hx, hy), degree in self.hint_degrees.items():
                hpx, hpy = self.board_renderer.to_pixel(hx, hy)
                hs = hf.render(str(degree), True, (107, 50, 71))
                screen.blit(hs, hs.get_rect(center=(hpx + cs - (cs // 6), hpy + (cs // 4))))

        # Draw P2 piece (red) then P1 (blue) on top
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

    def _render_menu_preview(self, screen: pygame.Surface) -> None:
        cs         = self.current_cell_size
        prev_board = self.get_selection("board")
        prev_piece = self.get_selection("piece")

        if self.board_model.cols != prev_board or self.board_model.rows != prev_board:
            self.board_model.cols = prev_board
            self.board_model.rows = prev_board
            self.board_model.clear()
            self.preview_pos = None

        if (self.preview_pos is None
                or not (0 <= self.preview_pos[0] < prev_board
                        and 0 <= self.preview_pos[1] < prev_board)):
            self.preview_pos = (prev_board // 2, prev_board // 2)

        demo_pl   = self.get_selection("path length")
        demo_fd   = self.get_selection("flag density")
        cache_key = (prev_board, prev_piece, demo_pl, demo_fd)
        if self.menu_preview_cache is None or self.menu_preview_cache[0] != cache_key:
            demo_move_func = pk.get_move_func(prev_piece)
            demo_mult = PATH_LENGTH_MAP[demo_pl]
            demo_min  = max(prev_board, int(prev_board * demo_mult))
            demo_max  = min(prev_board * prev_board, int(prev_board * demo_mult * 2))
            _, preview_flags = generate_open_path_with_flags(
                prev_board, demo_min, demo_max, demo_move_func,
                max_attempts=100, time_budget=0.1,
                flag_density_choice=demo_fd, seed=42,
            )
            self.menu_preview_cache = (cache_key, preview_flags or [])

        for fx, fy in self.menu_preview_cache[1]:
            if 0 <= fx < prev_board and 0 <= fy < prev_board:
                px, py = self.board_renderer.to_pixel(fx, fy)
                self._draw_flag(screen, "tan" if (fx + fy) % 2 == 0 else "ivory",
                                px, py, cs)

        prev_cx, prev_cy = self.preview_pos
        ppx, ppy = self.board_renderer.to_pixel(prev_cx, prev_cy)
        piece_rect = pygame.Rect(ppx + 1, ppy + 1, cs - 2, cs - 2)
        try:
            pk.draw_piece(screen, piece_rect, prev_piece)
        except Exception:
            pygame.draw.ellipse(screen, (0, 0, 0), piece_rect)

        if self.guide_mode_active and self.arrows:
            prev_legal = get_legal_moves_for_board(
                prev_piece, prev_cx, prev_cy, prev_board, prev_board, set())
            self._draw_arrows(screen, prev_legal, self.preview_pos)

    def _draw_peek_thumbnail(self, screen: pygame.Surface,
                              left_panel: UIPanel, line_height: int) -> None:
        cols, rows = self.board_model.cols, self.board_model.rows
        if not (self.flags and self.peek_mode_visible):
            return
        if cols < 1 or rows < 1:
            return

        button_bounds = left_panel.get_bounds("BUTTON_PANEL")
        thumb_area_y  = left_panel.get_line_y("BUTTON_PANEL", 0, line_height)
        thumb_area    = pygame.Rect(
            button_bounds["left"] + UI_SPACE,
            thumb_area_y,
            button_bounds["width"] - UI_SPACE * 2,
            button_bounds["bottom"] - thumb_area_y - UI_SPACE * 4,
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

        flag_positions = set(self.flags)
        for gy in range(rows):
            for gx in range(cols):
                color = (FLAG_SQ_LT if (gx + gy) % 2 == 0 else FLAG_SQ_DK) \
                        if (gx, gy) in flag_positions \
                        else (LT_SQUARE if (gx + gy) % 2 == 0 else DK_SQUARE)
                pygame.draw.rect(screen, color,
                                 (tx + gx * max_cell, ty + gy * max_cell, max_cell, max_cell))

        pygame.draw.rect(screen, GRID_COLOR, (tx - 1, ty - 1, tw + 2, th + 2), 1)

    # ================================================================== #
    #  Left / right panel rendering                                       #
    # ================================================================== #

    def _render_left_panel(self, screen: pygame.Surface, left_panel: UIPanel,
                            msg_left: int, msg_right: int, msg_bottom: int) -> None:
        btn_w       = UI_SPACE
        line_height = self.font.get_linesize() + UI_SPACE

        menu_bounds      = left_panel.get_bounds("MENU_PANEL")
        text_x           = menu_bounds["left"] + UI_SPACE
        menu_panel_items = [(i, (lbl, vals, cur))
                            for i, (lbl, vals, cur) in enumerate(self.menu_items)
                            if lbl != "piece"]

        max_lbl_w = max(self.font.render(lbl, True, (0,0,0)).get_width()
                        for lbl, _, _ in self.menu_items if lbl != "piece")
        minus_x = text_x + max_lbl_w + UI_SPACE
        plus_x  = menu_bounds["right"] - UI_SPACE * 4

        for list_idx, (item_idx, (label, values, cur_idx)) in enumerate(menu_panel_items):
            panel_y = left_panel.get_line_y("MENU_PANEL", list_idx, line_height)
            row_cy  = panel_y + btn_w // 2
            lbl_surf = self.font.render(f"{label}:", True, (0, 0, 0))
            screen.blit(lbl_surf, lbl_surf.get_rect(midleft=(text_x, row_cy)))

            val      = values[cur_idx]
            sel_text = _display_for_selection(val) if label == "clock" else str(val)
            sel_surf = self.font.render(sel_text, True, (0, 0, 0))
            sel_cx   = (minus_x + btn_w + plus_x + btn_w) / 2
            screen.blit(sel_surf, sel_surf.get_rect(center=(sel_cx, row_cy)))

            if self.game_state == GameState.MENU:
                mr = pygame.Rect(minus_x, panel_y, int(btn_w * 1.5), int(btn_w * 1.5))
                pygame.draw.rect(screen, DK_SQUARE, mr)
                lt = self.font.render("<", True, (0, 160, 0))
                screen.blit(lt, lt.get_rect(center=mr.center))
                self.widget_rects[("minus", item_idx)] = mr

                pr = pygame.Rect(plus_x, panel_y, int(btn_w * 1.5), int(btn_w * 1.5))
                pygame.draw.rect(screen, DK_SQUARE, pr)
                gt = self.font.render(">", True, (220, 0, 0))
                screen.blit(gt, gt.get_rect(center=pr.center))
                self.widget_rects[("plus", item_idx)] = pr

        is_playable = self.is_piece_playable

        # Enter/cancel share code
        self.buttons["enter_code"].active   = self.game_state == GameState.MENU
        self.buttons["enter_code"].text     = ("cancel code input" if self.seed_mode_active
                                               else "enter share code")
        self.buttons["enter_code"].bg_color = ((224, 64, 128) if self.seed_mode_active
                                               else (224, 0, 96))
        self.buttons["enter_code"].rect = left_panel.get_widget_rect("MENU_PANEL", 9, BTW, BTH)
        if self.buttons["enter_code"].active:
            self.buttons["enter_code"].draw(screen)

        if self.game_state == GameState.MENU and self.seed_mode_active:
            input_y = left_panel.get_line_y("MENU_PANEL", 10, line_height)
            input_x = menu_bounds["left"] + (menu_bounds["width"] - BTW) // 5
            self.codec_input.rect = pygame.Rect(input_x, input_y, BTW * 1.5, BTH)
            self.codec_input.draw(screen)

        # Share code display + copy button
        if self.puzzle_code and self.game_state in (
                GameState.WAITING, GameState.INGAME, GameState.ENDGAME):
            code_y = left_panel.get_line_y("MENU_PANEL", 10, line_height)
            code_s = self.font.render(self.puzzle_code, True, (0, 0, 0))
            screen.blit(code_s, code_s.get_rect(
                center=(menu_bounds["center_x"], code_y + line_height // 2)))
            self.buttons["copy_code"].active   = True
            self.buttons["copy_code"].bg_color = (
                (224, 64, 128) if self.copy_clicked else (224, 0, 96))
            self.buttons["copy_code"].text     = (
                "code copied!" if self.copy_clicked else "copy share code")
            self.buttons["copy_code"].rect     = left_panel.get_widget_rect(
                "MENU_PANEL", 9, BTW, BTH)
            self.buttons["copy_code"].draw(screen)
        else:
            self.buttons["copy_code"].active = False

        # ---- BUTTON_PANEL ----

        # WAITING prompt
        if self.game_state == GameState.WAITING:
            player_one = self.get_selection("first move")
            button_bounds = left_panel.get_bounds("BUTTON_PANEL")
            if player_one == "bot" and self.player2_pos is None:
                wait_msg = "click any non-flag square"
            else:
                wait_msg = "click any non-flag square"
            ws = self.font.render(wait_msg, True, (255, 0, 0))
            wy = left_panel.get_line_y("BUTTON_PANEL", 0, line_height)
            screen.blit(ws, ws.get_rect(
                centerx=button_bounds["center_x"], centery=wy + btn_w // 2))

        # Start button (MENU)
        if self.seed_mode_active:
            self.buttons["start"].active = (self.game_state == GameState.MENU
                                            and self._is_valid_codec_length())
        else:
            self.buttons["start"].active = (self.game_state == GameState.MENU
                                            and is_playable)
        self.buttons["start"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        if self.buttons["start"].active:
            self.buttons["start"].draw(screen)

        # Hint mode (INGAME)
        self.buttons["hint_mode"].active = self.game_state in (GameState.INGAME, GameState.ENDGAME)
        self.buttons["hint_mode"].text   = "hide degrees" if self.hint_mode_active else "show degrees"
        self.buttons["hint_mode"].rect   = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        if self.buttons["hint_mode"].active:
            self.buttons["hint_mode"].draw(screen)

        # Guide mode
        self.buttons["guide_mode"].text = ("hide move guide" if self.guide_mode_active
                                           else "show move guide")
        self.buttons["guide_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 2, BTW, BTH)
        if self.buttons["guide_mode"].active:
            self.buttons["guide_mode"].draw(screen)

        # Track mode (always)
        self.buttons["track_mode"].active = True
        self.buttons["track_mode"].text   = ("hide move track" if self.track_mode_active
                                             else "show move #'s")
        self.buttons["track_mode"].rect   = left_panel.get_widget_rect("BUTTON_PANEL", 4, BTW, BTH)
        self.buttons["track_mode"].draw(screen)

        # Undo (INGAME with history)
        self.buttons["undo_mode"].active = (self.game_state == GameState.INGAME
                                            and len(self.replay_states) > 1)
        self.buttons["undo_mode"].rect   = left_panel.get_widget_rect("BUTTON_PANEL", 6, BTW, BTH)
        if self.buttons["undo_mode"].active:
            self.buttons["undo_mode"].draw(screen)

        # Replay (ENDGAME)
        self.buttons["replay_mode"].active = self.game_state == GameState.ENDGAME
        self.buttons["replay_mode"].text   = ("end replay" if self.replay_mode_active
                                              else "start replay")
        self.buttons["replay_mode"].rect   = left_panel.get_widget_rect("BUTTON_PANEL", 6, BTW, BTH)
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

        # Resign (INGAME)
        self.buttons["resign"].active = self.game_state == GameState.INGAME
        self.buttons["resign"].rect   = left_panel.get_widget_rect("BUTTON_PANEL", 8, BTW, BTH)
        if self.buttons["resign"].active:
            self.buttons["resign"].draw(screen)

        # Retry (ENDGAME, MENU_PANEL slot 7)
        self.buttons["retry"].active = (self.game_state == GameState.ENDGAME
                                        and self.last_puzzle_seed is not None)
        self.buttons["retry"].rect   = left_panel.get_widget_rect("MENU_PANEL", 7, BTW, BTH)
        if self.buttons["retry"].active:
            self.buttons["retry"].draw(screen)

        # New game (WAITING or ENDGAME)
        self.buttons["new_game"].active = self.game_state in (GameState.WAITING, GameState.ENDGAME)
        self.buttons["new_game"].rect   = left_panel.get_widget_rect("BUTTON_PANEL", 8, BTW, BTH)
        if self.buttons["new_game"].active:
            self.buttons["new_game"].draw(screen)

        # Peek (INGAME/ENDGAME, fixed bottom-left)
        self.buttons["peek_mode"].active   = (self.game_state in (GameState.INGAME, GameState.ENDGAME)
                                              and bool(self.flags))
        self.buttons["peek_mode"].text     = "hide" if self.peek_mode_visible else "peek"
        self.buttons["peek_mode"].bg_color = DK_SQUARE
        self.buttons["peek_mode"].text_color = (255, 255, 240)
        self.buttons["peek_mode"].rect     = pygame.Rect(
            msg_left + UI_SPACE * 2, msg_bottom - UI_SPACE * 5, BTW // 2, BTH)
        if self.buttons["peek_mode"].active:
            self.buttons["peek_mode"].draw(screen)

        # Exit (always, fixed bottom-right)
        self.buttons["exit"].rect = pygame.Rect(
            msg_right - UI_SPACE * 10, msg_bottom - int(UI_SPACE * 5), BTW // 2, BTH)
        self.buttons["exit"].draw(screen)

        self._draw_peek_thumbnail(screen, left_panel, line_height)

    def _render_right_panel(self, screen: pygame.Surface, right_panel: UIPanel) -> None:
        line_height = self.font.get_linesize() + UI_SPACE
        btn_w       = UI_SPACE

        # ---- PIECE_PANEL ----
        piece_bounds = right_panel.get_bounds("PIECE_PANEL")
        right_tx     = piece_bounds["left"] + UI_SPACE

        piece_idx               = self.label_to_index["piece"]
        _, piece_vals, piece_cur = self.menu_items[piece_idx]
        piece_name_cur          = piece_vals[piece_cur]

        p_line_y  = right_panel.get_line_y("PIECE_PANEL", 0, line_height)
        p_row_cy  = p_line_y + btn_w // 2
        lbl_s     = self.font.render("piece:", True, (0, 0, 0))
        p_minus_x = lbl_s.get_rect(midleft=(right_tx, p_row_cy)).right + UI_SPACE
        p_plus_x  = piece_bounds["right"] - UI_SPACE * 4

        sel_s = self.font_large.render(piece_name_cur, True, (0, 0, 0))
        screen.blit(sel_s, sel_s.get_rect(center=(piece_bounds["center_x"], p_row_cy + 8)))

        if self.game_state == GameState.MENU:
            pm_r = pygame.Rect(p_minus_x - btn_w, p_line_y, int(btn_w * 1.5), int(btn_w * 1.5))
            pygame.draw.rect(screen, DK_SQUARE, pm_r)
            lt_surf = self.font.render("<", True, (0, 160, 0))
            screen.blit(lt_surf, lt_surf.get_rect(center=pm_r.center))
            self.widget_rects[("minus", piece_idx)] = pm_r

            pp_r = pygame.Rect(p_plus_x - btn_w, p_line_y, int(btn_w * 1.5), int(btn_w * 1.5))
            pygame.draw.rect(screen, DK_SQUARE, pp_r)
            gt_surf = self.font.render(">", True, (220, 0, 0))
            screen.blit(gt_surf, gt_surf.get_rect(center=pp_r.center))
            self.widget_rects[("plus", piece_idx)] = pp_r

        move_text = pk.get_piece_move_sets_text(piece_name_cur)
        info_y    = p_line_y + sel_s.get_height() + line_height
        if move_text:
            mt_s = self.font.render(move_text, True, (80, 80, 80))
            screen.blit(mt_s, mt_s.get_rect(centerx=piece_bounds["center_x"], top=info_y))

        is_playable = self.is_piece_playable
        if self.game_state == GameState.MENU and not is_playable and not self.seed_mode_active:
            min_n     = self.min_board_size
            warn_text = f"minimum {min_n} x {min_n} board for this piece" if min_n is not None else "use a larger board for this piece"
            warn_surf = self.font.render(warn_text, True, (200, 0, 0))
            screen.blit(warn_surf, warn_surf.get_rect(
                centerx=piece_bounds["center_x"],
                top=piece_bounds["top"] + 4 * line_height))

        # ---- STATS_PANEL: two-column layout ----
        stats_bounds = right_panel.get_bounds("STATS_PANEL")
        stats_w      = stats_bounds["width"]
        stats_left   = stats_bounds["left"]
        col1_cx      = stats_left + stats_w // 4
        col2_cx      = stats_left + 3 * stats_w // 4
        mid_cx       = stats_bounds["center_x"]

        if self.game_state in (GameState.WAITING, GameState.INGAME, GameState.ENDGAME):
            if (self.game_state == GameState.ENDGAME
                    and self.replay_mode_active and self.replay_states):
                snap       = self.replay_states[self.replay_index]
                p1_flags_n = len(snap.get("player1_flags", set()))
                p2_flags_n = len(snap.get("player2_flags", set()))
                p1_moves   = len(snap.get("player1_visited", set()))
                p2_moves   = len(snap.get("player2_visited", set()))
                disp_cur   = snap.get("current_player", 1)
            else:
                p1_flags_n = len(self.player1_flags)
                p2_flags_n = len(self.player2_flags)
                p1_moves   = len(self.player1_visited)
                p2_moves   = len(self.player2_visited)
                disp_cur   = self.current_player

            # Header row
            y0 = right_panel.get_line_y("STATS_PANEL", 0, line_height)
            p1_hdr = self.font.render("blue", True, (0, 0, 192))
            p2_hdr = self.font.render("red",  True, (192, 0, 0))
            screen.blit(p1_hdr, p1_hdr.get_rect(centerx=col1_cx, top=y0))
            screen.blit(p2_hdr, p2_hdr.get_rect(centerx=col2_cx, top=y0))

            # Flags row
            y1 = right_panel.get_line_y("STATS_PANEL", 1, line_height)
            n_flags = len(self.flags)
            p1_fs = self.font.render(str(p1_flags_n), True, (0, 0, 192))
            p2_fs = self.font.render(str(p2_flags_n), True, (192, 0, 0))
            lbl_s = self.font.render(f"{n_flags} flags", True, (0, 0, 0))
            screen.blit(p1_fs,  p1_fs.get_rect(centerx=col1_cx, top=y1))
            screen.blit(lbl_s, lbl_s.get_rect(centerx=mid_cx, top=y1))
            screen.blit(p2_fs,  p2_fs.get_rect(centerx=col2_cx, top=y1))

            # Moves row
            y2 = right_panel.get_line_y("STATS_PANEL", 2, line_height)
            p1_ms = self.font.render(str(p1_moves), True, (0, 0, 192))
            p2_ms = self.font.render(str(p2_moves), True, (192, 0, 0))
            mv_lbl = self.font.render("moves", True, (0, 0, 0))
            screen.blit(p1_ms,  p1_ms.get_rect(centerx=col1_cx, top=y2))
            screen.blit(mv_lbl, mv_lbl.get_rect(centerx=mid_cx, top=y2))
            screen.blit(p2_ms,  p2_ms.get_rect(centerx=col2_cx, top=y2))

            # Turn indicator (INGAME/WAITING)
            if self.game_state in (GameState.INGAME, GameState.WAITING):
                y3 = right_panel.get_line_y("STATS_PANEL", 3, line_height)
                turn_label = "blue" if disp_cur == 1 else "red"
                turn_color = (0, 0, 192) if disp_cur == 1 else (192, 0, 0)
                ts = self.font.render(f"{turn_label}'s turn", True, turn_color)
                screen.blit(ts, ts.get_rect(centerx=mid_cx, top=y3))

            # Bot resignation offer
            player_one = self.get_selection("first move")
            if player_one == "human":
                offer_color = (192, 0, 0)
                offer_text  = "red offers to resign"
            else:
                offer_color = (0, 0, 192)
                offer_text  = "blue offers to resign"

            if self.game_state == GameState.INGAME and self.bot_offers_resignation:
                y_off = right_panel.get_line_y("STATS_PANEL", 5, line_height)
                offer_s = self.font_large.render(offer_text, True, offer_color)
                screen.blit(offer_s, offer_s.get_rect(centerx=mid_cx, top=y_off))

                self.buttons["accept_resignation"].active = True
                y_acc = right_panel.get_line_y("STATS_PANEL", 7, line_height)
                self.buttons["accept_resignation"].rect = pygame.Rect(
                    mid_cx - BTW // 2, y_acc, BTW, BTH)
                self.buttons["accept_resignation"].draw(screen)
            else:
                self.buttons["accept_resignation"].active = False

            # Clock
            clock_sel   = self.get_selection("clock")
            clock_color = (0, 0, 0)
            if self.game_state == GameState.WAITING:
                time_str = "0:00"
            elif clock_sel == 0:
                time_str = _format_clock_seconds(self.clock_elapsed)
            else:
                rem = self._remaining_time()
                if rem is not None:
                    time_str    = _format_clock_seconds(rem)
                    clock_color = (200, 0, 0) if rem < 30 else (0, 0, 0)
                else:
                    time_str = _format_clock_seconds(self.clock_elapsed)
            abs_clk_y = stats_bounds["bottom"] - line_height * 2
            clk_s = self.font.render(time_str, True, clock_color)
            screen.blit(clk_s, clk_s.get_rect(
                centerx=mid_cx, centery=int(abs_clk_y + line_height // 2)))

        # Endgame result
        if self.game_state == GameState.ENDGAME and self.endgame_reason:
            endgame_messages = {
                "player1_wins":        "blue wins",
                "player2_wins":        "red wins",
                "draw":                "draw",
                "player1_resignation": "blue resigned",
                "player2_resignation": "red resigned",
                "timeout":             "time's up",
            }
            endgame_colors = {
                "player1_wins":        (0, 0, 192),
                "player2_wins":        (192, 0, 0),
                "draw":                (96, 0, 96),
                "player1_resignation": (0, 0, 192),
                "player2_resignation": (192, 0, 0),
                "timeout":             (0, 0, 200),
            }
            msg_text  = endgame_messages.get(self.endgame_reason, "game over")
            msg_color = endgame_colors.get(self.endgame_reason, (0, 0, 0))
            y_end     = right_panel.get_line_y("STATS_PANEL", 5, line_height)
            end_s     = self.font_large.render(msg_text, True, msg_color)
            screen.blit(end_s, end_s.get_rect(centerx=mid_cx, top=y_end))

    # ================================================================== #
    #  Main render entry point                                            #
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

        right_left = win_width - panel_width - margin

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

        if self.current_cell_size > 0:
            self._render_board_area(screen)

        self.board_renderer.draw_grid_lines(screen)

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

        self._render_left_panel(screen, left_panel, msg_left, msg_right, msg_bottom)
        self._render_right_panel(screen, right_panel)

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
                    lbl, vals, cur   = self.menu_items[item_idx]
                    if action == "plus":
                        self.menu_items[item_idx] = (lbl, vals, (cur + 1) % len(vals))
                    elif action == "minus":
                        self.menu_items[item_idx] = (lbl, vals, (cur - 1) % len(vals))
                    if lbl == "board":
                        new_b = self.menu_items[item_idx][1][self.menu_items[item_idx][2]]
                        self.board_model.cols = new_b
                        self.board_model.rows = new_b
                        self.board_model.clear()
                    if lbl in ("board", "path length", "flag density"):
                        self.menu_preview_cache = None
                    if lbl in ("board", "piece"):
                        self.update_playability()
                    break

            if self.game_state == GameState.WAITING:
                if not self.bot_move_pending:
                    grid_pos = self.board_renderer.to_grid(mx, my)
                    if grid_pos is not None:
                        self.commit_start_square(grid_pos)

            elif self.game_state == GameState.INGAME:
                if not self._is_bot_turn():
                    grid_pos = self.board_renderer.to_grid(mx, my)
                    if grid_pos is not None:
                        self.make_move(grid_pos)

            elif self.game_state == GameState.MENU:
                grid_pos = self.board_renderer.to_grid(mx, my)
                if grid_pos is not None:
                    self.preview_pos = grid_pos

        return True