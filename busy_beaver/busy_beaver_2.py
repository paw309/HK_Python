import csv

BOARD_SIZE = 7

MOVESETS = {
    (2, 3),
    (2, 5),
    (3, 4),
    (3, 5),
}

def neighbors(square, a, b):
    """All legal moves from 'square' using jumps ±a or ±b on 1..7."""
    out = []
    for d in (a, -a, b, -b):
        nxt = square + d
        if 1 <= nxt <= BOARD_SIZE:
            out.append(nxt)
    return out

def search_from(start, a, b):
    """All Hamiltonian paths starting from 'start' for leaper [a,b]."""
    paths = []
    visited = [False] * (BOARD_SIZE + 1)
    visited[start] = True

    def dfs(path):
        if len(path) == BOARD_SIZE:
            paths.append(path.copy())
            return
        cur = path[-1]
        for nxt in neighbors(cur, a, b):
            if not visited[nxt]:
                visited[nxt] = True
                path.append(nxt)
                dfs(path)
                path.pop()
                visited[nxt] = False

    dfs([start])
    return paths

def enumerate_all(a, b):
    """All Hamiltonian paths for leaper [a,b], from any start."""
    all_paths = []
    for start in range(1, BOARD_SIZE + 1):
        all_paths.extend(search_from(start, a, b))
    return all_paths

def mirror_path(path):
    """Mirror a path p = (x1,...,x7) to p' = (8-x1,...,8-x7)."""
    return [BOARD_SIZE + 1 - x for x in path]

def canonical_path(path):
    """Canonical representative: lexicographically smaller of path and its mirror."""
    m = mirror_path(path)
    return tuple(min(path, m))

def path_to_string(path):
    return "-".join(str(x) for x in path)

def main():
    csv_rows = []

    for (a, b) in sorted(MOVESETS):
        print(f"\n=== Leaper [{a},{b}] ===")
        all_paths = enumerate_all(a, b)
        print(f"Total Hamiltonian paths (raw): {len(all_paths)}")

        # Build symmetry classes via canonical representatives
        classes = {}
        for p in all_paths:
            canon = canonical_path(p)
            classes.setdefault(canon, []).append(p)

        canon_list = sorted(classes.keys())
        print(f"Number of symmetry classes: {len(canon_list)}")

        # Add rows for CSV
        for class_id, canon in enumerate(canon_list, start=1):
            csv_rows.append({
                "leaper_a": a,
                "leaper_b": b,
                "class_id": class_id,
                "path": path_to_string(canon),
            })

    # Write CSV
    filename = "paths_1x7_twomove.csv"
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["leaper_a", "leaper_b", "class_id", "path"])
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"\nCSV written to {filename}")

if __name__ == "__main__":
    main()
