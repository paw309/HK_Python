"""Find all polyominoes of a given size whose cells fit within 0 <= x < 4, 0 <= y < 4.

Polyomino data is sourced exclusively from tourbus/megalotours/.
"""

import importlib
import os
import sys

# Map polyomino size -> (module_name, variable_name, common_name)
SIZE_MAP = {
    7:  ("tourbus.megalotours.tours_heptomino",    "HEPTOMINO_TOURS",    "heptomino"),
    8:  ("tourbus.megalotours.tours_octomino",     "OCTOMINO_TOURS",     "octomino"),
    9:  ("tourbus.megalotours.tours_nonomino",     "NONOMINO_TOURS",     "nonomino"),
    10: ("tourbus.megalotours.tours_decomino",     "DECOMINO_TOURS",     "decomino"),
    11: ("tourbus.megalotours.tours_undecomino",   "UNDECOMINO_TOURS",   "undecomino"),
    12: ("tourbus.megalotours.tours_dodecomino",   "DODECOMINO_TOURS",   "dodecomino"),
    13: ("tourbus.megalotours.tours_tridecomino",  "TRIDECOMINO_TOURS",  "tridecomino"),
    14: ("tourbus.megalotours.tours_tetradecomino","TETRADECOMINO_TOURS","tetradecomino"),
    15: ("tourbus.megalotours.tours_pentadecomino","PENTADECOMINO_TOURS","pentadecomino"),
    16: ("tourbus.megalotours.tours_hexadecomino", "HEXADECOMINO_TOURS", "hexadecomino"),
    17: ("tourbus.megalotours.tours_heptadecomino","HEPTADECOMINO_TOURS","heptadecomino"),
    18: ("tourbus.megalotours.tours_octadecomino", "OCTADECOMINO_TOURS", "octadecomino"),
}

X_MAX = 3
Y_MAX = 6


def fits_in_grid(cells):
    """Return True if every cell (x, y) satisfies 0 <= x < 4 and 0 <= y < 4."""
    return all(0 <= x < X_MAX and 0 <= y < Y_MAX for x, y in cells)


def load_tours(size):
    """Import and return the tours dictionary for the given polyomino size."""
    module_name, var_name, _ = SIZE_MAP[size]
    module = importlib.import_module(module_name)
    return getattr(module, var_name)


def main():
    valid_sizes = sorted(SIZE_MAP.keys())
    size_list = ", ".join(
        f"{s} ({SIZE_MAP[s][2]})" for s in valid_sizes
    )
    print(f"Available sizes: {size_list}")

    while True:
        raw = input("Enter polyomino size to check: ").strip()
        try:
            size = int(raw)
        except ValueError:
            print("Please enter a whole number.")
            continue
        if size not in SIZE_MAP:
            print(f"Size {size} is not available. Choose from: {valid_sizes}")
            continue
        break

    _, _, name = SIZE_MAP[size]
    print(f"\nLoading {name} tours from tourbus/megalotours ...")
    tours = load_tours(size)

    matching = [
        poly_id
        for poly_id, cells in tours.items()
        if fits_in_grid(cells)
    ]

    total = len(tours)
    found = len(matching)

    print(f"\nTotal {name}s in library : {total}")
    print(f"Fit within 0<=x<4, 0<=y<4: {found}")

    if found:
        print("\nMatching polyomino IDs:")
        for poly_id in matching:
            print(f"  {poly_id}")
    else:
        print("\nNo polyominoes of this size fit within the 4x4 grid.")


if __name__ == "__main__":
    # Ensure the repo root is on the path so tourbus imports work.
    repo_root = os.path.dirname(os.path.abspath(__file__))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    main()