"""
parity_hampath.py

Interactive script: tests whether four fairy-chess pieces (assigned to board
squares by row/column parity) can complete a Hamiltonian path on a
user-specified rectangular board.

Parity → piece mapping
    (row % 2, col % 2):
        (0, 0)  →  piece 1   (perm[0])
        (0, 1)  →  piece 2   (perm[1])
        (1, 0)  →  piece 3   (perm[2])
        (1, 1)  →  piece 4   (perm[3])

Usage
    python parity_hampath.py

    The script will prompt for the number of columns, number of rows, and
    four piece names.  It then tests every permutation of those four pieces
    (skipping the reverse of any already-tested permutation) from every
    canonical start square (one representative per symmetry orbit of the
    board), with a 60-second DFS budget per (permutation, start-square) pair.

    For each permutation the line
        Testing (p1, p2, p3, p4) ...
    is printed immediately.  If any start square yields a full Hamiltonian
    path the word "yes" is appended.

Available pieces (from sharedlib/piecekeeper.py)
    knight  king  wazir  ferz  dabbaba  alfil
    threeleaper  tripper  camel  zebra  giraffe
    antelope  gazelle  flamingo  bharal
"""

import itertools
import math
import os
import sys
import time
from typing import List, Set, Tuple

# ---------------------------------------------------------------------------
# Path fix – allow running directly from any working directory.
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from piecekeeper import get_move_func  # noqa: E402

# ---------------------------------------------------------------------------
# Allowed piece names (from the problem statement)
# ---------------------------------------------------------------------------
AVAILABLE_PIECES: List[str] = [
    "knight", "king", "wazir", "ferz", "dabbaba", "alfil",
    "threeleaper", "tripper", "camel", "zebra", "giraffe",
    "antelope", "gazelle", "flamingo", "bharal",
]

# Seconds budget for the DFS on each (permutation, start-square) pair.
TIME_LIMIT: float = 60.0

# ---------------------------------------------------------------------------
# Rectangular move generation (wraps piecekeeper's square-board move funcs)
# ---------------------------------------------------------------------------

def _rect_moves(
    piece: str,
    row: int,
    col: int,
    rows: int,
    cols: int,
) -> List[Tuple[int, int]]:
    """Squares reachable by *piece* from (row, col) on a rows×cols board.

    ``get_move_func`` only supports square boards (single ``n`` argument).
    We pass ``n = rows + cols`` (guaranteed ≥ both dimensions) and then clip
    results to the actual rectangle.
    """
    n = rows + cols
    return [
        (r, c)
        for (r, c) in get_move_func(piece)(row, col, n)
        if 0 <= r < rows and 0 <= c < cols
    ]


# ---------------------------------------------------------------------------
# Parity-based piece selector
# ---------------------------------------------------------------------------

def _zone_idx(row: int, col: int) -> int:
    """Map a square's parity to an index into a 4-element piece list.

    (row%2, col%2):  (0,0)→0  (0,1)→1  (1,0)→2  (1,1)→3
    """
    return (row % 2) * 2 + (col % 2)


# ---------------------------------------------------------------------------
# Canonical start squares (one per symmetry orbit of the board)
# ---------------------------------------------------------------------------

def _symmetry_transforms(rows: int, cols: int):
    """Return transform functions for the board's symmetry group.

    Rectangular (rows ≠ cols): D₂ – identity, H-flip, V-flip, 180°.
    Square      (rows == cols): D₄ – above plus four rotations/reflections.
    """
    R, C = rows, cols
    transforms = [
        lambda r, c, R=R, C=C: (r,       c      ),   # identity
        lambda r, c, R=R, C=C: (r,       C-1-c  ),   # horizontal flip
        lambda r, c, R=R, C=C: (R-1-r,   c      ),   # vertical flip
        lambda r, c, R=R, C=C: (R-1-r,   C-1-c  ),   # 180°
    ]
    if rows == cols:
        n = rows
        transforms += [
            lambda r, c, n=n: (c,     n-1-r),         # 90° CW
            lambda r, c, n=n: (n-1-c, r    ),         # 90° CCW
            lambda r, c, n=n: (c,     r    ),         # main-diagonal transpose
            lambda r, c, n=n: (n-1-c, n-1-r),        # anti-diagonal transpose
        ]
    return transforms


def canonical_start_squares(rows: int, cols: int) -> List[Tuple[int, int]]:
    """Return one representative start square per symmetry orbit.

    Squares are iterated in row-major order; the lexicographically smallest
    image under all symmetry transforms is used as the orbit's canonical
    representative.  (0, 0) is always the first element returned.
    """
    transforms = _symmetry_transforms(rows, cols)
    seen_reps: Set[Tuple[int, int]] = set()
    canonical: List[Tuple[int, int]] = []

    for r in range(rows):
        for c in range(cols):
            images: Set[Tuple[int, int]] = set()
            for t in transforms:
                tr, tc = t(r, c)
                if 0 <= tr < rows and 0 <= tc < cols:
                    images.add((tr, tc))
            rep = min(images)
            if rep not in seen_reps:
                seen_reps.add(rep)
                canonical.append(rep)

    return canonical


# ---------------------------------------------------------------------------
# DFS + Warnsdorff Hamiltonian-path search
# ---------------------------------------------------------------------------

def find_hamiltonian_path(
    pieces: Tuple[str, ...],
    rows: int,
    cols: int,
    start: Tuple[int, int],
    deadline: float,
) -> bool:
    """Return True if a Hamiltonian path starting at *start* exists.

    Performs a depth-first search with Warnsdorff's heuristic (fewest onward
    moves first) and aborts when ``time.time()`` exceeds *deadline*.

    The piece used FROM each square is determined by that square's parity zone.
    """
    target_depth = rows * cols  # visit every square
    sys.setrecursionlimit(max(2000, target_depth * 4))

    visited: Set[Tuple[int, int]] = {start}

    def _warnsdorff_key(nxt: Tuple[int, int]) -> int:
        """Count onward moves from *nxt* (Warnsdorff degree)."""
        piece_at_nxt = pieces[_zone_idx(nxt[0], nxt[1])]
        return sum(
            1
            for m in _rect_moves(piece_at_nxt, nxt[0], nxt[1], rows, cols)
            if m not in visited
        )

    def _dfs(row: int, col: int, depth: int) -> bool:
        if depth == target_depth:
            return True
        if time.time() > deadline:
            return False

        piece = pieces[_zone_idx(row, col)]
        nexts = [
            m for m in _rect_moves(piece, row, col, rows, cols)
            if m not in visited
        ]
        if not nexts:
            return False

        nexts.sort(key=_warnsdorff_key)

        for nr, nc in nexts:
            visited.add((nr, nc))
            if _dfs(nr, nc, depth + 1):
                return True
            visited.discard((nr, nc))
            if time.time() > deadline:
                return False

        return False

    return _dfs(start[0], start[1], 1)


# ---------------------------------------------------------------------------
# Permutation generation (skip reverses of already-tested permutations)
# ---------------------------------------------------------------------------

def filtered_permutations(
    pieces: List[str],
) -> List[Tuple[str, ...]]:
    """All permutations of *pieces* with reverses of prior permutations skipped.

    For every permutation P, its reverse R = reversed(P) is also a
    permutation.  We keep the first of each {P, R} pair encountered in the
    standard lexicographic ordering produced by itertools.permutations.
    """
    seen: Set[Tuple[str, ...]] = set()
    result: List[Tuple[str, ...]] = []
    for perm in itertools.permutations(pieces):
        rev = tuple(reversed(perm))
        if rev not in seen:
            seen.add(perm)
            result.append(perm)
    return result


# ---------------------------------------------------------------------------
# User-input helpers
# ---------------------------------------------------------------------------

def _prompt_int(prompt: str, lo: int = 1) -> int:
    while True:
        try:
            val = int(input(prompt).strip())
            if val >= lo:
                return val
            print(f"  Please enter an integer ≥ {lo}.")
        except ValueError:
            print("  Please enter a valid integer.")


def _prompt_piece(label: str) -> str:
    while True:
        raw = input(label).strip().lower()
        if raw in AVAILABLE_PIECES:
            return raw
        print(
            f"  '{raw}' is not a recognized piece.\n"
            f"  Available: {', '.join(AVAILABLE_PIECES)}"
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=== Parity Hamiltonian Path Tester ===\n")

    # --- Board dimensions ---
    cols = _prompt_int("Number of columns (c): ")
    rows = _prompt_int("Number of rows    (r): ")
    total = rows * cols
    print(
        f"\nBoard  : {rows} rows × {cols} cols  ({total} squares)"
        f"\nTarget : {total - 1} moves  (full Hamiltonian path)\n"
    )

    # --- Piece selection ---
    print("Available pieces:")
    for i, name in enumerate(AVAILABLE_PIECES, 1):
        print(f"  {i:2d}. {name}")
    print()

    selected: List[str] = []
    for slot in range(1, 5):
        selected.append(_prompt_piece(f"Piece {slot}: "))
    print(f"\nSelected : {selected}\n")

    # --- Canonical start squares ---
    starts = canonical_start_squares(rows, cols)
    print(
        f"Canonical start squares ({len(starts)} unique under board symmetry):\n"
        f"  {starts}\n"
    )

    # --- Permutations (reverse pairs collapsed) ---
    perms = filtered_permutations(selected)
    all_perms_count = math.factorial(len(selected))
    print(
        f"Permutations to test : {len(perms)}"
        f"  (of {all_perms_count} total; reverses excluded)\n"
    )
    print("-" * 60)

    # --- Search ---
    found_any = False
    for perm in perms:
        label = "(" + ", ".join(perm) + ")"
        print(f"Testing {label} ...", end="", flush=True)

        perm_found = False
        for start in starts:
            deadline = time.time() + TIME_LIMIT
            if find_hamiltonian_path(perm, rows, cols, start, deadline):
                perm_found = True
                break

        if perm_found:
            print("  yes")
            found_any = True
        else:
            print()   # newline only; no "no" clutter

    print("-" * 60)
    if not found_any:
        print("No Hamiltonian path found for any permutation.")


if __name__ == "__main__":
    main()