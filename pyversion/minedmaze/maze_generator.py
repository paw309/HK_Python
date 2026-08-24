"""
maze_generator.py

Maze and path generation algorithms for Knights Maze game.
"""

import time
import random
from collections import deque
from typing import List, Tuple, Set, Callable, Optional


# Obstacle placement probability by density setting
_DENSITY_OBSTACLE_PROB = {"dense": 1.0, "sparse": 0.5}


def _make_rng(seed=None):
    """Create a random number generator with optional seed."""
    if seed is not None:
        return random.Random(seed)
    return random.Random()


def estimate_avg_mobility(
    move_func: Callable,
    n: int,
    samples: int = 50,
    rng=None,
) -> float:
    """
    Estimate the average number of legal moves per square for a piece on an n×n board.

    Samples random board squares and averages their legal move counts.  Used by
    adaptive_path_lengths() to scale path length targets by piece mobility.
    """
    if rng is None:
        rng = random.Random()
    squares = [(x, y) for x in range(n) for y in range(n)]
    total = sum(len(move_func(*rng.choice(squares), n)) for _ in range(samples))
    return total / samples


def adaptive_path_lengths(
    n: int,
    move_func: Callable,
    length_setting: str,
    rng=None,
) -> Tuple[int, int]:
    """
    Compute (min_len, max_len) for maze path generation based on board size and
    the piece's average mobility.

    High-mobility pieces (many legal moves per square) fill the board with
    obstacles quickly, causing paths to terminate early.  Lowering the target
    range for these pieces keeps generation fast and reliable.

    Args:
        n:              Board dimension (n×n).
        move_func:      Piece move function (x, y, n) → list of squares.
        length_setting: ``"short"`` or ``"long"``.
        rng:            Optional seeded random instance (used for sampling).

    Returns:
        ``(min_len, max_len)`` clamped to sensible minimums.
    """
    avg_mob = estimate_avg_mobility(move_func, n, rng=rng)

    # Reference mobility: knight-like piece (~5 avg moves on a typical board).
    # Scale is capped at 1.0 so low-mobility pieces don't get inflated targets.
    REF_MOBILITY = 5.0
    scale = min(1.0, REF_MOBILITY / max(avg_mob, 1.0))
    scale = max(scale, 0.2)  # never shrink targets to nothing

    n_sq = n * n

    if length_setting == "short":
        min_len = max(4, int(n * scale))
        max_len = max(min_len + 4, int(n * scale * 2))
    else:  # "long"
        min_len = max(5, int(n * scale * 2))
        max_len = max(min_len + 5, int(n_sq * scale))
        # Cap to board_area - board_size so the generator never tries to visit
        # every single square; this avoids exponentially long searches for
        # highly mobile pieces on large boards.
        max_len = min(max_len, n_sq - n)

    return min_len, max_len


def generate_path_and_obstacles(
    n: int,
    min_length: int,
    max_length: int,
    move_func: Callable,
    obstacles: Optional[Set] = None,
    start: Optional[Tuple[int, int]] = None,
    rng=None,
    density: str = "dense",
) -> Tuple[Optional[List[Tuple[int, int]]], Optional[Set[Tuple[int, int]]]]:
    """
    Generate a random path with obstacles on an n×n board.

    Walks a random path from start; at each step, squares reachable but not
    chosen may become obstacles depending on *density*:

    * ``"dense"``  – all unchosen reachable squares become obstacles (maximum mines).
    * ``"sparse"`` – each unchosen square becomes an obstacle with 50 % probability
                     (fewer mines, easier puzzle).

    Returns ``(path, obstacles)`` if path length is within ``[min_length,
    max_length]``, otherwise ``(None, None)``.
    """
    if rng is None:
        rng = random
    squares  = [(x, y) for x in range(n) for y in range(n)]
    if start is None:
        start = rng.choice(squares)
    path     = [start]
    path_set = {start}
    obstacles = set(obstacles) if obstacles else set()

    obs_prob = _DENSITY_OBSTACLE_PROB.get(density, 1.0)

    while len(path) < max_length:
        current = path[-1]
        moves   = [m for m in move_func(*current, n)
                   if m not in path_set and m not in obstacles]
        if not moves:
            break
        nxt = rng.choice(moves)
        path.append(nxt)
        path_set.add(nxt)
        for sq in moves:
            if sq == nxt or sq in obstacles or sq in path_set:
                continue
            if obs_prob >= 1.0 or rng.random() < obs_prob:
                obstacles.add(sq)

    if min_length <= len(path) <= max_length:
        return path, obstacles
    return None, None


def generate_maze_path_and_obstacles(
    n: int,
    min_length: int,
    max_length: int,
    move_func: Callable,
    max_attempts: int = 200,
    time_budget: float = 1.0,
    rng=None,
    density: str = "dense",
) -> Tuple[Optional[List[Tuple[int, int]]], Optional[Set[Tuple[int, int]]]]:
    """
    Attempt multiple starts to find a valid maze path with obstacles.

    Falls back to progressively shorter minimum lengths if needed.
    The *density* argument controls how many unchosen squares become obstacles
    (see :func:`generate_path_and_obstacles`).  Pass ``"random"`` to let this
    function resolve it internally using *rng* so the result is reproducible.

    Returns ``(path, obstacles)`` or ``(None, None)`` if unsuccessful.
    """
    if rng is None:
        rng = random

    # Resolve "random" density once so the entire generation run is consistent.
    if density == "random":
        density = rng.choice(["sparse", "dense"])

    squares        = [(x, y) for x in range(n) for y in range(n)]
    lowest_min_len = max(2, n // 2)

    for attempt_min_len in range(min_length, lowest_min_len - 1, -1):
        attempts   = 0
        start_time = time.time() if time_budget is not None else None
        while True:
            if max_attempts is not None and attempts >= max_attempts:
                break
            if time_budget is not None and (time.time() - start_time) > time_budget:
                break
            attempts += 1
            start = rng.choice(squares)
            path, obs = generate_path_and_obstacles(
                n, attempt_min_len, max_length, move_func,
                start=start, rng=rng, density=density,
            )
            if path:
                return path, obs

    return None, None


def min_moves_between(
    start: Tuple[int, int],
    target: Tuple[int, int],
    move_func: Callable,
    n: int
) -> float:
    """
    BFS minimum number of moves from start to target on an n×n board.
    Returns float('inf') if target is unreachable.
    """
    visited = set()
    queue   = deque([(start, 0)])
    while queue:
        current, dist = queue.popleft()
        if current == target:
            return dist
        for m in move_func(*current, n):
            if m not in visited:
                visited.add(m)
                queue.append((m, dist + 1))
    return float("inf")
