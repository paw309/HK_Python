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
    'wazil': [[0, 1], [2, 2]],
    'wazipper': [[0, 1], [3, 3]],
    'wazamel': [[0, 1], [1, 3]],
    'wazebra': [[0, 1], [2, 3]],
    'wazaffe': [[0, 1], [1, 4]],
    'wazibis': [[0, 1], [1, 5]],
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


# ─── Hamiltonian Path Counter (Undirected Paths) ───────────────────────────
def count_undirected_paths(shape_cells, piece_name):
    if not shape_cells:
        return 0

    cell_list = list(shape_cells)
    total_cells = len(cell_list)
    if total_cells == 1:
        return 1

    adjacency = {}
    for cell in shape_cells:
        r, c = cell
        raw_moves = get_piece_moves(piece_name, r, c)
        valid_neighbors = [m for m in raw_moves if m in shape_cells]
        adjacency[cell] = valid_neighbors

    total_directed_paths = 0

    for start_cell in cell_list:
        local_count = [0]

        def dfs_directed(current, path_set, path_len):
            if path_len == total_cells:
                local_count[0] += 1
                return

            neighbors = adjacency[current]
            unvisited_neighbors = [n for n in neighbors if n not in path_set]
            if not unvisited_neighbors:
                return

            unvisited_neighbors.sort(key=lambda n: sum(1 for nn in adjacency[n] if nn not in path_set))

            for nxt in unvisited_neighbors:
                path_set.add(nxt)
                dfs_directed(nxt, path_set, path_len + 1)
                path_set.remove(nxt)

        path_set = {start_cell}
        dfs_directed(start_cell, path_set, 1)
        total_directed_paths += local_count[0]

    # Every undirected Hamiltonian path corresponds to 2 directed orientations (start -> end and end -> start)
    return total_directed_paths // 2


# ─── Unique Rotations and Reflections Counter ──────────────────────────────
def count_unique_orientations(shape_cells):
    """
    Count the number of unique rotations and reflections (distinct visual orientations)
    under the dihedral group D4 (4 rotations x 2 reflections).
    """
    unique_shapes = set()
    cells = list(shape_cells)

    transformations = [
        lambda r, c: (r, c),
        lambda r, c: (-c, r),
        lambda r, c: (-r, -c),
        lambda r, c: (c, -r),
        lambda r, c: (r, -c),
        lambda r, c: (c, r),
        lambda r, c: (-r, c),
        lambda r, c: (-c, -r)
    ]

    for transform in transformations:
        transformed_cells = [transform(r, c) for r, c in cells]
        min_r = min(cell[0] for cell in transformed_cells)
        min_c = min(cell[1] for cell in transformed_cells)
        normalized = tuple(sorted((cell[0] - min_r, cell[1] - min_c) for cell in transformed_cells))
        unique_shapes.add(normalized)

    return len(unique_shapes)


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

    valid_shape_details = []

    # Store aggregated metrics per size
    size_metrics = {
        size: {
            "validShapes": 0,
            "totalPaths": 0,
            "totalOrientations": 0
        } for size in sizes
    }

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

            for shape_id, coords in shapes_data.items():
                cell_set = {(cell[0], cell[1]) for cell in coords}

                path_count = count_undirected_paths(cell_set, piece_name)
                if path_count > 0:
                    unique_orients = count_unique_orientations(cell_set)
                    valid_shape_details.append({
                        "shapeId": shape_id,
                        "size": size,
                        "paths": path_count,
                        "uniqueOrientations": unique_orients
                    })

                    # Accumulate counts for this size
                    size_metrics[size]["validShapes"] += 1
                    size_metrics[size]["totalPaths"] += path_count
                    size_metrics[size]["totalOrientations"] += unique_orients

        except Exception as e:
            print(f"  Error parsing {filename}: {e}")

    # Compute grand totals
    total_paths = sum(item["paths"] for item in valid_shape_details)
    total_unique_orientations = sum(item["uniqueOrientations"] for item in valid_shape_details)
    total_valid_shapes = len(valid_shape_details)

    output_filename = os.path.join(data_dir, f"{piece_name}-valid.json")
    output_data = {
        "piece": piece_name,
        "grandTotals": {
            "validShapes": total_valid_shapes,
            "paths": total_paths,
            "uniqueOrientations": total_unique_orientations
        },
        "sizeBreakdown": {
            f"{size:02d}-omino": size_metrics[size] for size in sizes
        },
        "validShapes": valid_shape_details
    }

    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)

    # ─── Console Display Output ──────────────────────────────────────────────
    print("\n" + "═" * 65)
    print(f" BREAKDOWN BY SHAPE SIZE FOR PIECE: {piece_name.upper()}")
    print("═" * 65)
    print(f"{'Size':<12} | {'Valid Shapes':<14} | {'Paths':<15} | {'Unique Orientations':<20}")
    print("─" * 65)

    for size in sizes:
        m = size_metrics[size]
        print(
            f"Size {size:02d}-omino | {m['validShapes']:<14,} | {m['totalPaths']:<15,} | {m['totalOrientations']:<20,}")

    print("═" * 65)
    print(f"{'GRAND TOTAL':<12} | {total_valid_shapes:<14,} | {total_paths:<15,} | {total_unique_orientations:<20,}")
    print("═" * 65)

    print(f"\nSaved detailed results to {output_filename}")


if __name__ == "__main__":
    main()