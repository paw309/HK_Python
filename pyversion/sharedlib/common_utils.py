"""
common_utils.py

Common utility functions used across all Hamiltonian-Knights games.
"""


def clamp(n: float, a: float, b: float) -> float:
    """Clamp n between a and b."""
    return max(a, min(n, b))


def format_time(total_seconds: int) -> str:
    """
    Format seconds as h:mm:ss or m:ss or ss.
    Examples:
      - 5s -> "5"
      - 65s -> "1:05"
      - 3665s -> "1:01:05"
    """
    total_seconds = max(0, int(total_seconds))
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    elif m > 0:
        return f"{m}:{s:02d}"
    else:
        return f"{m}:{s:02d}"


def normalize_piece_name(piece_name: str) -> str:
    """Normalize piece name to lowercase for consistent lookup."""
    return piece_name.lower().strip()


# Common color constants used across games
LT_SQUARE  = (255, 255, 240)
DK_SQUARE  = (232, 200, 150)
LT_VISITED = (192, 192, 192)
DK_VISITED = (128, 128, 128)
GRID_COLOR = (107, 70, 51)
BACK_COLOR = (244, 228, 195)
