#!/usr/bin/env python3
"""
busy_tetradecomino.py

Tests all combinations of three pieces taking alternating turns on every
tetradecomino, counting all Hamiltonian paths for each triplet.

No user input required.  Runs automatically and writes results to
tetradecomino_triplet_results.csv in the same directory.

CSV layout:
  rows    — one row per tetradecomino (skipped if all path counts are zero)
  columns — one column per piece-triplet combination (skipped if all counts
            across all tetradecominos are zero)
  cells   — number of Hamiltonian paths (0 if none found)

Piece triplets are generated with itertools.combinations so that no piece
appears more than once in any triplet and every unordered triplet appears
exactly once.  Within each triplet the pieces cycle as
  move 1, 4, 7, … → piece_a
  move 2, 5, 8, … → piece_b
  move 3, 6, 9, … → piece_c
"""

import csv
import itertools
import os
import sys
from typing import Dict, FrozenSet, List, Set, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from piecekeeper import PIECE_DATA
from pyversion.tourbus import TETRADECOMINO_TOURS

# ---------------------------------------------------------------------------
# Piece list
# ---------------------------------------------------------------------------

VALID_PIECES: List[str] = [
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
    "antelope",
    "gazelle",
    "flamingo",
]

# ---------------------------------------------------------------------------
# Move generation on a polyomino
# ---------------------------------------------------------------------------

# Buffer added on top of the polyomino bounding box when computing the
# virtual board size.  The largest leaper in VALID_PIECES has a (1,6)
# pattern (flamingo), so a reach of 6 in any direction is sufficient.
# Using 20 gives plenty of headroom for any future additions.
_LEAPER_BOUNDARY_BUFFER = 20


def _board_n(poly_set: FrozenSet[Tuple[int, int]]) -> int:
    """Smallest n such that all cells in *poly_set* lie within an n×n grid,
    plus a generous buffer so leapers are never boundary-clipped."""
    return max(max(a, b) for a, b in poly_set) + _LEAPER_BOUNDARY_BUFFER


def _get_moves_on_polyomino(
    piece_name: str,
    pos: Tuple[int, int],
    poly_set: FrozenSet[Tuple[int, int]],
    visited: Set[Tuple[int, int]],
) -> List[Tuple[int, int]]:
    """Return all unvisited squares reachable from *pos* inside *poly_set*."""
    x, y = pos
    move_func = PIECE_DATA[piece_name]["move_func"]
    raw = move_func(x, y, _board_n(poly_set))
    return [m for m in raw if m in poly_set and m not in visited]


# ---------------------------------------------------------------------------
# Hamiltonian path counter
# ---------------------------------------------------------------------------

def count_hamiltonian_paths(
    piece_a: str,
    piece_b: str,
    piece_c: str,
    coords: List[Tuple[int, int]],
) -> int:
    """Count all Hamiltonian paths on *coords* with three alternating pieces.

    *piece_a* makes moves 1, 4, 7, …
    *piece_b* makes moves 2, 5, 8, …
    *piece_c* makes moves 3, 6, 9, …
    Paths from every possible start square are counted.
    """
    poly_set = frozenset(tuple(c) for c in coords)
    target = len(coords)
    total = 0
    pieces = (piece_a, piece_b, piece_c)

    def dfs(pos: Tuple[int, int], visited: Set[Tuple[int, int]], move_index: int) -> None:
        nonlocal total
        if len(visited) == target:
            total += 1
            return
        piece = pieces[move_index % 3]
        for nxt in _get_moves_on_polyomino(piece, pos, poly_set, visited):
            visited.add(nxt)
            dfs(nxt, visited, move_index + 1)
            visited.remove(nxt)

    for start in poly_set:
        dfs(start, {start}, 0)

    return total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    tetra_ids = sorted(TETRADECOMINO_TOURS)

    # All unordered piece triplets with no repeated pieces.
    triplets: List[Tuple[str, str, str]] = list(
        itertools.combinations(VALID_PIECES, 3)
    )
    col_headers = [f"{a}/{b}/{c}" for a, b, c in triplets]

    total_tasks = len(tetra_ids) * len(triplets)
    done = 0

    # results[tetra_id][col_header] = path_count
    results: Dict[str, Dict[str, int]] = {tid: {} for tid in tetra_ids}

    print(
        f"busy_tetradecomino.py — testing {len(triplets)} piece triplets "
        f"× {len(tetra_ids)} tetradecominos ({total_tasks} tasks total)\n"
    )

    for tetra_id in tetra_ids:
        coords = TETRADECOMINO_TOURS[tetra_id]
        for piece_a, piece_b, piece_c in triplets:
            col = f"{piece_a}/{piece_b}/{piece_c}"
            paths = count_hamiltonian_paths(piece_a, piece_b, piece_c, coords)
            results[tetra_id][col] = paths
            done += 1
            print(
                f"  [{done}/{total_tasks}] {tetra_id}  {col:<45}  {paths}",
                flush=True,
            )

    # Determine which columns (triplets) have at least one non-zero result.
    active_cols = [
        col for col in col_headers
        if any(results[tid][col] > 0 for tid in tetra_ids)
    ]

    # Determine which tetradecomino rows have at least one non-zero result.
    active_ids = [
        tid for tid in tetra_ids
        if any(results[tid][col] > 0 for col in col_headers)
    ]

    # Write CSV
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "tetradecomino_triplet_results.csv")

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["tetradecomino"] + active_cols)
        for tid in active_ids:
            row = [tid] + [results[tid][col] for col in active_cols]
            writer.writerow(row)

    print(f"\nResults written to: {csv_path}")
    print(f"  Rows: {len(active_ids)} tetradecominos "
          f"(of {len(tetra_ids)} total, {len(tetra_ids) - len(active_ids)} skipped)")
    print(f"  Columns: {len(active_cols)} piece-triplet combinations "
          f"(of {len(triplets)} total, {len(triplets) - len(active_cols)} skipped)")


if __name__ == "__main__":
    main()