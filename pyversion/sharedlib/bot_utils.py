"""
bot_utils.py

Shared AI utilities for bot players across different game modes.
Provides common heuristics and helper functions for move selection.
"""

import random
from typing import List, Tuple, Set, Optional, Callable

from move_system import get_legal_moves_for_board


# ================================================================== #
#  Legal Move Helpers                                                 #
# ================================================================== #

def get_legal_moves(
        piece_name: str,
        pos: Tuple[int, int],
        board_size: int,
        all_visited: Set[Tuple[int, int]],
) -> List[Tuple[int, int]]:
    """
    Return legal moves for piece at pos, excluding all_visited.

    Parameters
    ----------
    piece_name  : piece type in use
    pos         : current position (x, y)
    board_size  : board dimension (n x n)
    all_visited : set of squares already visited

    Returns
    -------
    List of legal (x, y) positions
    """
    x, y = pos
    return get_legal_moves_for_board(piece_name, x, y, board_size, board_size, all_visited)


def calculate_warnsdorff_degree(
        piece_name: str,
        pos: Tuple[int, int],
        board_size: int,
        all_visited: Set[Tuple[int, int]],
) -> int:
    """
    Calculate Warnsdorff degree: number of moves available from pos after visiting it.

    This is the core of Warnsdorff's heuristic - choosing moves that leave the
    fewest onward options tends to avoid getting trapped.

    Parameters
    ----------
    piece_name  : piece type in use
    pos         : position to evaluate
    board_size  : board dimension (n x n)
    all_visited : set of squares already visited

    Returns
    -------
    Number of legal moves available from pos
    """
    new_visited = all_visited | {pos}
    return len(get_legal_moves(piece_name, pos, board_size, new_visited))


# ================================================================== #
#  Dead-End Detection                                                 #
# ================================================================== #

def is_dead_end(
        piece_name: str,
        pos: Tuple[int, int],
        board_size: int,
        all_visited: Set[Tuple[int, int]],
) -> bool:
    """
    Check if a move leads to a dead-end (no onward moves available).

    Parameters
    ----------
    piece_name  : piece type in use
    pos         : position to evaluate
    board_size  : board dimension (n x n)
    all_visited : set of squares already visited

    Returns
    -------
    True if pos is a dead-end, False otherwise
    """
    return calculate_warnsdorff_degree(piece_name, pos, board_size, all_visited) == 0


def filter_non_dead_ends(
        moves: List[Tuple[int, int]],
        piece_name: str,
        board_size: int,
        all_visited: Set[Tuple[int, int]],
) -> List[Tuple[int, int]]:
    """
    Filter out dead-end moves from a list of candidates.

    Returns non-dead-end moves if any exist, otherwise returns original list.
    This allows dead-ends to be chosen only when no alternatives exist.

    Parameters
    ----------
    moves       : candidate moves to filter
    piece_name  : piece type in use
    board_size  : board dimension (n x n)
    all_visited : set of squares already visited

    Returns
    -------
    Filtered list of moves, preferring non-dead-ends
    """
    safe_moves = [
        m for m in moves
        if not is_dead_end(piece_name, m, board_size, all_visited)
    ]
    return safe_moves if safe_moves else moves


# ================================================================== #
#  Position Evaluation Heuristics                                     #
# ================================================================== #

def calculate_center_distance(
        pos: Tuple[int, int],
        board_size: int,
) -> float:
    """
    Calculate Manhattan distance from position to board center.

    Lower distance is generally better (center control heuristic).

    Parameters
    ----------
    pos        : position to evaluate (x, y)
    board_size : board dimension (n x n)

    Returns
    -------
    Manhattan distance to center
    """
    x, y = pos
    center = (board_size - 1) / 2.0
    return abs(x - center) + abs(y - center)


# ================================================================== #
#  Warnsdorff Move Selection                                          #
# ================================================================== #

def select_warnsdorff_move(
        moves: List[Tuple[int, int]],
        piece_name: str,
        board_size: int,
        all_visited: Set[Tuple[int, int]],
        avoid_dead_ends: bool = True,
) -> Tuple[int, int]:
    """
    Select a move using Warnsdorff's rule (minimum degree heuristic).

    Warnsdorff's rule: among available moves, choose the one that leads to
    a square with the fewest onward moves. Ties are broken randomly.

    Parameters
    ----------
    moves            : candidate moves to choose from
    piece_name       : piece type in use
    board_size       : board dimension (n x n)
    all_visited      : set of squares already visited
    avoid_dead_ends  : if True, exclude dead-end moves before applying Warnsdorff

    Returns
    -------
    Selected move (x, y)
    """
    # Exclude dead-ends before applying Warnsdorff so a degree-0 move is
    # never chosen when higher-degree alternatives exist.
    candidate_moves = (
        filter_non_dead_ends(moves, piece_name, board_size, all_visited)
        if avoid_dead_ends else moves
    )

    candidates = []
    for m in candidate_moves:
        deg = calculate_warnsdorff_degree(piece_name, m, board_size, all_visited)
        candidates.append((deg, m))

    candidates.sort(key=lambda c: c[0])
    min_deg = candidates[0][0]
    tied = [m for d, m in candidates if d == min_deg]

    return random.choice(tied)


# ================================================================== #
#  Opponent Modeling                                                  #
# ================================================================== #

def count_opponent_moves(
        opponent_pos: Tuple[int, int],
        piece_name: str,
        board_size: int,
        all_visited: Set[Tuple[int, int]],
        hypothetical_move: Tuple[int, int],
) -> int:
    """
    Count how many legal moves the opponent would have after we make a move.

    Used for simple opponent modeling: prefer moves that minimize opponent options.

    Parameters
    ----------
    opponent_pos       : opponent's current position
    piece_name         : piece type in use
    board_size         : board dimension (n x n)
    all_visited        : set of squares already visited
    hypothetical_move  : our proposed move

    Returns
    -------
    Number of legal moves opponent would have
    """
    new_visited = all_visited | {hypothetical_move}
    return len(get_legal_moves(piece_name, opponent_pos, board_size, new_visited))


def apply_opponent_modeling(
        moves: List[Tuple[int, int]],
        opponent_pos: Optional[Tuple[int, int]],
        piece_name: str,
        board_size: int,
        all_visited: Set[Tuple[int, int]],
) -> List[Tuple[int, int]]:
    """
    Filter moves to minimize opponent's options (simple minimax).

    Among the given moves, returns those that minimize the number of legal
    moves available to the opponent. If opponent_pos is None, returns original list.

    Parameters
    ----------
    moves        : candidate moves to filter
    opponent_pos : opponent's current position (None if not applicable)
    piece_name   : piece type in use
    board_size   : board dimension (n x n)
    all_visited  : set of squares already visited

    Returns
    -------
    Filtered list of moves that minimize opponent options
    """
    if opponent_pos is None:
        return moves

    scored = []
    for m in moves:
        opp_moves = count_opponent_moves(opponent_pos, piece_name, board_size, all_visited, m)
        scored.append((opp_moves, m))

    scored.sort(key=lambda s: s[0])
    min_opp_moves = scored[0][0]
    return [m for opp_count, m in scored if opp_count == min_opp_moves]


# ================================================================== #
#  Advanced Multi-Ply Lookahead                                       #
# ================================================================== #

def calculate_two_ply_score(
        move: Tuple[int, int],
        piece_name: str,
        board_size: int,
        all_visited: Set[Tuple[int, int]],
) -> Tuple[int, float]:
    """
    Calculate two-ply lookahead score for a move.

    Returns (degree, avg_successor_degree) where:
    - degree: number of moves from this position (1-ply)
    - avg_successor_degree: average degree of successor positions (2-ply)

    Parameters
    ----------
    move        : position to evaluate
    piece_name  : piece type in use
    board_size  : board dimension (n x n)
    all_visited : set of squares already visited

    Returns
    -------
    Tuple of (degree, average_successor_degree)
    """
    new_visited = all_visited | {move}
    successors = get_legal_moves(piece_name, move, board_size, new_visited)
    deg = len(successors)

    if successors:
        successor_degrees = [
            calculate_warnsdorff_degree(piece_name, s, board_size, new_visited)
            for s in successors
        ]
        avg_deg = sum(successor_degrees) / len(successor_degrees)
    else:
        avg_deg = 0.0

    return deg, avg_deg


# ================================================================== #
#  Tie-Breaking with Multiple Heuristics                              #
# ================================================================== #

def select_with_heuristics(
        moves: List[Tuple[int, int]],
        piece_name: str,
        board_size: int,
        all_visited: Set[Tuple[int, int]],
        domain_scorer: Optional[Callable[[Tuple[int, int]], float]] = None,
        opponent_pos: Optional[Tuple[int, int]] = None,
        use_two_ply: bool = False,
) -> Tuple[int, int]:
    """
    Select move using multiple heuristics in priority order.

    Heuristic priority order:
    1. Dead-end avoidance (exclude dead-end moves before scoring when alternatives exist)
    2. Domain-specific objective (if domain_scorer provided, higher is better)
    3. Warnsdorff degree (lower is better - minimize onward moves)
    4. Two-ply lookahead (if enabled - higher avg successor degree is better)
    5. Center proximity (lower distance is better)
    6. Opponent modeling (if opponent_pos provided - minimize opponent options)
    7. Random tie-breaking

    Parameters
    ----------
    moves         : candidate moves to choose from
    piece_name    : piece type in use
    board_size    : board dimension (n x n)
    all_visited   : set of squares already visited
    domain_scorer : optional function to score domain-specific objective
    opponent_pos  : optional opponent position for modeling
    use_two_ply   : if True, use two-ply lookahead

    Returns
    -------
    Selected move (x, y)
    """
    # Exclude dead-ends before scoring so a degree-0 move is never chosen
    # when higher-degree alternatives exist.
    candidate_moves = filter_non_dead_ends(moves, piece_name, board_size, all_visited)

    scored = []

    for m in candidate_moves:
        # 1. Domain-specific score (negate for descending sort if higher is better)
        domain_score = -domain_scorer(m) if domain_scorer else 0.0

        # 2. Warnsdorff degree (ascending - lower is better)
        deg, avg_deg = calculate_two_ply_score(m, piece_name, board_size, all_visited)

        # 3. Two-ply average degree (negate for descending if used)
        avg_deg_score = -avg_deg if use_two_ply else 0.0

        # 4. Center proximity (ascending - lower is better)
        center_dist = calculate_center_distance(m, board_size)

        scored.append((domain_score, deg, avg_deg_score, center_dist, m))

    # Sort by all heuristics in priority order
    scored.sort(key=lambda s: (s[0], s[1], s[2], s[3]))
    best_key = (scored[0][0], scored[0][1], scored[0][2], scored[0][3])
    tied = [m for ds, d, ad, cd, m in scored if (ds, d, ad, cd) == best_key]

    # 5. Opponent modeling within ties
    if opponent_pos:
        tied = apply_opponent_modeling(tied, opponent_pos, piece_name, board_size, all_visited)

    # 6. Random selection from remaining ties
    return random.choice(tied)