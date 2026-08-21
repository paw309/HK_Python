#!/usr/bin/env python3
"""
busy_heptomino.py

Tests all combinations of two pieces taking alternating turns on every
heptomino, counting all Hamiltonian paths for each pair.

No user input required.  Runs automatically and writes results to
heptomino_pair_results.csv in the same directory.

CSV layout:
  rows    — one row per heptomino (07-001 … 07-108)
  columns — one column per piece-pair combination
  cells   — number of Hamiltonian paths (0 if none found)

Piece pairs are generated with itertools.combinations_with_replacement so
that same-piece pairs (e.g. knight/knight) are included and every unordered
pair appears exactly once.  Within each pair the first piece makes moves
1, 3, 5, … and the second piece makes moves 2, 4, 6, …
"""

import csv
import itertools
import os
import sys
from typing import Dict, FrozenSet, List, Set, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from piecekeeper import PIECE_DATA
from pyversion.tourbus.polymath.undecomino_data import SAMPLE_POLYOMINOES

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
]

# ---------------------------------------------------------------------------
# Move generation on a polyomino
# ---------------------------------------------------------------------------

# Buffer added on top of the polyomino bounding box when computing the
# virtual board size.  The largest leaper in VALID_PIECES has a (1,4)
# pattern (giraffe), so a reach of 4 in any direction is sufficient.
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
    coords: List[Tuple[int, int]],
) -> int:
    """Count all Hamiltonian paths on *coords* with two alternating pieces.

    *piece_a* makes moves 1, 3, 5, … and *piece_b* makes moves 2, 4, 6, …
    Paths from every possible start square are counted.
    """
    poly_set = frozenset(tuple(c) for c in coords)
    target = len(coords)
    total = 0
    pieces = (piece_a, piece_b)

    def dfs(pos: Tuple[int, int], visited: set, move_index: int) -> None:
        nonlocal total
        if len(visited) == target:
            total += 1
            return
        piece = pieces[move_index & 1]
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

def _get_heptominoes():
    return {k: v for k, v in SAMPLE_POLYOMINOES.items() if k.startswith("11-")}


def main() -> None:
    heptominoes = _get_heptominoes()
    hept_ids = sorted(heptominoes)

    # All unordered piece pairs including same-piece combinations.
    pairs: List[Tuple[str, str]] = list(
        itertools.combinations_with_replacement(VALID_PIECES, 2)
    )
    col_headers = [f"{a}/{b}" for a, b in pairs]

    total_tasks = len(hept_ids) * len(pairs)
    done = 0

    # results[hept_id][col_header] = path_count
    results: Dict[str, Dict[str, int]] = {hid: {} for hid in hept_ids}

    print(
        f"busy_heptomino.py — testing {len(pairs)} piece pairs "
        f"× {len(hept_ids)} heptominoes ({total_tasks} tasks total)\n"
    )

    for hept_id in hept_ids:
        coords = heptominoes[hept_id]
        for piece_a, piece_b in pairs:
            col = f"{piece_a}/{piece_b}"
            paths = count_hamiltonian_paths(piece_a, piece_b, coords)
            results[hept_id][col] = paths
            done += 1
            print(
                f"  [{done}/{total_tasks}] {hept_id}  {col:<30}  {paths}",
                flush=True,
            )

    # Write CSV
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "undecomino_pair_results.csv")

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["undecomino"] + col_headers)
        for hept_id in hept_ids:
            row = [hept_id] + [results[hept_id][col] for col in col_headers]
            writer.writerow(row)

    print(f"\nResults written to: {csv_path}")
    print(f"  Rows: {len(hept_ids)} undecominoes")
    print(f"  Columns: {len(pairs)} piece-pair combinations")


if __name__ == "__main__":
    main()