import pygame
import random
import time
from collections import deque

SQUARE_SIZE = 64
MARGIN = 40
FPS = 30
PURPLE = (160, 32, 240)

def knight_moves():
    return [
        (2, 1), (1, 2), (-1, 2), (-2, 1),
        (-2, -1), (-1, -2), (1, -2), (2, -1)
    ]

def is_valid(r, c, m, n):
    return 0 <= r < m and 0 <= c < n

def min_moves_and_dist_matrix(m, n, start, end):
    queue = deque()
    queue.append(start)
    dist = [[-1 for _ in range(n)] for _ in range(m)]
    dist[start[0]][start[1]] = 0
    while queue:
        r, c = queue.popleft()
        for dr, dc in knight_moves():
            nr, nc = r + dr, c + dc
            if is_valid(nr, nc, m, n) and dist[nr][nc] == -1:
                dist[nr][nc] = dist[r][c] + 1
                queue.append((nr, nc))
    return dist[end[0]][end[1]], dist

def squares_one_move_away(m, n, square):
    result = set()
    r, c = square
    for dr, dc in knight_moves():
        nr, nc = r + dr, c + dc
        if is_valid(nr, nc, m, n):
            result.add((nr, nc))
    return result

def find_knight_path_exact_x(m, n, start, end, x, y):
    tries = 0
    while True:
        visited = [[False for _ in range(n)] for _ in range(m)]
        visited[start[0]][start[1]] = True
        path = [start]
        res = _backtrack_knight_path(m, n, start[0], start[1], end, x, 0, path, visited)
        if res:
            if y == 2:
                forbidden = squares_one_move_away(m, n, end)
                if res[1] in forbidden:
                    tries += 1
                    if tries > 1000:
                        return None
                    continue
            return res
        tries += 1
        if tries > 1000:
            return None

def _backtrack_knight_path(m, n, r, c, end, x, depth, path, visited):
    if depth > x:
        return None
    if depth == x and (r, c) == end:
        return path[:]
    moves = knight_moves()
    random.shuffle(moves)
    for dr, dc in moves:
        nr, nc = r + dr, c + dc
        if is_valid(nr, nc, m, n) and not visited[nr][nc]:
            visited[nr][nc] = True
            path.append((nr, nc))
            result = _backtrack_knight_path(m, n, nr, nc, end, x, depth + 1, path, visited)
            if result:
                return result
            path.pop()
            visited[nr][nc] = False
    return None

def random_square(m, n):
    return (random.randint(0, m-1), random.randint(0, n-1))

def coords_to_algebraic(row, col):
    return f"{chr(col + ord('a'))}{row + 1}"

def generate_maze(settings):
    m = settings.get("board_w", 8)
    n = settings.get("board_h", 8)
    extra_obstacles_mode = settings.get("extra_obstacles", False)
    obstacles_visible = settings.get("obstacles_visible", True)
    while True:
        start = random_square(m, n)
        target = random_square(m, n)
        if start == target:
            continue
        y, _ = min_moves_and_dist_matrix(m, n, start, target)
        if y < 2:
            continue
        min_x = m // 2 + y
        max_x = m + y
        parity = y % 2
        possible_x = [x for x in range(min_x, max_x + 1) if x % 2 == parity]
        random.shuffle(possible_x)
        for x in possible_x:
            maze_path = find_knight_path_exact_x(m, n, start, target, x, y)
            if maze_path:
                break
        else:
            continue
        if maze_path:
            break
    maze_path_set = set(maze_path)
    y, dist_matrix = min_moves_and_dist_matrix(m, n, start, target)
    shortest_path_layer = set()
    queue = deque()
    queue.append((start[0], start[1], 0))
    shortest_path_layer.add(start)
    visited = [[False for _ in range(n)] for _ in range(m)]
    visited[start[0]][start[1]] = True
    while queue:
        r, c, d = queue.popleft()
        if d > y:
            continue
        for dr, dc in knight_moves():
            nr, nc = r + dr, c + dc
            if is_valid(nr, nc, m, n) and dist_matrix[nr][nc] == dist_matrix[r][c] + 1:
                shortest_path_layer.add((nr, nc))
                if not visited[nr][nc]:
                    visited[nr][nc] = True
                    queue.append((nr, nc, d + 1))
    obstacles = set()
    for sq in shortest_path_layer:
        if sq not in maze_path_set:
            obstacles.add(sq)
    extra_obstacles = set()
    remaining_squares = {(r, c) for r in range(m) for c in range(n)} - maze_path_set - obstacles - {start, target}
    available = len(remaining_squares)
    if extra_obstacles_mode and available > 0:
        min_extra = min(int(0.25 * available), available)
        max_extra = min(max(1, int(0.5 * available)), available)
        if min_extra > max_extra:
            min_extra = max_extra
        num_extra = random.randint(min_extra, max_extra) if max_extra > 0 else 0
        if num_extra > 0:
            extra_obstacles = set(random.sample(list(remaining_squares), num_extra))
    total_obstacles = obstacles | extra_obstacles
    return {
        "board_size": (m, n),
        "start": start,
        "target": target,
        "maze_path": maze_path,
        "obstacles": total_obstacles,
        "obstacles_visible": obstacles_visible,
        "return_to_start": settings.get("return_to_start", False),
        "timer_type": settings.get("timer_type", "stopwatch"),
        "timer_length": settings.get("timer_length", 5*60)
    }

def draw_text_menu(screen, font, options, selected, title=""):
    screen.fill((50, 50, 50))
    if title:
        title_font = pygame.font.SysFont(None, 48)
        title_surface = title_font.render(title, True, (255,255,0))
        title_rect = title_surface.get_rect(center=(screen.get_width()//2, 60))
        screen.blit(title_surface, title_rect)
    for i, opt in enumerate(options):
        color = (255, 255, 255) if i != selected else (255, 200, 50)
        txt = font.render(opt, True, color)
        txt_rect = txt.get_rect(center=(screen.get_width()//2, 150 + i*60))
        screen.blit(txt, txt_rect)
    pygame.display.flip()

def pygame_mode_selection():
    pygame.init()
    screen = pygame.display.set_mode((640, 360))
    font = pygame.font.SysFont(None, 36)
    options = ["Easy", "Hard", "Custom"]
    selected = 0
    running = True
    while running:
        draw_text_menu(screen, font, options, selected, "Choose Mode")
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_DOWN, pygame.K_s]:
                    selected = (selected + 1) % len(options)
                elif event.key in [pygame.K_UP, pygame.K_w]:
                    selected = (selected - 1) % len(options)
                elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    return options[selected].lower()
    pygame.quit()

def pygame_custom_settings():
    pygame.init()
    screen = pygame.display.set_mode((640, 600))
    font = pygame.font.SysFont(None, 32)
    settings = {}
    m, n = 8, 8
    prompts = [
        ("Board width (6-16): ", "board_w", 6, 16),
        ("Board height (6-16): ", "board_h", 6, 16)
    ]
    for prompt, key, minv, maxv in prompts:
        val = m if "width" in prompt else n
        done = False
        while not done:
            screen.fill((50,50,50))
            txt = font.render(f"{prompt}{val}", True, (255,255,255))
            screen.blit(txt, (80, 180))
            pygame.display.flip()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_UP, pygame.K_w]:
                        val = min(maxv, val+1)
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        val = max(minv, val-1)
                    elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        done = True
        settings[key] = val
    options = ["No extra obstacles", "Extra obstacles"]
    selected = 0
    while True:
        draw_text_menu(screen, font, options, selected, "Extra Obstacles?")
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); exit()
            elif event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_DOWN, pygame.K_s]: selected = 1
                elif event.key in [pygame.K_UP, pygame.K_w]: selected = 0
                elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    settings["extra_obstacles"] = bool(selected)
                    break
        if "extra_obstacles" in settings: break
    options = ["Obstacles visible", "Obstacles invisible"]
    selected = 0
    while True:
        draw_text_menu(screen, font, options, selected, "Obstacle Visibility")
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); exit()
            elif event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_DOWN, pygame.K_s]: selected = 1
                elif event.key in [pygame.K_UP, pygame.K_w]: selected = 0
                elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    settings["obstacles_visible"] = not selected
                    break
        if "obstacles_visible" in settings: break
    options = ["Stay on obstacle", "Return to start"]
    selected = 0
    while True:
        draw_text_menu(screen, font, options, selected, "Obstacle Effect")
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); exit()
            elif event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_DOWN, pygame.K_s]: selected = 1
                elif event.key in [pygame.K_UP, pygame.K_w]: selected = 0
                elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    settings["return_to_start"] = bool(selected)
                    break
        if "return_to_start" in settings: break
    options = ["Stopwatch", "Custom countdown timer"]
    selected = 0
    while True:
        draw_text_menu(screen, font, options, selected, "Timer Type")
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); exit()
            elif event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_DOWN, pygame.K_s]: selected = 1
                elif event.key in [pygame.K_UP, pygame.K_w]: selected = 0
                elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    settings["timer_type"] = "countdown" if selected else "stopwatch"
                    break
        if "timer_type" in settings: break
    if settings["timer_type"] == "countdown":
        selected = 4
        options = [f"{i} minute{'s' if i>1 else ''}" for i in range(1, 6)]
        while True:
            draw_text_menu(screen, font, options, selected, "Set countdown timer")
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_DOWN, pygame.K_s]:
                        selected = min(selected + 1, 4)
                    elif event.key in [pygame.K_UP, pygame.K_w]:
                        selected = max(selected - 1, 0)
                    elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        settings["timer_length"] = (selected + 1) * 60
                        break
            if "timer_length" in settings: break
    pygame.quit()
    return settings

def draw_stuck_button(screen, board_w, board_h, pressed=False):
    btn_x = MARGIN + board_w * SQUARE_SIZE + 20
    btn_y = MARGIN
    btn_w = 120
    btn_h = 50
    color = (200, 0, 0) if pressed else (255, 50, 50)
    pygame.draw.rect(screen, color, (btn_x, btn_y, btn_w, btn_h))
    font = pygame.font.SysFont(None, 30)
    txt = font.render("Stuck!", True, (255,255,255))
    txt_rect = txt.get_rect(center=(btn_x + btn_w//2, btn_y + btn_h//2))
    screen.blit(txt, txt_rect)
    return pygame.Rect(btn_x, btn_y, btn_w, btn_h)

def draw_board(screen, board_w, board_h, knight_pos, target, obstacles, revealed, move_numbers, show_obstacles, maze_path=[], endgame=False):
    maze_path_set = set(maze_path)
    for r in range(board_h):
        for c in range(board_w):
            x = MARGIN + c*SQUARE_SIZE
            y = MARGIN + r*SQUARE_SIZE
            rect = pygame.Rect(x, y, SQUARE_SIZE, SQUARE_SIZE)
            if endgame and (r, c) in maze_path_set:
                color = PURPLE
            elif (r + c) % 2 == 0:
                color = (240, 217, 181)
            else:
                color = (181, 136, 99)
            pygame.draw.rect(screen, color, rect)
            if (show_obstacles or endgame) and (r, c) in revealed:
                pygame.draw.rect(screen, (128, 0, 0), rect)
            if (r, c) == target:
                pygame.draw.circle(screen, (0, 255, 0), (x + SQUARE_SIZE//2, y + SQUARE_SIZE//2), SQUARE_SIZE//3)
            if (r, c) in move_numbers:
                num = move_numbers[(r, c)]
                font2 = pygame.font.SysFont(None, 36)
                txt = font2.render(str(num), True, (0,0,0))
                txt_rect = txt.get_rect(center=(x+SQUARE_SIZE//2, y+SQUARE_SIZE//2))
                screen.blit(txt, txt_rect)
            if (r, c) == knight_pos:
                pygame.draw.circle(screen, (0, 0, 255), (x + SQUARE_SIZE//2, y + SQUARE_SIZE//2), SQUARE_SIZE//3)
    for r in range(board_h+1):
        pygame.draw.line(screen, (0,0,0), (MARGIN, MARGIN + r*SQUARE_SIZE), (MARGIN + board_w*SQUARE_SIZE, MARGIN + r*SQUARE_SIZE), 2)
    for c in range(board_w+1):
        pygame.draw.line(screen, (0,0,0), (MARGIN + c*SQUARE_SIZE, MARGIN), (MARGIN + c*SQUARE_SIZE, MARGIN + board_h*SQUARE_SIZE), 2)

def main():
    mode = pygame_mode_selection()
    if mode == "easy":
        settings = {
            "board_w": 8,
            "board_h": 8,
            "extra_obstacles": False,
            "obstacles_visible": True,
            "return_to_start": False,
            "timer_type": "stopwatch",
            "timer_length": 5*60
        }
    elif mode == "hard":
        settings = {
            "board_w": 8,
            "board_h": 8,
            "extra_obstacles": True,
            "obstacles_visible": False,
            "return_to_start": True,
            "timer_type": "countdown",
            "timer_length": 5*60
        }
    else:
        settings = pygame_custom_settings()

    pygame.init()
    maze = generate_maze(settings)
    board_w, board_h = maze["board_size"]
    sw = MARGIN*2 + board_w*SQUARE_SIZE + 160
    sh = MARGIN*2 + board_h*SQUARE_SIZE + 80
    screen = pygame.display.set_mode((sw, sh))
    pygame.display.set_caption("The Knight's Maze")
    clock = pygame.time.Clock()

    knight_pos = maze["start"]
    target = maze["target"]
    obstacles = maze["obstacles"]
    revealed = set()
    started = False
    start_time = None
    stop_time = None
    won = False
    stuck = False
    time_up = False
    endgame = False

    move_numbers = {}
    move_count = 0
    move_numbers[knight_pos] = 0
    visited = set()
    visited.add(knight_pos)

    font = pygame.font.SysFont(None, 36)
    info_font = pygame.font.SysFont(None, 28)
    show_obstacles = maze["obstacles_visible"]
    timer_length = maze["timer_length"]
    timer_type = maze["timer_type"]
    obstacle_flash_time = 5 if not show_obstacles and settings.get("extra_obstacles", False) else None
    flash_obstacles = []

    maze_path = maze["maze_path"]
    maze_path_set = set(maze_path)

    running = True
    while running:
        mouse_pressed = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif not endgame and event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                btn_rect = draw_stuck_button(screen, board_w, board_h)
                if btn_rect.collidepoint(mx, my):
                    stuck = True
                    endgame = True
                    stop_time = time.time()
                elif MARGIN <= mx < MARGIN + board_w*SQUARE_SIZE and MARGIN <= my < MARGIN + board_h*SQUARE_SIZE:
                    c = (mx - MARGIN) // SQUARE_SIZE
                    r = (my - MARGIN) // SQUARE_SIZE
                    if (r, c) == knight_pos or endgame:
                        continue
                    if (r, c) in squares_one_move_away(board_h, board_w, knight_pos):
                        if (r, c) in visited:
                            continue
                        if not started:
                            started = True
                            start_time = time.time()
                        # Always flash red squares for invisible obstacles, even if return to start is chosen in custom mode
                        if (r, c) in obstacles:
                            if show_obstacles or endgame:
                                revealed.add((r, c))
                            elif not show_obstacles:
                                flash_obstacles.append(((r, c), time.time()))
                            if maze["return_to_start"]:
                                knight_pos = maze["start"]
                                move_count = 0
                                move_numbers = {knight_pos: 0}
                                visited = set([knight_pos])
                                if show_obstacles:
                                    revealed = set()
                        else:
                            move_count += 1
                            move_numbers[knight_pos] = move_count - 1
                            knight_pos = (r, c)
                            visited.add(knight_pos)
                            if knight_pos == target:
                                won = True
                                endgame = True
                                stop_time = time.time()
                                move_numbers[knight_pos] = move_count
        now = time.time()
        flash_obstacles = [(fo, ts) for fo, ts in flash_obstacles if now - ts < obstacle_flash_time] if obstacle_flash_time else []
        if started and not endgame:
            if stop_time is not None:
                elapsed = int(stop_time - start_time)
            else:
                elapsed = int(time.time() - start_time)
            if timer_type == "stopwatch":
                timer_text = f"Time: {elapsed//60}:{elapsed%60:02d}"
                time_up = False
            else:
                time_left = max(0, timer_length - elapsed)
                timer_text = f"Time left: {time_left//60}:{time_left%60:02d}"
                time_up = time_left == 0
                if time_up and not endgame:
                    endgame = True
                    stop_time = time.time()
        elif started and endgame:
            elapsed = int(stop_time - start_time) if stop_time is not None else 0
            if timer_type == "stopwatch":
                timer_text = f"Time: {elapsed//60}:{elapsed%60:02d}"
            else:
                timer_text = f"Time left: {max(0, timer_length - elapsed)//60}:{max(0, timer_length - elapsed)%60:02d}"
        else:
            timer_text = "Time: 0:00" if timer_type == "stopwatch" else f"Time left: {timer_length//60}:00"
            time_up = False

        screen.fill((50, 50, 50))
        if endgame:
            revealed_end = obstacles.copy()
            if not show_obstacles:
                revealed_end |= {fo for fo, ts in flash_obstacles}
            draw_board(screen, board_w, board_h, knight_pos, target, obstacles, revealed_end, move_numbers, True, maze_path=maze_path, endgame=True)
        else:
            if not show_obstacles and flash_obstacles:
                temp_revealed = revealed | {fo for fo, ts in flash_obstacles}
                draw_board(screen, board_w, board_h, knight_pos, target, obstacles, temp_revealed, move_numbers, True)
            else:
                draw_board(screen, board_w, board_h, knight_pos, target, obstacles, revealed, move_numbers, show_obstacles)
            draw_stuck_button(screen, board_w, board_h)
        screen.blit(font.render(timer_text, True, (255,255,255)), (MARGIN, MARGIN + board_h*SQUARE_SIZE + 10))
        screen.blit(info_font.render("Blue: Knight  Green: Target  Red: Revealed Obstacle", True, (255,255,255)), (MARGIN, MARGIN + board_h*SQUARE_SIZE + 50))
        if endgame:
            if won:
                screen.blit(font.render("Congratulations! You solved the Knight's Maze!", True, (255,255,0)), (MARGIN, MARGIN - 36))
            elif time_up:
                screen.blit(font.render("Time's up! Game over.", True, (255,0,0)), (MARGIN, MARGIN - 36))
            elif stuck:
                screen.blit(font.render("Stuck! Maze revealed.", True, (255,0,255)), (MARGIN, MARGIN - 36))
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()

if __name__ == "__main__":
    main()