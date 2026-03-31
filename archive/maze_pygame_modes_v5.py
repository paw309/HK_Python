import pygame
import random
import time

# --- CONSTANTS ---
MIN_SIZE = 6
MAX_SIZE = 12
DEFAULT_SIZE = 8
SQUARE_SIZE = 44
MARGIN = 20
MENU_HEIGHT = 200
END_HEIGHT = 20
TIMER_DEFAULT = 5 * 60  # seconds
WIN_W = MAX_SIZE * SQUARE_SIZE + 2 * MARGIN
WIN_H = MAX_SIZE * SQUARE_SIZE + MENU_HEIGHT + END_HEIGHT

WHITE = (255, 255, 255)
GRAY = (210, 210, 210)
GREEN = (30, 180, 30)
RED = (180, 30, 30)
BLUE = (0, 0, 200)
PURPLE = (160, 32, 240)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
OBSTACLE_COLOR = (60, 60, 60)
BUTTON_COLOR = (100, 100, 255)
END_BG = (220, 220, 250)
SLIDER_GREEN = GREEN
SLIDER_RED = RED

pygame.init()
FONT = pygame.font.SysFont("arial", 22)
SMALL_FONT = pygame.font.SysFont("arial", 16)
BIG_FONT = pygame.font.SysFont("arial", 32)

def knight_moves(x, y, n):
    moves = [(2, 1), (1, 2), (-1, 2), (-2, 1),
             (-2, -1), (-1, -2), (1, -2), (2, -1)]
    return [(x + dx, y + dy) for dx, dy in moves if 0 <= x + dx < n and 0 <= y + dy < n]

def find_valid_path_timed(n, min_len, max_len, timeout=15):
    start_time = time.time()
    while True:
        # Try paths until found or timeout
        result = find_valid_path(n, min_len, max_len, timeout=(timeout - (time.time()-start_time)))
        if result:
            return result
        # If time exceeded, try again with new random parameters
        if time.time() - start_time > timeout:
            start_time = time.time()
    return None, None, None

def find_valid_path(n, min_len, max_len, timeout=15):
    squares = [(x, y) for x in range(n) for y in range(n)]
    start_time = time.time()
    for _ in range(2000):
        if time.time() - start_time > timeout:
            break
        start = random.choice(squares)
        targets = [sq for sq in squares if sq != start]
        random.shuffle(targets)
        for target in targets:
            if time.time() - start_time > timeout:
                break
            path = dfs_knight_path(start, target, n, min_len, max_len, timeout=(timeout - (time.time()-start_time)))
            if path:
                return start, target, path
    return None

def dfs_knight_path(start, target, n, min_len, max_len, timeout=15):
    start_time = time.time()
    stack = [(start, [start])]
    while stack:
        if time.time() - start_time > timeout:
            break
        current, path = stack.pop()
        if current == target and min_len <= len(path) <= max_len:
            if path_degrees_okay(path, n):
                return path
        if len(path) >= max_len:
            continue
        for move in knight_moves(*current, n):
            if move not in path:
                stack.append((move, path + [move]))
    return None

def path_degrees_okay(path, n):
    path_set = set(path)
    for i, square in enumerate(path):
        neighbors = [m for m in knight_moves(*square, n) if m in path_set]
        if i == 0 or i == len(path)-1:  # Endpoints
            if len(neighbors) != 1:
                return False
        else:
            if len(neighbors) != 2:
                return False
    return True

def draw_knight(screen, rect):
    pygame.draw.circle(screen, YELLOW, rect.center, rect.width//2 - 4)
    ktxt = FONT.render('K', True, BLACK)
    screen.blit(ktxt, (rect.x + rect.width//3, rect.y + rect.height//4))

def draw_timer(screen, remaining, y=10):
    mins = remaining // 60
    secs = remaining % 60
    screen.blit(FONT.render(f"Time: {mins:02}:{secs:02}", True, BLACK), (MARGIN, y))

def draw_board(screen, n, maze_path, obstacles, knight_pos, move_nums, target, stuck, board_top, obstacles_visible, show_knight=True, show_start=True, show_target_num=True):
    board_left = MARGIN
    for y in range(n):
        for x in range(n):
            rect = pygame.Rect(board_left + x*SQUARE_SIZE, board_top + y*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
            color = WHITE
            if (x, y) == target:
                color = GREEN
            elif (x, y) in move_nums:
                color = BLUE
            elif stuck and (x, y) in maze_path:
                color = PURPLE
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, BLACK, rect, 2)
            if (x, y) in obstacles:
                if obstacles_visible or (x, y) in move_nums or stuck:
                    pygame.draw.rect(screen, OBSTACLE_COLOR, rect)
            # Only show knight on normal game display
            if show_knight and (x, y) == knight_pos:
                draw_knight(screen, rect)
            # Only show move numbers except target
            if (x, y) in move_nums and (x, y) != target:
                txt = FONT.render(str(move_nums[(x, y)]), True, WHITE if color == BLUE else BLACK)
                screen.blit(txt, (rect.x + 6, rect.y + 4))
            # Only show "S" on start square if show_start is True
            if show_start and stuck and (x, y) == maze_path[0]:
                txt = FONT.render("S", True, BLACK)
                screen.blit(txt, (rect.x + SQUARE_SIZE//2 - 11, rect.y + SQUARE_SIZE//2 - 11))
            # Do NOT number the target square at endgame
            if not show_target_num and stuck and (x, y) == target:
                pass
    # 'Stuck' button
    btn_rect = pygame.Rect(board_left, board_top + n*SQUARE_SIZE + 8, 110, 36)
    pygame.draw.rect(screen, RED if not stuck else GRAY, btn_rect)
    screen.blit(FONT.render("Stuck", True, WHITE), (btn_rect.x + 24, btn_rect.y + 5))
    return btn_rect

def draw_menu(screen, board_size, timer_val, obstacles_visible, return_to_start, controls):
    screen.fill(GRAY)
    y = MARGIN
    # Board size selection
    screen.blit(BIG_FONT.render("Knight's Maze", True, BLUE), (MARGIN, y))
    y += 40
    screen.blit(FONT.render("Board Size:", True, BLACK), (MARGIN, y))
    plus_rect, minus_rect = controls["board_plus"], controls["board_minus"]
    pygame.draw.rect(screen, BUTTON_COLOR, plus_rect)
    pygame.draw.rect(screen, BUTTON_COLOR, minus_rect)
    screen.blit(FONT.render("+", True, WHITE), (plus_rect.x + 7, plus_rect.y + 2))
    screen.blit(FONT.render("-", True, WHITE), (minus_rect.x + 7, minus_rect.y + 2))
    screen.blit(FONT.render(f"{board_size} x {board_size}", True, BLACK), (minus_rect.x + 40, y))

    # Timer selection
    y += 36
    screen.blit(FONT.render("Timer:", True, BLACK), (MARGIN, y))
    plus_t_rect, minus_t_rect = controls["timer_plus"], controls["timer_minus"]
    pygame.draw.rect(screen, BUTTON_COLOR, plus_t_rect)
    pygame.draw.rect(screen, BUTTON_COLOR, minus_t_rect)
    screen.blit(FONT.render("+", True, WHITE), (plus_t_rect.x + 7, plus_t_rect.y + 2))
    screen.blit(FONT.render("-", True, WHITE), (minus_t_rect.x + 7, minus_t_rect.y + 2))
    screen.blit(FONT.render(f"{timer_val//60} min", True, BLACK), (minus_t_rect.x + 55, y))

    # Obstacle Visibility slider
    y += 36
    obs_rect = controls["obstacle_slider"]
    pygame.draw.rect(screen, SLIDER_GREEN if obstacles_visible else SLIDER_RED, obs_rect)
    obs_txt = "Obstacles: Visible" if obstacles_visible else "Obstacles: Hidden"
    screen.blit(FONT.render(obs_txt, True, BLACK), (obs_rect.x + 50, obs_rect.y))

    # Return to Start slider
    y += 36
    ret_rect = controls["return_slider"]
    # Stay is green, Return to Start is red
    pygame.draw.rect(screen, SLIDER_GREEN if not return_to_start else SLIDER_RED, ret_rect)
    ret_txt = "On Obstacle: Stay" if not return_to_start else "On Obstacle: Return to Start"
    screen.blit(FONT.render(ret_txt, True, BLACK), (ret_rect.x + 50, ret_rect.y))

    # Start Game button
    y += 44
    start_rect = controls["start_button"]
    pygame.draw.rect(screen, GREEN, start_rect)
    screen.blit(FONT.render("Start Game", True, WHITE), (start_rect.x + 20, start_rect.y + 5))

def draw_setting_up(screen, timer_val):
    screen.fill(GRAY)
    draw_timer(screen, timer_val, y=10)
    txt = BIG_FONT.render("I'm setting up the game...", True, BLACK)
    tw, th = txt.get_size()
    screen.blit(txt, ((WIN_W-tw)//2, (WIN_H-th)//2))
    pygame.display.flip()

def draw_endgame(screen, n, maze_path, obstacles, knight_pos, target, board_top, obstacles_visible, playagain_rect, remaining):
    screen.fill(END_BG)
    draw_timer(screen, remaining, y=10)
    # Endgame display: no knight, no start S, no target number
    move_nums = {sq: i for i, sq in enumerate(maze_path)}
    draw_board(screen, n, maze_path, obstacles, None, move_nums, target, True, board_top, True, show_knight=False, show_start=False, show_target_num=False)
    screen.blit(BIG_FONT.render("Game Over!", True, RED), (MARGIN, board_top//2 - 20))
    pygame.draw.rect(screen, BUTTON_COLOR, playagain_rect)
    screen.blit(FONT.render("Play Again", True, WHITE), (playagain_rect.x + 25, playagain_rect.y + 8))

def menu_loop(screen):
    board_size = DEFAULT_SIZE
    timer_val = TIMER_DEFAULT
    obstacles_visible = True
    return_to_start = False

    controls = {
        "board_plus": pygame.Rect(MARGIN + 130, MARGIN + 40, 32, 28),
        "board_minus": pygame.Rect(MARGIN + 170, MARGIN + 40, 32, 28),
        "timer_plus": pygame.Rect(MARGIN + 130, MARGIN + 76, 32, 28),
        "timer_minus": pygame.Rect(MARGIN + 170, MARGIN + 76, 32, 28),
        "obstacle_slider": pygame.Rect(MARGIN + 18, MARGIN + 112, 38, 28),
        "return_slider": pygame.Rect(MARGIN + 18, MARGIN + 148, 38, 28),
        "start_button": pygame.Rect(MARGIN + 18, MARGIN + 192, 170, 38)
    }
    while True:
        draw_menu(screen, board_size, timer_val, obstacles_visible, return_to_start, controls)
        pygame.display.flip()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: return None
            if ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                if controls["board_plus"].collidepoint(mx, my) and board_size < MAX_SIZE:
                    board_size += 1
                elif controls["board_minus"].collidepoint(mx, my) and board_size > MIN_SIZE:
                    board_size -= 1
                elif controls["timer_plus"].collidepoint(mx, my) and timer_val < 5*60:
                    timer_val += 60
                elif controls["timer_minus"].collidepoint(mx, my) and timer_val > 60:
                    timer_val -= 60
                elif controls["obstacle_slider"].collidepoint(mx, my):
                    obstacles_visible = not obstacles_visible
                elif controls["return_slider"].collidepoint(mx, my):
                    return_to_start = not return_to_start
                elif controls["start_button"].collidepoint(mx, my):
                    return board_size, timer_val, obstacles_visible, return_to_start

def main():
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Knight's Maze")

    while True:
        menu_result = menu_loop(screen)
        if not menu_result:
            break
        board_size, timer_val, obstacles_visible, return_to_start = menu_result

        # --- SETTING UP ---
        draw_setting_up(screen, timer_val)
        pygame.display.flip()
        # Maze generation with timeout and retry
        n = board_size
        min_len = n
        max_len = 2*n
        while True:
            result = find_valid_path_timed(n, min_len, max_len, timeout=15)
            if result:
                start, target, maze_path = result
                if maze_path:
                    break
            draw_setting_up(screen, timer_val)
            pygame.display.flip()
        maze_path_set = set(maze_path)
        obstacles = set((x, y) for x in range(n) for y in range(n) if (x, y) not in maze_path_set)
        knight_pos = start
        move_nums = {knight_pos: 0}
        move_count = 0
        revealed_obstacles = set()
        timer_start = None
        stuck = False
        endgame = False
        board_top = MENU_HEIGHT

        # --- MAIN GAME LOOP ---
        while True:
            screen.fill(GRAY)
            if timer_start:
                elapsed = time.time() - timer_start
                remaining = max(0, timer_val - int(elapsed))
            else:
                remaining = timer_val
            draw_timer(screen, remaining, y=10)
            btn_rect = draw_board(screen, n, maze_path, revealed_obstacles, knight_pos, move_nums, target, stuck or endgame, board_top, obstacles_visible)
            pygame.display.flip()

            if stuck or endgame or remaining == 0 or knight_pos == target:
                playagain_rect = pygame.Rect(MARGIN + 18, board_top + n*SQUARE_SIZE + 48, 170, 38)
                draw_endgame(screen, n, maze_path, obstacles, knight_pos, target, board_top, obstacles_visible, playagain_rect, remaining)
                pygame.display.flip()
                while True:
                    for ev in pygame.event.get():
                        if ev.type == pygame.QUIT: return
                        elif ev.type == pygame.MOUSEBUTTONDOWN:
                            mx, my = ev.pos
                            if playagain_rect.collidepoint(mx, my):
                                stuck = False
                                endgame = False
                                break
                    else:
                        continue
                    break
                break  # return to menu

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: return
                elif ev.type == pygame.MOUSEBUTTONDOWN and not stuck:
                    mx, my = ev.pos
                    board_left = MARGIN
                    grid_x = (mx - board_left) // SQUARE_SIZE
                    grid_y = (my - board_top) // SQUARE_SIZE
                    clicked_square = (grid_x, grid_y)
                    if btn_rect.collidepoint(mx, my):
                        stuck = True
                    elif 0 <= grid_x < n and 0 <= grid_y < n and clicked_square in knight_moves(*knight_pos, n):
                        if timer_start is None:
                            timer_start = time.time()
                        if clicked_square in obstacles:
                            revealed_obstacles.add(clicked_square)
                            if return_to_start:
                                knight_pos = start
                                move_nums = {knight_pos: 0}
                                move_count = 0
                        else:
                            move_count += 1
                            knight_pos = clicked_square
                            move_nums[knight_pos] = move_count

if __name__ == "__main__":
    main()