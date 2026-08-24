"""
knightsturing_generator.py

Deterministic puzzle generator for the Knight's Turing Machine game.

Uses DFS with Warnsdorff degree ordering to find a Hamiltonian path of
length board_size² − 1 under the given piece cycle and rule set.

Public API:
    TURING_PIECES           – list of the 10 eligible leapers
    find_hamiltonian_path() – DFS search from a given start square
    generate_puzzle()       – tries every start square until a path is found
"""

import os
import sys
import time
from typing import List, Optional, Set, Tuple

# Ensure sharedlib is importable when running this module directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from piecekeeper import get_move_func
from pyversion.knightsturing.turing_engine import RuleSet, build_ruleset1, build_ruleset2, build_flip_flop_ruleset

# ---------------------------------------------------------------------------
# Piece pool – exactly the 11 leapers listed in the problem specification
# ---------------------------------------------------------------------------

TURING_PIECES: List[str] = [
    "knight",
    "king",
    "wazir",
    "ferz",
    "dabbaba",
    "alfil",
    "threeleaper",
    "tripper",
    "camel",
    "zebra",
    "giraffe",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _legal_moves(
    pos: Tuple[int, int],
    piece: str,
    visited: Set[Tuple[int, int]],
    board_size: int,
) -> List[Tuple[int, int]]:
    """Return unvisited squares reachable from *pos* with *piece*."""
    return [
        m for m in get_move_func(piece)(pos[0], pos[1], board_size)
        if m not in visited
    ]


def _warnsdorff_degree(
    move: Tuple[int, int],
    next_piece: str,
    visited: Set[Tuple[int, int]],
    board_size: int,
) -> int:
    """Count onward moves from *move* using *next_piece* (Warnsdorff ordering)."""
    temp = visited | {move}
    return len(_legal_moves(move, next_piece, temp, board_size))


# ---------------------------------------------------------------------------
# Core DFS
# ---------------------------------------------------------------------------

def find_hamiltonian_path(
    board_size: int,
    pieces: List[str],
    ruleset_id: int,
    start_pos: Tuple[int, int],
    deadline: float = float("inf"),
) -> Optional[List[Tuple[int, int, str]]]:
    """Try to find a Hamiltonian path starting from *start_pos*.

    Args:
        board_size: Side length of the square board.
        pieces:     Ordered list of piece names forming the cycle/rule set.
        ruleset_id: 1 for simple cycle, 2 for colour-based transitions.
        start_pos:  (row, col) of the starting square.
        deadline:   ``time.time()`` value after which to abort.

    Returns:
        A path as ``List[(row, col, piece)]`` of length ``board_size²``, or
        ``None`` if no Hamiltonian path was found before the deadline.

    Notes:
        The piece stored at position *i* of the returned path is the piece
        that will be used to make the *next* move **from** square *i*.
        (I.e. it is the result of applying the rule set upon *arriving* at
        square *i*.)  The very first entry always carries ``pieces[0]``.
    """
    ruleset: RuleSet = (
        build_ruleset1(pieces) if ruleset_id == 1
        else build_flip_flop_ruleset(pieces) if ruleset_id == 3
        else build_ruleset2(pieces)
    )
    # target = n² − 1 moves (edges) needed to visit all n² squares.
    # The path list has n² entries (one per square visited), so
    # len(path) − 1 == target means all squares have been visited.
    target: int = board_size * board_size - 1

    # Use explicit stack to avoid Python recursion limit on large boards.
    # Each stack frame: (pos, piece, visited_frozenset, path_snapshot)
    # This is memory-heavy; instead use a recursive helper with sys.setrecursionlimit.
    sys.setrecursionlimit(max(2000, board_size * board_size * 2))

    visited: Set[Tuple[int, int]] = {start_pos}
    path: List[Tuple[int, int, str]] = [(start_pos[0], start_pos[1], pieces[0])]

    def _dfs(pos: Tuple[int, int], piece: str) -> bool:
        """Return True when a complete Hamiltonian path has been appended."""
        if len(path) - 1 == target:
            return True
        if time.time() > deadline:
            return False

        legal = _legal_moves(pos, piece, visited, board_size)
        if not legal:
            return False

        # Compute next piece and Warnsdorff degree for each candidate move.
        # move_num = len(path) because path starts with 1 element (the start
        # square), so when making the N-th move the path already has N elements.
        # This naturally gives 1-based move numbers (N=1 for the first move).
        move_num = len(path)
        candidates: List[Tuple[int, int, int, str]] = []
        for m in legal:
            nxt = ruleset.apply(piece, m[0], m[1], move_num)
            deg = _warnsdorff_degree(m, nxt, visited, board_size)
            candidates.append((deg, m[0], m[1], nxt))

        # Sort by ascending degree then by (row, col) for determinism.
        candidates.sort()

        for deg, mr, mc, nxt_piece in candidates:
            m = (mr, mc)
            visited.add(m)
            path.append((mr, mc, nxt_piece))
            if _dfs(m, nxt_piece):
                return True
            path.pop()
            visited.discard(m)

        return False

    if _dfs(start_pos, pieces[0]):
        return list(path)
    return None


# ---------------------------------------------------------------------------
# Puzzle generator
# ---------------------------------------------------------------------------

def generate_puzzle(
    board_size: int,
    pieces: List[str],
    ruleset_id: int,
    seed: int = 0,
    time_limit: float = 10.0,
) -> Optional[List[Tuple[int, int, str]]]:
    """Find a Hamiltonian path by iterating through start squares.

    Start squares are tried in an order determined by *seed* (the first
    square tried is ``seed % board_size²``, then the rest in wrap-around
    order).  The first successful path found is returned.

    Args:
        board_size: Side length of the square board.
        pieces:     Ordered sequence of piece names (length 2, 3, or 4).
        ruleset_id: 1 or 2.
        seed:       Offsets which start square is tried first.
        time_limit: Wall-clock seconds budget for the whole search.

    Returns:
        Path as ``List[(row, col, piece)]`` of length ``board_size²``, or
        ``None`` if no path was found within the budget.
    """
    n2 = board_size * board_size
    offset = seed % n2
    deadline = time.time() + time_limit

    for i in range(n2):
        if time.time() > deadline:
            break
        idx = (offset + i) % n2
        row, col = divmod(idx, board_size)
        path = find_hamiltonian_path(
            board_size, pieces, ruleset_id, (row, col), deadline
        )
        if path is not None:
            return path

    return None