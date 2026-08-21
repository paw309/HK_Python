from itertools import combinations, permutations

MAX_N = 30
ROWS = [0, 1]  # two-row infinite board


# -----------------------------------------
# PIECE DEFINITIONS
# -----------------------------------------

def king_moves():
    moves = []
    for dr in [-1, 0, 1]:
        for dc in [-1, 0, 1]:
            if dr == 0 and dc == 0:
                continue
            moves.append((dr, dc))
    return moves

def ferz_moves():
    return [(1, 1), (1, -1), (-1, 1), (-1, -1)]

def leaper_0n(n):
    return [(0, n), (0, -n)]

def leaper_1n(n):
    return [(1, n), (1, -n), (-1, n), (-1, -n)]


def build_pieces():
    pieces = {}

    # (0,n) leapers for n=1..7
    for n in range(1, 8):
        pieces[f"L0{n}"] = leaper_0n(n)

    # (1,n) leapers for n=1..7
    for n in range(1, 8):
        pieces[f"L1{n}"] = leaper_1n(n)

    # King and Ferz
    pieces["K"] = king_moves()
    pieces["F"] = ferz_moves()

    return pieces


PIECES = build_pieces()


# -----------------------------------------
# SIMULATION
# -----------------------------------------

def legal_moves_from(pos, moves):
    r, c = pos
    result = []
    for dr, dc in moves:
        nr, nc = r + dr, c + dc
        if nr in ROWS:
            result.append((nr, nc))
    return result


def simulate_cycle(piece_cycle, max_n=MAX_N):
    """
    piece_cycle: tuple of piece names, e.g. ('L01', 'L12', 'K')
    At step n, use piece_cycle[(n-1) % len(piece_cycle)].
    Deterministic: always take the first legal move.
    Returns (halt_step, path) if a repeat occurs before max_n, else None.
    """
    visited = {(0, 0)}
    path = [(0, 0)]
    pos = (0, 0)
    k = len(piece_cycle)

    for n in range(1, max_n + 1):
        piece_name = piece_cycle[(n - 1) % k]
        moves = PIECES[piece_name]
        legal = legal_moves_from(pos, moves)

        if not legal:
            return (n, path)

        pos = legal[0]

        if pos in visited:
            return (n, path + [pos])

        visited.add(pos)
        path.append(pos)

    return None


# -----------------------------------------
# MAIN SEARCH
# -----------------------------------------

def main():
    print("Testing 2-, 3-, and 4-piece cycles on a 2-row infinite board...\n")

    piece_names = list(PIECES.keys())

    for r in [2, 3, 4]:
        print(f"--- Testing {r}-piece cycles ---")
        for combo in combinations(piece_names, r):
            for cycle in permutations(combo):
                result = simulate_cycle(cycle)
                if result is not None:
                    halt_step, path = result
                    print(f"HALT at step {halt_step:2d} | cycle={cycle} | path_len={len(path)}")
        print()


if __name__ == "__main__":
    main()
