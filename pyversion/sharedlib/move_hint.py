"""
move_hint.py

Calculates hint_degree values for squares reachable in one legal move from
the current position.  A hint_degree is the number of legal moves available
from that square after the piece arrives there (Warnsdorff-style lookahead).

Callable by any game in the repository – no dependency on a specific game
module.  Relies only on piecekeeper (also in sharedlib) and the Python
standard library.
"""

from typing import Callable, Dict, List, Optional, Set, Tuple

import piecekeeper as pk

SLIDING_PIECES: Set[str] = {"rook", "bishop", "queen"}


def _get_legal_moves(
    piece_name: str,
    x: int,
    y: int,
    cols: int,
    rows: int,
    visited: Set[Tuple[int, int]],
    forbidden: Optional[Set[Tuple[int, int]]] = None,
) -> List[Tuple[int, int]]:
    """Return all legal landing squares for *piece_name* from (x, y)."""
    if forbidden is None:
        forbidden = set()
    legal: List[Tuple[int, int]] = []
    max_n = max(cols, rows)
    lower_name = piece_name.lower()

    if lower_name in SLIDING_PIECES:
        dirs: List[Tuple[int, int]] = []
        if lower_name == "rook":
            dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        elif lower_name == "bishop":
            dirs = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        elif lower_name == "queen":
            dirs = [
                (1, 0), (-1, 0), (0, 1), (0, -1),
                (1, 1), (1, -1), (-1, 1), (-1, -1),
            ]
        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            while 0 <= nx < cols and 0 <= ny < rows:
                if (nx, ny) not in visited and (nx, ny) not in forbidden:
                    legal.append((nx, ny))
                nx += dx
                ny += dy
    else:
        move_func = pk.get_move_func(piece_name)
        raw = move_func(x, y, max_n)
        for mx, my in raw:
            if (
                0 <= mx < cols
                and 0 <= my < rows
                and (mx, my) not in visited
                and (mx, my) not in forbidden
            ):
                legal.append((mx, my))

    return legal


def calculate_hint_degrees(
    piece_name: str,
    current_pos: Tuple[int, int],
    cols: int,
    rows: int,
    visited: Set[Tuple[int, int]],
    forbidden: Optional[Set[Tuple[int, int]]] = None,
    next_piece_func: Optional[Callable[[int, int], str]] = None,
) -> Dict[Tuple[int, int], int]:
    """
    For every square reachable in one legal move from *current_pos*, compute
    the hint_degree – the number of onward legal moves available from that
    square (after it has been added to *visited*).

    Rules applied before returning:
    - Squares with hint_degree == 0 are excluded (dead ends shown as blank).
    - For sliding pieces (rook, bishop, queen) only the squares whose
      hint_degree is among the **two lowest non-zero values** are kept, to
      avoid visual clutter on high-mobility pieces.

    Parameters
    ----------
    piece_name     : name of the chess piece (used by piecekeeper).
    current_pos    : (x, y) grid coordinates of the current player position.
    cols, rows     : board dimensions.
    visited        : set of already-visited squares (includes *current_pos*).
    forbidden      : optional extra squares the piece cannot land on.
    next_piece_func: optional callable ``(x, y) -> piece_name`` that returns
                     the piece to use when counting onward moves from each
                     candidate square.  When supplied the degree for square
                     (mx, my) is the number of legal moves that *next piece*
                     has from (mx, my), rather than the moves of *piece_name*.
                     Useful for multi-piece cycling games where the active
                     piece changes upon landing.

    Returns
    -------
    Dict mapping (x, y) -> hint_degree for squares that should display a number.
    """
    cx, cy = current_pos
    legal_moves = _get_legal_moves(piece_name, cx, cy, cols, rows, visited, forbidden)

    degrees: Dict[Tuple[int, int], int] = {}
    for mx, my in legal_moves:
        # After moving to (mx, my) it becomes part of visited
        new_visited = visited | {(mx, my)}
        onward_piece = next_piece_func(mx, my) if next_piece_func is not None else piece_name
        onward = _get_legal_moves(onward_piece, mx, my, cols, rows, new_visited, forbidden)
        degree = len(onward)
        if degree >= 0:
            degrees[(mx, my)] = degree

    # For sliding pieces limit display to the two lowest non-zero degree values
    lower_name = piece_name.lower()
    if lower_name in SLIDING_PIECES and degrees:
        sorted_unique = sorted(set(degrees.values()))
        threshold = sorted_unique[1] if len(sorted_unique) >= 2 else sorted_unique[0]
        degrees = {pos: deg for pos, deg in degrees.items() if deg <= threshold}

    return degrees