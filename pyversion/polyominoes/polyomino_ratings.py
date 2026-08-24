"""
polyomino_ratings.py

Handles loading, caching, and computing piece ratings for Polyomino game.
Also includes the playability-assessment helper.

"""

import csv
import os
from collections import deque
from typing import Dict, Optional

# --- You must install piecekeeper.py in the same directory or python path ---
import piecekeeper as pk
from mobility_ratings import get_mobility_rating

# --- Piece Ratings Data and Lazy Loading ---

_AGILITY_RATINGS_DATA: Dict[str, Dict] = {}
_RATINGS_LOADED = False

DEFAULT_RATINGS = {
    'mobility_rating': 3,  # matches DEFAULT_MOBILITY_RATING in mobility_ratings.py
    'agility_rating': 0,
}


def _load_agility_ratings():
    """Load agility ratings from piece_agility_ratings.csv"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(script_dir, "piece_agility_ratings.csv")
    if not os.path.exists(filename):
        print(f"Warning: {filename} not found. Agility ratings will be unavailable.")
        return

    with open(filename, mode='r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            try:
                piece_name = row['piece']
                shape_type = row['shape_type']  # Short name: dom, tri, etc.
                agility_rating = int(row['agility_rating'])

                if piece_name not in _AGILITY_RATINGS_DATA:
                    _AGILITY_RATINGS_DATA[piece_name] = {}

                _AGILITY_RATINGS_DATA[piece_name][shape_type] = agility_rating

            except (KeyError, ValueError) as e:
                print(f"Warning: Skipping malformed row in {filename}: {row}. Error: {e}")


def _ensure_ratings_loaded():
    global _RATINGS_LOADED
    if not _RATINGS_LOADED:
        _load_agility_ratings()
        _RATINGS_LOADED = True


def get_piece_ratings(piece_name: str, board_size: int, shape_type: Optional[str] = None) -> Dict[str, int]:
    """
    Returns mobility rating (0-5) for a given piece and board size.
    If shape_type is provided, also returns agility rating (0-5).
    """
    _ensure_ratings_loaded()

    # Get mobility rating from pre-built lookup table (O(1))
    mobility_rating = get_mobility_rating(piece_name, board_size)

    # Get agility rating if shape_type provided
    agility_rating = 0
    if shape_type:
        # Map full names to short names
        shape_map = {
            "monomino": "mon",
            "domino": "dom",
            "triomino": "tri",
            "tetromino": "tet",
            "pentomino": "pen",
            "hexomino": "hex",
            "heptomino": "hep",
            "octomino": "oct",
            "mixed": "mix"
        }

        short_shape = shape_map.get(shape_type)
        if short_shape and piece_name in _AGILITY_RATINGS_DATA:
            agility_rating = _AGILITY_RATINGS_DATA[piece_name].get(short_shape, 0)

    return {
        'mobility_rating': mobility_rating,
        'agility_rating': agility_rating
    }


def assess_piece_playability(piece_name: str, board_size: int) -> str:
    move_func = pk.get_move_func(piece_name)
    is_slider = piece_name.lower() in {"rook", "queen"}

    total_moves = sum(len(move_func(x, y, board_size)) for y in range(board_size) for x in range(board_size))

    q = deque([(0, 0)])
    reachable = {(0, 0)}
    while q:
        x, y = q.popleft()
        for move in move_func(x, y, board_size):
            if move not in reachable:
                reachable.add(move)
                q.append(move)


    if total_moves == 0 or len(reachable) < board_size * board_size:
        return 'choose a larger board'


    theoretical_moves = pk.expand_patterns(pk.PIECE_DATA.get(piece_name, pk.PIECE_DATA["knight"])["display_pattern"])
    possible_deltas = set()
    for y in range(board_size):
        for x in range(board_size):
            for move_x, move_y in move_func(x, y, board_size):
                possible_deltas.add((move_x - x, move_y - y))

    if not theoretical_moves.issubset(possible_deltas): return ' '
    return ''