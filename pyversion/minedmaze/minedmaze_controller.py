"""
minedmaze_controller.py

Game controller for Knights Maze v0.2.
Inherits common functionality from BaseGameController.
"""

import math
import os
import sys
import time

import pygame
from typing import Optional, List, Tuple, Set, Dict, Any

# Add sharedlib to path when run directly
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHAREDLIB = os.path.join(BASE_DIR, "sharedlib")
for _p in (BASE_DIR, SHAREDLIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import piecekeeper as pk
from gameboard import BoardModel, BoardRenderer
from uipanel import UIPanel
from puzzle_codec import decode_params
from widgets import Button
from common_utils import format_time as _format_time
from base_game_controller import BaseGameController, GameState

from maze_generator import (
    generate_maze_path_and_obstacles,
    adaptive_path_lengths,
    _make_rng,
)

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
CODEC_TEXT_LENGTH = 16


PATH_LENGTH_CHOICES = ["short", "long"]
DENSITY_CHOICES     = ["sparse", "dense", "random"]
CLOCK_MODES          = ["game", "move"]
MAX_CLOCK_SECONDS = 330

# Colors
LT_SQUARE  = (255, 255, 240)
DK_SQUARE  = (232, 200, 150)
LT_MOVE    = (148, 220, 248)
DK_MOVE    = (100, 145, 225)
LT_BLOCK   = (255, 192, 192)
DK_BLOCK   = (255, 128, 128)
GRID_COLOR = (107, 70,  51)
BACK_COLOR = (244, 228, 195)

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

knightsmaze_schema = [
    ("board",   4, lambda v: int(v) - BOARD_MIN),
    ("length",  1, {"short": 0, "long": 1}),
    ("density", 2, {"sparse": 0, "dense": 1, "random": 2}),
    ("blocks",  1, {"show": 0, "hide": 1}),
    ("bounce",  1, {"stay": 0, "bounce": 1}),
]

# Public API for star imports and tools like minedmaze_v02.py
__all__ = ["MazeController", "GameState",
           "BOARD_MIN", "BOARD_MAX", "BOARD_DEFAULT", "FPS",
           "PATH_LENGTH_CHOICES", "DENSITY_CHOICES", "CLOCK_MODES",
           "knightsmaze_schema"]


def _display_clock(clock_selected):
    if clock_selected == 0:
        return "infinity" #INFINITY_SYMBOL
    m, s = divmod(clock_selected, 60)
    return f"{m}:{s:02d}"

#   return f"{clock_selected // 60}:00"


# ------------------------------------------------------------------ #
#  MazeController                                                     #
# ------------------------------------------------------------------ #

class MazeController(BaseGameController):
    """
    Game controller for Knights Maze v0.2.
    Inherits common functionality from BaseGameController.
    """

    # Use maze path colours for visited-square rendering
    VISITED_LT = LT_MOVE
    VISITED_DK = DK_MOVE

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
            font, font_large, base_dir, knightsmaze_schema,
        )

        # Load target and mine images
        markers_dir = os.path.join(base_dir, "assets", "markers")
        self.target_img     = pygame.image.load(os.path.join(markers_dir, "target.png")).convert_alpha()
        self.mine_light_img = pygame.image.load(os.path.join(markers_dir, "mine_light.png")).convert_alpha()
        self.mine_dark_img  = pygame.image.load(os.path.join(markers_dir, "mine_dark.png")).convert_alpha()

        # Maze-specific state
        self.maze_path:     Optional[List[Tuple[int, int]]] = None
        self.maze_path_set: Set[Tuple[int, int]]            = set()
        self.obstacles:     Set[Tuple[int, int]]            = set()

        self.obstacle_flash_list:    List[Tuple[Tuple[int, int], float]] = []
        self.obstacle_permanent_red: Set[Tuple[int, int]]                = set()

        self.attempt_count: int = 0
        self.total_move_count = 0

        # Per-move clock
        self.move_start_time: Optional[float] = None

        # Menu preview
        self.menu_preview_cache = None
        self.menu_preview_pos: Optional[Tuple[int, int]] = None

    # ================================================================== #
    #  Maze-specific helpers                                              #
    # ================================================================== #

    def _get_path_legal_moves(
        self, pos: Tuple[int, int], n: int, piece: str
    ) -> List[Tuple[int, int]]:
        """Legal moves that stay on the maze path and have not been visited."""
        raw = pk.get_move_func(piece)(*pos, n)
        return [
            (x, y) for (x, y) in raw
            if (x, y) in self.maze_path_set and (x, y) not in self.visited_moves
        ]

    def _get_all_legal_moves(
        self,
        pos:      Tuple[int, int],
        n:        int,
        piece:    str,
        excluded: Dict,
    ) -> List[Tuple[int, int]]:
        """All on-board moves from *pos*, excluding *excluded* squares."""
        raw = pk.get_move_func(piece)(*pos, n)
        return [(x, y) for (x, y) in raw if (x, y) not in excluded]

    def _get_excluded_for_guide_arrows(
        self,
        visited: Dict[Tuple[int, int], int]
    ) -> Set[Tuple[int, int]]:
        """
        Get squares to exclude from guide arrows.

        Args:
            visited: Dictionary mapping (x, y) coordinates to move numbers

        Returns:
            Set of squares to exclude from guide arrows

        Excludes:
        1. Visited squares that are NOT blocks (visited but not obstacles)
        2. Blocks that have been revealed in show blocks mode
        """
        excluded = set()
        # Exclude visited squares that are not blocks
        for sq in visited:
            if sq not in self.obstacles:
                excluded.add(sq)
        # Exclude revealed blocks (in show blocks mode)
        excluded.update(self.obstacle_permanent_red)
        return excluded

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
        """Validate maze share code and apply decoded settings."""
        try:
            params    = decode_params(codec_text, self.schema)
            board_val = params.get("board", 0) + BOARD_MIN
            if not (BOARD_MIN <= board_val <= BOARD_MAX):
                return False, None
            length_val  = params.get("length")
            density_val = params.get("density")
            blocks_val  = params.get("blocks")
            bounce_val  = params.get("bounce")
            if length_val  not in PATH_LENGTH_CHOICES: return False, None
            if density_val not in DENSITY_CHOICES:     return False, None
            if blocks_val  not in ("show", "hide"):    return False, None
            if bounce_val  not in ("stay", "bounce"):  return False, None

            def _apply(label, value):
                idx = self.label_to_index[label]
                lbl, vals, _ = self.menu_items[idx]
                if value in vals:
                    self.menu_items[idx] = (lbl, vals, vals.index(value))

            _apply("board",   board_val)
            _apply("length",  length_val)
            _apply("density", density_val)
            _apply("blocks",  blocks_val)
            _apply("bounce",  bounce_val)
            return True, {**params, "board": board_val}
        except Exception:
            return False, None

    def _game_specific_start_setup(self, seed: Optional[int] = None) -> bool:
        """Generate maze path and obstacles."""
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

        if not path or len(path) <= 4 or obs is None:
            return False

        self.maze_path     = path
        self.maze_path_set = set(path)
        self.obstacles     = set(obs)

        # Initialise common player / move state
        self.player_pos    = self.maze_path[0]
        self.visited       = {self.player_pos}
        self.visited_moves = {self.player_pos: 0}
        self.move_count    = 0
        self.attempt_count = 0
        self.total_move_count = 0

        self.obstacle_flash_list    = []
        self.obstacle_permanent_red = set()

        self._update_legal_moves()
        return True

    def _validate_move(self, target: Tuple[int, int]) -> bool:
        """Check that *target* is reachable from the current position."""
        piece = self.get_selection("piece")
        n     = self.board_model.cols
        reachable = pk.get_move_func(piece)(*self.player_pos, n)
        return target in reachable

    def _game_specific_make_move(self, target: Tuple[int, int]) -> bool:
        """Handle obstacle collisions and path validation."""
        self.total_move_count += 1
        blocks_show = self.get_selection("blocks") == "show"
        bounce      = self.get_selection("bounce") == "bounce"

        if target in self.obstacles:
            self.attempt_count += 1
            if blocks_show:
                self.obstacle_permanent_red.add(target)
            else:
                self.obstacle_flash_list.append((target, time.time()))

            if bounce:
                self.player_pos = self.maze_path[0]
                self.visited    = {self.player_pos}
                self.visited_moves.clear()
                self.visited_moves[self.player_pos] = 0
                self.move_count = 0
                self.replay_states.clear()
                self.replay_states.append(self._capture_game_state())
            return False

        if target not in self.maze_path_set or target in self.visited:
            return False

        self.move_count += 1
        return True

    def _check_endgame_conditions(self) -> Optional[str]:
        """Maze complete when player reaches the final square; no moves = blocked."""
        if self.player_pos == self.maze_path[-1]:
            return "maze_complete"
        path_legal = self._get_path_legal_moves(
            self.player_pos, self.board_model.cols, self.get_selection("piece")
        )
        if not path_legal:
            return "no_moves"
        return None

    def _update_legal_moves(self) -> None:
        """Update legal moves to path-only squares."""
        if not self.player_pos:
            self.legal_moves = []
            return
        piece = self.get_selection("piece")
        n     = self.board_model.cols
        self.legal_moves = self._get_path_legal_moves(self.player_pos, n, piece)

    def _calculate_hint_degrees(self) -> None:
        """Warnsdorff degrees constrained to the maze path."""
        if not self.player_pos or self.game_state != GameState.INGAME:
            self.hint_degrees = {}
            return
        piece     = self.get_selection("piece")
        n         = self.board_model.cols
        reachable = self._get_path_legal_moves(self.player_pos, n, piece)
        degrees: Dict[Tuple[int, int], int] = {}
        for sq in reachable:
            onward = self._get_path_legal_moves(sq, n, piece)
            if onward:
                degrees[sq] = len(onward)
        self.hint_degrees = degrees

    def _capture_game_state(self) -> Dict[str, Any]:
        return {
            "pos":           self.player_pos,
            "visited":       self.visited.copy(),
            "visited_moves": dict(self.visited_moves),
            "move_count":    self.move_count,
        }

    def _restore_game_state(self, state: Dict[str, Any]) -> None:
        self.player_pos    = state["pos"]
        self.visited       = state["visited"].copy()
        self.visited_moves = dict(state["visited_moves"])
        self.move_count    = state["move_count"]
        self._update_legal_moves()

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
    #  Game start override                                                #
    # ================================================================== #

    def start_game(self, use_seed: Optional[int] = None) -> None:
        """Start a new game, then configure the per-move clock if applicable."""
        super().start_game(use_seed)
        if self.game_state == GameState.INGAME:
            if self._is_per_move_mode():
                self.clock_start_time = None
                self.move_start_time  = time.time()
            else:
                self.move_start_time = None

    # ================================================================== #
    #  Button management                                                  #
    # ================================================================== #

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
            "undo_mode":   Button(pygame.Rect(0,0,0,0), "undo last move",
                                  f, (255,255,255), (64,128,255),  self.undo_move),
            "resign":      Button(pygame.Rect(0,0,0,0), "resign",
                                  f, (255,255,255), (107,50,71), self.resign_game),
            "reveal":      Button(pygame.Rect(0,0,0,0), "show maze path",
                                  f, (255,255,255), (255,128,96),  self.toggle_reveal),
            "replay_mode": Button(pygame.Rect(0,0,0,0), "start replay",
                                  f, (255,255,255), (64,128,255),  self.toggle_replay_mode),
            "replay_prev": Button(pygame.Rect(0,0,0,0), "-",
                                  f, (255,255,240), (64,128,255),  lambda: self.navigate_replay(-1)),
            "replay_next": Button(pygame.Rect(0,0,0,0), "+",
                                  f, (255,255,240), (64,128,255),  lambda: self.navigate_replay(1)),
            "retry":       Button(pygame.Rect(0,0,0,0), "retry",
                                  f, (255,255,255), (92,192,92),   self.retry_game),
            "new_game":    Button(pygame.Rect(0,0,0,0), "new game",
                                  f, (255,255,255), (32,128,96),   self.new_game),
            "peek_mode":   Button(pygame.Rect(0,0,0,0), "peek",
                                  f, (255,255,240), DK_SQUARE,     self.toggle_peek),
            "exit":        Button(pygame.Rect(0,0,0,0), "exit",
                                  f, (255,255,255), (220,40,40),   self.quit_game),
        }

    # ================================================================== #
    #  Per-frame update (extends base to clean up flash list)             #
    # ================================================================== #

    def update(self, dt: int) -> None:
        super().update(dt)
        now = time.time()
        self.obstacle_flash_list = [
            (sq, ts) for sq, ts in self.obstacle_flash_list if now - ts < 2.0
        ]
        # Per-move timeout check
        if self.game_state == GameState.INGAME:
            if self._is_per_move_mode() and self.move_start_time is not None:
                clock_sel = self.get_selection("clock")
                if now - self.move_start_time >= clock_sel:
                    self.final_elapsed = int(now - self.move_start_time)
                    self.end_state     = "timeout"
                    self.game_state    = GameState.ENDGAME

    # ================================================================== #
    #  Move logic                                                         #
    # ================================================================== #

    def make_move(self, target_pos: Tuple[int, int]) -> None:
        """Attempt a move, with per-move clock management."""
        if self.game_state != GameState.INGAME:
            return
        if not self._validate_move(target_pos):
            return

        # Per-game mode: start clock on first move
        if not self._is_per_move_mode() and self.clock_start_time is None:
            self.clock_start_time = time.time()

        result = self._game_specific_make_move(target_pos)

        if not result:
            # Mine hit: reset per-move clock
            if target_pos in self.obstacles and self._is_per_move_mode():
                self.move_start_time = time.time()
            return

        # Valid path move
        self.player_pos = target_pos
        self.visited.add(target_pos)
        self.visited_moves[target_pos] = self.move_count
        self.replay_states.append(self._capture_game_state())
        self._update_legal_moves()
        if self.hint_mode_active:
            self._calculate_hint_degrees()

        # Reset per-move clock after a valid path move
        if self._is_per_move_mode():
            self.move_start_time = time.time()

        end_condition = self._check_endgame_conditions()
        if end_condition:
            self.final_elapsed = int(self.paused_elapsed + (
                (time.time() - self.clock_start_time)
                if self.clock_start_time else 0))
            self.end_state  = end_condition
            self.game_state = GameState.ENDGAME


    def _render_game_specific_board(self, screen: pygame.Surface) -> None:
        """Draw maze path, obstacles, target, visited squares, arrows, and piece."""
        cs = self.current_cell_size
        gs = self.game_state

        show_full_path = (
            (gs == GameState.INGAME  and self.peek_mode_visible) or
            (gs == GameState.ENDGAME and self.reveal_mode_active)
        )

        if show_full_path and self.maze_path:
            for gx, gy in self.maze_path:
                if (gx, gy) != self.maze_path[-1] and (gx, gy) not in self.visited_moves:
                    px, py = self.board_renderer.to_pixel(gx, gy)
                    color  = LT_MOVE if (gx + gy) % 2 == 0 else DK_MOVE
                    pygame.draw.rect(screen, color, (px + 1, py + 1, cs - 1, cs - 1))

        # In peek mode, draw path numbers in upper right corner of each unvisited path square
        if gs == GameState.INGAME and self.peek_mode_visible and self.maze_path:
            pf = pygame.font.SysFont("arial", max(6, cs // 4))
            for num, (gx, gy) in enumerate(self.maze_path):
                if (gx, gy) == self.maze_path[-1] or (gx, gy) in self.visited_moves:
                    continue
                px, py = self.board_renderer.to_pixel(gx, gy)
                ns = pf.render(str(num), True, (0, 0, 0))
                screen.blit(ns, (px + cs - ns.get_width() - 2, py + 2))

        # Draw target square
        if self.maze_path:
            tx, ty = self.maze_path[-1]
            px, py = self.board_renderer.to_pixel(tx, ty)
            # Draw appropriate board color based on square position
            #target_color = LT_SQUARE if (tx + ty) % 2 == 0 else DK_SQUARE
            #pygame.draw.rect(screen, target_color, (px + 1, py + 1, cs - 1, cs - 1))
            # Draw target image on top
            if cs > 0:
                scaled_target = pygame.transform.smoothscale(self.target_img, (cs, cs))
                screen.blit(scaled_target, (px, py))

        # Draw permanent red obstacles
        for gx, gy in self.obstacle_permanent_red:
            px, py = self.board_renderer.to_pixel(gx, gy)
            mine_img = self.mine_dark_img if (gx + gy) % 2 == 0 else self.mine_light_img
            if cs > 0:
                img_size = max(1, int(cs * 0.6))
                scaled_mine = pygame.transform.smoothscale(mine_img, (img_size, img_size))
                offset = (cs - img_size) // 2
                screen.blit(scaled_mine, (px + offset, py + offset))

        # Draw flashing obstacles
        flash_now = time.time()
        for sq, ts in self.obstacle_flash_list:
            if flash_now - ts < 1.5:
                gx, gy = sq
                px, py = self.board_renderer.to_pixel(gx, gy)
                mine_img = self.mine_dark_img if (gx + gy) % 2 == 0 else self.mine_light_img
                if cs > 0:
                    img_size = max(1, int(cs * 0.6))
                    scaled_mine = pygame.transform.smoothscale(mine_img, (img_size, img_size))
                    offset = (cs - img_size) // 2
                    screen.blit(scaled_mine, (px + offset, py + offset))


        # Draw visited squares (uses base-class helper).
        # When reveal is active in ENDGAME, suppress move numbers so path
        # numbers can be drawn instead.
        if gs == GameState.ENDGAME and self.reveal_mode_active:
            saved_track = self.track_mode_active
            self.track_mode_active = False
            try:
                self._draw_visited_squares(screen)
            finally:
                self.track_mode_active = saved_track
        else:
            self._draw_visited_squares(screen)

        # When reveal is active in ENDGAME, draw path numbers on every path square
        if gs == GameState.ENDGAME and self.reveal_mode_active and self.maze_path:
            pf = pygame.font.SysFont("arial", max(8, cs // 4))
            for num, (gx, gy) in enumerate(self.maze_path):
                px, py = self.board_renderer.to_pixel(gx, gy)
                if (gx, gy) == self.maze_path[-1]:
                    bg = LT_SQUARE if (gx + gy) % 2 == 0 else DK_SQUARE
                elif (gx, gy) in self.visited_moves:
                    bg = self.VISITED_LT if (gx + gy) % 2 == 0 else self.VISITED_DK
                else:
                    bg = LT_MOVE if (gx + gy) % 2 == 0 else DK_MOVE
                luma = bg[0] * 0.299 + bg[1] * 0.587 + bg[2] * 0.114
                nc = (0, 0, 0) if luma > 128 else (255, 255, 255)
                ns = pf.render(str(num), True, nc)
                screen.blit(ns, ns.get_rect(center=(px + cs // 2, py + cs // 2)))

        # Draw guide arrows
        if self.guide_mode_active and self.arrows:
            n_brd = self.board_model.cols
            piece = self.get_selection("piece")
            if (gs == GameState.ENDGAME and self.replay_mode_active
                    and self.replay_states):
                snap     = self.replay_states[self.replay_index]
                rpos     = snap["pos"]
                rvisited = snap["visited_moves"]
                valid_squares = self.maze_path_set | self.obstacles
                if rpos:
                    excluded = self._get_excluded_for_guide_arrows(rvisited)
                    guide_moves = self._get_all_legal_moves(rpos, n_brd, piece, excluded)
                    guide_moves = [sq for sq in guide_moves if sq in valid_squares]
                    self._draw_arrows(screen, guide_moves, rpos)
            elif self.player_pos:
                valid_squares = self.maze_path_set | self.obstacles
                excluded = self._get_excluded_for_guide_arrows(self.visited_moves)
                guide_moves = self._get_all_legal_moves(
                    self.player_pos, n_brd, piece, excluded)
                guide_moves = [sq for sq in guide_moves if sq in valid_squares]
                self._draw_arrows(screen, guide_moves, self.player_pos)

        # Draw hint degrees (uses base-class helper)
        if self.hint_mode_active and self.hint_degrees:
            self._draw_hint_degrees(screen)

        # Draw color and number for current player position (before drawing piece)
        if self.player_pos:
            # Determine which position/moves to display (replay or current)
            if (gs == GameState.ENDGAME
                    and self.replay_mode_active
                    and self.replay_states):
                disp_pos   = self.replay_states[self.replay_index]["pos"]
                disp_moves = self.replay_states[self.replay_index]["visited_moves"]
            else:
                disp_pos   = self.player_pos
                disp_moves = self.visited_moves

            # Draw color and number for the square the piece is on
            if disp_pos and disp_pos in disp_moves:
                px, py = self.board_renderer.to_pixel(*disp_pos)
                # Draw appropriate color
                vc = self.VISITED_LT if (disp_pos[0] + disp_pos[1]) % 2 == 0 else self.VISITED_DK
                pygame.draw.rect(screen, vc, (px + 3, py + 3, cs - 4, cs - 4))
                # Draw move number if track mode is active
                if self.track_mode_active:
                    luma = vc[0] * 0.299 + vc[1] * 0.587 + vc[2] * 0.114
                    nc   = (0, 0, 0) if luma > 128 else (255, 255, 255)
                    nf   = pygame.font.SysFont("arial", max(8, cs // 4))
                    ns   = nf.render(str(disp_moves[disp_pos]), True, nc)
                    screen.blit(ns, ns.get_rect(center=(px + (cs // 6), py + cs // 6)))

        # Draw player piece (uses base-class helper)
        self._draw_player_piece(screen)

    def _render_game_specific_stats(
        self, screen: pygame.Surface, stats_panel: UIPanel
    ) -> None:
        """Render time, move count, block count, and end message."""
        stats_bounds = stats_panel.get_bounds("STATS_PANEL")
        line_height  = self.font.get_linesize() + UI_SPACE

        # Displayed move count may differ in replay mode
        if (self.game_state == GameState.ENDGAME and self.replay_mode_active
                and self.replay_states):
            disp_count = self.replay_states[self.replay_index]["move_count"]
        else:
            disp_count = self.move_count

        if self.game_state in (GameState.INGAME, GameState.ENDGAME):
            rem     = self._remaining_time()
            elapsed = self.final_elapsed if self.game_state == GameState.ENDGAME else self.clock_elapsed
            if rem is not None:
                time_str    = _format_time(rem)
                clock_color = (200, 0, 0) if rem < 30 else (0, 0, 0)
            else:
                time_str    = _format_time(elapsed)
                clock_color = (0, 0, 0)
            clk_s = self.font.render(time_str, True, clock_color)
            clk_y = stats_panel.get_line_y("STATS_PANEL", 9, line_height)
            screen.blit(clk_s, clk_s.get_rect(centerx=stats_bounds["center_x"], top=clk_y))

            #if self.get_selection("bounce") == "bounce":
            self.bounce_moves = self.total_move_count - self.attempt_count
            tm_label = "move" if self.bounce_moves == 1 else "moves"
            tm_s     = self.font.render(f"{self.bounce_moves} {tm_label}", True, (0, 0, 0))
            tm_y     = stats_panel.get_line_y("STATS_PANEL", 2, line_height)
            screen.blit(tm_s, tm_s.get_rect(centerx=stats_bounds["center_x"], top=tm_y))

            bl_label = "block" if self.attempt_count == 1 else "blocks"
            bl_s     = self.font.render(f"{self.attempt_count} {bl_label}", True, (0, 0, 0))
            bl_y     = stats_panel.get_line_y("STATS_PANEL", 3, line_height)
            screen.blit(bl_s, bl_s.get_rect(centerx=stats_bounds["center_x"], top=bl_y))






        if self.game_state == GameState.ENDGAME and self.end_state:
            end_messages = {
                "maze_complete": ("maze completed", (0, 160, 0)),
                "no_moves":      ("no legal moves", (200, 0, 0)),
                "resignation":   ("resigned",        (107, 50, 71)),
                "timeout":       ("time's up",       (0, 0, 200)),
            }
            msg, msg_color = end_messages.get(self.end_state, ("game over", (0, 0, 0)))
            em_s = self.font_large.render(msg, True, msg_color)
            em_y = stats_panel.get_line_y("STATS_PANEL", 6, line_height)
            screen.blit(em_s, em_s.get_rect(centerx=stats_bounds["center_x"], top=em_y))

    # ================================================================== #
    #  Menu preview                                                       #
    # ================================================================== #

    def _render_menu_preview(self, screen: pygame.Surface) -> None:
        """Draw the MENU board preview."""
        cs  = self.current_cell_size
        brd = self.get_selection("board")

        cache_key = (
            brd,
            self.get_selection("piece"),
            self.get_selection("length"),
            self.get_selection("density"),
        )

        if self.menu_preview_cache is None or self.menu_preview_cache[0] != cache_key:
            prev_piece   = self.get_selection("piece")
            prev_length  = self.get_selection("length")
            prev_density = self.get_selection("density")
            move_func    = pk.get_move_func(prev_piece)
            prev_rng     = _make_rng(None)
            mn_len, mx_len = adaptive_path_lengths(brd, move_func, prev_length, rng=prev_rng)

            pp, po = generate_maze_path_and_obstacles(
                brd, mn_len, mx_len, move_func,
                max_attempts=100, time_budget=0.5, rng=prev_rng, density=prev_density)
            self.menu_preview_cache = (cache_key, pp, po or set())
            self.menu_preview_pos   = pp[0] if pp else None

        _, prev_path, prev_obs = self.menu_preview_cache
        if not prev_path:
            return

        if (self.menu_preview_pos is None
                or not (0 <= self.menu_preview_pos[0] < brd
                        and 0 <= self.menu_preview_pos[1] < brd)):
            self.menu_preview_pos = prev_path[0]

        pf = pygame.font.SysFont("arial", max(6, cs // 4))
        for i, (gx, gy) in enumerate(prev_path[:-1]):
            px, py = self.board_renderer.to_pixel(gx, gy)
            color  = LT_MOVE if (gx + gy) % 2 == 0 else DK_MOVE
            pygame.draw.rect(screen, color, (px + 1, py + 1, cs - 1, cs - 1))
            luma = color[0] * 0.299 + color[1] * 0.587 + color[2] * 0.114
            nc = (0, 0, 0) if luma > 128 else (255, 255, 255)
            ns = pf.render(str(i), True, nc)
            screen.blit(ns, ns.get_rect(center=(px + (cs // 6), py + cs // 6)))
        tx, ty = prev_path[-1]
        px, py = self.board_renderer.to_pixel(tx, ty)
        # Draw target image on top in menu preview
        if cs > 0:
            scaled_target = pygame.transform.smoothscale(self.target_img, (cs, cs))
            screen.blit(scaled_target, (px, py))

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
        """Render MENU_PANEL and BUTTON_PANEL on the left panel."""
        btn_w       = UI_SPACE
        line_height = self.font.get_linesize() + UI_SPACE

        # ---- MENU_PANEL ----
        menu_bounds      = left_panel.get_bounds("MENU_PANEL")
        text_x           = menu_bounds["left"] + UI_SPACE
        menu_panel_items = [(i, (lbl, vals, cur))
                            for i, (lbl, vals, cur) in enumerate(self.menu_items)
                            if lbl != "piece"]

        max_lbl_w = max(
            self.font.render(lbl, True, (0, 0, 0)).get_width()
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

        is_playable = self.get_selection("board") >= self._get_min_board_size(
            self.get_selection("piece"))

        self.buttons["enter_code"].active   = self.game_state == GameState.MENU
        self.buttons["enter_code"].text     = ("cancel code input" if self.seed_mode_active
                                               else "enter share code")
        self.buttons["enter_code"].bg_color = (224, 64, 128) if self.seed_mode_active else (224, 0, 96)
        self.buttons["enter_code"].rect     = left_panel.get_widget_rect("MENU_PANEL",
                                                                         9, BTW, BTH)
        self.buttons["enter_code"].draw(screen)

        if self.game_state == GameState.MENU and self.seed_mode_active:
            input_y = left_panel.get_line_y("MENU_PANEL", 9, line_height)
            input_x = menu_bounds["left"] + (menu_bounds["width"] // 2) - BTW * .75
            self.codec_input.rect = pygame.Rect(input_x, input_y, BTW * 1.5, BTH)
            self.codec_input.draw(screen)

        if self.puzzle_code and self.game_state in (GameState.INGAME, GameState.ENDGAME):
            code_y   = left_panel.get_line_y("MENU_PANEL", 10, line_height)
            cs2_surf = self.font.render(self.puzzle_code, True, (0, 0, 0))
            screen.blit(cs2_surf, cs2_surf.get_rect(
                center=(menu_bounds["center_x"], code_y + line_height // 2)))
            self.buttons["copy_code"].active    = True
            self.buttons["copy_code"].bg_color  = (224, 64, 128) if self.copy_clicked else (224, 0, 96)
            self.buttons["copy_code"].text      = ("code copied!" if self.copy_clicked
                                                   else "copy share code")
            self.buttons["copy_code"].rect      = left_panel.get_widget_rect("MENU_PANEL",
                                                                             9, BTW, BTH)
            self.buttons["copy_code"].draw(screen)
        else:
            self.buttons["copy_code"].active = False


        # ---- BUTTON_PANEL ----
        button_bounds = left_panel.get_bounds("BUTTON_PANEL")

        if self.game_state == GameState.MENU:
            if not self.seed_mode_active:
                self.buttons["start"].active = is_playable
                self.buttons["start"].rect   = left_panel.get_widget_rect("BUTTON_PANEL",
                                                                          0, BTW, BTH)
                self.buttons["start"].draw(screen)
                if not is_playable:
                    mb  = self._get_min_board_size(self.get_selection("piece"))
                    ws  = self.font.render(f"board must be >= {mb}", True, (200, 0, 0))
                    wby = self.buttons["start"].rect.bottom + 4
                    screen.blit(ws, ws.get_rect(centerx=button_bounds["center_x"], top=wby))
            elif self._is_valid_codec_length():
                self.buttons["start"].active = True
                self.buttons["start"].rect   = left_panel.get_widget_rect("BUTTON_PANEL",
                                                                          0, BTW, BTH)
                self.buttons["start"].draw(screen)

            self.buttons["guide_mode"].active = True
            self.buttons["guide_mode"].text   = ("hide move guide" if self.guide_mode_active
                                                 else "show move guide")
            self.buttons["guide_mode"].rect   = left_panel.get_widget_rect("BUTTON_PANEL",
                                                                           2, BTW, BTH)
            self.buttons["guide_mode"].draw(screen)

            self.buttons["track_mode"].active = True
            self.buttons["track_mode"].text   = ("hide move track" if self.track_mode_active
                                                 else "show move track")
            self.buttons["track_mode"].rect   = left_panel.get_widget_rect("BUTTON_PANEL",
                                                                           4, BTW, BTH)
            #self.buttons["track_mode"].draw(screen)

        elif self.game_state == GameState.ENDGAME:
            # Deactivate INGAME-only buttons so they cannot fire ghost clicks
            for btn_key in ("resign", "undo_mode"):
                self.buttons[btn_key].active = False

            self.buttons["guide_mode"].active = True
            self.buttons["guide_mode"].text = ("hide move guide" if self.guide_mode_active
                                               else "show move guide")
            self.buttons["guide_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL",
                                                                         2, BTW, BTH)
            self.buttons["guide_mode"].draw(screen)



            self.buttons["replay_mode"].active = True
            self.buttons["replay_mode"].text   = "end replay" if self.replay_mode_active else "start replay"
            self.buttons["replay_mode"].rect   = left_panel.get_widget_rect("BUTTON_PANEL",
                                                                            6, BTW, BTH)
            self.buttons["replay_mode"].draw(screen)

            self.buttons["reveal"].active = True
            self.buttons["reveal"].text   = ("hide maze path" if self.reveal_mode_active
                                             else "show maze path")
            self.buttons["reveal"].rect   = left_panel.get_widget_rect("BUTTON_PANEL",
                                                                       0, BTW, BTH)
            #self.buttons["reveal"].draw(screen)

            track_enabled = not self.reveal_mode_active
            self.buttons["track_mode"].active = track_enabled
            self.buttons["track_mode"].text   = ("hide move track" if self.track_mode_active
                                                 else "show move track")
            self.buttons["track_mode"].rect   = left_panel.get_widget_rect("BUTTON_PANEL",
                                                                           4, BTW, BTH)
            self.buttons["track_mode"].draw(screen)

            self.buttons["retry"].active = self.last_puzzle_seed is not None
            self.buttons["retry"].rect   = left_panel.get_widget_rect("MENU_PANEL",
                                                                      7, BTW, BTH)
            self.buttons["retry"].draw(screen)

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

            self.buttons["new_game"].active = True
            self.buttons["new_game"].rect   = left_panel.get_widget_rect("BUTTON_PANEL",
                                                                         8, BTW, BTH)
            self.buttons["new_game"].draw(screen)

        elif self.game_state == GameState.INGAME:
            # Deactivate ENDGAME-only buttons so they cannot fire ghost clicks
            for btn_key in ("start", "new_game", "retry", "reveal", "replay_mode",
                            "replay_prev", "replay_next"):
                self.buttons[btn_key].active = False

            self.buttons["guide_mode"].active = True
            self.buttons["guide_mode"].text = ("hide move guide" if self.guide_mode_active
                                                 else "show move guide")
            self.buttons["guide_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL",
                                                                         2, BTW, BTH)
            self.buttons["guide_mode"].draw(screen)

            self.buttons["track_mode"].active = True
            self.buttons["track_mode"].text = ("hide move track" if self.track_mode_active
                                                 else "show move track")
            self.buttons["track_mode"].rect = left_panel.get_widget_rect("BUTTON_PANEL",
                                                                         4, BTW, BTH)
            self.buttons["track_mode"].draw(screen)

            can_undo = len(self.replay_states) > 1
            if can_undo:
                self.buttons["undo_mode"].active = True
                self.buttons["undo_mode"].rect   = left_panel.get_widget_rect("BUTTON_PANEL",
                                                                              6, BTW, BTH)
                self.buttons["undo_mode"].draw(screen)
            else:
                self.buttons["undo_mode"].active = False

            self.buttons["resign"].active = True
            self.buttons["resign"].rect   = left_panel.get_widget_rect("BUTTON_PANEL",
                                                                       8, BTW, BTH)
            self.buttons["resign"].draw(screen)

        # Peek button (INGAME or ENDGAME, bottom left)
        if self.game_state in (GameState.INGAME, GameState.ENDGAME) and self.maze_path is not None:
            self.buttons["peek_mode"].active = True
            self.buttons["peek_mode"].text   = "hide" if self.peek_mode_visible else "peek"
            self.buttons["peek_mode"].rect   = pygame.Rect(
                msg_left + UI_SPACE * 3, msg_bottom - UI_SPACE * 5, BTW // 2, BTH)
            self.buttons["peek_mode"].draw(screen)
        else:
            self.buttons["peek_mode"].active = False

        # Exit button (always, bottom right)
        self.buttons["exit"].rect = pygame.Rect(
            msg_right - UI_SPACE * 10, msg_bottom - int(UI_SPACE * 5), BTW // 2, BTH)
        self.buttons["exit"].draw(screen)

    # ================================================================== #
    #  Right-panel rendering                                              #
    # ================================================================== #

    def _render_right_panel(
        self, screen: pygame.Surface, right_panel: UIPanel,
    ) -> None:
        """Render PIECE_PANEL and STATS_PANEL on the right panel."""
        btn_w       = UI_SPACE
        line_height = self.font.get_linesize() + UI_SPACE

        # ---- PIECE_PANEL ----
        piece_bounds = right_panel.get_bounds("PIECE_PANEL")
        right_tx     = piece_bounds["left"] + UI_SPACE

        piece_idx                = self.label_to_index["piece"]
        _, piece_vals, piece_cur = self.menu_items[piece_idx]
        piece_name               = piece_vals[piece_cur]

        p_line_y  = right_panel.get_line_y("PIECE_PANEL", 0, line_height)
        p_row_cy  = p_line_y + btn_w // 2
        lbl_s     = self.font.render("piece:", True, (0, 0, 0))
        p_minus_x = lbl_s.get_rect(midleft=(right_tx, p_row_cy)).right + UI_SPACE
        p_plus_x  = piece_bounds["right"] - UI_SPACE * 4

        sel_s = self.font_large.render(piece_name, True, (0, 0, 0))
        screen.blit(sel_s, sel_s.get_rect(center=(piece_bounds["center_x"], p_row_cy + 8)))

        if self.game_state == GameState.MENU:
            pm_r = pygame.Rect(p_minus_x - btn_w, p_line_y, int(btn_w * 1.5), int(btn_w * 1.5))
            pygame.draw.rect(screen, DK_SQUARE, pm_r)
            screen.blit(self.font.render("<", True, (0, 160, 0)),
                        self.font.render("<", True, (0, 160, 0)).get_rect(center=pm_r.center))
            self.widget_rects[("minus", piece_idx)] = pm_r

            pp_r = pygame.Rect(p_plus_x - btn_w, p_line_y, int(btn_w * 1.5), int(btn_w * 1.5))
            pygame.draw.rect(screen, DK_SQUARE, pp_r)
            screen.blit(self.font.render(">", True, (220, 0, 0)),
                        self.font.render(">", True, (220, 0, 0)).get_rect(center=pp_r.center))
            self.widget_rects[("plus", piece_idx)] = pp_r

        move_text = pk.get_piece_move_sets_text(piece_name)
        info_y    = p_line_y + sel_s.get_height() + line_height
        if move_text:
            mt_s = self.font.render(move_text, True, (80, 80, 80))
            screen.blit(mt_s, mt_s.get_rect(centerx=piece_bounds["center_x"], top=info_y))
            info_y += self.font.get_linesize() + UI_SPACE

        is_playable = self.get_selection("board") >= self._get_min_board_size(piece_name)
        if self.game_state == GameState.MENU and not is_playable:
            mb     = self._get_min_board_size(piece_name)
            warn_s = self.font.render("use a larger board for this piece", True, (160, 0, 0))
            screen.blit(warn_s, warn_s.get_rect(centerx=piece_bounds["center_x"], top=info_y))

        # ---- STATS_PANEL ----
        self._render_game_specific_stats(screen, right_panel)

    # ================================================================== #
    #  Full-frame render                                                  #
    # ================================================================== #

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

        area_left   = msg_right + margin
        area_top    = margin
        area_right  = right_left - margin
        area_bottom = win_height - margin

        # Sync board model size in MENU
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
        """Process one pygame event; returns False if the game should quit."""
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
                    break

            if self.game_state == GameState.INGAME:
                grid_pos = self.board_renderer.to_grid(mx, my)
                if grid_pos is not None:
                    self.make_move(grid_pos)

            if self.game_state == GameState.MENU:
                grid_pos = self.board_renderer.to_grid(mx, my)
                if grid_pos is not None:
                    self.menu_preview_pos = grid_pos

        return True