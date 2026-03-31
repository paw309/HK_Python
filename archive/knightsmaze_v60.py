# This file is knights_maze_v60.py
# It uses the new piecekeeper module for piece metadata, move generation, and image handling.

import random
import time

import pygame
import sys

import piecekeeper as pk

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
image_dir_path = os.path.join(BASE_DIR, "assets")
pieces_dir    = os.path.join(BASE_DIR, "assets", "pieces")
arrows_dir    = os.path.join(BASE_DIR, "assets", "arrows")
markers_dir   = os.path.join(BASE_DIR, "assets", "markers")

pygame.init()

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

font_16 = pygame.font.SysFont("arial", 16)
font_18 = pygame.font.SysFont("arial", 18)
font_20 = pygame.font.SysFont("arial", 20)
font_32 = pygame.font.SysFont("arial", 32)


PATH_LENGTH_MAP = {
    "short": 1,
    "medium": 2,
    "long": 4
}


PIECE_MIN_BOARD_SIZE_FOR_MAZE = {
    "knight": 5,
    "king": 5,
    "queen": 5,
    "rook": 5,
    "bishop": 5,
    "gamma": 5,
    "delta": 5,
    "theta": 5,
    "lambda": 8,
    "xi": 5,
    "pi": 5,
    "sigma": 5,
    "phi": 8,
    "psi": 8,
    "omega": 8,
    "mercury": 5,
    "venus": 5,
    "earth": 5,
    "mars": 5,
    "jupiter": 5,
    "saturn": 5,
    "uranus": 5,
    "neptune": 5,
    "ceres": 5,
    "pallas": 8,
    "pluto": 16,
    "leo": 5,
    "virgo": 5,
    "libra": 5,
    "scorpio": 6,
    "sagittarius": 5,
    "capricorn": 5,
    "fibonacci": 5,
    "gunkan": 5,
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


def display_for_selection(clock_selected_seconds):
    if clock_selected_seconds == 0:
        return INFINITY_SYMBOL
    return format_clock_seconds(clock_selected_seconds)


def remaining_for(clock_selected_seconds, clock_elapsed_seconds):
    if clock_selected_seconds == 0:
        return None
    return max(0, int(clock_selected_seconds) - int(clock_elapsed_seconds or 0))


def clock_has_expired(clock_selected_seconds, clock_elapsed_seconds):
    if clock_selected_seconds == 0:
        return False
    return int(clock_elapsed_seconds or 0) >= int(clock_selected_seconds)


# button definitions

button_ht = SQ_SIZE * .75

STANDARD_BUTTONS = {
    "start": {
        "color": BLUE,
        "text": "start",
        "rect": lambda menu_inner: pygame.Rect(SQ_SIZE * 3, menu_inner.top + SQ_SIZE * 12.25,
                                               SQ_SIZE * 4, button_ht),
    },

    "guide": {
        "color": GREEN,
        "text": "move guide (dummy)",
        "rect": lambda menu_inner: pygame.Rect(SQ_SIZE * 3, menu_inner.top + SQ_SIZE * 12.25,
                                               SQ_SIZE * 4, button_ht),
    },

    "replay": {
        "color": BLUE,
        "text": "play again",
        "rect": lambda menu_inner: pygame.Rect(SQ_SIZE * 3, menu_inner.top + SQ_SIZE * 12.25,
                                               SQ_SIZE * 4, button_ht),
    },

    "resign": {
        "color": GRAY,
        "text": "resign",
        "rect": lambda menu_inner: pygame.Rect(SQ_SIZE * 3, menu_inner.top + SQ_SIZE * 13.5,
                                          SQ_SIZE * 4, button_ht),
    },

    "menu": {
        "color": GREEN,
        "text": "new game",
        "rect": lambda menu_inner: pygame.Rect(SQ_SIZE * 3, menu_inner.top + SQ_SIZE * 13.5,
                                               SQ_SIZE * 4, button_ht),
    },

    "exit": {
        "color": RED,
        "text": "exit",
        "rect": lambda menu_inner: pygame.Rect(SQ_SIZE * 6, menu_inner.top + SQ_SIZE * 14.75,
                                               SQ_SIZE * 2, button_ht),
    },

}

MAZE_TYPE_CHOICES = ["walled", "open"]
PATH_LENGTH_CHOICES = ["short", "medium", "long"]


def maximize_window():
    if sys.platform.startswith("win"):
        hwnd = pygame.display.get_wm_info().get('window')
        if hwnd:
            try:
                import ctypes
                ctypes.windll.user32.ShowWindow(hwnd, 3)
            except Exception as e:
                print("Could not maximize window:", e)


# generate maze path

def generate_path_and_obstacles(n, min_length, max_length, move_func, obstacles=None, start=None):
    squares = [(x, y) for x in range(n) for y in range(n)]
    if start is None:
        start = random.choice(squares)
    path = [start]
    path_set = {start}
    obstacles = obstacles or set()

    while len(path) < max_length:
        current = path[-1]
        moves = [move for move in move_func(*current, n) if move not in path_set and move not in obstacles]
        if not moves:
            break
        next_square = random.choice(moves)
        path.append(next_square)
        path_set.add(next_square)
        obstacles.update({sq for sq in moves if sq != next_square and sq not in obstacles and sq not in path_set})

    if min_length <= len(path) <= max_length:
        return path, obstacles
    else:
        return None, None


def generate_maze_path_and_obstacles(
        n,
        min_length=None,
        max_length=None,
        move_func=None,
        max_attempts=None,
        time_budget=None
):
    if move_func is None:
        move_func = pk.get_move_func("knight")

    if min_length is None:
        min_length = n + 1
    if max_length is None:
        max_length = n * 2

    squares = [(x, y) for x in range(n) for y in range(n)]
    lowest_min_length = max(2, n // 2)

    for attempt_min_length in range(min_length, lowest_min_length - 1, -1):
        attempts = 0
        start_time = time.time() if time_budget is not None else None
        while True:
            if max_attempts is not None and attempts >= max_attempts:
                break
            if time_budget is not None and (time.time() - start_time) > time_budget:
                break

            attempts += 1
            start = random.choice(squares)
            path, obstacles = generate_path_and_obstacles(
                n, attempt_min_length, max_length, move_func, start=start
            )
            if path:
                return path, obstacles

    return None, None


def min_moves_between(start, target, move_func, n):
    """Breadth-first search: returns minimum number of moves from start to target or float('inf') if not reachable."""
    from collections import deque
    visited = set()
    queue = deque([(start, 0)])
    while queue:
        current, dist = queue.popleft()
        if current == target:
            return dist
        for m in move_func(*current, n):
            if m not in visited:
                visited.add(m)
                queue.append((m, dist+1))
    return float('inf')

def generate_open_maze_path_and_obstacles(
        n,
        min_length=None,
        max_length=None,
        move_func=None,
        max_attempts=None,
        time_budget=None
):
    if move_func is None:
        move_func = pk.get_move_func("knight")
    if min_length is None:
        min_length = n + 1
    if max_length is None:
        max_length = n * 2
    squares = [(x, y) for x in range(n) for y in range(n)]
    # Pick a random target square for each attempt
    start_time = time.time() if time_budget is not None else None
    for attempt in range(max_attempts or 1000):
        if time_budget is not None and (time.time() - start_time) > time_budget:
            break
        target = random.choice(squares)
        # Only consider starts >= 3 moves away from target
        far_starts = [
            sq for sq in squares if min_moves_between(sq, target, move_func, n) >= 3
        ]
        if not far_starts:
            continue
        start = random.choice(far_starts)
        path = [start]
        path_set = {start}
        while len(path) < max_length:
            current = path[-1]
            moves = [move for move in move_func(*current, n) if move not in path_set]
            # Check if we can legally reach target from current and add it as soon as legal
            if target in move_func(*current, n) and target not in path_set:
                path.append(target)
                path_set.add(target)
                break
            if not moves:
                break
            next_square = random.choice(moves)
            path.append(next_square)
            path_set.add(next_square)
        if (
            len(path) >= min_length and
            path[-1] == target and
            all(sq in path_set for sq in [start, target])
        ):
            obstacles = set(squares) - set(path)
            return path, obstacles
    return None, None

# helper: compute the menu and board border/inner rectangles
def compute_layout():
    menu_border = pygame.Rect(SQ_SIZE, SQ_SIZE, PANEL_W + SQ_SIZE / 8, PANEL_H)
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


def draw_button(screen, rect, color, label, font=font_18):
    pygame.draw.rect(screen, color, rect)
    txt = font.render(label, True, WHITE)
    tw = txt.get_width()
    th = txt.get_height()
    screen.blit(txt, (rect.x + (rect.width - tw) // 2, rect.y + (rect.height - th) // 2))


def draw_standard_button(screen, button_name, menu_inner, font=font_18):
    properties = STANDARD_BUTTONS[button_name]
    rect = properties["rect"](menu_inner)
    draw_button(screen, rect, properties["color"], properties["text"], font)
    return rect


def draw_menu_labels(screen, sq_size, menu_inner):
    start_x = sq_size * 2
    start_y = menu_inner.top + sq_size
    spacing_y = sq_size / 2

    labels = [
        ("board", 0),
        ("type", 2),
        ("length", 4),
        ("blocks", 6),
        ("bounce", 8),
        ("clock", 10),
    ]
    for text, mult in labels:
        label = font_18.render(text, True, BLACK)
        screen.blit(label, (start_x, start_y + spacing_y * mult))


def opening_menu(screen, selected_piece, board_size, maze_type_choice, path_length_choice,
                 obstacles_visible, return_to_start, clock_selected, controls):
    menu_border, menu_inner, board_border, board_inner, right_menu_border, right_menu_inner = compute_layout()

    pygame.draw.rect(screen, BROWN, menu_border, width=1)
    pygame.draw.rect(screen, WHITE, menu_inner)

    pygame.draw.rect(screen, BROWN, right_menu_border, width=1)
    pygame.draw.rect(screen, WHITE, right_menu_inner)

    board_size = board_size
    maze_path = [(0, 0)]
    obstacles = {}
    knight_pos = (0, 0)
    move_nums = {}
    resignation = False
    board_left = board_border.left
    board_top = 36
    obstacle_flash_list = {}
    obstacle_permanent_red = {}


    draw_board(screen, board_size, maze_path, obstacles, knight_pos, move_nums, maze_path[0],
                       resignation, board_left, board_top,
                       obstacles_visible,
                       obstacle_flash_list=obstacle_flash_list,
                       obstacle_permanent_red=obstacle_permanent_red,
                       selected_piece=selected_piece)

    draw_menu_labels(screen, SQ_SIZE, menu_inner)

    btn_w = SQ_SIZE / 2
    btn_h = SQ_SIZE / 2
    col1 = menu_inner.left + SQ_SIZE * 3
    col2 = menu_inner.left + SQ_SIZE * 6
    col3 = menu_inner.left + SQ_SIZE * 28
    col4 = menu_inner.left + SQ_SIZE * 31

    start_y = menu_inner.top + SQ_SIZE
    spacing_y = SQ_SIZE / 2

    piece_minus_rect = pygame.Rect(col3, start_y, btn_w, btn_h)
    piece_plus_rect = pygame.Rect(col4, start_y, btn_w, btn_h)

    board_minus_rect = pygame.Rect(col1, start_y, btn_w, btn_h)
    board_plus_rect = pygame.Rect(col2, start_y, btn_w, btn_h)

    maze_minus_rect = pygame.Rect(col1, start_y + spacing_y * 2, btn_w, btn_h)
    maze_plus_rect = pygame.Rect(col2, start_y + spacing_y * 2, btn_w, btn_h)

    length_minus_rect = pygame.Rect(col1, start_y + spacing_y * 4, btn_w, btn_h)
    length_plus_rect = pygame.Rect(col2, start_y + spacing_y * 4, btn_w, btn_h)

    obstacles_minus_rect = pygame.Rect(col1, start_y + spacing_y * 6, btn_w, btn_h)
    obstacles_plus_rect = pygame.Rect(col2, start_y + spacing_y * 6, btn_w, btn_h)

    bounce_minus_rect = pygame.Rect(col1, start_y + spacing_y * 8, btn_w, btn_h)
    bounce_plus_rect = pygame.Rect(col2, start_y + spacing_y * 8, btn_w, btn_h)

    clock_minus_rect = pygame.Rect(col1, start_y + spacing_y * 10, btn_w, btn_h)
    clock_plus_rect = pygame.Rect(col2, start_y + spacing_y * 10, btn_w, btn_h)

    # Check if current selection allows starting
    min_required = get_min_board_size(selected_piece)

    can_start = board_size >= min_required

    if can_start:
        start_rect = draw_standard_button(screen, "start", menu_inner)
    else:
        # Draw grayed-out start button
        start_rect_temp = STANDARD_BUTTONS["start"]["rect"](menu_inner)
        draw_button(screen, start_rect_temp, GRAY, "start", font_18)
        start_rect = start_rect_temp

        # Show warning message below start button
        warning_msg = f"minimum board: {min_required} x {min_required}"
        warn_surf = font_18.render(warning_msg, True, RED)
        warn_w = warn_surf.get_width()
        warn_x = start_rect.centerx - warn_w // 2
        warn_y = start_rect.bottom - 110
        screen.blit(warn_surf, (warn_x, warn_y))

    exit_rect = draw_standard_button(screen, "exit", menu_inner)
    controls["start_button"] = start_rect
    controls["exit_button"] = exit_rect
    controls["can_start"] = can_start  # Store this for click handling

    controls["piece_minus"] = piece_minus_rect
    controls["piece_plus"] = piece_plus_rect
    controls["board_minus"] = board_minus_rect
    controls["board_plus"] = board_plus_rect
    controls["maze_type_minus"] = maze_minus_rect
    controls["maze_type_plus"] = maze_plus_rect
    controls["path_length_minus"] = length_minus_rect
    controls["path_length_plus"] = length_plus_rect
    controls["obstacles_minus"] = obstacles_minus_rect
    controls["obstacles_plus"] = obstacles_plus_rect
    controls["bounce_minus"] = bounce_minus_rect
    controls["bounce_plus"] = bounce_plus_rect
    controls["clock_minus"] = clock_minus_rect
    controls["clock_plus"] = clock_plus_rect


    #piece
    txt_piece_minus = font_18.render("<<", True, GREEN)
    txt_piece_plus = font_18.render(">>", True, RED)
    screen.blit(txt_piece_minus, (piece_minus_rect.x, piece_minus_rect.y))
    screen.blit(txt_piece_plus, (piece_plus_rect.x, piece_plus_rect.y))

    piece_state_txt = font_18.render(selected_piece, True, BLACK)
    tw = piece_state_txt.get_width()
    center_x = (piece_minus_rect.right + piece_plus_rect.left) // 2
    txt_x = center_x - tw // 2
    screen.blit(piece_state_txt, (txt_x, start_y))

    #move text
    move_text = pk.get_piece_move_sets_text(selected_piece)
    if move_text:
        move_surf = font_18.render(move_text, True, BLACK)
        mw, mh = move_surf.get_size()
        center_x = (piece_minus_rect.right + piece_plus_rect.left) // 2
        mx = center_x - mw // 2
        my = start_y + spacing_y * 2
        screen.blit(move_surf, (mx, my))

    #board
    txt_board_minus = font_18.render("<<", True, GREEN)
    txt_board_plus = font_18.render(">>", True, RED)
    screen.blit(txt_board_minus, (board_minus_rect.x, board_minus_rect.y))
    screen.blit(txt_board_plus, (board_plus_rect.x, board_plus_rect.y))

    txt_board = font_18.render(f"{board_size} x {board_size}", True, BLACK)
    tw = txt_board.get_width()
    center_x = (board_minus_rect.right + board_plus_rect.left) // 2
    txt_x = center_x - tw // 2
    txt_y = start_y
    screen.blit(txt_board, (txt_x, txt_y))

    #maze type
    txt_maze_minus = font_18.render("<<", True, GREEN)
    txt_maze_plus = font_18.render(">>", True, RED)
    screen.blit(txt_maze_minus, (maze_minus_rect.x, maze_minus_rect.y))
    screen.blit(txt_maze_plus, (maze_plus_rect.x, maze_plus_rect.y))

    txt_mult = font_18.render(f"{maze_type_choice}", True, BLACK)
    tw = txt_mult.get_width()
    center_x = (maze_minus_rect.right + maze_plus_rect.left) // 2
    txt_x = center_x - tw // 2
    txt_y = start_y + spacing_y * 2
    screen.blit(txt_mult, (txt_x, txt_y))


    #path length
    txt_length_minus = font_18.render("<<", True, GREEN)
    txt_length_plus = font_18.render(">>", True, RED)
    screen.blit(txt_length_minus, (length_minus_rect.x, length_minus_rect.y))
    screen.blit(txt_length_plus, (length_plus_rect.x, length_plus_rect.y))

    txt_mult = font_18.render(f"{path_length_choice}", True, BLACK)
    tw = txt_mult.get_width()
    center_x = (length_minus_rect.right + length_plus_rect.left) // 2
    txt_x = center_x - tw // 2
    txt_y = start_y + spacing_y * 4
    screen.blit(txt_mult, (txt_x, txt_y))

    #obstacles
    txt_obstacles_minus = font_18.render("<<", True, GREEN)
    txt_obstacles_plus = font_18.render(">>", True, RED)
    screen.blit(txt_obstacles_minus, (obstacles_minus_rect.x, obstacles_minus_rect.y))
    screen.blit(txt_obstacles_plus, (obstacles_plus_rect.x, obstacles_plus_rect.y))

    obs_state_txt = font_18.render("show" if obstacles_visible else "hide", True, BLACK)
    tw = obs_state_txt.get_width()
    center_x = (obstacles_minus_rect.right + obstacles_plus_rect.left) // 2
    txt_x = center_x - tw // 2
    txt_y = start_y + spacing_y * 6
    screen.blit(obs_state_txt, (txt_x, txt_y))

    #bounce
    txt_bounce_minus = font_18.render("<<", True, GREEN)
    txt_bounce_plus = font_18.render(">>", True, RED)
    screen.blit(txt_bounce_minus, (bounce_minus_rect.x, bounce_minus_rect.y))
    screen.blit(txt_bounce_plus, (bounce_plus_rect.x, bounce_plus_rect.y))

    bounce_state_txt = font_18.render("stay" if not return_to_start else "bounce", True, BLACK)
    tw = bounce_state_txt.get_width()
    center_x = (bounce_minus_rect.right + bounce_plus_rect.left) // 2
    txt_x = center_x - tw // 2
    txt_y = start_y + spacing_y * 8
    screen.blit(bounce_state_txt, (txt_x, txt_y))

    #clock
    txt_clock_minus = font_18.render("<<", True, GREEN)
    screen.blit(txt_clock_minus, (clock_minus_rect.x, clock_minus_rect.y))
    txt_plus_t = font_18.render(">>", True, RED)
    screen.blit(txt_plus_t, (clock_plus_rect.x, clock_plus_rect.y))

    if clock_selected != 0:
        clock_surf = font_18.render(f"{clock_selected // 60}:00", True, BLACK)
        tw = clock_surf.get_width()
        center_x = (clock_minus_rect.right + clock_plus_rect.left) // 2
        txt_x = center_x - tw // 2
        txt_y = start_y + spacing_y * 10
        screen.blit(clock_surf, (txt_x, txt_y))
    else:
        inf_surf = font_32.render(INFINITY_SYMBOL, True, BLACK)
        tw = inf_surf.get_width()
        center_x = (clock_minus_rect.right + clock_plus_rect.left) // 2
        txt_x = center_x - tw // 2
        txt_y = start_y + spacing_y * 10 - (font_32.get_height() - font_18.get_height()) // 2
        screen.blit(inf_surf, (txt_x, txt_y))


def draw_clock(screen, clock_elapsed_seconds, menu_inner, clock_selected_seconds):
    rem = remaining_for(clock_selected_seconds, clock_elapsed_seconds)
    if rem is None:
        text = format_clock_seconds(clock_elapsed_seconds or 0)
    else:
        text = format_clock_seconds(rem)

    clock_surf = font_18.render(text, True, BLACK)
    tx = (menu_inner.left + menu_inner.right) / 2
#    tx = (clock_minus_rect.right + clock_plus_rect.left) // 2
    ty = menu_inner.top + SQ_SIZE * 6
    screen.blit(clock_surf, (tx, ty))


def draw_moves(screen, move_count, menu_inner):
    moves_label = "move" if move_count == 1 else "moves"
    moves_surf = font_18.render(f"{move_count} {moves_label}", True, BLACK)
    mw, mh = moves_surf.get_size()
    mx = (menu_inner.left + menu_inner.right) / 2 - mw / 4
    my = menu_inner.top + SQ_SIZE * 8
    screen.blit(moves_surf, (mx, my))


def draw_attempts(screen, attempt_count, menu_inner):
    attempts_label = "block" if attempt_count == 1 else "blocks"
    attempts_surf = font_18.render(f"{attempt_count} {attempts_label}", True, BLACK)
    aw, ah = attempts_surf.get_size()
    ax = (menu_inner.left + menu_inner.right) / 2 - aw / 4
    ay = menu_inner.top + SQ_SIZE * 9
    screen.blit(attempts_surf, (ax, ay))


def draw_bounces(screen, attempt_count, menu_inner):
    attempts_label = "bounce" if attempt_count == 1 else "bounces"
    attempts_surf = font_18.render(f"{attempt_count} {attempts_label}", True, BLACK)
    aw, ah = attempts_surf.get_size()
    ax = (menu_inner.left + menu_inner.right) / 2 - aw / 4
    ay = menu_inner.top + SQ_SIZE * 6
    screen.blit(attempts_surf, (ax, ay))


def draw_selection_summary(
        screen,
        menu_inner,
        maze_type_choice,
        path_length_choice,
        obstacles_visible,
        return_to_start,
        clock_selected,
        font=font_18
):
    maze_str = f"{maze_type_choice}"
    path_str = f"{path_length_choice}"
    blocks_str = f"{'show' if obstacles_visible else 'hide'}"
    bounce_str = f"{'bounce' if return_to_start else 'stay'}"

    maze_x = len(maze_str) / 2
    path_x = len(path_str) / 2
    blocks_x = len(path_str) / 2
    bounce_x = len(path_str) / 2

    info_x = (menu_inner.left + menu_inner.right) / 2
    info_y = menu_inner.top + SQ_SIZE

    if maze_str == "walled":
        maze_color = GREEN
    else:
        maze_color = RED
    screen.blit(font.render(maze_str, True, maze_color), (info_x - maze_x, info_y + SQ_SIZE))

    if path_str == "short":
        path_color = GREEN
    else:
        path_color = RED
    screen.blit(font.render(path_str, True, path_color), (info_x - path_x, info_y + SQ_SIZE * 2))

    if blocks_str == "show":
        path_color = GREEN
    else:
        path_color = RED
    screen.blit(font.render(blocks_str, True, path_color), (info_x - blocks_x, info_y + SQ_SIZE * 3))

    if bounce_str == "stay":
        path_color = GREEN
    else:
        path_color = RED
    screen.blit(font.render(bounce_str, True, path_color), (info_x - bounce_x, info_y + SQ_SIZE * 4))


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


def draw_board(screen, board_size, maze_path, obstacles, knight_pos, move_nums, target, resign, board_left,
               board_top, obstacles_visible, show_knight=True, show_start=True, show_target_num=True,
               obstacle_flash_list=None, obstacle_permanent_red=None,
               selected_piece='knight', force_reveal_obstacles=False):
    if obstacle_permanent_red is None:
        obstacle_permanent_red = set()
    now = time.time()
    path_set = set(maze_path)

    board_border = pygame.Rect(board_left, board_top, board_size * SQ_SIZE + 2, board_size * SQ_SIZE + 2)

    pygame.draw.rect(screen, BROWN, board_border, width=1)

    board_inner = pygame.Rect(
        board_border.left + 1,
        board_border.top + 1,
        board_size * SQ_SIZE,
        board_size * SQ_SIZE
    )

    pygame.draw.rect(screen, WHITE, board_inner)

    for y in range(board_size):
        for x in range(board_size):
            rect = pygame.Rect(board_inner.left + x * SQ_SIZE, board_inner.top + y * SQ_SIZE, SQ_SIZE, SQ_SIZE)
#            color = LIGHT_SQUARE if (x + y) % 2 == 0 else DARK_SQUARE
            if (x, y) == target:
                color = PURPLE
            elif (x, y) in move_nums and (x, y) != knight_pos:
                color = LIGHT_MOVE if (x + y) % 2 == 0 else DARK_MOVE
            elif resign and (x, y) != knight_pos and (x, y) in path_set:
                color = PURPLE
            else:
                color = LIGHT_SQUARE if (x + y) % 2 == 0 else DARK_SQUARE
            if force_reveal_obstacles and (x, y) in obstacles:
                if (x, y) in obstacles:
                    if (x + y) % 2 == 0:
                        obstacle_color = LIGHT_BLOCK
                    else:
                        obstacle_color = DARK_BLOCK
                    pygame.draw.rect(screen, obstacle_color, rect)
            elif (x, y) in obstacle_permanent_red:
                if (x, y) in obstacles:
                    if (x + y) % 2 == 0:
                        obstacle_color = LIGHT_BLOCK
                    else:
                        obstacle_color = DARK_BLOCK
                    pygame.draw.rect(screen, obstacle_color, rect)
            else:
                flash_red = False
                if obstacle_flash_list:
                    flash_red = any(
                        sq == (x, y) and now - timestamp < 2
                        for sq, timestamp in obstacle_flash_list
                    )
                if flash_red:
                    if (x, y) in obstacles:
                        if (x + y) % 2 == 0:
                            obstacle_color = LIGHT_BLOCK
                        else:
                            obstacle_color = RED
                        pygame.draw.rect(screen, obstacle_color, rect)
                else:
                    pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, BROWN, rect, 1)
            if (x, y) in obstacles:
                if force_reveal_obstacles:
                    pass
                elif (x, y) in obstacle_permanent_red:
                    pass
                elif obstacles_visible:
                    pass
                elif resign:
                    if (x, y) in obstacles:
                        if (x + y) % 2 == 0:
                            obstacle_color = LIGHT_BLOCK
                        else:
                            obstacle_color = RED
                        pygame.draw.rect(screen, obstacle_color, rect)
            if show_knight and (x, y) == knight_pos:
                pk.draw_piece(screen, rect, selected_piece)
            if (x, y) in move_nums and (show_target_num or (x, y) != target) and (x, y) != knight_pos:
                move_str = str(move_nums[(x, y)])
                txt = font_18.render(move_str, True, WHITE if color == DARK_MOVE else BLACK)
                tw, th = txt.get_size()
                txt_x = rect.x + (rect.width - tw) // 2
                txt_y = rect.y + (rect.height - th) // 2
                screen.blit(txt, (txt_x, txt_y))
            if show_start and resign and (x, y) == maze_path[0]:
                txt = font_18.render("s", True, BLACK)
                tw, th = txt.get_size()
                txt_x = rect.x + (rect.width - tw) // 2
                txt_y = rect.y + (rect.height - th) // 2
                screen.blit(txt, (txt_x, txt_y))

    return None


def draw_endgame(
        screen, board_size, maze_path, obstacles, target, board_top,
        board_left, end_state="maze_complete",
        knight_pos=None, move_nums=None, attempt_count=0, selected_piece="",
        revealed_obstacles=None,
        maze_type_choice="walled",
        path_length_choice="short",
        obstacles_visible=True,
        return_to_start=False,
        clock_selected=0,
        clock_elapsed=0,
):
    screen.fill(BACK_COLOR)

    path_nums = {sq: i for i, sq in enumerate(maze_path)}

    draw_board(
        screen, board_size, maze_path, obstacles, knight_pos, path_nums, target, True, board_left, board_top,
        True, show_knight=True, show_start=False, show_target_num=True,
        obstacle_flash_list=None, obstacle_permanent_red=(revealed_obstacles or set()),
        selected_piece=selected_piece, force_reveal_obstacles=False
    )

    menu_border, menu_inner, board_border, board_inner, right_menu_border, right_menu_inner = compute_layout()

    pygame.draw.rect(screen, BROWN, menu_border, width=1)
    pygame.draw.rect(screen, WHITE, menu_inner)

    pygame.draw.rect(screen, BROWN, right_menu_border, width=1)
    pygame.draw.rect(screen, WHITE, right_menu_inner)

    start_y = menu_inner.top + SQ_SIZE

    draw_menu_labels(screen, SQ_SIZE, menu_inner)

    draw_selection_summary(
        screen,
        menu_inner,
        maze_type_choice,
        path_length_choice,
        obstacles_visible,
        return_to_start,
        clock_selected
    )

    piece_txt = font_18.render(selected_piece.lower(), True, BLACK)

    piece_x = len(selected_piece) / 2

    px = (right_menu_inner.left + right_menu_inner.right) / 2 - piece_x #+ SQ_SIZE * 25.4
    py = start_y
    screen.blit(piece_txt, (px, py))

    move_text = pk.get_piece_move_sets_text(selected_piece)

    move_x = len(move_text) / 2


    if move_text:
        move_surf = font_18.render(move_text, True, BLACK)
        mx = (right_menu_inner.left + right_menu_inner.right) / 2 - move_x # + SQ_SIZE * 25.4
        my = py + SQ_SIZE
        screen.blit(move_surf, (mx, my))

    board_txt = font_18.render(f"{board_size} x {board_size}", True, BLACK)
#    bw, height = board_txt.get_size()
    bx = (menu_inner.left + menu_inner.right) / 2
    by = menu_inner.top + SQ_SIZE
    screen.blit(board_txt, (bx, by))


    remaining = remaining_for(clock_selected, clock_elapsed)
    if remaining is None:
        right_clock_text = format_clock_seconds(clock_elapsed)
    else:
        right_clock_text = format_clock_seconds(remaining)

    draw_clock(screen, clock_elapsed, menu_inner, clock_selected)

    if end_state == "maze_complete":
        move_count = len(maze_path) - 1
    else:
        move_count = max(move_nums.values(), default=0) if move_nums else 0

    draw_moves(screen, move_count, menu_inner)

    draw_attempts(screen, attempt_count, menu_inner)


    # draw endgame message
    endgame_messages = {
        'maze_complete': 'maze completed',
        'no_moves': 'no legal moves',
        'resignation': 'resigned',
        "timeout": "time's up"
    }
    end_reason = endgame_messages[end_state]

    endgame_colors = {
        'maze completed': (0, 128, 0),
        'no legal moves': (255, 0, 0),
        'resigned': (255, 0, 0),
        "time's up": (0, 0, 255)
    }

    endgame_color = endgame_colors.get(end_reason, (255, 0, 0))

    msg_txt = font_18.render(str(end_reason), True, endgame_color)
    msg_tw, msg_th = msg_txt.get_size()
    msg_x = (menu_inner.left + SQ_SIZE * 29.5) - msg_tw / 2
    msg_y = start_y + SQ_SIZE * 7
    screen.blit(msg_txt, (msg_x, msg_y))


    draw_standard_button(screen, "replay", menu_inner)
    draw_standard_button(screen, "menu", menu_inner)
    draw_standard_button(screen, "exit", menu_inner)


def menu_loop(screen, width, height, preset=None):
    if preset:
        selected_piece = preset.get("piece", "knight")
        board_size = preset["board_size"]
        maze_type_choice = preset.get("maze_type_choice", 1)
        path_length_choice = preset.get("path_length_choice", 2)
        obstacles_visible = preset.get("obstacles_visible", True)
        return_to_start = preset.get("return_to_start", False)
        clock_selected = preset.get("clock_selected", CLOCK_DEFAULT)
    else:
        selected_piece = "knight"
        board_size = BOARD_DEFAULT
        maze_type_choice = "walled"
        path_length_choice = "short"
        obstacles_visible = True
        return_to_start = False
        clock_selected = CLOCK_DEFAULT

    controls = {
        "board_minus": pygame.Rect(0, 0, 0, 0),
        "board_plus": pygame.Rect(0, 0, 0, 0),
        "maze_type_minus": pygame.Rect(0, 0, 0, 0),
        "maze_type_plus": pygame.Rect(0, 0, 0, 0),
        "path_length_minus": pygame.Rect(0, 0, 0, 0),
        "path_length_plus": pygame.Rect(0, 0, 0, 0),
        "obstacles_minus": pygame.Rect(0, 0, 0, 0),
        "obstacles_plus": pygame.Rect(0, 0, 0, 0),
        "bounce_minus": pygame.Rect(0, 0, 0, 0),
        "bounce_plus": pygame.Rect(0, 0, 0, 0),
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

        opening_menu(screen, selected_piece, board_size, maze_type_choice, path_length_choice,
                     obstacles_visible, return_to_start, clock_selected, controls)
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

                if controls["board_plus"].collidepoint(mx, my):
                    if board_size < BOARD_MAX:
                        board_size += 1
                    else:
                        board_size = BOARD_MIN

                if controls["board_minus"].collidepoint(mx, my):
                    if board_size > BOARD_MIN:
                        board_size -= 1
                    else:
                        board_size = BOARD_MAX

                current_idx = MAZE_TYPE_CHOICES.index(maze_type_choice)
                if controls["maze_type_plus"].collidepoint(mx, my):
                    maze_type_choice = MAZE_TYPE_CHOICES[(current_idx + 1) % len(MAZE_TYPE_CHOICES)]

                if controls["maze_type_minus"].collidepoint(mx, my):
                    maze_type_choice = MAZE_TYPE_CHOICES[(current_idx - 1) % len(MAZE_TYPE_CHOICES)]

                current_idx = PATH_LENGTH_CHOICES.index(path_length_choice)
                if controls["path_length_plus"].collidepoint(mx, my):
                    path_length_choice = PATH_LENGTH_CHOICES[(current_idx + 1) % len(PATH_LENGTH_CHOICES)]

                if controls["path_length_minus"].collidepoint(mx, my):
                    path_length_choice = PATH_LENGTH_CHOICES[(current_idx - 1) % len(PATH_LENGTH_CHOICES)]

                if controls["obstacles_plus"].collidepoint(mx, my):
                    obstacles_visible = not obstacles_visible

                if controls["obstacles_minus"].collidepoint(mx, my):
                    obstacles_visible = not obstacles_visible

                if controls["bounce_plus"].collidepoint(mx, my):
                    return_to_start = not return_to_start

                if controls["bounce_minus"].collidepoint(mx, my):
                    return_to_start = not return_to_start

                if controls["clock_plus"].collidepoint(mx, my):
                    if clock_selected < 30 * 60:
                        clock_selected += 60
                    else:
                        clock_selected = 0

                if controls["clock_minus"].collidepoint(mx, my):
                    if clock_selected > 0:
                        clock_selected -= 60
                    else:
                        clock_selected = 30 * 60

                if controls["piece_minus"].collidepoint(mx, my):
                    if piece_index > 0:
                        piece_index -= 1
                    else:
                        piece_index = len(pk.PIECE_LIST) - 1
                    selected_piece = pk.PIECE_LIST[piece_index]

                if controls["piece_plus"].collidepoint(mx, my):
                    if piece_index < len(pk.PIECE_LIST) - 1:
                        piece_index += 1
                    else:
                        piece_index = 0
                    selected_piece = pk.PIECE_LIST[piece_index]

                if controls["start_button"].collidepoint(mx, my):
                    # Only allow starting if validation passed
                    if controls.get("can_start", True):
                        return {
                            "piece": selected_piece,
                            "board_size": board_size,
                            "maze_type_choice": maze_type_choice,
                            "path_length_choice": path_length_choice,
                            "obstacles_visible": obstacles_visible,
                            "return_to_start": return_to_start,
                            "clock_selected": clock_selected,
                            "width": width,
                            "height": height

                        }

                if controls["exit_button"].collidepoint(mx, my):
                    return None


def run_game(screen, params):
    # --- UNPACK GAME SETTINGS ---
    selected_piece = params.get("piece", "knight")
    board_size = params["board_size"]
    maze_type_choice = params["maze_type_choice"]
    path_length_choice = params["path_length_choice"]
    obstacles_visible = params["obstacles_visible"]
    return_to_start = params["return_to_start"]
    clock_selected = params["clock_selected"]

    n = board_size
    multiplier = PATH_LENGTH_MAP[path_length_choice]
    min_length = n * multiplier + 1
    if path_length_choice == "long":
        max_length = n * n
    else:
        max_length = n * 2 * multiplier

    # --- BOARD LAYOUT COMPUTATION ---
    menu_border, menu_inner, board_border, board_inner, right_menu_border, right_menu_inner = compute_layout()
    board_left = board_border.left
    board_top = board_border.top

    # --- SHAREDLIB BOARD MODEL & RENDERER ---
    from gameboard import BoardModel, BoardRenderer
    board_model = BoardModel(n, n)
    board_origin = (board_left, board_top)
    board_renderer = BoardRenderer(board_model, SQ_SIZE, board_origin)

    # --- MAZE GENERATION ---
    move_func = pk.get_move_func(selected_piece)
    if maze_type_choice == "open":
        maze_path, obstacles = generate_open_maze_path_and_obstacles(
            n, min_length, max_length, move_func=move_func,
            max_attempts=200, time_budget=1.0
        )
    else:  # "walled"
        maze_path, obstacles = generate_maze_path_and_obstacles(
            n, min_length, max_length, move_func=move_func,
            max_attempts=200, time_budget=1.0
        )

    if not maze_path or len(maze_path) <= 4 or obstacles is None:
        # Error handling: Failed to generate maze
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
        return "menu"

    knight_pos = maze_path[0]
    move_nums = {knight_pos: 0}
    move_count = 0
    attempt_count = 0

    clock_start = None
    paused_elapsed = 0
    paused_due_to_minimize = False

    resignation = False
    endgame = False
    obstacle_flash_list = []
    obstacle_permanent_red = set()
    revealed_obstacles = set()

    running = True
    end_state = "win"

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

        draw_selection_summary(
            screen,
            menu_inner,
            maze_type_choice,
            path_length_choice,
            obstacles_visible,
            return_to_start,
            clock_selected
        )

        piece_txt = font_18.render(selected_piece.lower(), True, BLACK)

        piece_len = len(selected_piece) / 2
#        center_x = (piece_minus_rect.right + piece_plus_rect.left) // 2
        px = (right_menu_inner.left + right_menu_inner.right) / 2 - piece_len
        py = menu_inner.top + SQ_SIZE
        screen.blit(piece_txt, (px, py))

        move_text = pk.get_piece_move_sets_text(selected_piece)
        if move_text:
            move_surf = font_18.render(move_text, True, BLACK)
            mw = len(move_text) / 2
            mx = (right_menu_inner.left + right_menu_inner.right) / 2 - mw  #+ SQ_SIZE * 25.4
            my = menu_inner.top + SQ_SIZE * 2
            screen.blit(move_surf, (mx, my))

        board_txt = font_18.render(f"{n} x {n}", True, BLACK)
#        bw, height = board_txt.get_size()
        bx = (menu_inner.left + menu_inner.right) / 2
        by = menu_inner.top + SQ_SIZE
        screen.blit(board_txt, (bx, by))

        draw_moves(screen, move_count, menu_inner)

        draw_attempts(screen, attempt_count, menu_inner)

        draw_clock(screen, clock_elapsed, menu_inner, clock_selected)

        now = time.time()
        obstacle_flash_list = [(sq, ts) for (sq, ts) in obstacle_flash_list if now - ts < 3]

        if not endgame:
            if knight_pos == maze_path[-1]:
                end_state = "maze_complete"
                endgame = True
            elif resignation:
                end_state = "resignation"
                endgame = True
            elif clock_has_expired(clock_selected, clock_elapsed):
                end_state = "timeout"
                endgame = True

        if endgame:
            if clock_start is None:
                final_elapsed = paused_elapsed
            else:
                final_elapsed = int(paused_elapsed + (time.time() - clock_start))

            replay_rect = draw_standard_button(screen, "replay", menu_inner)
            menu_rect = draw_standard_button(screen, "menu", menu_inner)
            exit_rect = draw_standard_button(screen, "exit", menu_inner)

            if end_state == "win":
                end_knight_pos = maze_path[-1]
            else:
                end_knight_pos = knight_pos

            draw_endgame(
                screen, n, maze_path, obstacles, maze_path[-1], board_top,
                board_left, end_state,
                clock_selected=clock_selected,
                clock_elapsed=final_elapsed,
                knight_pos=end_knight_pos,
                move_nums=move_nums,
                attempt_count=attempt_count,
                selected_piece=selected_piece,
                revealed_obstacles=revealed_obstacles,
                maze_type_choice=maze_type_choice,
                path_length_choice=path_length_choice,
                obstacles_visible=obstacles_visible,
                return_to_start=return_to_start
            )
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
                        draw_endgame(
                            screen, n, maze_path, obstacles, maze_path[-1], board_top,
                            board_left, end_state,
                            clock_selected=clock_selected,
                            clock_elapsed=final_elapsed,
                            knight_pos=end_knight_pos,
                            move_nums=move_nums,
                            attempt_count=attempt_count,
                            selected_piece=selected_piece,
                            revealed_obstacles=revealed_obstacles,
                            maze_type_choice=maze_type_choice,
                            path_length_choice=path_length_choice,
                            obstacles_visible=obstacles_visible,
                            return_to_start=return_to_start
                        )
                        pygame.display.flip()
                    if event2.type == pygame.ACTIVEEVENT:
                        if getattr(event2, "gain", None) == 1 and getattr(event2, "state", None) == 1:
                            draw_endgame(
                                screen, n, maze_path, obstacles, maze_path[-1], board_top,
                                board_left, end_state,
                                clock_selected=clock_selected,
                                clock_elapsed=final_elapsed,
                                knight_pos=end_knight_pos,
                                move_nums=move_nums,
                                attempt_count=attempt_count,
                                selected_piece=selected_piece,
                                revealed_obstacles=revealed_obstacles,
                                maze_type_choice=maze_type_choice,
                                path_length_choice=path_length_choice,
                                obstacles_visible=obstacles_visible,
                                return_to_start=return_to_start
                            )
                            pygame.display.flip()
                    elif event2.type == pygame.MOUSEBUTTONDOWN:
                        mx, my = event2.pos
                        if replay_rect.collidepoint(mx, my):
                            return "replay"
                        elif menu_rect.collidepoint(mx, my):
                            screen.fill(BACK_COLOR)
                            pygame.display.flip()
                            return "menu"
                        elif exit_rect.collidepoint(mx, my):
                            return None
                pygame.time.wait(10)
        else:
            draw_board(screen, board_size, maze_path, obstacles, knight_pos, move_nums, maze_path[-1],
                       resignation, board_left, board_top,
                       obstacles_visible,
                       obstacle_flash_list=obstacle_flash_list,
                       obstacle_permanent_red=obstacle_permanent_red,
                       selected_piece=selected_piece)

            move_guide_rect = draw_standard_button(screen, "guide", menu_inner)
            resign_rect = draw_standard_button(screen, "resign", menu_inner)
            exit_rect = draw_standard_button(screen, "exit", menu_inner)
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
                elif ev.type == pygame.MOUSEBUTTONDOWN and not resignation:
                    mx, my = ev.pos
                    _mb, _mi, _bb, board_inner, right_menu_border, right_menu_inner = compute_layout()
                    grid_x = (mx - board_inner.left) // SQ_SIZE
                    grid_y = (my - board_inner.top) // SQ_SIZE
                    click_square = (grid_x, grid_y)

                    if exit_rect.collidepoint(mx, my):
                        return None
                    elif resign_rect.collidepoint(mx, my):
                        resignation = True
                    elif 0 <= grid_x < n and 0 <= grid_y < n and click_square in pk.get_move_func(selected_piece)(
                            *knight_pos, n):
                        if clock_start is None:
                            clock_start = time.time()
                        if click_square in obstacles:
                            attempt_count += 1
                            revealed_obstacles.add(click_square)
                            if not obstacles_visible and click_square not in obstacle_permanent_red:
                                obstacle_flash_list.append((click_square, time.time()))
                            if obstacles_visible and click_square not in obstacle_permanent_red:
                                obstacle_permanent_red.add(click_square)
                            if return_to_start:
                                knight_pos = maze_path[0]
                                move_nums = {knight_pos: 0}
                                move_count = 0
                        elif click_square in maze_path and click_square not in move_nums:
                            attempt_count += 0
                            move_count += 1
                            knight_pos = click_square
                            move_nums[knight_pos] = move_count
            pygame.time.wait(10)
    return None


def main():
    pygame.display.set_caption("Knight's Maze v60")
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
        if result == "menu":
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
