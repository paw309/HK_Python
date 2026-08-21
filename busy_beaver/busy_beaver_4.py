import time
from itertools import permutations
from typing import List, Tuple, Optional

ROWS = 9
COLS = 12
N_SQUARES = ROWS * COLS

# Parity → piece mapping:
# (row % 2, col % 2):
#   (0,0) -> King
#   (0,1) -> Knight
#   (1,0) -> Giraffe
#   (1,1) -> Zebra

def in_bounds(r: int, c: int) -> bool:
    return 0 <= r < ROWS and 0 <= c < COLS

def wazir_moves(r: int, c: int):
    deltas = [
        (-1,0), #(-3, 0),
        (-0,1), #(-0, 3),
        ( 0,-1), #( 0, 3),
        ( 1,0), #( 3, 0),
    ]
    return [(r+dr, c+dc) for dr,dc in deltas if in_bounds(r+dr, c+dc)]

def ferz_moves(r: int, c: int):
    deltas = [
        (-1,1), #(-3, 0),
        (-1,1), #(-0, 3),
        ( 1,-1), #( 0, 3),
        ( 1,1), #( 3, 0),
    ]
    return [(r+dr, c+dc) for dr,dc in deltas if in_bounds(r+dr, c+dc)]



def knight_moves(r: int, c: int):
    deltas = [
        (-2,-1), (-2, 1),
        (-1,-2), (-1, 2),
        ( 1,-2), ( 1, 2),
        ( 2,-1), ( 2, 1),
    ]
    return [(r+dr, c+dc) for dr,dc in deltas if in_bounds(r+dr, c+dc)]

def king_moves(r: int, c: int):
    deltas = [
        (-1,-1), (-1,0), (-1,1),
        ( 0,-1),         ( 0,1),
        ( 1,-1), ( 1,0), ( 1,1),
    ]
    return [(r+dr, c+dc) for dr,dc in deltas if in_bounds(r+dr, c+dc)]


def threeleaper_moves(r: int, c: int):
    # (1,3) leaper
    deltas = [
        (-3,0), #(-3, 0),
        (-0,3), #(-0, 3),
        ( 0,-3), #( 0, 3),
        ( 3,0), #( 3, 0),
    ]
    return [(r+dr, c+dc) for dr,dc in deltas if in_bounds(r+dr, c+dc)]

def tripper_moves(r: int, c: int):
    # (1,3) leaper
    deltas = [
        (-3,3), #(-3, 0),
        (-3,3), #(-0, 3),
        ( 3,-3), #( 0, 3),
        ( 3,3), #( 3, 0),
    ]
    return [(r+dr, c+dc) for dr,dc in deltas if in_bounds(r+dr, c+dc)]


def giraffe_moves(r: int, c: int):
    # (2,3) leaper
    deltas = [
        (-4,-1), (-4, 1),
        (-1,-4), (-1, 4),
        ( 1,-4), ( 1, 4),
        ( 4,-1), ( 4, 1),
    ]
    return [(r+dr, c+dc) for dr,dc in deltas if in_bounds(r+dr, c+dc)]

def camel_moves(r: int, c: int):
    # (2,3) leaper
    deltas = [
        (-3,-1), (-3, 1),
        (-1,-3), (-1, 3),
        ( 1,-3), ( 1, 3),
        ( 3,-1), ( 3, 1),
    ]
    return [(r+dr, c+dc) for dr,dc in deltas if in_bounds(r+dr, c+dc)]

def flamingo_moves(r: int, c: int):
    # (2,3) leaper
    deltas = [
        (-6,-1), (-6, 1),
        (-1,-6), (-1, 6),
        ( 1,-6), ( 1, 6),
        ( 6,-1), ( 6, 1),
    ]
    return [(r+dr, c+dc) for dr,dc in deltas if in_bounds(r+dr, c+dc)]


def zebra_moves(r: int, c: int):
    # (2,3) leaper
    deltas = [
        (-3,-2), (-3, 2),
        (-2,-3), (-2, 3),
        ( 2,-3), ( 2, 3),
        ( 3,-2), ( 3, 2),
    ]
    return [(r+dr, c+dc) for dr,dc in deltas if in_bounds(r+dr, c+dc)]

def antelope_moves(r: int, c: int):
    # (2,3) leaper
    deltas = [
        (-3,-4), (-3, 4),
        (-4,-3), (-4, 3),
        ( 4,-3), ( 4, 3),
        ( 3,-4), ( 3, 4),
    ]
    return [(r+dr, c+dc) for dr,dc in deltas if in_bounds(r+dr, c+dc)]


ALL_PIECES = [zebra_moves, king_moves, knight_moves, wazir_moves]
ALL_PIECE_NAMES = ["zebra", "king", "knight", "wazir"]

# Parity slot index: (r%2)*2 + (c%2)
#   0 -> (0,0), 1 -> (0,1), 2 -> (1,0), 3 -> (1,1)
def moves_for_square(r: int, c: int, piece_fns):
    slot = (r % 2) * 2 + (c % 2)
    return piece_fns[slot](r, c)

IMPROVEMENT_TIMEOUT = 60  # seconds: move on if no new best for this long

def canonical_start(r: int, c: int) -> Tuple[int, int]:
    """Return the lexicographically smallest equivalent start square under the
    4 rectangular symmetries: identity, horizontal flip, vertical flip, and
    180-degree rotation.  Only the canonical representative is searched."""
    return min(
        (r,          c),
        (r,          COLS - 1 - c),
        (ROWS - 1 - r, c),
        (ROWS - 1 - r, COLS - 1 - c),
    )

def search_from(start_r: int, start_c: int, piece_fns):
    visited = [[False]*COLS for _ in range(ROWS)]
    path: List[Tuple[int,int]] = []

    best_len = 0
    best_path: List[Tuple[int,int]] = []
    last_improvement_time = time.monotonic()
    timed_out = False

    def dfs(r: int, c: int, depth: int):
        nonlocal best_len, best_path, last_improvement_time, timed_out

        if timed_out:
            return False

        # Check timeout periodically (every 10 depth levels) to limit overhead
        if depth % 10 == 0 and time.monotonic() - last_improvement_time > IMPROVEMENT_TIMEOUT:
            timed_out = True
            print(f"  Timeout: no improvement for {IMPROVEMENT_TIMEOUT}s, abandoning start ({start_r},{start_c})")
            return False

        visited[r][c] = True
        path.append((r, c))

        # Update best partial tour
        if depth > best_len:
            best_len = depth
            best_path = path.copy()
            last_improvement_time = time.monotonic()
            print(f"New best length {best_len}: {best_path}")

        # Full Hamiltonian tour found
        if depth == N_SQUARES:
            print("FOUND FULL 108-SQUARE TOUR!")
            print(best_path)
            return True

        # Warnsdorff-style ordering
        next_moves = []
        for nr, nc in moves_for_square(r, c, piece_fns):
            if not visited[nr][nc]:
                onward = sum(
                    1 for rr, cc in moves_for_square(nr, nc, piece_fns)
                    if not visited[rr][cc]
                )
                next_moves.append((onward, nr, nc))
        next_moves.sort(key=lambda x: x[0])

        for _, nr, nc in next_moves:
            if dfs(nr, nc, depth+1):
                return True

        # Backtrack
        visited[r][c] = False
        path.pop()
        return False

    dfs(start_r, start_c, 1)
    return best_len, best_path

def main():
    tested_perms = set()

    for perm in permutations(range(4)):
        rev = perm[::-1]
        if rev in tested_perms:
            print(f"\n=== Skipping {list(perm)} (reverse of already-tested {list(rev)}) ===")
            continue
        tested_perms.add(perm)

        piece_fns = [ALL_PIECES[i] for i in perm]
        piece_names = [ALL_PIECE_NAMES[i] for i in perm]
        print(f"\n{'='*60}")
        print(f"=== Piece assignment: {piece_names} ===")
        print(f"    slots: (0,0)={piece_names[0]}  (0,1)={piece_names[1]}"
              f"  (1,0)={piece_names[2]}  (1,1)={piece_names[3]}")
        print(f"{'='*60}")

        global_best_len = 0
        global_best_path = None
        global_best_start = None

        for r in range(ROWS):
            for c in range(COLS):
                if canonical_start(r, c) != (r, c):
                    print(f"\n=== Skipping ({r},{c}) — equivalent to canonical {canonical_start(r,c)} ===")
                    continue
                print(f"\n=== Trying start at ({r},{c}) ===")
                best_len, best_path = search_from(r, c, piece_fns)

                if best_len > global_best_len:
                    global_best_len = best_len
                    global_best_path = best_path
                    global_best_start = (r, c)
                    print(f"*** NEW GLOBAL BEST {global_best_len} from start {global_best_start} ***")

                if best_len == N_SQUARES:
                    print("Full tour found — stopping search.")
                    return

        print(f"\n=== RESULTS FOR {piece_names} ===")
        print(f"Best length achieved: {global_best_len}")
        print(f"Best starting square: {global_best_start}")
        if global_best_path:
            print("Best path:")
            for step, (rr, cc) in enumerate(global_best_path):
                print(f"{step:3d}: ({rr},{cc})")

if __name__ == "__main__":
    main()