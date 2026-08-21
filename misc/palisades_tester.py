"""
palisades_twomoveset_tester.py

Tests a two-moveset piece (e.g. toad) in Palisades (non-crossing) conditions.

A two-moveset piece has exactly two component leap patterns (such as toad =
dabbaba {0,2} + threeleaper {0,3}).  At each step the piece may land on any
square reachable via *either* component pattern, provided:
  - the destination has not been visited, and
  - the new move-segment would not cross any earlier segment of the path.

The script runs NUM_TESTS (default 1000) random walks from random starting
squares and reports the longest path found and the average path length.

Usage:
    python palisades_twomoveset_tester.py

You will be prompted for a piece name and a board size.
"""

import sys
import os
import random

# Allow importing from sharedlib when run from any directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sharedlib"))

import piecekeeper as pk

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

NUM_TESTS = 100000


# ---------------------------------------------------------------------------
# Two-moveset helpers
# ---------------------------------------------------------------------------

def get_two_movesets(piece_name):
    """
    Return (deltas_a, deltas_b) for a piece with exactly two component patterns.

    Each returned value is the full symmetric delta-set for that component
    (produced by piecekeeper.expand_patterns).  Returns None if the piece
    does not have exactly two component patterns.
    """
    data = pk.PIECE_DATA.get(piece_name)
    if data is None:
        return None
    patterns = data["display_pattern"]
    if len(patterns) != 2:
        return None
    deltas_a = pk.expand_patterns([patterns[0]])
    deltas_b = pk.expand_patterns([patterns[1]])
    return deltas_a, deltas_b


def two_moveset_pieces():
    """Return all piece names that have exactly two component patterns (combo leapers)."""
    return [
        p for p in pk.PIECE_LIST
        if (pk.PIECE_DATA[p].get("piece_group") == "combo"
            and len(pk.PIECE_DATA[p].get("display_pattern", [])) == 2)
    ]


def moves_from_deltas(x, y, n, deltas):
    """Squares reachable from (x, y) on an n×n board using the given delta-set."""
    return [(x + dx, y + dy) for dx, dy in deltas
            if 0 <= x + dx < n and 0 <= y + dy < n]


# ---------------------------------------------------------------------------
# Non-crossing geometry (mirrors palisades_controller.py logic)
# ---------------------------------------------------------------------------

def _cross(o, a, b):
    """Signed area of triangle OAB (×2)."""
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _on_segment_interior(p, a, b):
    """True if point p lies strictly between a and b on segment a–b.

    Non-strict bounds are used so that axis-aligned segments (where min==max
    on one axis) are handled correctly; the endpoint exclusion (p != a, p != b)
    ensures we test only strictly interior points.
    """
    if _cross(a, b, p) != 0:
        return False
    return (
        min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
        and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])
        and p != a and p != b
    )


def _segments_properly_intersect(p1, p2, p3, p4):
    """True if segment p1–p2 crosses segment p3–p4 at an interior point."""
    d1 = _cross(p3, p4, p1)
    d2 = _cross(p3, p4, p2)
    d3 = _cross(p1, p2, p3)
    d4 = _cross(p1, p2, p4)
    return (
        ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0))
        and ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0))
    )


def _would_create_crossing(path, new_end):
    """
    Return True if the segment path[-1]→new_end would cross any earlier
    segment of path.

    Checks both proper X-intersections and T-intersections (a path vertex
    landing on the interior of the new segment, or the new endpoint landing
    on the interior of an existing segment).
    """
    n = len(path)
    if n < 3:
        return False
    new_start = path[-1]
    # Check all existing segments except the last (which shares new_start).
    for i in range(n - 2):
        s, e = path[i], path[i + 1]
        if _segments_properly_intersect(s, e, new_start, new_end):
            return True
        if _on_segment_interior(new_end, s, e):
            return True
    # T-intersection: an existing path vertex on the interior of the new segment.
    for v in path[:-1]:
        if _on_segment_interior(v, new_start, new_end):
            return True
    return False


# ---------------------------------------------------------------------------
# Random walk
# ---------------------------------------------------------------------------

def run_random_walk(n, deltas_a, deltas_b):
    """
    Run one random non-crossing walk on an n×n board.

    The piece starts at a random square and at each step moves to any
    unvisited square reachable via deltas_a OR deltas_b that would not
    create a crossing.  The walk ends when no such square exists.

    Returns the number of squares visited (path length).
    """
    start = (random.randint(0, n - 1), random.randint(0, n - 1))
    path = [start]
    visited = {start}

    while True:
        cx, cy = path[-1]
        raw_a = moves_from_deltas(cx, cy, n, deltas_a)
        raw_b = moves_from_deltas(cx, cy, n, deltas_b)

        candidates = list({
            m for m in raw_a + raw_b
            if m not in visited and not _would_create_crossing(path, m)
        })

        if not candidates:
            break

        nxt = random.choice(candidates)
        path.append(nxt)
        visited.add(nxt)

    return len(path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    valid_pieces = two_moveset_pieces()
    print("Two-moveset pieces available:")
    print("  " + ", ".join(valid_pieces))
    print()

    piece_name = input("Enter piece name: ").strip().lower()
    movesets = get_two_movesets(piece_name)
    if movesets is None or piece_name not in valid_pieces:
        print(f"Error: '{piece_name}' is not a recognized two-moveset piece.")
        print("Valid pieces: " + ", ".join(valid_pieces))
        sys.exit(1)

    deltas_a, deltas_b = movesets

    try:
        n = int(input("Enter board size (e.g. 8 for 8×8): ").strip())
    except ValueError:
        print("Error: board size must be an integer.")
        sys.exit(1)

    if n < 2:
        print("Error: board size must be at least 2.")
        sys.exit(1)

    patterns = pk.PIECE_DATA[piece_name]["display_pattern"]
    p0 = tuple(sorted(patterns[0]))
    p1 = tuple(sorted(patterns[1]))
    print(
        f"\nRunning {NUM_TESTS} random non-crossing walks for {piece_name} "
        f"(movesets {{{p0[0]},{p0[1]}}} and {{{p1[0]},{p1[1]}}}) "
        f"on a {n}×{n} board ...\n"
    )

    lengths = []
    longest = 0
    for _ in range(NUM_TESTS):
        length = run_random_walk(n, deltas_a, deltas_b)
        lengths.append(length)
        if length > longest:
            longest = length

    avg = sum(lengths) / len(lengths)
    print(f"Results after {NUM_TESTS} tests:")
    print(f"  Longest path : {longest} square(s)")
    print(f"  Average path : {avg:.2f} square(s)")


if __name__ == "__main__":
    main()