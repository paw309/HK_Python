import time

# --- Move Vectors Definition ---
PIECE_VECTORS = {
    "KNIGHT": [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)],
    "KING": [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)],
    "WAZIR": [(0, 1), (1, 0), (0, -1), (-1, 0)],
    "FERZ": [(1, 1), (1, -1), (-1, 1), (-1, -1)],
    "DABBABA": [(0, 2), (2, 0), (0, -2), (-2, 0)],
    "ALFIL": [(2, 2), (2, -2), (-2, 2), (-2, -2)],
    "THREELEAPER": [(0, 3), (3, 0), (0, -3), (-3, 0)],
    "TRIPPER": [(3, 3), (3, -3), (-3, 3), (-3, -3)],
    "CAMEL": [(1, 3), (3, 1), (-1, 3), (-3, 1), (1, -3), (3, -1), (-1, -3), (-3, -1)],
    "ZEBRA": [(2, 3), (3, 2), (-2, 3), (-3, 2), (2, -3), (3, -2), (-2, -3), (-3, -2)],
    "GIRAFFE": [(1, 4), (4, 1), (-1, 4), (-4, 1), (1, -4), (4, -1), (-1, -4), (-4, -1)],
}

RULESETS = ["2-cycle", "3-cycle", "4-cycle", "6-cycle"]


# --- State Transition Engine ---
def get_next_state(ruleset_name, active_idx, target_r, target_c):
    """Calculates the next piece index based on ruleset logic."""
    is_dark = (target_r + target_c) % 2 == 1

    if ruleset_name == "2-cycle":
        return (active_idx + 1) % 2

    elif ruleset_name == "3-cycle":
        return (active_idx + 1) % 3

    elif ruleset_name == "4-cycle":
        # Linear 4-piece state rotation: 0 -> 1 -> 2 -> 3 -> 0
        return (active_idx + 1) % 4

    elif ruleset_name == "6-cycle":
        # 6-cycle (color-based) transition logic:
        # A + black -> B, A + white -> C
        # B + black -> C, B + white -> A
        # C + black -> A, C + white -> B
        if active_idx == 0:
            return 1 if is_dark else 2
        elif active_idx == 1:
            return 2 if is_dark else 0
        else:  # active_idx == 2
            return 0 if is_dark else 1


# --- Graph Generator ---
def get_legal_moves(r, c, piece_name, visited_mask, board_size):
    """Generates all legal, unvisited target squares for a given piece position."""
    moves = []
    for dr, dc in PIECE_VECTORS[piece_name]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < board_size and 0 <= nc < board_size:
            idx = nr * board_size + nc
            if not (visited_mask & (1 << idx)):
                moves.append((nr, nc, idx))
    return moves


# --- Solver Algorithm ---
def find_hamiltonian_path(board_size, ruleset_name, pieces, start_r, start_c):
    """Depth-First Search enhanced with Warnsdorff's lookahead heuristic."""
    total_squares = board_size * board_size
    target_mask = (1 << total_squares) - 1
    start_idx = start_r * board_size + start_c
    initial_visited = 1 << start_idx

    def dfs(r, c, active_piece_idx, visited_mask, path):
        if visited_mask == target_mask:
            return path

        legal_targets = get_legal_moves(r, c, pieces[active_piece_idx], visited_mask, board_size)

        # Warnsdorff's Heuristic: Evaluate legal options by their onward degree
        branch_options = []
        for nr, nc, n_idx in legal_targets:
            next_p_idx = get_next_state(ruleset_name, active_piece_idx, nr, nc)
            next_visited = visited_mask | (1 << n_idx)

            # Count onward options for Warnsdorff sorting
            onward_moves = len(get_legal_moves(nr, nc, pieces[next_p_idx], next_visited, board_size))
            branch_options.append((onward_moves, nr, nc, n_idx, next_p_idx, next_visited))

        # Sort by lowest onward degree first (Warnsdorff heuristic)
        branch_options.sort(key=lambda x: x[0])

        for degree, nr, nc, n_idx, next_p_idx, next_visited in branch_options:
            path.append((nr, nc, pieces[next_p_idx]))
            result = dfs(nr, nc, next_p_idx, next_visited, path)
            if result:
                return result
            path.pop()  # Backtrack

        return None

    initial_path = [(start_r, start_c, pieces[0])]
    return dfs(start_r, start_c, 0, initial_visited, initial_path)


# --- Interactive Terminal Interface ---
def main():
    print("==================================================")
    print("  KNIGHT'S TURING MACHINE — HAMILTONIAN SOLVER   ")
    print("==================================================\n")

    # 1. Select Board Size
    while True:
        try:
            board_size = int(input("Select Board Size (5 to 8): "))
            if 5 <= board_size <= 8:
                break
            print("Please enter an integer between 5 and 8.")
        except ValueError:
            print("Invalid input. Enter a number.")

    # 2. Select Ruleset
    print("\nAvailable Rulesets:")
    for idx, r in enumerate(RULESETS, 1):
        print(f"  {idx}. {r}")

    while True:
        try:
            r_choice = int(input("Select Ruleset (1-4): "))
            if 1 <= r_choice <= 4:
                ruleset_name = RULESETS[r_choice - 1]
                break
            print("Please enter a number between 1 and 4.")
        except ValueError:
            print("Invalid input.")

    # 3. Select Pieces Dynamically Based on Ruleset
    piece_names = list(PIECE_VECTORS.keys())
    if ruleset_name == "2-cycle":
        required_pieces = 2
    elif ruleset_name == "4-cycle":
        required_pieces = 4
    else:  # 3-cycle or 6-cycle
        required_pieces = 3

    print(f"\nSelect {required_pieces} pieces from the roster:")
    for idx, p in enumerate(piece_names, 1):
        print(f"  {idx:2d}. {p}")

    chosen_pieces = []
    for i in range(required_pieces):
        while True:
            try:
                p_choice = int(input(f"Select Piece {i + 1} (1-11): "))
                if 1 <= p_choice <= 11:
                    chosen_pieces.append(piece_names[p_choice - 1])
                    break
                print("Please enter a number between 1 and 11.")
            except ValueError:
                print("Invalid input.")

    print(f"\n---> Testing Config: Board {board_size}x{board_size} | {ruleset_name} | Pieces: {chosen_pieces}")
    print("Searching for a Hamiltonian path across all starting squares...")

    start_time = time.time()
    solution_found = False

    # Check all possible starting squares on the board
    for r in range(board_size):
        for c in range(board_size):
            path = find_hamiltonian_path(board_size, ruleset_name, chosen_pieces, r, c)
            if path:
                elapsed = (time.time() - start_time) * 1000
                print(f"\n✅ SOLVABLE! Path found in {elapsed:.2f} ms.")
                print(f"Starting Square: ({r}, {c}) with Piece: {chosen_pieces[0]}\n")

                show_path = input("Display step-by-step path sequence? (y/n): ").strip().lower()
                if show_path == 'y':
                    print("\nStep-by-step solution path:")
                    for step_idx, (pr, pc, piece) in enumerate(path, 1):
                        coord = f"({pr},{pc})"
                        print(f"  Step {step_idx:2d}: {coord:7s} | Active Piece: {piece}")

                solution_found = True
                break
        if solution_found:
            break

    if not solution_found:
        elapsed = (time.time() - start_time) * 1000
        print(f"\n❌ UNSOLVABLE. Checked all starting positions in {elapsed:.2f} ms.")
        print("No complete Hamiltonian path exists for this configuration.")


if __name__ == "__main__":
    main()