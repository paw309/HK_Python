"""
vexillum_v01

Refactored version using a shared controller.
Navigate the board capturing all flags before running out of moves or time.
"""

import os
import sys

import pygame

# --- path setup ---
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_DIR  = os.path.dirname(os.path.abspath(__file__))
SHAREDLIB = os.path.join(BASE_DIR, "sharedlib")
for _p in (BASE_DIR, SHAREDLIB, GAME_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gameboard import BoardModel, BoardRenderer

from pyversion.vexillology.vexillum_controller import (
    CaptureFlagsController,
    BOARD_MIN, BOARD_MAX, BOARD_DEFAULT, FPS,
    MAX_CLOCK_SECONDS, CLOCK_MODES, PATH_LENGTH_CHOICES,
    FLAG_DENSITY_CHOICES, FLAG_ORDER_CHOICES, get_globally_valid_pieces,
)


def main() -> None:
    pygame.init()

    info   = pygame.display.Info()
    screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.RESIZABLE)
    pygame.display.set_caption("Vexillum")

    try:
        import ctypes
        hwnd = pygame.display.get_wm_info()["window"]
        ctypes.windll.user32.ShowWindow(hwnd, 3)
    except (KeyError, AttributeError, OSError, ImportError):
        pass

    clock_ticker = pygame.time.Clock()
    font         = pygame.font.SysFont("arial", 18)
    font_large   = pygame.font.SysFont("arial", 20)

    # --- menu items ---
    menu_items = [
        ("board",        list(range(BOARD_MIN, BOARD_MAX + 1)), 3),
        ("piece",        get_globally_valid_pieces(), 0),
        ("path length",  PATH_LENGTH_CHOICES[:], 0),
        ("flag density", FLAG_DENSITY_CHOICES[:], 0),
        ("flag order",   FLAG_ORDER_CHOICES[:], 0),
        ("clock",        [0] + list(range(30, MAX_CLOCK_SECONDS, 30)), 0),  # values in seconds
        ("time per",     CLOCK_MODES[:], 0),
    ]
    label_to_index = {lbl: i for i, (lbl, _, _) in enumerate(menu_items)}

    # --- board model / renderer ---
    board_model    = BoardModel(BOARD_DEFAULT, BOARD_DEFAULT)
    board_renderer = BoardRenderer(board_model, 10, (0, 0))

    # --- controller ---
    controller = CaptureFlagsController(
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