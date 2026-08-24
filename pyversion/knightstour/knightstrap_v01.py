"""
Knightstrap v01

Two-player competitive knight's tour game.
Players take alternating turns to visit more squares than their opponent.
"""

import os
import sys

import pygame

# --- path setup ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
icon_path = os.path.join(BASE_DIR, "assets", "pieces", "knight.png")
GAME_DIR = os.path.dirname(os.path.abspath(__file__))
SHAREDLIB = os.path.join(BASE_DIR, "sharedlib")
for _p in (BASE_DIR, SHAREDLIB, GAME_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gameboard import BoardModel, BoardRenderer

from pyversion.knightstour.knightstrap_controller import (
    KnightsTrapController, BOARD_MIN, BOARD_MAX, BOARD_DEFAULT, FPS,
    FIRST_SQUARE_CHOICES, OPPONENT_LEVEL_CHOICES, PLAYER_ONE_CHOICES, CLOCK_MODES, MAX_CLOCK_SECONDS,
    get_globally_valid_pieces,
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
    pygame.display.set_caption("Knight's Trap")

    try:
        import ctypes
        hwnd = pygame.display.get_wm_info()["window"]
        ctypes.windll.user32.ShowWindow(hwnd, 3)
    except (KeyError, AttributeError, OSError, ImportError):
        pass

    clock_ticker = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 18)
    font_large = pygame.font.SysFont("arial", 20)

    valid_pieces = get_globally_valid_pieces()

    # --- menu items ---
    menu_items = [
        ("board", list(range(BOARD_MIN, BOARD_MAX + 1)), 3),  # idx 3 -> 8
        ("piece", valid_pieces[:], 0),
        ("player one", PLAYER_ONE_CHOICES[:], 0),
        ("first square", FIRST_SQUARE_CHOICES[:], 0),
        ("opponent", OPPONENT_LEVEL_CHOICES[:], 0),
        ("clock", [0] + list(range(30, MAX_CLOCK_SECONDS, 30)), 0),  # values in seconds
#        ("clock", [0] + list(range(60, 30 * 60 + 1, 60)), 0),  # 0 = infinity
        ("time per", CLOCK_MODES[:], 0),
    ]
    label_to_index = {lbl: i for i, (lbl, _, _) in enumerate(menu_items)}

    # --- board model / renderer ---
    board_model = BoardModel(BOARD_DEFAULT, BOARD_DEFAULT)
    board_renderer = BoardRenderer(board_model, 10, (0, 0))

    # --- controller ---
    controller = KnightsTrapController(
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