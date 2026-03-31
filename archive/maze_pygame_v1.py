import pygame
import random
import time
from collections import deque

# ---- Game settings ----
BOARD_W, BOARD_H = 8, 8  # You can change these in 6-16 range
SQUARE_SIZE = 64
MARGIN = 40
FPS = 30

# ---- Knight movement ----
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

def find_knight_path_exact_x(m, n, start, end, x):
    def backtrack(r, c, depth, path, visited):
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
                result = backtrack(nr, nc, depth + 1, path, visited)
                if result:
                    return result
                path.pop()
                visited[nr][nc] = False
        return None
    visited = [[False for _ in range(n)] for _ in range(m)]
    visited[start[0]][start[1]] = True
    path = [start]
    return backtrack(start[0], start[1], 0, path, visited)

def squares_one_move_away(m, n, square):
    result = set()
    r, c = square
    for dr, dc in knight_moves():
        nr, nc = r + dr, c + dc
        if is_valid(nr, nc, m, n):
            result.add((nr, nc))
    return result

def random_square(m, n):
    return (random.randint(0, m-1), random.randint(0, n-1))

def coords_to_algebraic(row, col):
    return f"{chr(col + ord('a'))}{row + 1}"

def generate_maze(m=BOARD_W, n=BOARD_H):
    # 1. Generate start/target squares
    while True:
        start = random_square(m, n)
        target = random_square(m, n)
        if start != target:
            y, dist_matrix = min_moves_and_dist_matrix(m, n, start, target)
            if y >= 2:
                break
    min_x = m // 2 + y
    max_x = m + y
    parity = y % 2
    possible_x = [x for x in range(min_x, max_x + 1) if x % 2 == parity]
    random.shuffle(possible_x)
    x = possible_x[0]
    tries = 0
    while True:
        maze_path = find_knight_path_exact_x(m, n, start, target, x)
        tries += 1
        if maze_path:
            if y == 2:
                sqrs_one_from_target = squares_one_move_away(m, n, target)
                if maze_path[1] not in sqrs_one_from_target:
                    break
            else:
                break
        if tries > 1000:
            raise Exception("Maze path generation failed!")
    # Find shortest path squares (BFS layers)
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
    maze_path_set = set(maze_path)
    obstacles = set()
    for sq in shortest_path_layer:
        if sq not in maze_path_set:
            obstacles.add(sq)
    return {
        "board_size": (m, n),
        "start": start,
        "target": target,
        "maze_path": maze_path,
        "obstacles": obstacles
    }

# ---- Pygame GUI ----
def draw_board(screen, board_w, board_h, knight_pos, target, obstacles, revealed, path):
    for r in range(board_h):
        for c in range(board_w):
            x = MARGIN + c*SQUARE_SIZE
            y = MARGIN + r*SQUARE_SIZE
            rect = pygame.Rect(x, y, SQUARE_SIZE, SQUARE_SIZE)
            if (r + c) % 2 == 0:
                color = (240, 217, 181)
            else:
                color = (181, 136, 99)
            pygame.draw.rect(screen, color, rect)
            # Draw revealed obstacles
            if (r, c) in revealed:
                pygame.draw.rect(screen, (128, 0, 0), rect)
            # Draw target
            if (r, c) == target:
                pygame.draw.circle(screen, (0, 255, 0), rect.center, SQUARE_SIZE//3)
            # Draw maze path
            if (r, c) in path:
                pygame.draw.rect(screen, (173, 216, 230), rect, 4)
            # Draw start
            if (r, c) == knight_pos:
                pygame.draw.circle(screen, (0, 0, 255), rect.center, SQUARE_SIZE//3)
    # Draw grid
    for r in range(board_h+1):
        pygame.draw.line(screen, (0,0,0), (MARGIN, MARGIN + r*SQUARE_SIZE), (MARGIN + board_w*SQUARE_SIZE, MARGIN + r*SQUARE_SIZE), 2)
    for c in range(board_w+1):
        pygame.draw.line(screen, (0,0,0), (MARGIN + c*SQUARE_SIZE, MARGIN), (MARGIN + c*SQUARE_SIZE, MARGIN + board_h*SQUARE_SIZE), 2)

def main():
    pygame.init()
    maze = generate_maze()
    board_w, board_h = maze["board_size"]
    screen = pygame.display.set_mode((MARGIN*2 + board_w*SQUARE_SIZE, MARGIN*2 + board_h*SQUARE_SIZE + 80))
    pygame.display.set_caption("The Knight's Maze")
    clock = pygame.time.Clock()

    knight_pos = maze["start"]
    target = maze["target"]
    obstacles = maze["obstacles"]
    maze_path = maze["maze_path"]
    revealed = set()
    started = False
    start_time = None
    won = False

    font = pygame.font.SysFont(None, 36)
    info_font = pygame.font.SysFont(None, 28)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and not won:
                mx, my = event.pos
                if MARGIN <= mx < MARGIN + board_w*SQUARE_SIZE and MARGIN <= my < MARGIN + board_h*SQUARE_SIZE:
                    c = (mx - MARGIN) // SQUARE_SIZE
                    r = (my - MARGIN) // SQUARE_SIZE
                    if (r, c) == knight_pos:
                        continue
                    if (r, c) in squares_one_move_away(board_h, board_w, knight_pos):
                        if not started:
                            started = True
                            start_time = time.time()
                        if (r, c) in obstacles:
                            revealed.add((r, c))
                        else:
                            knight_pos = (r, c)
                            if knight_pos == target:
                                won = True
        screen.fill((50, 50, 50))
        draw_board(screen, board_w, board_h, knight_pos, target, obstacles, revealed, maze_path)
        # Info
        if started:
            elapsed = int(time.time() - start_time)
            timer_text = f"Time: {elapsed//60}:{elapsed%60:02d}"
        else:
            timer_text = "Time: 0:00"
        screen.blit(font.render(timer_text, True, (255,255,255)), (MARGIN, MARGIN + board_h*SQUARE_SIZE + 10))
        screen.blit(info_font.render("Blue: Knight  Green: Target  Red: Revealed Obstacle", True, (255,255,255)), (MARGIN, MARGIN + board_h*SQUARE_SIZE + 50))
        if won:
            screen.blit(font.render("Congratulations! You solved the Knight's Maze!", True, (255,255,0)), (MARGIN, MARGIN - 36))
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()

if __name__ == "__main__":
    main()