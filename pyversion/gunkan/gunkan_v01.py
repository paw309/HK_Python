"""
Gunkan v01

Two-player battleship-inspired game.
Each player owns a hidden set of polyomino shapes.  Race to land on all of
your opponent's shapes before they land on all of yours.
"""

import os
import sys

import pygame

# --- path setup ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_DIR = os.path.dirname(os.path.abspath(__file__))
SHAREDLIB = os.path.join(BASE_DIR, "sharedlib")
POLYOMINOES_DIR = os.path.join(BASE_DIR, "polyominoes")
DUELOMINOES_DIR = os.path.join(BASE_DIR, "duelominoes")
for _p in (BASE_DIR, SHAREDLIB, GAME_DIR, POLYOMINOES_DIR, DUELOMINOES_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gameboard import BoardModel, BoardRenderer

from pyversion.gunkan.gunkan_controller import (
    GunkanController,
    BOARD_MIN, BOARD_MAX, BOARD_DEFAULT, FPS,
    SHAPES_CHOICES, PLAYER_ONE_CHOICES, OPPONENT_LEVEL_CHOICES, CLOCK_MODES,
    get_globally_valid_pieces,
)


def main() -> None:
    pygame.init()

    info = pygame.display.Info()
    screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.RESIZABLE)
    pygame.display.set_caption("Gunkan")

    try:
        import ctypes
        hwnd = pygame.display.get_wm_info()["window"]
        ctypes.windll.user32.ShowWindow(hwnd, 3)
    except (KeyError, AttributeError, OSError, ImportError):
        pass

    clock_ticker = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 18)
    font_large = pygame.font.SysFont("arial", 20)

    # --- menu items ---
    globally_valid_pieces = get_globally_valid_pieces()

    menu_items = [
        ("board",      list(range(BOARD_MIN, BOARD_MAX + 1)), 6),  # idx 3 → 8
        ("piece",      globally_valid_pieces[:], 30),
        ("shapes",     SHAPES_CHOICES[:], 0),                       # idx 0 → classic
        ("first move", PLAYER_ONE_CHOICES[:], 0),                   # idx 0 → human
        ("level",      OPPONENT_LEVEL_CHOICES[:], 0),               # idx 0 → 1
        ("clock",      [0] + list(range(30, 330, 30)), 0),          # values in seconds
        ("time per",   CLOCK_MODES[:], 0),                          # idx 0 → game
    ]
    label_to_index = {lbl: i for i, (lbl, _, _) in enumerate(menu_items)}

    # --- board model / renderer ---
    board_model = BoardModel(BOARD_DEFAULT, BOARD_DEFAULT)
    board_renderer = BoardRenderer(board_model, 10, (0, 0))

    # --- controller ---
    controller = GunkanController(
        board_model, board_renderer,
        menu_items, label_to_index,
        font, font_large,
        BASE_DIR,
    )

    # --- main loop ---
    while True:
        dt = clock_ticker.tick(FPS)
        controller.update(dt)

        for event in pygame.event.get():
            if not controller.handle_event(event):
                pygame.quit()
                return

        controller.render(screen)
        pygame.display.flip()
        pygame.time.wait(5)


if __name__ == "__main__":
    main()