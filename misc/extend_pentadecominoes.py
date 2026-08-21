"""
Script to extend 15-square polyominoes (pentadecominoes) to 16-square polyominoes (hexadecominoes).

For each pentadecomino tour, this script:
1. Tries adding a single square at each position that is a knight's move from
   either the first square (index 0) or last square (index 14)
2. Validates that the new square:
   - Does not overlap an existing square
   - Is orthogonally connected to at least one existing square
3. Writes valid hexadecominoes to an output file in wide table parquet format

The output is a parquet file where each row represents one hexadecomino tour.
Columns: tour_key, x0, y0, x1, y1, ..., x15, y15
"""

import sys
import os
import pandas as pd

# Script directory setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)

from typing import List, Tuple, Set, Dict
from tours_pentadecomino import PENTADECOMINO_TOURS

# Type aliases
Coord = Tuple[int, int]
Path = List[Coord]


def normalize_path(path: Path) -> Path:
    """
    Normalize a path by shifting it so the minimum x and y coordinates are 0.
    """
    if not path:
        return []

    min_x = min(coord[0] for coord in path)
    min_y = min(coord[1] for coord in path)

    return [(x - min_x, y - min_y) for x, y in path]


def get_knight_moves(coord: Coord) -> List[Coord]:
    """
    Get all possible knight's moves from a given coordinate.
    """
    x, y = coord
    moves = [
        (x + 1, y + 2), (x + 1, y - 2),
        (x - 1, y + 2), (x - 1, y - 2),
        (x + 2, y + 1), (x + 2, y - 1),
        (x - 2, y + 1), (x - 2, y - 1)
    ]
    return moves


def are_orthogonally_adjacent(coord1: Coord, coord2: Coord) -> bool:
    """Check if two coordinates are orthogonally adjacent (edge-to-edge)."""
    dx = abs(coord1[0] - coord2[0])
    dy = abs(coord1[1] - coord2[1])
    return (dx == 1 and dy == 0) or (dx == 0 and dy == 1)


def has_orthogonal_connection(new_coord: Coord, path: Path) -> bool:
    """
    Check if the new coordinate is orthogonally connected to at least one
    coordinate in the path.
    """
    for coord in path:
        if are_orthogonally_adjacent(new_coord, coord):
            return True
    return False


def extend_tour(tour: Path) -> List[Path]:
    """
    Extend a 15-square tour to 16-square tours by adding one square.

    The new square must be:
    1. A knight's move from either the first square or the last square
    2. Not overlapping an existing square
    3. Orthogonally connected to at least one existing square

    Returns a list of valid 16-square tours.
    """
    extended_tours = []
    tour_set = set(tour)

    # Get first and last squares
    first_square = tour[0]
    last_square = tour[14]  # Index 14 for 15-square tour

    # Try knight's moves from the first square
    for new_coord in get_knight_moves(first_square):
        # Check if not overlapping
        if new_coord in tour_set:
            continue

        # Check if orthogonally connected to at least one existing square
        if not has_orthogonal_connection(new_coord, tour):
            continue

        # Create new tour by inserting at the beginning
        new_tour = [new_coord] + tour
        extended_tours.append(new_tour)

    # Try knight's moves from the last square
    for new_coord in get_knight_moves(last_square):
        # Check if not overlapping
        if new_coord in tour_set:
            continue

        # Check if orthogonally connected to at least one existing square
        if not has_orthogonal_connection(new_coord, tour):
            continue

        # Create new tour by appending at the end
        new_tour = tour + [new_coord]
        extended_tours.append(new_tour)

    return extended_tours


def main():
    """Main function to extend pentadecomino tours to hexadecomino tours."""
    print("=" * 80)
    print("Pentadecomino to Hexadecomino Extension")
    print("Extending 15-square tours to 16-square tours")
    print("=" * 80)
    print()

    # Load pentadecomino tours
    pentadecomino_tours = PENTADECOMINO_TOURS
    print(f"Loaded {len(pentadecomino_tours)} pentadecomino tours")
    print()

    # List to store all generated hexadecomino data for DataFrame
    hexadecomino_data = []
    tour_count = 0

    # Process each pentadecomino tour
    for pent_key, pent_tour in pentadecomino_tours.items():
        # Extend the tour
        extended = extend_tour(pent_tour)

        # Add each extended tour to our collection
        for ext_tour in extended:
            # Normalize the tour
            normalized = normalize_path(ext_tour)

            # Generate a key
            hex_key = f"16-{tour_count:05d}"

            # Convert path to wide format: flatten coordinates into columns
            # For 16-square tour: x0, y0, x1, y1, ..., x15, y15
            row_data = {'tour_key': hex_key}
            for i, (x, y) in enumerate(normalized):
                row_data[f'x{i}'] = x
                row_data[f'y{i}'] = y

            hexadecomino_data.append(row_data)
            tour_count += 1

            # Display progress every 100 tours
            if tour_count % 100 == 0:
                print(f"Generated {tour_count} hexadecominoes...")

    print()
    print(f"Total hexadecominoes generated: {tour_count}")
    print()

    # Create DataFrame in wide table format
    df = pd.DataFrame(hexadecomino_data)

    # Ensure columns are in proper order: tour_key, x0, y0, x1, y1, ..., x15, y15
    coord_columns = []
    for i in range(16):
        coord_columns.extend([f'x{i}', f'y{i}'])
    df = df[['tour_key'] + coord_columns]

    # Write to parquet file
    output_file = os.path.join(SCRIPT_DIR, "tours_hexadecomino.parquet")
    df.to_parquet(output_file, index=False)

    print(f"Wrote {tour_count} hexadecominoes to {output_file}")
    print(f"Output format: wide table parquet with columns: tour_key, x0, y0, x1, y1, ..., x15, y15")
    print()
    print("=" * 80)
    print("Extension complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()