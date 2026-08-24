"""
minedcontrol_bot.py

Bot AI for Mined Maze 2, the two-player competitive mined-maze race.
Five difficulty levels numbered 1 (easiest) through 5 (hardest).

Level 1 – pure random: any reachable unvisited square, no path or mine
          awareness.  Hits mines very frequently.
Level 2 – high confusion (55 %): most moves are random (possibly hitting
          mines); occasionally follows the correct path.
Level 3 – medium confusion (30 %): often follows the path but still makes
          a fair number of wrong turns.
Level 4 – low confusion (12 %): mostly follows the path with occasional
          random detours into mines.
Level 5 – very low confusion (4 %): nearly always correct but still
          imperfect — a skilled human can beat it.

Confusion model
---------------
The maze guarantees exactly one correct next path square from every
position; every other reachable square is a mine.  At levels 2–5 the bot
knows the correct move (via maze_path_set / path_index), but with
probability `confusion_rate` it IGNORES all mine knowledge and picks a
completely random non-visited move.  Because many of those moves are mines,
this produces genuine mine hits at every level, in every game mode
(including "show mines" mode), and even in positions the bot has already
partially explored.  Lower confusion = fewer mine hits = harder to beat.

Domain data dict (passed as domain_data):
    maze_path_set   : Set[Tuple[int,int]]      – quick membership test for path
    path_index      : Dict[Tuple,int]          – position → index in path
    bot_player_num  : int                      – 1 (counts up) or 2 (counts down)
    known_mines     : Set[Tuple[int,int]]      – mines discovered by this player
    blocks_show     : bool                     – True when all mines are visible
    obstacles       : Set[Tuple[int,int]]      – all obstacle squares
"""

import random
from enum import Enum
from typing import Dict, List, Tuple, Set, Optional, Any

from bot_utils import get_legal_moves


# Probability of making a confused (completely random) move instead of
# following the correct path, per difficulty level.  When confused the bot
# picks from ALL non-visited moves — including mines — ignoring any mine
# knowledge.  This guarantees genuine mine hits in every game mode.
_CONFUSION_RATE: Dict[str, float] = {
    "2": 0.80,
    "3": 0.40,
    "4": 0.25,
    "5": 0.10,
}


class BotLevel(Enum):
    """Bot difficulty levels for Mined Maze 2."""
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
    Choose a move for the Mined Maze 2 bot.

    Parameters
    ----------
    level        : BotLevel difficulty
    piece_name   : piece type in use
    pos          : current bot position
    board_size   : board dimension (n x n)
    all_visited  : squares visited by this player
    domain_data  : maze-specific context dict (see module docstring)
    opponent_pos : opponent's current position (unused; reserved for future use)

    Returns
    -------
    Chosen (x, y) square, or None if no moves available.
    """
    moves = get_legal_moves(piece_name, pos, board_size, all_visited)
    if not moves:
        return None

    dd = domain_data or {}
    maze_path_set: Set  = dd.get("maze_path_set", set())
    path_index: Dict    = dd.get("path_index", {})
    bot_player_num: int = dd.get("bot_player_num", 1)
    known_mines: Set    = dd.get("known_mines", set())
    blocks_show: bool   = dd.get("blocks_show", False)
    obstacles: Set      = dd.get("obstacles", set())

    # P1 moves toward higher path indices; P2 moves toward lower path indices.
    direction: int = 1 if bot_player_num == 1 else -1

    # In show mode the bot sees all mines; otherwise only discovered ones.
    visible_mines: Set = obstacles if blocks_show else known_mines

    if level == BotLevel.LEVEL_1:
        return _level1_move(moves, maze_path_set, obstacles)

    # Levels 2–5 share the same path-aware + confusion model.
    confusion = _CONFUSION_RATE.get(level.value, 0.0)
    return _leveln_move(
        moves, pos, maze_path_set, path_index,
        visible_mines, direction, confusion, obstacles,
    )


# ================================================================== #
#  Shared maze-path helpers                                           #
# ================================================================== #

def _safe_moves(
    moves: List[Tuple[int, int]],
    visible_mines: Set[Tuple[int, int]],
) -> List[Tuple[int, int]]:
    """
    Return moves not in visible_mines (i.e. not known to be mines).
    Falls back to all moves if every candidate is a known mine.
    """
    safe = [m for m in moves if m not in visible_mines]
    return safe if safe else moves


def _maze_moves(
    moves: List[Tuple[int, int]],
    maze_path_set: Set[Tuple[int, int]],
    all_obstacles: Set[Tuple[int, int]],
) -> List[Tuple[int, int]]:
    """
    Filter moves to only valid maze squares (path or obstacle/mine).

    The maze generator may leave neutral squares on the board that are
    reachable by the piece but are neither path nor obstacle.  Selecting
    such a square causes make_move() to silently return without advancing
    the game, leaving the bot permanently stuck.  This filter ensures the
    bot never picks a neutral square.

    Falls back to the full move list if no valid maze squares are reachable
    (should not occur in a well-formed maze, but keeps the bot moving).
    """
    filtered = [m for m in moves if m in maze_path_set | all_obstacles]
    return filtered if filtered else moves


def _forward_path_moves(
    moves: List[Tuple[int, int]],
    pos: Tuple[int, int],
    maze_path_set: Set[Tuple[int, int]],
    path_index: Dict[Tuple[int, int], int],
    visible_mines: Set[Tuple[int, int]],
    direction: int,
) -> List[Tuple[int, int]]:
    """
    Return the correct forward path move(s), excluding known mines.

    direction=1  (P1): forward means higher path_index (counting up).
    direction=-1 (P2): forward means lower path_index (counting down).
    Falls back to any safe non-mine move when the path is fully blocked.
    """
    current_idx = path_index.get(pos, -1)
    # Path squares in the correct direction that aren't known mines.
    if direction > 0:
        forward = [m for m in moves
                   if m in maze_path_set
                   and m not in visible_mines
                   and path_index.get(m, -1) > current_idx]
    else:
        forward = [m for m in moves
                   if m in maze_path_set
                   and m not in visible_mines
                   and path_index.get(m, len(path_index)) < current_idx]
    if forward:
        return forward
    # Fall back to any non-mine move.
    return _safe_moves(moves, visible_mines)


# ================================================================== #
#  Level 1: pure random                                               #
# ================================================================== #

def _level1_move(
    moves: List[Tuple[int, int]],
    maze_path_set: Set[Tuple[int, int]],
    all_obstacles: Set[Tuple[int, int]],
) -> Tuple[int, int]:
    """Level 1: random move with no path or mine awareness."""
    return random.choice(_maze_moves(moves, maze_path_set, all_obstacles))


# ================================================================== #
#  Levels 2–5: path-aware with graduated confusion                   #
# ================================================================== #

def _leveln_move(
    moves: List[Tuple[int, int]],
    pos: Tuple[int, int],
    maze_path_set: Set[Tuple[int, int]],
    path_index: Dict[Tuple[int, int], int],
    visible_mines: Set[Tuple[int, int]],
    direction: int,
    confusion_rate: float,
    all_obstacles: Set[Tuple[int, int]],
) -> Tuple[int, int]:
    """
    Path-aware move with a confusion rate.

    With probability `confusion_rate` the bot is "confused" and picks
    completely at random from ALL non-visited moves — including every mine,
    whether or not it has been hit before and whether or not mines are
    displayed on the board.  Ignoring all mine knowledge guarantees genuine
    imperfection at every level and in every game mode.

    With probability (1 - confusion_rate) the bot follows the correct
    forward path move, avoiding known/visible mines.
    """
    # Restrict to valid maze squares (path or obstacle/mine) to prevent
    # selecting neutral squares that cause make_move() to silently return.
    candidates = _maze_moves(moves, maze_path_set, all_obstacles)

    if random.random() < confusion_rate:
        # Confused: ignore ALL mine knowledge and pick a random non-visited move.
        # This ensures mine hits even in "show mines" mode and even when the
        # bot has already discovered every mine adjacent to the current square.
        return random.choice(candidates)

    # Focused: follow the correct path, avoiding known/visible mines.
    return random.choice(
        _forward_path_moves(candidates, pos, maze_path_set, path_index,
                            visible_mines, direction)
    )