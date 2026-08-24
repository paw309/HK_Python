"""
vexillum_controller.py

Game controller for Vexillum v01.
Manages game state, move validation, flag tracking, and rendering.
Inherits common functionality from BaseGameController.
"""

import os
import time
import math
from collections import deque

import pygame
from typing import Optional, List, Tuple, Set, Dict, Any

# sharedlib imports (BASE_DIR must already be on sys.path)
import piecekeeper as pk
from gameboard import BoardModel, BoardRenderer
from uipanel import UIPanel
from text_input import TextInput
from puzzle_codec import encode_params, decode_params
from widgets import Button
from common_utils import clamp as _clamp
from move_system import get_legal_moves_for_board
from move_hint import calculate_hint_degrees
from base_game_controller import BaseGameController, GameState

from vexillum_generator import generate_open_path_with_flags

# --- constants shared with the controller ---
BOARD_MIN         = 5
BOARD_MAX         = 16
BOARD_DEFAULT     = 8
FPS               = 60
UI_SPACE          = 10
BTW               = int(UI_SPACE * 15)
BTH               = int(UI_SPACE * 3)
CODEC_TEXT_LENGTH = 16
MAX_CLOCK_SECONDS = 330
CLOCK_MODES = ["game", "move"]

PATH_LENGTH_CHOICES = ["short", "medium", "long", "super"]
PATH_LENGTH_MAP     = {"short": 2, "medium": 3, "long": 4, "super": 6}

FLAG_DENSITY_CHOICES = ["low", "medium", "high"]
FLAG_DENSITY_MAP     = {"low": 0.1, "medium": 0.25, "high": 0.6}

FLAG_ORDER_CHOICES = ["any", "only", "next"]

# Even-parity pieces that cannot complete a full Hamiltonian tour
EXCLUDED_PIECES = {"bishop", "ferz", "dabbaba", "alfil", "threeleaper", "tripper", "camel"}

# Colors
LT_SQUARE  = (255, 255, 240)
DK_SQUARE  = (232, 200, 150)
LT_VISITED = (224, 224, 224)
DK_VISITED = (192, 192, 192)
GRID_COLOR = (107, 70, 51)
BACK_COLOR = (244, 228, 195)
FLAG_SQ_DK = (128, 160, 225) # (189, 135, 249)
FLAG_SQ_LT = (192, 220, 248) # (220, 195, 248)

FLAG_IMG_FALLBACK_COLORS = {
    "blue":   (30,  100, 220),
    "green":  (50,  180,  50),
    "purple": (140,  70, 210),
    "red":    (220,  40,  40),
    "ivory":  (200, 175, 130),
    "tan":    (170, 140,  95),
}

# Note: path_length uses 2 bits, so only "short"/"medium"/"long" are codec-compatible.
# "super" is a valid in-game choice but cannot be share-coded; start_game falls
# back gracefully (encode_params will raise and puzzle_code is left empty).
captureflags_schema = [
    ("board",        4, lambda v: int(v) - BOARD_MIN),
    ("path_length",  2, {"short": 0, "medium": 1, "long": 2}),
    ("flag_density", 2, {"low":   0, "medium": 1, "high":  2}),
    ("flag_order",   2, {"any":   0, "only":   1, "next":  2}),
]


def get_globally_valid_pieces() -> List[str]:
    """Return piece names valid for any board size (excluding even-parity pieces)."""
    return [p for p in pk.PIECE_LIST if p not in EXCLUDED_PIECES]


def _format_clock_seconds(seconds) -> str:
    if seconds is None:
        seconds = 0
    seconds = max(0, int(seconds))
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins}:{secs:02d}"


def _display_for_selection(clock_selected) -> str:
    if clock_selected == 0:
        return "infinity"
    return _format_clock_seconds(clock_selected)


class CaptureFlagsController(BaseGameController):
    """Controls game logic and rendering for Vexillum v01."""

    def __init__(self, board_model: BoardModel, board_renderer: BoardRenderer,
                 menu_items: list, label_to_index: dict,
                 font: pygame.font.Font, font_large: pygame.font.Font,
                 base_dir: str):
        super().__init__(
            board_model, board_renderer, menu_items, label_to_index,
            font, font_large, base_dir, captureflags_schema,
        )

        # Override base class defaults for vexillum
        self.guide_mode_active = False
        self.track_mode_active = False

        # Flag-specific state
        self.flags_dir      = os.path.join(base_dir, "assets", "flags")
        self.path:  List[Tuple[int, int]]                    = []
        self.flags: List[Tuple[int, int]]                    = []
        self.flags_set:   Set[Tuple[int, int]]               = set()
        self.flags_index: Dict[Tuple[int, int], int]         = {}
        self.flags_reached:             Set[Tuple[int, int]] = set()
        self.flags_reached_in_order:    Set[Tuple[int, int]] = set()
        self.flags_reached_out_of_order: Set[Tuple[int, int]] = set()
        self.flag_images: Dict[str, Optional[pygame.Surface]] = {}
        self.menu_preview_cache = None
        self.preview_pos: Optional[Tuple[int, int]] = None

        # Per-move clock tracking
        self.move_start_time: Optional[float] = None

        # Playability state (cached, updated when board or piece changes)
        self.is_piece_playable: bool     = True
        self.min_board_size:    Optional[int] = None

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
        """Validate codec text and apply settings. Returns (ok, params) or (False, None)."""
        try:
            params    = decode_params(codec_text, captureflags_schema)
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

        start      = path[0]
        flags_list = [f for f in flags_list if f != start]

        self.path                        = path
        self.flags                       = flags_list
        self.flags_set                   = set(flags_list)
        self.flags_index                 = {pos: i for i, pos in enumerate(flags_list)}
        self.flags_reached               = set()
        self.flags_reached_in_order      = set()
        self.flags_reached_out_of_order  = set()

        self.player_pos    = start
        self.visited       = {start}
        self.visited_moves = {start: 0}
        self.move_count    = 0

        # Reset mode flags to vexillum defaults on game start
        self.guide_mode_active = False
        self.hint_mode_active  = False

        self._update_legal_moves()
        return True

    def _validate_move(self, target: Tuple[int, int]) -> bool:
        return target in self.legal_moves

    def _game_specific_make_move(self, target: Tuple[int, int]) -> bool:
        self.move_count += 1

        if target in self.flags_set and target not in self.flags_reached:
            flag_order_mode = self.get_selection("flag order")
            if flag_order_mode == "next":
                next_target_idx = next(
                    (i for i in range(len(self.flags)) if self.flags[i] not in self.flags_reached),
                    -1
                )
                self.flags_reached.add(target)
                if self.flags_index[target] == next_target_idx:
                    self.flags_reached_in_order.add(target)
                else:
                    self.flags_reached_out_of_order.add(target)
            else:
                ordinal  = len(self.flags_reached) + 1
                cardinal = self.flags_index[target] + 1
                self.flags_reached.add(target)
                if ordinal == cardinal:
                    self.flags_reached_in_order.add(target)
                else:
                    self.flags_reached_out_of_order.add(target)

        return True

    def _check_endgame_conditions(self) -> Optional[str]:
        if len(self.flags_reached) == len(self.flags):
            return "all_flags_reached"
        elif not self.legal_moves:
            return "no_moves"
        return None

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

    def _capture_game_state(self) -> Dict[str, Any]:
        return {
            "pos":                        self.player_pos,
            "visited":                    self.visited.copy(),
            "flags_reached":              self.flags_reached.copy(),
            "flags_reached_in_order":     self.flags_reached_in_order.copy(),
            "flags_reached_out_of_order": self.flags_reached_out_of_order.copy(),
            "visited_moves":              self.visited_moves.copy(),
            "move_count":                 self.move_count,
        }

    def _restore_game_state(self, state: Dict[str, Any]) -> None:
        self.player_pos               = state["pos"]
        self.visited                  = state["visited"].copy()
        self.visited_moves            = state["visited_moves"].copy()
        self.flags_reached            = state["flags_reached"].copy()
        self.flags_reached_in_order   = state.get("flags_reached_in_order",    set()).copy()
        self.flags_reached_out_of_order = state.get("flags_reached_out_of_order", set()).copy()
        self.move_count = state.get("move_count",
                                    max(state["visited_moves"].values(), default=0))
        self._update_legal_moves()
        if self.hint_mode_active:
            self._calculate_hint_degrees()
        else:
            self.hint_degrees = {}

    def _update_legal_moves(self) -> None:
        piece_name = self.get_selection("piece")
        cols, rows = self.board_model.cols, self.board_model.rows
        self.legal_moves = get_legal_moves_for_board(
            piece_name, *self.player_pos, cols, rows, self.visited)

    def _calculate_hint_degrees(self) -> None:
        piece_name = self.get_selection("piece")
        self.hint_degrees = calculate_hint_degrees(
            piece_name, self.player_pos,
            self.board_model.cols, self.board_model.rows, self.visited)

    def _render_game_specific_board(self, screen: pygame.Surface) -> None:
        """Draw INGAME/ENDGAME board overlays (flags, visited squares, arrows, hints, piece)."""
        if self.game_state not in (GameState.INGAME, GameState.ENDGAME):
            return

        cs     = self.current_cell_size
        fo_val = self.get_selection("flag order")

        # Get display state (may differ when replaying)
        if self.game_state == GameState.ENDGAME and self.replay_mode_active and self.replay_states:
            disp = self.replay_states[self.replay_index]
            disp_pos                        = disp["pos"]
            disp_visited                    = disp["visited"]
            disp_visited_moves              = disp["visited_moves"]
            disp_flags_reached              = disp["flags_reached"]
            disp_flags_reached_in_order     = disp.get("flags_reached_in_order",    set())
            disp_flags_reached_out_of_order = disp.get("flags_reached_out_of_order", set())
        else:
            disp_pos                        = self.player_pos
            disp_visited                    = self.visited
            disp_visited_moves              = self.visited_moves
            disp_flags_reached              = self.flags_reached
            disp_flags_reached_in_order     = self.flags_reached_in_order
            disp_flags_reached_out_of_order = self.flags_reached_out_of_order

        # Visited squares (skip current position and flag squares handled below)
        nf_move_vis = pygame.font.SysFont("arial", max(8, cs // 5))
        for vx, vy in disp_visited:
            if (vx, vy) == disp_pos:
                continue
            if (vx, vy) in self.flags_set:
                if fo_val != "next" or (vx, vy) not in disp_flags_reached_out_of_order:
                    continue
            px, py = self.board_renderer.to_pixel(vx, vy)
            parity = (vx + vy) % 2
            vcolor = LT_VISITED if parity == 0 else DK_VISITED
            pygame.draw.rect(screen, vcolor, (px + 3, py + 3, cs - 4, cs - 4))
            if self.track_mode_active and (vx, vy) in disp_visited_moves:
                luma      = vcolor[0] * 0.299 + vcolor[1] * 0.587 + vcolor[2] * 0.114
                num_color = (0, 0, 0) if luma > 128 else (255, 255, 255)
                ns = nf_move_vis.render(str(disp_visited_moves[(vx, vy)]), True, num_color)
                screen.blit(ns, ns.get_rect(center=(px + (cs // 6), py + cs // 6)))

        # Flag images
        nf_card = pygame.font.SysFont("arial", max(7, cs // 4))
        nf_move = pygame.font.SysFont("arial", max(8, cs // 5))
        if fo_val == "next":
            next_target_idx = next(
                (i for i in range(len(self.flags)) if self.flags[i] not in disp_flags_reached),
                -1
            )
        else:
            next_target_idx = len(disp_flags_reached)

        for flag_idx, flag_pos in enumerate(self.flags):
            fx, fy = flag_pos
            px, py = self.board_renderer.to_pixel(fx, fy)

            if fo_val == "only":
                is_next = (flag_idx == next_target_idx)
                if flag_pos in disp_flags_reached_in_order:
                    img_key = "blue"
                elif flag_pos in disp_flags_reached_out_of_order:
                    img_key = "red"
                elif is_next:
                    img_key = "green"
                else:
                    img_key = "tan" if (fx + fy) % 2 == 0 else "ivory"
            elif fo_val == "next":
                if flag_pos in disp_flags_reached_in_order:
                    img_key = "blue"
                elif flag_pos in disp_flags_reached_out_of_order:
                    img_key = "red"
                elif flag_idx == next_target_idx:
                    img_key = "green"
                else:
                    continue  # future flags hidden in "next" mode
            else:  # "any"
                img_key = "purple" if flag_pos in disp_flags_reached \
                    else ("tan" if (fx + fy) % 2 == 0 else "ivory")

            self._draw_flag(screen, img_key, px, py, cs)

            if self.track_mode_active and flag_pos in disp_visited_moves:
                ns = nf_move.render(str(disp_visited_moves[flag_pos]), True, (0, 0, 0))
                screen.blit(ns, ns.get_rect(center=(px + (cs // 6), py + cs // 6)))

            if fo_val == "only":
                card_surf = nf_card.render(str(flag_idx + 1), True, (0, 0, 0))
                screen.blit(card_surf, (px + cs - card_surf.get_width() - 20, py + cs - (cs // 3)))

        # Guide arrows
        if self.guide_mode_active and self.arrows and disp_pos:
            if self.replay_mode_active and self.game_state == GameState.ENDGAME:
                moves_for_arrows = get_legal_moves_for_board(
                    self.get_selection("piece"), *disp_pos,
                    self.board_model.cols, self.board_model.rows, disp_visited)
            else:
                moves_for_arrows = self.legal_moves
            self._draw_arrows(screen, moves_for_arrows, disp_pos)

        # Hint degrees (Warnsdorff numbers)
        if self.hint_mode_active and self.hint_degrees:
            hf = pygame.font.SysFont("arial", max(8, cs // 5))
            for (hx, hy), degree in self.hint_degrees.items():
                hpx, hpy = self.board_renderer.to_pixel(hx, hy)
                bg   = LT_SQUARE if (hx + hy) % 2 == 0 else DK_SQUARE
                luma = bg[0] * 0.299 + bg[1] * 0.587 + bg[2] * 0.114
                hc   = (107, 50, 71) if luma > 128 else (255, 255, 255)
                hs   = hf.render(str(degree), True, hc)
                screen.blit(hs, hs.get_rect(center=(hpx + cs - (cs // 6), hpy + (cs // 6))))

        # Player piece
        if disp_pos:
            ppx, ppy = self.board_renderer.to_pixel(*disp_pos)
            piece_rect = pygame.Rect(ppx + 1, ppy + 1, cs - 2, cs - 2)
            try:
                pk.draw_piece(screen, piece_rect, self.get_selection("piece"))
            except Exception:
                pygame.draw.ellipse(screen, (0, 0, 0), piece_rect)

    def _render_game_specific_stats(
        self, screen: pygame.Surface, stats_panel: UIPanel
    ) -> None:
        """Stats are rendered as part of _render_right_panel() for this game."""
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
                                  f, (255,255,255), (107, 50, 71),    self.resign_game),
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
    #  Overrides with vexillum-specific behaviour                     #
    # ================================================================== #

    def _update_cell_size(self, area_left, area_top, area_width, area_height) -> None:
        old_cs = self.current_cell_size
        super()._update_cell_size(area_left, area_top, area_width, area_height)
        if self.current_cell_size != old_cs and self.current_cell_size > 0:
            self._load_flag_images(self.current_cell_size)

    def toggle_guide_mode(self) -> None:
        super().toggle_guide_mode()
        #if self.guide_mode_active:
            #self.hint_mode_active = False
            #self.hint_degrees.clear()

    def toggle_hint_mode(self) -> None:
        self.hint_mode_active = not self.hint_mode_active
        if self.hint_mode_active:
            #self.guide_mode_active = False
            if self.player_pos:
                self._calculate_hint_degrees()
        else:
            self.hint_degrees = {}

    def new_game(self) -> None:
        super().new_game()
        self.preview_pos = None
        self.path = []
        self.move_start_time = None

    def make_move(self, target_pos: Tuple[int, int]) -> None:
        """Override to reset per-move clock after each successful move."""
        if self.game_state != GameState.INGAME:
            return
        if not self._validate_move(target_pos):
            return

        super().make_move(target_pos)

        if self._is_per_move_mode():
            # Prevent base class per-game clock from running
            self.clock_start_time = None
            # Reset the per-move countdown (only if game is still running)
            if self.game_state == GameState.INGAME:
                self.move_start_time = time.time()

    def update(self, dt: int) -> None:
        """Per-frame update: handle per-move clock timeout."""
        super().update(dt)

        if self.game_state == GameState.INGAME:
            if self._is_per_move_mode() and self.move_start_time is not None:
                clock_sel = self.get_selection("clock")
                if time.time() - self.move_start_time >= clock_sel:
                    self.final_elapsed = int(time.time() - self.move_start_time)
                    self.end_state = "timeout"
                    self.game_state = GameState.ENDGAME

    # ------------------------------------------------------------------ #
    #  asset loading                                                       #
    # ------------------------------------------------------------------ #

    def _load_flag_images(self, cell_size: int) -> None:
        flag_img_size = max(8, int(cell_size * 0.68))
        _flag_img_names = {
            "black":  "flag_black.png",
            "blue":   "flag_blue.png",
            "green":  "flag_green.png",
            "ivory":  "flag_ivory.png",
            "orange": "flag_orange.png",
            "purple": "flag_purple.png",
            "red":    "flag_red.png",
            "tan":    "flag_tan.png",
            "white":  "flag_white.png",
            "yellow": "flag_yellow.png",
        }
        self.flag_images.clear()
        for key, fname in _flag_img_names.items():
            fpath = os.path.join(self.flags_dir, fname)
            try:
                fimg = pygame.image.load(fpath).convert_alpha()
                self.flag_images[key] = pygame.transform.smoothscale(
                    fimg, (flag_img_size, flag_img_size))
            except Exception:
                self.flag_images[key] = None

    # ------------------------------------------------------------------ #
    #  game-specific rendering helpers                                     #
    # ------------------------------------------------------------------ #

    def _draw_flag(self, screen: pygame.Surface,
                   img_key: str, px: int, py: int, cs: int) -> None:
        """Draw a flag image (or fallback rectangle) centred on the given cell."""
        fimg = self.flag_images.get(img_key)
        if fimg:
            screen.blit(fimg, fimg.get_rect(center=(px + cs // 2, py + cs // 2)))
        else:
            fb_color = FLAG_IMG_FALLBACK_COLORS.get(img_key, (128, 128, 128))
            fb_sz    = max(6, int(cs * 0.68))
            pygame.draw.rect(screen, fb_color,
                             (px + (cs - fb_sz) // 2, py + (cs - fb_sz) // 2, fb_sz, fb_sz))

    def _draw_peek_thumbnail(self, screen: pygame.Surface,
                              left_panel: UIPanel, line_height: int) -> None:
        """Draw the peek-mode path thumbnail inside BUTTON_PANEL."""
        cols, rows = self.board_model.cols, self.board_model.rows
        if not (self.path and self.peek_mode_visible):
            return
        if cols < 1 or rows < 1:
            return

        button_bounds = left_panel.get_bounds("BUTTON_PANEL")
        peek_line     = 0
        thumb_area_y  = left_panel.get_line_y("BUTTON_PANEL", peek_line, line_height)
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
                if (gx, gy) in flag_positions:
                    color = FLAG_SQ_LT if (gx + gy) % 2 == 0 else FLAG_SQ_DK
                else:
                    color = LT_SQUARE if (gx + gy) % 2 == 0 else DK_SQUARE
                pygame.draw.rect(screen, color,
                                 (tx + gx * max_cell, ty + gy * max_cell, max_cell, max_cell))

        font_size = max(6, int(max_cell * 0.6))
        num_font  = pygame.font.SysFont("arial", font_size)
        for path_idx, (gx, gy) in enumerate(self.path):
            if 0 <= gx < cols and 0 <= gy < rows:
                ns = num_font.render(str(path_idx), True, (0, 0, 0))
                screen.blit(ns, ns.get_rect(center=(
                    tx + gx * max_cell + max_cell // 2,
                    ty + gy * max_cell + max_cell // 2)))

        pygame.draw.rect(screen, GRID_COLOR, (tx - 1, ty - 1, tw + 2, th + 2), 1)

    def _render_menu_preview(self, screen: pygame.Surface) -> None:
        """Draw the MENU board with a flag density preview."""
        cs         = self.current_cell_size
        prev_board = self.get_selection("board")
        prev_piece = self.get_selection("piece")

        if (self.board_model.cols != prev_board or self.board_model.rows != prev_board):
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
            prev_piece, prev_cx, prev_cy, prev_board, prev_board, set())

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

        ppx, ppy = self.board_renderer.to_pixel(prev_cx, prev_cy)
        piece_rect = pygame.Rect(ppx + 1, ppy + 1, cs - 2, cs - 2)
        try:
            pk.draw_piece(screen, piece_rect, prev_piece)
        except Exception:
            pygame.draw.ellipse(screen, (0, 0, 0), piece_rect)

        if self.guide_mode_active and self.arrows:
            self._draw_arrows(screen, prev_legal, self.preview_pos)

    def _render_left_panel(self, screen: pygame.Surface, left_panel: UIPanel,
                            msg_left: int, msg_right: int, msg_bottom: int) -> None:
        """Render MENU_PANEL and BUTTON_PANEL on left_panel."""
        btn_w       = UI_SPACE
        line_height = self.font.get_linesize() + UI_SPACE

        # ---- MENU_PANEL: selector rows ----
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

        # Enter/cancel share code button
        self.buttons["enter_code"].active   = self.game_state == GameState.MENU
        self.buttons["enter_code"].text     = ("cancel code input" if self.seed_mode_active
                                               else "enter share code")
        self.buttons["enter_code"].bg_color = (224, 64, 128) if self.seed_mode_active else (224, 0, 96)
        self.buttons["enter_code"].rect = left_panel.get_widget_rect("MENU_PANEL", 9, BTW, BTH)
        if self.buttons["enter_code"].active:
            self.buttons["enter_code"].draw(screen)

        if self.game_state == GameState.MENU and self.seed_mode_active:
            input_y = left_panel.get_line_y("MENU_PANEL", 10, line_height)
            input_x = menu_bounds["left"] + (menu_bounds["width"] - BTW) // 5
            self.codec_input.rect = pygame.Rect(input_x, input_y, BTW * 1.5, BTH)
            self.codec_input.draw(screen)

        # Share code display + copy button
        if self.puzzle_code and self.game_state in (GameState.INGAME, GameState.ENDGAME):
            code_y   = left_panel.get_line_y("MENU_PANEL", 10, line_height)
            code_s   = self.font.render(self.puzzle_code, True, (0, 0, 0))
            screen.blit(code_s, code_s.get_rect(
                center=(menu_bounds["center_x"], code_y + line_height // 2)))
            self.buttons["copy_code"].active    = True
            self.buttons["copy_code"].bg_color  = (224, 64, 128) if self.copy_clicked else (224, 0, 96)
            self.buttons["copy_code"].text      = ("code copied!" if self.copy_clicked
                                                   else "copy share code")
            self.buttons["copy_code"].rect      = left_panel.get_widget_rect(
                "MENU_PANEL", 9, BTW, BTH)
            self.buttons["copy_code"].draw(screen)
        else:
            self.buttons["copy_code"].active = False

        # ---- BUTTON_PANEL ----

        # Slot 0: start (MENU)
        if self.seed_mode_active:
            self.buttons["start"].active = (self.game_state == GameState.MENU
                                            and self._is_valid_codec_length())
        else:
            self.buttons["start"].active = self.game_state == GameState.MENU and is_playable
        self.buttons["start"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        if self.buttons["start"].active:
            self.buttons["start"].draw(screen)

        # Slot 0: hint_mode (INGAME)
        self.buttons["hint_mode"].active = self.game_state in (GameState.INGAME, GameState.ENDGAME)
        self.buttons["hint_mode"].text   = "hide degrees" if self.hint_mode_active else "show degrees"
        self.buttons["hint_mode"].rect   = left_panel.get_widget_rect("BUTTON_PANEL",
                                                                      0, BTW, BTH)
        if self.buttons["hint_mode"].active:
            self.buttons["hint_mode"].draw(screen)

        # Slot 2: guide_mode (all states)
        self.buttons["guide_mode"].text   = ("hide move guide" if self.guide_mode_active
                                             else "show move guide")
        self.buttons["guide_mode"].rect   = left_panel.get_widget_rect("BUTTON_PANEL",
                                                                       2, BTW, BTH)
        if self.buttons["guide_mode"].active:
            self.buttons["guide_mode"].draw(screen)

        # Slot 4: track_mode (always)
        self.buttons["track_mode"].active = True
        self.buttons["track_mode"].text   = ("hide move track" if self.track_mode_active
                                             else "show move #'s")
        self.buttons["track_mode"].rect   = left_panel.get_widget_rect("BUTTON_PANEL",
                                                                       4, BTW, BTH)
        self.buttons["track_mode"].draw(screen)

        # Slot 6: undo_mode (INGAME)
        self.buttons["undo_mode"].active = (self.game_state == GameState.INGAME
                                            and len(self.replay_states) > 1)
        self.buttons["undo_mode"].rect   = left_panel.get_widget_rect("BUTTON_PANEL",
                                                                      6, BTW, BTH)
        if self.buttons["undo_mode"].active:
            self.buttons["undo_mode"].draw(screen)

        # Slot 8: resign (INGAME)
        self.buttons["resign"].active = self.game_state == GameState.INGAME
        self.buttons["resign"].rect   = left_panel.get_widget_rect("BUTTON_PANEL", 8, BTW, BTH)
        if self.buttons["resign"].active:
            self.buttons["resign"].draw(screen)

        # Retry: MENU_PANEL slot 6 (ENDGAME)
        self.buttons["retry"].active = (self.game_state == GameState.ENDGAME
                                        and self.last_puzzle_seed is not None)
        self.buttons["retry"].rect   = left_panel.get_widget_rect("MENU_PANEL", 7, BTW, BTH)
        if self.buttons["retry"].active:
            self.buttons["retry"].draw(screen)

        # Slot 6: replay_mode (ENDGAME)
        self.buttons["replay_mode"].active = self.game_state == GameState.ENDGAME
        self.buttons["replay_mode"].text   = "end replay" if self.replay_mode_active else "start replay"
        self.buttons["replay_mode"].rect   = left_panel.get_widget_rect("BUTTON_PANEL",
                                                                        6, BTW, BTH)
        if self.buttons["replay_mode"].active:
            self.buttons["replay_mode"].draw(screen)

        # Replay navigation (reset always, then set conditionally)
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

        # Slot 8: new_game (ENDGAME)
        self.buttons["new_game"].active = self.game_state == GameState.ENDGAME
        self.buttons["new_game"].rect   = left_panel.get_widget_rect("BUTTON_PANEL",
                                                                     8, BTW, BTH)
        if self.buttons["new_game"].active:
            self.buttons["new_game"].draw(screen)

        # Peek button (INGAME or ENDGAME, fixed bottom-left)
        self.buttons["peek_mode"].active     = (self.game_state in (GameState.INGAME, GameState.ENDGAME)
                                                and bool(self.flags))
        self.buttons["peek_mode"].text       = "hide" if self.peek_mode_visible else "peek"
        self.buttons["peek_mode"].bg_color   = DK_SQUARE
        self.buttons["peek_mode"].text_color = (255, 255, 240)
        self.buttons["peek_mode"].rect       = pygame.Rect(
            msg_left + UI_SPACE * 2, msg_bottom - UI_SPACE * 5, BTW // 2, BTH)
        if self.buttons["peek_mode"].active:
            self.buttons["peek_mode"].draw(screen)

        # Exit button (always, fixed bottom-right)
        self.buttons["exit"].rect = pygame.Rect(
            msg_right - UI_SPACE * 10, msg_bottom - int(UI_SPACE * 5), BTW // 2, BTH)
        self.buttons["exit"].draw(screen)

        # Peek thumbnail
        self._draw_peek_thumbnail(screen, left_panel, line_height)

    def _render_right_panel(self, screen: pygame.Surface, right_panel: UIPanel,
                             disp_visited_moves: Dict,
                             disp_flags_reached: Set,
                             disp_flags_reached_in_order: Set,
                             disp_flags_reached_out_of_order: Set) -> None:
        """Render PIECE_PANEL and STATS_PANEL on right_panel."""
        btn_w       = UI_SPACE
        line_height = self.font.get_linesize() + UI_SPACE
        fo_val      = self.get_selection("flag order")

        # ---- PIECE_PANEL ----
        piece_bounds = right_panel.get_bounds("PIECE_PANEL")
        right_tx     = piece_bounds["left"] + UI_SPACE

        piece_idx               = self.label_to_index["piece"]
        _, piece_vals, piece_cur = self.menu_items[piece_idx]
        piece_name_cur          = piece_vals[piece_cur]

        p_line_y = right_panel.get_line_y("PIECE_PANEL", 0, line_height)
        p_row_cy = p_line_y + btn_w // 2
        lbl_s    = self.font.render("piece:", True, (0, 0, 0))
        p_minus_x = lbl_s.get_rect(midleft=(right_tx, p_row_cy)).right + UI_SPACE
        p_plus_x  = piece_bounds["right"] - UI_SPACE * 4

        sel_s = self.font_large.render(piece_name_cur, True, (0, 0, 0))
        screen.blit(sel_s, sel_s.get_rect(center=(piece_bounds["center_x"], p_row_cy + 8)))

        if self.game_state == GameState.MENU:
            pm_r = pygame.Rect(p_minus_x - btn_w, p_line_y, int(btn_w * 1.5), int(btn_w * 1.5))
            pygame.draw.rect(screen, DK_SQUARE, pm_r)
            pm_s = self.font.render("<", True, (0, 160, 0))
            screen.blit(pm_s, pm_s.get_rect(center=pm_r.center))
            self.widget_rects[("minus", piece_idx)] = pm_r

            pp_r = pygame.Rect(p_plus_x - btn_w, p_line_y, int(btn_w * 1.5), int(btn_w * 1.5))
            pygame.draw.rect(screen, DK_SQUARE, pp_r)
            pp_s = self.font.render(">", True, (220, 0, 0))
            screen.blit(pp_s, pp_s.get_rect(center=pp_r.center))
            self.widget_rects[("plus", piece_idx)] = pp_r

        move_text = pk.get_piece_move_sets_text(piece_name_cur)
        info_y    = p_line_y + sel_s.get_height() + line_height
        if move_text:
            mt_s = self.font.render(move_text, True, (80, 80, 80))
            screen.blit(mt_s, mt_s.get_rect(centerx=piece_bounds["center_x"], top=info_y))
            info_y += self.font.get_linesize() + UI_SPACE

        is_playable = self.is_piece_playable
        if self.game_state == GameState.MENU and not is_playable and not self.seed_mode_active:
            min_n     = self.min_board_size
            warn_text = f"minimum {min_n} x {min_n} board for this piece" if min_n is not None else "use a larger board for this piece"
            warn_surf = self.font.render(warn_text, True, (200, 0, 0))
            warn_y    = piece_bounds["top"] + 4 * line_height
            screen.blit(warn_surf, warn_surf.get_rect(
                centerx=piece_bounds["center_x"], top=warn_y))

        # ---- STATS_PANEL ----
        stats_bounds = right_panel.get_bounds("STATS_PANEL")
        s_line = 0

        clock_sel = self.get_selection("clock")
        if self.game_state != GameState.MENU:
            rem = self._remaining_time()
            if rem is not None:
                clock_disp  = _format_clock_seconds(rem)
                clock_color = (200, 0, 0) if rem < 30 else (0, 0, 0)
            else:
                clock_disp  = _format_clock_seconds(self.clock_elapsed)
                clock_color = (0, 0, 0)
            clk_s = self.font.render(clock_disp, True, clock_color)
            clk_y = right_panel.get_line_y("STATS_PANEL", 9, line_height)
            screen.blit(clk_s, clk_s.get_rect(centerx=stats_bounds["center_x"], top=clk_y))
            s_line += 1

        if self.game_state in (GameState.INGAME, GameState.ENDGAME):
            move_count  = max(disp_visited_moves.values(), default=0)
            moves_label = "move" if move_count == 1 else "moves"
            mc_s = self.font.render(f"{move_count} {moves_label}", True, (0, 0, 0))
            mc_y = right_panel.get_line_y("STATS_PANEL", s_line, line_height)
            screen.blit(mc_s, mc_s.get_rect(centerx=stats_bounds["center_x"], top=mc_y))
            s_line += 1

            n_flags   = len(self.flags)
            n_reached = len(disp_flags_reached)
            fl_label  = "flag" if n_flags == 1 else "flags"
            fl_s = self.font.render(f"{n_reached} of {n_flags} {fl_label}", True, (0, 0, 0))
            fl_y = right_panel.get_line_y("STATS_PANEL", s_line, line_height)
            screen.blit(fl_s, fl_s.get_rect(centerx=stats_bounds["center_x"], top=fl_y))
            s_line += 1

            if fo_val == "only":
                n_in  = len(disp_flags_reached_in_order)
                n_out = len(disp_flags_reached_out_of_order)
                in_s  = self.font.render(f"flags in order: {n_in}", True, (0, 0, 255))
                in_y  = right_panel.get_line_y("STATS_PANEL", s_line, line_height)
                screen.blit(in_s, in_s.get_rect(centerx=stats_bounds["center_x"], top=in_y))
                s_line += 1
                out_s = self.font.render(f"flags out of order: {n_out}", True, (255, 0, 0))
                out_y = right_panel.get_line_y("STATS_PANEL", s_line, line_height)
                screen.blit(out_s, out_s.get_rect(centerx=stats_bounds["center_x"], top=out_y))
                s_line += 1
            elif fo_val == "next":
                n_nf  = len(disp_flags_reached_in_order)
                nf_s  = self.font.render(f"next flags found: {n_nf}", True, (0, 0, 255))
                nf_y  = right_panel.get_line_y("STATS_PANEL", s_line, line_height)
                screen.blit(nf_s, nf_s.get_rect(centerx=stats_bounds["center_x"], top=nf_y))
                s_line += 1

        if self.game_state == GameState.ENDGAME and self.end_state:
            end_messages = {
                "all_flags_reached": ("all flags captured", (34, 177,  76)),
                "no_moves":          ("no legal moves",     (200,   0,   0)),
                "resignation":       ("resigned",           (180,   0,   0)),
                "timeout":           ("time's up",          (  0,   0, 200)),
            }
            msg, msg_color = end_messages.get(self.end_state, ("game over", (0, 0, 0)))
            em_s = self.font_large.render(msg, True, msg_color)
            em_y = right_panel.get_line_y("STATS_PANEL", s_line + 1, line_height)
            screen.blit(em_s, em_s.get_rect(centerx=stats_bounds["center_x"], top=em_y))

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

        right_left = win_width - panel_width - margin

        left_panel_rect  = pygame.Rect(msg_left,  msg_top, panel_width, msg_bottom - msg_top)
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

        # Sync board model size in MENU
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

        # Compute display state (may differ when replaying) – used by right panel
        if self.game_state == GameState.ENDGAME and self.replay_mode_active and self.replay_states:
            disp = self.replay_states[self.replay_index]
            disp_visited_moves              = disp["visited_moves"]
            disp_flags_reached              = disp["flags_reached"]
            disp_flags_reached_in_order     = disp.get("flags_reached_in_order",    set())
            disp_flags_reached_out_of_order = disp.get("flags_reached_out_of_order", set())
        else:
            disp_visited_moves              = self.visited_moves
            disp_flags_reached              = self.flags_reached
            disp_flags_reached_in_order     = self.flags_reached_in_order
            disp_flags_reached_out_of_order = self.flags_reached_out_of_order

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
            ex = area_left + (aw - es.get_width())  // 2
            ey = area_top  + (ah - es.get_height()) // 2
            pygame.draw.rect(screen, (255, 240, 240),
                             (ex - 8, ey - 6, es.get_width() + 16, es.get_height() + 12))
            screen.blit(es, (ex, ey))
        elif self.error_message and pygame.time.get_ticks() >= self.error_timer:
            self.error_message = ""

        self._render_left_panel(screen, left_panel, msg_left, msg_right, msg_bottom)
        self._render_right_panel(screen, right_panel,
                                 disp_visited_moves, disp_flags_reached,
                                 disp_flags_reached_in_order,
                                 disp_flags_reached_out_of_order)

    # ------------------------------------------------------------------ #
    #  event handling                                                      #
    # ------------------------------------------------------------------ #

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Process one pygame event.
        Returns False if the game should quit.
        """
        if not super().handle_event(event):
            return False

        # Hint mode keyboard shortcut (vexillum-specific)
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

            if self.game_state == GameState.INGAME:
                grid_pos = self.board_renderer.to_grid(mx, my)
                if grid_pos is not None:
                    self.make_move(grid_pos)

            elif self.game_state == GameState.MENU:
                grid_pos = self.board_renderer.to_grid(mx, my)
                if grid_pos is not None:
                    self.preview_pos = grid_pos

        return True