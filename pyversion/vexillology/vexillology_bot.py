"""
vexillology_bot.py

Bot AI for Vexillology – a two-player flag-capture game.
Three difficulty levels, numbered 1 (easiest) through 3 (hardest).

Level 1 – random legal move
Level 2 – prefer uncaptured flags, avoid dead-ends
Level 3 – Warnsdorff heuristic + flag-seeking domain scorer + opponent modeling
"""

import random
from enum import Enum
from typing import List, Tuple, Set, Optional

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


# ================================================================== #
#  Domain scorer                                                       #
# ================================================================== #

def _make_flag_scorer(
    uncaptured_flags: Set[Tuple[int, int]],
):
    """
    Build a domain scorer that rewards moves landing on or close to an
    uncaptured flag.

    Parameters
    ----------
    uncaptured_flags : set of flag positions not yet captured by either player

    Returns
    -------
    Callable[(x, y) -> float] or None
    """
    if not uncaptured_flags:
        return None

    def flag_scorer(move: Tuple[int, int]) -> float:
        # Immediate capture: highest priority
        if move in uncaptured_flags:
            return 10.0
        # Score by inverse Manhattan distance to nearest uncaptured flag
        min_dist = min(
            abs(move[0] - fx) + abs(move[1] - fy)
            for fx, fy in uncaptured_flags
        )
        return 1.0 / (1.0 + min_dist)

    return flag_scorer


# ================================================================== #
#  Public entry point                                                  #
# ================================================================== #

def make_bot_move(
    level: BotLevel,
    piece_name: str,
    pos: Tuple[int, int],
    board_size: int,
    all_visited: Set[Tuple[int, int]],
    uncaptured_flags: Optional[Set[Tuple[int, int]]] = None,
    opponent_pos: Optional[Tuple[int, int]] = None,
) -> Optional[Tuple[int, int]]:
    """
    Choose a move for the bot.

    Parameters
    ----------
    level            : BotLevel difficulty
    piece_name       : piece type in use
    pos              : current bot position
    board_size       : board dimension (n × n)
    all_visited      : combined set of squares visited by both players
    uncaptured_flags : flags not yet captured by either player
    opponent_pos     : opponent's current position (used at Level 3)

    Returns
    -------
    Chosen (x, y) square, or None if no legal moves exist.
    """
    moves = get_legal_moves(piece_name, pos, board_size, all_visited)
    if not moves:
        return None

    if level == BotLevel.LEVEL_1:
        return random.choice(moves)
    elif level == BotLevel.LEVEL_2:
        return _level2_move(piece_name, board_size, all_visited, moves, uncaptured_flags)
    elif level == BotLevel.LEVEL_3:
        return _level3_move(
            piece_name, board_size, all_visited, moves, uncaptured_flags, opponent_pos
        )
    return random.choice(moves)


# ================================================================== #
#  Level implementations                                              #
# ================================================================== #

def _level2_move(
    piece_name: str,
    board_size: int,
    all_visited: Set[Tuple[int, int]],
    moves: List[Tuple[int, int]],
    uncaptured_flags: Optional[Set[Tuple[int, int]]],
) -> Tuple[int, int]:
    """
    Level 2: avoid dead-end squares; strongly prefer flag squares.

    1. If any move lands directly on an uncaptured flag, take it.
    2. Otherwise pick the move(s) with the shortest Manhattan distance to
       the nearest uncaptured flag (dead-ends excluded when possible).
    3. Fall back to any non-dead-end move.
    """
    safe = filter_non_dead_ends(moves, piece_name, board_size, all_visited)

    if uncaptured_flags:
        # Immediate flag capture
        flag_moves = [m for m in safe if m in uncaptured_flags]
        if flag_moves:
            return random.choice(flag_moves)

        # Closest to a flag
        def _min_dist(m: Tuple[int, int]) -> int:
            return min(abs(m[0] - fx) + abs(m[1] - fy) for fx, fy in uncaptured_flags)

        best_dist = min(_min_dist(m) for m in safe)
        best_moves = [m for m in safe if _min_dist(m) == best_dist]
        return random.choice(best_moves)

    return random.choice(safe)


def _level3_move(
    piece_name: str,
    board_size: int,
    all_visited: Set[Tuple[int, int]],
    moves: List[Tuple[int, int]],
    uncaptured_flags: Optional[Set[Tuple[int, int]]],
    opponent_pos: Optional[Tuple[int, int]],
) -> Tuple[int, int]:
    """
    Level 3: Warnsdorff heuristic + flag-seeking domain scorer + opponent modeling.

    Heuristic priorities (via select_with_heuristics):
    1. Dead-end avoidance
    2. Domain score – prefer moves toward/onto uncaptured flags
    3. Warnsdorff degree (lower onward degree is better)
    4. Two-ply lookahead
    5. Center proximity
    6. Opponent modeling – minimize opponent's options
    7. Random tie-breaking
    """
    domain_scorer = _make_flag_scorer(uncaptured_flags) if uncaptured_flags else None
    return select_with_heuristics(
        moves=moves,
        piece_name=piece_name,
        board_size=board_size,
        all_visited=all_visited,
        domain_scorer=domain_scorer,
        opponent_pos=opponent_pos,
        use_two_ply=True,
    )