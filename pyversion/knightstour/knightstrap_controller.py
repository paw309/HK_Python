"""
knightstrap_controller.py

Game controller for Knightstrap: a two-player competitive knight's tour.
Inherits common functionality from BaseGameController.
"""

import time
import math
import random
from collections import deque
from functools import lru_cache

import pygame
from typing import Optional, List, Tuple, Dict, Any, Set

# sharedlib imports (BASE_DIR must already be on sys.path)
import piecekeeper as pk
from gameboard import BoardModel, BoardRenderer
from uipanel import UIPanel
from puzzle_codec import encode_params, decode_params
from widgets import Button
from move_system import get_legal_moves_for_board
from move_hint import calculate_hint_degrees
from base_game_controller import BaseGameController, GameState

from pyversion.knightstour.knightstrap_bot import BotLevel, make_bot_move

# ------------------------------------------------------------------ #
#  Shared constants                                                    #
# ------------------------------------------------------------------ #

BOARD_MIN = 5
BOARD_MAX = 16
BOARD_DEFAULT = 8
FPS = 60
UI_SPACE = 10
BTW = int(UI_SPACE * 15)
BTH = int(UI_SPACE * 3)
CODEC_TEXT_LENGTH = 16
MAX_CLOCK_SECONDS = 330

FIRST_SQUARE_CHOICES = ["select", "random"]
OPPONENT_LEVEL_CHOICES = ["1", "2", "3", "4", "5"]
PLAYER_ONE_CHOICES = ["human", "bot"]
CLOCK_MODES = ["game", "move"]

# Even-parity pieces that cannot complete a full Hamiltonian tour
EXCLUDED_PIECES = {"bishop", "ferz", "dabbaba", "alfil", "threeleaper", "tripper", "camel"}

# Board colours
LT_SQUARE = (255, 255, 240)
DK_SQUARE = (232, 200, 150)
GRID_COLOR = (107, 70, 51)
BACK_COLOR = (244, 228, 195)
WARN_COLOR = (128, 0, 0)

# Player 1 (Blue)
P1_LT_VISITED = (192, 220, 248)
P1_DK_VISITED = (128, 160, 225)

# Player 2 (Red)
P2_LT_VISITED = (255, 192, 192)
P2_DK_VISITED = (255, 128, 128)

# Bot move delay range (ms)
BOT_MOVE_DELAY_MIN = 500
BOT_MOVE_DELAY_MAX = 800

# Schema for puzzle codes (12-bit settings limit: 4+1+1+6 = 12 bits)
# opponent_level is not encoded: difficulty doesn't affect reproducibility
knightstrap_schema = [
    ("board", 4, lambda v: int(v) - BOARD_MIN),        # 5-16 → 0-11
    ("player_one", 1, {"human": 0, "bot": 1}),
    ("first_square", 1, {"select": 0, "random": 1}),
    ("clock", 6, lambda v: int(v) // 60 if v > 0 else 0),  # store minutes
]


def get_globally_valid_pieces() -> List[str]:
    """Return piece names valid for any board size (excluding even-parity pieces)."""
    return [p for p in pk.PIECE_LIST if p not in EXCLUDED_PIECES]


@lru_cache(maxsize=None)
def _piece_min_board_size(piece_name: str) -> int:
    """Return the smallest board size (BOARD_MIN..BOARD_MAX) on which *piece_name*
    can reach every square via BFS.  Returns BOARD_MAX + 1 if no such size exists."""
    move_func = pk.get_move_func(piece_name)
    for n in range(BOARD_MIN, BOARD_MAX + 1):
        reachable = {(0, 0)}
        queue = deque([(0, 0)])
        while queue:
            cx, cy = queue.popleft()
            for move in move_func(cx, cy, n):
                if move not in reachable:
                    reachable.add(move)
                    queue.append(move)
        if len(reachable) == n * n:
            return n
    return BOARD_MAX + 1


def _format_clock_seconds(seconds) -> str:
    if seconds is None:
        seconds = 0
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def _display_for_selection(clock_selected) -> str:
    if clock_selected == 0:
        return "infinity"
    return _format_clock_seconds(clock_selected)


class KnightsTrapController(BaseGameController):
    """Controls game logic and rendering for Knightstrap two-player mode."""

    def __init__(self, board_model: BoardModel, board_renderer: BoardRenderer,
                 menu_items: list, label_to_index: dict,
                 font: pygame.font.Font, font_large: pygame.font.Font,
                 base_dir: str):
        super().__init__(
            board_model, board_renderer, menu_items, label_to_index,
            font, font_large, base_dir, knightstrap_schema,
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
        self.current_player: int = 1  # 1 or 2

        # Who can move (continuation rule: one player may keep going alone)
        self.player1_can_move: bool = True
        self.player2_can_move: bool = True

        # Bot scheduling
        self.bot_move_pending: bool = False
        self.bot_move_timer: int = 0

        # Bot resignation offer
        self.bot_offers_resignation: bool = False

        # Per-move clock tracking
        self.move_start_time: Optional[float] = None

        # Preview
        self.preview_pos: Optional[Tuple[int, int]] = None

    # ================================================================== #
    #  Abstract method implementations                                    #
    # ================================================================== #

    def _get_min_board_size(self, piece_name: str) -> int:
        return _piece_min_board_size(piece_name)

    def _get_encode_params(self) -> Dict[str, Any]:
        return {
            "board": self.get_selection("board"),
            "player_one": self.get_selection("player one"),
            "first_square": self.get_selection("first square"),
            "clock": self.get_selection("clock"),
        }

    def _validate_codec(self, codec_text: str) -> Tuple[bool, Optional[Dict]]:
        try:
            params = decode_params(codec_text, knightstrap_schema)
            board_val = params.get("board", 0) + BOARD_MIN
            if not (BOARD_MIN <= board_val <= BOARD_MAX):
                return False, None
            clock_minutes = params.get("clock", 0)
            clock_val = clock_minutes * 60 if clock_minutes > 0 else 0
            first_sq = params.get("first_square")
            if first_sq not in FIRST_SQUARE_CHOICES:
                return False, None
            player_one = params.get("player_one")
            if player_one not in PLAYER_ONE_CHOICES:
                return False, None

            def _apply(label, value):
                idx = self.label_to_index[label]
                lbl, vals, _ = self.menu_items[idx]
                if value in vals:
                    self.menu_items[idx] = (lbl, vals, vals.index(value))

            _apply("board", board_val)
            _apply("clock", clock_val)
            _apply("first square", first_sq)
            _apply("player one", player_one)
            return True, {**params, "board": board_val, "clock": clock_val}
        except Exception:
            return False, None

    def _game_specific_start_setup(self, seed: Optional[int] = None) -> bool:
        """Initialize two-player state."""
        board_size = self.get_selection("board")
        first_square_mode = self.get_selection("first square")

        if seed is not None:
            random.seed(seed)

        self._clear_two_player_state()
        self.current_player = 1

        if first_square_mode == "random":
            # Choose non-overlapping random starts for both players
            all_squares = list(range(board_size * board_size))
            idx1 = random.randint(0, len(all_squares) - 1)
            p1_sq = all_squares.pop(idx1)
            p1_x, p1_y = p1_sq % board_size, p1_sq // board_size

            idx2 = random.randint(0, len(all_squares) - 1)
            p2_sq = all_squares[idx2]
            p2_x, p2_y = p2_sq % board_size, p2_sq // board_size

            self._place_player(1, (p1_x, p1_y))
            self._place_player(2, (p2_x, p2_y))

        # else "select": positions set by commit_start_square()

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
            p1_count = len(self.player1_visited)
            p2_count = len(self.player2_visited)
            if p1_count == p2_count:
                return "draw"
            elif p1_count > p2_count:
                return "player1_wins"
            else:
                return "player2_wins"
        return None

    def _check_bot_resignation_condition(self) -> bool:
        """Check if bot should offer to resign.

        Bot offers to resign if:
        - Bot has no legal moves and human has reached more squares

        Only tests current game state, not possible future states.
        """
        player_one = self.get_selection("player one")
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

        bot_squares = len(self.player1_visited) if bot_player == 1 else len(self.player2_visited)
        human_squares = len(self.player1_visited) if human_player == 1 else len(self.player2_visited)

        # Bot has no legal moves and human has reached more squares
        if not bot_moves and human_moves and human_squares > bot_squares:
            return True

        return False

    # ================================================================== #
    #  Clock helpers                                                      #
    # ================================================================== #

    def _is_per_move_mode(self) -> bool:
        """Return True when the clock is in per-move countdown mode."""
        clock_sel = self.get_selection("clock")
        time_per = self.get_selection("time per")
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

    def _render_game_specific_board(self, screen: pygame.Surface) -> None:
        """Draw visited squares and pieces for both players."""
        if self.game_state not in (GameState.INGAME, GameState.ENDGAME, GameState.WAITING):
            return

        cs = self.current_cell_size
        nf = pygame.font.SysFont("arial", max(8, cs // 4))

        # Get display state (may differ when replaying)
        if self.game_state == GameState.ENDGAME and self.replay_mode_active and self.replay_states:
            snap = self.replay_states[self.replay_index]
            disp_p1_pos = snap.get("player1_pos")
            disp_p2_pos = snap.get("player2_pos")
            disp_p1_vis = snap.get("player1_visited", set())
            disp_p2_vis = snap.get("player2_visited", set())
            disp_p1_vm = snap.get("player1_visited_moves", {})
            disp_p2_vm = snap.get("player2_visited_moves", {})
            disp_cur = snap.get("current_player", 1)
        else:
            disp_p1_pos = self.player1_pos
            disp_p2_pos = self.player2_pos
            disp_p1_vis = self.player1_visited
            disp_p2_vis = self.player2_visited
            disp_p1_vm = self.player1_visited_moves
            disp_p2_vm = self.player2_visited_moves
            disp_cur = self.current_player

        # Draw player 1 visited squares (blue)
        for vx, vy in disp_p1_vis:
            #if (vx, vy) == disp_p1_pos:
            #    continue
            px, py = self.board_renderer.to_pixel(vx, vy)
            vcolor = P1_LT_VISITED if (vx + vy) % 2 == 0 else P1_DK_VISITED
            pygame.draw.rect(screen, vcolor, (px + 3, py + 3, cs - 4, cs - 4))
            if self.track_mode_active and (vx, vy) in disp_p1_vm:
                luma = vcolor[0] * 0.299 + vcolor[1] * 0.587 + vcolor[2] * 0.114
                nc = (0, 0, 0) if luma > 128 else (255, 255, 240)
                ns = nf.render(str(disp_p1_vm[(vx, vy)]), True, nc)
                screen.blit(ns, ns.get_rect(center=(px + 20, py + 20)))

        # Draw player 2 visited squares (red)
        for vx, vy in disp_p2_vis:
            #if (vx, vy) == disp_p2_pos:
            #    continue
            px, py = self.board_renderer.to_pixel(vx, vy)
            vcolor = P2_LT_VISITED if (vx + vy) % 2 == 0 else P2_DK_VISITED
            pygame.draw.rect(screen, vcolor, (px + 3, py + 3, cs - 4, cs - 4))
            if self.track_mode_active and (vx, vy) in disp_p2_vm:
                luma = vcolor[0] * 0.299 + vcolor[1] * 0.587 + vcolor[2] * 0.114
                nc = (0, 0, 0) if luma > 128 else (255, 255, 240)
                ns = nf.render(str(disp_p2_vm[(vx, vy)]), True, nc)
                screen.blit(ns, ns.get_rect(center=(px + 20, py + 20)))

        # Guide arrows for current player (INGAME only or replay)
        if self.guide_mode_active and self.arrows:
            if self.game_state == GameState.ENDGAME and self.replay_mode_active:
                # Show legal moves for the player whose turn it is at this replay state
                disp_pos = disp_p1_pos if disp_cur == 1 else disp_p2_pos
                all_vis = disp_p1_vis | disp_p2_vis
                if disp_pos:
                    piece = self.get_selection("piece")
                    n = self.board_model.cols
                    replay_moves = get_legal_moves_for_board(piece, *disp_pos, n, n, all_vis)
                    self._draw_arrows(screen, replay_moves, disp_pos)
            elif self.game_state == GameState.INGAME:
                cur_pos = disp_p1_pos if disp_cur == 1 else disp_p2_pos
                cur_moves = self.player1_legal_moves if disp_cur == 1 else self.player2_legal_moves
                if cur_pos and cur_moves:
                    self._draw_arrows(screen, cur_moves, cur_pos)

        # Hint degrees for current player
        if self.hint_mode_active and self.hint_degrees and self.game_state == GameState.INGAME:
            for (hx, hy), deg in self.hint_degrees.items():
                px, py = self.board_renderer.to_pixel(hx, hy)
                if self.current_player == 1:
                    hs = nf.render(str(deg), True, (0, 0, 192))
                else:
                    hs = nf.render(str(deg), True, (192, 0, 0))
                screen.blit(hs, hs.get_rect(center=(px + cs - (cs // 5), py + (cs // 5))))

        # Draw player 2 piece (red tint)
        if disp_p2_pos:
            ppx, ppy = self.board_renderer.to_pixel(*disp_p2_pos)
            piece_rect = pygame.Rect(ppx + 1, ppy + 1, cs - 2, cs - 2)
            self._draw_tinted_piece(screen, piece_rect, P2_DK_VISITED)

        # Draw player 1 piece (blue tint)
        if disp_p1_pos:
            ppx, ppy = self.board_renderer.to_pixel(*disp_p1_pos)
            piece_rect = pygame.Rect(ppx + 1, ppy + 1, cs - 2, cs - 2)
            self._draw_tinted_piece(screen, piece_rect, P1_DK_VISITED)

    def _render_game_specific_stats(
            self, screen: pygame.Surface, stats_panel: UIPanel
    ) -> None:
        """Render player scores and turn indicator."""
        bounds = stats_panel.get_bounds("STATS_PANEL")
        line_height = self.font.get_linesize() + UI_SPACE
        cx = bounds["center_x"]

        if self.game_state == GameState.ENDGAME and self.replay_mode_active and self.replay_states:
            snap = self.replay_states[self.replay_index]
            p1_count = len(snap.get("player1_visited", set()))
            p2_count = len(snap.get("player2_visited", set()))
            disp_cur = snap.get("current_player", 1)
        else:
            p1_count = len(self.player1_visited)
            p2_count = len(self.player2_visited)
            disp_cur = self.current_player

        # ---- STATS_PANEL: two-column layout ----
        stats_bounds = stats_panel.get_bounds("STATS_PANEL")
        stats_w = stats_bounds['width']
        stats_left = stats_bounds['left']
        col1_cx = stats_left + stats_w // 4      # Player 1 column centre
        col2_cx = stats_left + 3 * stats_w // 4  # Player 2 column centre
        mid_cx = stats_bounds['center_x']

        # Row 0: column headers
        p1_color = (0, 0, 192)
        p2_color = (192, 0, 0)
        y0 = stats_panel.get_line_y("STATS_PANEL", 0, line_height)
        p1_h = self.font.render("blue", True, p1_color)
        p2_h = self.font.render("red", True, p2_color)
        screen.blit(p1_h, p1_h.get_rect(centerx=col1_cx, top=y0))
        screen.blit(p2_h, p2_h.get_rect(centerx=col2_cx, top=y0))

        # Player 1 label + squares
        y0 = stats_panel.get_line_y("STATS_PANEL", 1, line_height)
        p1_text = f"{p1_count}"
        p1_surf = self.font.render(p1_text, True, p1_color)
        screen.blit(p1_surf, p1_surf.get_rect(centerx=col1_cx, top=y0))

        # Player 2 label + squares
        y2 = stats_panel.get_line_y("STATS_PANEL", 1, line_height)
        p2_text = f"{p2_count}"
        p2_surf = self.font.render(p2_text, True, p2_color)
        screen.blit(p2_surf, p2_surf.get_rect(centerx=col2_cx, top=y2))

        y4 = stats_panel.get_line_y("STATS_PANEL", 1, line_height)
        turn_text = f"squares"
        turn_surf = self.font.render(turn_text, True, (0, 0, 0))
        screen.blit(turn_surf, turn_surf.get_rect(centerx=cx, top=y4))

        # Bot resignation offer
        player_one = self.get_selection("player one")
        if player_one == "bot":
            # P1 is bot (blue)
            offer_color = (0, 0, 192)
            offer_text = "blue offers to resign"
        else:
            # P2 is bot (red)
            offer_color = (192, 0, 0)
            offer_text = "red offers to resign"

        if self.game_state == GameState.INGAME and self.bot_offers_resignation:
            y_resign_msg = stats_panel.get_line_y("STATS_PANEL", 5, line_height)
            resign_msg = self.font_large.render(offer_text, True, offer_color)
            screen.blit(resign_msg, resign_msg.get_rect(centerx=mid_cx, top=y_resign_msg))

            # Accept button on line 11
            y_accept_btn = stats_panel.get_line_y("STATS_PANEL", 7, line_height)
            self.buttons["accept_resignation"].active = True
            self.buttons["accept_resignation"].rect = pygame.Rect(
                mid_cx - BTW // 2, y_accept_btn, BTW, BTH)
            self.buttons["accept_resignation"].draw(screen)
        else:
            self.buttons["accept_resignation"].active = False

    def _capture_game_state(self) -> Dict[str, Any]:
        return {
            "current_player": self.current_player,
            "pos": self.player_pos,
            "player1_pos": self.player1_pos,
            "player2_pos": self.player2_pos,
            "player1_visited": self.player1_visited.copy(),
            "player2_visited": self.player2_visited.copy(),
            "player1_visited_moves": self.player1_visited_moves.copy(),
            "player2_visited_moves": self.player2_visited_moves.copy(),
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
        self.visited = state.get("visited", set()).copy()
        self.visited_moves = state.get("visited_moves", {}).copy()
        self.move_count = state.get("move_count", 0)
        self.player_pos = state.get("pos")
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
        if not cur_pos:
            self.hint_degrees = {}
            return
        all_visited = self.player1_visited | self.player2_visited
        self.hint_degrees = calculate_hint_degrees(
            piece_name, cur_pos,
            self.board_model.cols, self.board_model.rows,
            all_visited,
        )

    def _build_buttons(self) -> None:
        f = self.font
        self.buttons: Dict[str, Button] = {
            "start": Button(pygame.Rect(0, 0, 0, 0), "start", f,
                            (255, 255, 255), (92, 192, 92), self.start_game),
            "blind_draw": Button(pygame.Rect(0, 0, 0, 0), "blind draw", f,
                                 (255, 255, 255), (128, 32, 64), self.start_blind_draw),
            "enter_code": Button(pygame.Rect(0, 0, 0, 0), "enter share code", f,
                                 (255, 255, 255), (224, 0, 96), self.toggle_codec_input),
            "copy_code": Button(pygame.Rect(0, 0, 0, 0), "copy share code", f,
                                (255, 255, 255), (224, 0, 96), self.copy_code_to_clipboard),
            "retry": Button(pygame.Rect(0, 0, 0, 0), "retry", f,
                            (255, 255, 255), (92, 192, 92), self.retry_game),
            "hint_mode": Button(pygame.Rect(0, 0, 0, 0), "show degrees", f,
                                (255, 255, 255), (255, 128, 96), self.toggle_hint_mode),
            "guide_mode": Button(pygame.Rect(0, 0, 0, 0), "show move guide", f,
                                 (255, 255, 255), (128, 64, 255), self.toggle_guide_mode),
            "track_mode": Button(pygame.Rect(0, 0, 0, 0), "show move numbers", f,
                                 (255, 255, 255), (255, 92, 128), self.toggle_track_mode),
            "undo_mode": Button(pygame.Rect(0, 0, 0, 0), "undo last move", f,
                                (255, 255, 255), (64, 128, 255), self.undo_move),
            "resign": Button(pygame.Rect(0, 0, 0, 0), "resign", f,
                             (255, 255, 255), (107,70,51), self.resign_game),
            "accept_resignation": Button(pygame.Rect(0, 0, 0, 0), "accept", f,
                                        (255, 255, 255), (107, 70, 51), self.accept_bot_resignation),
            "replay_mode": Button(pygame.Rect(0, 0, 0, 0), "start replay", f,
                                  (255, 255, 255), (64, 128, 255), self.toggle_replay_mode),
            "replay_prev": Button(pygame.Rect(0, 0, 0, 0), "-", f,
                                  (255, 255, 240), (64, 128, 255),
                                  lambda: self.navigate_replay(-1)),
            "replay_next": Button(pygame.Rect(0, 0, 0, 0), "+", f,
                                  (255, 255, 240), (64, 128, 255),
                                  lambda: self.navigate_replay(1)),
            "new_game": Button(pygame.Rect(0, 0, 0, 0), "new game", f,
                               (255, 255, 255), (32, 128, 96), self.new_game),
            "exit": Button(pygame.Rect(0, 0, 0, 0), "exit", f,
                           (255, 255, 255), (220, 40, 40), self.quit_game),
        }

    # ================================================================== #
    #  Override start/move/undo with two-player logic                     #
    # ================================================================== #

    def start_game(self, use_seed: Optional[int] = None) -> None:
        """Override to handle two-phase start for 'select' mode."""
        board_size = self.get_selection("board")
        piece_name = self.get_selection("piece")
        first_square_mode = self.get_selection("first square")

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

        if first_square_mode == "select":
            self._clear_two_player_state()
            self.player1_legal_moves = []
            self.player2_legal_moves = []
            self.legal_moves = []
            self.replay_states = []

            # If human is player 2, place bot (player 1) piece before WAITING
            human_player = self._human_player_num()
            if human_player == 2:
                if not self._place_bot_piece_randomly(board_size):
                    self.error_message = "Failed to place bot piece"
                    self.error_timer = pygame.time.get_ticks() + 3000
                    return

            self.game_state = GameState.WAITING
        else:
            self._common_ingame_start()
            # If player 1 is a bot, schedule its first move
            if self._is_bot_turn():
                self._schedule_bot_move()

    def _common_ingame_start(self) -> None:
        """Transition to INGAME state with clean common state."""
        self.end_state = None
        if self._is_per_move_mode():
            self.clock_start_time = None
            self.move_start_time = time.time()
        else:
            self.clock_start_time = time.time()
            self.move_start_time = None
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

    def commit_start_square(self, pos_gx: int, pos_gy: int) -> None:
        """Called when the human clicks a square in WAITING state."""
        if self.game_state != GameState.WAITING:
            return

        board_size = self.get_selection("board")
        if not (0 <= pos_gx < board_size and 0 <= pos_gy < board_size):
            return

        human_player = self._human_player_num()
        bot_player = 3 - human_player

        if human_player == 1:
            human_pos = (pos_gx, pos_gy)
            # Auto-select bot position (avoid human's square)
            occupied = {human_pos}
            bot_pos = self._random_start(board_size, occupied)
            if bot_pos is None:
                return
            self._place_player(1, human_pos)
            self._place_player(2, bot_pos)
        else:
            # Human is player 2
            # Bot (player 1) piece was already placed in start_game
            human_pos = (pos_gx, pos_gy)
            # Check if human clicked on bot's square
            if (pos_gx, pos_gy) == self.player1_pos:
                self.error_message = "Cannot select bot's square"
                self.error_timer = pygame.time.get_ticks() + 2000
                return  # Invalid: can't click on bot's square
            self._place_player(2, human_pos)

        self._update_all_legal_moves()
        self._sync_base_state()
        self._common_ingame_start()

        # If player 1 is bot, schedule its first move
        if self._is_bot_turn():
            self._schedule_bot_move()

        if self.hint_mode_active and self.game_state == GameState.INGAME:
            self._calculate_hint_degrees()

    def make_move(self, target_pos: Tuple[int, int]) -> None:
        """Two-player move logic."""
        if self.game_state != GameState.INGAME:
            return
        if not self._validate_move(target_pos):
            return
        if self.bot_move_pending:
            return  # Don't allow moves while bot is "thinking"

        if not self._is_per_move_mode() and self.clock_start_time is None:
            self.clock_start_time = time.time()

        self._apply_move(self.current_player, target_pos)

        end_condition = self._check_endgame_conditions()
        if end_condition:
            self._go_to_endgame(end_condition)
            return

        # Switch player (respecting continuation rule)
        other = 3 - self.current_player
        other_moves = self.player1_legal_moves if other == 1 else self.player2_legal_moves
        if other_moves:
            self.current_player = other
        # else: current player continues alone (continuation rule)

        # Reset per-move clock after each completed move
        if self._is_per_move_mode():
            self.move_start_time = time.time()

        self._sync_base_state()

        # Check for bot resignation conditions (only if game continues)
        player_one = self.get_selection("player one")
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

    def undo_move(self) -> None:
        """Undo the last move pair (both players' most recent moves)."""
        if self.game_state != GameState.INGAME:
            return
        # Cancel pending bot move
        self.bot_move_pending = False

        # Need at least 2 moves to undo a pair (initial state + 2 moves = 3 states)
        if len(self.replay_states) >= 3:
            self.replay_states.pop()
            self.replay_states.pop()
        elif len(self.replay_states) == 2:
            self.replay_states.pop()
        else:
            return

        self._restore_game_state(self.replay_states[-1])

        # Reset per-move clock so the player gets fresh time after undo
        if self._is_per_move_mode():
            self.move_start_time = time.time()

        # If it's now the bot's turn, schedule bot move
        if self._is_bot_turn():
            self._schedule_bot_move()

    def resign_game(self) -> None:
        """Human player resigns."""
        if self.game_state != GameState.INGAME:
            return
        self.bot_move_pending = False
        self.final_elapsed = int(self.paused_elapsed + (
            (time.time() - self.clock_start_time) if self.clock_start_time else 0))
        self.end_state = "resignation"
        self.game_state = GameState.ENDGAME

    def accept_bot_resignation(self) -> None:
        """Human accepts bot's resignation offer."""
        if self.game_state != GameState.INGAME or not self.bot_offers_resignation:
            return
        self.bot_move_pending = False
        self.final_elapsed = int(self.paused_elapsed + (
            (time.time() - self.clock_start_time) if self.clock_start_time else 0))

        # Determine which player is the bot
        player_one = self.get_selection("player one")
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
        self._clear_two_player_state()
        self.preview_pos = None
        self.bot_move_pending = False
        self.bot_offers_resignation = False
        self.copy_clicked = False
        self.hint_degrees = {}
        self.codec_input.set_text("")


    # ================================================================== #
    #  Toggle overrides (mutual exclusivity)                              #
    # ================================================================== #

    def toggle_hint_mode(self) -> None:
        self.hint_mode_active = not self.hint_mode_active
        if self.hint_mode_active:
            if self.game_state == GameState.INGAME:
                self._calculate_hint_degrees()
        else:
            self.hint_degrees = {}

    def toggle_guide_mode(self) -> None:
        self.guide_mode_active = not self.guide_mode_active

    # ================================================================== #
    #  Blind draw                                                         #
    # ================================================================== #

    def start_blind_draw(self) -> None:
        """Randomize all menu settings and start a game."""
        piece_name = self.get_selection("piece")
        for i, (label, values, _) in enumerate(self.menu_items):
            if label == "board":
                while True:
                    new_idx = random.randint(0, len(values) - 1)
                    if values[new_idx] >= self._get_min_board_size(piece_name):
                        self.menu_items[i] = (label, values, new_idx)
                        break
            elif label in ("player one", "first square", "opponent", "clock"):
                self.menu_items[i] = (label, values, random.randint(0, len(values) - 1))
        self.start_game()

    # ================================================================== #
    #  Bot helpers                                                        #
    # ================================================================== #

    def _human_player_num(self) -> int:
        """Return 1 if human is player 1, else 2."""
        return 1 if self.get_selection("player one") == "human" else 2

    def _is_bot_turn(self) -> bool:
        """Return True if the current player is the bot."""
        return self.current_player != self._human_player_num()

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

        level_str = self.get_selection("opponent")
        try:
            level = BotLevel(level_str)
        except ValueError:
            level = BotLevel.LEVEL_1

        piece_name = self.get_selection("piece")
        board_size = self.board_model.cols
        all_visited = self.player1_visited | self.player2_visited

        # Get opponent position for advanced level opponent modeling
        opponent_pos = self.player2_pos if bot_player == 1 else self.player1_pos

        chosen = make_bot_move(
            level, piece_name, bot_pos, board_size, all_visited,
            domain_data=None, opponent_pos=opponent_pos
        )
        if chosen is not None:
            self.make_move(chosen)

    # ================================================================== #
    #  Internal helpers                                                   #
    # ================================================================== #

    def _clear_two_player_state(self) -> None:
        self.player1_pos = None
        self.player2_pos = None
        self.player1_visited = set()
        self.player2_visited = set()
        self.player1_visited_moves = {}
        self.player2_visited_moves = {}
        self.player1_legal_moves = []
        self.player2_legal_moves = []
        self.player1_can_move = True
        self.player2_can_move = True
        self.current_player = 1
        self.visited = set()
        self.visited_moves = {}
        self.player_pos = None
        self.legal_moves = []
        self.move_count = 0
        self.clock_elapsed = 0
        self.final_elapsed = 0
        self.move_start_time = None

    def _place_player(self, player: int, pos: Tuple[int, int]) -> None:
        """Set a player's starting position."""
        if player == 1:
            self.player1_pos = pos
            self.player1_visited = {pos}
            self.player1_visited_moves = {pos: 1}
        else:
            self.player2_pos = pos
            self.player2_visited = {pos}
            self.player2_visited_moves = {pos: 1}

    def _place_bot_piece_randomly(self, board_size: int, occupied: Set[Tuple[int, int]] = None) -> bool:
        """
        Place the bot (player 1) piece on a random unoccupied square.

        Returns:
            True if successful, False if no free squares available
        """
        if occupied is None:
            occupied = set()
        bot_pos = self._random_start(board_size, occupied)
        if bot_pos is None:
            return False
        self._place_player(1, bot_pos)
        return True

    def _random_start(
        self, board_size: int, occupied: Set[Tuple[int, int]]
    ) -> Optional[Tuple[int, int]]:
        """Choose a random unoccupied starting square."""
        free = [(x, y) for x in range(board_size) for y in range(board_size)
                if (x, y) not in occupied]
        return random.choice(free) if free else None

    def _apply_move(self, player: int, pos: Tuple[int, int]) -> None:
        """Apply a move for the given player and update replay states."""
        if player == 1:
            self.player1_pos = pos
            self.player1_visited.add(pos)
            self.player1_visited_moves[pos] = len(self.player1_visited)
        else:
            self.player2_pos = pos
            self.player2_visited.add(pos)
            self.player2_visited_moves[pos] = len(self.player2_visited)

        self.move_count += 1
        self.visited = self.player1_visited | self.player2_visited
        self._update_all_legal_moves()
        self.replay_states.append(self._capture_game_state())

    def _update_all_legal_moves(self) -> None:
        """Recompute legal moves for both players."""
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

    def _sync_base_state(self) -> None:
        """Sync base class fields to the current player's data."""
        if self.current_player == 1:
            self.player_pos = self.player1_pos
            self.legal_moves = self.player1_legal_moves
            self.visited_moves = self.player1_visited_moves
        else:
            self.player_pos = self.player2_pos
            self.legal_moves = self.player2_legal_moves
            self.visited_moves = self.player2_visited_moves

    def _go_to_endgame(self, end_condition: str) -> None:
        """Finalize the game with the given end condition."""
        self.final_elapsed = int(self.paused_elapsed + (
            (time.time() - self.clock_start_time) if self.clock_start_time else 0))
        self.end_state = end_condition
        self.game_state = GameState.ENDGAME
        self.bot_move_pending = False

    def _draw_tinted_piece(self, screen: pygame.Surface,
                            piece_rect: pygame.Rect,
                            tint_color: Tuple[int, int, int]) -> None:
        """Draw the selected piece with a color tint overlay."""
        piece_name = self.get_selection("piece")

        # Draw piece normally
        try:
            pk.draw_piece(screen, piece_rect, piece_name)
        except Exception:
            pygame.draw.ellipse(screen, tint_color, piece_rect)
            return

    # ================================================================== #
    #  Update and event handling                                          #
    # ================================================================== #

    def update(self, dt: int) -> None:
        """Per-frame update: handle clock and bot moves."""
        super().update(dt)

        if self.game_state == GameState.INGAME:
            # Per-move timeout: expire if the current move takes too long
            if self._is_per_move_mode() and self.move_start_time is not None:
                clock_sel = self.get_selection("clock")
                if time.time() - self.move_start_time >= clock_sel:
                    self.final_elapsed = int(time.time() - self.move_start_time)
                    self.end_state = "timeout"
                    self.game_state = GameState.ENDGAME
                    return

            # Execute pending bot move when timer fires
            if self.bot_move_pending and pygame.time.get_ticks() >= self.bot_move_timer:
                self._execute_bot_move()

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
                        new_b = self.menu_items[item_idx][1][self.menu_items[item_idx][2]]
                        self.board_model.cols = new_b
                        self.board_model.rows = new_b
                        self.board_model.clear()
                        self.preview_pos = None
                    elif lbl == "piece":
                        self.preview_pos = None
                    break

            if self.game_state == GameState.WAITING:
                grid_pos = self.board_renderer.to_grid(mx, my)
                if grid_pos is not None:
                    self.commit_start_square(*grid_pos)

            elif self.game_state == GameState.INGAME:
                # Only allow human to click
                if not self._is_bot_turn():
                    grid_pos = self.board_renderer.to_grid(mx, my)
                    if grid_pos is not None:
                        self.make_move(grid_pos)

            elif self.game_state == GameState.MENU:
                grid_pos = self.board_renderer.to_grid(mx, my)
                if grid_pos is not None:
                    self.preview_pos = grid_pos

        return True

    # ================================================================== #
    #  Rendering                                                          #
    # ================================================================== #

    def render(self, screen: pygame.Surface) -> None:
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

        left_panel.draw_panel(screen, "MENU_PANEL", LT_SQUARE, GRID_COLOR)
        left_panel.draw_panel(screen, "BUTTON_PANEL", LT_SQUARE, GRID_COLOR)
        right_panel.draw_panel(screen, "PIECE_PANEL", LT_SQUARE, GRID_COLOR)
        right_panel.draw_panel(screen, "STATS_PANEL", LT_SQUARE, GRID_COLOR)

        area_left = msg_right + margin
        area_top = margin
        area_right = right_left - margin
        area_bottom = win_height - margin

        # Sync board size in MENU
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
            elif self.game_state in (GameState.INGAME, GameState.ENDGAME, GameState.WAITING):
                self._render_game_specific_board(screen)

        self.board_renderer.draw_grid_lines(screen)

        # WAITING message
        if self.game_state == GameState.WAITING:
            human_player = self._human_player_num()
            wait_msg = f"click a starting square"
            mf = pygame.font.SysFont("arial", 18)
            if human_player == 1:
                ms = mf.render(wait_msg, True, (0, 0, 128))
            else:
                ms = mf.render(wait_msg, True, (128, 0, 0))
            aw = area_right - area_left
            ah = area_bottom - area_top
            mx_pos = area_left + (aw - ms.get_width()) // 2
            my_pos = area_top + (ah - ms.get_height()) // 2
            pygame.draw.rect(screen, (240, 248, 255),
                             (mx_pos - 8, my_pos - 6, ms.get_width() + 16, ms.get_height() + 12))
            screen.blit(ms, (mx_pos, my_pos))

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

        self._render_left_panel(screen, left_panel, msg_left, msg_right, msg_bottom)
        self._render_right_panel(screen, right_panel)

    def _render_menu_preview(self, screen: pygame.Surface) -> None:
        """Draw the MENU board with a preview of the selected piece's moves."""
        cs = self.current_cell_size
        prev_board = self.get_selection("board")
        piece_name = self.get_selection("piece")

        if self.board_model.cols != prev_board or self.board_model.rows != prev_board:
            self.board_model.cols = prev_board
            self.board_model.rows = prev_board
            self.board_model.clear()
            self.preview_pos = None

        if (self.preview_pos is None
                or not (0 <= self.preview_pos[0] < prev_board
                        and 0 <= self.preview_pos[1] < prev_board)):
            self.preview_pos = (prev_board // 2, prev_board // 2)

        prev_cx, prev_cy = self.preview_pos
        prev_legal = get_legal_moves_for_board(
            piece_name, prev_cx, prev_cy, prev_board, prev_board, set())

        ppx, ppy = self.board_renderer.to_pixel(prev_cx, prev_cy)
        piece_rect = pygame.Rect(ppx + 1, ppy + 1, cs - 2, cs - 2)
        try:
            pk.draw_piece(screen, piece_rect, piece_name)
        except Exception:
            pygame.draw.ellipse(screen, (0, 0, 0), piece_rect)

        if self.guide_mode_active and self.arrows:
            self._draw_arrows(screen, prev_legal, self.preview_pos)

    def _render_left_panel(self, screen: pygame.Surface, left_panel: UIPanel,
                           msg_left: int, msg_right: int, msg_bottom: int) -> None:
        """Render MENU_PANEL and BUTTON_PANEL."""
        btn_w = int(UI_SPACE * 1.5)
        line_height = self.font.get_linesize() + UI_SPACE

        # ---- MENU_PANEL ----
        menu_bounds = left_panel.get_bounds("MENU_PANEL")
        text_x = menu_bounds["left"] + UI_SPACE
        menu_panel_items = [(i, (lbl, vals, cur))
                            for i, (lbl, vals, cur) in enumerate(self.menu_items)
                            if lbl != "piece"]

        max_lbl_w = max(self.font.render(lbl + ":", True, (0, 0, 0)).get_width()
                        for lbl, _, _ in self.menu_items if lbl != "piece")
        minus_x = text_x + max_lbl_w + UI_SPACE
        plus_x = menu_bounds["right"] - UI_SPACE * 4

        for list_idx, (item_idx, (label, values, cur_idx)) in enumerate(menu_panel_items):
            panel_y = left_panel.get_line_y("MENU_PANEL", list_idx, line_height)
            row_cy = panel_y + btn_w // 2
            lbl_surf = self.font.render(f"{label}", True, (0, 0, 0))
            screen.blit(lbl_surf, lbl_surf.get_rect(midleft=(text_x, row_cy)))

            val = values[cur_idx]
            sel_text = _display_for_selection(val) if label == "clock" else str(val)
            sel_surf = self.font.render(sel_text, True, (0, 0, 0))
            sel_cx = (minus_x + btn_w + plus_x) / 2
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

        # Blind draw button
        self.buttons["blind_draw"].active = (self.game_state == GameState.MENU
                                              and not self.seed_mode_active)
        self.buttons["blind_draw"].rect = left_panel.get_widget_rect(
            "MENU_PANEL", 7, BTW, BTH)
        if self.buttons["blind_draw"].active:
            self.buttons["blind_draw"].draw(screen)

        # Enter/cancel share code button
        self.buttons["enter_code"].active = self.game_state == GameState.MENU
        self.buttons["enter_code"].text = ("cancel code input" if self.seed_mode_active
                                           else "enter share code")
        self.buttons["enter_code"].bg_color = (224, 64, 128) if self.seed_mode_active else (224, 0, 96)
        self.buttons["enter_code"].rect = left_panel.get_widget_rect("MENU_PANEL", 9, BTW, BTH)
        self.buttons["enter_code"].draw(screen)

        if self.game_state == GameState.MENU and self.seed_mode_active:
            input_y = left_panel.get_line_y("MENU_PANEL", 10, line_height)
            input_x = menu_bounds["left"] + (menu_bounds["width"] // 2) - BTW * .75
            self.codec_input.rect = pygame.Rect(input_x, input_y, BTW * 1.5, BTH)
            self.codec_input.draw(screen)

        # Share code display
        if (self.puzzle_code
                and self.game_state in (GameState.WAITING, GameState.INGAME, GameState.ENDGAME)):
            code_y = left_panel.get_line_y("MENU_PANEL", 10, line_height)
            code_s = self.font.render(self.puzzle_code, True, (0, 0, 0))
            screen.blit(code_s, code_s.get_rect(
                center=(menu_bounds["center_x"], code_y + UI_SPACE)))

        # Copy share code button
        self.buttons["copy_code"].active = self.game_state in (
            GameState.WAITING, GameState.INGAME, GameState.ENDGAME)
        self.buttons["copy_code"].bg_color = (224, 64, 128) if self.copy_clicked else (224, 0, 96)
        self.buttons["copy_code"].text = ("share code copied" if self.copy_clicked
                                          else "copy share code")
        self.buttons["copy_code"].rect = left_panel.get_widget_rect("MENU_PANEL", 9, BTW, BTH)
        if self.buttons["copy_code"].active:
            self.buttons["copy_code"].draw(screen)

        # ---- BUTTON_PANEL ----
        piece_name = self.get_selection("piece")
        is_playable = self.get_selection("board") >= self._get_min_board_size(piece_name)

        # Start button
        if self.seed_mode_active:
            self.buttons["start"].active = (self.game_state == GameState.MENU
                                            and self._is_valid_codec_length())
        else:
            self.buttons["start"].active = self.game_state == GameState.MENU and is_playable
        self.buttons["start"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        if self.buttons["start"].active:
            self.buttons["start"].draw(screen)

        # Hint mode
        self.buttons["hint_mode"].active = self.game_state in (GameState.INGAME, GameState.ENDGAME)
        self.buttons["hint_mode"].text = "hide degrees" if self.hint_mode_active else "show degrees"
        self.buttons["hint_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        if self.buttons["hint_mode"].active:
            self.buttons["hint_mode"].draw(screen)

        # Guide mode
        self.buttons["guide_mode"].active = self.game_state in (
            GameState.MENU, GameState.INGAME, GameState.ENDGAME)
        self.buttons["guide_mode"].text = ("hide move guide" if self.guide_mode_active
                                           else "show move guide")
        self.buttons["guide_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 2, BTW, BTH)
        if self.buttons["guide_mode"].active:
            self.buttons["guide_mode"].draw(screen)

        # Track mode
        self.buttons["track_mode"].active = True
        self.buttons["track_mode"].text = ("hide move #'s" if self.track_mode_active
                                           else "show move #'s")
        self.buttons["track_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 4, BTW, BTH)
        self.buttons["track_mode"].draw(screen)

        # Undo (INGAME only, when there are states to undo)
        can_undo = (self.game_state == GameState.INGAME
                    and len(self.replay_states) > 1
                    and not self.bot_move_pending)
        self.buttons["undo_mode"].active = can_undo
        self.buttons["undo_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 6, BTW, BTH)
        if self.buttons["undo_mode"].active:
            self.buttons["undo_mode"].draw(screen)

        # Resign (INGAME only)
        self.buttons["resign"].active = self.game_state == GameState.INGAME
        self.buttons["resign"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 8, BTW, BTH)
        if self.buttons["resign"].active:
            self.buttons["resign"].draw(screen)

        # Retry (ENDGAME only)
        self.buttons["retry"].active = (self.game_state == GameState.ENDGAME
                                        and self.last_puzzle_seed is not None)
        self.buttons["retry"].rect = left_panel.get_widget_rect("MENU_PANEL", 7, BTW, BTH)
        if self.buttons["retry"].active:
            self.buttons["retry"].draw(screen)

        # Replay mode (ENDGAME only)
        self.buttons["replay_mode"].active = self.game_state == GameState.ENDGAME
        self.buttons["replay_mode"].text = "end replay" if self.replay_mode_active else "start replay"
        self.buttons["replay_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 6, BTW, BTH)
        if self.buttons["replay_mode"].active:
            self.buttons["replay_mode"].draw(screen)

        # Replay navigation
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

        # New game (ENDGAME only)
        self.buttons["new_game"].active = self.game_state == GameState.ENDGAME
        self.buttons["new_game"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 8, BTW, BTH)
        if self.buttons["new_game"].active:
            self.buttons["new_game"].draw(screen)

        # Exit button
        self.buttons["exit"].rect = pygame.Rect(
            msg_right - UI_SPACE * 8, msg_bottom - int(UI_SPACE * 5),
            BTW // 3, int(BTH * 0.75))
        self.buttons["exit"].draw(screen)

    def _render_right_panel(self, screen: pygame.Surface, right_panel: UIPanel) -> None:
        """Render PIECE_PANEL and STATS_PANEL."""
        btn_w = UI_SPACE
        line_height = self.font.get_linesize() + UI_SPACE

        # ---- PIECE_PANEL ----
        piece_bounds = right_panel.get_bounds("PIECE_PANEL")
        right_tx = piece_bounds["left"] + UI_SPACE

        piece_idx = self.label_to_index["piece"]
        _, piece_values, piece_cur = self.menu_items[piece_idx]
        piece_name = piece_values[piece_cur] if piece_values else "knight"

        p_line_y = right_panel.get_line_y("PIECE_PANEL", 0, line_height)
        p_row_cy = p_line_y
        lbl_s = self.font.render("piece:", True, (0, 0, 0))
        lbl_rect = lbl_s.get_rect(midleft=(right_tx, p_row_cy))
        p_minus_x = lbl_rect.right + UI_SPACE
        p_plus_x = piece_bounds["left"] + piece_bounds["width"] - UI_SPACE - btn_w * 5

        sel_s = self.font_large.render(piece_name, True, (0, 0, 0))
        screen.blit(sel_s, sel_s.get_rect(center=(piece_bounds["center_x"], p_row_cy + 8)))

        move_set_text = pk.get_piece_move_sets_text(piece_name)
        if move_set_text:
            mst_s = self.font.render(move_set_text, True, (0, 0, 0))
            screen.blit(mst_s, mst_s.get_rect(
                centerx=piece_bounds["center_x"],
                top=p_row_cy + sel_s.get_height() + self.font.get_linesize()))

        if self.game_state == GameState.MENU:
            pm_r = pygame.Rect(p_minus_x - btn_w, p_line_y, int(btn_w * 1.5), int(btn_w * 1.5))
            pygame.draw.rect(screen, DK_SQUARE, pm_r)
            lt = self.font.render("<", True, (0, 160, 0))
            screen.blit(lt, lt.get_rect(center=pm_r.center))
            self.widget_rects[("minus", piece_idx)] = pm_r

            pp_r = pygame.Rect(p_plus_x - btn_w, p_line_y, int(btn_w * 1.5), int(btn_w * 1.5))
            pygame.draw.rect(screen, DK_SQUARE, pp_r)
            gt = self.font.render(">", True, (192, 0, 0))
            screen.blit(gt, gt.get_rect(center=pp_r.center))
            self.widget_rects[("plus", piece_idx)] = pp_r

        # Piece too small warning
        min_n = _piece_min_board_size(piece_name)
        if self.game_state == GameState.MENU and self.get_selection("board") < min_n:
            warn_y = right_panel.get_line_y("PIECE_PANEL", 3, line_height)
            warn_text = (f"minimum {min_n} x {min_n} board for this piece"
                         if min_n <= BOARD_MAX else "use a larger board for this piece")
            ws = self.font.render(warn_text, True, WARN_COLOR)
            screen.blit(ws, ws.get_rect(centerx=piece_bounds["center_x"], top=warn_y))

        # ---- STATS_PANEL ----
        self._render_game_specific_stats(screen, right_panel)

        # Clock
        stats_bounds = right_panel.get_bounds("STATS_PANEL")
        if self.game_state != GameState.MENU:
            remaining = self._remaining_time()
            if remaining is not None:
                clock_disp = _format_clock_seconds(remaining)
                clock_color = (200, 0, 0) if remaining < 30 else (0, 0, 0)
            else:
                clock_disp = _format_clock_seconds(self.clock_elapsed)
                clock_color = (0, 0, 0)
            clock_y = right_panel.get_line_y("STATS_PANEL", 9, line_height)
            clock_surf = self.font.render(clock_disp, True, clock_color)
            screen.blit(clock_surf, clock_surf.get_rect(
                centerx=stats_bounds["center_x"], top=clock_y))

        # Endgame message
        if self.game_state == GameState.ENDGAME and self.end_state:
            end_messages = {
                "player1_wins": ("blue wins", (0, 0, 192)),
                "player2_wins": ("red wins", (192, 0, 0)),
                "player1_resignation": ("blue resigned", (0, 0, 192)),
                "player2_resignation": ("red resigned", (192, 0, 0)),
                "draw": ("draw", (96, 0, 96)),
                #"resignation": ("resigned", (107, 70, 51)),
                "timeout": ("time's up", (64, 0, 64)),
            }
            msg, msg_color = end_messages.get(self.end_state, ("game over", (0, 0, 0)))
            em_s = self.font_large.render(msg, True, msg_color)
            em_y = right_panel.get_line_y("STATS_PANEL", 5, line_height)
            screen.blit(em_s, em_s.get_rect(centerx=stats_bounds["center_x"], top=em_y))