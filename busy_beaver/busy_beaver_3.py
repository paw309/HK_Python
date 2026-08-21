# 2×11 strict 3-cycle Hamiltonian path enumerator with symmetry reduction
# User chooses 3 pieces; script enumerates ALL tours.
# user input: 1, 2
# if user input is 1, run the script as it is now
# if user input is 2:
#   test every permutation of 7 pieces
#   write the result to a csv file with separate columns for each piece and the number of paths found
#   write a permutation even if there are zero paths
#   also write the same information to the console

import csv
import itertools
import sys

ROWS = 2
COLS = 11

def idx(r, c):
    return r * COLS + c

def rc(i):
    return divmod(i, COLS)

# --- Move generators ---
def knight_moves(r, c):
    out = []
    for dr, dc in [(1,2),(1,-2),(-1,2),(-1,-2)]:
        rr, cc = r+dr, c+dc
        if 0 <= rr < ROWS and 0 <= cc < COLS:
            out.append(idx(rr,cc))
    return out

def wazir_moves(r, c):
    out = []
    for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
        rr, cc = r+dr, c+dc
        if 0 <= rr < ROWS and 0 <= cc < COLS:
            out.append(idx(rr,cc))
    return out

def ferz_moves(r, c):
    out = []
    for dr, dc in [(1,1),(1,-1),(-1,1),(-1,-1)]:
        rr, cc = r+dr, c+dc
        if 0 <= rr < ROWS and 0 <= cc < COLS:
            out.append(idx(rr,cc))
    return out

def king_moves(r, c):
    out = []
    for dr in [-1,0,1]:
        for dc in [-1,0,1]:
            if dr == 0 and dc == 0:
                continue
            rr, cc = r+dr, c+dc
            if 0 <= rr < ROWS and 0 <= cc < COLS:
                out.append(idx(rr,cc))
    return out

def dabbaba_moves(r, c):
    out = []
    for dr, dc in [(2,0),(-2,0),(0,2),(0,-2)]:
        rr, cc = r+dr, c+dc
        if 0 <= rr < ROWS and 0 <= cc < COLS:
            out.append(idx(rr,cc))
    return out

def threeleaper_moves(r, c):
    out = []
    for dr, dc in [(3,0),(-3,0),(0,3),(0,-3)]:
        rr, cc = r+dr, c+dc
        if 0 <= rr < ROWS and 0 <= cc < COLS:
            out.append(idx(rr,cc))
    return out

def camel_moves(r, c):
    out = []
    for dr, dc in [(1,3),(1,-3),(-1,3),(-1,-3),(3,1),(3,-1),(-3,1),(-3,-1)]:
        rr, cc = r+dr, c+dc
        if 0 <= rr < ROWS and 0 <= cc < COLS:
            out.append(idx(rr,cc))
    return out

def giraffe_moves(r, c):
    out = []
    for dr, dc in [(1,4),(1,-4),(-1,4),(-1,-4),(4,1),(4,-1),(-4,1),(-4,-1)]:
        rr, cc = r+dr, c+dc
        if 0 <= rr < ROWS and 0 <= cc < COLS:
            out.append(idx(rr,cc))
    return out

def stork_moves(r, c):
    out = []
    for dr, dc in [(1,5),(1,-5),(-1,5),(-1,-5),(5,1),(5,-1),(-5,1),(-5,-1)]:
        rr, cc = r+dr, c+dc
        if 0 <= rr < ROWS and 0 <= cc < COLS:
            out.append(idx(rr,cc))
    return out

MOVESETS = {
    "knight": knight_moves,
    "king": king_moves,
    "wazir": wazir_moves,
    "ferz": ferz_moves,
    "dabbaba": dabbaba_moves,
    "threeleaper": threeleaper_moves,
    "camel": camel_moves,
    "giraffe": giraffe_moves,
    "stork": stork_moves,
}

PIECE_CODES = {
    "knight": "N",
    "king": "K",
    "wazir": "W",
    "ferz": "F",
    "dabbaba": "D",
    "threeleaper": "T",
    "camel": "C",
    "giraffe": "G",
    "stork": "S",
}

# --- Symmetry operations ---
def reflect_horizontal(i):
    r, c = rc(i)
    return idx(r, COLS-1-c)

def reflect_vertical(i):
    r, c = rc(i)
    return idx(ROWS-1-r, c)

def symmetry_orbit(i):
    a = i
    b = reflect_horizontal(i)
    c = reflect_vertical(i)
    d = reflect_vertical(reflect_horizontal(i))
    return {a, b, c, d}

# --- DFS enumeration ---
def enumerate_tours(pieces):
    A, B, C = pieces
    pattern = [A, B, C] * 7  # 21 moves

    # Precompute moves
    moves = {p: {} for p in pieces}
    for p in pieces:
        gen = MOVESETS[p]
        for i in range(22):
            r, c = rc(i)
            moves[p][i] = gen(r, c)

    # Canonical starting squares
    canonical_starts = []
    for i in range(22):
        if i == min(symmetry_orbit(i)):
            canonical_starts.append(i)

    all_tours = []

    for start in canonical_starts:
        used = [False]*22
        used[start] = True
        path = [start]
        dfs(1, start, used, path, pattern, moves, all_tours)

    return all_tours

def dfs(step, current, used, path, pattern, moves, all_tours):
    if step == 22:
        all_tours.append(path.copy())
        return

    piece = pattern[step-1]
    for nxt in moves[piece][current]:
        if not used[nxt]:
            used[nxt] = True
            path.append(nxt)
            dfs(step+1, nxt, used, path, pattern, moves, all_tours)
            path.pop()
            used[nxt] = False

# --- Main ---
def run_mode_1():
    print("Enter three pieces (space-separated):")
    print("Choices: knight, king, wazir, ferz, dabbaba, threeleaper, camel, giraffe, stork")
    pieces = input("Pieces: ").strip().split()

    if len(pieces) != 3 or any(p not in MOVESETS for p in pieces):
        print("Invalid input.")
        sys.exit(1)

    print(f"\nSearching for strict repeating pattern: {pieces[0]} → {pieces[1]} → {pieces[2]} → ...\n")

    tours = enumerate_tours(pieces)

    if not tours:
        print("No Hamiltonian tours found.")
        sys.exit(0)

    print(f"FOUND {len(tours)} TOURS:\n")

    for tnum, tour in enumerate(tours, start=1):
        print(f"--- Tour {tnum} ---")
        grid = [[0]*COLS for _ in range(ROWS)]
        for move_num, square in enumerate(tour, start=1):
            r, c = rc(square)
            grid[r][c] = move_num
        for r in range(ROWS):
            print(" ".join(f"{grid[r][c]:2d}" for c in range(COLS)))
        print()


def run_mode_2():
    csv_filename = "busy_beaver_3_results.csv"
    py_filename = "../../pyversion/knightsturing/busy_beaver_3_tours.py"
    piece_names = list(MOVESETS.keys())
    header = ["piece1", "piece2", "piece3", "paths_found"]

    print(f"Testing all permutations of 3 pieces from {piece_names}\n")
    print(f"{'piece1':<14} {'piece2':<14} {'piece3':<14} {'paths_found':>11}")
    print("-" * 57)

    rows = []
    all_tours_dict = {}
    for pieces in itertools.permutations(piece_names, 3):
        tours = enumerate_tours(list(pieces))
        count = len(tours)
        rows.append([pieces[0], pieces[1], pieces[2], count])
        print(f"{pieces[0]:<14} {pieces[1]:<14} {pieces[2]:<14} {count:>11}")

        code = "".join(PIECE_CODES[p] for p in pieces)
        for tour_num, tour in enumerate(tours, start=1):
            key = f"{code}-{tour_num:03d}"
            all_tours_dict[key] = [rc(sq) for sq in tour]

    with open(csv_filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    print(f"\nResults written to {csv_filename}")

    with open(py_filename, "w") as f:
        f.write("BUSY_BEAVER_3_TOURS = {\n")
        for key, path in all_tours_dict.items():
            coords = ", ".join(str(sq) for sq in path)
            f.write(f'    "{key}": [{coords}],\n')
        f.write("}\n")

    print(f"Tours written to {py_filename}")


if __name__ == "__main__":
    print("Select mode:")
    print("  1 - Enter three pieces and enumerate tours")
    print("  2 - Test every 3-piece permutation from 7 available pieces and write results to CSV and Python dict file")
    mode = input("Mode: ").strip()

    if mode == "1":
        run_mode_1()
    elif mode == "2":
        run_mode_2()
    else:
        print("Invalid mode. Please enter 1 or 2.")
        sys.exit(1)