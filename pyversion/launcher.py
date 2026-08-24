"""
Hamiltonian Knights Launcher

A pygame-based game launcher.  Select any game from the list and click
a button to start it in a separate process.  The launcher waits while
the game runs and returns to the menu automatically when the game exits.
"""

import os
import pathlib
import subprocess
import sys
import webbrowser

import pygame

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Game registry
# Each entry: title, solo script, readme path, vs-bot script, description.
# None means no button is drawn for that action.
# ---------------------------------------------------------------------------
GAMES = [
    {
        "title":  "Knight's Tour",
        "solo":   os.path.join("knightstour", "knightstour_v02.py"),
        "readme": os.path.join("knightstour", "README.md"),
        "vs_bot": os.path.join("knightstour", "knightstrap_v01.py"),
        "desc":   "classic Knight's Tour puzzle",
    },
    {
        "title": "Knight's Turing Machine",
        "solo":   os.path.join("knightsturing", "knightsturing_v01.py"),
        "readme": os.path.join("knightsturing", "README.md"),
        "vs_bot": None,
        "desc":   "Hamiltonian path on Turing machines (in dev)",
    },
    {
        "title":  "Palisades",
        "solo":   os.path.join("palisades", "palisades_v01.py"),
        "readme": os.path.join("palisades", "README.md"),
        "vs_bot": None,
        "desc":   "non-crossing Knight's Tour",
    },
    {
        "title":  "Vexillology",
        "solo":   os.path.join("vexillology", "vexillum_v01.py"),
        "readme": os.path.join("vexillology", "README.md"),
        "vs_bot": os.path.join("vexillology", "vexillology_v01.py"),
        "desc":   "capture the flags",
    },
    {
        "title":  "Mined Maze",
        "solo":   os.path.join("minedmaze", "minedmaze_v02.py"),
        "readme": os.path.join("minedmaze", "README.md"),
        "vs_bot": os.path.join("minedmaze", "minedcontrol_v01.py"),
        "desc":   "adapted from classic Mind Maze",
    },
    {
        "title":  "Polyomino",
        "solo":   os.path.join("polyominoes", "polyomino_v02.py"),
        "readme": os.path.join("polyominoes", "README.md"),
        "vs_bot": os.path.join("polyominoes", "duelomino_v01.py"),
        "desc":   "find hidden polyominoes",
    },
    {
        "title":  "Gunkan",
        "solo":   None,
        "readme": os.path.join("gunkan", "README.md"),
        "vs_bot": os.path.join("gunkan", "gunkan_v01.py"),
        "desc":   "adapted from classic Battleship",
    },
    {
        "title":  "Cliquebait",
        "solo":   None,
        "readme": os.path.join("cliquebait", "README.md"),
        "vs_bot": None,
        "desc":   "avoid monochromatic cliques in colored graph",
    },
    {
        "title":  "Megalomino",
        "solo":   os.path.join("hippomino", "megalomino_v02.py"),
        "readme": os.path.join("hippomino", "README.md"),
        "vs_bot": None,
        "desc":   "Knight's Tour on a single polyomino",
    },
    {
        "title": "piecekeeper",
        "solo": None,
        "readme": os.path.join("sharedlib", "piece_suitability_per_game.md"),
        "vs_bot": None,
        "desc": "discussion of all 38 pieces",
    },
]

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

WINDOW_W      = 1200
WINDOW_H      = 800
FPS           = 30
HEADER_H      = 90
TITLE_ROW_H   = 70   # height of the title + buttons row
TITLE_COL_W   = 180  # reserved width for the game title before the description
ROW_TEXT_PAD  = 14   # horizontal padding before title/description text within a row
GAME_H        = TITLE_ROW_H
SIDE_PAD      = 40
BTN_W         = 100
BTN_H         = 32
BTN_GAP       = 8    # horizontal gap between buttons
BTN_RIGHT_PAD = 10   # gap between rightmost button and row edge
ICON_SIZE     = 60

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------

COL_BG          = (244,228,195)
COL_HEADER_BG   = (244,228,195)
COL_ROW_EVEN    = (255,255,240)
COL_ROW_ODD     = (232,200,150)
COL_ROW_HOVER   = (0,192,255)
COL_DIVIDER     = (107,70,51)
COL_TITLE       = (0,0,128)
COL_SUBTITLE    = (0,0,192)
COL_GAME_NAME   = (107,70,51)
COL_BTN         = (107,70,51)
COL_BTN_HOVER   = (0,192,0) #(192,0,192)
COL_BTN_TEXT    = (255,255,255)
COL_QUIT_BTN    = (175,70,70)
COL_QUIT_HOVER  = (255,0,0)
COL_WAIT_BG     = (107,70,51)
COL_WAIT_TEXT   = (140,220,140)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_knight_icon(size: int) -> pygame.Surface | None:
    path = os.path.join(BASE_DIR, "assets", "pieces", "knight.png")
    try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.smoothscale(img, (size, size))
    except Exception:
        return None


def _draw_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    font: pygame.font.Font,
    base_col: tuple,
    hover_col: tuple,
    text_col: tuple,
    mouse_pos: tuple,
) -> bool:
    """Draw a rounded button; return True if the cursor is over it."""
    hovered = rect.collidepoint(mouse_pos)
    pygame.draw.rect(surface, hover_col if hovered else base_col, rect, border_radius=6)
    pygame.draw.rect(surface, COL_DIVIDER, rect, width=1, border_radius=6)
    text_surf = font.render(label, True, text_col)
    surface.blit(text_surf, text_surf.get_rect(center=rect.center))
    return hovered


# ---------------------------------------------------------------------------
# Main launcher loop
# ---------------------------------------------------------------------------

def run_launcher() -> None:
    pygame.init()

    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H), pygame.RESIZABLE)
    pygame.display.set_caption("Hamiltonian Knights Launcher")

    knight_img = _load_knight_icon(ICON_SIZE)
    if knight_img:
        icon_surf = pygame.transform.smoothscale(knight_img, (32, 32))
        pygame.display.set_icon(icon_surf)

    clock_ticker = pygame.time.Clock()

    font_title   = pygame.font.SysFont("arial", 30, bold=True)
    font_sub     = pygame.font.SysFont("arial", 18)
    font_game    = pygame.font.SysFont("arial", 19, bold=True)
    font_btn     = pygame.font.SysFont("arial", 15, bold=True)
    font_waiting = pygame.font.SysFont("arial", 22, bold=True)

    running_proc: subprocess.Popen | None = None
    launch_error: str | None = None

    while True:
        win_wide, win_high = screen.get_size()
        mouse_pos = pygame.mouse.get_pos()
        clicked   = False

        # ----------------------------------------------------------------
        # Event handling
        # ----------------------------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if running_proc is not None:
                    running_proc.terminate()
                pygame.quit()
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True

        # ----------------------------------------------------------------
        # While a game is running — show a waiting screen
        # ----------------------------------------------------------------
        if running_proc is not None:
            if running_proc.poll() is not None:
                running_proc = None          # game exited → fall through to menu
            else:
                screen.fill(COL_WAIT_BG)
                msg1 = font_waiting.render("Game is running…", True, COL_WAIT_TEXT)
                msg2 = font_sub.render(
                    "Close the game window to return here.", True, COL_SUBTITLE
                )
                screen.blit(msg1, msg1.get_rect(center=(win_wide // 2, win_high // 2 - 18)))
                screen.blit(msg2, msg2.get_rect(center=(win_wide // 2, win_high // 2 + 18)))
                pygame.display.flip()
                clock_ticker.tick(FPS)
                continue

        # ----------------------------------------------------------------
        # Draw the launcher menu
        # ----------------------------------------------------------------
        screen.fill(COL_BG)

        # --- Header ---
        pygame.draw.rect(screen, COL_HEADER_BG, (0, 0, win_wide, HEADER_H))
        pygame.draw.line(screen, COL_DIVIDER, (0, HEADER_H), (win_wide, HEADER_H), 1)

        text_x = SIDE_PAD
        if knight_img:
            icon_y = (HEADER_H - ICON_SIZE) // 2
            screen.blit(knight_img, (SIDE_PAD, icon_y))
            text_x = SIDE_PAD + ICON_SIZE + 10

        title_surf = font_title.render("Hamiltonian Knights", True, COL_TITLE)
#        sub_surf   = font_sub.render("select a game and click launch", True, COL_SUBTITLE)
        screen.blit(title_surf, (text_x, HEADER_H // 2 - title_surf.get_height() // 2 - 8))
#        screen.blit(sub_surf,   (text_x, HEADER_H // 2 + title_surf.get_height() // 2 - 6))

        # --- Fixed button column x-positions (vertically aligned across all games) ---
        # Columns (right to left): vs bot | README | solo
        btn_vsbot_x  = win_wide - SIDE_PAD - BTN_W - BTN_RIGHT_PAD
        btn_readme_x = btn_vsbot_x - BTN_W - BTN_GAP
        btn_solo_x   = btn_readme_x - BTN_W - BTN_GAP

        # --- Game rows ---
        list_top  = HEADER_H + 30
        # btn_rects entries: (rect, path, "launch"|"readme")
        btn_rects: list[tuple[pygame.Rect, str, str]] = []

        for i, game in enumerate(GAMES):
            game_y = list_top + i * GAME_H

            # Hover rect / row background (single row)
            title_row_rect = pygame.Rect(SIDE_PAD, game_y, win_wide - 2 * SIDE_PAD, GAME_H - 1)
            row_bg = (
                COL_ROW_HOVER
                if title_row_rect.collidepoint(mouse_pos)
                else (COL_ROW_EVEN if i % 2 == 0 else COL_ROW_ODD)
            )

            # Draw title row background
            pygame.draw.rect(screen, row_bg, title_row_rect, border_radius=4)

            # Title (row 1, left-aligned)
            name_surf = font_game.render(game["title"], True, COL_GAME_NAME)
            screen.blit(
                name_surf,
                (title_row_rect.x + ROW_TEXT_PAD, title_row_rect.centery - name_surf.get_height() // 2),
            )

            # Buttons (row 1, right-aligned at fixed columns)
            btn_y = title_row_rect.centery - BTN_H // 2

            if game["solo"]:
                solo_rect = pygame.Rect(btn_solo_x, btn_y, BTN_W, BTN_H)
                _draw_button(screen, solo_rect, "solo",
                             font_btn, COL_BTN, COL_BTN_HOVER, COL_BTN_TEXT, mouse_pos)
                btn_rects.append((solo_rect, game["solo"], "launch"))

            if game["readme"]:
                readme_rect = pygame.Rect(btn_readme_x, btn_y, BTN_W, BTN_H)
                _draw_button(screen, readme_rect, "README",
                             font_btn, COL_BTN, COL_BTN_HOVER, COL_BTN_TEXT, mouse_pos)
                btn_rects.append((readme_rect, game["readme"], "readme"))

            if game["vs_bot"]:
                vsbot_rect = pygame.Rect(btn_vsbot_x, btn_y, BTN_W, BTN_H)
                _draw_button(screen, vsbot_rect, "vs bot",
                             font_btn, COL_BTN, COL_BTN_HOVER, COL_BTN_TEXT, mouse_pos)
                btn_rects.append((vsbot_rect, game["vs_bot"], "launch"))

            # Description (row 1, left-aligned at fixed column after title)
            desc_x = title_row_rect.x + ROW_TEXT_PAD * 4 + TITLE_COL_W
            desc_surf = font_sub.render(game["desc"], True, COL_GAME_NAME)
            screen.blit(
                desc_surf,
                (desc_x, title_row_rect.centery - desc_surf.get_height() // 2),
            )

        # --- Quit button ---
        footer_y  = list_top + len(GAMES) * GAME_H + 10
        quit_rect = pygame.Rect(win_wide // 2 - 60, footer_y, 120, BTN_H)
        _draw_button(
            screen, quit_rect, "quit",
            font_btn, COL_QUIT_BTN, COL_QUIT_HOVER, COL_BTN_TEXT, mouse_pos,
        )

        # --- Handle clicks ---
        if clicked:
            launch_error = None
            if quit_rect.collidepoint(mouse_pos):
                pygame.quit()
                return
            for btn_rect, path, action in btn_rects:
                if btn_rect.collidepoint(mouse_pos):
                    full_path = os.path.join(BASE_DIR, path)
                    if action == "readme":
                        try:
                            webbrowser.open(pathlib.Path(full_path).as_uri())
                        except Exception as exc:
                            launch_error = f"Could not open README: {exc}"
                    else:
                        try:
                            running_proc = subprocess.Popen([sys.executable, full_path])
                        except Exception as exc:
                            launch_error = f"Could not launch game: {exc}"
                    break

        # --- Show launch error if any ---
        if launch_error:
            err_surf = font_sub.render(launch_error, True, (220, 80, 80))
            screen.blit(err_surf, err_surf.get_rect(center=(win_wide // 2, footer_y + BTN_H + 14)))

        pygame.display.flip()
        clock_ticker.tick(FPS)


if __name__ == "__main__":
    run_launcher()