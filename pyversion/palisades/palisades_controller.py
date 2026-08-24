"""
palisades_controller.py

Game controller for Palisades: Non-Crossing Knight's Tour.

A non-crossing knight's tour is a sequence of legal knight moves on a
chessboard such that no square is visited more than once and the path
formed by connecting move endpoints does not intersect itself.

Manages game state, move validation, crossing detection, and rendering.
Inherits common functionality from BaseGameController.
"""

import time
import random
from collections import deque
from functools import lru_cache

import pygame
from typing import Optional, List, Tuple, Dict, Any

# sharedlib imports (BASE_DIR must already be on sys.path)
import piecekeeper as pk
from gameboard import BoardModel, BoardRenderer
from uipanel import UIPanel
from puzzle_codec import decode_params
from widgets import Button
from move_system import get_legal_moves_for_board
from base_game_controller import BaseGameController, GameState

from pyversion.knightstour.knights_tour_logic import KnightsTour

# --- Constants ---
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
CLOCK_MODES = ["game", "move"]

# Even-parity pieces that cannot complete a full Hamiltonian tour
EXCLUDED_PIECES = {"bishop", "rook", "queen", "king",
                   "wazir", "ferz", "dabbaba", "alfil", "threeleaper", "tripper", "camel",
                   "toad", "pterodactyl", "gunkan"
                   }

# Colors — green-tinted to distinguish from the standard Knight's Tour
LT_SQUARE = (255, 255, 240)
DK_SQUARE = (232, 200, 150)
LT_VISITED = (192, 230, 192)
DK_VISITED = (128, 180, 128)
GRID_COLOR = (107, 70, 51)
BACK_COLOR = (244, 228, 195)
PATH_LINE_COLOR = (255,0,64)
HINT_NUM_COLOR =  (107, 50, 71)
WAITING_MSG_COLOR = (0, 0, 192)
WARN_COLOR = (128, 0, 0)

# Clock: 0-63 values (0=infinite, 1-30 = minutes)
palisades_schema = [
    ("board", 4, lambda v: int(v) - BOARD_MIN),
    ("first_square", 1, {"select": 0, "random": 1}),
    ("clock", 6, lambda v: int(v) // 60 if v > 0 else 0),
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
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins}:{secs:02d}"


def _display_for_selection(clock_selected) -> str:
    if clock_selected == 0:
        return "infinity"
    return _format_clock_seconds(clock_selected)


# ================================================================== #
#  Geometry helpers for non-crossing detection                        #
# ================================================================== #

def _cross_product(
    o: Tuple[int, int],
    a: Tuple[int, int],
    b: Tuple[int, int],
) -> float:
    """
    Signed area of triangle OAB (×2).

    Positive = OA→OB is counter-clockwise; negative = clockwise; zero = collinear.
    """
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _segments_properly_intersect(
    p1: Tuple[int, int],
    p2: Tuple[int, int],
    p3: Tuple[int, int],
    p4: Tuple[int, int],
) -> bool:
    """
    Return True if segment p1-p2 properly crosses segment p3-p4.

    'Properly' means the two segments cross at an interior point: each
    segment's endpoints are on strictly opposite sides of the other
    segment's supporting line.  Touching at shared endpoints is NOT
    considered a crossing.
    """
    d1 = _cross_product(p3, p4, p1)
    d2 = _cross_product(p3, p4, p2)
    d3 = _cross_product(p1, p2, p3)
    d4 = _cross_product(p1, p2, p4)
    return (
        ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0))
        and ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0))
    )


def _point_on_segment_interior(
    p: Tuple[int, int],
    a: Tuple[int, int],
    b: Tuple[int, int],
) -> bool:
    """
    Return True if point p lies strictly in the interior of segment a-b.

    'Interior' means p is collinear with a and b, lies between them, and
    is not equal to either endpoint.  Used to detect T-intersections that
    _segments_properly_intersect misses (e.g. a slider landing exactly on
    an existing path segment).
    """
    if _cross_product(a, b, p) != 0:
        return False
    return (
        min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
        and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])
        and p != a and p != b
    )


def _would_create_crossing(
    path: List[Tuple[int, int]],
    new_start: Tuple[int, int],
    new_end: Tuple[int, int],
) -> bool:
    """
    Return True if adding segment (new_start → new_end) would cross any
    existing segment in *path*, excluding the final segment which shares
    *new_start* as an endpoint.

    Crossing includes proper X-intersections as well as T-intersections:
    - new_end lands on the interior of an existing segment, or
    - an existing path vertex lies on the interior of the new segment
      (relevant for sliding pieces that skip over visited squares).

    Path layout example (n points):
        p0 → p1 → … → p_{n-2} → p_{n-1}   (p_{n-1} == new_start)
    We skip segment p_{n-2}-p_{n-1} (shares new_start).
    We check the new segment against segments p0-p1 … p_{n-3}-p_{n-2}.
    """
    n = len(path)
    if n < 3:
        # At most one existing segment, and it shares new_start → no crossing possible.
        return False
    # Check segments [0, n-3] inclusive (i.e. n-2 segments, skipping the last one).
    for i in range(n - 2):
        seg_s, seg_e = path[i], path[i + 1]
        if _segments_properly_intersect(seg_s, seg_e, new_start, new_end):
            return True
        # T-intersection: new_end lands on the interior of an existing segment.
        if _point_on_segment_interior(new_end, seg_s, seg_e):
            return True
    # T-intersection: an existing path vertex lies on the interior of the new
    # segment.  Sliding pieces skip over visited squares, so the drawn segment
    # can pass through earlier path vertices even though they are not land-on
    # squares.  All vertices except new_start (= path[-1]) are checked.
    for vertex in path[:-1]:
        if _point_on_segment_interior(vertex, new_start, new_end):
            return True
    return False


def _would_close_crossing(
    path: List[Tuple[int, int]],
    last_pos: Tuple[int, int],
    first_pos: Tuple[int, int],
) -> bool:
    """
    Return True if the *closing* segment (last_pos → first_pos) would cross
    any segment in *path* other than the first and last segments (which share
    the closing segment's endpoints).

    As with _would_create_crossing, T-intersections are also detected.
    """
    n = len(path)
    if n < 4:
        return False
    # Skip segment 0 (shares first_pos) and segment n-2 (shares last_pos).
    for i in range(1, n - 2):
        seg_s, seg_e = path[i], path[i + 1]
        if _segments_properly_intersect(seg_s, seg_e, last_pos, first_pos):
            return True
        # T-intersection: closing endpoint on interior of an existing segment.
        if _point_on_segment_interior(first_pos, seg_s, seg_e):
            return True
        if _point_on_segment_interior(last_pos, seg_s, seg_e):
            return True
    # T-intersection: interior path vertex on the closing segment.
    # Skip path[0] (= first_pos) and path[-1] (= last_pos) as those are endpoints.
    for vertex in path[1:-1]:
        if _point_on_segment_interior(vertex, last_pos, first_pos):
            return True
    return False


# ================================================================== #
#  PalisadesController                                               #
# ================================================================== #

class PalisadesController(BaseGameController):
    """Controls game logic and rendering for Palisades: Non-Crossing Knight's Tour."""

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
            font, font_large, base_dir, palisades_schema,
        )

        # Override base-class defaults
        self.guide_mode_active = True
        self.track_mode_active = True
        self.hint_mode_active = False

        # Tour-specific state
        self.tour_complete: bool = False
        self.is_closed_tour: bool = False
        self.preview_pos: Optional[Tuple[int, int]] = None
        self.kt_solver: Optional[KnightsTour] = None

        # Ordered sequence of positions for crossing detection and rendering
        self.path: List[Tuple[int, int]] = []

    # ================================================================== #
    #  Abstract-method implementations                                    #
    # ================================================================== #

    def _get_min_board_size(self, piece_name: str) -> int:
        return _piece_min_board_size(piece_name)

    def _get_encode_params(self) -> Dict[str, Any]:
        return {
            "board": self.get_selection("board"),
            "first_square": self.get_selection("first square"),
            "clock": self.get_selection("clock"),
        }

    def _validate_codec(self, codec_text: str) -> Tuple[bool, Optional[Dict]]:
        """Validate codec text and apply settings.  Returns (ok, params)."""
        try:
            params = decode_params(codec_text, palisades_schema)
            board_val = params.get("board", 0) + BOARD_MIN
            if not (BOARD_MIN <= board_val <= BOARD_MAX):
                return False, None

            clock_minutes = params.get("clock", 0)
            clock_val = clock_minutes * 60 if clock_minutes > 0 else 0

            first_sq = params.get("first_square")
            if first_sq not in FIRST_SQUARE_CHOICES:
                return False, None

            def _apply(label, value):
                idx = self.label_to_index[label]
                lbl, vals, _ = self.menu_items[idx]
                if value in vals:
                    self.menu_items[idx] = (lbl, vals, vals.index(value))

            _apply("board", board_val)
            _apply("clock", clock_val)
            _apply("first square", first_sq)
            return True, {**params, "board": board_val, "clock": clock_val}
        except Exception:
            return False, None

    def _game_specific_start_setup(self, seed: Optional[int] = None) -> bool:
        """Initialise game state for a new non-crossing knight's tour."""
        board_size = self.get_selection("board")
        first_square_mode = self.get_selection("first square")

        self.kt_solver = KnightsTour(size=board_size)

        if first_square_mode == "random":
            if seed is not None:
                random.seed(seed)
            start_idx = random.randint(0, board_size * board_size - 1)
            start_x = start_idx % board_size
            start_y = start_idx // board_size
            start_pos = (start_x, start_y)
        else:
            # "select" mode – will be committed by commit_start_square()
            start_pos = (board_size // 2, board_size // 2)

        self.player_pos = start_pos
        self.visited = {start_pos}
        self.visited_moves = {start_pos: 0}
        self.move_count = 0
        self.tour_complete = False
        self.is_closed_tour = False
        self.path = [start_pos]

        self.guide_mode_active = True
        self.track_mode_active = True
        self.hint_mode_active = False

        self._update_legal_moves()
        return True

    def _game_specific_make_move(self, target: Tuple[int, int]) -> bool:
        """Append target to the path and increment move counter."""
        self.move_count += 1
        self.path.append(target)
        return True

    def _validate_move(self, target: Tuple[int, int]) -> bool:
        """Return True if target is in the pre-filtered non-crossing legal moves."""
        return target in self.legal_moves

    def _check_endgame_conditions(self) -> Optional[str]:
        """Return end-state string when the tour is complete or blocked."""
        board_size = self.get_selection("board")
        total_squares = board_size * board_size

        if len(self.visited) == total_squares:
            self.tour_complete = True
            # Check whether the path can also be closed without crossing.
            if len(self.path) >= 2:
                first_pos = self.path[0]
                last_pos = self.path[-1]
                piece_name = self.get_selection("piece")
                moves_from_last = get_legal_moves_for_board(
                    piece_name, *last_pos, board_size, board_size, set()
                )
                if first_pos in moves_from_last:
                    self.is_closed_tour = not _would_close_crossing(
                        self.path, last_pos, first_pos
                    )
                else:
                    self.is_closed_tour = False
            return "tour_complete"

        if not self.legal_moves:
            return "no_moves"
        return None

    def _render_game_specific_board(self, screen: pygame.Surface) -> None:
        """Draw visited squares, path lines, arrows, hint numbers, and piece."""
        if self.game_state not in (GameState.INGAME, GameState.ENDGAME):
            return

        cs = self.current_cell_size

        # Choose display data (live or replay snapshot)
        if self.game_state == GameState.ENDGAME and self.replay_mode_active and self.replay_states:
            disp = self.replay_states[self.replay_index]
            disp_pos = disp["pos"]
            disp_visited = disp["visited"]
            disp_visited_moves = disp["visited_moves"]
            disp_path = disp.get("path", [])
        else:
            disp_pos = self.player_pos
            disp_visited = self.visited
            disp_visited_moves = self.visited_moves
            disp_path = self.path

        # Draw visited squares (green tint to signal non-crossing game)
        nf_move = pygame.font.SysFont("arial", max(8, cs // 4))
        for vx, vy in disp_visited:
            px, py = self.board_renderer.to_pixel(vx, vy)
            parity = (vx + vy) % 2
            vcolor = LT_VISITED if parity == 0 else DK_VISITED
            pygame.draw.rect(screen, vcolor, (px + 3, py + 3, cs - 4, cs - 4))

            if self.track_mode_active and (vx, vy) in disp_visited_moves:
                # ITU-R BT.601 coefficients for perceived luminance
                luma = vcolor[0] * 0.299 + vcolor[1] * 0.587 + vcolor[2] * 0.114
                num_color = (0, 0, 0) if luma > 128 else (255, 255, 255)
                ns = nf_move.render(
                    str(disp_visited_moves[(vx, vy)] + 1), True, num_color
                )
                screen.blit(ns, ns.get_rect(center=(px + cs // 6, py + cs // 4)))

        # Draw path as connected line segments
        if len(disp_path) >= 2:
            line_w = max(2, cs // 8)
            for i in range(len(disp_path) - 1):
                x1, y1 = disp_path[i]
                x2, y2 = disp_path[i + 1]
                px1, py1 = self.board_renderer.to_pixel(x1, y1)
                px2, py2 = self.board_renderer.to_pixel(x2, y2)
                cx1, cy1 = px1 + cs // 2, py1 + cs // 2
                cx2, cy2 = px2 + cs // 2, py2 + cs // 2
                pygame.draw.line(screen, PATH_LINE_COLOR, (cx1, cy1), (cx2, cy2), line_w)

        # Guide arrows toward legal (non-crossing) moves
        if self.guide_mode_active and self.arrows and disp_pos:
            if self.replay_mode_active and self.game_state == GameState.ENDGAME:
                # In replay the legal_moves list may not correspond to this snapshot;
                # recompute standard moves for the arrow display only.
                moves_for_arrows = get_legal_moves_for_board(
                    self.get_selection("piece"), *disp_pos,
                    self.board_model.cols, self.board_model.rows, disp_visited,
                )
            else:
                moves_for_arrows = self.legal_moves
            self._draw_arrows(screen, moves_for_arrows, disp_pos)

        # Hint degrees
        if self.hint_mode_active and self.hint_degrees:
            nf_hint = pygame.font.SysFont("arial", max(8, cs // 4))
            for (hx, hy), deg in self.hint_degrees.items():
                px, py = self.board_renderer.to_pixel(hx, hy)
                hs = nf_hint.render(str(deg), True, HINT_NUM_COLOR)
                screen.blit(hs, hs.get_rect(center=(px + cs - (cs // 5), py + (cs // 5))))

        # Draw current piece
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
        """Render progress statistics into the STATS_PANEL area."""
        bounds = stats_panel.get_bounds("STATS_PANEL")
        line_height = self.font.get_linesize() + UI_SPACE

        board_size = self.get_selection("board")
        total_squares = board_size * board_size

        if self.game_state == GameState.ENDGAME and self.replay_mode_active and self.replay_states:
            disp_visited = self.replay_states[self.replay_index]["visited"]
        else:
            disp_visited = self.visited

        # Line 1: squares visited
        y0 = stats_panel.get_line_y("STATS_PANEL", 1, line_height)
        progress_text = f"square {len(disp_visited)} of {total_squares}"
        progress_surf = self.font.render(progress_text, True, (0, 0, 0))
        screen.blit(
            progress_surf,
            progress_surf.get_rect(centerx=bounds["center_x"], top=y0),
        )

    def _capture_game_state(self) -> Dict[str, Any]:
        """Snapshot current game state for replay / undo."""
        return {
            "pos": self.player_pos,
            "visited": self.visited.copy(),
            "visited_moves": self.visited_moves.copy(),
            "move_count": self.move_count,
            "path": self.path[:],
        }

    def _restore_game_state(self, state: Dict[str, Any]) -> None:
        """Restore game state from a previously captured snapshot."""
        self.player_pos = state["pos"]
        self.visited = state["visited"].copy()
        self.visited_moves = state["visited_moves"].copy()
        self.move_count = state.get(
            "move_count", max(state["visited_moves"].values(), default=0)
        )
        self.path = state.get("path", [])[:]
        self._update_legal_moves()
        if self.hint_mode_active:
            self._calculate_hint_degrees()
        else:
            self.hint_degrees = {}

    def _update_legal_moves(self) -> None:
        """
        Recompute legal moves: standard piece moves that also do not create
        a crossing in the path drawn so far.
        """
        cols, rows = self.board_model.cols, self.board_model.rows
        piece_name = self.get_selection("piece")
        standard_moves = get_legal_moves_for_board(
            piece_name, *self.player_pos, cols, rows, self.visited
        )
        # Filter out any move that would cause the new segment to cross an
        # existing segment in the path.
        self.legal_moves = [
            m for m in standard_moves
            if not _would_create_crossing(self.path, self.player_pos, m)
        ]

    def _calculate_hint_degrees(self) -> None:
        """
        Compute non-crossing Warnsdorff hint degrees.

        For each currently-legal (non-crossing) move, the degree is the
        number of non-crossing moves that would be available *from* that
        square after landing there.
        """
        piece_name = self.get_selection("piece")
        cols, rows = self.board_model.cols, self.board_model.rows
        self.hint_degrees = {}
        for move in self.legal_moves:
            next_visited = self.visited | {move}
            next_path = self.path + [move]
            next_standard = get_legal_moves_for_board(
                piece_name, *move, cols, rows, next_visited
            )
            next_non_crossing = [
                m2 for m2 in next_standard
                if not _would_create_crossing(next_path, move, m2)
            ]
            self.hint_degrees[move] = len(next_non_crossing)

    def _build_buttons(self) -> None:
        """Populate self.buttons with the game-specific Button set."""
        f = self.font
        self.buttons: Dict[str, Button] = {
            "start": Button(
                pygame.Rect(0, 0, 0, 0), "start",
                f, (255, 255, 255), (92, 192, 92), self.start_game,
            ),
            "guide_mode": Button(
                pygame.Rect(0, 0, 0, 0), "show move guide",
                f, (255, 255, 255), (128, 64, 255), self.toggle_guide_mode,
            ),
            "track_mode": Button(
                pygame.Rect(0, 0, 0, 0), "show move numbers",
                f, (255, 255, 255), (255, 92, 128), self.toggle_track_mode,
            ),
            "hint_mode": Button(
                pygame.Rect(0, 0, 0, 0), "show degrees",
                f, (255, 255, 255), (255, 128, 96), self.toggle_hint_mode,
            ),
            "undo_mode": Button(
                pygame.Rect(0, 0, 0, 0), "undo last move",
                f, (255, 255, 255), (64, 128, 255), self.undo_move,
            ),
            "resign": Button(
                pygame.Rect(0, 0, 0, 0), "resign",
                f, (255, 255, 255), (107, 70, 51), self.resign_game,
            ),
            "retry": Button(
                pygame.Rect(0, 0, 0, 0), "retry",
                f, (255, 255, 255), (92, 192, 92), self.retry_game,
            ),
            "replay_mode": Button(
                pygame.Rect(0, 0, 0, 0), "start replay",
                f, (255, 255, 255), (64, 128, 255), self.toggle_replay_mode,
            ),
            "replay_prev": Button(
                pygame.Rect(0, 0, 0, 0), "-",
                f, (255, 255, 240), (64, 128, 255),
                lambda: self.navigate_replay(-1),
            ),
            "replay_next": Button(
                pygame.Rect(0, 0, 0, 0), "+",
                f, (255, 255, 240), (64, 128, 255),
                lambda: self.navigate_replay(1),
            ),
            "new_game": Button(
                pygame.Rect(0, 0, 0, 0), "new game",
                f, (255, 255, 255), (32, 128, 96), self.new_game,
            ),
            "exit": Button(
                pygame.Rect(0, 0, 0, 0), "exit",
                f, (255, 255, 255), (220, 40, 40), self.quit_game,
            ),
        }

    # ================================================================== #
    #  Overrides with palisades-specific behaviour                       #
    # ================================================================== #

    def start_game(self, use_seed: Optional[int] = None) -> None:
        """Override to handle the two-phase start for 'select' mode."""
        first_square_mode = self.get_selection("first square")
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
            self.error_message = "Failed to initialize tour"
            self.error_timer = pygame.time.get_ticks() + 3000
            return

        n = self.get_selection("board")
        self.board_model.cols = n
        self.board_model.rows = n
        self.board_model.clear()

        if first_square_mode == "select":
            # Two-phase start: wait for player to click a starting square.
            self.visited.clear()
            self.visited_moves.clear()
            self.legal_moves = []
            self.replay_states = []
            self.path = []
            self.game_state = GameState.WAITING
        else:
            self.end_state = None
            self.clock_start_time = time.time()
            self.paused_elapsed = 0.0
            self.clock_elapsed = 0
            self.final_elapsed = 0
            self.replay_states = [self._capture_game_state()]
            self.replay_index = 0
            self.replay_mode_active = False
            self.reveal_mode_active = False
            self.hint_degrees = {}
            self.game_state = GameState.INGAME

    def commit_start_square(self, pos_gx: int, pos_gy: int) -> None:
        """Called when the player clicks a square in WAITING state (select mode)."""
        if self.game_state != GameState.WAITING:
            return

        board_size = self.get_selection("board")
        if not (0 <= pos_gx < board_size and 0 <= pos_gy < board_size):
            return

        self.player_pos = (pos_gx, pos_gy)
        self.visited = {self.player_pos}
        self.visited_moves = {self.player_pos: 0}
        self.move_count = 0
        self.path = [self.player_pos]

        self._update_legal_moves()
        self.replay_states = [self._capture_game_state()]

        self.clock_start_time = time.time()
        self.paused_elapsed = 0.0
        self.clock_elapsed = 0

        self.game_state = GameState.INGAME

    def toggle_hint_mode(self) -> None:
        """Toggle hint mode (non-crossing Warnsdorff degrees)."""
        self.hint_mode_active = not self.hint_mode_active
        if self.hint_mode_active:
            #self.guide_mode_active = False
            if self.player_pos:
                self._calculate_hint_degrees()
        else:
            self.hint_degrees = {}

    def toggle_guide_mode(self) -> None:
        """Toggle guide mode (move arrows)."""
        self.guide_mode_active = not self.guide_mode_active
#        if self.guide_mode_active:
#            self.hint_mode_active = False
#            self.hint_degrees = {}

    def new_game(self) -> None:
        """Reset to the menu, clearing all tour-specific state."""
        super().new_game()
        self.preview_pos = None
        self.tour_complete = False
        self.is_closed_tour = False
        self.copy_clicked = False
        self.kt_solver = None
        self.path = []
        self.player_pos = None
        self.visited.clear()
        self.visited_moves.clear()
        self.legal_moves.clear()
        self.move_count = 0
        self.clock_elapsed = 0
        self.final_elapsed = 0
        self.codec_input.set_text("")

    # ================================================================== #
    #  Rendering helpers                                                   #
    # ================================================================== #

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

        if (
            self.preview_pos is None
            or not (
                0 <= self.preview_pos[0] < prev_board
                and 0 <= self.preview_pos[1] < prev_board
            )
        ):
            self.preview_pos = (prev_board // 2, prev_board // 2)

        prev_cx, prev_cy = self.preview_pos
        prev_legal = get_legal_moves_for_board(
            piece_name, prev_cx, prev_cy, prev_board, prev_board, set()
        )

        ppx, ppy = self.board_renderer.to_pixel(prev_cx, prev_cy)
        piece_rect = pygame.Rect(ppx + 1, ppy + 1, cs - 2, cs - 2)
        try:
            pk.draw_piece(screen, piece_rect, piece_name)
        except Exception:
            pygame.draw.ellipse(screen, (0, 0, 0), piece_rect)

        if self.guide_mode_active and self.arrows:
            self._draw_arrows(screen, prev_legal, self.preview_pos)

    def _render_left_panel(
        self,
        screen: pygame.Surface,
        left_panel: UIPanel,
        msg_left: int,
        msg_right: int,
        msg_bottom: int,
    ) -> None:
        """Render MENU_PANEL and BUTTON_PANEL on the left panel."""
        btn_w = int(UI_SPACE * 1.5)
        line_height = self.font.get_linesize() + UI_SPACE

        # ---- MENU_PANEL: selector rows (piece shown in PIECE_PANEL) ----
        menu_bounds = left_panel.get_bounds("MENU_PANEL")
        text_x = menu_bounds["left"] + UI_SPACE
        menu_panel_items = [
            (i, (lbl, vals, cur))
            for i, (lbl, vals, cur) in enumerate(self.menu_items)
            if lbl != "piece"
        ]

        max_lbl_w = max(
            self.font.render(lbl + ":", True, (0, 0, 0)).get_width()
            for lbl, _, _ in self.menu_items
            if lbl != "piece"
        )
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

        # ---- BUTTON_PANEL ----
        piece_name = self.get_selection("piece")
        is_playable = self.get_selection("board") >= self._get_min_board_size(piece_name)

        if self.seed_mode_active:
            self.buttons["start"].active = (
                self.game_state == GameState.MENU and self._is_valid_codec_length()
            )
        else:
            self.buttons["start"].active = (
                self.game_state == GameState.MENU and is_playable
            )
        self.buttons["start"].rect = left_panel.get_widget_rect("BUTTON_PANEL", 0, BTW, BTH)
        if self.buttons["start"].active:
            self.buttons["start"].draw(screen)

        self.buttons["hint_mode"].active = self.game_state in (
            GameState.INGAME, GameState.ENDGAME
        )
        self.buttons["hint_mode"].text = (
            "hide degrees" if self.hint_mode_active else "show degrees"
        )
        self.buttons["hint_mode"].rect = left_panel.get_widget_rect(
            "BUTTON_PANEL", 0, BTW, BTH
        )
        if self.buttons["hint_mode"].active:
            self.buttons["hint_mode"].draw(screen)

        self.buttons["guide_mode"].active = self.game_state in (
            GameState.MENU, GameState.WAITING, GameState.INGAME, GameState.ENDGAME
        )
        self.buttons["guide_mode"].text = (
            "hide move guide" if self.guide_mode_active else "show move guide"
        )
        self.buttons["guide_mode"].rect = left_panel.get_widget_rect(
            "BUTTON_PANEL", 2, BTW, BTH
        )
        if self.buttons["guide_mode"].active:
            self.buttons["guide_mode"].draw(screen)

        self.buttons["track_mode"].active = True
        self.buttons["track_mode"].text = (
            "hide move #'s" if self.track_mode_active else "show move #'s"
        )
        self.buttons["track_mode"].rect = left_panel.get_widget_rect(
            "BUTTON_PANEL", 4, BTW, BTH
        )
        self.buttons["track_mode"].draw(screen)

        self.buttons["undo_mode"].active = (
            self.game_state == GameState.INGAME and len(self.replay_states) > 1
        )
        self.buttons["undo_mode"].rect = left_panel.get_widget_rect(
            "BUTTON_PANEL", 6, BTW, BTH
        )
        if self.buttons["undo_mode"].active:
            self.buttons["undo_mode"].draw(screen)

        self.buttons["resign"].active = self.game_state == GameState.INGAME
        self.buttons["resign"].rect = left_panel.get_widget_rect(
            "BUTTON_PANEL", 8, BTW, BTH
        )
        if self.buttons["resign"].active:
            self.buttons["resign"].draw(screen)

        self.buttons["retry"].active = (
            self.game_state == GameState.ENDGAME
            and self.last_puzzle_seed is not None
        )
        self.buttons["retry"].rect = left_panel.get_widget_rect(
            "MENU_PANEL", 7, BTW, BTH
        )
        if self.buttons["retry"].active:
            self.buttons["retry"].draw(screen)

        self.buttons["replay_mode"].active = self.game_state == GameState.ENDGAME
        self.buttons["replay_mode"].text = (
            "end replay" if self.replay_mode_active else "start replay"
        )
        self.buttons["replay_mode"].rect = left_panel.get_widget_rect(
            "BUTTON_PANEL", 6, BTW, BTH
        )
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
                    rm_rect.left - nav_w - 4, rm_rect.top, nav_w, BTH
                )
                self.buttons["replay_prev"].draw(screen)
            if self.replay_index < len(self.replay_states) - 1:
                self.buttons["replay_next"].active = True
                self.buttons["replay_next"].rect = pygame.Rect(
                    rm_rect.right + 4, rm_rect.top, nav_w, BTH
                )
                self.buttons["replay_next"].draw(screen)

        self.buttons["new_game"].active = self.game_state == GameState.ENDGAME
        self.buttons["new_game"].rect = left_panel.get_widget_rect(
            "BUTTON_PANEL", 8, BTW, BTH
        )
        if self.buttons["new_game"].active:
            self.buttons["new_game"].draw(screen)

        self.buttons["exit"].rect = pygame.Rect(
            msg_right - UI_SPACE * 8,
            msg_bottom - int(UI_SPACE * 5),
            BTW // 3,
            int(BTH * 0.75),
        )
        self.buttons["exit"].draw(screen)

    def _get_visible_button_names(self) -> List[str]:
        if self.game_state == GameState.MENU:
            return ["start", "guide_mode", "track_mode", "exit"]
        elif self.game_state == GameState.WAITING:
            return ["guide_mode", "track_mode", "resign"]
        elif self.game_state == GameState.INGAME:
            return ["guide_mode", "track_mode", "hint_mode", "undo_mode", "resign"]
        elif self.game_state == GameState.ENDGAME:
            btns = [
                "guide_mode", "track_mode", "hint_mode",
                "replay_mode", "retry", "new_game", "exit",
            ]
            if self.replay_mode_active:
                btns.insert(3, "replay_prev")
                btns.insert(4, "replay_next")
            return btns
        return []

    def _render_right_panel(self, screen: pygame.Surface, right_panel: UIPanel) -> None:
        """Render PIECE_PANEL and STATS_PANEL on the right panel."""
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
        p_plus_x = piece_bounds["left"] + piece_bounds["width"] - UI_SPACE - btn_w * 3

        sel_s = self.font_large.render(piece_name, True, (0, 0, 0))
        screen.blit(sel_s, sel_s.get_rect(center=(piece_bounds["center_x"], p_row_cy + 8)))

        move_set_text = pk.get_piece_move_sets_text(piece_name)
        if move_set_text:
            mst_s = self.font.render(move_set_text, True, (0, 0, 0))
            screen.blit(
                mst_s,
                mst_s.get_rect(
                    centerx=piece_bounds["center_x"],
                    top=p_row_cy + sel_s.get_height() + self.font.get_linesize(),
                ),
            )

        if self.game_state == GameState.MENU:
            pm_r = pygame.Rect(
                p_minus_x - btn_w, p_line_y, int(btn_w * 1.5), int(btn_w * 1.5)
            )
            pygame.draw.rect(screen, DK_SQUARE, pm_r)
            lt = self.font.render("<", True, (0, 160, 0))
            screen.blit(lt, lt.get_rect(center=pm_r.center))
            self.widget_rects[("minus", piece_idx)] = pm_r

            pp_r = pygame.Rect(
                p_plus_x - btn_w, p_line_y, int(btn_w * 1.5), int(btn_w * 1.5)
            )
            pygame.draw.rect(screen, DK_SQUARE, pp_r)
            gt = self.font.render(">", True, (255, 0, 0))
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

        stats_bounds = right_panel.get_bounds("STATS_PANEL")

        # Clock display
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
            screen.blit(
                clock_surf,
                clock_surf.get_rect(centerx=stats_bounds["center_x"], top=clock_y),
            )

        # Endgame message
        if self.game_state == GameState.ENDGAME and self.end_state:
            if self.end_state == "tour_complete" and self.tour_complete:
                tour_type = "closed" if self.is_closed_tour else "open"
                msg = f"non-crossing {tour_type} tour!"
                msg_color = (34, 177, 76) if self.is_closed_tour else (0, 128, 64)
            else:
                end_messages = {
                    "no_moves": ("no legal moves", (192, 0, 0)),
                    "resignation": ("resigned", (107, 70, 51)),
                    "timeout": ("time's up", (0, 0, 0)),
                }
                msg, msg_color = end_messages.get(self.end_state, ("game over", (0, 0, 0)))

            em_s = self.font_large.render(msg, True, msg_color)
            em_y = right_panel.get_line_y("STATS_PANEL", 5, line_height)
            screen.blit(em_s, em_s.get_rect(centerx=stats_bounds["center_x"], top=em_y))

    # ================================================================== #
    #  Main render and event handling                                     #
    # ================================================================== #

    def render(self, screen: pygame.Surface) -> None:
        """Render a complete game frame."""
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

        # Sync board model size in MENU
        if self.game_state == GameState.MENU:
            brd = self.get_selection("board")
            if self.board_model.cols != brd or self.board_model.rows != brd:
                self.board_model.cols = brd
                self.board_model.rows = brd
                self.board_model.clear()

        self._update_cell_size(
            area_left, area_top, area_right - area_left, area_bottom - area_top
        )

        self.board_renderer.draw_background(screen)
        self.widget_rects.clear()

        cs = self.current_cell_size
        if cs > 0:
            if self.game_state == GameState.MENU:
                self._render_menu_preview(screen)
            elif self.game_state in (
                GameState.INGAME, GameState.ENDGAME, GameState.WAITING
            ):
                self._render_game_specific_board(screen)

        self.board_renderer.draw_grid_lines(screen)

        # Overlay for WAITING state
        if self.game_state == GameState.WAITING:
            mf = pygame.font.SysFont("arial", 18)
            ms = mf.render("click a square to start", True, WAITING_MSG_COLOR)
            aw = area_right - area_left
            ah = area_bottom - area_top
            mx_pos = area_left + (aw - ms.get_width()) // 2
            my_pos = area_top + (ah - ms.get_height()) // 2
            pygame.draw.rect(
                screen, (240, 248, 255),
                (mx_pos - 8, my_pos - 6, ms.get_width() + 16, ms.get_height() + 12),
            )
            screen.blit(ms, (mx_pos, my_pos))

        # Error overlay
        if self.error_message and pygame.time.get_ticks() < self.error_timer:
            ef = pygame.font.SysFont("arial", 18)
            es = ef.render(self.error_message, True, (200, 0, 0))
            aw = area_right - area_left
            ah = area_bottom - area_top
            ex = area_left + (aw - es.get_width()) // 2
            ey = area_top + (ah - es.get_height()) // 2
            pygame.draw.rect(
                screen, (255, 240, 240),
                (ex - 8, ey - 6, es.get_width() + 16, es.get_height() + 12),
            )
            screen.blit(es, (ex, ey))
        elif self.error_message and pygame.time.get_ticks() >= self.error_timer:
            self.error_message = ""

        self._render_left_panel(screen, left_panel, msg_left, msg_right, msg_bottom)
        self._render_right_panel(screen, right_panel)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Process one pygame event.  Returns False if the game should quit."""
        if not super().handle_event(event):
            return False

        # Keyboard shortcut: H → toggle hint mode (in INGAME)
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
                        new_b = self.menu_items[item_idx][1][
                            self.menu_items[item_idx][2]
                        ]
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
                grid_pos = self.board_renderer.to_grid(mx, my)
                if grid_pos is not None:
                    self.make_move(grid_pos)

            elif self.game_state == GameState.MENU:
                grid_pos = self.board_renderer.to_grid(mx, my)
                if grid_pos is not None:
                    self.preview_pos = grid_pos

        return True