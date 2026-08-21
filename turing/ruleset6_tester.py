import random
import sys
sys.setrecursionlimit(100000)

# ───────────────────────────────────────────────────────────────
#  Movement definitions for all pieces
# ───────────────────────────────────────────────────────────────

MOVES = {
    "wazir":        [(1,0), (-1,0), (0,1), (0,-1)],
    "ferz":         [(1,1), (1,-1), (-1,1), (-1,-1)],
    "dabbaba":      [(2,0), (-2,0), (0,2), (0,-2)],
    "alfil":        [(2,2), (2,-2), (-2,2), (-2,-2)],
    "threeleaper":  [(3,0), (-3,0), (0,3), (0,-3)],
    "knight":       [(2,1), (2,-1), (-2,1), (-2,-1),
                     (1,2), (1,-2), (-1,2), (-1,-2)],
    "camel":        [(3,1), (3,-1), (-3,1), (-3,-1),
                     (1,3), (1,-3), (-1,3), (-1,-3)],
    "giraffe":      [(4,1), (4,-1), (-4,1), (-4,-1),
                     (1,4), (1,-4), (-1,4), (-1,-4)],
    "zebra":        [(3,2), (3,-2), (-3,2), (-3,-2),
                     (2,3), (2,-3), (-2,3), (-2,-3)],
    "king":         [(1,0), (-1,0), (0,1), (0,-1),
                     (1,1), (1,-1), (-1,1), (-1,-1)],
}

# ───────────────────────────────────────────────────────────────
#  Rule 6: color‑controlled reversible 3‑state machine
# ───────────────────────────────────────────────────────────────

def square_color(r, c):
    return "white" if (r + c) % 2 == 0 else "black"

def rule6_next(piece_index, r, c):
    color = square_color(r, c)
    if piece_index == 1:
        return 2 if color == "white" else 3
    if piece_index == 2:
        return 3 if color == "white" else 1
    if piece_index == 3:
        return 1 if color == "white" else 2
    raise ValueError("Invalid piece index")

# ───────────────────────────────────────────────────────────────
#  Warnsdorff-style heuristic: order moves by onward degree
# ───────────────────────────────────────────────────────────────

def onward_degree(board_size, triplet, r, c, piece_index, visited):
    """Count how many moves are available from (r,c) with given piece_index."""
    moves = MOVES[triplet[piece_index - 1]]
    count = 0
    for dr, dc in moves:
        nr, nc = r + dr, c + dc
        if 0 <= nr < board_size and 0 <= nc < board_size and (nr, nc) not in visited:
            count += 1
    return count

# ───────────────────────────────────────────────────────────────
#  Randomized DFS Hamiltonian search with node cap
# ───────────────────────────────────────────────────────────────

def find_hamiltonian(board_size, triplet, tries=1000, max_nodes_per_attempt=50000):
    success_count = 0
    total_squares = board_size * board_size

    for _ in range(tries):
        start_r = random.randrange(board_size)
        start_c = random.randrange(board_size)

        visited = set()
        visited.add((start_r, start_c))

        piece_index = 1
        nodes_used = 0

        def dfs(r, c, depth, piece_index):
            nonlocal nodes_used
            if depth == total_squares:
                return True
            if nodes_used > max_nodes_per_attempt:
                return False

            nodes_used += 1

            moves = MOVES[triplet[piece_index - 1]]

            # Generate candidate moves
            candidates = []
            for dr, dc in moves:
                nr, nc = r + dr, c + dc
                if 0 <= nr < board_size and 0 <= nc < board_size:
                    if (nr, nc) not in visited:
                        next_piece = rule6_next(piece_index, nr, nc)
                        deg = onward_degree(board_size, triplet, nr, nc, next_piece, visited)
                        candidates.append((deg, nr, nc, next_piece))

            # Warnsdorff-style: sort by onward degree (fewest first), then randomize ties
            random.shuffle(candidates)
            candidates.sort(key=lambda x: x[0])

            for _, nr, nc, next_piece in candidates:
                visited.add((nr, nc))
                if dfs(nr, nc, depth + 1, next_piece):
                    return True
                visited.remove((nr, nc))

            return False

        if dfs(start_r, start_c, 1, piece_index):
            success_count += 1

    return success_count

# ───────────────────────────────────────────────────────────────
#  Triplets (1,2,3)
# ───────────────────────────────────────────────────────────────

TRIPLETS = {
    "T01": ["wazir", "knight", "king"],
    "T02": ["wazir", "camel", "king"],
    "T03": ["wazir", "zebra", "king"],
    "T04": ["wazir", "giraffe", "king"],
    "T05": ["threeleaper", "knight", "king"],
    "T06": ["threeleaper", "camel", "king"],
    "T07": ["threeleaper", "zebra", "king"],
    "T08": ["threeleaper", "giraffe", "king"],
}

BOARD_SIZES = [5, 6, 7, 8]

# ───────────────────────────────────────────────────────────────
#  Run tests ##
# ───────────────────────────────────────────────────────────────

def main():
    tries = 5000  # you can lower this while experimenting
    max_nodes = 5000  # per attempt; tune if still slow

    for name, triplet in TRIPLETS.items():
        print(f"\n=== {name}: {triplet} ===")
        for size in BOARD_SIZES:
            successes = find_hamiltonian(size, triplet, tries=tries, max_nodes_per_attempt=max_nodes)
            print(f"  Board {size}x{size}: {successes} successful paths")

if __name__ == "__main__":
    main()
