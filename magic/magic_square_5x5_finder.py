"""
magic_square_5x5_finder.py

Constructs valid 5×5 magic squares, tests each for a Hamiltonian path using
dynamic Factor Drift DFS, and saves validated (matrix, start_tile) entries
to magic_squares_5x5.json.
"""

from __future__ import annotations

import json
import sys

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

N          = 5                            # board / magic-square order
TOTAL      = N * N                        # 25 cells
MAGIC_SUM  = N * (N * N + 1) // 2         # 65
COMPL_BASE = N * N + 1                    # 26  (v + complement(v) = 26)
TARGET     = 25
OUTPUT     = "magic_squares_5x5.json"

Matrix = list[list[int]]


# ═══════════════════════════════════════════════════════════════════════════════
# Section 1 – Dynamic Factor Drift Vector Engine & Static Pre-computation
# ═══════════════════════════════════════════════════════════════════════════════

def get_effective_prime(p: int) -> int:
    """Map prime factors to valid grid span dimensions for N=5."""
    if p < 4:
        return p
    mod = p % 4
    return 4 if mod == 0 else mod

def get_prime_factors(n: int) -> list[int]:
    """Return unique prime factors of n."""
    if n == 1:
        return [1]
    factors = []
    divisor = 2
    temp = n
    while temp >= 2:
        if temp % divisor == 0:
            if divisor not in factors:
                factors.append(divisor)
            temp //= divisor
        else:
            divisor += 1
    return factors

def expand_symmetrical_vectors(base_vectors: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Expand relative vectors across all 8 symmetric reflections/rotations."""
    expanded = set()
    for dx, dy in base_vectors:
        variations = [
            (dx, dy), (dx, -dy), (-dx, dy), (-dx, -dy),
            (dy, dx), (dy, -dx), (-dy, dx), (-dy, -dx)
        ]
        for vx, vy in variations:
            expanded.add((vx, vy))
    return list(expanded)

def get_factor_drift_vectors(val: int) -> list[tuple[int, int]]:
    """Derive dynamic move vectors for N=5 based on prime factors."""
    factors = get_prime_factors(val)

    if val == 1:
        raw_vectors = [(0, 1), (1, 1)]
    elif len(factors) == 1:
        p_prime = get_effective_prime(factors[0])
        raw_vectors = [(1, p_prime), (0, p_prime), (p_prime, p_prime)]
    else:
        p1 = get_effective_prime(factors[0])
        p2 = get_effective_prime(factors[1])
        raw_vectors = [(p1, p2), (0, p1), (0, p2)]

    return expand_symmetrical_vectors(raw_vectors)


# Pre-compute valid delta steps for all numbers 1..25 on a 5x5 board
# Key: (val, r, c) -> List of valid (nr, nc) coordinates
VECTOR_CACHE: dict[int, list[tuple[int, int]]] = {
    v: get_factor_drift_vectors(v) for v in range(1, TOTAL + 1)
}

def get_valid_neighbors(r: int, c: int, val: int) -> list[tuple[int, int]]:
    neighbors = []
    for dr, dc in VECTOR_CACHE[val]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < N and 0 <= nc < N:
            neighbors.append((nr, nc))
    return neighbors


# ═══════════════════════════════════════════════════════════════════════════════
# Section 2 – Magic-square utilities & Base Pools
# ═══════════════════════════════════════════════════════════════════════════════

def is_magic(M: Matrix) -> bool:
    """Return True iff M is a valid normal 5×5 magic square."""
    flat = sorted(M[r][c] for r in range(N) for c in range(N))
    if flat != list(range(1, TOTAL + 1)):
        return False
    for r in range(N):
        if sum(M[r]) != MAGIC_SUM:
            return False
    for c in range(N):
        if sum(M[r][c] for r in range(N)) != MAGIC_SUM:
            return False
    if sum(M[i][i] for i in range(N)) != MAGIC_SUM:
        return False
    if sum(M[i][N - 1 - i] for i in range(N)) != MAGIC_SUM:
        return False
    return True


def _rot90(M: Matrix) -> Matrix:
    return [[M[N - 1 - c][r] for c in range(N)] for r in range(N)]


def _refl_h(M: Matrix) -> Matrix:
    return [row[::-1] for row in M]


def d4_family(M: Matrix) -> list[Matrix]:
    seen: set[tuple] = set()
    out: list[Matrix] = []
    cur = M
    for _ in range(4):
        for variant in (cur, _refl_h(cur)):
            key = tuple(tuple(r) for r in variant)
            if key not in seen:
                seen.add(key)
                out.append([r[:] for r in variant])
        cur = _rot90(cur)
    return out


def complement_sq(M: Matrix) -> Matrix:
    return [[COMPL_BASE - M[r][c] for c in range(N)] for r in range(N)]


BASE_SQUARES: list[Matrix] = [
    # 0 - Standard Siamese Method
    [[17, 24,  1,  8, 15], [23,  5,  7, 14, 16], [ 4,  6, 13, 20, 22], [10, 12, 19, 21,  3], [11, 18, 25,  2,  9]],
    # 1 - Knight's Move Construction
    [[11, 24,  7, 20,  3], [ 4, 12, 25,  8, 16], [17,  5, 13, 21,  9], [10, 18,  1, 14, 22], [23,  6, 19,  2, 15]],
    # 2 - Symmetric Variant A
    [[ 3, 16,  9, 22, 15], [20,  8, 21, 14,  2], [ 7, 25, 13,  1, 19], [24, 12,  5, 18,  6], [11,  4, 17, 10, 23]],
    # 3 - Symmetric Variant B
    [[ 7, 20,  3, 11, 24], [13, 21,  9, 17,  5], [19,  2, 15, 23,  6], [25,  8, 16,  4, 12], [ 1, 14, 22, 10, 18]]
]


def build_pool() -> list[Matrix]:
    seen: set[tuple] = set()
    pool: list[Matrix] = []

    def _try_add(M: Matrix) -> None:
        key = tuple(tuple(r) for r in M)
        if key not in seen:
            seen.add(key)
            pool.append(M)

    for idx, base in enumerate(BASE_SQUARES):
        before = len(pool)
        for v in d4_family(base):
            _try_add(v)
        for v in d4_family(complement_sq(base)):
            _try_add(v)
        print(f"[pool]  base {idx} → {len(pool) - before:2d} new squares  (pool total {len(pool):3d})")

    return pool


# ═══════════════════════════════════════════════════════════════════════════════
# Section 3 – Optimized Factor Drift DFS
# ═══════════════════════════════════════════════════════════════════════════════

def factor_drift_dfs(board: Matrix, start_r: int, start_c: int) -> bool:
    """Return True if a complete Hamiltonian tour exists starting at (start_r, start_c)."""
    # Pre-build dynamic target lookup for this specific board setup
    graph = {
        (r, c): get_valid_neighbors(r, c, board[r][c])
        for r in range(N) for c in range(N)
    }

    vis = [[False] * N for _ in range(N)]
    vis[start_r][start_c] = True

    def dfs(r: int, c: int, depth: int) -> bool:
        if depth == TOTAL:
            return True

        # Extract unvisited candidates
        cands = [(nr, nc) for nr, nc in graph[(r, c)] if not vis[nr][nc]]
        if not cands:
            return False

        # Fast Warnsdorff heuristic calculation
        def score(pos: tuple[int, int]) -> tuple[int, int]:
            nr, nc = pos
            deg = sum(1 for nnr, nnc in graph[(nr, nc)] if not vis[nnr][nnc])
            return (deg, board[nr][nc])

        cands.sort(key=score)

        for nr, nc in cands:
            vis[nr][nc] = True
            if dfs(nr, nc, depth + 1):
                return True
            vis[nr][nc] = False

        return False

    return dfs(start_r, start_c, 1)


# ═══════════════════════════════════════════════════════════════════════════════
# Section 4 – Main Execution Loop
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 5_000))

    print(f"Board Order     : {N}x{N}")
    print(f"Magic constant  : {MAGIC_SUM}")
    print(f"Target entries  : {TARGET}")
    print(f"Output file     : {OUTPUT}\n")

    pool = build_pool()
    print(f"\n[main] pool ready → {len(pool)} distinct {N}x{N} magic squares\n")

    results: list[dict] = []
    seen_keys: set[tuple] = set()

    for pool_idx, M in enumerate(pool, start=1):
        if len(results) >= TARGET:
            break

        mat_key = tuple(tuple(r) for r in M)
        found = 0
        done = False

        for r in range(N):
            if done:
                break
            for c in range(N):
                if len(results) >= TARGET:
                    done = True
                    break
                ek = (mat_key, (r, c))
                if ek in seen_keys:
                    continue
                if factor_drift_dfs(M, r, c):
                    seen_keys.add(ek)
                    results.append({
                        "matrix": [row[:] for row in M],
                        "start": [r, c],
                    })
                    found += 1

        print(
            f"  sq {pool_idx:3d}:  {found:2d}/{TOTAL} starts solved"
            f"  |  total = {len(results)}"
        )

    results = results[:TARGET]
    with open(OUTPUT, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)

    print(f"\nSaved {len(results)} entries to '{OUTPUT}'.")


if __name__ == "__main__":
    main()