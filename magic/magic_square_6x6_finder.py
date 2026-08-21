from typing import List, Tuple, Dict, Set, TypedDict


class Point(TypedDict):
    x: int
    y: int


class ValidationResult(TypedDict):
    is_fully_solvable: bool
    solvable_count: int
    unsolvable_starts: List[Point]


BOARD_SIZE = 6
TOTAL_CELLS = BOARD_SIZE * BOARD_SIZE  # 36


def map_prime_factor(p: int) -> int:
    """
    Maps prime factor p to a 1-based step coordinate in [1, 5] for a 6x6 grid.
    Formula: p mod 4, with 0 mapping to 4.
    """
    mapped = p % 4
    return 4 if mapped == 0 else mapped


def get_prime_factors(n: int) -> List[int]:
    """Extracts prime factors for a tile value v in [1, 36]."""
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
    """Generates all legal vector directions (dx, dy) for a tile value v on a 6x6 board."""
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


def can_solve_from_start(grid: List[List[int]], start_x: int, start_y: int) -> bool:
    """Backtracking solver to check if a full 36-step Hamiltonian tour is possible."""
    visited = [[False] * BOARD_SIZE for _ in range(BOARD_SIZE)]

    def dfs(x: int, y: int, count: int) -> bool:
        if count == TOTAL_CELLS:
            return True

        visited[y][x] = True
        tile_val = grid[y][x]
        vectors = get_vectors_for_value(tile_val)

        for dx, dy in vectors:
            nx, ny = x + dx, y + dy

            if (0 <= nx < BOARD_SIZE) and (0 <= ny < BOARD_SIZE) and not visited[ny][nx]:
                if dfs(nx, ny, count + 1):
                    return True

        visited[y][x] = False  # Backtrack
        return False

    return dfs(start_x, start_y, 1)


def evaluate_6x6_magic_square(grid: List[List[int]]) -> ValidationResult:
    """Evaluates a candidate 6x6 magic square for 100% start-cell solvability (36/36)."""
    solvable_count = 0
    unsolvable_starts: List[Point] = []

    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            if can_solve_from_start(grid, x, y):
                solvable_count += 1
            else:
                unsolvable_starts.append({"x": x, "y": y})

    return {
        "is_fully_solvable": solvable_count == TOTAL_CELLS,
        "solvable_count": solvable_count,
        "unsolvable_starts": unsolvable_starts
    }


# ==========================================
# EXAMPLE USAGE: TESTING A 6x6 MAGIC SQUARE
# ==========================================
if __name__ == "__main__":
    test_6x6_magic_square = [
        [35,  1,  6, 26, 19, 24],
        [ 3, 32,  7, 21, 23, 25],
        [31,  9,  2, 22, 27, 20],
        [ 8, 28, 33, 17, 10, 15],
        [30,  5, 34, 12, 14,  6],
        [ 4, 36, 29, 13, 18, 11]
    ]

    result = evaluate_6x6_magic_square(test_6x6_magic_square)

    print(f"Solvable Starts: {result['solvable_count']} / {TOTAL_CELLS}")
    if result["is_fully_solvable"]:
        print("SUCCESS: 6x6 Magic Square is 100% solvable from ALL 36 starting tiles!")
    else:
        print("Failed Start Coordinates:", result["unsolvable_starts"])