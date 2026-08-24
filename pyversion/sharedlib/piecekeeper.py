"""
piecekeeper.py

Reusable piece library for chess / fairy chess pieces.

- Provides move generation (deltas, expanded patterns, move functions).
- Provides piece metadata (PIECE_LIST, PIECE_MOVE_SETS).
- Provides lazy image loading and safe fallbacks that only import pygame when image functions are called.
- Provides convenience draw_piece(screen, rect, piece_name) which blits the piece image centered into rect.
"""

#import csv
import os
import math
from math import gcd
from typing import List, Tuple, Set, Dict, Callable, Optional
#from collections import deque

# --- Core Piece Metadata: Single Source of Truth ---

def moves_from_deltas(x: int, y: int, n: int, deltas: Set[Tuple[int, int]]) -> List[Tuple[int,int]]:
    return [(x + dx, y + dy) for dx, dy in deltas if 0 <= x + dx < n and 0 <= y + dy < n]

def expand_patterns(patterns: List[Tuple[int, int]]) -> Set[Tuple[int,int]]:
    deltas = set()
    for a, b in patterns:
        for sx in (1, -1):
            for sy in (1, -1):
                deltas.add((sx * a, sy * b))
        if a != b:
            for sx in (1, -1):
                for sy in (1, -1):
                    deltas.add((sx * b, sy * a))
    return deltas

def slider_moves_from_dirs(x: int, y: int, n: int, directions: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    moves: List[Tuple[int, int]] = []
    for dx, dy in directions:
        cx, cy = x + dx, y + dy
        while 0 <= cx < n and 0 <= cy < n:
            moves.append((cx, cy))
            cx += dx
            cy += dy
    return moves

# Define core deltas and slider directions

# canon
KNIGHT_PATTERN = [(1,2)]
BISHOP_DIRS = [(1,1), (1,-1), (-1,1), (-1,-1)]
ROOK_DIRS = [(1,0), (-1,0), (0,1), (0,-1)]
QUEEN_DIRS = ROOK_DIRS + BISHOP_DIRS
KING_PATTERN = [(0,1), (1,1)]

# atomic
WAZIR_PATTERN = [(0,1)]
FERZ_PATTERN = [(1,1)]
DABBABA_PATTERN = [(0,2)]
ALFIL_PATTERN = [(2,2)]
THREELEAPER_PATTERN = [(0,3)]
TRIPPER_PATTERN = [(3,3)]

# hippo
CAMEL_PATTERN = [(1,3)]
ZEBRA_PATTERN = [(2,3)]
GIRAFFE_PATTERN = [(1,4)]
ANTELOPE_PATTERN = [(3,4)]
GAZELLE_PATTERN = [(2,5)]
FLAMINGO_PATTERN = [(1,6)]
BHARAL_PATTERN = [(4,5)]

# combo
WAPITI_PATTERN = [(1,1), (1,2)] # ferz + knight
GNU_PATTERN = [(1,2), (1,3)] # knight + camel
WILDEBEEST_PATTERN = [(1,2), (2,3)] # knight + zebra
ZEBU_PATTERN = [(1,3), (1,4)] # camel + giraffe
BISON_PATTERN = [(1,3), (2,3)] # camel + zebra

FROG_PATTERN = [(1,1), (0,3)] # ferz + threeleaper
TOAD_PATTERN = [(0,2), (0,3)] # dabbaba + threeleaper
NEWT_PATTERN = [(0,2), (1,4)] # dabbaba + giraffe

EULER_PATTERN = [(0,3), (2,2)] # dabbaba + zebra
EUCLID_PATTERN = [(0,2), (2,3)] # alfil + threeleaper

JUPITER_PATTERN = [(1,2), (2,2)] # ferz + zebra
CERES_PATTERN = [(0,3), (1,3)] # alfil + zebra
PALLAS_PATTERN = [(3,4), (0,5)] # root25

# multi
VIRGO_PATTERN = [(0,3), (1,4), (2,3)]
LIBRA_PATTERN = [(1,3), (3,4), (5,6)]
SCORPIO_PATTERN = [(0,2), (1,4), (2,5)]
CAPRICORN_PATTERN = [(2,3), (0,4), (5,6)]

PTERODACTYL_PATTERN = [(3,3), (5,5), (0,15)]

FIBONACCI_PATTERN = [(0,1), (1,1), (1,2), (2,3), (3,5), (5,8), (8,13)]
GUNKAN_PATTERN = []    # handled specially


PIECE_DATA = {
    "knight": {
        "display_pattern": KNIGHT_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(KNIGHT_PATTERN)),
        "piece_group": "leaper",
        "image": "knight.png",
    },
    "bishop": {
        "display_pattern": [(1, 1)],
        "move_func": lambda x, y, n: slider_moves_from_dirs(x, y, n, BISHOP_DIRS),
        "piece_group": "slider",
        "image": "bishop.png",
    },
    "rook": {
        "display_pattern": [(0, 1), (1, 0)],
        "move_func": lambda x, y, n: slider_moves_from_dirs(x, y, n, ROOK_DIRS),
        "piece_group": "slider",
        "image": "rook.png",
    },
    "queen": {
        "display_pattern": [(0,1), (1,1)],
        "move_func": lambda x, y, n: slider_moves_from_dirs(x, y, n, QUEEN_DIRS),
        "piece_group": "slider",
        "image": "queen.png",
    },
    "king": {
        "display_pattern": KING_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(KING_PATTERN)),
        "piece_group": "leaper",
        "image": "king.png",
    },
    "wazir": {
        "display_pattern": WAZIR_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(WAZIR_PATTERN)),
        "piece_group": "leaper",
        "image": "gamma.png",
    },
    "ferz": {
        "display_pattern": FERZ_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(FERZ_PATTERN)),
        "piece_group": "leaper",
        "image": "delta.png",
    },
    "dabbaba": {
        "display_pattern": DABBABA_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(DABBABA_PATTERN)),
        "piece_group": "leaper",
        "image": "theta.png",
    },
    "alfil": {
        "display_pattern": ALFIL_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(ALFIL_PATTERN)),
        "piece_group": "leaper",
        "image": "xi.png",
    },
    "threeleaper": {
        "display_pattern": THREELEAPER_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(THREELEAPER_PATTERN)),
        "piece_group": "leaper",
        "image": "theta.png",
    },
    "tripper": {
        "display_pattern": TRIPPER_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(TRIPPER_PATTERN)),
        "piece_group": "fleaper",
        "image": "xi.png",
    },
    "camel": {
        "display_pattern": CAMEL_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(CAMEL_PATTERN)),
        "piece_group": "leaper",
        "image": "lambda.png",
    },
    "zebra": {
        "display_pattern": ZEBRA_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(ZEBRA_PATTERN)),
        "piece_group": "leaper",
        "image": "pi.png",
    },
    "giraffe": {
        "display_pattern": GIRAFFE_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(GIRAFFE_PATTERN)),
        "piece_group": "leaper",
        "image": "sigma.png",
    },
    "antelope": {
        "display_pattern": ANTELOPE_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(ANTELOPE_PATTERN)),
        "piece_group": "fleaper",
        "image": "phi.png",
    },
    "gazelle": {
        "display_pattern": GAZELLE_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(GAZELLE_PATTERN)),
        "piece_group": "fleaper",
        "image": "psi.png",
    },
    "flamingo": {
        "display_pattern": FLAMINGO_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(FLAMINGO_PATTERN)),
        "piece_group": "fleaper",
        "image": "omega.png",
    },
    "bharal": {
        "display_pattern": BHARAL_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(BHARAL_PATTERN)),
        "piece_group": "fleaper",
        "image": "bharal.png",
    },
    "wapiti": {
        "display_pattern": WAPITI_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(WAPITI_PATTERN)),
        "piece_group": "combo",
        "image": "uranus.png",
    },
    "gnu": {
        "display_pattern": GNU_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(GNU_PATTERN)),
        "piece_group": "combo",
        "image": "uranus.png",
    },
    "wildebeest": {
        "display_pattern": WILDEBEEST_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(WILDEBEEST_PATTERN)),
        "piece_group": "combo",
        "image": "neptune.png",
    },
    "zebu": {
        "display_pattern": ZEBU_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(ZEBU_PATTERN)),
        "piece_group": "combo",
        "image": "uranus.png",
    },
    "bison": {
        "display_pattern": BISON_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(BISON_PATTERN)),
        "piece_group": "combo",
        "image": "neptune.png",
    },
    "frog": {
        "display_pattern": FROG_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(FROG_PATTERN)),
        "piece_group": "combo",
        "image": "mercury.png",
    },
    "toad": {
        "display_pattern": TOAD_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(TOAD_PATTERN)),
        "piece_group": "combo",
        "image": "venus.png",
    },
    "newt": {
        "display_pattern": NEWT_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(NEWT_PATTERN)),
        "piece_group": "combo",
        "image": "earth.png",
    },
    "euler": {
        "display_pattern": EULER_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(EULER_PATTERN)),
        "piece_group": "combo",
        "image": "mars.png",
    },
    "jupiter": {
        "display_pattern": JUPITER_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(JUPITER_PATTERN)),
        "piece_group": "combo",
        "image": "jupiter.png",
    },
    "euclid": {
        "display_pattern": EUCLID_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(EUCLID_PATTERN)),
        "piece_group": "combo",
        "image": "saturn.png",
    },
    "ceres": {
        "display_pattern": CERES_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(CERES_PATTERN)),
        "piece_group": "combo",
        "image": "ceres.png",
    },
    "pallas": {
        "display_pattern": PALLAS_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(PALLAS_PATTERN)),
        "piece_group": "combo",
        "image": "pallas.png",
    },
    "virgo": {
        "display_pattern": VIRGO_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(VIRGO_PATTERN)),
        "piece_group": "multi",
        "image": "virgo.png",
    },
    "libra": {
        "display_pattern": LIBRA_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(LIBRA_PATTERN)),
        "piece_group": "multi",
        "image": "libra.png",
    },
    "scorpio": {
        "display_pattern": SCORPIO_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(SCORPIO_PATTERN)),
        "piece_group": "multi",
        "image": "scorpio.png",
    },
    "capricorn": {
        "display_pattern": CAPRICORN_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(CAPRICORN_PATTERN)),
        "piece_group": "multi",
        "image": "capricorn.png",
    },
    "pterodactyl": {
        "display_pattern": PTERODACTYL_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(PTERODACTYL_PATTERN)),
        "piece_group": "combo",
        "image": "pluto.png",
    },
    "fibonacci": {
        "display_pattern": FIBONACCI_PATTERN,
        "move_func": lambda x, y, n: moves_from_deltas(x, y, n, expand_patterns(FIBONACCI_PATTERN)),
        "piece_group": "multi",
        "image": "fibonacci.png",
    },
    "gunkan": {
        "display_pattern": [("r", "s"), ("gcd", 1)],
        "move_func": lambda x, y, n: moves_from_deltas(
            x, y, n,
            set(
                d for r in range(n) for s in range(n)
                if not (r == 0 and s == 0) and gcd(r,s) == 1
                for d in expand_patterns([(r,s)])
            )
        ),
        "piece_group": "multi",
        "image": "gunkan.png",
    },
}

# --- Metadata helpers and compatibility ---
PIECE_LIST = list(PIECE_DATA.keys())

def get_move_func(piece_name: str) -> Callable[[int, int, int], List[Tuple[int, int]]]:
    return PIECE_DATA.get(piece_name, PIECE_DATA["knight"])["move_func"]

def get_piece_move_sets_text(piece_name: str) -> str:
    if piece_name == "gunkan":
        return "gcd (r,s) = 1"
    # Slider pieces use special notation
    if piece_name == "queen":
        return "{n,0} {0,n} {n,n}"
    elif piece_name == "rook":
        return "{n,0} {0,n}"
    elif piece_name == "bishop":
        return "{n,n}"
    # All other pieces: display sorted normalized patterns
    patterns = PIECE_DATA.get(piece_name, PIECE_DATA["knight"])["display_pattern"]
    normalized = [tuple(sorted(s)) for s in patterns]
    normalized.sort(key=lambda t: math.sqrt(t[0] ** 2 + t[1] ** 2))
    parts = [f"{{{a},{b}}}" for a, b in normalized]
    return " ".join(parts)


# --- Image handling ---

_IMAGES: Dict[str, "pygame.Surface"] = {}
_IMAGE_DIR: Optional[str] = None
_IMAGE_SQ: Optional[int] = None

def _ensure_pygame():
    import pygame as _pygame
    return _pygame

def _create_generic_image(sq_size: int, letter: Optional[str] = None):
    pygame = _ensure_pygame()
    size = (sq_size, sq_size)
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    try:
        font = pygame.font.SysFont("arial", max(12, int(sq_size * 0.7)))
    except Exception:
        pygame.font.init()
        font = pygame.font.SysFont("arial", max(12, int(sq_size * 0.7)))
    text = (letter or "?").upper()
    txt = font.render(text, True, (0, 0, 0))
    tw, th = txt.get_size()
    surf.blit(txt, ((size[0] - tw) // 2, (size[1] - th) // 2))
    return surf

def _load_image_scaled(filename: str, sq_size: int):
    pygame = _ensure_pygame()
    try:
        img = pygame.image.load(filename)
        img = img.convert_alpha()
        return pygame.transform.smoothscale(img, (sq_size, sq_size))
    except Exception:
        return None

def load_images(image_dir: str = "images", sq_size: int = 39) -> Dict[str, "pygame.Surface"]:
    global _IMAGES, _IMAGE_DIR, _IMAGE_SQ
    _ensure_pygame()
    _IMAGE_DIR = image_dir
    _IMAGE_SQ = int(sq_size)
    imgs: Dict[str, "pygame.Surface"] = {}
    for piece, pdata in PIECE_DATA.items():
        fname = pdata.get("image", "")
        fullpath = os.path.join(image_dir, fname)
        surf = _load_image_scaled(fullpath, _IMAGE_SQ)
        if surf is None:
            letter = piece[0] if piece else "?"
            surf = _create_generic_image(_IMAGE_SQ, letter)
        imgs[piece] = surf
    _IMAGES = imgs
    return _IMAGES

def get_image(piece_name: str, image_dir: Optional[str] = None, sq_size: Optional[int] = None):
    global _IMAGES, _IMAGE_DIR, _IMAGE_SQ
    if not _IMAGES:
        dir_to_use = image_dir or _IMAGE_DIR or "images"
        sq_to_use = int(sq_size or _IMAGE_SQ or 39)
        load_images(dir_to_use, sq_to_use)

    if piece_name in _IMAGES:
        return _IMAGES[piece_name]
    else:
        letter = piece_name[0] if piece_name else "?"
        return _create_generic_image(_IMAGE_SQ or (sq_size or 39), letter)

def draw_piece(screen, rect, piece_name: str = "knight"):
    img = get_image(piece_name)
    img_rect = img.get_rect(center=rect.center)
    screen.blit(img, img_rect)