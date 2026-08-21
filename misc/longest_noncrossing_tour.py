"""
longest_noncrossing_tour.py

Finds the longest non-crossing tour a chess/fairy-chess piece can complete
on an n x n board, using pieces defined in sharedlib/piecekeeper.py.

A "non-crossing" tour is a path where no two move-segments intersect
(share a point other than a shared endpoint).

Starting squares that are related by a rotation or reflection of the board
are equivalent, so only one representative from each symmetry class is tested.

Usage:
    python longest_noncrossing_tour.py

You will be prompted for a piece name and a board size.
All tours of the greatest length are written to a Python file named:
    {piece}_{n}x{n}_noncrossing_tours.py

The file contains a dictionary in the same format as the megalotours directory:
    {PIECE}_NONCROSSING_TOURS = {
        "{n}-1": [(x, y), ...],
        "{n}-2": [(x, y), ...],
        ...
    }
"""

import sys
import os

# Allow importing from sharedlib when run from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "sharedlib"))

from piecekeeper import PIECE_LIST, get_move_func


# ---------------------------------------------------------------------------
# Board symmetry helpers
# ---------------------------------------------------------------------------

def _all_transforms(x, y, n):
    """
    Return all 8 images of (x, y) under the dihedral symmetries of an n x n
    board (4 rotations x 2 reflections).
    """
    m = n - 1
    return [
        (x,     y    ),           # identity
        (y,     m - x),           # 90 deg CCW
        (m - x, m - y),           # 180 deg
        (m - y, x    ),           # 270 deg CCW
        (m - x, y    ),           # flip horizontal
        (x,     m - y),           # flip vertical
        (y,     x    ),           # flip main diagonal
        (m - y, m - x),           # flip anti-diagonal
    ]


def _canonical(x, y, n):
    """Canonical representative of (x, y) under all board symmetries."""
    return min(_all_transforms(x, y, n))


def representative_starts(n):
    """
    Return the list of starting squares that need to be searched.

    Any square whose canonical form has already been seen is skipped because
    its results are just a rotation/reflection of tours already found.
    """
    seen = set()
    reps = []
    for sx in range(n):
        for sy in range(n):
            key = _canonical(sx, sy, n)
            if key not in seen:
                seen.add(key)
                reps.append((sx, sy))
    return reps


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _cross(o, a, b):
    """2-D cross product of vectors OA and OB."""
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _on_segment(p, q, r):
    """True if point q lies on segment pr (collinear case)."""
    return (min(p[0], r[0]) <= q[0] <= max(p[0], r[0]) and
            min(p[1], r[1]) <= q[1] <= max(p[1], r[1]))


def segments_cross(p1, p2, p3, p4):
    """
    Return True if segment p1-p2 properly crosses segment p3-p4.

    Endpoints that coincide (shared tour waypoints) are *not* treated as
    crossings — only a genuine interior intersection counts.
    """
    d1 = _cross(p3, p4, p1)
    d2 = _cross(p3, p4, p2)
    d3 = _cross(p1, p2, p3)
    d4 = _cross(p1, p2, p4)

    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
       ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
        return True

    # Collinear cases — only count as crossing if one segment's interior
    # contains the other's endpoint AND the two segments share no endpoint.
    shared_endpoints = {p1, p2} & {p3, p4}

    if d1 == 0 and _on_segment(p3, p1, p4):
        if p1 not in shared_endpoints:
            return True
    if d2 == 0 and _on_segment(p3, p2, p4):
        if p2 not in shared_endpoints:
            return True
    if d3 == 0 and _on_segment(p1, p3, p2):
        if p3 not in shared_endpoints:
            return True
    if d4 == 0 and _on_segment(p1, p4, p2):
        if p4 not in shared_endpoints:
            return True

    return False


def new_segment_crosses_tour(path, new_sq):
    """
    Check whether the move from path[-1] to new_sq crosses any existing
    segment in the tour (path[i] -> path[i+1] for i in 0..len-2).

    The segment immediately before the new one (path[-2] -> path[-1]) shares
    an endpoint with the new move and is skipped.
    """
    if len(path) < 2:
        return False
    seg_start = path[-1]
    # Walk all existing segments except the one adjacent to seg_start
    for i in range(len(path) - 2):
        if segments_cross(seg_start, new_sq, path[i], path[i + 1]):
            return True
    return False


# ---------------------------------------------------------------------------
# DFS search
# ---------------------------------------------------------------------------

def find_longest_noncrossing_tours(piece_name, n):
    """
    Exhaustive DFS to find the longest non-crossing tour for *piece_name*
    on an n x n board.

    Returns (max_length, list_of_tours) where each tour is a list of (x,y).
    """
    move_func = get_move_func(piece_name)

    best_length = [1]          # mutable so inner function can update it
    best_tours = [[]]          # list of tours at best_length

    total_squares = n * n

    def dfs(path, visited):
        current = path[-1]
        candidates = [sq for sq in move_func(current[0], current[1], n)
                      if sq not in visited
                      and not new_segment_crosses_tour(path, sq)]

        if not candidates:
            # Dead end — record if this is a new best
            length = len(path)
            if length > best_length[0]:
                best_length[0] = length
                best_tours[0] = [list(path)]
                print(f"  New best: {length} squares", flush=True)
            elif length == best_length[0]:
                best_tours[0].append(list(path))
            return

        for sq in candidates:
            visited.add(sq)
            path.append(sq)
            dfs(path, visited)
            path.pop()
            visited.remove(sq)

    # Try only one representative starting square per symmetry class
    starts = representative_starts(n)
    print(f"  Testing {len(starts)} representative starting square(s) "
          f"(out of {n * n} total, symmetry-reduced).", flush=True)
    for start in starts:
        print(f"Starting from {start} ...", flush=True)
        dfs([start], {start})

    # Report Hamiltonian tours if found
    if best_length[0] == total_squares:
        print(f"\nHamiltonian tour found — visits all {total_squares} squares.")

    return best_length[0], best_tours[0]


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_tours(piece_name, n, tours, filename):
    """
    Write all longest tours to a Python file as a dictionary, using the same
    format as the megalotours directory.

    Keys:   "{n}-{instance}"  (e.g. "5-1", "5-2", ...)
    Values: list of (x, y) tuples representing the tour path
    """
    var_name = f"{piece_name.upper()}_NONCROSSING_TOURS"
    with open(filename, "w") as f:
        f.write(f"{var_name} = {{\n")
        for i, tour in enumerate(tours, 1):
            key = f"{n}-{i}"
            coords = ", ".join(f"({x}, {y})" for x, y in tour)
            f.write(f'    "{key}": [{coords}],\n')
        f.write("}\n")
    print(f"\nWrote {len(tours)} tour(s) to '{filename}'.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("Available pieces:")
    print("  " + ", ".join(PIECE_LIST))
    print()

    piece_name = input("Enter piece name: ").strip().lower()
    if piece_name not in PIECE_LIST:
        print(f"Error: '{piece_name}' is not a recognized piece.")
        print("Valid pieces: " + ", ".join(PIECE_LIST))
        sys.exit(1)

    try:
        n = int(input("Enter board size (single number, e.g. 5 for 5x5): ").strip())
    except ValueError:
        print("Error: board size must be an integer.")
        sys.exit(1)

    if n < 2:
        print("Error: board size must be at least 2.")
        sys.exit(1)

    print(f"\nSearching for the longest non-crossing tour of a {piece_name} "
          f"on a {n}x{n} board ...\n")

    max_length, tours = find_longest_noncrossing_tours(piece_name, n)

    filename = f"{piece_name}_{n}x{n}_noncrossing_tours.py"
    write_tours(piece_name, n, tours, filename)

    print(f"\nLongest tour: {max_length} square(s)  |  "
          f"Distinct tours found: {len(tours)}")


if __name__ == "__main__":
    main()