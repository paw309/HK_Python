import os
import json
import sys

# ─── Exact Piece Movement Vectors from PieceLibrary.ts ───────────────────────
PIECE_VECTORS = {
    'knight': [[1, 2]],
    'wazir': [[0, 1]],
    'prince': [[0, 1], [1, 2]],
    'squire': [[1, 1], [1, 2]],
    'lancer': [[0, 2], [1, 2]],
    'courier': [[1, 2], [2, 2]],
    'striker': [[1, 2], [0, 3]],
    'harrier': [[1, 2], [3, 3]],
    'gnu': [[1, 2], [1, 3]],
    'unicorn': [[1, 2], [2, 3]],
    'aurochs': [[1, 2], [1, 4]],
    'ostrich': [[1, 2], [1, 5]],
    'impala': [[1, 2], [3, 4]],
    'wapiti': [[1, 2], [2, 5]],
    'wazipper': [[0, 1], [3, 3]],
    'wazamel': [[0, 1], [1, 3]],
    'wazebra': [[0, 1], [2, 3]],
    'wazaffe': [[0, 1], [1, 4]],
    'wazelope': [[0, 1], [3, 4]],
    'wazelle': [[0, 1], [2, 5]],
    'ferzeaper': [[1, 1], [0, 3]],
    'ferzebra': [[1, 1], [2, 3]],
    'ferzaffe': [[1, 1], [1, 4]],
    'ferzelope': [[1, 1], [3, 4]],
    'ferzelle': [[1, 1], [2, 5]],
    'ferzingo': [[1, 1], [1, 6]],
    'zebbaba': [[0, 2], [2, 3]],
    'alfebra': [[2, 2], [2, 3]],
    'bison': [[1, 3], [2, 3]],
    'zebu': [[1, 3], [1, 4]],
    'vicuna': [[1, 3], [2, 5]],
    'frog': [[1, 1], [0, 3]],
    'eft': [[1, 1], [0, 5]],
    'toad': [[0, 2], [0, 3]],
    'tadpole': [[0, 3], [1, 3]],
    'fibonacci': [[1, 1], [2, 3], [3, 5], [5, 8]]
}


def get_piece_moves(piece_name, r, c):
    """
    Generate all possible legal absolute target positions for a piece from (r, c)
    by expanding each [dr, dc] vector across all valid sign combinations and
    coordinate permutations (rotations/reflections).
    """
    base_vectors = PIECE_VECTORS.get(piece_name, PIECE_VECTORS['knight'])
    moves = set()

    for dr, dc in base_vectors:
        for r_sign in (-1, 1):
            for c_sign in (-1, 1):
                moves.add((r + r_sign * dr, c + c_sign * dc))
                if dr != dc:
                    moves.add((r + r_sign * dc, c + c_sign * dr))

    return list(moves)


# ─── Hamiltonian Path Solver (Backtracking with Warnsdorf's Rule) ───────────
def has_valid_path(shape_cells, piece_name):
    if not shape_cells:
        return False

    cell_list = list(shape_cells)
    total_cells = len(cell_list)

    adjacency = {}
    for cell in shape_cells:
        r, c = cell
        raw_moves = get_piece_moves(piece_name, r, c)
        valid_neighbors = [m for m in raw_moves if m in shape_cells]
        if not valid_neighbors and total_cells > 1:
            return False
        adjacency[cell] = valid_neighbors

    def dfs_path(current, path, path_set):
        if len(path) == total_cells:
            return True

        neighbors = adjacency[current]
        unvisited_neighbors = [n for n in neighbors if n not in path_set]

        if not unvisited_neighbors and len(path) < total_cells:
            return False

        unvisited_neighbors.sort(key=lambda n: sum(1 for nn in adjacency[n] if nn not in path_set))

        for nxt in unvisited_neighbors:
            path_set.add(nxt)
            path.append(nxt)
            if dfs_path(nxt, path, path_set):
                return True
            path.pop()
            path_set.remove(nxt)

        return False

    for start_cell in cell_list:
        path_set = {start_cell}
        path = [start_cell]
        if dfs_path(start_cell, path, path_set):
            return True

    return False


# ─── Main Execution ──────────────────────────────────────────────────────────
def main():
    if len(sys.argv) > 1:
        piece_input = sys.argv[1]
    else:
        print("Available pieces:", ", ".join(PIECE_VECTORS.keys()))
        piece_input = input("Enter piece name: ")

    piece_name = piece_input.strip().lower()

    if piece_name not in PIECE_VECTORS:
        print(f"\nError: Unknown piece '{piece_name}'. Available pieces are: {list(PIECE_VECTORS.keys())}")
        sys.exit(1)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "hipcheck")
    sizes = range(8, 14)  # 08 to 13

    valid_shapes = []
    size_counts = {size: 0 for size in sizes}

    print(f"\nScanning polyomino libraries in '{data_dir}' (sizes 08-13) for piece: '{piece_name}'...")

    for size in sizes:
        size_str = f"{size:02d}"
        filename = os.path.join(data_dir, f"{size_str}-omino.json")

        if not os.path.exists(filename):
            print(f"  [Skipping] File not found: {filename}")
            continue

        print(f"  Processing {filename}...")

        try:
            with open(filename, 'r', encoding='utf-8') as f:
                shapes_data = json.load(f)

            count_for_size = 0
            for shape_id, coords in shapes_data.items():
                cell_set = {(cell[0], cell[1]) for cell in coords}

                if has_valid_path(cell_set, piece_name):
                    valid_shapes.append(shape_id)
                    count_for_size += 1

            size_counts[size] = count_for_size

        except Exception as e:
            print(f"  Error parsing {filename}: {e}")

    # Print summary breakdown by shape size
    print("\n" + "═" * 40)
    print(f" VALID PATH SUMMARY FOR PIECE: {piece_name.upper()}")
    print("═" * 40)
    for size in sizes:
        print(f"  Size {size:02d}-omino: {size_counts[size]} valid shapes")
    print("─" * 40)
    print(f"  Total Valid Shapes: {len(valid_shapes)}")
    print("═" * 40)

    output_filename = os.path.join(data_dir, f"{piece_name}-valid.json")
    output_data = {
        "piece": piece_name,
        "validShapes": valid_shapes
    }

    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)

    print(f"\nSaved results to {output_filename}")


if __name__ == "__main__":
    main()