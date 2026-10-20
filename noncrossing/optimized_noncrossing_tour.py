"""
longest_noncrossing_tour.py

Finds the longest non-crossing tour a chess/fairy-chess piece can complete
on an n x n board, using pieces defined in sharedlib/piecekeeper.py.

Performance Architecture:
  1. Complete Precomputed Edge-Intersection Graph (O(1) Bitwise Collision Masking).
  2. Depth-2 Branch Splitting: Pre-generates valid 2-step paths and distributes
     them across CPU cores to maximize parallel workload balancing on complex pieces.
  3. Lock-Free Dynamic DFS Traversal.
"""

import sys
import os
import time
from multiprocessing import Pool, cpu_count

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
# Precomputed Intersection Matrix
# ---------------------------------------------------------------------------

def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _on_segment(p, q, r):
    return (min(p[0], r[0]) <= q[0] <= max(p[0], r[0]) and
            min(p[1], r[1]) <= q[1] <= max(p[1], r[1]))


def segments_cross(p1, p2, p3, p4):
    """
    Return True if segment p1-p2 properly crosses segment p3-p4.
    """
    d1 = _cross(p3, p4, p1)
    d2 = _cross(p3, p4, p2)
    d3 = _cross(p1, p2, p3)
    d4 = _cross(p1, p2, p4)

    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
       ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
        return True

    shared_endpoints = {p1, p2} & {p3, p4}

    if d1 == 0 and _on_segment(p3, p1, p4) and p1 not in shared_endpoints:
        return True
    if d2 == 0 and _on_segment(p3, p2, p4) and p2 not in shared_endpoints:
        return True
    if d3 == 0 and _on_segment(p1, p3, p2) and p3 not in shared_endpoints:
        return True
    if d4 == 0 and _on_segment(p1, p4, p2) and p4 not in shared_endpoints:
        return True

    return False


class BoardGraph:
    """
    Precomputes the complete directed move graph and edge conflict bitmasks.
    """
    def __init__(self, piece_name, n):
        self.n = n
        self.move_func = get_move_func(piece_name)

        self.edges = []
        self.adj = {}

        for x in range(n):
            for y in range(n):
                u = (x, y)
                self.adj[u] = []
                for v in self.move_func(x, y, n):
                    edge = (u, v)
                    edge_id = len(self.edges)
                    self.edges.append(edge)
                    self.adj[u].append((v, edge_id))

        num_edges = len(self.edges)
        self.conflict_mask = [0] * num_edges

        for i in range(num_edges):
            u1, v1 = self.edges[i]
            mask = 0
            for j in range(num_edges):
                if i == j:
                    continue
                u2, v2 = self.edges[j]
                if segments_cross(u1, v1, u2, v2):
                    mask |= (1 << j)
            self.conflict_mask[i] = mask


# ---------------------------------------------------------------------------
# Parallel Worker Task & Branch Decomposition
# ---------------------------------------------------------------------------

GLOBAL_GRAPH = None


def _init_worker(piece_name, n):
    global GLOBAL_GRAPH
    GLOBAL_GRAPH = BoardGraph(piece_name, n)


def _worker_search_branch(task_args):
    """
    Evaluates a specific 2-step (or 1-step) initial branch.
    task_args: (path_tuple, active_mask)
    """
    g = GLOBAL_GRAPH
    path = list(task_args[0])
    visited = set(path)
    active_mask = task_args[1]

    best_len = 0
    tours = []

    def dfs(curr_path, mask):
        nonlocal best_len, tours
        curr = curr_path[-1]
        has_branches = False

        for v, eid in g.adj[curr]:
            if v not in visited and not (mask & (1 << eid)):
                has_branches = True
                visited.add(v)
                curr_path.append(v)
                dfs(curr_path, mask | g.conflict_mask[eid])
                curr_path.pop()
                visited.remove(v)

        if not has_branches:
            length = len(curr_path)
            if length > best_len:
                best_len = length
                tours = [list(curr_path)]
            elif length == best_len:
                tours.append(list(curr_path))

    dfs(path, active_mask)
    return best_len, tours


def generate_depth2_branches(piece_name, n):
    """
    Generates all non-crossing initial paths up to depth 2 starting from
    symmetry-reduced representative squares.
    """
    g = BoardGraph(piece_name, n)
    starts = representative_starts(n)
    tasks = []

    for start in starts:
        # Depth 1 moves
        for v1, eid1 in g.adj[start]:
            mask1 = g.conflict_mask[eid1]
            path1 = (start, v1)

            # Depth 2 moves
            v2_found = False
            for v2, eid2 in g.adj[v1]:
                if v2 != start and not (mask1 & (1 << eid2)):
                    v2_found = True
                    mask2 = mask1 | g.conflict_mask[eid2]
                    tasks.append(((start, v1, v2), mask2))

            # If no second move is possible, record depth-1 branch as a task
            if not v2_found:
                tasks.append((path1, mask1))

    return tasks


def find_longest_noncrossing_tours(piece_name, n):
    print("Generating initial Depth-2 branches for workload distribution...", flush=True)
    tasks = generate_depth2_branches(piece_name, n)
    print(f"  Split search into {len(tasks)} parallel sub-tasks across available CPU cores.\n", flush=True)

    workers = cpu_count()
    start_time = time.time()

    with Pool(processes=workers, initializer=_init_worker, initargs=(piece_name, n)) as pool:
        results = pool.map(_worker_search_branch, tasks, chunksize=1)

    elapsed = time.time() - start_time
    print(f"Search completed in {elapsed:.2f} seconds.")

    global_max = 0
    all_tours = []

    for length, tours in results:
        if length > global_max:
            global_max = length
            all_tours = tours
        elif length == global_max:
            all_tours.extend(tours)

    total_squares = n * n
    if global_max == total_squares:
        print(f"\nHamiltonian tour found — visits all {total_squares} squares.")

    return global_max, all_tours


# ---------------------------------------------------------------------------
# Output File Generation
# ---------------------------------------------------------------------------

def write_tours(piece_name, n, tours, filename):
    """
    Write all longest tours to a Python file as a dictionary, using the same
    format as the megalotours directory.
    """
    var_name = f"{piece_name.upper()}_NONCROSSING_TOURS"
    with open(filename, "w") as f:
        f.write(f"{var_name} = {{\n")
        for i, tour in enumerate(tours, 1):
            key = f"{n}-{i}"
            coords = ", ".join(f"({x}, {y})" for x, y in tour)
            f.write(f'    "{key}": [{coords}],\n')
        f.write("}\n")
    print(f"Wrote {len(tours)} tour(s) to '{filename}'.")


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