import sys

# -----------------------------------------------------------------------------
# 1. MOVEMENT VECTOR DEFINITIONS & ISOMETRIES
# -----------------------------------------------------------------------------

BASE_OFFSETS = [
    (1, -2), (2, -1), (2, 1), (1, 2),
    (-1, 2), (-2, 1), (-2, -1), (-1, -2)
]

VECTOR_MAPS = []
for shift in range(8):
    m_cw = {d + 1: BASE_OFFSETS[(d + shift) % 8] for d in range(8)}
    m_ccw = {d + 1: BASE_OFFSETS[(-d + shift) % 8] for d in range(8)}
    VECTOR_MAPS.extend([m_cw, m_ccw])


def get_grid_symmetries(board_size):
    max_idx = board_size - 1
    return [
        ("Identity", lambda c, r: (c, r)),
        ("H-flip", lambda c, r: (max_idx - c, r)),
        ("V-flip", lambda c, r: (c, max_idx - r)),
        ("Rot180", lambda c, r: (max_idx - c, max_idx - r)),
        ("MainDiag", lambda c, r: (r, c)),
        ("AntiDiag", lambda c, r: (max_idx - r, max_idx - c)),
        ("Rot90CW", lambda c, r: (max_idx - r, c)),
        ("Rot90CCW", lambda c, r: (r, max_idx - c))
    ]


# -----------------------------------------------------------------------------
# 2. HELPER FUNCTIONS
# -----------------------------------------------------------------------------

def trace_path(start_c, start_r, digits, vmap, board_size):
    c, r = start_c, start_r
    path = [board_size * r + c]
    for d in digits:
        dc, dr = vmap[d]
        c += dc
        r += dr
        if not (0 <= c < board_size and 0 <= r < board_size):
            return None
        path.append(board_size * r + c)
    return path


def verify_knight_path(path, board_size):
    for i in range(len(path) - 1):
        c1, r1 = path[i] % board_size, path[i] // board_size
        c2, r2 = path[i + 1] % board_size, path[i + 1] // board_size
        dc, dr = abs(c2 - c1), abs(r2 - r1)
        if (dc, dr) not in [(1, 2), (2, 1)]:
            return False
    return True


# -----------------------------------------------------------------------------
# 3. MAIN CONVERSION PROCESSOR
# -----------------------------------------------------------------------------

def process_knight_string(board_size, input_str, max_len=72):
    digits = [int(ch) for ch in input_str if ch.isdigit()]

    if len(digits) == 0:
        raise ValueError("Error: Input string contains no valid move digits (1-8).")
    if len(digits) > max_len:
        raise ValueError(f"Error: Move string exceeds maximum limit of {max_len} characters.")

    expected_square_count = len(digits) + 1

    valid_base_traces = []
    for vmap in VECTOR_MAPS:
        for r in range(board_size):
            for c in range(board_size):
                p = trace_path(c, r, digits, vmap, board_size)
                if p is not None and len(p) == len(set(p)):
                    valid_base_traces.append((c, r, p))
                    break
            if valid_base_traces:
                break
        if valid_base_traces:
            break

    if not valid_base_traces:
        raise ValueError(
            f"Error: Could not trace a valid non-crossing path on the {board_size}x{board_size} board with this vector string.")

    base_c, base_r, base_path = valid_base_traces[0]

    ul_candidates = []
    ul_limit = board_size // 2
    grid_symmetries = get_grid_symmetries(board_size)

    for sym_name, sym_fn in grid_symmetries:
        sc, sr = sym_fn(base_c, base_r)
        if sc <= ul_limit and sr <= ul_limit:
            t_path = []
            for sq in base_path:
                c_orig, r_orig = sq % board_size, sq // board_size
                c_new, r_new = sym_fn(c_orig, r_orig)
                t_path.append(board_size * r_new + c_new)
            ul_candidates.append((board_size * sr + sc, sc, sr, sym_name, t_path))

    ul_candidates.sort(key=lambda x: x[0])
    best_start_sq, col, row, symmetry_used, final_path = ul_candidates[0]

    actual_square_count = len(final_path)
    is_valid_moves = verify_knight_path(final_path, board_size)
    is_count_matching = (actual_square_count == expected_square_count)

    return {
        "board_size": board_size,
        "digits_processed": len(digits),
        "expected_squares": expected_square_count,
        "actual_squares": actual_square_count,
        "is_count_matching": is_count_matching,
        "is_valid_moves": is_valid_moves,
        "start_square": final_path[0],
        "end_square": final_path[-1],
        "symmetry_applied": symmetry_used,
        "path_array": final_path
    }


# -----------------------------------------------------------------------------
# 4. SINGLE-PROMPT CLI RUNNER
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("--- N x N Non-Crossing Knight Path Converter ---")
    print("Provide inputs as two items separated by space or newline:")
    print("  1. Board size N (5 to 10)")
    print("  2. Move digit string (up to 72 chars)")
    print("Example: 9 47477475238338381747474774718254383838316747471\n")

    try:
        raw_input = input("Enter inputs: ").strip()
        if not raw_input:
            print("No input provided. Exiting.")
            sys.exit(1)

        parts = raw_input.split(None, 1)
        if len(parts) < 2:
            raise ValueError("Error: Please provide both the board size integer and the move string.")

        board_size = int(parts[0])
        if not (5 <= board_size <= 10):
            raise ValueError("Error: Board size must be an integer between 5 and 10.")

        user_string = parts[1].strip()

        res = process_knight_string(board_size, user_string)

        print("=" * 60)
        print(f"Board Dimensions   : {res['board_size']}x{res['board_size']}")
        print(f"Moves Input Length : {res['digits_processed']} moves")
        print(
            f"Start Square       : {res['start_square']} (col {res['start_square'] % board_size}, row {res['start_square'] // board_size})")
        print(
            f"End Square         : {res['end_square']} (col {res['end_square'] % board_size}, row {res['end_square'] // board_size})")
        print(f"Symmetry Applied   : {res['symmetry_applied']} (Oriented to Upper-Left Quadrant)")
        print("-" * 60)
        print(
            f"Coverage Verification : Expected={res['expected_squares']} | Output={res['actual_squares']} | Match={res['is_count_matching']}")
        print(f"Knight Rule Check    : Valid={res['is_valid_moves']}")
        print("=" * 60)
        print("\nConverted Integer Path Array:")
        print(str(res['path_array']).replace(" ", ""))

    except Exception as err:
        print(f"\n{err}")