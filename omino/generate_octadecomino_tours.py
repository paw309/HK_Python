"""
Script to construct 18-square polyominoes (octadecominoes) that support knight's tours
by joining two 8-square knight's-tour-supporting polyominoes (nonominoes).

This script implements:
1. Combinatorial pairing with all rotations and reflections
2. Placement criteria validation (knight's move, orthogonal connectivity, bounds)
3. Tour validity checking (Hamiltonian path)
4. Canonicalization for uniqueness
5. Separate tracking of closed tours (cycles)
"""

from tours_nonomino import NONOMINO_TOURS
from typing import List, Tuple, Set, Dict
import itertools

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


def rotate_90(path: Path) -> Path:
    """Rotate path 90 degrees clockwise."""
    return [(y, -x) for x, y in path]


def reflect_horizontal(path: Path) -> Path:
    """Reflect path horizontally."""
    return [(-x, y) for x, y in path]


def reflect_vertical(path: Path) -> Path:
    """Reflect path vertically."""
    return [(x, -y) for x, y in path]


def get_all_orientations(path: Path) -> List[Path]:
    """
    Generate all 8 possible orientations of a path:
    - 4 rotations (0°, 90°, 180°, 270°)
    - 2 reflections (horizontal, vertical) for each rotation

    Returns normalized versions of each orientation.
    """
    orientations = []

    # Original
    current = path
    for _ in range(4):
        # Add rotation
        orientations.append(normalize_path(current))
        # Add horizontal reflection of rotation
        orientations.append(normalize_path(reflect_horizontal(current)))
        # Rotate for next iteration
        current = rotate_90(current)

    return orientations


def is_knight_move(coord1: Coord, coord2: Coord) -> bool:
    """Check if two coordinates are one knight's move apart."""
    dx = abs(coord1[0] - coord2[0])
    dy = abs(coord1[1] - coord2[1])
    return (dx == 1 and dy == 2) or (dx == 2 and dy == 1)


def are_orthogonally_adjacent(coord1: Coord, coord2: Coord) -> bool:
    """Check if two coordinates are orthogonally adjacent (edge-to-edge)."""
    dx = abs(coord1[0] - coord2[0])
    dy = abs(coord1[1] - coord2[1])
    return (dx == 1 and dy == 0) or (dx == 0 and dy == 1)


def has_orthogonal_connection(path1: Path, path2: Path) -> bool:
    """
    Check if at least one cell from path1 is orthogonally connected
    to at least one cell from path2.
    """
    for coord1 in path1:
        for coord2 in path2:
            if are_orthogonally_adjacent(coord1, coord2):
                return True
    return False


def is_contiguous(path: Path) -> bool:
    """
    Check if a polyomino is contiguous (all cells are connected).
    Uses BFS to verify all cells can be reached from the first cell.
    """
    if not path:
        return True

    coords_set = set(path)
    visited = set()
    queue = [path[0]]
    visited.add(path[0])

    while queue:
        current = queue.pop(0)
        x, y = current

        # Check all 4 orthogonal neighbors
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            neighbor = (x + dx, y + dy)
            if neighbor in coords_set and neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return len(visited) == len(path)


def is_valid_knight_tour(path: Path) -> bool:
    """
    Validate that a path is a valid knight's tour:
    - Each square is visited exactly once
    - All consecutive moves are legal knight's moves
    """
    if not path:
        return False

    # Check for unique coordinates
    if len(path) != len(set(path)):
        return False

    # Check all consecutive moves are knight's moves
    for i in range(len(path) - 1):
        if not is_knight_move(path[i], path[i + 1]):
            return False

    return True


def is_closed_tour(path: Path) -> bool:
    """
    Check if a tour is closed (the last square can reach the first with a knight's move).
    """
    if len(path) < 3:
        return False
    return is_knight_move(path[-1], path[0])


def translate_path(path: Path, offset: Coord) -> Path:
    """Translate a path by a given offset."""
    dx, dy = offset
    return [(x + dx, y + dy) for x, y in path]


def combine_paths(path1: Path, path2: Path, connection_type: str) -> Path:
    """
    Combine two paths based on connection type:
    - 'start-start': path2 reversed + path1
    - 'start-end': path2 + path1
    - 'end-start': path1 + path2
    - 'end-end': path1 + path2 reversed
    """
    if connection_type == 'start-start':
        return list(reversed(path2)) + path1
    elif connection_type == 'start-end':
        return path2 + path1
    elif connection_type == 'end-start':
        return path1 + path2
    elif connection_type == 'end-end':
        return path1 + list(reversed(path2))
    else:
        raise ValueError(f"Invalid connection type: {connection_type}")


def canonicalize_path(path: Path) -> Tuple[Path, str]:
    """
    Generate the canonical form of a path by:
    1. Generating all symmetries (rotations and reflections)
    2. Normalizing each to start at (0, 0)
    3. Selecting the lexicographically minimal one

    Returns the canonical path and its unique key.
    """
    if not path:
        return [], ""

    all_symmetries = []

    # Generate all 8 orientations
    current = path
    for _ in range(4):
        # Add rotation
        all_symmetries.append(normalize_path(current))
        # Add horizontal reflection
        all_symmetries.append(normalize_path(reflect_horizontal(current)))
        # Rotate for next iteration
        current = rotate_90(current)

    # Also try starting from different positions (for closed tours)
    if is_closed_tour(path):
        for start_idx in range(len(path)):
            rotated_path = path[start_idx:] + path[:start_idx]
            current = rotated_path
            for _ in range(4):
                all_symmetries.append(normalize_path(current))
                all_symmetries.append(normalize_path(reflect_horizontal(current)))
                current = rotate_90(current)

    # Find lexicographically minimal
    canonical = min(all_symmetries)

    # Generate unique key
    key = f"{len(canonical)}-" + "-".join(f"{x}{y}" for x, y in canonical)

    return canonical, key


def find_valid_placements(path1: Path, path2: Path) -> List[Tuple[Path, str]]:
    """
    Find all valid placements where path2 can be positioned relative to path1.

    For each connection type, we translate path2 to all possible positions where
    the connecting endpoint would be a knight's move from path1's endpoint.

    Returns list of (combined_path, connection_type) tuples.
    """
    valid_placements = []

    # All possible knight's moves (dx, dy)
    knight_moves = [
        (1, 2), (2, 1), (2, -1), (1, -2),
        (-1, -2), (-2, -1), (-2, 1), (-1, 2)
    ]

    connection_configs = [
        ('start-start', path1[0], path2[0]),  # Connect start of path1 to start of path2
        ('start-end', path1[0], path2[-1]),  # Connect start of path1 to end of path2
        ('end-start', path1[-1], path2[0]),  # Connect end of path1 to start of path2
        ('end-end', path1[-1], path2[-1])  # Connect end of path1 to end of path2
    ]

    for conn_type, ep1_path1, ep2_path2 in connection_configs:
        # Try placing path2 at each knight's move position from ep1
        for dx, dy in knight_moves:
            # Calculate where ep2 of path2 should be positioned
            target_pos = (ep1_path1[0] + dx, ep1_path1[1] + dy)

            # Calculate offset needed to move ep2_path2 to target_pos
            offset = (target_pos[0] - ep2_path2[0], target_pos[1] - ep2_path2[1])

            # Translate entire path2
            translated_path2 = translate_path(path2, offset)

            # Verify the endpoint is now at the right position
            if conn_type.endswith('-start'):
                check_ep = translated_path2[0]
            else:  # ends with '-end'
                check_ep = translated_path2[-1]

            if check_ep != target_pos:
                continue

            # Check for overlapping coordinates
            set1 = set(path1)
            set2 = set(translated_path2)
            if set1 & set2:  # Intersection is not empty
                continue

            # Check orthogonal connectivity (at least one edge-to-edge connection)
            if not has_orthogonal_connection(path1, translated_path2):
                continue

            # Combine the paths
            combined = combine_paths(path1, translated_path2, conn_type)

            # Check contiguity
            if not is_contiguous(combined):
                continue

            # Check tour validity
            if not is_valid_knight_tour(combined):
                continue

            valid_placements.append((combined, conn_type))

    return valid_placements


def generate_octadecomino_tours(nonomino_tours: Dict[str, Path],
                                max_results: int = None) -> Tuple[Dict[str, Path], Dict[str, Path]]:
    """
    Generate all unique octadecomino tours by combining pairs of nonomino tours.

    Returns:
        (all_tours, closed_tours) - Two dictionaries of unique tours
    """
    all_unique_tours = {}
    closed_unique_tours = {}
    seen_keys = set()

    nonomino_keys = list(nonomino_tours.keys())
    total_pairs = len(nonomino_keys) * len(nonomino_keys)
    processed = 0

    print(f"Processing {total_pairs} pairs of nonominoes...")

    # Try all pairs (including same nonomino with itself in different orientations)
    for key1 in nonomino_keys:
        path1_original = nonomino_tours[key1]

        for key2 in nonomino_keys:
            path2_original = nonomino_tours[key2]

            processed += 1
            if processed % 10 == 0:
                print(f"  Processed {processed}/{total_pairs} pairs, found {len(all_unique_tours)} unique tours")

            # Try all orientations of both paths
            orientations1 = get_all_orientations(path1_original)
            orientations2 = get_all_orientations(path2_original)

            for path1 in orientations1:
                for path2 in orientations2:
                    # Find valid placements
                    placements = find_valid_placements(path1, path2)

                    for combined_path, conn_type in placements:
                        # Canonicalize
                        canonical, key = canonicalize_path(combined_path)

                        # Check if we've seen this before
                        if key in seen_keys:
                            continue

                        seen_keys.add(key)

                        # Generate a simple numeric key
                        tour_id = f"18-{len(all_unique_tours):05d}"
                        all_unique_tours[tour_id] = canonical

                        # Check if it's a closed tour
                        if is_closed_tour(canonical):
                            closed_unique_tours[tour_id] = canonical

                        if max_results and len(all_unique_tours) >= max_results:
                            print(f"Reached maximum of {max_results} results")
                            return all_unique_tours, closed_unique_tours

    print(f"\nCompleted! Found {len(all_unique_tours)} unique tours")
    print(f"  {len(closed_unique_tours)} are closed tours (cycles)")

    return all_unique_tours, closed_unique_tours


def write_tours_file(tours: Dict[str, Path], filename: str, var_name: str):
    """Write tours to a Python file in the same format as tours_nonomino.py"""
    with open(filename, 'w') as f:
        f.write(f'{var_name} = {{\n')

        for key, path in sorted(tours.items()):
            path_str = ', '.join(f'({x}, {y})' for x, y in path)
            f.write(f'    "{key}": [{path_str}],\n')

        f.write('}\n')

    print(f"Wrote {len(tours)} tours to {filename}")


def main():
    """Main function to generate octadecomino tours."""
    import os

    print("=" * 80)
    print("Octadecomino Tour Generator")
    print("Constructing 18-square polyominoes from nonomino pairs")
    print("=" * 80)
    print()

    # Load nonomino tours
    print(f"Loaded {len(NONOMINO_TOURS)} nonomino tours")
    print()

    # Generate octadecomino tours
    # Set max_results to limit output during development/z_testing
    # Remove or set to None for full generation
    all_tours, closed_tours = generate_octadecomino_tours(
        NONOMINO_TOURS,
        max_results=None  # Set to e.g., 100 for z_testing, None for full run
    )

    # Write output files
    output_dir = os.path.dirname(os.path.abspath(__file__))

    all_tours_file = os.path.join(output_dir, "generated_octadecomino_tours.py")
    closed_tours_file = os.path.join(output_dir, "generated_octadecomino_closed_tours.py")

    write_tours_file(all_tours, all_tours_file, "OCTADECOMINO_TOURS")
    write_tours_file(closed_tours, closed_tours_file, "OCTADECOMINO_CLOSED_TOURS")

    print()
    print("=" * 80)
    print("Generation complete!")
    print(f"Total unique tours: {len(all_tours)}")
    print(f"Closed tours: {len(closed_tours)}")
    print("=" * 80)


if __name__ == "__main__":
    main()