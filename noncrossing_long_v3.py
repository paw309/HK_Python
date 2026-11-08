import json
import math
import time
from typing import List, Tuple, Set, Dict, Optional

# =============================================================================
# HIGHLY PLAYABLE PIECE DEFINITIONS (5x5 to 10x10)
# =============================================================================

PLAYABLE_PIECES: Dict[str, List[Tuple[int, int]]] = {
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
    "nyala": [(2, 3), (3, 4)],

}

Position = Tuple[int, int]


# =============================================================================
# FAST CROSSING DETECTION GEOMETRY
# =============================================================================

def cross_product(o: Position, a: Position, b: Position) -> int:
    return (a[1] - o[1]) * (b[0] - o[0]) - (a[0] - o[0]) * (b[1] - o[1])


def segments_properly_intersect(p1: Position, p2: Position, p3: Position, p4: Position) -> bool:
    if (max(p1[0], p2[0]) < min(p3[0], p4[0]) or max(p3[0], p4[0]) < min(p1[0], p2[0]) or
            max(p1[1], p2[1]) < min(p3[1], p4[1]) or max(p3[1], p4[1]) < min(p1[1], p2[1])):
        return False

    d1 = cross_product(p3, p4, p1)
    d2 = cross_product(p3, p4, p2)
    d3 = cross_product(p1, p2, p3)
    d4 = cross_product(p1, p2, p4)

    return (
            ((d1 > 0 > d2) or (d1 < 0 < d2)) and
            ((d3 > 0 > d4) or (d3 < 0 < d4))
    )


def point_on_segment_interior(p: Position, a: Position, b: Position) -> bool:
    if cross_product(a, b, p) != 0:
        return False
    return (
            min(a[1], b[1]) <= p[1] <= max(a[1], b[1]) and
            min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and
            p != a and p != b
    )


def would_create_crossing(path: List[Position], new_start: Position, new_end: Position) -> bool:
    n = len(path)
    if n < 3:
        return False

    for i in range(n - 2):
        seg_s, seg_e = path[i], path[i + 1]
        if segments_properly_intersect(seg_s, seg_e, new_start, new_end):
            return True
        if point_on_segment_interior(new_end, seg_s, seg_e):
            return True

    for i in range(n - 1):
        if point_on_segment_interior(path[i], new_start, new_end):
            return True

    return False


# =============================================================================
# MOVE DELTA GENERATOR & SYMMETRY HELPERS
# =============================================================================

def expand_patterns(patterns: List[Tuple[int, int]]) -> List[Position]:
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
    canonical_squares = []
    for r in range((board_size + 1) // 2):
        for c in range(r, (board_size + 1) // 2):
            canonical_squares.append((r, c))
    return canonical_squares


# =============================================================================
# SOLVER ENGINE (WITH THROTTLED TIME CHECKS)
# =============================================================================

class PalisadesSolver:
    def __init__(self, piece_name: str, board_size: int, time_limit_sec: float = 10.0):
        self.piece_name = piece_name
        self.board_size = board_size
        self.time_limit_sec = time_limit_sec
        self.vectors = PLAYABLE_PIECES[piece_name]
        self.deltas = expand_patterns(self.vectors)
        self.total_squares = board_size * board_size

        self.best_paths: List[List[Position]] = []
        self.max_path_length: int = 0
        self.start_time = 0.0
        self.timed_out = False
        self.node_count = 0

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
        self.node_count += 1
        if self.node_count & 255 == 0:
            if time.time() - self.start_time > self.time_limit_sec:
                self.timed_out = True
                return

        current_len = len(path)
        if current_len > self.max_path_length:
            self.max_path_length = current_len
            self.best_paths = [list(path)]
        elif current_len == self.max_path_length:
            if path not in self.best_paths:
                self.best_paths.append(list(path))

        if current_len == self.total_squares:
            return

        next_moves = self.get_legal_moves(current_pos, visited, path)
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
        self.best_paths = [[start_pos]]
        self.max_path_length = 1
        self.timed_out = False
        self.node_count = 0
        self.start_time = time.time()

        visited = {start_pos}
        self._dfs(start_pos, [start_pos], visited)
        elapsed = time.time() - self.start_time

        return {
            "start_square": start_pos,
            "max_length": self.max_path_length,
            "paths": self.best_paths,
            "elapsed_sec": round(elapsed, 3),
            "timed_out": self.timed_out
        }


# =============================================================================
# CUSTOM JSON EXPORTER (INLINE PATH FORMATTING)
# =============================================================================

def custom_format_json(obj, indent=1) -> str:
    """Recursively formats dictionary data, enforcing inline single-line lists for paths."""

    def format_val(v, level):
        ind = " " * (level * indent)
        next_ind = " " * ((level + 1) * indent)

        if isinstance(v, dict):
            if not v:
                return "{}"
            items = []
            for k, val in v.items():
                formatted_item = format_val(val, level + 1)
                items.append(f'{next_ind}"{k}": {formatted_item}')
            return "{\n" + ",\n".join(items) + f"\n{ind}}}"

        elif isinstance(v, list):
            # Check if this is the list of paths (list of integer lists)
            if v and isinstance(v[0], list):
                path_lines = []
                for path in v:
                    path_str = "[" + ",".join(map(str, path)) + "]"
                    path_lines.append(f'{next_ind}{path_str}')
                return "[\n" + ",\n".join(path_lines) + f"\n{ind}]"
            else:
                return json.dumps(v)

        elif isinstance(v, str):
            return json.dumps(v)
        else:
            return str(v)

    return format_val(obj, 0)


def export_results_to_json(piece_name: str, board_size: int, results_dict: dict, filename: Optional[str] = None):
    if not filename:
        filename = f"{piece_name}_board_{board_size}.json"

    output_data = {
        piece_name: {
            str(board_size): results_dict
        }
    }

    formatted_string = custom_format_json(output_data, indent=1)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(formatted_string)

    print(f"\nSuccessfully exported formatted results to '{filename}'")


# =============================================================================
# CLI INTERACTION & RUNNER
# =============================================================================

def main():
    print("=" * 75)
    print("PALISADES — LONGEST NON-CROSSING PATH SOLVER & CUSTOM JSON EXPORTER")
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

    known_starts_data = {}
    estimated_starts_data = {}

    overall_max = 0
    total_max_paths_found = 0

    for start_sq in canonical_starts:
        solver = PalisadesSolver(selected_piece, board_size, time_limit_sec=time_limit)
        result = solver.solve_from_start(start_sq)

        overall_max = max(overall_max, result["max_length"])
        total_max_paths_found += len(result["paths"])

        status = "TIMEOUT" if result["timed_out"] else "EXHAUSTED"
        if len(result["paths"]) > 0 and len(result["paths"][0]) == board_size * board_size:
            status = "HAMILTONIAN"

        print(
            f"{str(start_sq):<15} | {result['max_length']:<10} | {len(result['paths']):<12} | {status:<12} | {result['elapsed_sec']:<8}")

        sq_key = f"{start_sq[0]},{start_sq[1]}"

        # Convert (r, c) tuples into flattened linear cell indices (r * board_size + c)
        formatted_paths = [
            [r * board_size + c for r, c in path_seq]
            for path_seq in result["paths"]
        ]

        sq_entry = {
            "length": result["max_length"],
            "paths": formatted_paths
        }

        if result["timed_out"]:
            estimated_starts_data[sq_key] = sq_entry
        else:
            known_starts_data[sq_key] = sq_entry

    board_output_section = {}
    if known_starts_data:
        board_output_section["known"] = {
            "length": max([v["length"] for v in known_starts_data.values()], default=0),
            "starts": known_starts_data
        }
    if estimated_starts_data:
        board_output_section["estimated"] = {
            "length": max([v["length"] for v in estimated_starts_data.values()], default=0),
            "starts": estimated_starts_data
        }

    export_results_to_json(selected_piece, board_size, board_output_section)

    print("-" * 75)
    print(f"Overall Longest Path Found for {selected_piece} on {board_size}x{board_size}: {overall_max} squares")
    print(f"Total Unique Longest Path Variations Across Canonical Starts: {total_max_paths_found}")
    print("=" * 75)


if __name__ == "__main__":
    main()