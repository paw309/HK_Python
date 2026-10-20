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
    'wazamel': [[0, 1], [1, 3]],
    'wazebra': [[0, 1], [2, 3]],
    'ferzebra': [[1, 1], [2, 3]],
    'ferzaffe': [[1, 1], [1, 4]],
    'zebbaba': [[0, 2], [2, 3]],
    'bison': [[1, 3], [2, 3]],
    'zebu': [[1, 3], [1, 4]],
    'vicuna': [[1, 3], [2, 5]],
    'frog': [[1, 1], [0, 3]],
    'eft': [[1, 1], [0, 5]],
    'toad': [[0, 2], [0, 3]],
    'tadpole': [[0, 3], [1, 3]],
    'fibonacci': [[1, 1], [2, 3], [3, 5], [5, 8]]
}


def normalize_shape(cells):
    """Shift cells so min row is 0 and min col is 0, then return as a sorted tuple."""
    if not cells:
        return tuple()
    min_r = min(r for r, c in cells)
    min_c = min(c for r, c in cells)
    return tuple(sorted((r - min_r, c - min_c) for r, c in cells))


def is_symmetrical(cells):
    """
    Determine if a polyomino is symmetrical in rotation or reflection
    by checking if it has fewer than 8 unique dihedral transformations.
    """
    ops = [
        lambda r, c: (r, c),
        lambda r, c: (c, r),
        lambda r, c: (-r, c),
        lambda r, c: (-c, r),
        lambda r, c: (r, -c),
        lambda r, c: (c, -r),
        lambda r, c: (-r, -c),
        lambda r, c: (-c, -r),
    ]

    transforms = set()
    for op in ops:
        transformed = {op(r, c) for r, c in cells}
        transforms.add(normalize_shape(transformed))

    return len(transforms) < 8


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

    valid_json_path = os.path.join(data_dir, f"{piece_name}-valid.json")
    if not os.path.exists(valid_json_path):
        print(f"\nError: '{valid_json_path}' not found. Please run the valid path generation script first.")
        sys.exit(1)

    print(f"\nLoading valid shapes from '{valid_json_path}'...")
    with open(valid_json_path, 'r', encoding='utf-8') as f:
        valid_data = json.load(f)

    valid_shape_ids = valid_data.get("validShapes", [])
    print(f"Loaded {len(valid_shape_ids)} valid shapes for piece: '{piece_name}'.")

    # Load all xx-omino.json files (sizes 08 to 13) to build a shape_id -> coordinates lookup
    shape_lookup = {}
    sizes = range(8, 14)
    print(f"Loading polyomino libraries from '{data_dir}'...")
    for size in sizes:
        filename = os.path.join(data_dir, f"{size:02d}-omino.json")
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    shapes_data = json.load(f)
                    shape_lookup.update(shapes_data)
            except Exception as e:
                print(f"  Error parsing {filename}: {e}")

    print("Checking symmetry for valid shapes...")
    symmetrical_shapes = []

    for shape_id in valid_shape_ids:
        if shape_id in shape_lookup:
            coords = shape_lookup[shape_id]
            cell_set = {(cell[0], cell[1]) for cell in coords}
            if is_symmetrical(cell_set):
                symmetrical_shapes.append(shape_id)

    # Print summary breakdown
    print("\n" + "═" * 40)
    print(f" SYMMETRY CHECK SUMMARY FOR: {piece_name.upper()}")
    print("═" * 40)
    print(f"  Total Valid Shapes Checked: {len(valid_shape_ids)}")
    print(f"  Total Symmetrical Shapes: {len(symmetrical_shapes)}")
    print("═" * 40)

    output_filename = os.path.join(data_dir, f"{piece_name}-symmetrical.json")
    output_data = {
        "piece": piece_name,
        "symmetricalShapes": symmetrical_shapes
    }

    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)

    print(f"\nSaved results to {output_filename}")


if __name__ == "__main__":
    main()