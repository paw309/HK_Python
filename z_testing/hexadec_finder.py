import random
import itertools
import time
from collections import deque

# -------- Configuration --------
N = 16                 # Hexadecomino size
TARGET_COUNT = 5000    # Number of knightable shapes to sample
OUTPUT_FILENAME = f"tours_hexadecominoes.py"
MAX_ATTEMPTS = 10**7   # Safety cutoff

# -------- Polyomino utilities --------

def normalize(poly):
    # Canonical form: sort coords, shift so (0,0) is included, choose minimal orientation
    variants = []
    for rot in range(4):
        for flip in [False, True]:
            p = [(x, y) for x, y in poly]
            # Rotate
            for _ in range(rot):
                p = [(-y, x) for x, y in p]
            # Flip
            if flip:
                p = [(-x, y) for x, y in p]
            min_x = min(x for x, y in p)
            min_y = min(y for x, y in p)
            norm = tuple(sorted((x-min_x, y-min_y) for x, y in p))
            variants.append(norm)
    return min(variants)

def random_polyomino(n):
    """Random walk to generate n-omino, returns tuple of coordinates."""
    for tries in range(100):  # try a few times if stuck
        shape = {(0, 0)}
        front = [(0, 0)]
        while len(shape) < n:
            curr = random.choice(front)
            # neighbors not in shape
            nbrs = [(curr[0]+dx, curr[1]+dy) for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]]
            nbrs = [p for p in nbrs if p not in shape]
            if not nbrs:
                break
            nxt = random.choice(nbrs)
            shape.add(nxt)
            front.append(nxt)
        if len(shape) == n:
            return normalize(shape)
    return None

knight_moves = [(-2,-1), (-2,1), (-1,-2), (-1,2), (1,-2), (1,2), (2,-1), (2,1)]

def build_knight_graph(cells):
    cell_set = set(cells)
    graph = {pt: set() for pt in cells}
    for pt in cells:
        for dx, dy in knight_moves:
            np = (pt[0]+dx, pt[1]+dy)
            if np in cell_set:
                graph[pt].add(np)
    return graph

def quick_knight_connected(graph):
    """Early rejection: all cells must be knight-reachable from some start node (BFS)"""
    nodes = list(graph)
    visited = set()
    queue = deque([nodes[0]])
    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        queue.extend(graph[node] - visited)
    return len(visited) == len(nodes)

def knight_tour(graph):
    """Try to find a knight's tour (Hamiltonian path) for the graph."""
    N = len(graph)
    def dfs(node, visited, path):
        if len(path) == N:
            return path
        for nb in graph[node]:
            if nb not in visited:
                res = dfs(nb, visited | {nb}, path + [nb])
                if res:
                    return res
        return None
    for start in graph:
        res = dfs(start, {start}, [start])
        if res:
            return res
    return None

def poly_to_str(poly, idx):
    return f"16-{idx+20001:04d}"

def coord_list_str(path):
    return "[" + ", ".join(f"({x}, {y})" for x, y in path) + "]"

# -------- Main sampling loop --------

found = {}
seen = set()
attempts = 0
start_time = time.time()

while len(found) < TARGET_COUNT and attempts < MAX_ATTEMPTS:
    poly = random_polyomino(N)
    attempts += 1
    if poly is None or poly in seen:
        continue
    seen.add(poly)
    graph = build_knight_graph(poly)
    # Early rejection
    if not quick_knight_connected(graph):
        continue
    if any(len(neigh) < 2 for neigh in graph.values()):
        continue  # must have at least two knight neighbors per cell
    tour = knight_tour(graph)
    if tour:
        idx = len(found)
        found[poly_to_str(poly, idx)] = tour
        print(f"Found {len(found)}/{TARGET_COUNT} at attempt {attempts} (elapsed: {int(time.time()-start_time)}s)")
    if attempts % 5000 == 0:
        print(f"Attempts: {attempts}, Found: {len(found)}, Time: {int(time.time()-start_time)}s")

# -------- Write to output file --------

print(f"\nWriting {len(found)} found shapes to {OUTPUT_FILENAME}")

with open(OUTPUT_FILENAME, "w") as f:
    f.write('"""\nAuto-generated tours on hexadecominoes.\n"""\n\n')
    f.write("TOURS_HEXADECOMINO = {\n")
    for key, path in found.items():
        coords = ", ".join(f"({x}, {y})" for (x, y) in path)
        f.write(f'    "{key}": [{coords}],\n')
    f.write("}\n")

print(f"Done! Sampled {len(found)} shapes in {attempts} attempts. Elapsed time: {int(time.time()-start_time)} seconds.")