import json
import random
import time


def generate_siamese_base():
    """Generates the classic 5x5 Siamese magic square."""
    n = 5
    grid = [[0] * n for _ in range(n)]
    r, c = 0, n // 2
    for val in range(1, 26):
        grid[r][c] = val
        nr, nc = (r - 1) % n, (c + 1) % n
        if grid[nr][nc] != 0:
            r = (r + 1) % n
        else:
            r, c = nr, nc
    return grid


def get_canonical_key(matrix):
    """Returns the lexicographically smallest symmetry of the 5x5 grid

    to guarantee uniqueness up to rotations and reflections.
    """

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


def generate_5x5_magic_squares(target_count=92):
    results = []
    seen_keys = set()

    # Valid row/col shifts and transformations for 5x5 associative/regular magic squares
    # Toroidal shifts (offsetting row/col indices modulo 5) preserve line sums
    base = generate_siamese_base()

    # We generate variants by applying:
    # 1. Toroidal row/column shift combinations
    # 2. Complement transformation (x -> 26 - x)
    # 3. Transposition (matrix flip)
    # 4. Row/Column permutations that preserve diagonal invariants

    # Valid shift vectors and transformations
    while len(results) < target_count:
        # Create a candidate by applying valid linear index mappings modulo 5
        # x' = (a*r + b*c + e) % 5, y' = (c*r + d*c + f) % 5
        # For magic preservation, the transformation matrix [[a,b],[c,d]] must be invertible mod 5
        # and satisfy main diagonal sum conservation.

        a = random.choice([1, 2, 3, 4])
        b = random.choice([0, 1, 2, 3, 4])
        c = random.choice([0, 1, 2, 3, 4])
        d = random.choice([1, 2, 3, 4])

        # Determinant check mod 5 to ensure invertibility (bijective mapping)
        if (a * d - b * c) % 5 == 0:
            continue

        # Diagonal preservation checks
        if (a + b) % 5 == 0 or (c + d) % 5 == 0:
            continue
        if (a - b) % 5 == 0 or (c - d) % 5 == 0:
            continue

        offset_r = random.randint(0, 4)
        offset_c = random.randint(0, 4)
        invert_vals = random.choice([True, False])

        candidate = [[0] * 5 for _ in range(5)]
        for r in range(5):
            for col in range(5):
                nr = (a * r + b * col + offset_r) % 5
                nc = (c * r + d * col + offset_c) % 5
                val = base[r][col]
                if invert_vals:
                    val = 26 - val
                candidate[nr][nc] = val

        # Verify magic constant (65) on rows, cols, diags
        if not is_magic(candidate):
            continue

        canon_key = get_canonical_key(candidate)
        if canon_key not in seen_keys:
            seen_keys.add(canon_key)
            results.append(candidate)

    return results


def is_magic(matrix):
    """Validation helper."""
    # Rows and Columns
    for i in range(5):
        if sum(matrix[i]) != 65:
            return False
        if sum(matrix[r][i] for r in range(5)) != 65:
            return False

    # Diagonals
    if sum(matrix[i][i] for i in range(5)) != 65:
        return False
    if sum(matrix[i][4 - i] for i in range(5)) != 65:
        return False

    return True


def main():
    target = 92
    output_filename = "magic_squares_5x5_92.json"

    print(f"Generating {target:,} unique 5x5 magic squares...")
    start_time = time.time()

    squares = generate_5x5_magic_squares(target_count=target)

    elapsed = time.time() - start_time
    print(
        f"Successfully generated {len(squares):,} unique squares in {elapsed:.2f} seconds!"
    )

    with open(output_filename, "w") as f:
        json.dump(squares, f, indent=2)

    print(f"Saved output to {output_filename}")


if __name__ == "__main__":
    main()