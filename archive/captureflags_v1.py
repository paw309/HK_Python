# This file is captureflags_v1.py
# It uses the new piecekeeper module for piece metadata, move generation, and image handling.

import time

import pygame
import sys

import piecekeeper as pk

import os

pygame.init()
screen = pygame.display.set_mode((800, 600))  # This opens the window

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
image_dir_path = os.path.join(BASE_DIR, "assets")
pieces_dir    = os.path.join(BASE_DIR, "assets", "pieces")
arrows_dir    = os.path.join(BASE_DIR, "assets", "arrows")
flags_dir   = os.path.join(BASE_DIR, "assets", "flags")
markers_dir   = os.path.join(BASE_DIR, "assets", "markers")


# --- CONSTANTS ---
BOARD_MIN = 5
BOARD_MAX = 16
BOARD_DEFAULT = 8
CLOCK_DEFAULT = 0 * 60  # seconds
SQ_SIZE = 36
PANEL_W = SQ_SIZE * 8
PANEL_H = SQ_SIZE * 16
BOARD_W = SQ_SIZE * 16
BOARD_H = SQ_SIZE * 16

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
PURPLE = (189, 135, 249)
GREEN = (30, 180, 30)
ORANGE = (255, 150, 0)
BROWN = (102, 51, 0)
GRAY = (128, 128, 128)

BACK_COLOR = (244, 228, 195)
LIGHT_SQUARE = (255, 255, 240)
DARK_SQUARE = (232, 200, 150)
LIGHT_MOVE = (148, 220, 248)
DARK_MOVE = (100, 145, 225)
LIGHT_BLOCK = (255, 192, 192)
DARK_BLOCK = (255, 128, 128)

FONT_16 = pygame.font.SysFont("arial", 16)
FONT_18 = pygame.font.SysFont("arial", 18)
FONT_20 = pygame.font.SysFont("arial", 20)
FONT_32 = pygame.font.SysFont("arial", 32)


PATH_LENGTH_CHOICES = ["short", "medium", "long"]

PATH_LENGTH_MAP = {
    "short": 2,
    "medium": 3,
    "long": 4
}

FLAG_DENSITY_CHOICES = ["low", "medium", "high"]


FLAG_DENSITY_MAP = {
    "low": 0.2,
    "medium": 0.4,
    "high": 0.6
}


FLAG_ORDER_CHOICES = ["any", "only"]


flag_icons = {
    "gray": pygame.image.load(os.path.join(flags_dir, "flag_gray.png")).convert_alpha(),
    "black": pygame.image.load(os.path.join(flags_dir, "flag_black.png")).convert_alpha(),
    "color": pygame.image.load(os.path.join(flags_dir, "flag_blue.png")).convert_alpha(),
}


PIECE_MIN_BOARD_SIZE_FOR_MAZE = {
    "knight": 5, "king": 5, "queen": 5, "rook": 5, "bishop": 5,
    "gamma": 5, "delta": 5, "theta": 5, "lambda": 8, "xi": 5,
    "pi": 5, "sigma": 5, "phi": 8, "psi": 8, "omega": 8,
    "mercury": 5, "venus": 5, "earth": 5, "mars": 5,
    "jupiter": 5, "saturn": 5, "uranus": 5, "neptune": 5,
    "ceres": 5, "pallas": 8, "pluto": 16,
    "leo": 5, "virgo": 5, "libra": 5,
    "scorpio": 6, "sagittarius": 5, "capricorn": 5,
    "fibonacci": 5, "gunkan": 5,
}


def get_min_board_size(selected_piece):
    """Get minimum board size for maze generation with this piece."""
    return PIECE_MIN_BOARD_SIZE_FOR_MAZE.get(selected_piece, 5)


# --- Clock helper functions ---

INFINITY_SYMBOL = "∞"


def format_clock_seconds(seconds):
    if seconds is None:
        seconds = 0
    seconds = max(0, int(seconds))
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins}:{secs:02d}"


def display_for_selection(clock_selected):
    if clock_selected == 0:
        return INFINITY_SYMBOL
    return format_clock_seconds(clock_selected)


def remaining_for(clock_selected, clock_elapsed):
    if clock_selected == 0:
        return None
    return max(0, int(clock_selected) - int(clock_elapsed or 0))


def clock_has_expired(clock_selected, clock_elapsed):
    if clock_selected == 0:
        return False
    return int(clock_elapsed or 0) >= int(clock_selected)


# button definitions

BUTTON_HT = SQ_SIZE * .75

STANDARD_BUTTONS = {
    "start": {
        "color": BLUE,
        "text": "start",
        "rect": lambda menu_inner: pygame.Rect(SQ_SIZE * 3.25, menu_inner.top + SQ_SIZE * 8,
                                               SQ_SIZE * 4, BUTTON_HT),
    },
    "resign": {
        "color": GRAY,
        "text": "resign",
        "rect": lambda menu_inner: pygame.Rect(SQ_SIZE * 3.25, menu_inner.top + SQ_SIZE * 12,
                                               SQ_SIZE * 4, BUTTON_HT),
    },
    "exit": {
        "color": RED,
        "text": "exit",
        "rect": lambda menu_inner: pygame.Rect(SQ_SIZE * 6.25, menu_inner.top + SQ_SIZE * 14,
                                               SQ_SIZE * 2, BUTTON_HT),
    },
    "move_guide": {
        "color": GREEN,
        "text": "move guide",
        "rect": lambda menu_inner: pygame.Rect(SQ_SIZE * 3.25, menu_inner.top + SQ_SIZE * 10,
                                               SQ_SIZE * 4, BUTTON_HT),
    },
    "replay": {
        "color": BLUE,
        "text": "play again",
        "rect": lambda menu_inner: pygame.Rect(SQ_SIZE * 3.25, menu_inner.top + SQ_SIZE * 8,
                                               SQ_SIZE * 4, BUTTON_HT),
    },
    "newgame": {
        "color": GREEN,
        "text": "new game",
        "rect": lambda menu_inner: pygame.Rect(SQ_SIZE * 3.25, menu_inner.top + SQ_SIZE * 12,
                                               SQ_SIZE * 4, BUTTON_HT),
    },
}


def maximize_window():
    if sys.platform.startswith("win"):
        hwnd = pygame.display.get_wm_info().get('window')
        if hwnd:
            try:
                import ctypes
                ctypes.windll.user32.ShowWindow(hwnd, 3)
            except Exception as e:
                print("Could not maximize window:", e)


# generate path and flags

def generate_open_path_with_flags(
        board_size,
        min_length=None,
        max_length=None,
        move_func=None,
        max_attempts=None,
        time_budget=None,
        flag_density_choice="low"
):
    """
    Generates an open path (with no obstacles) in an n x n board,
    and selects multiple targets (flags) along the path based on density.

    Returns: (path, flags) where
      - path: list of board positions representing the path (including start)
      - flags: list of positions along the path (ordinal order matters for modes like 'next')
    """
    import random
    import time

    if move_func is None:
        move_func = pk.get_move_func("knight")
    if min_length is None:
        min_length = board_size + 1
    if max_length is None:
        max_length = board_size * 2

    squares = [(x, y) for x in range(board_size) for y in range(board_size)]
    start_time = time.time() if time_budget is not None else None

    for attempt in range(max_attempts or 1000):
        if time_budget is not None and (time.time() - start_time) > time_budget:
            break
        # Pick random starting point
        start = random.choice(squares)
        path = [start]
        path_set = {start}
        while len(path) < max_length:
            current = path[-1]
            moves = [move for move in move_func(*current, board_size) if move not in path_set]
            if not moves:
                break
            next_square = random.choice(moves)
            path.append(next_square)
            path_set.add(next_square)
        if len(path) >= min_length:
            # Select flags by density (always including the last square as a flag)
            num_flags = max(1, int(len(path) * FLAG_DENSITY_MAP[flag_density_choice]))
            last_idx = len(path) - 1
            num_random_flags = num_flags - 1
            flag_pool = list(range(len(path) - 1))
            random_flag_indices = random.sample(flag_pool, k=num_random_flags) if num_random_flags > 0 else []
            # Produce a sorted list for consistent flag ordering
            flags_idx = sorted(random_flag_indices + [last_idx])
            flags = [path[idx] for idx in flags_idx]  # flags returned in path order
            return path, flags
    return None, None

# helper: compute the menu and board border/inner rectangles
def compute_layout():
    menu_border = pygame.Rect(SQ_SIZE, SQ_SIZE, PANEL_W + SQ_SIZE / 8, PANEL_H + SQ_SIZE / 8)
    menu_inner = pygame.Rect(
        menu_border.left + 1,
        menu_border.top + 1,
        max(0, menu_border.width - 2),
        max(0, menu_border.height - 2),
    )

    right_menu_border = pygame.Rect(SQ_SIZE * 26.5, SQ_SIZE, PANEL_W, PANEL_H + SQ_SIZE / 8)
    right_menu_inner = pygame.Rect(
        right_menu_border.left + 1,
        right_menu_border.top + 1,
        max(0, right_menu_border.width - 2),
        max(0, right_menu_border.height - 2),
    )

    board_border_left = menu_border.right + SQ_SIZE * .67
    board_border_top = menu_border.top

    board_border = pygame.Rect(board_border_left, board_border_top, BOARD_W + 12, BOARD_H + 12)
    board_inner = pygame.Rect(
        board_border.left + 1,
        board_border.top + 1,
        max(0, board_border.width - 2),
        max(0, board_border.height - 2),
    )

    return menu_border, menu_inner, board_border, board_inner, right_menu_border, right_menu_inner


def draw_button(screen, rect, color, label, font=FONT_18):
    pygame.draw.rect(screen, color, rect)
    txt = font.render(label, True, WHITE)
    tw = txt.get_width()
    th = txt.get_height()
    screen.blit(txt, (rect.x + (rect.width - tw) // 2, rect.y + (rect.height - th) // 2))


def draw_standard_button(screen, button_name, menu_inner, font=FONT_18):
    properties = STANDARD_BUTTONS[button_name]
    rect = properties["rect"](menu_inner)
    draw_button(screen, rect, properties["color"], properties["text"], font)
    return rect


def get_menu_field_rects(menu_inner, sq_size):
    btn_w = SQ_SIZE / 2
    btn_h = SQ_SIZE / 2
    col1 = menu_inner.left + SQ_SIZE * 3
    col2 = menu_inner.left + SQ_SIZE * 6
    col3 = menu_inner.left + SQ_SIZE * 27.5
    col4 = menu_inner.left + SQ_SIZE * 30.5
    start_y = menu_inner.top + SQ_SIZE
    spacing_y = SQ_SIZE / 2

    rects = {
        "piece_minus": pygame.Rect(col3, start_y, btn_w, btn_h),
        "piece_plus": pygame.Rect(col4, start_y, btn_w, btn_h),
        "board_minus": pygame.Rect(col1, start_y, btn_w, btn_h),
        "board_plus": pygame.Rect(col2, start_y, btn_w, btn_h),
        "length_minus": pygame.Rect(col1, start_y + spacing_y * 2, btn_w, btn_h),
        "length_plus": pygame.Rect(col2, start_y + spacing_y * 2, btn_w, btn_h),
        "flag_density_minus": pygame.Rect(col1, start_y + spacing_y * 4, btn_w, btn_h),
        "flag_density_plus": pygame.Rect(col2, start_y + spacing_y * 4, btn_w, btn_h),
        "flag_order_minus": pygame.Rect(col1, start_y + spacing_y * 6, btn_w, btn_h),
        "flag_order_plus": pygame.Rect(col2, start_y + spacing_y * 6, btn_w, btn_h),
        "clock_minus": pygame.Rect(col1, start_y + spacing_y * 8, btn_w, btn_h),
        "clock_plus": pygame.Rect(col2, start_y + spacing_y * 8, btn_w, btn_h),
        # You can add more if needed
    }
    return rects


def draw_menu_labels(screen, sq_size, menu_inner):
    start_x = sq_size * 1.5
    start_y = menu_inner.top + sq_size
    spacing_y = sq_size / 2

    labels = [
#        ("piece", 0),
        ("board size", 0),
        ("path length", 2),
        ("flag density", 4),
        ("flag order", 6),
        ("clock", 8),
    ]
    for text, mult in labels:
        label = FONT_18.render(text, True, BLACK)
        screen.blit(label, (start_x, start_y + spacing_y * mult))


def opening_menu(screen, selected_piece, board_size, path_length_choice,
                 flag_density_choice, flag_order_choice, clock_selected, controls):
    menu_border, menu_inner, board_border, board_inner, right_menu_border, right_menu_inner = compute_layout()

    pygame.draw.rect(screen, BROWN, menu_border, width=1)
    pygame.draw.rect(screen, WHITE, menu_inner)

    pygame.draw.rect(screen, BROWN, right_menu_border, width=1)
    pygame.draw.rect(screen, WHITE, right_menu_inner)

    board_border = pygame.Rect(board_border.left, board_border.top, board_border.width + 8, board_border.height + 8)

    draw_menu_labels(screen, SQ_SIZE, menu_inner)

    rects = get_menu_field_rects(menu_inner, SQ_SIZE)

    # Check if current selection allows starting
    min_required = get_min_board_size(selected_piece)
    can_start = board_size >= min_required

    if can_start:
        start_rect = draw_standard_button(screen, "start", menu_inner)
    else:
        # Draw grayed-out start button
        start_rect_temp = STANDARD_BUTTONS["start"]["rect"](menu_inner)
        draw_button(screen, start_rect_temp, GRAY, "start", FONT_18)
        start_rect = start_rect_temp

        # Show warning message below start button
        warning_msg = f"minimum board: {min_required} x {min_required}"
        warn_surf = FONT_18.render(warning_msg, True, RED)
        warn_w = warn_surf.get_width()
        warn_x = start_rect.centerx - warn_w // 2
        warn_y = start_rect.bottom - 110
        screen.blit(warn_surf, (warn_x, warn_y))


    controls["start_button"] = start_rect
    controls["exit_button"] = draw_standard_button(screen, "exit", menu_inner) #exit_rect
    controls["can_start"] = can_start  # Store this for click handling

    controls["piece_minus"] = rects["piece_minus"]
    controls["piece_plus"] = rects["piece_plus"]
    controls["board_minus"] = rects["board_minus"]
    controls["board_plus"] = rects["board_plus"]
    controls["path_length_minus"] = rects["length_minus"]
    controls["path_length_plus"] = rects["length_plus"]
    controls["flag_density_minus"] = rects["flag_density_minus"]
    controls["flag_density_plus"] = rects["flag_density_plus"]
    controls["flag_order_minus"] = rects["flag_order_minus"]
    controls["flag_order_plus"] = rects["flag_order_plus"]
    controls["clock_minus"] = rects["clock_minus"]
    controls["clock_plus"] = rects["clock_plus"]

    def draw_menu_field(screen, font, minus_rect, plus_rect, value, value_y, inf_font=None, has_arrows=True):
        if has_arrows:
            txt_minus = font.render("<<", True, GREEN)
            txt_plus = font.render(">>", True, RED)
            screen.blit(txt_minus, (minus_rect.x, minus_rect.y))
            screen.blit(txt_plus, (plus_rect.x, plus_rect.y))
        if value == INFINITY_SYMBOL and inf_font is not None:
            value_txt = inf_font.render(value, True, BLACK)
        else:
            value_txt = font.render(str(value), True, BLACK)
        tw = value_txt.get_width()
        center_x = (minus_rect.right + plus_rect.left) // 2
        txt_x = center_x - tw // 2
        screen.blit(value_txt, (txt_x, value_y))

    fields = [
        ("piece", FONT_18, rects["piece_minus"], rects["piece_plus"], selected_piece,
         rects["piece_minus"].y, None, True),

        ("move_text", FONT_18, rects["piece_minus"], rects["piece_plus"],
         pk.get_piece_move_sets_text(selected_piece),
         rects["piece_minus"].y + SQ_SIZE,
         None, False),

        ("board", FONT_18, rects["board_minus"], rects["board_plus"], f"{board_size} x {board_size}",
         rects["board_minus"].y, None, True),

        ("length", FONT_18, rects["length_minus"], rects["length_plus"], path_length_choice,
         rects["length_minus"].y, None, True),

        ("density", FONT_18, rects["flag_density_minus"], rects["flag_density_plus"], flag_density_choice,
         rects["flag_density_minus"].y, None, True),

        ("order", FONT_18, rects["flag_order_minus"], rects["flag_order_plus"], flag_order_choice,
         rects["flag_order_minus"].y, None, True),

        ("clock", FONT_18, rects["clock_minus"], rects["clock_plus"],
         f"{clock_selected // 60}:00" if clock_selected != 0 else INFINITY_SYMBOL,
         rects["clock_minus"].y, FONT_32, True)
    ]

    for (_, font, minus_rect, plus_rect, value, value_y, inf_font, has_arrows) in fields:
        if _ == "move_text" and not value:
            continue
        draw_menu_field(screen, font, minus_rect, plus_rect, value, value_y, inf_font, has_arrows)

    board_size = board_size
    maze_path = [(0, 0)]
    knight_pos = (0, 0)
    move_nums = {}
    flags = (board_size - 1, board_size - 1)
    resignation = False

    draw_board(
        screen, board_size, maze_path, knight_pos, move_nums, flags, resignation,
        board_border.left, board_border.top,
        show_knight=True,
        show_start=True,
        show_target_num=True,
        selected_piece=selected_piece
    )


def draw_clock(
    screen,
    clock_elapsed,
    clock_selected,
    x=None,
    y=None
):
    rem = remaining_for(clock_selected, clock_elapsed)
    if rem is None:
        text = format_clock_seconds(clock_elapsed or 0)
    else:
        text = format_clock_seconds(rem)

    clock_surf = FONT_18.render(text, True, BLACK)

    screen.blit(clock_surf, (x, y))


def draw_moves(screen, move_count, menu_inner):
    moves_label = "move" if move_count == 1 else "moves"
    moves_surf = FONT_18.render(f"{move_count} {moves_label}", True, BLACK)
    mw, mh = moves_surf.get_size()
    mx = (menu_inner.left + SQ_SIZE * 29.5) - mw / 2
    my = menu_inner.top + SQ_SIZE * 10
    screen.blit(moves_surf, (mx, my))


def draw_flags(screen, flags_count, menu_inner, flags):
    flags_label = "flag" if flags_count == 1 else "flags"
    flags_surf = FONT_18.render(f"{flags_count} of {len(flags)} {flags_label}", True, BLACK)
    fw, fh = flags_surf.get_size()
    fx = (menu_inner.left + SQ_SIZE * 29.5) - fw / 2
    fy = menu_inner.top + SQ_SIZE * 11
    screen.blit(flags_surf, (fx, fy))


def draw_selection_summary_fields(
    screen,
    rects,
    selected_piece,
    board_size,
    path_length_choice,
    flag_density_choice,
    flag_order_choice,
    font_18,
    pk,
):
    """
    Draws all main selection summary fields (piece, move text, board, length, density, order, clock)
    with color coding, centered and aligned exactly like in opening_menu.
    """

    # 1. Piece
    piece_surface = font_18.render(selected_piece, True, BLACK)
    piece_minus = rects["piece_minus"]
    piece_plus = rects["piece_plus"]
    piece_x = (piece_minus.right + piece_plus.left) // 2 - piece_surface.get_width() // 2
    piece_y = piece_minus.y
    screen.blit(piece_surface, (piece_x, piece_y))

    # 2. Move set description row (optional)
    move_text = pk.get_piece_move_sets_text(selected_piece)
    if move_text:
        moves_surface = font_18.render(move_text, True, BLACK)
        # Place it halfway between piece and board lines
        moves_y = piece_minus.y + SQ_SIZE #(rects["board_minus"].y - piece_minus.y) // 2
        moves_x = (piece_minus.right + piece_plus.left) // 2 - moves_surface.get_width() // 2
        screen.blit(moves_surface, (moves_x, moves_y))

    # 3. Board size
    board_value = f"{board_size} x {board_size}"
    board_surface = font_18.render(board_value, True, BLACK)
    board_minus = rects["board_minus"]
    board_plus = rects["board_plus"]
    board_x = (board_minus.right + board_plus.left) // 2 - board_surface.get_width() // 2
    board_y = board_minus.y
    screen.blit(board_surface, (board_x, board_y))

    # 4. Path length (color coded: GREEN for "short", RED otherwise)
    path_color = GREEN if str(path_length_choice) == "short" else RED
    length_surface = font_18.render(str(path_length_choice), True, path_color)
    length_minus = rects["length_minus"]
    length_plus = rects["length_plus"]
    length_x = (length_minus.right + length_plus.left) // 2 - length_surface.get_width() // 2
    length_y = length_minus.y
    screen.blit(length_surface, (length_x, length_y))

    # 5. Flag density (GREEN for "low", RED otherwise)
    dens_color = GREEN if str(flag_density_choice) == "low" else RED
    density_surface = font_18.render(str(flag_density_choice), True, dens_color)
    density_minus = rects["flag_density_minus"]
    density_plus = rects["flag_density_plus"]
    density_x = (density_minus.right + density_plus.left) // 2 - density_surface.get_width() // 2
    density_y = density_minus.y
    screen.blit(density_surface, (density_x, density_y))

    # 6. Order (GREEN for "any", RED for "only")
    order_text = "any" if flag_order_choice else "only"
#    ord_color = GREEN if order_text == "any" else RED
    ord_color = GREEN if str(flag_order_choice) == "any" else RED
    order_surface = font_18.render(str(flag_order_choice), True, ord_color)
#    order_surface = font_18.render(order_text, True, ord_color)
    flag_order_minus = rects["flag_order_minus"]
    flag_order_plus = rects["flag_order_plus"]
    order_x = (flag_order_minus.right + flag_order_plus.left) // 2 - order_surface.get_width() // 2
    order_y = flag_order_minus.y
    screen.blit(order_surface, (order_x, order_y))


def _wrap_text_to_width(text, font, max_width):
    if text is None:
        return []
    text = str(text)
    if text == "":
        return [""]
    words = text.split(" ")
    lines = []
    current = ""
    for w in words:
        candidate = w if current == "" else current + " " + w
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            if font.size(w)[0] > max_width:
                part = ""
                for ch in w:
                    if font.size(part + ch)[0] <= max_width:
                        part += ch
                    else:
                        if part:
                            lines.append(part)
                        part = ch
                if part:
                    current = part
                else:
                    current = ""
            else:
                current = w
    if current:
        lines.append(current)
    return lines


def draw_board(
    screen, board_size, maze_path, knight_pos, move_nums, flags, resignation, board_left, board_top,
    show_knight=True, show_start=True, show_target_num=True, selected_piece='knight'
):

    now = time.time()
    path_set = set(maze_path)

    board_border = pygame.Rect(board_left, board_top, board_size * SQ_SIZE + 2,
                               board_size * SQ_SIZE + 2)

    pygame.draw.rect(screen, BROWN, board_border, width=1)

    board_inner = pygame.Rect(
        board_border.left + 1,
        board_border.top + 1,
        board_size * SQ_SIZE,
        board_size * SQ_SIZE
    )

 #   pygame.draw.rect(screen, WHITE, board_inner)

    for y in range(board_size):
        for x in range(board_size):
            rect = pygame.Rect(board_inner.left + x * SQ_SIZE, board_inner.top + y * SQ_SIZE, SQ_SIZE, SQ_SIZE)
            color = LIGHT_SQUARE if (x + y) % 2 == 0 else DARK_SQUARE
            if (x, y) in flags:
                color = PURPLE
            elif (x, y) in move_nums and (x, y) != knight_pos:
                color = LIGHT_MOVE if (x + y) % 2 == 0 else DARK_MOVE
            elif resignation and (x, y) != knight_pos and (x, y) in path_set:
                color = PURPLE

            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, BROWN, rect, 1)

            if show_knight and (x, y) == knight_pos:
                pk.draw_piece(screen, rect, selected_piece)
            if (x, y) in move_nums and (show_target_num or (x, y) != target) and (x, y) != knight_pos:
                move_str = str(move_nums[(x, y)])
                txt = FONT_20.render(move_str, True, WHITE if color == DARK_MOVE else BLACK)
                tw, th = txt.get_size()
                txt_x = rect.x + (rect.width - tw) // 2
                txt_y = rect.y + (rect.height - th) // 2
                screen.blit(txt, (txt_x, txt_y))
            if show_start and resignation and (x, y) == maze_path[0]:
                txt = FONT_20.render("s", True, BLACK)
                tw, th = txt.get_size()
                txt_x = rect.x + (rect.width - tw) // 2
                txt_y = rect.y + (rect.height - th) // 2
                screen.blit(txt, (txt_x, txt_y))

    return None


def draw_endgame(
        screen, board_size, maze_path, flags, board_top,
        board_left, end_state="all_flags_reached",
        knight_pos=None, move_nums=None, move_count=0, selected_piece='knight',
        path_length_choice="short",
        flag_density_choice="low",
        flag_order_choice="any",
        clock_selected=0,
        clock_elapsed=0,
        resignation=False,
        flags_reached=None,
):
    screen.fill(BACK_COLOR)

    menu_border, menu_inner, board_border, board_inner, right_menu_border, right_menu_inner = compute_layout()
    rects = get_menu_field_rects(menu_inner, SQ_SIZE)

#    path_nums = {sq: i for i, sq in enumerate(maze_path)}

    draw_board(
        screen, board_size, [], knight_pos,  move_nums, flags, resignation,
        board_left, board_top,
        show_knight=True,
        show_start=False,  # as desired
        show_target_num=True,
        selected_piece=selected_piece
    )

    menu_border, menu_inner, board_border, board_inner, right_menu_border, right_menu_inner = compute_layout()
    pygame.draw.rect(screen, BROWN, menu_border, width=1)
    pygame.draw.rect(screen, WHITE, menu_inner)

    pygame.draw.rect(screen, BROWN, right_menu_border, width=1)
    pygame.draw.rect(screen, WHITE, right_menu_inner)

    start_y = menu_inner.top + SQ_SIZE

    draw_menu_labels(screen, SQ_SIZE, menu_inner)

    draw_selection_summary_fields(
        screen,
        rects,
        selected_piece,
        board_size,
        path_length_choice,
        flag_density_choice,
        flag_order_choice,
        FONT_18,
        pk,
    )


    if end_state == "all_flags_reached":
        flags_count = len(flags_reached) if flags_reached else 0
    else:
        move_count = max(move_nums.values(), default=0) if move_nums else 0
        flags_count = len(flags_reached)

    draw_moves(screen, move_count, menu_inner)
    draw_flags(screen, flags_count, menu_inner, flags)


    remaining = remaining_for(clock_selected, clock_elapsed)
    if remaining is None:
        right_clock_text = format_clock_seconds(clock_elapsed)
    else:
        right_clock_text = format_clock_seconds(remaining)

    clock_minus = rects["clock_minus"]
    clock_plus = rects["clock_plus"]
    clock_surf = FONT_18.render("00:00", True, (0, 0, 0))
    clock_x = (clock_minus.right + clock_plus.left) // 2
    clock_y = clock_minus.y

    draw_clock(
        screen,
        clock_elapsed,
        clock_selected,
        x=clock_x - (clock_surf.get_width() // 2),
        y=clock_y
    )


    endgame_messages = {
        'all_flags_reached': 'all flags reached',
        'no_moves': 'no legal moves',
        'resignation': 'resigned',
        "timeout": "time's up"
    }
    end_reason = endgame_messages[end_state]

    endgame_colors = {
        'resigned': (255, 0, 0),
        'no legal moves': (255, 0, 0),
        'all flags reached': (0, 128, 0),
        "time's up": (0, 0, 255)
    }

    endgame_color = endgame_colors.get(end_reason, (255, 0, 0))

    msg_txt = FONT_18.render(str(end_reason), True, endgame_color)
    msg_tw, msg_th = msg_txt.get_size()
    msg_x = (menu_inner.left + SQ_SIZE * 29.5) - msg_tw / 2
    msg_y = start_y + SQ_SIZE * 7
    screen.blit(msg_txt, (msg_x, msg_y))


    draw_standard_button(screen, "replay", menu_inner)
    draw_standard_button(screen, "newgame", menu_inner)
    draw_standard_button(screen, "exit", menu_inner)


def menu_loop(screen, width, height, preset=None):
    if preset:
        selected_piece = preset.get("piece", "knight")
        board_size = preset["board_size"]
        path_length_choice = preset.get("path_length_choice", 1)
        flag_density_choice = preset.get("flag_density_choice", 1)
        flag_order_choice = preset.get("flag_order_choice", 1)
        clock_selected = preset.get("clock_selected", CLOCK_DEFAULT)
    else:
        selected_piece = "knight"
        board_size = BOARD_DEFAULT
        path_length_choice = "short"
        flag_density_choice = "low"
        flag_order_choice = "any"
        clock_selected = CLOCK_DEFAULT

    controls = {
        "board_minus": pygame.Rect(0, 0, 0, 0),
        "board_plus": pygame.Rect(0, 0, 0, 0),
        "path_length_minus": pygame.Rect(0, 0, 0, 0),
        "path_length_plus": pygame.Rect(0, 0, 0, 0),
        "flag_density_minus": pygame.Rect(0, 0, 0, 0),
        "flag_density_plus": pygame.Rect(0, 0, 0, 0),
        "flag_order_minus": pygame.Rect(0, 0, 0, 0),
        "flag_order_plus": pygame.Rect(0, 0, 0, 0),
        "clock_minus": pygame.Rect(0, 0, 0, 0),
        "clock_plus": pygame.Rect(0, 0, 0, 0),
        "start_button": pygame.Rect(0, 0, 0, 0),
        "exit_button": pygame.Rect(0, 0, 0, 0),
        "piece_minus": pygame.Rect(0, 0, 0, 0),
        "piece_plus": pygame.Rect(0, 0, 0, 0)
    }

    try:
        piece_index = pk.PIECE_LIST.index(selected_piece)
    except ValueError:
        piece_index = 0
        selected_piece = pk.PIECE_LIST[0]

    while True:
        screen.fill(BACK_COLOR)

        opening_menu(screen, selected_piece, board_size, path_length_choice,
                     flag_density_choice, flag_order_choice,
                     clock_selected, controls)

        pygame.display.flip()

        for ev in pygame.event.get():
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_m:
                    pygame.display.iconify()
            if ev.type == pygame.QUIT:
                return None
            if ev.type == pygame.VIDEORESIZE:
                width, height = ev.w, ev.h
                screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
                screen.fill(BACK_COLOR)
                pygame.display.flip()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                _mb, _mi, _bb, board_inner, right_menu_border, right_menu_inner = compute_layout()
#                grid_x = (mx - board_inner.left) // SQ_SIZE
#                grid_y = (my - board_inner.top) // SQ_SIZE
#                click_square = (grid_x, grid_y)

                # Handle exit and resign buttons as before
                if controls["exit_button"].collidepoint(mx, my):
                    return None
#                elif controls["exit_button"].collidepoint(mx, my):
#                    resignation = True



                if controls["board_plus"].collidepoint(mx, my):
                    if board_size < BOARD_MAX:
                        board_size += 1
                    else:
                        board_size = BOARD_MIN

                elif controls["board_minus"].collidepoint(mx, my):
                    if board_size > BOARD_MIN:
                        board_size -= 1
                    else:
                        board_size = BOARD_MAX

                current_idx = PATH_LENGTH_CHOICES.index(path_length_choice)
                if controls["path_length_plus"].collidepoint(mx, my):
                    path_length_choice = PATH_LENGTH_CHOICES[(current_idx + 1) % len(PATH_LENGTH_CHOICES)]
                elif controls["path_length_minus"].collidepoint(mx, my):
                    path_length_choice = PATH_LENGTH_CHOICES[(current_idx - 1) % len(PATH_LENGTH_CHOICES)]


                current_idx = FLAG_DENSITY_CHOICES.index(flag_density_choice)
                if controls["flag_density_plus"].collidepoint(mx, my):
                    flag_density_choice = FLAG_DENSITY_CHOICES[(current_idx + 1) % len(FLAG_DENSITY_CHOICES)]
                elif controls["flag_density_minus"].collidepoint(mx, my):
                    flag_density_choice = FLAG_DENSITY_CHOICES[(current_idx - 1) % len(FLAG_DENSITY_CHOICES)]

                current_idx = FLAG_ORDER_CHOICES.index(flag_order_choice)
                if controls["flag_order_plus"].collidepoint(mx, my):
                    flag_order_choice = FLAG_ORDER_CHOICES[(current_idx + 1) % len(FLAG_ORDER_CHOICES)]
                elif controls["flag_order_minus"].collidepoint(mx, my):
                    flag_order_choice = FLAG_ORDER_CHOICES[(current_idx - 1) % len(FLAG_ORDER_CHOICES)]

                elif controls["clock_plus"].collidepoint(mx, my):
                    if clock_selected < 30 * 60:
                        clock_selected += 60
                    else:
                        clock_selected = 0
                elif controls["clock_minus"].collidepoint(mx, my):
                    if clock_selected > 0:
                        clock_selected -= 60
                    else:
                        clock_selected = 30 * 60

                elif controls["piece_minus"].collidepoint(mx, my):
                    if piece_index > 0:
                        piece_index -= 1
                    else:
                        piece_index = len(pk.PIECE_LIST) - 1
                    selected_piece = pk.PIECE_LIST[piece_index]

                elif controls["piece_plus"].collidepoint(mx, my):
                    if piece_index < len(pk.PIECE_LIST) - 1:
                        piece_index += 1
                    else:
                        piece_index = 0
                    selected_piece = pk.PIECE_LIST[piece_index]

                elif controls["start_button"].collidepoint(mx, my):
                    # Only allow starting if validation passed
                    if controls.get("can_start", True):
                        return {
                            "piece": selected_piece,
                            "board_size": board_size,
                            "path_length_choice": path_length_choice,
                            "flag_density_choice": flag_density_choice,
                            "flag_order_choice": flag_order_choice,
                            "clock_selected": clock_selected,
                            "width": width,
                            "height": height

                        }

                elif controls["exit_button"].collidepoint(mx, my):
                    return None

def run_game(screen, params):
    controls = {}

    # --- BOARD LAYOUT COMPUTATION ---
    menu_border, menu_inner, board_border, board_inner, right_menu_border, right_menu_inner = compute_layout()
    rects = get_menu_field_rects(menu_inner, SQ_SIZE)

    board_left = board_border.left
    board_top = board_border.top

    selected_piece = params.get("piece", "knight")
    board_size = params["board_size"]
    path_length_choice = params["path_length_choice"]
    flag_density_choice = params["flag_density_choice"]
    flag_order_choice = params["flag_order_choice"]
    clock_selected = params["clock_selected"]

    n = board_size
    multiplier = PATH_LENGTH_MAP[path_length_choice]

    min_length = max(n, int(n * multiplier))
    max_length = min(n * n, int(n * multiplier * 2))

    flags_reached = set()
    flags_count = 0

    from gameboard import BoardModel, BoardRenderer
    board_model = BoardModel(n, n)
    board_origin = (board_left, board_top)
    board_renderer = BoardRenderer(board_model, SQ_SIZE, board_origin)

    move_func = pk.get_move_func(selected_piece)

    maze_path, flags = generate_open_path_with_flags(
        board_size, min_length, max_length, move_func=move_func,
        max_attempts=200, time_budget=1.0,
        flag_density_choice=flag_density_choice
    )

    flag_ordinals = {pos: idx + 1 for idx, pos in enumerate(flags)}

    # Remove starting square from flags
    if maze_path and flags:
        start = maze_path[0]
        flags = [flag for flag in flags if flag != start]

    if not maze_path or len(maze_path) <= 4:
        error_font = pygame.font.SysFont("arial", 30)
        error_msg = "Failed to generate maze."
        error_msg2 = "Returning to menu..."
        screen.fill(BACK_COLOR)
        msg1_surf = error_font.render(error_msg, True, RED)
        msg2_surf = error_font.render(error_msg2, True, BLACK)
        screen.blit(msg1_surf, (SQ_SIZE * 10, SQ_SIZE * 8))
        screen.blit(msg2_surf, (SQ_SIZE * 10, SQ_SIZE * 9.5))
        pygame.display.flip()
        pygame.time.wait(2000)
        return "newgame"

    knight_pos = maze_path[0]
    move_nums = {knight_pos: 0}
    move_count = 0

    clock_start = None
    paused_elapsed = 0
    paused_due_to_minimize = False

    resignation = False
    running = True
    endgame = False
    end_state = None

    while running:
        screen.fill(BACK_COLOR)

        now = time.time()
        if clock_start is None:
            clock_elapsed = int(paused_elapsed)
        else:
            clock_elapsed = int(paused_elapsed + (now - clock_start))

        menu_border, menu_inner, board_border, board_inner, right_menu_border, right_menu_inner = compute_layout()

        pygame.draw.rect(screen, BROWN, menu_border, width=1)
        pygame.draw.rect(screen, WHITE, menu_inner)

        pygame.draw.rect(screen, BROWN, right_menu_border, width=1)
        pygame.draw.rect(screen, WHITE, right_menu_inner)

        draw_menu_labels(screen, SQ_SIZE, menu_inner)

        draw_selection_summary_fields(
            screen,
            rects,
            selected_piece,
            board_size,
            path_length_choice,
            flag_density_choice,
            flag_order_choice,
            FONT_18,
            pk,
        )

        draw_moves(screen, move_count, menu_inner)
        draw_flags(screen, flags_count, menu_inner, flags)

        clock_minus = rects["clock_minus"]
        clock_plus = rects["clock_plus"]
        clock_surf = FONT_18.render("00:00", True,
                                    (0, 0, 0))  # Width used for centering
        clock_x = (clock_minus.right + clock_plus.left) // 2

        # Vertically align at the top of the rect
        clock_y = clock_minus.y

        draw_clock(
            screen,
            clock_elapsed,
            clock_selected,
            x=clock_x - (clock_surf.get_width() // 2),
            y=clock_y
        )

        # Draw main board
        draw_board(
            screen, board_size, maze_path, knight_pos, move_nums, flags,
            resignation, board_left, board_top,
            show_knight=True,
            show_start=True,
            show_target_num=True,
            selected_piece=selected_piece
        )

        # Check for endgame after all moves/events:
        if not endgame:
            # Win if all flags reached
            if len(flags_reached) == len(flags):
                end_state = "all_flags_reached"
                endgame = True
            else:
                move_func = pk.get_move_func(selected_piece)
                move_set = move_func(*knight_pos, n)
                legal_moves = [sq for sq in move_set if sq not in move_nums]
                if not legal_moves:
                    end_state = "no_moves"
                    endgame = True
                elif resignation:
                    end_state = "resignation"
                    endgame = True
                elif clock_has_expired(clock_selected, clock_elapsed):
                    end_state = "timeout"
                    endgame = True

        # Draw gameplay buttons and assign their rects
        controls["move_guide_button"] = draw_standard_button(screen, "move_guide", menu_inner)
        controls["resign_button"] = draw_standard_button(screen, "resign", menu_inner)
        controls["exit_button"] = draw_standard_button(screen, "exit", menu_inner)

        pygame.display.flip()

        # --- ENDGAME SCREEN ---
        if endgame:
            final_elapsed = (
                paused_elapsed if clock_start is None else
                int(paused_elapsed + (time.time() - clock_start))
            )
            end_knight_pos = knight_pos #maze_path[-1] if end_state == "win" else knight_pos

            controls["replay_button"] = draw_standard_button(screen, "replay", menu_inner)
            controls["newgame_button"] = draw_standard_button(screen, "newgame", menu_inner)
            controls["exit_button"] = draw_standard_button(screen, "exit", menu_inner)

            endgame_args = dict(
                screen=screen,
                board_size=board_size,
                maze_path=maze_path,
                flags=flags,
                board_top=board_top,
                board_left=board_left,
                end_state=end_state,
                knight_pos=end_knight_pos,
                move_nums=move_nums,
                move_count=move_count,
                selected_piece=selected_piece,
                path_length_choice=path_length_choice,
                flag_density_choice=flag_density_choice,
                flag_order_choice=flag_order_choice,
                clock_selected=clock_selected,
                clock_elapsed=final_elapsed,
                resignation=resignation,
                flags_reached=flags_reached,
            )

            draw_endgame(**endgame_args)

            pygame.display.flip()
            while True:
                for event2 in pygame.event.get():
                    if event2.type == pygame.KEYDOWN:
                        if event2.key == pygame.K_m:
                            pygame.display.iconify()
                    if event2.type == pygame.QUIT:
                        return None
                    if event2.type == pygame.VIDEORESIZE:
                        width, height = event2.w, event2.h
                        screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
                        screen.fill(BACK_COLOR)

                        draw_endgame(**endgame_args)
                        pygame.display.flip()

                    elif event2.type == pygame.ACTIVEEVENT:
                        if getattr(event2, "gain", None) == 1 and getattr(event2, "state", None) == 1:
                            draw_endgame(**endgame_args)
                            pygame.display.flip()
                    elif event2.type == pygame.MOUSEBUTTONDOWN:
                        mx, my = event2.pos
                        if controls["replay_button"].collidepoint(mx, my):
                            return "replay"
                        elif controls["newgame_button"].collidepoint(mx, my):
                            screen.fill(BACK_COLOR)
                            pygame.display.flip()
                            return "newgame"
                        elif controls["exit_button"].collidepoint(mx, my):
                            return None
                pygame.time.wait(10)
        else:
            # --- GAMEPLAY EVENTS ---
            for ev in pygame.event.get():
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_m:
                        pygame.display.iconify()
                if ev.type == pygame.QUIT:
                    return None
                if ev.type == pygame.VIDEORESIZE:
                    width, height = ev.w, ev.h
                    screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
                    screen.fill(BACK_COLOR)
                elif ev.type == pygame.ACTIVEEVENT:
                    state = getattr(ev, "state", 0)
                    gain = getattr(ev, "gain", 0)
                    if state & 4:
                        if gain == 0:
                            if clock_start is not None:
                                paused_elapsed += (time.time() - clock_start)
                                clock_start = None
                                paused_due_to_minimize = True
                        elif gain == 1:
                            if paused_due_to_minimize and not endgame:
                                clock_start = time.time()
                                paused_due_to_minimize = False
                elif ev.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = ev.pos

                    # --- Always allow exit and resign ---
                    if controls.get("exit_button") and controls["exit_button"].collidepoint(mx, my):
                        return None
                    if controls.get("resign_button") and controls["resign_button"].collidepoint(mx, my):
                        resignation = True

                    # --- Only allow movement if not resigned ---
                    if not resignation:
                        _mb, _mi, _bb, board_inner, right_menu_border, right_menu_inner = compute_layout()
                        grid_x = (mx - board_inner.left) // SQ_SIZE
                        grid_y = (my - board_inner.top) // SQ_SIZE
                        click_square = (grid_x, grid_y)
                        move_func = pk.get_move_func(selected_piece)
                        move_set = move_func(*knight_pos, n)
                        if (0 <= grid_x < n and 0 <= grid_y < n
                            and click_square in move_set
                            and click_square not in move_nums
                        ):

                            if clock_start is None:
                                clock_start = time.time()

                            knight_pos = click_square
                            move_count += 1
                            move_nums[knight_pos] = move_count

                            if click_square in flags and click_square not in flags_reached:
                                flags_reached.add(click_square)
                                flags_count += 1

            pygame.time.wait(10)

    return None


def main():
    pygame.display.set_caption("Capture the Flags v1")
    safe_width, safe_height = 800, 600
    screen = pygame.display.set_mode((safe_width, safe_height), pygame.RESIZABLE)
    maximize_window()


    pk.load_images(pieces_dir)


    screen.fill(BACK_COLOR)
    pygame.display.flip()

    menu_params = None
    settings = menu_loop(screen, safe_width, safe_height, preset=menu_params)
    if not settings:
        return
    menu_params = dict(settings)

    while True:
        result = run_game(screen, menu_params)
        if result == "newgame":
            settings = menu_loop(screen, safe_width, safe_height, preset=menu_params)
            if not settings:
                break
            menu_params = dict(settings)
            continue
        elif result == "replay":
            continue
        else:
            break


if __name__ == "__main__":
    main()
