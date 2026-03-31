import random
import time
from collections import deque

# --- Utility functions from previous script ---
def algebraic_to_coords(square):
    col = ord(square[0].lower()) - ord('a')
    row = int(square[1:]) - 1
    return row, col

def coords_to_algebraic(row, col):
    return f"{chr(col + ord('a'))}{row + 1}"

def is_valid(r, c, m, n):
    return 0 <= r < m and 0 <= c < n

def knight_moves():
    return [
        (2, 1), (1, 2), (-1, 2), (-2, 1),
        (-2, -1), (-1, -2), (1, -2), (2, -1)
    ]

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

# --- Maze Game Setup ---
def random_square(m, n):
    return (random.randint(0, m-1), random.randint(0, n-1))

def squares_one_move_away(m, n, square):
    result = set()
    r, c = square
    for dr, dc in knight_moves():
        nr, nc = r + dr, c + dc
        if is_valid(nr, nc, m, n):
            result.add((nr, nc))
    return result

def generate_game_board(m=8, n=8, obstacle_mode="normal", timer_mode="stopwatch"):
    # 1. Generate start and target squares
    while True:
        start = random_square(m, n)
        target = random_square(m, n)
        if start != target:
            y, dist_matrix = min_moves_and_dist_matrix(m, n, start, target)
            if y >= 2:
                break

    print(f"Start: {coords_to_algebraic(*start)}, Target: {coords_to_algebraic(*target)}, Minimum moves (y): {y}")

    # 2. Calculate allowed maze path length
    min_x = m // 2 + y
    max_x = m + y
    parity = y % 2
    possible_x = [x for x in range(min_x, max_x + 1) if x % 2 == parity]
    random.shuffle(possible_x)
    x = possible_x[0]

    # 3. Generate maze path
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
        if tries > 1000:  # avoid infinite loop
            raise Exception("Could not generate a maze path with constraints.")

    print(f"Maze path length (x): {x}")
    print(f"Maze path: {[coords_to_algebraic(*sq) for sq in maze_path]}")

    # 4. Find shortest path squares
    # Use BFS/backtracking to enumerate shortest path squares
    # For simplicity, use BFS layers to approximate all shortest path squares
    # (For full enumeration, see previous scripts)
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

    # 5. Obstacles on shortest path not in maze path
    maze_path_set = set(maze_path)
    obstacles = set()
    for sq in shortest_path_layer:
        if sq not in maze_path_set:
            obstacles.add(sq)

    # 6. Optionally add random obstacles
    remaining_squares = {(r, c) for r in range(m) for c in range(n)} - maze_path_set - obstacles
    extra_obstacles = set()
    if obstacle_mode == "extra":
        num_extra = random.randint(int(0.1 * len(remaining_squares)), max(1, int(0.5 * len(remaining_squares))))
        extra_obstacles = set(random.sample(list(remaining_squares), num_extra))
        print(f"Extra obstacles placed: {num_extra}")

    total_obstacles = obstacles | extra_obstacles
    print(f"Obstacles: {[coords_to_algebraic(*sq) for sq in total_obstacles]}")

    # 7. Output all game settings
    return {
        "board_size": (m, n),
        "start": start,
        "target": target,
        "maze_path": maze_path,
        "obstacles": total_obstacles,
        "stopwatch": timer_mode == "stopwatch",
        "countdown": timer_mode == "countdown"
    }

if __name__ == "__main__":
    # Example usage
    game_settings = generate_game_board()
    # You can now use game_settings to implement the actual gameplay loop!