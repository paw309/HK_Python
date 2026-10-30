import math
import time
from typing import List, Tuple, Set, Dict, Optional

# =============================================================================
# HIGHLY PLAYABLE PIECE DEFINITIONS (5x5 to 10x10)
# =============================================================================

PLAYABLE_PIECES: Dict[str, List[Tuple[int, int]]] = {
    # Existing core roster
    "knight": [(1, 2)],
    "camel": [(1, 3)],
    "zebra": [(2, 3)],
    "giraffe": [(1, 4)],
    "antelope": [(3, 4)],
    "gnu": [(1, 2), (1, 3)],
    "unicorn": [(1, 2), (2, 3)],
    "bison": [(1, 3), (2, 3)],
    "zebu": [(1, 3), (1, 4)],
    "okapi": [(2, 3), (1, 4)],
}

Position = Tuple[int, int]


# =============================================================================
# CROSSING DETECTION GEOMETRY
# =============================================================================

def cross_product(o: Position, a: Position, b: Position) -> int:
    """Signed area of triangle OAB (x2)."""
    return (a[1] - o[1]) * (b[0] - o[0]) - (a[0] - o[0]) * (b[1] - o[1])


def segments_properly_intersect(p1: Position, p2: Position, p3: Position, p4: Position) -> bool:
    """Return True if segment p1-p2 properly crosses segment p3-p4."""
    d1 = cross_product(p3, p4, p1)
    d2 = cross_product(p3, p4, p2)
    d3 = cross_product(p1, p2, p3)
    d4 = cross_product(p1, p2, p4)

    return (
            ((d1 > 0 > d2) or (d1 < 0 < d2)) and
            ((d3 > 0 > d4) or (d3 < 0 < d4))
    )


def point_on_segment_interior(p: Position, a: Position, b: Position) -> bool:
    """Return True if point p lies strictly in the interior of segment a-b."""
    if cross_product(a, b, p) != 0:
        return False
    return (
            min(a[1], b[1]) <= p[1] <= max(a[1], b[1]) and
            min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and
            p != a and p != b
    )


def would_create_crossing(path: List[Position], new_start: Position, new_end: Position) -> bool:
    """Check if adding segment (new_start -> new_end) crosses existing path segments."""
    n = len(path)
    if n < 3:
        return False

    # Check against previous non-adjacent path segments [0, n-3]
    for i in range(n - 2):
        seg_s, seg_e = path[i], path[i + 1]
        if segments_properly_intersect(seg_s, seg_e, new_start, new_end):
            return True
        if point_on_segment_interior(new_end, seg_s, seg_e):
            return True

    # Check if existing vertices lie inside the new segment
    for i in range(n - 1):
        if point_on_segment_interior(path[i], new_start, new_end):
            return True

    return False


# =============================================================================
# MOVE DELTA GENERATOR & SYMMETRY HELPERS
# =============================================================================

def expand_patterns(patterns: List[Tuple[int, int]]) -> List[Position]:
    """Generate all 8-way symmetric move deltas for given (a, b) vector patterns."""
    deltas: Set[Position] = set()
    for a, b in patterns:
        for sx in (1, -1):
            for sy in (1, -1):
                deltas.add((sx * a, sy * b))
                if a != b:
                    deltas.add((sx * b, sy * a))
    deltas.discard((0, 0))
    return list(deltas)


def get_canonical_start_squares(board_size: int) -> List[Position]:
    """Generate non-equivalent starting squares in the fundamental octant (D4 symmetry)."""
    canonical_squares = []
    for r in range((board_size + 1) // 2):
        for c in range(r, (board_size + 1) // 2):
            canonical_squares.append((r, c))
    return canonical_squares


# =============================================================================
# SOLVER ENGINE (DEPTH-FIRST SEARCH WITH PATH COUNTING)
# =============================================================================

class PalisadesSolver:
    def __init__(self, piece_name: str, board_size: int, time_limit_sec: float = 10.0):
        self.piece_name = piece_name
        self.board_size = board_size
        self.time_limit_sec = time_limit_sec
        self.vectors = PLAYABLE_PIECES[piece_name]
        self.deltas = expand_patterns(self.vectors)
        self.total_squares = board_size * board_size

        self.best_path: List[Position] = []
        self.max_path_count: int = 0
        self.start_time = 0.0
        self.timed_out = False

    def get_legal_moves(self, current_pos: Position, visited: Set[Position], path: List[Position]) -> List[Position]:
        legal = []
        r, c = current_pos
        for dr, dc in self.deltas:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.board_size and 0 <= nc < self.board_size:
                target = (nr, nc)
                if target not in visited:
                    if not would_create_crossing(path, current_pos, target):
                        legal.append(target)
        return legal

    def _dfs(self, current_pos: Position, path: List[Position], visited: Set[Position]):
        if time.time() - self.start_time > self.time_limit_sec:
            self.timed_out = True
            return

        current_len = len(path)
        if current_len > len(self.best_path):
            self.best_path = list(path)
            self.max_path_count = 1  # Reset count for the new higher record
        elif current_len == len(self.best_path):
            self.max_path_count += 1  # Found another distinct path of the same max length

        if current_len == self.total_squares:
            return  # Full Hamiltonian tour found, max possible length reached

        next_moves = self.get_legal_moves(current_pos, visited, path)

        # Warnsdorff-like heuristic sorting (order by onward mobility)
        next_moves.sort(key=lambda m: len(self.get_legal_moves(m, visited | {m}, path + [m])))

        for move in next_moves:
            visited.add(move)
            path.append(move)

            self._dfs(move, path, visited)

            path.pop()
            visited.remove(move)

            if self.timed_out:
                return

    def solve_from_start(self, start_pos: Position) -> Dict:
        self.best_path = [start_pos]
        self.max_path_count = 1
        self.timed_out = False
        self.start_time = time.time()

        visited = {start_pos}
        self._dfs(start_pos, [start_pos], visited)
        elapsed = time.time() - self.start_time

        return {
            "start_square": start_pos,
            "max_length": len(self.best_path),
            "path_count": self.max_path_count,
            "is_hamiltonian": len(self.best_path) == self.total_squares,
            "path": self.best_path,
            "elapsed_sec": round(elapsed, 3),
            "timed_out": self.timed_out
        }


# =============================================================================
# CLI INTERACTION & RUNNER
# =============================================================================

def main():
    print("=" * 75)
    print("PALISADES — LONGEST NON-CROSSING PATH SOLVER & COUNTER (5x5 to 10x10)")
    print("=" * 75)

    print("\nHighly Playable Candidate Pieces:")
    pieces = list(PLAYABLE_PIECES.keys())
    for i, name in enumerate(pieces, 1):
        vec_str = ", ".join([f"({a},{b})" for a, b in PLAYABLE_PIECES[name]])
        print(f"  [{i:2d}] {name:<12} Vectors: {vec_str}")

    print("\nSelect Options:")
    piece_idx = int(input(f"Enter Piece Number [1-{len(pieces)}] (default 1 - knight): ") or "1") - 1
    selected_piece = pieces[piece_idx]

    board_size = int(input("Enter Board Size [5-10] (default 5): ") or "5")
    time_limit = float(input("Enter Time Limit per start square in seconds (default 5.0): ") or "5.0")

    print(f"\nRunning Search for '{selected_piece}' on {board_size}x{board_size} board...")
    print("-" * 75)
    print(f"{'Start Square':<15} | {'Max Length':<10} | {'Path Count':<12} | {'Status':<12} | {'Time (s)':<8}")
    print("-" * 75)

    canonical_starts = get_canonical_start_squares(board_size)
    overall_max = 0
    total_max_paths_found = 0

    for start_sq in canonical_starts:
        solver = PalisadesSolver(selected_piece, board_size, time_limit_sec=time_limit)
        result = solver.solve_from_start(start_sq)

        overall_max = max(overall_max, result["max_length"])
        total_max_paths_found += result["path_count"]
        status = "HAMILTONIAN" if result["is_hamiltonian"] else ("TIMEOUT" if result["timed_out"] else "EXHAUSTED")

        print(f"{str(start_sq):<15} | {result['max_length']:<10} | {result['path_count']:<12} | {status:<12} | {result['elapsed_sec']:<8}")

    print("-" * 75)
    print(f"Overall Longest Path Found for {selected_piece} on {board_size}x{board_size}: {overall_max} squares")
    print(f"Total Unique Longest Path Variations Across Canonical Starts: {total_max_paths_found}")
    print("=" * 75)


if __name__ == "__main__":
    main()