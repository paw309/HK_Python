"""
tour_combiner.py

Utility for combining two smaller knight's tour polyominoes into a larger one.
Used to generate larger polyominoes (hexadecomino through icosomino) on-the-fly.

Constraints:
1. Size: The two shapes must sum to the desired target size
2. Knight connectivity: First or last square of second tour must be within one knight's move
   of the first or last square of the first tour
3. No overlap: The two shapes cannot have any overlapping squares
4. Orthogonal continuity: At least one square of the second tour must be orthogonally
   adjacent to at least one square of the first tour
5. Coordinate bounds: No coordinate value can exceed 8
"""

from typing import List, Tuple, Set, Optional
import random

# Type aliases
Coord = Tuple[int, int]
Path = List[Coord]

# Knight moves (8 possible L-shaped moves)
KNIGHT_MOVES = [
    (-2, -1), (-2, 1), (-1, -2), (-1, 2),
    (1, -2), (1, 2), (2, -1), (2, 1)
]


def normalize_path(path: Path) -> Path:
    """
    Normalize a path by shifting it so the minimum x and y coordinates are 0.
    """
    if not path:
        return []

    min_x = min(coord[0] for coord in path)
    min_y = min(coord[1] for coord in path)

    return [(x - min_x, y - min_y) for x, y in path]


def are_orthogonally_adjacent(coord1: Coord, coord2: Coord) -> bool:
    """Check if two coordinates are orthogonally adjacent (edge-to-edge)."""
    dx = abs(coord1[0] - coord2[0])
    dy = abs(coord1[1] - coord2[1])
    return (dx == 1 and dy == 0) or (dx == 0 and dy == 1)


def has_orthogonal_connection(path1: Path, path2: Path) -> bool:
    """
    Check if at least one square from path2 is orthogonally adjacent to
    at least one square from path1.
    """
    for coord1 in path1:
        for coord2 in path2:
            if are_orthogonally_adjacent(coord1, coord2):
                return True
    return False


def is_knight_move(coord1: Coord, coord2: Coord) -> bool:
    """Check if moving from coord1 to coord2 is a valid knight's move."""
    dx = coord2[0] - coord1[0]
    dy = coord2[1] - coord1[1]
    return (dx, dy) in KNIGHT_MOVES


def has_knight_connectivity(path1: Path, path2: Path) -> Tuple[bool, Optional[str]]:
    """
    Check if the first or last square of path2 is within one knight's move
    of the first or last square of path1.

    Returns: (is_connected, connection_type)
    connection_type is one of: "first-first", "first-last", "last-first", "last-last", or None
    """
    if not path1 or not path2:
        return False, None

    first1, last1 = path1[0], path1[-1]
    first2, last2 = path2[0], path2[-1]

    # Check all four possible connections
    if is_knight_move(first1, first2):
        return True, "first-first"
    if is_knight_move(first1, last2):
        return True, "first-last"
    if is_knight_move(last1, first2):
        return True, "last-first"
    if is_knight_move(last1, last2):
        return True, "last-last"

    return False, None


def has_overlap(path1: Path, path2: Path) -> bool:
    """Check if the two paths have any overlapping coordinates."""
    set1 = set(path1)
    set2 = set(path2)
    return len(set1 & set2) > 0


def max_coordinate_value(path: Path) -> int:
    """
    Get the maximum coordinate value (x or y) in the path.
    Uses abs() to handle both positive and negative coordinates before normalization.
    """
    if not path:
        return 0
    return max(max(abs(x), abs(y)) for x, y in path)


def validate_coordinate_bounds(path: Path, max_value: int = 8) -> bool:
    """Check if all coordinate values are within the allowed bounds."""
    return max_coordinate_value(path) <= max_value


def offset_path(path: Path, offset: Coord) -> Path:
    """Offset all coordinates in a path by the given offset."""
    dx, dy = offset
    return [(x + dx, y + dy) for x, y in path]


def try_combine_tours(
    tour1: Path,
    tour2: Path,
    max_attempts: int = 100,
    seed: Optional[int] = None,
) -> Optional[Path]:
    """
    Try to combine two tours into a single contiguous shape that satisfies all constraints.

    The function tries different offsets for tour2 relative to tour1 to find a valid combination.

    Args:
        tour1: First tour path
        tour2: Second tour path
        max_attempts: Maximum number of random offsets to try
        seed: Optional RNG seed.  When provided the random offsets are
              generated deterministically, so the same (tour1, tour2, seed)
              triple always produces the same result.

    Returns:
        Combined tour path if successful, None otherwise
    """
    rng = random.Random(seed)

    # Normalize tour1 to start at origin
    tour1_norm = normalize_path(tour1)

    # Try various strategic offsets for tour2
    offsets_to_try = []

    # Get first and last coordinates of tour1
    first1 = tour1_norm[0]
    last1 = tour1_norm[-1]

    # For each endpoint of tour1, calculate offsets that would place
    # tour2's endpoints at knight's move distances
    for anchor1 in [first1, last1]:
        for km in KNIGHT_MOVES:
            for anchor2_idx in [0, -1]:  # first or last of tour2
                # Calculate offset that would place tour2's anchor at knight's move from tour1's anchor
                anchor2 = tour2[anchor2_idx]
                target = (anchor1[0] + km[0], anchor1[1] + km[1])
                offset = (target[0] - anchor2[0], target[1] - anchor2[1])
                offsets_to_try.append(offset)

    # Also try some random offsets (deterministic when seed is provided)
    for _ in range(max_attempts // 2):
        offset = (rng.randint(-5, 5), rng.randint(-5, 5))
        offsets_to_try.append(offset)

    # Try each offset
    for offset in offsets_to_try:
        tour2_offset = offset_path(tour2, offset)

        # Check all constraints
        if has_overlap(tour1_norm, tour2_offset):
            continue

        is_connected, conn_type = has_knight_connectivity(tour1_norm, tour2_offset)
        if not is_connected:
            continue

        if not has_orthogonal_connection(tour1_norm, tour2_offset):
            continue

        # Combine the tours based on connection type
        if conn_type == "last-first":
            # tour1 ... -> tour2 ...
            combined = tour1_norm + tour2_offset
        elif conn_type == "last-last":
            # tour1 ... -> ... tour2 (reversed)
            combined = tour1_norm + tour2_offset[::-1]
        elif conn_type == "first-first":
            # ... tour1 (reversed) <- tour2 ...
            combined = tour1_norm[::-1] + tour2_offset
        elif conn_type == "first-last":
            # ... tour2 -> tour1 ...
            combined = tour2_offset + tour1_norm
        else:
            combined = tour1_norm + tour2_offset

        # Normalize the combined path
        combined_norm = normalize_path(combined)

        # Check coordinate bounds
        if not validate_coordinate_bounds(combined_norm):
            continue

        return combined_norm

    return None


def combine_tours(
    tour1: Path,
    tour2: Path,
    target_size: int,
    max_attempts: int = 100,
    seed: Optional[int] = None,
) -> Optional[Path]:
    """
    Combine two tours into a single tour of the target size.

    Args:
        tour1: First tour path
        tour2: Second tour path
        target_size: Desired total size (must equal len(tour1) + len(tour2))
        max_attempts: Maximum number of attempts to find a valid combination
        seed: Optional RNG seed for deterministic combination.

    Returns:
        Combined tour path if successful, None otherwise
    """
    # Validate sizes
    if len(tour1) + len(tour2) != target_size:
        return None

    # Try to combine
    result = try_combine_tours(tour1, tour2, max_attempts, seed=seed)

    # Verify result
    if result and len(result) == target_size:
        return result

    return None