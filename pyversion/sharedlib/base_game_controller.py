"""
base_game_controller.py

Abstract base class for Hamiltonian-Knights game controllers.
Provides common game-loop infrastructure, UI management, asset loading,
mode toggles, and per-frame updates so individual game controllers only
need to implement game-specific logic.

Subclasses must implement the abstract methods listed below.
"""

import os
import sys
import time
import random

import pygame
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple, Set, Dict, Any
from enum import Enum, auto

# sharedlib imports (caller must have added sharedlib to sys.path)
import piecekeeper as pk
from gameboard import BoardModel, BoardRenderer
from uipanel import UIPanel
from text_input import TextInput
from puzzle_codec import encode_params
from common_utils import clamp as _clamp

# ------------------------------------------------------------------ #
#  Shared constants                                                    #
# ------------------------------------------------------------------ #

UI_SPACE          = 16
BTW               = int(UI_SPACE * 9)
BTH               = int(UI_SPACE * 2)
CODEC_TEXT_LENGTH = 16
INFINITY_SYMBOL   = "\u221e"

# Common board colours (used in left/right panels)
LT_SQUARE  = (255, 255, 240)
DK_SQUARE  = (232, 200, 150)
GRID_COLOR = (107, 70,  51)
BACK_COLOR = (244, 228, 195)


class GameState(Enum):
    MENU    = auto()
    INGAME  = auto()
    ENDGAME = auto()
    WAITING = auto()  # Used for blind draw / two-phase start square selection


# ------------------------------------------------------------------ #
#  BaseGameController                                                  #
# ------------------------------------------------------------------ #

class BaseGameController(ABC):
    """
    Abstract base controller for Hamiltonian-Knights games.

    Subclasses implement the abstract methods to supply game-specific
    behaviour (maze generation, flag capture, polyomino placement, …).
    All common state, asset loading, toggle helpers, undo/resign/retry,
    replay navigation, clipboard, clock, and basic event handling are
    provided here.
    """

    # Subclasses may override these class attributes to change the colour
    # used by _draw_visited_squares().
    VISITED_LT: Tuple[int, int, int] = (192, 220, 248)
    VISITED_DK: Tuple[int, int, int] = (128, 160, 225)

    # ------------------------------------------------------------------ #
    #  construction                                                        #
    # ------------------------------------------------------------------ #

    def __init__(
        self,
        board_model:    BoardModel,
        board_renderer: BoardRenderer,
        menu_items:     list,
        label_to_index: dict,
        font:           pygame.font.Font,
        font_large:     pygame.font.Font,
        base_dir:       str,
        schema:         list,
    ) -> None:
        self.board_model    = board_model
        self.board_renderer = board_renderer
        self.menu_items     = menu_items      # mutable list of (label, vals, cur_idx)
        self.label_to_index = label_to_index
        self.font           = font
        self.font_large     = font_large
        self.base_dir       = base_dir
        self.schema         = schema          # puzzle-codec schema for this game
        self.pieces_dir     = os.path.join(base_dir, "assets", "pieces")
        self.arrows_dir     = os.path.join(base_dir, "assets", "arrows")

        # Game state
        self.game_state: GameState      = GameState.MENU
        self.end_state:  Optional[str]  = None

        # Player / movement state
        self.player_pos:     Optional[Tuple[int, int]]       = None
        self.visited:        Set[Tuple[int, int]]             = set()
        self.visited_moves:  Dict[Tuple[int, int], int]       = {}
        self.legal_moves:    List[Tuple[int, int]]            = []
        self.hint_degrees:   Dict[Tuple[int, int], int]       = {}
        self.move_count:     int                              = 0

        # Mode flags
        self.guide_mode_active:  bool        = False
        self.track_mode_active:  bool        = True
        self.hint_mode_active:   bool        = False
        self.peek_mode_visible:  bool        = False
        self.reveal_mode_active: bool        = False
        self.replay_mode_active: bool        = False
        self.replay_index:       int         = 0
        self.replay_states:      List[Dict]  = []

        # Clock
        self.clock_start_time: Optional[float] = None
        self.paused_elapsed:   float            = 0.0
        self.clock_elapsed:    int              = 0
        self.final_elapsed:    int              = 0

        # Puzzle code / share
        self.puzzle_code:      str           = ""
        self.last_puzzle_seed: Optional[int] = None
        self.seed_mode_active: bool          = False
        self.copy_clicked:     bool          = False
        self.copy_timer:       int           = 0

        # Error display
        self.error_message: str = ""
        self.error_timer:   int = 0

        # Assets / UI bookkeeping
        self.current_cell_size: int                             = 0
        self.arrows:      Dict[Tuple[int, int], pygame.Surface] = {}
        self.widget_rects: Dict                                 = {}

        # Text input for share codes (max_length=19: 16 chars + up to 3 dashes)
        self.codec_input = TextInput(pygame.Rect(0, 0, BTW, BTH), font, max_length=19)

        # Subclass provides buttons and loads initial piece images
        self._build_buttons()
        self._load_piece_images(36)

    # ================================================================== #
    #  Abstract interface – must be implemented by every subclass         #
    # ================================================================== #

    @abstractmethod
    def _game_specific_start_setup(self, seed: Optional[int] = None) -> bool:
        """
        Generate game content (path, obstacles, flags, …) for *seed*.

        Must set at minimum:
          self.player_pos, self.visited, self.visited_moves, self.move_count
        Returns True on success, False on failure.
        """
        ...

    @abstractmethod
    def _game_specific_make_move(self, target: Tuple[int, int]) -> bool:
        """
        Apply game-specific move logic for a move to *target*.

        Should increment self.move_count when a successful move occurs.
        Returns True if the move should be committed (player_pos updated),
        False otherwise (obstacle hit, off-path, etc.).
        """
        ...

    @abstractmethod
    def _validate_move(self, target: Tuple[int, int]) -> bool:
        """Return True if *target* is reachable from the current position."""
        ...

    @abstractmethod
    def _check_endgame_conditions(self) -> Optional[str]:
        """
        Inspect current state and return an end_state string if the game is
        over (e.g. "maze_complete", "no_moves"), or None to continue.
        """
        ...

    @abstractmethod
    def _render_game_specific_board(self, screen: pygame.Surface) -> None:
        """Draw game-specific board overlays (path, obstacles, flags, …)."""
        ...

    @abstractmethod
    def _render_game_specific_stats(
        self, screen: pygame.Surface, stats_panel: UIPanel
    ) -> None:
        """Render game-specific statistics into the STATS_PANEL area."""
        ...

    @abstractmethod
    def _capture_game_state(self) -> Dict[str, Any]:
        """Snapshot current game state for replay / undo."""
        ...

    @abstractmethod
    def _restore_game_state(self, state: Dict[str, Any]) -> None:
        """Restore game state from a previously captured snapshot."""
        ...

    @abstractmethod
    def _get_min_board_size(self, piece_name: str) -> int:
        """Return the minimum board dimension for *piece_name*."""
        ...

    @abstractmethod
    def _update_legal_moves(self) -> None:
        """Recompute self.legal_moves for the current player position."""
        ...

    @abstractmethod
    def _calculate_hint_degrees(self) -> None:
        """Compute self.hint_degrees (Warnsdorff-style) for current position."""
        ...

    @abstractmethod
    def _validate_codec(
        self, codec_text: str
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Validate a share-code string and apply the decoded settings to
        self.menu_items.  Returns (True, params) on success, (False, None)
        on failure.
        """
        ...

    @abstractmethod
    def _build_buttons(self) -> None:
        """Populate self.buttons with the game-specific Button set."""
        ...

    @abstractmethod
    def _get_encode_params(self) -> Dict[str, Any]:
        """
        Return the params dict used to encode the puzzle code.
        Keys must match the game's schema field names.
        """
        ...

    # ================================================================== #
    #  Common helpers                                                      #
    # ================================================================== #

    def get_selection(self, label: str) -> Any:
        """Return the currently selected value for *label* in menu_items."""
        i = self.label_to_index[label]
        _, vals, cur = self.menu_items[i]
        return vals[cur]

    def _is_valid_codec_length(self) -> bool:
        """Return True when the codec input contains exactly CODEC_TEXT_LENGTH chars."""
        return len(self.codec_input.get_text().replace("-", "")) == CODEC_TEXT_LENGTH

    def _clock_has_expired(self) -> bool:
        clock_sel = self.get_selection("clock")
        if clock_sel == 0:
            return False
        return int(self.clock_elapsed) >= int(clock_sel)

    def _remaining_time(self) -> Optional[int]:
        clock_sel = self.get_selection("clock")
        if clock_sel == 0:
            return None
        elapsed = self.final_elapsed if self.game_state == GameState.ENDGAME else self.clock_elapsed
        return max(0, int(clock_sel) - int(elapsed))

    # ================================================================== #
    #  Asset loading                                                       #
    # ================================================================== #

    def _load_piece_images(self, sq_size: int) -> None:
        try:
            pk.load_images(self.pieces_dir, sq_size)
        except Exception as e:
            print(f"Warning: could not load piece images: {e}")

    def _load_arrows(self, cell_size: int) -> None:
        arrow_names = {
            (0, -1): "arrow_n.png",  (1, -1): "arrow_ne.png",
            (1,  0): "arrow_e.png",  (1,  1): "arrow_se.png",
            (0,  1): "arrow_s.png",  (-1, 1): "arrow_sw.png",
            (-1, 0): "arrow_w.png",  (-1,-1): "arrow_nw.png",
        }
        self.arrows.clear()
        arrow_size = max(8, cell_size // 2)
        diag_size  = max(6, int(arrow_size * 0.75))
        for direction, fname in arrow_names.items():
            fpath = os.path.join(self.arrows_dir, fname)
            try:
                img = pygame.image.load(fpath).convert_alpha()
                dx, dy = direction
                sz = diag_size if (dx != 0 and dy != 0) else arrow_size
                self.arrows[direction] = pygame.transform.smoothscale(img, (sz, sz))
            except Exception:
                pass

    def _load_star_images(self) -> None:
        star_size = 22
        try:
            sf = pygame.image.load(os.path.join(self.markers_dir, "star_filled.png")).convert_alpha()
            se = pygame.image.load(os.path.join(self.markers_dir, "star_empty.png")).convert_alpha()
            self.star_filled = pygame.transform.smoothscale(sf, (star_size, star_size))
            self.star_empty  = pygame.transform.smoothscale(se, (star_size, star_size))
        except Exception as e:
            print(f"Warning: could not load star images: {e}")
            self.star_filled = None
            self.star_empty  = None


    # ================================================================== #
    #  Rendering helpers                                                   #
    # ================================================================== #

    def _update_cell_size(
        self,
        area_left: int,
        area_top: int,
        area_width: int,
        area_height: int,
    ) -> None:
        cols, rows = self.board_model.cols, self.board_model.rows
        if cols > 0 and rows > 0:
            new_cs = max(12, min(area_width // cols, area_height // rows))
        else:
            new_cs = 0
        if new_cs != self.current_cell_size and new_cs > 0:
            self.current_cell_size = new_cs
            self.board_renderer.cell_size = new_cs
            self._load_piece_images(max(12, new_cs - 4))
            self._load_arrows(new_cs)
        board_pixel_w = cols * self.current_cell_size
        board_pixel_h = rows * self.current_cell_size
        origin_x = area_left + (area_width  - board_pixel_w) // 2
        origin_y = area_top  + (area_height - board_pixel_h) // 2
        self.board_renderer.origin = (origin_x, origin_y)

    def _draw_arrows(
        self,
        screen:  pygame.Surface,
        moves:   List[Tuple[int, int]],
        ref_pos: Tuple[int, int],
    ) -> None:
        """Draw directional arrow sprites toward each square in *moves*."""
        cs = self.current_cell_size
        for mx, my in moves:
            dx = int(_clamp(mx - ref_pos[0], -1, 1))
            dy = int(_clamp(my - ref_pos[1], -1, 1))
            a  = self.arrows.get((dx, dy))
            if a:
                gpx, gpy = self.board_renderer.to_pixel(mx, my)
                screen.blit(a, a.get_rect(center=(gpx + cs // 2, gpy + cs // 2)))

    def _draw_visited_squares(self, screen: pygame.Surface) -> None:
        """
        Draw visited squares using VISITED_LT / VISITED_DK class colours.
        Respects replay mode and track_mode_active for move numbers.
        """
        cs     = self.current_cell_size
        lt, dk = self.VISITED_LT, self.VISITED_DK

        # In replay mode use the snapshot at the current replay index
        if (self.game_state == GameState.ENDGAME
                and self.replay_mode_active
                and self.replay_states):
            snap      = self.replay_states[self.replay_index]
            disp_pos  = snap["pos"]
            disp_moves = snap["visited_moves"]
        else:
            disp_pos   = self.player_pos
            disp_moves = self.visited_moves

        for vx, vy in disp_moves:
            if (vx, vy) == disp_pos:
                continue
            px, py = self.board_renderer.to_pixel(vx, vy)
            vc = lt if (vx + vy) % 2 == 0 else dk
            pygame.draw.rect(screen, vc, (px + 3, py + 3, cs - 4, cs - 4))
            if self.track_mode_active:
                luma = vc[0] * 0.299 + vc[1] * 0.587 + vc[2] * 0.114
                nc   = (0, 0, 0) if luma > 128 else (255, 255, 255)
                nf   = pygame.font.SysFont("arial", max(8, cs // 3))
                ns   = nf.render(str(disp_moves[(vx, vy)]), True, nc)
                screen.blit(ns, ns.get_rect(center=(px + cs // 2, py + cs // 2)))

    def _draw_hint_degrees(self, screen: pygame.Surface) -> None:
        """Draw Warnsdorff hint-degree numbers on reachable squares."""
        cs = self.current_cell_size
        for (hx, hy), degree in self.hint_degrees.items():
            px, py = self.board_renderer.to_pixel(hx, hy)
            hf = pygame.font.SysFont("arial", max(8, cs // 3))
            hs = hf.render(str(degree), True, (0, 100, 0))
            screen.blit(hs, hs.get_rect(center=(px + cs // 2, py + cs // 2)))

    def _draw_player_piece(self, screen: pygame.Surface) -> None:
        """Draw the player's chess piece at its current (or replay) position."""
        if not self.player_pos:
            return
        # Use replay-state position if replaying
        if (self.game_state == GameState.ENDGAME
                and self.replay_mode_active
                and self.replay_states):
            disp_pos = self.replay_states[self.replay_index]["pos"]
        else:
            disp_pos = self.player_pos
        if not disp_pos:
            return
        cs       = self.current_cell_size
        ppx, ppy = self.board_renderer.to_pixel(*disp_pos)
        pr_rect  = pygame.Rect(ppx + 1, ppy + 1, cs - 2, cs - 2)
        try:
            pk.draw_piece(screen, pr_rect, self.get_selection("piece"))
        except Exception:
            pygame.draw.ellipse(screen, (0, 0, 0), pr_rect)

    # ================================================================== #
    #  Game actions                                                        #
    # ================================================================== #

    def start_game(self, use_seed: Optional[int] = None) -> None:
        """
        Start (or restart) a game.

        Validates board size, resolves the RNG seed (random / share-code /
        explicit), delegates to _game_specific_start_setup(), encodes the
        puzzle code, and transitions to INGAME.
        """
        piece      = self.get_selection("piece")
        board_size = self.get_selection("board")

        min_board = self._get_min_board_size(piece)
        if board_size < min_board:
            self.error_message = f"{piece} needs board >= {min_board}"
            self.error_timer   = pygame.time.get_ticks() + 3000
            return

        if use_seed is not None:
            seed = use_seed
        elif self.seed_mode_active:
            code_text = self.codec_input.get_text()
            ok, params = self._validate_codec(code_text)
            if ok and params:
                seed = params["seed"]
                # _validate_codec already applied decoded settings to menu_items
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

        # Sync board model to the (possibly codec-updated) board size
        n = self.get_selection("board")
        self.board_model.cols = n
        self.board_model.rows = n
        self.board_model.clear()

        # Encode puzzle code using game-specific params + common schema
        try:
            self.puzzle_code = encode_params(self._get_encode_params(), self.schema, seed)
        except Exception:
            self.puzzle_code = ""

        # Reset common game state
        self.end_state          = None
        self.clock_start_time   = None
        self.paused_elapsed     = 0.0
        self.clock_elapsed      = 0
        self.final_elapsed      = 0
        self.replay_states      = [self._capture_game_state()]
        self.replay_index       = 0
        self.replay_mode_active = False
        self.peek_mode_visible  = False
        self.reveal_mode_active = False
        self.hint_degrees       = {}
        self.game_state         = GameState.INGAME

    def make_move(self, target_pos: Tuple[int, int]) -> None:
        """
        Attempt to move the player to *target_pos*.

        Validates reachability, delegates to _game_specific_make_move(),
        updates common state on success, and checks end-game conditions.
        """
        if self.game_state != GameState.INGAME:
            return
        if not self._validate_move(target_pos):
            return

        if self.clock_start_time is None:
            self.clock_start_time = time.time()

        result = self._game_specific_make_move(target_pos)
        if result:
            # _game_specific_make_move already incremented self.move_count
            self.player_pos = target_pos
            self.visited.add(target_pos)
            self.visited_moves[target_pos] = self.move_count
            self.replay_states.append(self._capture_game_state())
            self._update_legal_moves()
            if self.hint_mode_active:
                self._calculate_hint_degrees()

            end_condition = self._check_endgame_conditions()
            if end_condition:
                self.final_elapsed = int(self.paused_elapsed + (
                    (time.time() - self.clock_start_time)
                    if self.clock_start_time else 0))
                self.end_state  = end_condition
                self.game_state = GameState.ENDGAME

    def undo_move(self) -> None:
        if self.game_state != GameState.INGAME or len(self.replay_states) <= 1:
            return
        self.replay_states.pop()
        self._restore_game_state(self.replay_states[-1])

    def resign_game(self) -> None:
        if self.game_state != GameState.INGAME:
            return
        self.final_elapsed = int(self.paused_elapsed + (
            (time.time() - self.clock_start_time) if self.clock_start_time else 0))
        self.end_state  = "resignation"
        self.game_state = GameState.ENDGAME

    def toggle_track_mode(self)  -> None: self.track_mode_active  = not self.track_mode_active

    def toggle_peek(self)        -> None: self.peek_mode_visible  = not self.peek_mode_visible

    def toggle_codec_input(self) -> None: self.seed_mode_active   = not self.seed_mode_active

    def toggle_hint_mode(self) -> None:
        """Toggle hint mode (move hints)."""
        self.hint_mode_active = not self.hint_mode_active
        if self.hint_mode_active:
            if self.player_pos and self.game_state == GameState.INGAME:
                self._calculate_hint_degrees()
        else:
            self.hint_degrees = {}

    def toggle_guide_mode(self) -> None:
        """Toggle guide mode (move arrows)."""
        self.guide_mode_active = not self.guide_mode_active


    def toggle_replay_mode(self) -> None:
        if self.game_state != GameState.ENDGAME:
            return
        if not self.replay_mode_active:
            self.replay_mode_active = True
            self.board_model.clear()
            self.replay_index       = 0
            if self.replay_states:
                self._restore_game_state(self.replay_states[0])
        else:
            self.replay_mode_active = False
            if self.replay_states:
                self._restore_game_state(self.replay_states[-1])
        # Ensure we stay in ENDGAME after state restore
        self.game_state = GameState.ENDGAME


    def navigate_replay(self, delta: int) -> None:
        if not self.replay_mode_active or not self.replay_states:
            return
        self.replay_index = int(_clamp(self.replay_index + delta, 0,
                                       len(self.replay_states) - 1))
        self._restore_game_state(self.replay_states[self.replay_index])

    def toggle_reveal(self) -> None:
        if self.game_state == GameState.ENDGAME:
            self.reveal_mode_active = not self.reveal_mode_active

    def retry_game(self) -> None:
        if self.last_puzzle_seed is not None:
            self.start_game(use_seed=self.last_puzzle_seed)

    def new_game(self) -> None:
        self.end_state          = None
        self.peek_mode_visible  = False
        self.reveal_mode_active = False
        self.seed_mode_active   = False
        self.replay_mode_active = False
        self.puzzle_code        = ""
        self.codec_input.set_text("")
        self.game_state         = GameState.MENU

    @staticmethod
    def quit_game() -> None:
        pygame.quit()
        sys.exit()

    def copy_code_to_clipboard(self) -> None:
        if not self.puzzle_code:
            return
        try:
            import pyperclip
            pyperclip.copy(self.puzzle_code)
        except Exception:
            try:
                import subprocess
                subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=self.puzzle_code.encode(),
                    check=False,
                )
            except Exception:
                pass
        self.copy_clicked = True
        self.copy_timer   = pygame.time.get_ticks() + 2000

    # ================================================================== #
    #  Window-focus / clock pause                                         #
    # ================================================================== #

    def handle_window_focus(self, state_attr: int, gain_attr: int) -> None:
        """Pause the clock on focus loss, resume on focus gain."""
        if state_attr & 4:
            if gain_attr == 0:
                if (self.clock_start_time is not None
                        and self.game_state == GameState.INGAME):
                    self.paused_elapsed  += time.time() - self.clock_start_time
                    self.clock_start_time = None
            elif gain_attr == 1:
                if (self.game_state == GameState.INGAME
                        and self.clock_start_time is None
                        and self.move_count > 0):
                    self.clock_start_time = time.time()

    # ================================================================== #
    #  Per-frame update                                                    #
    # ================================================================== #

    def update(self, dt: int) -> None:
        """Call once per frame with milliseconds elapsed since last frame."""
        self.codec_input.update(dt)

        #if self.copy_clicked and pygame.time.get_ticks() > self.copy_timer:
        #    self.copy_clicked = False

        if self.game_state == GameState.INGAME:
            if self.clock_start_time is not None:
                self.clock_elapsed = int(
                    self.paused_elapsed + (time.time() - self.clock_start_time)
                )
            if self._clock_has_expired():
                self.final_elapsed = self.clock_elapsed
                self.end_state     = "timeout"
                self.game_state    = GameState.ENDGAME

    # ================================================================== #
    #  Basic event handling (subclasses extend this)                      #
    # ================================================================== #

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Process one pygame event.  Returns False if the application should quit.

        Handles: QUIT, keyboard shortcuts (Escape/g/t/p/u/m, arrow keys for
        replay), ACTIVEEVENT (focus), codec text input, and all buttons.

        Subclasses should call super().handle_event(event) first and return
        False if that call does so, then add their own game-specific logic.
        """
        if event.type == pygame.QUIT:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.game_state == GameState.INGAME:
                    self.resign_game()
                elif self.game_state == GameState.ENDGAME:
                    self.new_game()
            elif event.key == pygame.K_m:
                pygame.display.iconify()
            elif event.key == pygame.K_u and self.game_state == GameState.INGAME:
                self.undo_move()
            elif event.key == pygame.K_h and self.game_state == GameState.INGAME:
                self.toggle_hint_mode()
            elif event.key == pygame.K_g:
                self.toggle_guide_mode()
            elif event.key == pygame.K_t:
                self.toggle_track_mode()
            elif event.key == pygame.K_p:
                self.toggle_peek()
            elif event.key == pygame.K_r:
                self.go_to_menu()


        if event.type == pygame.KEYDOWN and self.replay_mode_active:
            if event.key == pygame.K_LEFT:
                self.navigate_replay(-1)
            elif event.key == pygame.K_RIGHT:
                self.navigate_replay(1)

        if event.type == pygame.ACTIVEEVENT:
            self.handle_window_focus(
                getattr(event, "state", 0),
                getattr(event, "gain",  0),
            )

        if self.game_state == GameState.MENU and self.seed_mode_active:
            self.codec_input.handle_event(event)

        for btn in self.buttons.values():
            btn.handle_event(event)

        return True