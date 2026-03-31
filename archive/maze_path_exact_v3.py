import sys
from collections import deque

def algebraic_to_coords(square):
    col = ord(square[0].lower()) - ord('a')
    row = int(square[1:]) - 1
    return row, col

def coords_to_algebraic(row, col):
    return f"{chr(col + ord('a'))}{row + 1}"

def is_valid(r, c, n):
    return 0 <= r < n and 0 <= c < n

def knight_moves():
    return [
        (2, 1), (1, 2), (-1, 2), (-2, 1),
        (-2, -1), (-1, -2), (1, -2), (2, -1)
    ]

def min_moves_and_dist_matrix(n, start, end):
    # BFS to get minimum moves and distance matrix
    queue = deque()
    queue.append(start)
    dist = [[-1 for _ in range(n)] for _ in range(n)]
    dist[start[0]][start[1]] = 0
    while queue:
        r, c = queue.popleft()
        if (r, c) == end:
            break
        for dr, dc in knight_moves():
            nr, nc = r + dr, c + dc
            if is_valid(nr, nc, n) and dist[nr][nc] == -1:
                dist[nr][nc] = dist[r][c] + 1
                queue.append((nr, nc))
    return dist[end[0]][end[1]], dist

def count_shortest_paths_and_unique_squares(n, start, end, min_moves, dist):
    # Backtrack all shortest paths, collect unique squares
    squares_on_shortest = set()
    num_paths = [0]

    def backtrack(current, path):
        r, c = current
        path.append((r, c))
        if len(path)-1 > min_moves:
            path.pop()
            return
        if current == end and len(path)-1 == min_moves:
            squares_on_shortest.update(path)
            num_paths[0] += 1
            path.pop()
            return
        for dr, dc in knight_moves():
            nr, nc = r + dr, c + dc
            if is_valid(nr, nc, n) and dist[nr][nc] == dist[r][c] + 1:
                backtrack((nr, nc), path)
        path.pop()

    backtrack(start, [])
    return num_paths[0], squares_on_shortest

def find_knight_path_exact_x(n, start, end, x):
    # Backtracking for a simple path of length x
    def backtrack(r, c, depth, path, visited):
        if depth > x:
            return None
        if depth == x and (r, c) == end:
            return path[:]
        for dr, dc in knight_moves():
            nr, nc = r + dr, c + dc
            if is_valid(nr, nc, n) and not visited[nr][nc]:
                visited[nr][nc] = True
                path.append((nr, nc))
                result = backtrack(nr, nc, depth + 1, path, visited)
                if result:
                    return result
                path.pop()
                visited[nr][nc] = False
        return None

    visited = [[False for _ in range(n)] for _ in range(n)]
    visited[start[0]][start[1]] = True
    path = [start]
    return backtrack(start[0], start[1], 0, path, visited)

def main():
    print("Knight Paths Calculator (simple path, exact-move search)")
    board_size_input = input("Enter board size (n for n x n board, or just press enter for 8): ").strip()
    n = 8 if board_size_input == "" else int(board_size_input)
    start_square = input(f"Enter start square (e.g., a1): ").strip()
    end_square = input(f"Enter end square (e.g., c5): ").strip()

    try:
        start_coords = algebraic_to_coords(start_square)
        end_coords = algebraic_to_coords(end_square)
    except Exception:
        print("Invalid square format. Please use algebraic notation like 'a1'.")
        sys.exit(1)

    if not (is_valid(start_coords[0], start_coords[1], n) and is_valid(end_coords[0], end_coords[1], n)):
        print("One or both squares are outside the board.")
        sys.exit(1)

    min_moves, dist_matrix = min_moves_and_dist_matrix(n, start_coords, end_coords)
    if min_moves == -1:
        print(f"No path from {start_square} to {end_square} exists.")
        return

    num_paths, squares_shortest = count_shortest_paths_and_unique_squares(n, start_coords, end_coords, min_moves, dist_matrix)
    print(f"Minimum moves: {min_moves}")
    print(f"Number of shortest paths: {num_paths}")
    print(f"Number of unique squares in all shortest paths: {len(squares_shortest)}\n")

    x_input = input("Enter exact number of moves (x) for the path: ").strip()
    x = int(x_input)

    path = find_knight_path_exact_x(n, start_coords, end_coords, x)
    if path:
        print(f"\nPath of exactly {x} moves from {start_square} to {end_square} (no repeats):")
        print(f"{'Move #':<7} {'Square':<6}")
        print("-" * 15)
        for idx, (r, c) in enumerate(path):
            print(f"{idx:<7} {coords_to_algebraic(r, c):<6}")
    else:
        print(f"No simple path of exactly {x} moves from {start_square} to {end_square} was found.")

    path_set = set(path) if path else set()
    squares_intersection = squares_shortest & path_set

    print("\nSquares on both a shortest path and the generated path:")
    for (r, c) in sorted(squares_intersection):
        print(coords_to_algebraic(r, c), end=" ")
    print("\n")

if __name__ == "__main__":
    main()