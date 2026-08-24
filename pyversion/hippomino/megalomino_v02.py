"""
Megalomino v02

Navigate a single polyomino with a knight by visiting each square just once.
Based on knightstour_controller.py structure.
"""

import os
import sys

import pygame

# --- path setup ----
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
icon_path = os.path.join(BASE_DIR, "assets", "pieces", "knight.png")
GAME_DIR = os.path.dirname(os.path.abspath(__file__))
SHAREDLIB = os.path.join(BASE_DIR, "sharedlib")
for _p in (BASE_DIR, SHAREDLIB, GAME_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gameboard import BoardModel, BoardRenderer

from pyversion.hippomino.megalomino_controller import (
    MegalominoController,
    FPS, CLASS_NAMES, BOARD_COLOR_CHOICES, CLOCK_CHOICES, CLOCK_MODES,
)

def main() -> None:
    pygame.init()

    info = pygame.display.Info()
    screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.RESIZABLE)
    try:
        knight_icon = pygame.image.load(icon_path).convert_alpha()
        pygame.display.set_icon(pygame.transform.smoothscale(knight_icon, (32, 32)))
    except Exception as e:
        print(f"Could not set knight icon: {e}")
    pygame.display.set_caption("Megalomino")

    try:
        import ctypes
        hwnd = pygame.display.get_wm_info()["window"]
        ctypes.windll.user32.ShowWindow(hwnd, 3)
    except (KeyError, AttributeError, OSError, ImportError):
        pass

    clock_ticker = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 18)
    font_large = pygame.font.SysFont("arial", 20)

    # --- menu items ----
    menu_items = [
        ("board", BOARD_COLOR_CHOICES[:], 0),
        ("shape", CLASS_NAMES[:], 0),
        ("clock", CLOCK_CHOICES, CLOCK_CHOICES.index(0)),
        ("time", CLOCK_MODES[:], 0),
    ]
    label_to_index = {lbl: i for i, (lbl, _, _) in enumerate(menu_items)}

    # --- board model / renderer ---
    # Board is not used in the traditional sense, but we need it for base class
    board_model = BoardModel(8, 8)
    board_renderer = BoardRenderer(board_model, 20, (0, 0))

    # --- controller ---
    controller = MegalominoController(
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