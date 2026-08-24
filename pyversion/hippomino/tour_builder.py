"""
tour_builder.py

On-the-fly builder for large polyomino tours (hexadecomino through icosomino: 16-20 squares).
Combines smaller tours from existing dictionaries to create larger tours dynamically.

This module provides an interface compatible with the static tour dictionaries,
but generates tours on demand by combining smaller shapes.
"""

from typing import List, Tuple, Dict, Optional
import random

from pyversion.hippomino.tour_combiner import combine_tours
from pyversion.hippomino.megalomino_codec import encode as codec_encode, derive_seed as codec_derive_seed

# Import existing tour dictionaries for smaller shapes (7-15 squares)
from pyversion.tourbus.megalotours.tours_heptomino import HEPTOMINO_TOURS
from pyversion.tourbus.megalotours.tours_octomino import OCTOMINO_TOURS
from pyversion.tourbus.megalotours.tours_nonomino import NONOMINO_TOURS
from pyversion.tourbus.megalotours.tours_decomino import DECOMINO_TOURS
from pyversion.tourbus.megalotours.tours_undecomino import UNDECOMINO_TOURS
from pyversion.tourbus.megalotours.tours_dodecomino import DODECOMINO_TOURS
from pyversion.tourbus.megalotours.tours_tridecomino import TRIDECOMINO_TOURS
from pyversion.tourbus.megalotours.tours_tetradecomino import TETRADECOMINO_TOURS
from pyversion.tourbus.megalotours.tours_pentadecomino import PENTADECOMINO_TOURS

# Type aliases
Coord = Tuple[int, int]
Path = List[Coord]

# Map size to available tours
SIZE_TO_TOURS = {
    7: HEPTOMINO_TOURS,
    8: OCTOMINO_TOURS,
    9: NONOMINO_TOURS,
    10: DECOMINO_TOURS,
    11: UNDECOMINO_TOURS,
    12: DODECOMINO_TOURS,
    13: TRIDECOMINO_TOURS,
    14: TETRADECOMINO_TOURS,
    15: PENTADECOMINO_TOURS,
}

# Cache for generated tours
_TOUR_CACHE: Dict[str, Path] = {}


def get_size_combinations(target_size: int) -> List[Tuple[int, int]]:
    """
    Get all possible combinations of two sizes that sum to the target size.
    Returns pairs (size1, size2) where both sizes have available tours.
    """
    combinations = []
    for size1 in range(7, 16):  # Sizes 7-15
        size2 = target_size - size1
        if size2 >= 7 and size2 <= 15 and size1 in SIZE_TO_TOURS and size2 in SIZE_TO_TOURS:
            combinations.append((size1, size2))
    return combinations


def generate_tour_id(tour1_id: str, tour2_id: str) -> str:
    """
    Generate a reproducible codec ID for a combined tour.

    The result is a string like ``"16-ABCD-EFGH"`` derived from the two
    component shape IDs via :func:`megalomino_codec.encode`.
    """
    return codec_encode(tour1_id, tour2_id)


def build_tour(target_size: int, max_attempts: int = 50) -> Optional[Tuple[str, Path]]:
    """
    Build a tour of the target size by combining two smaller tours.

    Args:
        target_size: Desired tour size (16-20)
        max_attempts: Maximum number of attempts to find a valid combination

    Returns:
        Tuple of (codec_id, tour_path) where *codec_id* is a human-readable
        code like ``"16-ABCD-EFGH"`` derived from the two component shape IDs.
        Returns None if no valid combination is found.
    """
    if target_size < 16 or target_size > 20:
        return None

    # Get possible size combinations
    combinations = get_size_combinations(target_size)
    if not combinations:
        return None

    # Shuffle combinations to add variety
    random.shuffle(combinations)

    # Try each combination
    for size1, size2 in combinations:
        tours1 = SIZE_TO_TOURS[size1]
        tours2 = SIZE_TO_TOURS[size2]

        # Randomly select tours from each size
        for _ in range(max_attempts // max(1, len(combinations)) + 1):
            tour1_id = random.choice(list(tours1.keys()))
            tour2_id = random.choice(list(tours2.keys()))

            tour1 = tours1[tour1_id]
            tour2 = tours2[tour2_id]

            # Try to combine them
            combined = combine_tours(tour1, tour2, target_size)

            if combined:
                tour_id = generate_tour_id(tour1_id, tour2_id)
                return tour_id, combined

    return None


def build_tour_from_ids(id_a: str, id_b: str) -> Optional[Path]:
    """
    Reconstruct a large polyomino tour deterministically from two component
    shape IDs.

    The combination is seeded with a value derived from *id_a* and *id_b* so
    that the same pair always produces the same tour, making the result fully
    reproducible from the codec string.

    Args:
        id_a: First component shape ID, e.g. ``"09-00123"``.
        id_b: Second component shape ID, e.g. ``"07-00456"``.

    Returns:
        The combined tour path, or None if no valid combination could be found.
    """
    try:
        size_a = int(id_a.split("-")[0])
        size_b = int(id_b.split("-")[0])
    except (ValueError, IndexError):
        return None

    tours_a = SIZE_TO_TOURS.get(size_a)
    tours_b = SIZE_TO_TOURS.get(size_b)
    if tours_a is None or tours_b is None:
        return None

    tour_a = tours_a.get(id_a)
    tour_b = tours_b.get(id_b)
    if tour_a is None or tour_b is None:
        return None

    target_size = size_a + size_b
    seed = codec_derive_seed(id_a, id_b)
    return combine_tours(tour_a, tour_b, target_size, seed=seed)


def build_tour_set(target_size: int, count: int = 10) -> Dict[str, Path]:
    """
    Build a set of tours of the target size.

    Args:
        target_size: Desired tour size
        count: Number of tours to generate

    Returns:
        Dictionary mapping tour IDs to tour paths
    """
    tours = {}
    attempts = 0
    max_total_attempts = count * 100

    while len(tours) < count and attempts < max_total_attempts:
        attempts += 1
        result = build_tour(target_size)
        if result:
            tour_id, path = result
            # Use normalized path as key to avoid duplicates
            path_key = tuple(path)
            if path_key not in [tuple(p) for p in tours.values()]:
                tours[tour_id] = path

    return tours


class DynamicTourProvider:
    """
    Provides tours dynamically, generating them on-the-fly when requested.
    Compatible with the static tour dictionary interface.
    """

    def __init__(self, target_size: int, cache_size: int = 50):
        """
        Initialize the dynamic tour provider.

        Args:
            target_size: Size of tours to provide
            cache_size: Maximum number of tours to keep in cache
        """
        self.target_size = target_size
        self.cache_size = cache_size
        self._cache: Dict[str, Path] = {}
        self._cache_order: List[str] = []

    def get_random_tour(self) -> Optional[Tuple[str, Path]]:
        """Get a random tour, generating it if necessary."""
        # 30% chance to return from cache if available
        if self._cache and random.random() < 0.3:
            tour_id = random.choice(list(self._cache.keys()))
            return tour_id, self._cache[tour_id]

        # Generate new tour
        result = build_tour(self.target_size)
        if result:
            tour_id, path = result
            self._add_to_cache(tour_id, path)
            return tour_id, path

        # Fallback to cache if generation failed
        if self._cache:
            tour_id = random.choice(list(self._cache.keys()))
            return tour_id, self._cache[tour_id]

        return None

    def _add_to_cache(self, tour_id: str, path: Path):
        """Add a tour to the cache, removing oldest if necessary."""
        if tour_id not in self._cache:
            self._cache[tour_id] = path
            self._cache_order.append(tour_id)

            # Remove oldest if cache is full
            if len(self._cache) > self.cache_size:
                oldest = self._cache_order.pop(0)
                del self._cache[oldest]

    def get_available_tour_ids(self) -> List[str]:
        """Get list of currently cached tour IDs."""
        return list(self._cache.keys())


# Create providers for each large size
HEXADECOMINO_PROVIDER = DynamicTourProvider(16)
HEPTADECOMINO_PROVIDER = DynamicTourProvider(17)
OCTADECOMINO_PROVIDER = DynamicTourProvider(18)
NONADECOMINO_PROVIDER = DynamicTourProvider(19)
ICOSOMINO_PROVIDER = DynamicTourProvider(20)

# Map sizes to providers
SIZE_TO_PROVIDER = {
    16: HEXADECOMINO_PROVIDER,
    17: HEPTADECOMINO_PROVIDER,
    18: OCTADECOMINO_PROVIDER,
    19: NONADECOMINO_PROVIDER,
    20: ICOSOMINO_PROVIDER,
}