"""
move_system.py

Common move system for all Hamiltonian-Knights games.
Handles move validation and legal move generation.
"""

from typing import List, Tuple, Set, Optional


import piecekeeper as pk


def get_legal_moves_for_board(
    piece_name: str,
    x: int,
    y: int,
    cols: int,
    rows: int,
    visited: Set[Tuple[int, int]],
    forbidden: Optional[Set[Tuple[int, int]]] = None
) -> List[Tuple[int, int]]:
    """
    Get all legal moves for a piece at (x, y) on a board.

    Uses piecekeeper for piece-specific move generation. Visited and forbidden
    squares cannot be landed on. For sliding pieces, the path continues past
    visited squares (they are skipped but do not block further squares).

    Args:
        piece_name: Name of the chess piece (any piece in piecekeeper.PIECE_LIST)
        x, y: Current position
        cols, rows: Board dimensions
        visited: Set of already-visited squares (cannot land on)
        forbidden: Optional set of forbidden squares (cannot land on)

    Returns:
        List of legal (x, y) positions
    """
    if forbidden is None:
        forbidden = set()

    excluded = visited | forbidden
    n = max(cols, rows)
    raw_moves = pk.get_move_func(piece_name)(x, y, n)

    legal_moves = []
    for mx, my in raw_moves:
        if 0 <= mx < cols and 0 <= my < rows and (mx, my) not in excluded:
            legal_moves.append((mx, my))

    return legal_moves


def validate_move(
    from_pos: Tuple[int, int],
    to_pos: Tuple[int, int],
    legal_moves: List[Tuple[int, int]]
) -> bool:
    """
    Check if a move from from_pos to to_pos is legal.

    Args:
        from_pos: Starting position (unused but kept for API clarity)
        to_pos: Target position
        legal_moves: List of legal destination positions

    Returns:
        True if move is legal
    """
    return to_pos in legal_moves
