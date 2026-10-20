import os
import json
import sys


def find_shape_and_size(shape_id, data_dir):
    """
    Search xx-omino.json files in data_dir to find coordinates for shape_id.
    """
    sizes = range(1, 20)  # Scan common polyomino size range

    for size in sizes:
        filename = os.path.join(data_dir, f"{size:02d}-omino.json")
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    shapes_data = json.load(f)
                    if shape_id in shapes_data:
                        return shapes_data[shape_id]
            except Exception as e:
                print(f"Error reading {filename}: {e}")
    return None


def generate_svg(coords, cell_size=40, padding=20):
    """
    Generates an SVG string representation of the polyomino coordinates
    using alternating light and dark square colors based on cell parity (row + col % 2).
    Transparent background.
    """
    if not coords:
        return ""

    min_r = min(cell[0] for cell in coords)
    max_r = max(cell[0] for cell in coords)
    min_c = min(cell[1] for cell in coords)
    max_c = max(cell[1] for cell in coords)

    num_rows = max_r - min_r + 1
    num_cols = max_c - min_c + 1

    svg_width = num_cols * cell_size + 2 * padding
    svg_height = num_rows * cell_size + 2 * padding

    # Style colors for parity
    light_square_color = "#f0d9b5"  # Light wood / classic board light
    dark_square_color = "#b58863"   # Dark wood / classic board dark
    border_color = "#333333"

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}">',
        f'  <g transform="translate({padding}, {padding})">'
    ]

    for r, c in coords:
        # Normalize coordinates so bounding box starts at (0, 0)
        norm_r = r - min_r
        norm_c = c - min_c

        x = norm_c * cell_size
        y = norm_r * cell_size

        # Determine fill color based on board parity
        fill_color = light_square_color if (r + c) % 2 == 0 else dark_square_color

        svg_lines.append(
            f'    <rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" '
            f'fill="{fill_color}" stroke="{border_color}" stroke-width="1.5" rx="2" ry="2" />'
        )

    svg_lines.append('  </g>')
    svg_lines.append('</svg>')

    return "\n".join(svg_lines)


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "hipcheck")

    if len(sys.argv) > 1:
        shape_id = sys.argv[1].strip()
    else:
        shape_id = input("Enter shape ID (e.g. 10-0042): ").strip()

    if not shape_id:
        print("Error: No shape ID provided.")
        sys.exit(1)

    coords = find_shape_and_size(shape_id, data_dir)

    if not coords:
        print(f"Error: Shape ID '{shape_id}' not found in '{data_dir}'.")
        sys.exit(1)

    svg_content = generate_svg(coords)

    out_filename = f"{shape_id}.svg"
    out_path = os.path.join(base_dir, out_filename)

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)

    print(f"Successfully generated SVG for '{shape_id}' -> {out_path}")


if __name__ == "__main__":
    main()