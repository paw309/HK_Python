import os
import json
import sys

# ─── Supported Pieces List ───────────────────────────────────────────────────
SUPPORTED_PIECES = [
    'knight', 'prince', 'squire', 'lancer', 'striker', 'ferzebra', 'ferzamel', 'courier',
    'gnu', 'unicorn', 'aurochs', 'ostrich', 'impala', 'wapiti'
]


def main():
    # Check for command-line argument first; if missing, prompt the user
    if len(sys.argv) > 1:
        piece_input = sys.argv[1]
    else:
        print("Available pieces:", ", ".join(SUPPORTED_PIECES))
        piece_input = input("Enter piece name to filter: ")

    piece_name = piece_input.strip().lower()

    if piece_name not in SUPPORTED_PIECES:
        print(f"\nError: Unknown piece '{piece_name}'. Available pieces are: {SUPPORTED_PIECES}")
        sys.exit(1)

    if piece_name == 'knight':
        print("\nError: Cannot filter 'knight-valid.json' against itself.")
        sys.exit(1)

    # Base directory is one level above 'hipcheck' (root project directory)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "hipcheck")

    knight_json_path = os.path.join(data_dir, "knight-valid.json")
    piece_json_path = os.path.join(data_dir, f"{piece_name}-valid.json")

    # Verify files exist
    if not os.path.exists(knight_json_path):
        print(f"\nError: Could not find '{knight_json_path}'. Please generate knight-valid.json first.")
        sys.exit(1)

    if not os.path.exists(piece_json_path):
        print(f"\nError: Could not find '{piece_json_path}'. Please run the tester script for '{piece_name}' first.")
        sys.exit(1)

    print(f"\nProcessing filter for piece: '{piece_name}'...")

    # Load knight-valid shapes into a set for fast O(1) lookup
    try:
        with open(knight_json_path, 'r', encoding='utf-8') as f:
            k_data = json.load(f)
            knight_valid_set = set(k_data.get("validShapes", []))
        print(f"  Loaded {len(knight_valid_set)} knight-valid shapes.")
    except Exception as e:
        print(f"  Error reading knight-valid.json: {e}")
        sys.exit(1)

    # Load the target piece's valid shapes
    try:
        with open(piece_json_path, 'r', encoding='utf-8') as f:
            piece_data = json.load(f)
            piece_shapes = piece_data.get("validShapes", [])
        print(f"  Loaded {len(piece_shapes)} shapes from '{piece_name}-valid.json'.")
    except Exception as e:
        print(f"  Error reading {piece_name}-valid.json: {e}")
        sys.exit(1)

    # Perform comparison and removal
    original_count = len(piece_shapes)
    filtered_shapes = [shape_id for shape_id in piece_shapes if shape_id not in knight_valid_set]
    removed_count = original_count - len(filtered_shapes)

    # Tally remaining shapes by size (assuming shape IDs start with or contain the size prefix, e.g., "09-..." or "9_...")
    # Alternatively, extract size from the first two characters of the shape ID if formatted as "09..."
    sizes = range(9, 15)
    size_counts = {size: 0 for size in sizes}

    for shape_id in filtered_shapes:
        # Check if the shape ID starts with a two-digit size string (e.g., "09", "10", etc.)
        prefix = shape_id[:2]
        if prefix.isdigit():
            s_val = int(prefix)
            if s_val in size_counts:
                size_counts[s_val] += 1

    # Update data structure
    piece_data["validShapes"] = filtered_shapes

    # Save cleaned list back to the piece JSON file
    try:
        with open(piece_json_path, 'w', encoding='utf-8') as f:
            json.dump(piece_data, f, indent=2)

        print("\n" + "═" * 45)
        print(f" FILTER COMPLETE FOR: {piece_name.upper()}")
        print("═" * 45)
        print(f"  Removed (Knight duplicates): {removed_count}")
        print("─" * 45)
        print("  REMAINING UNIQUE SHAPES BY SIZE:")
        for size in sizes:
            print(f"    Size {size:02d}-omino: {size_counts[size]} shapes")
        print("─" * 45)
        print(f"  Total Remaining Shapes:      {len(filtered_shapes)}")
        print("═" * 45)
        print(f"  Successfully updated: {piece_json_path}")
    except Exception as e:
        print(f"  Error saving {piece_json_path}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()