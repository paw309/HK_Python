import json

INPUT_FILE = "skinny_16ominoes.json"
OUTPUT_FILE = "tours_16_N.json"

KNIGHT_MOVES = [
    (2, 1), (1, 2), (1, -2), (2, -1),
    (-2, -1), (-1, -2), (-1, 2), (-2, 1)
]

def build_graph(cells):
    """Build adjacency list for knight moves restricted to given cells."""
    cell_set = set(map(tuple, cells))
    graph = {tuple(c): [] for c in cells}
    for x, y in cell_set:
        for dx, dy in KNIGHT_MOVES:
            nx, ny = x + dx, y + dy
            if (nx, ny) in cell_set:
                graph[(x, y)].append((nx, ny))
    return graph

def warnsdorff_order(graph, current, unvisited):
    """Order neighbors by Warnsdorff's heuristic (fewest onward moves)."""
    neighbors = [n for n in graph[current] if n in unvisited]
    def degree(n):
        return sum(1 for m in graph[n] if m in unvisited and m != current)
    neighbors.sort(key=degree)
    return neighbors

def backtrack_tour(graph, cells, use_warnsdorff=True):
    """Try to find a Hamiltonian path (knight's tour) starting from any cell."""
    n = len(cells)
    cell_list = [tuple(c) for c in cells]
    cell_set = set(cell_list)

    for start in cell_list:
        path = [start]
        visited = {start}

        def dfs(current):
            if len(path) == n:
                return True
            unvisited = cell_set - visited
            if use_warnsdorff:
                next_moves = warnsdorff_order(graph, current, unvisited)
            else:
                next_moves = [n for n in graph[current] if n in unvisited]
            for nxt in next_moves:
                visited.add(nxt)
                path.append(nxt)
                if dfs(nxt):
                    return True
                path.pop()
                visited.remove(nxt)
            return False

        if dfs(start):
            return path

    return None

def main():
    # Load input polyominoes
    with open(INPUT_FILE, "r") as f:
        poly_dict = json.load(f)

    tours = {}
    total = len(poly_dict)
    found = 0

    for idx, (key, cells) in enumerate(poly_dict.items(), start=1):
        graph = build_graph(cells)
        tour = backtrack_tour(graph, cells, use_warnsdorff=True)
        if tour is not None:
            tours[key] = [list(c) for c in tour]
            found += 1
        if idx % 100 == 0 or idx == total:
            print(f"tested {idx}/{total}, tours found: {found}")

    # Write successful tours to output file
    with open(OUTPUT_FILE, "w") as f:
        json.dump(tours, f, separators=(",", ":"))

    print(f"finished. {found} tours written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
