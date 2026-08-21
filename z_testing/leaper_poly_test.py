#!/usr/bin/env python3
"""
test_poly_tour.py

Tests whether a single leaper can complete a full Hamiltonian path on a class
of polyominoes.

Usage (run from repo root):
    python -m z_testing.test_poly_tour <piece_name> <num_squares>

    piece_name  : one of knight camel zebra giraffe antelope gazelle flamingo bharal
    num_squares : 10 (decomino) | 11 (undecomino) | 12 (dodecomino)
                  13 (tridecomino) | 14 (tetradecomino) | 15 (pentadecomino)

Output:
    CSV file named  <piece_name>_<polyomino_class>.csv  written next to this script.
    Each row contains a sequential count and the polyomino key for every shape on
    which the leaper can complete a Hamiltonian path.
    Keys are wrapped as  ="key"  so that Microsoft Excel treats them as plain text
    and does not interpret them as dates.
"""

import csv
import importlib
import os
import sys
from typing import Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Ensure the repo root is on sys.path so imports work when running with
# `python z_testing/test_poly_tour.py` as well as `python -m z_testing...`
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from piecekeeper import PIECE_DATA, expand_patterns  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LEAPERS = ["knight", "zebra", "giraffe", "antelope", "gazelle", "flamingo", "bharal"]

# Maps the number of squares to (human-readable class name, importable module path)
POLYOMINO_REGISTRY: Dict[int, Tuple[str, str]] = {
    10: ("decomino",      "tourbus.polymath.decomino_data"),
    11: ("undecomino",    "tourbus.polymath.undecomino_data"),
    12: ("dodecomino",    "tourbus.polymath.dodecomino_data"),
    13: ("tridecomino",   "tourbus.polymath.tridecomino_data"),
    14: ("tetradecomino", "tourbus.polymath.tetradecomino_data"),
    15: ("pentadecomino", "tourbus.polymath.pentadecomino_data"),
    16: ("hexadecomino", "tourbus.megalotours.tours_hexadecomino"),
}


# ---------------------------------------------------------------------------
# Leaper tour logic
# ---------------------------------------------------------------------------

class LeaperTourPolyomino:
    """
    Tests whether a given leaper can complete a Hamiltonian path on a polyomino.
    """

    def __init__(self, polyomino: List[Tuple[int, int]], move_deltas: Set[Tuple[int, int]]):
        self.polyomino: Set[Tuple[int, int]] = set(polyomino)
        self.size: int = len(polyomino)
        self.coord_list: List[Tuple[int, int]] = list(polyomino)
        self.deltas: Set[Tuple[int, int]] = move_deltas

    def _valid_moves(self, pos: Tuple[int, int], visited: Set[Tuple[int, int]]) -> List[Tuple[int, int]]:
        x, y = pos
        return [
            (x + dx, y + dy)
            for dx, dy in self.deltas
            if (x + dx, y + dy) in self.polyomino and (x + dx, y + dy) not in visited
        ]

    def _onward_count(self, pos: Tuple[int, int], visited: Set[Tuple[int, int]]) -> int:
        return len(self._valid_moves(pos, visited))

    def find_tour_from_start(self, start: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
        """DFS with Warnsdorff heuristic; returns path list or None."""
        visited: Set[Tuple[int, int]] = set()
        path: List[Tuple[int, int]] = []

        def backtrack(pos: Tuple[int, int]) -> bool:
            visited.add(pos)
            path.append(pos)
            if len(visited) == self.size:
                return True
            moves = self._valid_moves(pos, visited)
            moves.sort(key=lambda p: self._onward_count(p, visited))
            for nxt in moves:
                if backtrack(nxt):
                    return True
            visited.remove(pos)
            path.pop()
            return False

        return path if backtrack(start) else None

    def find_any_tour(self) -> Optional[List[Tuple[int, int]]]:
        """Try every square as a starting position; return first path found."""
        for start in self.coord_list:
            tour = self.find_tour_from_start(start)
            if tour:
                return tour
        return None


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_polyomino_dict(num_squares: int) -> Optional[Dict[str, List[Tuple[int, int]]]]:
    """
    Import and return the SAMPLE_POLYOMINOES dict for the requested size.
    Returns None if the data file does not exist.
    """
    if num_squares not in POLYOMINO_REGISTRY:
        print(f"[error] No registry entry for {num_squares}-square polyominoes.")
        return None
    class_name, module_path = POLYOMINO_REGISTRY[num_squares]
    try:
        mod = importlib.import_module(module_path)
        data = getattr(mod, "SAMPLE_POLYOMINOES", None)
        if data is None:
            print(f"[warning] Module {module_path} has no SAMPLE_POLYOMINOES variable.")
        return data
    except ModuleNotFoundError:
        print(f"[warning] Data file for {class_name} not found ({module_path}). Skipping.")
        return None


def get_leaper_deltas(piece_name: str) -> Set[Tuple[int, int]]:
    """Return the full set of move deltas for a named leaper."""
    if piece_name not in PIECE_DATA:
        raise ValueError(f"Unknown piece '{piece_name}'. Available leapers: {LEAPERS}")
    pattern = PIECE_DATA[piece_name]["display_pattern"]
    return expand_patterns(pattern)


# ---------------------------------------------------------------------------
# Testing and CSV output
# ---------------------------------------------------------------------------

def run_tests(
    piece_name: str,
    polyomino_dict: Dict[str, List[Tuple[int, int]]],
    class_name: str,
) -> None:
    """
    Test all polyominoes in *polyomino_dict* for Hamiltonian-path feasibility
    with *piece_name*, then write a CSV of successful keys.
    """
    deltas = get_leaper_deltas(piece_name)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, f"{piece_name}_{class_name}.csv")

    print(f"\nTesting {len(polyomino_dict)} {class_name} polyominoes with {piece_name}...")

    successful: List[Tuple[int, str]] = []  # (1-based index, key)

    for key, coords in polyomino_dict.items():
        print(f"  {key} ({len(coords)} squares)...", end=" ", flush=True)
        tester = LeaperTourPolyomino(coords, deltas)
        tour = tester.find_any_tour()
        if tour:
            count = len(successful) + 1
            successful.append((count, key))
            print(f"✓")
        else:
            print("✗")

    # Write CSV
    # Keys are wrapped as ="key" so Excel treats them as text, not dates.
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["count", "polyomino_key"])
        for count, key in successful:
            writer.writerow([count, f'="{key}"'])

    print(f"\nResults written to: {csv_path}")
    print(f"  Successful: {len(successful)} / {len(polyomino_dict)}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _prompt_piece() -> str:
    """Prompt the user to choose a leaper and return the validated name."""
    print(f"Available leapers: {', '.join(LEAPERS)}")
    while True:
        piece_name = input("Enter piece name: ").lower().strip()
        if piece_name in LEAPERS:
            return piece_name
        print(f"  [invalid] '{piece_name}' not recognised. Please choose from: {', '.join(LEAPERS)}")


def _prompt_num_squares() -> int:
    """Prompt the user to choose a polyomino class and return the validated size."""
    size_labels = ", ".join(
        f"{k} ({v[0]})" for k, v in sorted(POLYOMINO_REGISTRY.items())
    )
    print(f"Available polyomino classes: {size_labels}")
    while True:
        raw = input("Enter number of squares: ").strip()
        try:
            num_squares = int(raw)
        except ValueError:
            print("  [invalid] Please enter a whole number.")
            continue
        if num_squares in POLYOMINO_REGISTRY:
            return num_squares
        print(f"  [invalid] {num_squares} is not available. Choose from: {sorted(POLYOMINO_REGISTRY.keys())}")


def main() -> None:
    # Accept optional command-line args for non-interactive use; otherwise prompt.
    if len(sys.argv) == 3:
        piece_name = sys.argv[1].lower().strip()
        if piece_name not in LEAPERS:
            print(f"[error] '{piece_name}' is not in the supported leaper list: {LEAPERS}")
            sys.exit(1)
        try:
            num_squares = int(sys.argv[2])
        except ValueError:
            print(f"[error] num_squares must be an integer, got '{sys.argv[2]}'")
            sys.exit(1)
        if num_squares not in POLYOMINO_REGISTRY:
            print(f"[error] num_squares must be one of {sorted(POLYOMINO_REGISTRY.keys())}")
            sys.exit(1)
    elif len(sys.argv) == 1:
        print("=" * 60)
        print("Leaper Hamiltonian Path Tester")
        print("=" * 60)
        piece_name = _prompt_piece()
        num_squares = _prompt_num_squares()
    else:
        print("Usage: python z_testing/test_poly_tour.py [<piece_name> <num_squares>]")
        print(f"  piece_name  : {', '.join(LEAPERS)}")
        print(f"  num_squares : {', '.join(str(k) for k in sorted(POLYOMINO_REGISTRY))}")
        sys.exit(1)

    class_name, _ = POLYOMINO_REGISTRY[num_squares]
    polyomino_dict = load_polyomino_dict(num_squares)
    if polyomino_dict is None:
        print(f"[error] Could not load polyomino data for size {num_squares}. Exiting.")
        sys.exit(1)

    print("=" * 60)
    print(f"Leaper: {piece_name}  |  Polyomino class: {class_name} ({num_squares} squares)")
    print("=" * 60)

    run_tests(piece_name, polyomino_dict, class_name)

    print("\n" + "=" * 60)
    print("DONE")


if __name__ == "__main__":
    main()