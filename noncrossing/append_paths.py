import json
import os
import re


def compact_json_arrays(json_str):
    """Collapses flat arrays (like coordinates and lists of numbers) onto a single line."""

    def clean_match(match):
        content = match.group(1)
        # If the array contains nested brackets or objects, leave it multi-line
        if '[' in content or '{' in content:
            return match.group(0)
        # Otherwise, collapse all internal newlines and excess whitespace
        flattened = re.sub(r'\s+', ' ', content).strip()
        # Clean up spacing around commas for neatness
        flattened = re.sub(r'\s*,\s*', ', ', flattened)
        return f"[{flattened}]"

    # Find all square bracket blocks and apply the flattening rule
    return re.sub(r'\[(.*?)\]', clean_match, json_str, flags=re.DOTALL)


def main():
    # Accept user input for the file name to be appended, with a default suggestion
    input_filename = input("Enter the filename containing the paths to append (default: knight_board_9.json): ").strip()
    if not input_filename:
        input_filename = "knight_board_9.json"

    paths_filename = "paths.json"

    # Check if input file exists
    if not os.path.exists(input_filename):
        print(f"Error: Input file '{input_filename}' not found.")
        return

    # Load input data
    with open(input_filename, 'r', encoding='utf-8') as f:
        try:
            input_data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from '{input_filename}': {e}")
            return

    # Load existing paths.json or initialize empty dictionary
    if os.path.exists(paths_filename):
        with open(paths_filename, 'r', encoding='utf-8') as f:
            try:
                paths_data = json.load(f)
            except json.JSONDecodeError:
                paths_data = {}
    else:
        paths_data = {}

    # Transform and merge input data into paths.json format
    for piece_name, boards in input_data.items():
        if piece_name not in paths_data:
            paths_data[piece_name] = {}

        for board_size, data in boards.items():
            if "known" in data:
                known_data = data["known"]
                transformed_entry = {
                    "status": "known",
                    "length": known_data.get("length"),
                    "starts": known_data.get("starts", {})
                }
                paths_data[piece_name][board_size] = transformed_entry
            else:
                paths_data[piece_name][board_size] = data

    # Generate standard indented JSON string
    raw_json = json.dumps(paths_data, indent=1)

    # Compact flat arrays (coordinates/lists) back to horizontal format
    formatted_json = compact_json_arrays(raw_json)

    # Write out the formatted string to paths.json
    with open(paths_filename, 'w', encoding='utf-8') as f:
        f.write(formatted_json)

    print(
        f"Successfully added paths from '{input_filename}' to '{paths_filename}' with horizontal coordinate formatting.")


if __name__ == "__main__":
    main()