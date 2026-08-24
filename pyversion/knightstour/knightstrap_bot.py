"""
knightstrap_bot.py

Bot AI for Knightstrap two-player competitive knight's tour game.
Five difficulty levels, numbered 1 (easiest) through 5 (hardest).

Level 1 – random legal move
Level 2 – avoid dead-end squares (random among non-dead-ends)
Level 3 – Warnsdorff's rule with dead-end avoidance
Level 4 – Warnsdorff + two-ply lookahead + center proximity
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
    domain_data  : optional domain-specific data (reserved for future use)
    opponent_pos : optional opponent position (used at Level 5)

    Returns
    -------
    The chosen (x, y) square, or None if no moves available.
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
        return _level4_move(piece_name, board_size, all_visited, moves)
    elif level == BotLevel.LEVEL_5:
        return _level5_move(piece_name, board_size, all_visited, moves, opponent_pos)
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
    legal move when all candidates are dead-ends (filter_non_dead_ends
    returns the original list in that case).
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
#  Level 4: Warnsdorff + two-ply + center proximity                 #
# ================================================================== #

def _level4_move(
    piece_name: str,
    board_size: int,
    all_visited: Set[Tuple[int, int]],
    moves: List[Tuple[int, int]],
) -> Tuple[int, int]:
    """
    Level 4: multi-heuristic without opponent modeling.

    Heuristic priorities:
    1. Dead-end avoidance
    2. Warnsdorff degree
    3. Two-ply lookahead
    4. Center proximity
    5. Random tie-breaking
    """
    return select_with_heuristics(
        moves=moves,
        piece_name=piece_name,
        board_size=board_size,
        all_visited=all_visited,
        domain_scorer=None,
        opponent_pos=None,
        use_two_ply=True,
    )


# ================================================================== #
#  Level 5: all heuristics + opponent modeling                       #
# ================================================================== #

def _level5_move(
    piece_name: str,
    board_size: int,
    all_visited: Set[Tuple[int, int]],
    moves: List[Tuple[int, int]],
    opponent_pos: Optional[Tuple[int, int]],
) -> Tuple[int, int]:
    """
    Level 5: full multi-heuristic with opponent modeling.

    Heuristic priorities:
    1. Dead-end avoidance
    2. Warnsdorff degree
    3. Two-ply lookahead
    4. Center proximity
    5. Opponent modeling (minimize opponent's options)
    6. Random tie-breaking
    """
    return select_with_heuristics(
        moves=moves,
        piece_name=piece_name,
        board_size=board_size,
        all_visited=all_visited,
        domain_scorer=None,
        opponent_pos=opponent_pos,
        use_two_ply=True,
    )