import sys
import os
import random

# Allow importing from sharedlib when run from any directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sharedlib"))
import piecekeeper as pk

NUM_TESTS = 100000

# ---------------------------------------------------------------------------
# Coordinate packing (major speedup)
# ---------------------------------------------------------------------------

def enc(x, y, n):
    return x * n + y

def dec(p, n):
    return divmod(p, n)

# ---------------------------------------------------------------------------
# Two-moveset helpers
# ---------------------------------------------------------------------------

def get_two_movesets(piece_name):
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
    return [
        p for p in pk.PIECE_LIST
        if (pk.PIECE_DATA[p].get("piece_group") == "combo"
            and len(pk.PIECE_DATA[p].get("display_pattern", [])) == 2)
    ]

# ---------------------------------------------------------------------------
# Precompute moves (huge speedup)
# ---------------------------------------------------------------------------

def precompute_moves(n, deltas):
    moves = [[] for _ in range(n*n)]
    for x in range(n):
        for y in range(n):
            p = enc(x, y, n)
            lst = moves[p]
            for dx, dy in deltas:
                nx, ny = x + dx, y + dy
                if 0 <= nx < n and 0 <= ny < n:
                    lst.append(enc(nx, ny, n))
    return moves

# ---------------------------------------------------------------------------
# Geometry (optimized)
# ---------------------------------------------------------------------------

def cross(ax, ay, bx, by, cx, cy):
    return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)

def on_segment_interior(px, py, ax, ay, bx, by):
    if cross(ax, ay, bx, by, px, py) != 0:
        return False
    return (
        min(ax, bx) <= px <= max(ax, bx) and
        min(ay, by) <= py <= max(ay, by) and
        not (px == ax and py == ay) and
        not (px == bx and py == by)
    )

def segments_intersect(ax, ay, bx, by, cx, cy, dx, dy):
    d1 = cross(cx, cy, dx, dy, ax, ay)
    d2 = cross(cx, cy, dx, dy, bx, by)
    d3 = cross(ax, ay, bx, by, cx, cy)
    d4 = cross(ax, ay, bx, by, dx, dy)
    return (
        ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and
        ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0))
    )

def would_cross(path, newp, n):
    if len(path) < 3:
        return False

    nx, ny = dec(newp, n)
    sx, sy = dec(path[-1], n)

    # Check against all but last segment
    for i in range(len(path) - 2):
        ax, ay = dec(path[i], n)
        bx, by = dec(path[i+1], n)

        if segments_intersect(ax, ay, bx, by, sx, sy, nx, ny):
            return True
        if on_segment_interior(nx, ny, ax, ay, bx, by):
            return True

    # T-intersection: existing vertex on new segment
    for p in path[:-1]:
        px, py = dec(p, n)
        if on_segment_interior(px, py, sx, sy, nx, ny):
            return True

    return False

# ---------------------------------------------------------------------------
# Random walk (optimized)
# ---------------------------------------------------------------------------

def run_random_walk(n, moves_a, moves_b):
    start = enc(random.randint(0, n-1), random.randint(0, n-1), n)
    path = [start]
    visited = {start}

    while True:
        p = path[-1]
        candidates = []

        for nxt in moves_a[p]:
            if nxt not in visited and not would_cross(path, nxt, n):
                candidates.append(nxt)

        for nxt in moves_b[p]:
            if nxt not in visited and not would_cross(path, nxt, n):
                candidates.append(nxt)

        if not candidates:
            break

        nxt = random.choice(candidates)
        visited.add(nxt)
        path.append(nxt)

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

    moves_a = precompute_moves(n, deltas_a)
    moves_b = precompute_moves(n, deltas_b)

    lengths = []
    longest = 0
    for _ in range(NUM_TESTS):
        length = run_random_walk(n, moves_a, moves_b)
        lengths.append(length)
        if length > longest:
            longest = length

    avg = sum(lengths) / len(lengths)
    print(f"Results after {NUM_TESTS} tests:")
    print(f"  Longest path : {longest} square(s)")
    print(f"  Average path : {avg:.2f} square(s)")


if __name__ == "__main__":
    main()
