import os
import json
from hiptester import PIECE_VECTORS


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "hipcheck")
    sizes = range(8, 14)  # 08 to 13

    print("Scanning shape-to-size mapping from omino files...")
    shape_to_size = {}

    # Map each shape ID to its corresponding size by reading the source omino files
    for size in sizes:
        size_str = f"{size:02d}"
        filename = os.path.join(data_dir, f"{size_str}-omino.json")
        if not os.path.exists(filename):
            continue
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                shapes_data = json.load(f)
                for shape_id in shapes_data.keys():
                    shape_to_size[shape_id] = size
        except Exception as e:
            print(f"Error reading {filename}: {e}")

    master_unique_shapes = set()
    print("\nReading piece validation files...")

    # Iterate through every piece in PIECE_VECTORS and collect unique shape IDs
    for piece_name in PIECE_VECTORS.keys():
        piece_filename = os.path.join(data_dir, f"{piece_name}-valid.json")
        if not os.path.exists(piece_filename):
            print(f"  [Skipping] Not found: {piece_filename}")
            continue

        try:
            with open(piece_filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                valid_shapes = data.get("validShapes", [])
                master_unique_shapes.update(valid_shapes)
            print(f"  Loaded {len(valid_shapes)} shapes from {piece_name}-valid.json")
        except Exception as e:
            print(f"  Error reading {piece_filename}: {e}")

    # Sort all unique shape IDs
    sorted_master_shapes = sorted(list(master_unique_shapes))

    # Count unique shapes by size
    size_counts = {size: 0 for size in sizes}
    unknown_size_count = 0

    for shape_id in sorted_master_shapes:
        size = shape_to_size.get(shape_id)
        if size in size_counts:
            size_counts[size] += 1
        else:
            unknown_size_count += 1

    # Print summary breakdown by shape size
    print("\n" + "═" * 40)
    print(" MASTER UNIQUE SHAPE ID SUMMARY")
    print("═" * 40)
    for size in sizes:
        print(f"  Size {size:02d}-omino: {size_counts[size]} unique shapes")
    if unknown_size_count > 0:
        print(f"  Unknown Size: {unknown_size_count} unique shapes")
    print("─" * 40)
    print(f"  Total Unique Shape IDs: {len(sorted_master_shapes)}")
    print("═" * 40)

    # Save sorted master list to file
    output_filename = os.path.join(data_dir, "master-unique-shapes.json")
    output_data = {
        "totalUniqueShapes": len(sorted_master_shapes),
        "sizeCounts": size_counts,
        "uniqueShapeIds": sorted_master_shapes
    }

    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)

    print(f"\nSaved master sorted shape list to {output_filename}")


if __name__ == "__main__":
    main()