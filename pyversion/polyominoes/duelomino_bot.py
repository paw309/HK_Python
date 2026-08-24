"""
duelomino_bot.py

Bot AI for Gunkan two-player competitive polyomino game.
Five difficulty levels, numbered 1 (easiest) through 5 (hardest).

Level 1 – random legal move
Level 2 – avoid dead-end squares (random among non-dead-ends)
Level 3 – Warnsdorff's rule with dead-end avoidance
Level 4 – Warnsdorff + two-ply lookahead + center proximity + polyomino domain scorer
Level 5 – all of Level 4 + opponent modeling (minimize opponent's options)
"""

import random
from enum import Enum
from typing import List, Tuple, Set, Optional, Any

from bot_utils import (
    get_legal_moves,
    select_warnsdorff_move,
    select_with_heuristics,
    filter_non_dead_ends,
)


class BotLevel(Enum):
    """Bot difficulty levels."""
    LEVEL_1 = "1"
    LEVEL_2 = "2"
    LEVEL_3 = "3"
    LEVEL_4 = "4"
    LEVEL_5 = "5"




# ================================================================== #
#  Domain-Specific Helpers for Polyomino Game                       #
# ================================================================== #

def _count_new_polyomino_units(
    move: Tuple[int, int],
    puzzle_layout: List[Any],
    player_found_units: Set[Tuple[int, int]],
) -> int:
    """
    Count how many new polyomino units would be revealed by this move.

    Parameters
    ----------
    move               : proposed move position
    puzzle_layout      : list of PuzzleShape objects
    player_found_units : set of units already found by this player

    Returns
    -------
    Number of new units that would be revealed
    """
    count = 0
    for shape in puzzle_layout:
        if move in shape.puzzle_units and move not in player_found_units:
            count += 1
    return count


def _evaluate_polyomino_potential(
    move: Tuple[int, int],
    puzzle_layout: List[Any],
    player_found_units: Set[Tuple[int, int]],
) -> Tuple[int, int]:
    """
    Evaluate polyomino potential of a move.

    Returns (new_units, partial_shapes) where:
    - new_units: number of new polyomino units revealed
    - partial_shapes: number of shapes that would become partially completed

    Parameters
    ----------
    move               : proposed move position
    puzzle_layout      : list of PuzzleShape objects
    player_found_units : set of units already found by this player

    Returns
    -------
    Tuple of (new_units, partial_shapes)
    """
    new_units = 0
    partial_shapes = set()

    for shape in puzzle_layout:
        if move in shape.puzzle_units and move not in player_found_units:
            new_units += 1
            partial_shapes.add(shape.id)

    return new_units, len(partial_shapes)


def make_bot_move(
    level: BotLevel,
    piece_name: str,
    pos: Tuple[int, int],
    board_size: int,
    all_visited: Set[Tuple[int, int]],
    domain_data: Optional[Any] = None,
    opponent_pos: Optional[Tuple[int, int]] = None,
) -> Optional[Tuple[int, int]]:
    """
    Choose a move for the bot.

    Parameters
    ----------
    level        : BotLevel difficulty
    piece_name   : piece type in use
    pos          : current bot position
    board_size   : board dimension (n x n)
    all_visited  : combined set of squares visited by both players
    domain_data  : optional domain-specific data (for Gunkan: (puzzle_layout, player_found_units))
    opponent_pos : optional opponent position (used at Level 5)

    Returns
    -------
    The chosen (x, y) square, or None if no moves available.

    Notes
    -----
    For Gunkan, domain_data should be a tuple of (puzzle_layout, player_found_units)
    where puzzle_layout is a list of PuzzleShape objects and player_found_units
    is a set of units already found by this bot.
    """
    moves = get_legal_moves(piece_name, pos, board_size, all_visited)
    if not moves:
        return None

    if level == BotLevel.LEVEL_1:
        return _level1_move(moves)
    elif level == BotLevel.LEVEL_2:
        return _level2_move(piece_name, board_size, all_visited, moves)
    elif level == BotLevel.LEVEL_3:
        return _level3_move(piece_name, board_size, all_visited, moves)
    elif level == BotLevel.LEVEL_4:
        return _level4_move(piece_name, board_size, all_visited, moves, domain_data)
    elif level == BotLevel.LEVEL_5:
        return _level5_move(
            piece_name, board_size, all_visited, moves, domain_data, opponent_pos
        )
    return random.choice(moves)



# ================================================================== #
#  Level 1: pure random                                              #
# ================================================================== #

def _level1_move(
    moves: List[Tuple[int, int]],
) -> Tuple[int, int]:
    """Level 1: random move selection."""
    return random.choice(moves)


# ================================================================== #
#  Level 2: dead-end avoidance                                       #
# ================================================================== #

def _level2_move(
    piece_name: str,
    board_size: int,
    all_visited: Set[Tuple[int, int]],
    moves: List[Tuple[int, int]],
) -> Tuple[int, int]:
    """
    Level 2: avoid dead-end squares.

    Prefers moves that leave at least one onward move; falls back to any
    legal move when all candidates are dead-ends.
    """
    safe = filter_non_dead_ends(moves, piece_name, board_size, all_visited)
    return random.choice(safe)


# ================================================================== #
#  Level 3: Warnsdorff with dead-end avoidance                      #
# ================================================================== #

def _level3_move(
    piece_name: str,
    board_size: int,
    all_visited: Set[Tuple[int, int]],
    moves: List[Tuple[int, int]],
) -> Tuple[int, int]:
    """
    Level 3: Warnsdorff's rule with dead-end avoidance.

    Excludes dead-end moves first, then picks the move with the fewest
    onward options (Warnsdorff's heuristic).
    """
    return select_warnsdorff_move(
        moves, piece_name, board_size, all_visited,
        avoid_dead_ends=True,
    )


# ================================================================== #
#  Level 4: Warnsdorff + two-ply + center proximity + domain score  #
# ================================================================== #

def _level4_move(
    piece_name: str,
    board_size: int,
    all_visited: Set[Tuple[int, int]],
    moves: List[Tuple[int, int]],
    domain_data: Optional[Any],
) -> Tuple[int, int]:
    """
    Level 4: multi-heuristic with polyomino domain scorer, no opponent modeling.

    Heuristic priorities:
    1. Dead-end avoidance
    2. Domain objective (polyomino unit discovery)
    3. Warnsdorff degree
    4. Two-ply lookahead
    5. Center proximity
    6. Random tie-breaking
    """
    domain_scorer = _make_polyomino_scorer(domain_data)
    return select_with_heuristics(
        moves=moves,
        piece_name=piece_name,
        board_size=board_size,
        all_visited=all_visited,
        domain_scorer=domain_scorer,
        opponent_pos=None,
        use_two_ply=True,
    )


# ================================================================== #
#  Level 5: all heuristics + opponent modeling + domain score       #
# ================================================================== #

def _level5_move(
    piece_name: str,
    board_size: int,
    all_visited: Set[Tuple[int, int]],
    moves: List[Tuple[int, int]],
    domain_data: Optional[Any],
    opponent_pos: Optional[Tuple[int, int]],
) -> Tuple[int, int]:
    """
    Level 5: full multi-heuristic with polyomino domain scorer and opponent modeling.

    Heuristic priorities:
    1. Dead-end avoidance
    2. Domain objective (polyomino unit discovery)
    3. Warnsdorff degree
    4. Two-ply lookahead
    5. Center proximity
    6. Opponent modeling (minimize opponent's options)
    7. Random tie-breaking
    """
    domain_scorer = _make_polyomino_scorer(domain_data)
    return select_with_heuristics(
        moves=moves,
        piece_name=piece_name,
        board_size=board_size,
        all_visited=all_visited,
        domain_scorer=domain_scorer,
        opponent_pos=opponent_pos,
        use_two_ply=True,
    )


# ================================================================== #
#  Internal helpers                                                  #
# ================================================================== #

def _make_polyomino_scorer(domain_data: Optional[Any]) -> Optional[Any]:
    """
    Build a domain scorer function from domain_data, or return None.

    Parameters
    ----------
    domain_data : tuple of (puzzle_layout, player_found_units), or None

    Returns
    -------
    Callable or None
    """
    if domain_data is None:
        return None
    if not (isinstance(domain_data, tuple) and len(domain_data) >= 2):
        return None
    puzzle_layout, player_found_units = domain_data[0], domain_data[1]
    if puzzle_layout is None or player_found_units is None:
        return None

    def polyomino_scorer(move: Tuple[int, int]) -> float:
        """Score based on number of new polyomino units revealed."""
        new_units, _ = _evaluate_polyomino_potential(
            move, puzzle_layout, player_found_units
        )
        return float(new_units)

    return polyomino_scorer