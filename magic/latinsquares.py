import time
from typing import List, Tuple, Dict, TypedDict


class Point(TypedDict):
    x: int
    y: int


class ValidationResult(TypedDict):
    is_fully_solvable: bool
    solvable_count: int
    unsolvable_starts: List[Point]


BOARD_SIZE = 9
TOTAL_CELLS = BOARD_SIZE * BOARD_SIZE  # 81


def map_prime_factor(p: int) -> int:
    """
    Maps prime factor p to a step coordinate for Factor Drift.
    Formula: p mod 4, with 0 mapping to 4.
    For v in 1..9, prime factors mapped are:
      2 -> 2
      3 -> 3
      5 -> 1
      7 -> 3
    """
    mapped = p % 4
    return 4 if mapped == 0 else mapped


def get_prime_factors(n: int) -> List[int]:
    """Extracts prime factors for a tile value v in [1, 9]."""
    factors = []
    d = 2
    temp = n
    while temp >= 2:
        if temp % d == 0:
            factors.append(d)
            temp //= d
        else:
            d += 1
    return factors


def get_vectors_for_value(v: int) -> List[Tuple[int, int]]:
    """Generates all legal vector directions (dx, dy) for a tile value v in [1, 9]."""
    if v == 1:
        # Unit tile: King steps (Wazir + Ferz)
        return [
            (0, 1), (0, -1), (1, 0), (-1, 0),
            (1, 1), (1, -1), (-1, 1), (-1, -1)
        ]

    factors = get_prime_factors(v)
    raw_spans = [map_prime_factor(p) for p in factors]

    if len(raw_spans) == 1:
        # Prime or Prime Power
        s = raw_spans[0]
        spans = [s, s]
    else:
        # Composite: Take unique mapped components
        unique_spans = list(dict.fromkeys(raw_spans))
        if len(unique_spans) == 1:
            unique_spans.append(unique_spans[0])
        spans = unique_spans

    s1, s2 = spans[0], spans[1]

    # Base symmetric moves
    base_moves = [
        (s1, s2), (s1, -s2), (-s1, s2), (-s1, -s2),
        (s2, s1), (s2, -s1), (-s2, s1), (-s2, -s1),
        # Include orthogonal recovery components for composite stability
        (0, s1), (0, -s1), (s1, 0), (-s1, 0),
        (0, s2), (0, -s2), (s2, 0), (-s2, 0)
    ]

    # Deduplicate move set
    return list(dict.fromkeys(base_moves))


def get_valid_neighbors(
        grid: List[List[int]],
        visited: List[List[bool]],
        x: int,
        y: int,
        vector_cache: Dict[int, List[Tuple[int, int]]]
) -> List[Tuple[int, int]]:
    """Returns valid unvisited neighbor coordinates (nx, ny) from (x, y)."""
    tile_val = grid[y][x]
    vectors = vector_cache[tile_val]
    neighbors = []

    for dx, dy in vectors:
        nx, ny = x + dx, y + dy
        if (0 <= nx < BOARD_SIZE) and (0 <= ny < BOARD_SIZE) and not visited[ny][nx]:
            neighbors.append((nx, ny))

    return neighbors


def can_solve_from_start(
        grid: List[List[int]],
        start_x: int,
        start_y: int,
        vector_cache: Dict[int, List[Tuple[int, int]]]
) -> bool:
    """
    Solves for an 81-step Hamiltonian path using DFS with Warnsdorff's Heuristic.
    """
    visited = [[False] * BOARD_SIZE for _ in range(BOARD_SIZE)]

    def dfs(x: int, y: int, count: int) -> bool:
        if count == TOTAL_CELLS:
            return True

        visited[y][x] = True
        neighbors = get_valid_neighbors(grid, visited, x, y, vector_cache)

        # Warnsdorff's Heuristic: Sort neighbors by their remaining unvisited degree (ascending)
        neighbors.sort(
            key=lambda pos: len(get_valid_neighbors(grid, visited, pos[0], pos[1], vector_cache))
        )

        for nx, ny in neighbors:
            if dfs(nx, ny, count + 1):
                return True

        visited[y][x] = False  # Backtrack
        return False

    return dfs(start_x, start_y, 1)


def generate_sudoku_latin_square() -> List[List[int]]:
    """Generates a classic valid 9x9 Sudoku grid (Sudoku-style Latin Square)."""

    # Standard valid Sudoku pattern base
    def pattern(r, c):
        return (3 * (r % 3) + r // 3 + c) % 9

    def shuffle(s):
        import random
        return random.sample(s, len(s))

    r_base = range(3)
    rows = [g * 3 + r for g in shuffle(r_base) for r in shuffle(r_base)]
    cols = [g * 3 + c for g in shuffle(r_base) for c in shuffle(r_base)]
    nums = shuffle(range(1, 10))

    return [[nums[pattern(r, c)] for c in cols] for r in rows]


def evaluate_9x9_sudoku_latin_square(grid: List[List[int]]) -> ValidationResult:
    """Evaluates a 9x9 board for 100% start-cell solvability (81/81)."""
    # Pre-cache move vectors for values 1..9
    vector_cache = {v: get_vectors_for_value(v) for v in range(1, 10)}

    solvable_count = 0
    unsolvable_starts: List[Point] = []

    start_time = time.time()

    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            if can_solve_from_start(grid, x, y, vector_cache):
                solvable_count += 1
            else:
                unsolvable_starts.append({"x": x, "y": y})

    elapsed = time.time() - start_time
    print(f"Evaluated all 81 starts in {elapsed:.2f} seconds.")

    return {
        "is_fully_solvable": solvable_count == TOTAL_CELLS,
        "solvable_count": solvable_count,
        "unsolvable_starts": unsolvable_starts
    }


# ==========================================
# EXECUTION & BOARD VERIFICATION
# ==========================================
if __name__ == "__main__":
    grid = generate_sudoku_latin_square()

    print("Generated 9x9 Sudoku Latin Square:")
    for row in grid:
        print(" ".join(f"{num:2d}" for num in row))
    print("-" * 30)

    result = evaluate_9x9_sudoku_latin_square(grid)

    print(f"Solvable Starts: {result['solvable_count']} / {TOTAL_CELLS}")
    if result["is_fully_solvable"]:
        print("SUCCESS: The 9x9 Sudoku Latin Square is 100% solvable from ALL 81 starting tiles!")
    else:
        print("Failed Start Coordinates:", result["unsolvable_starts"])