import json
import random
import time

MAGIC_SUM = 65

def get_canonical_key(matrix):
    """Finds the lexicographically smallest 1D tuple among all 8 rotations and reflections."""
    def rotate(m):
        return [list(row) for row in zip(*m[::-1])]
    def reflect(m):
        return [row[::-1] for row in m]

    symmetries = []
    curr = [row[:] for row in matrix]
    for _ in range(4):
        symmetries.append(curr)
        symmetries.append(reflect(curr))
        curr = rotate(curr)

    flat_syms = [tuple(c for r in s for c in r) for s in symmetries]
    return min(flat_syms)


def generate_5x5_magic_squares(target_count=100):
    seen_keys = set()
    results = []

    # Interleaved placement order to trigger row/col/diag completion constraints early
    # (row 0, col 0, row 1, col 1, center, etc.)
    placement_order = [
        (0, 0), (0, 1), (0, 2), (0, 3), # (0,4) forced by row 0
        (1, 0), (2, 0), (3, 0),         # (4,0) forced by col 0
        (1, 1), (1, 2), (1, 3),         # (1,4) forced by row 1
        (2, 1), (3, 1),                 # (4,1) forced by col 1
        (2, 2), (2, 3),                 # (2,4) forced by row 2
        (3, 2),                         # (4,2) forced by col 2
        (3, 3),                         # (3,4) forced by row 3 & (4,3) forced by col 3
    ]

    def solve_one():
        grid = [[0] * 5 for _ in range(5)]
        used = [False] * 26
        row_sums = [0] * 5
        col_sums = [0] * 5

        def place(step):
            # Base case: all variable cells filled
            if step == len(placement_order):
                # Calculate forced remaining cells: (4,3), (4,4)
                r3_4 = MAGIC_SUM - row_sums[3]
                c3_4 = MAGIC_SUM - col_sums[3]
                if r3_4 != c3_4 or not (1 <= r3_4 <= 25) or used[r3_4]:
                    return None

                grid[3][4] = r3_4
                used[r3_4] = True
                col_sums[4] += r3_4

                r4_4 = MAGIC_SUM - col_sums[4]
                if not (1 <= r4_4 <= 25) or used[r4_4]:
                    used[r3_4] = False
                    col_sums[4] -= r3_4
                    return None

                grid[4][4] = r4_4

                # Validate final diagonal sums
                d1 = grid[0][0] + grid[1][1] + grid[2][2] + grid[3][3] + grid[4][4]
                d2 = grid[0][4] + grid[1][3] + grid[2][2] + grid[3][1] + grid[4][0]

                used[r3_4] = False
                col_sums[4] -= r3_4

                if d1 == MAGIC_SUM and d2 == MAGIC_SUM:
                    return [row[:] for row in grid]
                return None

            r, c = placement_order[step]

            # Collect available candidate numbers
            candidates = [v for v in range(1, 26) if not used[v]]
            random.shuffle(candidates)

            for num in candidates:
                if row_sums[r] + num >= MAGIC_SUM or col_sums[c] + num >= MAGIC_SUM:
                    continue

                grid[r][c] = num
                used[num] = True
                row_sums[r] += num
                col_sums[c] += num

                # Check if this placement forces the last element of row 'r'
                forced_r = None
                if c == 3:  # 4th cell in row r
                    needed_r = MAGIC_SUM - row_sums[r]
                    if 1 <= needed_r <= 25 and not used[needed_r]:
                        grid[r][4] = needed_r
                        used[needed_r] = True
                        col_sums[4] += needed_r
                        forced_r = needed_r
                    else:
                        # Undo cell placement
                        used[num] = False
                        row_sums[r] -= num
                        col_sums[c] -= num
                        continue

                # Check if this placement forces the last element of col 'c'
                forced_c = None
                if r == 3:  # 4th cell in col c
                    needed_c = MAGIC_SUM - col_sums[c]
                    if 1 <= needed_c <= 25 and not used[needed_c]:
                        grid[4][c] = needed_c
                        used[needed_c] = True
                        row_sums[4] += needed_c
                        forced_c = needed_c
                    else:
                        # Clean up row force if applied
                        if forced_r is not None:
                            used[forced_r] = False
                            col_sums[4] -= forced_r
                            grid[r][4] = 0
                        used[num] = False
                        row_sums[r] -= num
                        col_sums[c] -= num
                        continue

                # Recurse
                res = place(step + 1)
                if res is not None:
                    return res

                # Backtrack forced assignments
                if forced_c is not None:
                    used[forced_c] = False
                    row_sums[4] -= forced_c
                    grid[4][c] = 0

                if forced_r is not None:
                    used[forced_r] = False
                    col_sums[4] -= forced_r
                    grid[r][4] = 0

                used[num] = False
                row_sums[r] -= num
                col_sums[c] -= num

            return None

        return place(0)

    print("Generating unique 5x5 magic squares...")
    start_time = time.time()

    while len(results) < target_count:
        square = solve_one()
        if square is not None:
            key = get_canonical_key(square)
            if key not in seen_keys:
                seen_keys.add(key)
                results.append(square)
                if len(results) % 2000 == 0:
                    print(f"Generated {len(results):,} / {target_count:,}...")

    elapsed = time.time() - start_time
    print(f"Successfully generated {len(results):,} unique squares in {elapsed:.2f}s!")
    return results


def main():
    target = 100
    output_filename = "magic_squares_5x5_10k.json"

    squares = generate_5x5_magic_squares(target_count=target)

    print(f"Saving to '{output_filename}'...")
    with open(output_filename, "w") as f:
        json.dump(squares, f, indent=2)

    print("Done!")


if __name__ == "__main__":
    main()