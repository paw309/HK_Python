"""
vexillum_generator.py

Path and flag-placement generator for Capture the Flags.
Generates a random open path on a square grid and distributes flags along it.
"""

import time
import random
from typing import Optional, Tuple, List

import piecekeeper as pk


FLAG_DENSITY_MAP = {"low": 0.2, "medium": 0.3, "high": 0.4}


def generate_open_path_with_flags(
        board_size: int,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        move_func=None,
        max_attempts: int = 1000,
        time_budget: Optional[float] = None,
        flag_density_choice: str = "low",
        seed: Optional[int] = None,
) -> Tuple[Optional[List], Optional[List]]:
    """
    Generate a random open path on a square board and place flags on it.

    The last square of the path always gets a flag.  The remaining flags are
    placed at randomly chosen earlier squares so that the total flag count is
    approximately ``flag_density_choice`` × path length.

    Parameters
    ----------
    board_size          : Side length of the square board.
    min_length          : Minimum acceptable path length (default: board_size + 1).
    max_length          : Maximum path length to attempt (default: board_size * 2).
    move_func           : Callable ``(x, y, n) -> [(x, y), ...]``.  Defaults to
                          the knight move function from piecekeeper.
    max_attempts        : How many random starts to try before giving up.
    time_budget         : Optional wall-clock time limit in seconds.
    flag_density_choice : One of "low", "medium", "high".
    seed                : Optional RNG seed for reproducibility.

    Returns
    -------
    (path, flags) on success, or (None, None) on failure.
    ``path``  is a list of (x, y) tuples.
    ``flags`` is a subset of ``path`` positions where flags are placed.
    """
    rng = random.Random(seed)
    if move_func is None:
        move_func = pk.get_move_func("knight")
    if min_length is None:
        min_length = board_size + 1
    if max_length is None:
        max_length = board_size * 2

    squares = [(x, y) for x in range(board_size) for y in range(board_size)]
    start_time = time.time() if time_budget is not None else None

    for _ in range(max_attempts):
        if time_budget is not None and (time.time() - start_time) > time_budget:
            break
        start = rng.choice(squares)
        path = [start]
        path_set = {start}
        while len(path) < max_length:
            current = path[-1]
            moves = [m for m in move_func(*current, board_size) if m not in path_set]
            if not moves:
                break
            path.append(rng.choice(moves))
            path_set.add(path[-1])
        if len(path) >= min_length:
            num_flags = max(1, int(len(path) * FLAG_DENSITY_MAP[flag_density_choice]))
            last_idx = len(path) - 1
            num_random = num_flags - 1
            pool = list(range(len(path) - 1))
            k = min(num_random, len(pool))
            random_indices = rng.sample(pool, k=k)
            flags_idx = sorted(random_indices + [last_idx])
            return path, [path[i] for i in flags_idx]

    return None, None