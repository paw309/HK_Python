"""
polyomino_difficulty.py

Challenge rating and difficulty calculations for the Polyominoes game.

Uses a simplified additive point-based system that is transparent and easy to tune.
Each category contributes a fixed number of difficulty points, which are summed and
scaled to a 1 to 5-star rating.

Point categories and their maximum contributions:
  - Piece difficulty   (0–5.0 pts): inverted mobility + agility ratings
  - Board size         (0.5–2.0 pts): small/large boards add difficulty
  - Shape complexity   (0–4.5 pts): more complex shapes = more points
  - Density            (0–1.5 pts): low and high density both add difficulty
  - Color scheme       (0–2.0 pts): same color = hardest; unique = easiest
  - Blind mode         (×1.2 modifier): applied when puzzle is hidden from player

Theoretical maximum: ~15.0 points → 5.0 stars.
"""

from typing import Any, Dict, Tuple

# ---------------------------------------------------------------------------
# Point lookup tables (module-level so both public functions share them)
# ---------------------------------------------------------------------------

# Shape complexity: larger polyominoes are harder to complete (0–4.5 pts)
_SHAPE_POINTS: Dict[str, float] = {
    "monomino": 0.0,
    "domino":   0.0,
    "triomino": 0.5,
    "tetromino": 1.0,
    "pentomino": 1.5,
    "hexomino":  3.5,
    "heptomino": 4.5,
    "octomino":  5.5,
    "mixed":     7.0,
}

# Density paradox: both extremes add difficulty for different reasons (0–1.5 pts)
_DENSITY_POINTS: Dict[str, float] = {
    "low":    1.0,   # shapes are hard to find
    "medium": 1.5,   # balanced
    "high":   2.0,   # routing conflicts; crowded board
}

# Color scheme: same color removes all visual grouping cues (0–2.0 pts)
_COLOR_POINTS: Dict[str, float] = {
    "unique": 0.0,   # clear visual grouping per shape class
    "random": 1.5,   # partial clues; can mislead
    "same":   2.5,   # no visual boundary cues at all
}

# Blind mode multiplier
_BLIND_MODIFIER = 1.2


def _compute_points(
    selections: Dict[str, Any],
    mobility_rating: int,
    agility_rating: int,
) -> Tuple[float, float, float, float, float]:
    """
    Compute raw difficulty points for each category.

    Returns:
        Tuple of (piece_points, size_points, shape_points, density_points, color_points).
    """
    board_size = int(selections.get("board", 8))
    shapes = selections.get("shapes", "pentomino")
    density = selections.get("density", "medium")
    colors = selections.get("colors", "unique")

    # a) Piece difficulty (0–5.0 pts): lower ratings = harder piece to play with
    piece_points = (5 - mobility_rating) * 0.5 + (5 - agility_rating) * 0.5

    # b) Board size (0.5–2.0 pts): extremes are harder
    if board_size <= 6:
        size_points = 1.5    # cramped; limited routing options
    elif board_size >= 14:
        size_points = 2.0    # overwhelming; hard to track the full board
    else:
        size_points = 0.5    # sweet spot

    # c–e) Lookup table values
    shape_points   = _SHAPE_POINTS.get(shapes, 1.0)
    density_points = _DENSITY_POINTS.get(density, 0.0)
    color_points   = _COLOR_POINTS.get(colors, 0.0)

    return piece_points, size_points, shape_points, density_points, color_points


def calculate_challenge_rating(
    selections: Dict[str, Any],
    mobility_rating: int,
    agility_rating: int,
    blind_mode: bool = False,
) -> float:
    """
    Return the challenge rating (1.0–5.0) for the given puzzle configuration.

    Points are summed across five independent categories and scaled to 1.0–5.0.
    An optional blind-mode modifier (×1.2) is applied after summing.

    Args:
        selections:      Dict with keys 'piece', 'board', 'shapes', 'density', 'colors'.
        mobility_rating: Piece mobility rating (0–5); higher = easier to navigate.
        agility_rating:  Piece agility rating (0–5); higher = easier to complete shapes.
        blind_mode:      True if the player cannot see the puzzle configuration.

    Returns:
        Float challenge rating rounded to one decimal, in [1.0, 5.0].
    """
    piece_points, size_points, shape_points, density_points, color_points = (
        _compute_points(selections, mobility_rating, agility_rating)
    )

    # Total points (theoretical max: 5.0 + 2.0 + 4.5 + 1.5 + 2.0 = 15.0)
    total_points = piece_points + size_points + shape_points + density_points + color_points

    # Blind mode modifier: unknown configuration feels ~20% harder
    if blind_mode:
        total_points *= _BLIND_MODIFIER

    # Scale to 1.0–5.0 range and clamp
    challenge_rating = 1.0 + (total_points / 15.0) * 4.0
    return round(max(1.0, min(5.0, challenge_rating)), 1)


def get_difficulty_breakdown(
    selections: Dict[str, Any],
    mobility_rating: int,
    agility_rating: int,
    blind_mode: bool = False,
) -> Dict[str, float]:
    """
    Return a per-category difficulty breakdown for UI display or debugging.

    Args:
        selections:      Dict with keys 'piece', 'board', 'shapes', 'density', 'colors'.
        mobility_rating: Piece mobility rating (0–5).
        agility_rating:  Piece agility rating (0–5).
        blind_mode:      True if the player cannot see the puzzle configuration.

    Returns:
        Dict with keys:
            piece_points     - difficulty from piece mobility + agility (0–5.0)
            size_points      - difficulty from board size (0.5–2.0)
            shape_points     - difficulty from shape complexity (0–4.5)
            density_points   - difficulty from piece density (0–1.5)
            color_points     - difficulty from color scheme (0–2.0)
            total_points     - sum of above five categories (before blind modifier)
            challenge_rating - final 1.0–5.0 rating (blind modifier applied if active)
            blind_modifier   - 1.2 if blind mode active, else 1.0
    """
    piece_points, size_points, shape_points, density_points, color_points = (
        _compute_points(selections, mobility_rating, agility_rating)
    )
    total_points = piece_points + size_points + shape_points + density_points + color_points

    challenge_rating = calculate_challenge_rating(
        selections, mobility_rating, agility_rating, blind_mode
    )

    return {
        "piece_points":      round(piece_points, 2),
        "size_points":       round(size_points, 2),
        "shape_points":      round(shape_points, 2),
        "density_points":    round(density_points, 2),
        "color_points":      round(color_points, 2),
        "total_points":      round(total_points, 2),
        "challenge_rating":  challenge_rating,
        "blind_modifier":    _BLIND_MODIFIER if blind_mode else 1.0,
    }