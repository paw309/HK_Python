import sys

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

def num_knight_paths(n, start, end):
    from collections import deque
    queue = deque()
    queue.append((start[0], start[1]))
    visited = [[-1 for _ in range(n)] for _ in range(n)]
    paths = [[0 for _ in range(n)] for _ in range(n)]

    visited[start[0]][start[1]] = 0
    paths[start[0]][start[1]] = 1

    while queue:
        r, c = queue.popleft()
        for dr, dc in knight_moves():
            nr, nc = r + dr, c + dc
            if is_valid(nr, nc, n):
                if visited[nr][nc] == -1:
                    visited[nr][nc] = visited[r][c] + 1
                    paths[nr][nc] = paths[r][c]
                    queue.append((nr, nc))
                elif visited[nr][nc] == visited[r][c] + 1:
                    paths[nr][nc] += paths[r][c]
    return visited[end[0]][end[1]], paths[end[0]][end[1]]

def find_knight_path_exact_x(n, start, end, x):
    # Backtracking search for a simple path of length x
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
    x_input = input("Enter exact number of moves (x) for the path: ").strip()
    x = int(x_input)

    try:
        start_coords = algebraic_to_coords(start_square)
        end_coords = algebraic_to_coords(end_square)
    except Exception:
        print("Invalid square format. Please use algebraic notation like 'a1'.")
        sys.exit(1)

    if not (is_valid(start_coords[0], start_coords[1], n) and is_valid(end_coords[0], end_coords[1], n)):
        print("One or both squares are outside the board.")
        sys.exit(1)

    min_moves, num_paths = num_knight_paths(n, start_coords, end_coords)
    if min_moves == -1:
        print(f"No path from {start_square} to {end_square} exists.")
    else:
        print(f"Minimum moves: {min_moves}")
        print(f"Number of shortest paths: {num_paths}")

    path = find_knight_path_exact_x(n, start_coords, end_coords, x)
    if path:
        print(f"Path of exactly {x} moves from {start_square} to {end_square} (no repeats):")
        print(" -> ".join(coords_to_algebraic(r, c) for r, c in path))
    else:
        print(f"No simple path of exactly {x} moves from {start_square} to {end_square} was found.")

if __name__ == "__main__":
    main()
