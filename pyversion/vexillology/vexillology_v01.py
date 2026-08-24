"""
Vexillology v0.1

A two-player competitive flag-capture game.

Players take alternating turns navigating a shared board; the first to
collect the majority of flags wins.  The game ends when neither player
can make a legal move.
"""

import os
import sys

import pygame

# --- path setup ---
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_DIR  = os.path.dirname(os.path.abspath(__file__))
SHAREDLIB = os.path.join(BASE_DIR, "sharedlib")
CTF_DIR   = os.path.join(BASE_DIR, "vexillum")
for _p in (BASE_DIR, SHAREDLIB, GAME_DIR, CTF_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gameboard import BoardModel, BoardRenderer
from pyversion.vexillology.vexillology_controller import (
    VexillologyController,
    BOARD_MIN, BOARD_MAX, BOARD_DEFAULT, FPS,
    PATH_LENGTH_CHOICES, FLAG_DENSITY_CHOICES, FLAG_ORDER_CHOICES,
    PLAYER_ONE_CHOICES, OPPONENT_LEVEL_CHOICES, CLOCK_MODES,
    MAX_CLOCK_SECONDS, get_globally_valid_pieces,
)


def main() -> None:
    pygame.init()

    info = pygame.display.Info()
    screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.RESIZABLE)
    pygame.display.set_caption("Vexillology")

    try:
        import ctypes
        hwnd = pygame.display.get_wm_info()["window"]
        ctypes.windll.user32.ShowWindow(hwnd, 3)
    except (KeyError, AttributeError, OSError, ImportError):
        pass

    clock_ticker = pygame.time.Clock()
    font       = pygame.font.SysFont("arial", 18)
    font_large = pygame.font.SysFont("arial", 20)

    # --- menu items ---
    # Clock options: 0 = infinity, then 30-second increments from 30 to 300
    clock_values = [0] + list(range(30, MAX_CLOCK_SECONDS + 1, 30))

    menu_items = [
        ("board",       list(range(BOARD_MIN, BOARD_MAX + 1)), 3),  # idx 3 → 8
        ("piece",       get_globally_valid_pieces(), 0),
        ("path length", PATH_LENGTH_CHOICES[:], 1),                  # medium
        ("flag density",FLAG_DENSITY_CHOICES[:], 1),                 # medium
        ("flag order",  FLAG_ORDER_CHOICES[:], 0),                   # any
        ("first move",  PLAYER_ONE_CHOICES[:], 0),                   # human
        ("level",       OPPONENT_LEVEL_CHOICES[:], 0),               # level 1
        ("clock",       clock_values, 0),                            # infinity
        ("time per",    CLOCK_MODES[:], 0),                          # game
    ]
    label_to_index = {lbl: i for i, (lbl, _, _) in enumerate(menu_items)}

    # --- board model / renderer ---
    board_model    = BoardModel(BOARD_DEFAULT, BOARD_DEFAULT)
    board_renderer = BoardRenderer(board_model, 10, (0, 0))

    # --- controller ---
    controller = VexillologyController(
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