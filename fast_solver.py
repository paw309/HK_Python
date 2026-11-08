import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from typing import List, Tuple, Set, Dict, Optional

try:
    import numpy as np
    from numba import njit, objmode
    HAVE_NUMBA = True
except ImportError:  # falls back to the (slower) pure-Python search
    HAVE_NUMBA = False

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
    "quagga": [(0, 2), (2, 3)],
    "eland": [(2, 2), (2, 3)],
    "dromedary": [(0, 3), (1, 3)],
}

Position = Tuple[int, int]

# Cap on how many max-length paths are stored per start square (all are still counted).
MAX_STORED_PATHS = 1000


# =============================================================================
# GEOMETRY (used only once, to precompute the edge-conflict table)
# =============================================================================

def cross_product(o: Position, a: Position, b: Position) -> int:
    return (a[1] - o[1]) * (b[0] - o[0]) - (a[0] - o[0]) * (b[1] - o[1])


def segments_properly_intersect(p1, p2, p3, p4) -> bool:
    if (max(p1[0], p2[0]) < min(p3[0], p4[0]) or max(p3[0], p4[0]) < min(p1[0], p2[0]) or
            max(p1[1], p2[1]) < min(p3[1], p4[1]) or max(p3[1], p4[1]) < min(p1[1], p2[1])):
        return False
    d1 = cross_product(p3, p4, p1)
    d2 = cross_product(p3, p4, p2)
    d3 = cross_product(p1, p2, p3)
    d4 = cross_product(p1, p2, p4)
    return ((d1 > 0 > d2) or (d1 < 0 < d2)) and ((d3 > 0 > d4) or (d3 < 0 < d4))


def point_on_segment_interior(p, a, b) -> bool:
    if cross_product(a, b, p) != 0:
        return False
    return (min(a[1], b[1]) <= p[1] <= max(a[1], b[1]) and
            min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and p != a and p != b)


def segments_conflict(a1, a2, b1, b2) -> bool:
    """True if two move segments may not both appear in a palisade path."""
    return (segments_properly_intersect(a1, a2, b1, b2) or
            point_on_segment_interior(b1, a1, a2) or point_on_segment_interior(b2, a1, a2) or
            point_on_segment_interior(a1, b1, b2) or point_on_segment_interior(a2, b1, b2))


def expand_patterns(patterns: List[Tuple[int, int]]) -> List[Position]:
    deltas: Set[Position] = set()
    for a, b in patterns:
        for sx in (1, -1):
            for sy in (1, -1):
                deltas.add((sx * a, sy * b))
                if a != b:
                    deltas.add((sx * b, sy * a))
    deltas.discard((0, 0))
    return sorted(deltas)


def get_canonical_start_squares(board_size: int) -> List[Position]:
    half = (board_size + 1) // 2
    return [(r, c) for r in range(half) for c in range(r, half)]


# =============================================================================
# PRECOMPUTED MOVE GRAPH
#   cells are ints (r*n+c); edges are ints; sets are Python-int bitmasks.
# =============================================================================

class MoveGraph:
    def __init__(self, piece_name: str, n: int):
        self.n = n
        deltas = expand_patterns(PLAYABLE_PIECES[piece_name])
        edge_id: Dict[Tuple[int, int], int] = {}
        endpoints: List[Tuple[Position, Position]] = []
        self.adj: List[List[Tuple[int, int, int]]] = [[] for _ in range(n * n)]  # (dest, dest_bit, edge_bit)

        for r in range(n):
            for c in range(n):
                u = r * n + c
                for dr, dc in deltas:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < n and 0 <= nc < n:
                        v = nr * n + nc
                        key = (min(u, v), max(u, v))
                        if key not in edge_id:
                            edge_id[key] = len(endpoints)
                            endpoints.append(((r, c), (nr, nc)))
                        self.adj[u].append((v, 1 << v, 1 << edge_id[key]))

        # conflict[e] = bitmask of all edges that may not coexist with edge e
        E = len(endpoints)
        conflict = [0] * E
        for i in range(E):
            a1, a2 = endpoints[i]
            for j in range(i + 1, E):
                b1, b2 = endpoints[j]
                if segments_conflict(a1, a2, b1, b2):
                    conflict[i] |= 1 << j
                    conflict[j] |= 1 << i
        self.conflict_by_bit = {1 << i: m for i, m in enumerate(conflict)}
        self.num_edges = E
        # True if every move changes square colour (e.g. knight, unicorn) -> parity bound applies
        self.colour_alternating = all((dr + dc) % 2 for dr, dc in deltas)

        if HAVE_NUMBA:
            V = n * n
            maxdeg = max(len(a) for a in self.adj)
            self.np_adj_len = np.array([len(a) for a in self.adj], dtype=np.int32)
            self.np_adj_dest = np.zeros((V, maxdeg), dtype=np.int32)
            self.np_adj_edge = np.zeros((V, maxdeg), dtype=np.int32)
            for u, lst in enumerate(self.adj):
                for k, (v, _, eb) in enumerate(lst):
                    self.np_adj_dest[u, k] = v
                    self.np_adj_edge[u, k] = eb.bit_length() - 1
            self.np_conf_mat = np.zeros((E, E), dtype=np.bool_)
            ptr, idx = [0], []
            for i in range(E):
                js = [j for j in range(E) if (conflict[i] >> j) & 1]
                idx.extend(js)
                ptr.append(len(idx))
                self.np_conf_mat[i, js] = True
            self.np_conf_ptr = np.array(ptr, dtype=np.int32)
            self.np_conf_idx = np.array(idx if idx else [0], dtype=np.int32)
            self.np_colour = np.array([(c // n + c % n) & 1 for c in range(V)], dtype=np.int8)



# =============================================================================
# COMPILED SEARCH KERNEL (Numba) — iterative DFS, same semantics as the Python search
# =============================================================================

if HAVE_NUMBA:
    @njit(cache=True)
    def _now():
        with objmode(t="float64"):
            t = time.time()
        return t

    @njit(cache=True)
    def _upper_bound(cur, visited, blocked, adj_len, adj_dest, adj_edge, colour, alternating,
                     mark, stamp, stack):
        sp = 0
        stack[sp] = cur
        sp += 1
        mark[cur] = stamp
        cnt = 0
        leaves = 0
        same = 0
        cc = colour[cur]
        while sp > 0:
            sp -= 1
            u = stack[sp]
            deg = 0
            for k in range(adj_len[u]):
                v = adj_dest[u, k]
                if blocked[adj_edge[u, k]] == 0 and (not visited[v] or v == cur):
                    deg += 1
                    if mark[v] != stamp:
                        mark[v] = stamp
                        cnt += 1
                        if colour[v] == cc:
                            same += 1
                        stack[sp] = v
                        sp += 1
            if u != cur and deg == 1:
                leaves += 1
        bound = cnt - (leaves - 1 if leaves > 1 else 0)
        if alternating:
            opp = cnt - same
            par = 2 * same + 1 if opp > same else 2 * opp
            if par < bound:
                bound = par
        return bound

    @njit(cache=True)
    def _search_kernel(start, total, adj_len, adj_dest, adj_edge, conf_ptr, conf_idx, conf_mat,
                       colour, alternating, lower_bound, max_stored, time_limit):
        V = adj_len.shape[0]
        E = conf_ptr.shape[0] - 1
        maxdeg = adj_dest.shape[1]
        visited = np.zeros(V, dtype=np.bool_)
        blocked = np.zeros(E, dtype=np.int32)
        path = np.zeros(total, dtype=np.int32)
        path_edge = np.zeros(total, dtype=np.int32)
        mv_dest = np.zeros((total, maxdeg), dtype=np.int32)
        mv_edge = np.zeros((total, maxdeg), dtype=np.int32)
        mv_key = np.zeros(maxdeg, dtype=np.int32)
        mv_n = np.zeros(total, dtype=np.int32)
        mv_i = np.zeros(total, dtype=np.int32)
        mark = np.zeros(V, dtype=np.int64)
        stack = np.zeros(V + 1, dtype=np.int32)
        stored = np.zeros((max_stored, total), dtype=np.int32)
        n_stored = 0
        count = 0
        best = lower_bound if lower_bound > 1 else 1
        if best == 1:
            stored[0, 0] = start
            n_stored = 1
            count = 0  # the start node itself is recorded on entry below
        stamp = 0
        nodes = 0
        t0 = _now()
        timed_out = False

        visited[start] = True
        path[0] = start
        d = 0
        entering = True
        while True:
            if entering:
                entering = False
                nodes += 1
                if (nodes & 65535) == 0 and _now() - t0 > time_limit:
                    timed_out = True
                    break
                length = d + 1
                if length > best:
                    best = length
                    count = 0
                    n_stored = 0
                if length == best:
                    count += 1
                    if n_stored < max_stored:
                        for i in range(length):
                            stored[n_stored, i] = path[i]
                        n_stored += 1
                mv_n[d] = 0
                mv_i[d] = 0
                if length < total:
                    stamp += 1
                    cur = path[d]
                    if length + _upper_bound(cur, visited, blocked, adj_len, adj_dest, adj_edge,
                                             colour, alternating, mark, stamp, stack) >= best:
                        # generate moves, insertion-sorted by onward degree (Warnsdorff)
                        m = 0
                        for k in range(adj_len[cur]):
                            v = adj_dest[cur, k]
                            e = adj_edge[cur, k]
                            if visited[v] or blocked[e] != 0:
                                continue
                            deg = 0
                            for q in range(adj_len[v]):
                                w = adj_dest[v, q]
                                f = adj_edge[v, q]
                                if not visited[w] and w != v and blocked[f] == 0 and not conf_mat[e, f]:
                                    deg += 1
                            j = m
                            while j > 0 and mv_key[j - 1] > deg:
                                mv_key[j] = mv_key[j - 1]
                                mv_dest[d, j] = mv_dest[d, j - 1]
                                mv_edge[d, j] = mv_edge[d, j - 1]
                                j -= 1
                            mv_key[j] = deg
                            mv_dest[d, j] = v
                            mv_edge[d, j] = e
                            m += 1
                        mv_n[d] = m

            if mv_i[d] < mv_n[d]:
                k = mv_i[d]
                mv_i[d] = k + 1
                v = mv_dest[d, k]
                e = mv_edge[d, k]
                for p in range(conf_ptr[e], conf_ptr[e + 1]):
                    blocked[conf_idx[p]] += 1
                visited[v] = True
                d += 1
                path[d] = v
                path_edge[d] = e
                entering = True
            else:
                if d == 0:
                    break
                e = path_edge[d]
                for p in range(conf_ptr[e], conf_ptr[e + 1]):
                    blocked[conf_idx[p]] -= 1
                visited[path[d]] = False
                d -= 1

        return best, count, stored[:n_stored, :best].copy(), nodes, timed_out

# =============================================================================
# SOLVER ENGINE
# =============================================================================

class _Timeout(Exception):
    pass


class PalisadesSolver:
    def __init__(self, piece_name: str, board_size: int, time_limit_sec: float = 10.0,
                 graph: Optional[MoveGraph] = None, max_stored_paths: int = MAX_STORED_PATHS):
        self.piece_name = piece_name
        self.board_size = board_size
        self.time_limit_sec = time_limit_sec
        self.g = graph or MoveGraph(piece_name, board_size)
        self.total_squares = board_size * board_size
        self.max_stored_paths = max_stored_paths

    def solve_from_start(self, start_pos: Position, lower_bound: int = 1) -> Dict:
        if HAVE_NUMBA:
            return self._solve_compiled(start_pos, lower_bound)
        return self._solve_python(start_pos, lower_bound)

    def _solve_compiled(self, start_pos: Position, lower_bound: int) -> Dict:
        g, n = self.g, self.board_size
        t0 = time.time()
        best, count, stored, nodes, timed_out = _search_kernel(
            start_pos[0] * n + start_pos[1], self.total_squares,
            g.np_adj_len, g.np_adj_dest, g.np_adj_edge, g.np_conf_ptr, g.np_conf_idx, g.np_conf_mat,
            g.np_colour, g.colour_alternating, lower_bound, self.max_stored_paths, self.time_limit_sec)
        return {
            "start_square": start_pos,
            "max_length": int(best),
            "paths": [[(int(c) // n, int(c) % n) for c in row] for row in stored],
            "path_count": int(count),
            "elapsed_sec": round(time.time() - t0, 3),
            "timed_out": bool(timed_out),
            "nodes": int(nodes),
        }

    def _solve_python(self, start_pos: Position, lower_bound: int = 1) -> Dict:
        n = self.n = self.board_size
        adj = self.g.adj
        conflict = self.g.conflict_by_bit
        total = self.total_squares
        max_stored = self.max_stored_paths
        start = start_pos[0] * n + start_pos[1]

        best_len = max(1, lower_bound)
        best_paths: List[List[int]] = [[start]] if best_len == 1 else []
        best_count = 1 if best_len == 1 else 0
        path = [start]
        nodes = 0
        t0 = time.time()
        deadline = t0 + self.time_limit_sec
        timed_out = False
        colour = [(c // n + c % n) & 1 for c in range(total)]
        alternating = self.g.colour_alternating

        def upper_bound(cur: int, visited: int, blocked: int) -> int:
            """Max extra cells the path could still visit from cur (admissible bound).

            Flood-fills unvisited cells reachable via still-usable edges, then tightens with:
              * dead ends: a cell with only one usable edge can only be the path's last cell,
                so at most one of them can be used;
              * colour parity (colour-alternating pieces only): the path must alternate colours.
            """
            seen = 0
            stack = [cur]
            cnt = leaves = same = 0
            cur_col = colour[cur]
            while stack:
                u = stack.pop()
                deg = 0
                for v, vb, eb in adj[u]:
                    if not (blocked & eb) and (not (visited & vb) or v == cur):
                        deg += 1
                        if v != cur and not (seen & vb):
                            seen |= vb
                            cnt += 1
                            if colour[v] == cur_col:
                                same += 1
                            stack.append(v)
                if u != cur and deg == 1:
                    leaves += 1
            bound = cnt - (leaves - 1 if leaves > 1 else 0)
            if alternating:
                opp = cnt - same
                par = 2 * same + 1 if opp > same else 2 * opp
                if par < bound:
                    bound = par
            return bound

        def dfs(cur: int, visited: int, blocked: int, length: int):
            nonlocal nodes, best_len, best_paths, best_count
            nodes += 1
            if not (nodes & 4095) and time.time() > deadline:
                raise _Timeout

            if length > best_len:
                best_len = length
                best_paths = [path[:]]
                best_count = 1
            elif length == best_len:
                best_count += 1
                if len(best_paths) < max_stored:
                    best_paths.append(path[:])

            if length == total:
                return

            # Branch-and-bound: prune if even visiting every reachable cell can't tie the best.
            if length + upper_bound(cur, visited, blocked) < best_len:
                return

            # Collect legal moves; order by fewest onward moves (Warnsdorff) so long paths are found early.
            moves = []
            for v, vb, eb in adj[cur]:
                if not (visited & vb) and not (blocked & eb):
                    nb = blocked | conflict[eb]
                    nv = visited | vb
                    deg = 0
                    for w, wb, fb in adj[v]:
                        if not (nv & wb) and not (nb & fb):
                            deg += 1
                    moves.append((deg, v, vb, nb))
            moves.sort()

            for _, v, vb, nb in moves:
                path.append(v)
                dfs(v, visited | vb, nb, length + 1)
                path.pop()

        sys.setrecursionlimit(max(10000, total * 4))
        try:
            dfs(start, 1 << start, 0, 1)
        except _Timeout:
            timed_out = True

        elapsed = time.time() - t0
        return {
            "start_square": start_pos,
            "max_length": best_len,
            "paths": [[(c // n, c % n) for c in p] for p in best_paths],
            "path_count": best_count,
            "elapsed_sec": round(elapsed, 3),
            "timed_out": timed_out,
            "nodes": nodes,
        }


def _solve_worker(args):
    piece, size, time_limit, start = args
    return PalisadesSolver(piece, size, time_limit).solve_from_start(start)


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
            items = [f'{next_ind}"{k}": {format_val(val, level + 1)}' for k, val in v.items()]
            return "{\n" + ",\n".join(items) + f"\n{ind}}}"
        elif isinstance(v, list):
            if v and isinstance(v[0], list):
                path_lines = [f'{next_ind}[' + ",".join(map(str, p)) + "]" for p in v]
                return "[\n" + ",\n".join(path_lines) + f"\n{ind}]"
            return json.dumps(v)
        elif isinstance(v, str):
            return json.dumps(v)
        return str(v)

    return format_val(obj, 0)


def export_results_to_json(piece_name: str, board_size: int, results_dict: dict, filename: Optional[str] = None):
    if not filename:
        filename = f"{piece_name}_board_{board_size}.json"
    output_data = {piece_name: {str(board_size): results_dict}}
    with open(filename, "w", encoding="utf-8") as f:
        f.write(custom_format_json(output_data, indent=1))
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
    workers = int(input(f"Parallel worker processes (default {os.cpu_count()}): ") or str(os.cpu_count()))

    print(f"\nRunning Search for '{selected_piece}' on {board_size}x{board_size} board...")
    print("-" * 75)
    print(f"{'Start Square':<15} | {'Max Length':<10} | {'Path Count':<12} | {'Status':<12} | {'Time (s)':<8}")
    print("-" * 75)

    canonical_starts = get_canonical_start_squares(board_size)
    known_starts_data = {}
    estimated_starts_data = {}
    overall_max = 0
    total_max_paths_found = 0

    jobs = [(selected_piece, board_size, time_limit, s) for s in canonical_starts]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(_solve_worker, jobs):
            start_sq = result["start_square"]
            overall_max = max(overall_max, result["max_length"])
            total_max_paths_found += result["path_count"]

            status = "TIMEOUT" if result["timed_out"] else "EXHAUSTED"
            if result["max_length"] == board_size * board_size:
                status = "HAMILTONIAN"

            print(f"{str(start_sq):<15} | {result['max_length']:<10} | {result['path_count']:<12} | "
                  f"{status:<12} | {result['elapsed_sec']:<8}")

            sq_entry = {
                "length": result["max_length"],
                "paths": [[r * board_size + c for r, c in p] for p in result["paths"]],
            }
            target = estimated_starts_data if result["timed_out"] else known_starts_data
            target[f"{start_sq[0]},{start_sq[1]}"] = sq_entry

    board_output_section = {}
    if known_starts_data:
        board_output_section["known"] = {
            "length": max(v["length"] for v in known_starts_data.values()),
            "starts": known_starts_data,
        }
    if estimated_starts_data:
        board_output_section["estimated"] = {
            "length": max(v["length"] for v in estimated_starts_data.values()),
            "starts": estimated_starts_data,
        }

    export_results_to_json(selected_piece, board_size, board_output_section)

    print("-" * 75)
    print(f"Overall Longest Path Found for {selected_piece} on {board_size}x{board_size}: {overall_max} squares")
    print(f"Total Unique Longest Path Variations Across Canonical Starts: {total_max_paths_found}")
    print("=" * 75)


if __name__ == "__main__":
    main()