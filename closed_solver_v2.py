import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from typing import List, Tuple, Set, Dict, Optional

import numpy as np
from numba import njit, objmode

# =============================================================================
# HIGHLY PLAYABLE PIECE DEFINITIONS (5x5 to 10x10)
# =============================================================================

PLAYABLE_PIECES: Dict[str, List[Tuple[int, int]]] = {
    "knight": [(1, 2)],
    "camel": [(1, 3)],
    "zebra": [(2, 3)],
    "giraffe": [(1, 4)],
    "antelope": [(3, 4)],
    "chamois": [(0, 3), (2, 2)],
    "markhor": [(0, 3), (2, 3)],
    "ibex": [(0, 3), (1, 4)],
    "argali": [(0, 3), (2, 4)],
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
MAX_STORED_PATHS = 1000


# =============================================================================
# GEOMETRY
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


def board_symmetries(n: int):
    """The 8 dihedral maps of the board, as functions on (r, c)."""
    m = n - 1
    return [
        lambda r, c: (r, c), lambda r, c: (c, m - r), lambda r, c: (m - r, m - c), lambda r, c: (m - c, r),
        lambda r, c: (r, m - c), lambda r, c: (m - r, c), lambda r, c: (c, r), lambda r, c: (m - c, m - r),
    ]


# =============================================================================
# PRECOMPUTED MOVE GRAPH
# =============================================================================

class MoveGraph:
    def __init__(self, piece_name: str, n: int):
        self.n = n
        deltas = expand_patterns(PLAYABLE_PIECES[piece_name])
        edge_id: Dict[Tuple[int, int], int] = {}
        endpoints: List[Tuple[Position, Position]] = []
        adj: List[List[Tuple[int, int]]] = [[] for _ in range(n * n)]

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
                        adj[u].append((v, edge_id[key]))

        E = len(endpoints)
        conflict: List[List[int]] = [[] for _ in range(E)]
        for i in range(E):
            a1, a2 = endpoints[i]
            for j in range(i + 1, E):
                b1, b2 = endpoints[j]
                if segments_conflict(a1, a2, b1, b2):
                    conflict[i].append(j)
                    conflict[j].append(i)
        self.num_edges = E
        self.colour_alternating = all((dr + dc) % 2 for dr, dc in deltas)

        V = n * n
        maxdeg = max(len(a) for a in adj)
        self.np_adj_len = np.array([len(a) for a in adj], dtype=np.int32)
        self.np_adj_dest = np.zeros((V, maxdeg), dtype=np.int32)
        self.np_adj_edge = np.zeros((V, maxdeg), dtype=np.int32)
        for u, lst in enumerate(adj):
            for k, (v, e) in enumerate(lst):
                self.np_adj_dest[u, k] = v
                self.np_adj_edge[u, k] = e
        self.np_conf_mat = np.zeros((E, E), dtype=np.bool_)
        ptr, idx = [0], []
        for i in range(E):
            js = sorted(conflict[i])
            idx.extend(js)
            ptr.append(len(idx))
            self.np_conf_mat[i, js] = True
        self.np_conf_ptr = np.array(ptr, dtype=np.int32)
        self.np_conf_idx = np.array(idx if idx else [0], dtype=np.int32)
        self.np_colour = np.array([(c // n + c % n) & 1 for c in range(V)], dtype=np.int8)

        # rotation tables: sym[m] = (sym_v, sym_e) holding g^0..g^(m-1) for the
        # 360/m-degree rotation (m = 1 is the identity, i.e. no symmetry constraint)
        def rot(r, c):
            return c, n - 1 - r
        self.sym = {}
        for m in (1, 2, 4):
            step = 4 // m if m > 1 else 0
            sv = np.zeros((m, V), dtype=np.int32)
            se = np.zeros((m, E), dtype=np.int32)
            for j in range(m):
                def g(p, t=step * j):
                    r, c = p
                    for _ in range(t):
                        r, c = rot(r, c)
                    return r, c
                for v in range(V):
                    r, c = g((v // n, v % n))
                    sv[j, v] = r * n + c
                for i, (a, b) in enumerate(endpoints):
                    ga, gb = g(a), g(b)
                    u2, v2 = ga[0] * n + ga[1], gb[0] * n + gb[1]
                    se[j, i] = edge_id[(min(u2, v2), max(u2, v2))]
            self.sym[m] = (sv, se, False)
        for key, mirror in (("h", lambda r, c: (r, n - 1 - c)), ("d", lambda r, c: (c, r))):
            sv = np.zeros((2, V), dtype=np.int32)
            se = np.zeros((2, E), dtype=np.int32)
            for v in range(V):
                sv[0, v] = v
                r, c = mirror(v // n, v % n)
                sv[1, v] = r * n + c
            for i, (a, b) in enumerate(endpoints):
                se[0, i] = i
                u2, v2 = sv[1, a[0] * n + a[1]], sv[1, b[0] * n + b[1]]
                se[1, i] = edge_id[(min(u2, v2), max(u2, v2))]
            self.sym[key] = (sv, se, True)


# =============================================================================
# COMPILED SEARCH KERNEL (Numba) — closed tours
# =============================================================================

@njit(cache=True)
def _now():
    with objmode(t="float64"):
        t = time.time()
    return t


@njit(cache=True)
def _closed_bound(cur, start, first, length, visited, blocked, adj_len, adj_dest, adj_edge,
                  colour, alternating, vis_col, mark, alive, deg, queue, stamp):
    """Upper bound on how many more squares a closed tour can add, given the current path
    start..cur; -1 if the tour can no longer be closed through unvisited squares.

    The rest of the tour is a path cur -> x1 -> ... -> xk -> start, so every xi needs two
    usable (unblocked) edges into {unvisited} + {cur, start}. Squares failing that are
    peeled off repeatedly (2-core), then only the part still connected to cur counts, and
    it must touch start. For colour-alternating pieces the cycle must be colour-balanced.
    Only squares numbered above `first` may make the closing move (direction symmetry breaking).
    """
    # 1. region reachable from cur through unvisited squares
    qt = 0
    queue[qt] = cur
    qt += 1
    mark[cur] = stamp
    qh = 0
    while qh < qt:
        u = queue[qh]
        qh += 1
        for k in range(adj_len[u]):
            v = adj_dest[u, k]
            if visited[v] or mark[v] == stamp or blocked[adj_edge[u, k]] != 0:
                continue
            mark[v] = stamp
            queue[qt] = v
            qt += 1
    if qt == 1:
        return -1
    if start < 0:
        return qt - 1
    # 2. degrees inside region + {cur, start}
    for i in range(1, qt):
        alive[queue[i]] = stamp
    sp = qt  # reuse tail of queue as peel stack
    for i in range(1, qt):
        u = queue[i]
        dg = 0
        for k in range(adj_len[u]):
            if blocked[adj_edge[u, k]] != 0:
                continue
            v = adj_dest[u, k]
            if alive[v] == stamp or v == cur or (v == start and u > first):
                dg += 1
        deg[u] = dg
        if dg < 2:
            alive[u] = 0
            queue[sp] = u
            sp += 1
    # 3. peel to 2-core
    while sp > qt:
        sp -= 1
        u = queue[sp]
        for k in range(adj_len[u]):
            v = adj_dest[u, k]
            if alive[v] == stamp and blocked[adj_edge[u, k]] == 0:
                deg[v] -= 1
                if deg[v] < 2:
                    alive[v] = 0
                    queue[sp] = v
                    sp += 1
    # 4. component of cur among surviving squares; must touch start
    s2 = -stamp  # distinct marker value for this pass
    qt = 0
    queue[qt] = cur
    qt += 1
    qh = 0
    cnt = 0
    c0 = 0
    touches_start = False
    while qh < qt:
        u = queue[qh]
        qh += 1
        for k in range(adj_len[u]):
            if blocked[adj_edge[u, k]] != 0:
                continue
            v = adj_dest[u, k]
            if v == start and u != cur and u > first:
                touches_start = True
            if alive[v] == stamp:
                alive[v] = s2
                queue[qt] = v
                qt += 1
                cnt += 1
                if colour[v] == 0:
                    c0 += 1
    if not touches_start:
        return -1
    bound = cnt
    if alternating:
        a = vis_col[0] + c0
        b = vis_col[1] + cnt - c0
        par = 2 * (a if a < b else b) - length
        if par < bound:
            bound = par
    return bound


@njit(cache=True)
def _search_kernel(prefix, total, adj_len, adj_dest, adj_edge, conf_ptr, conf_idx, conf_mat,
                   colour, alternating, lower_bound, max_stored, time_limit, seed, randomize, max_nodes,
                   sym_v, sym_e, reflect):
    """DFS for the longest non-crossing closed tour that begins with the fixed path `prefix`
    (usually just the start square) and closes back to prefix[0].
    Records tours of length >= lower_bound (ties are counted/stored too).

    sym_v/sym_e (shape (m, V) / (m, E)) are the powers g^0..g^(m-1) of a board rotation g.
    With m > 1 only tours invariant under g are searched: the kernel builds one arc
    P = start..w and the tour is P, gP, ..., g^(m-1)P, closed by the move w -> g(start).
    Every square/move is added together with its images, so the depth drops m-fold.

    With `reflect` (m = 2, g a mirror) the tour is P followed by g(P) reversed: the arc starts
    on the mirror axis (or with the axis-crossing move start -> g(start)) and is closed by a
    move w -> g(w) or by stepping onto an unvisited axis square y (w -> y -> g(w))."""
    m_sym = sym_v.shape[0]
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
    alive = np.zeros(V, dtype=np.int64)
    deg = np.zeros(V, dtype=np.int32)
    queue = np.zeros(3 * V + 2, dtype=np.int32)
    vis_col = np.zeros(2, dtype=np.int32)
    stored = np.zeros((max_stored, total), dtype=np.int32)
    n_stored = 0
    count = 0
    best = lower_bound if lower_bound > 3 else 3
    found = 0
    stamp = 0
    nodes = 0
    t0 = _now()
    timed_out = False
    rng = np.uint64(seed * 2654435761 + 88172645463325252)

    start = prefix[0]
    target = sym_v[1 % m_sym, start]  # square the arc must close onto
    if m_sym > 1:
        alternating = False  # colour bound below assumes a plain (non-symmetric) tour
        for j in range(1, m_sym):
            if sym_v[j, start] == start and not reflect:
                return 0, 0, stored[:0, :0].copy(), 0, False
    start_fixed = reflect and sym_v[1, start] == start
    if reflect:
        target = -1
        if not start_fixed:
            # the tour must cross the axis with the move start -> g(start)
            gs = sym_v[1, start]
            se = -1
            for k in range(adj_len[start]):
                if adj_dest[start, k] == gs:
                    se = adj_edge[start, k]
            if se < 0:
                return 0, 0, stored[:0, :0].copy(), 0, False
            for p in range(conf_ptr[se], conf_ptr[se + 1]):
                blocked[conf_idx[p]] += 1
    for i in range(prefix.shape[0]):
        v = prefix[i]
        for j in range(m_sym):
            visited[sym_v[j, v]] = True
        vis_col[colour[v]] += 1
        path[i] = v
        if i > 0:
            u = prefix[i - 1]
            for k in range(adj_len[u]):
                if adj_dest[u, k] == v:
                    e = adj_edge[u, k]
                    path_edge[i] = e
                    for j in range(m_sym):
                        ej = sym_e[j, e]
                        for p in range(conf_ptr[ej], conf_ptr[ej + 1]):
                            blocked[conf_idx[p]] += 1
                    break
    base = prefix.shape[0] - 1
    # Each tour is found in both directions; for a plain search keep only the direction whose
    # first move goes to a lower-numbered square than the last one (halves the search).
    break_dir = base == 0 and m_sym == 1
    d = base
    entering = True
    while True:
        if entering:
            entering = False
            nodes += 1
            if nodes > max_nodes or ((nodes & 16383) == 0 and _now() - t0 > time_limit):
                timed_out = True
                break

            length = d + 1
            cur = path[d]
            mv_n[d] = 0
            mv_i[d] = 0

            # A closing move needs >= 3 squares; with 2 it would reuse the same edge.
            full = length * m_sym
            if reflect:
                if length >= 2:
                    base_len = 2 * length - (1 if start_fixed else 0)
                    for k in range(adj_len[cur]):
                        v = adj_dest[cur, k]
                        f = adj_edge[cur, k]
                        if blocked[f] != 0:
                            continue
                        if v == sym_v[1, cur]:
                            full = base_len
                            mid = -1
                        elif sym_v[1, v] == v and not visited[v] and not conf_mat[f, sym_e[1, f]]:
                            full = base_len + 1
                            mid = v
                        else:
                            continue
                        if full > best:
                            best = full
                            count = 0
                            n_stored = 0
                        if full == best:
                            found = best
                            count += 1
                            if n_stored < max_stored:
                                q = 0
                                for i in range(length):
                                    stored[n_stored, q] = path[i]
                                    q += 1
                                if mid >= 0:
                                    stored[n_stored, q] = mid
                                    q += 1
                                lo = 1 if start_fixed else 0
                                for i in range(length - 1, lo - 1, -1):
                                    stored[n_stored, q] = sym_v[1, path[i]]
                                    q += 1
                                n_stored += 1
            elif full >= 3 and not (m_sym == 2 and length == 1):
                for k in range(adj_len[cur]):
                    if adj_dest[cur, k] == target:
                        f = adj_edge[cur, k]
                        ok = blocked[f] == 0 and not (break_dir and cur < path[1])
                        for j in range(1, m_sym):
                            if conf_mat[f, sym_e[j, f]]:
                                ok = False
                        if ok:
                            if full > best:
                                best = full
                                count = 0
                                n_stored = 0
                            if full == best:
                                found = best
                                count += 1
                                if n_stored < max_stored:
                                    for j in range(m_sym):
                                        for i in range(length):
                                            stored[n_stored, j * length + i] = sym_v[j, path[i]]
                                    n_stored += 1
                        break

            if length < total:
                ok = True
                if d > 0:
                    stamp += 1
                    first = path[1] if break_dir else -1
                    ub = _closed_bound(cur, target, first, length, visited, blocked, adj_len, adj_dest, adj_edge,
                                       colour, alternating, vis_col, mark, alive, deg, queue, stamp)
                    if reflect:
                        ok = ub >= 0 and 2 * (length + ub) + 1 >= best
                    else:
                        ok = ub >= 0 and (length + ub) * m_sym >= best
                if ok:
                    m = 0
                    for k in range(adj_len[cur]):
                        v = adj_dest[cur, k]
                        e = adj_edge[cur, k]
                        if visited[v] or blocked[e] != 0:
                            continue
                        bad = False
                        for j in range(1, m_sym):
                            if sym_v[j, v] == v or sym_e[j, e] == e or conf_mat[e, sym_e[j, e]]:
                                bad = True
                        if bad:
                            continue
                        dg = 0
                        for q in range(adj_len[v]):
                            w = adj_dest[v, q]
                            f = adj_edge[v, q]
                            if not visited[w] and blocked[f] == 0 and not conf_mat[e, f]:
                                dg += 1
                        key = dg * 64
                        if randomize:
                            rng ^= rng << np.uint64(13)
                            rng ^= rng >> np.uint64(7)
                            rng ^= rng << np.uint64(17)
                            key += np.int32(rng & np.uint64(63))
                        j = m
                        while j > 0 and mv_key[j - 1] > key:
                            mv_key[j] = mv_key[j - 1]
                            mv_dest[d, j] = mv_dest[d, j - 1]
                            mv_edge[d, j] = mv_edge[d, j - 1]
                            j -= 1
                        mv_key[j] = key
                        mv_dest[d, j] = v
                        mv_edge[d, j] = e
                        m += 1
                    mv_n[d] = m

        if mv_i[d] < mv_n[d]:
            k = mv_i[d]
            mv_i[d] = k + 1
            v = mv_dest[d, k]
            e = mv_edge[d, k]
            for j in range(m_sym):
                ej = sym_e[j, e]
                for p in range(conf_ptr[ej], conf_ptr[ej + 1]):
                    blocked[conf_idx[p]] += 1
                visited[sym_v[j, v]] = True
            vis_col[colour[v]] += 1
            d += 1
            path[d] = v
            path_edge[d] = e
            entering = True
        else:
            if d == base:
                break
            e = path_edge[d]
            for j in range(m_sym):
                ej = sym_e[j, e]
                for p in range(conf_ptr[ej], conf_ptr[ej + 1]):
                    blocked[conf_idx[p]] -= 1
                visited[sym_v[j, path[d]]] = False
            vis_col[colour[path[d]]] -= 1
            d -= 1

    if found == 0:
        best = 0
    return best, count, stored[:n_stored, :best].copy(), nodes, timed_out


# =============================================================================
# SOLVER ENGINE
# =============================================================================

_GRAPH_CACHE: Dict[Tuple[str, int], MoveGraph] = {}


def get_graph(piece: str, n: int) -> MoveGraph:
    key = (piece, n)
    if key not in _GRAPH_CACHE:
        _GRAPH_CACHE[key] = MoveGraph(piece, n)
    return _GRAPH_CACHE[key]


class PalisadesSolver:
    def __init__(self, piece_name: str, board_size: int, time_limit_sec: float = 10.0,
                 graph: Optional[MoveGraph] = None, max_stored_paths: int = MAX_STORED_PATHS):
        self.piece_name = piece_name
        self.board_size = board_size
        self.time_limit_sec = time_limit_sec
        self.g = graph or get_graph(piece_name, board_size)
        self.total_squares = board_size * board_size
        self.max_stored_paths = max_stored_paths

    def solve_from_start(self, start_pos: Position, lower_bound: int = 0, seed: int = 0,
                         randomize: bool = False, prefix: Optional[List[int]] = None,
                         max_nodes: int = 1 << 62, symmetry=1) -> Dict:
        g, n = self.g, self.board_size
        t0 = time.time()
        if prefix is None:
            prefix = [start_pos[0] * n + start_pos[1]]
        best, count, stored, nodes, timed_out = _search_kernel(
            np.array(prefix, dtype=np.int32), self.total_squares,
            g.np_adj_len, g.np_adj_dest, g.np_adj_edge, g.np_conf_ptr, g.np_conf_idx, g.np_conf_mat,
            g.np_colour, g.colour_alternating, lower_bound, self.max_stored_paths, self.time_limit_sec,
            seed, randomize, max_nodes, *g.sym[symmetry])
        return {
            "start_square": start_pos,
            "max_length": int(best),
            "paths": [[int(c) for c in row] for row in stored],
            "path_count": int(count),
            "elapsed_sec": round(time.time() - t0, 3),
            "timed_out": bool(timed_out),
            "nodes": int(nodes),
        }


SYMMETRIES = (2, 4, "h", "d")  # 180/90-degree rotations, vertical and diagonal mirrors


def _seed_worker(args):
    """Phase 1: cheap seeds. Searches restricted to symmetric tours are much shallower and
    often find long tours quickly; randomized restarts cover pieces/boards where they don't."""
    piece, size, time_limit, start, slices, seed0 = args
    best_len, best_path = 0, None
    t_sym = time_limit / 2 / len(SYMMETRIES)
    sym_solver = PalisadesSolver(piece, size, t_sym, max_stored_paths=1)
    for m in SYMMETRIES:
        r = sym_solver.solve_from_start(start, lower_bound=best_len + 1, symmetry=m)
        if r["max_length"] > best_len:
            best_len, best_path = r["max_length"], r["paths"][0]
    # independent of the symmetric seeds, so phase 2 also gets an asymmetric starting tour
    solver = PalisadesSolver(piece, size, time_limit / 2 / slices, max_stored_paths=1)
    probe_len, probe_path = 0, None
    for i in range(slices):
        r = solver.solve_from_start(start, lower_bound=probe_len + 1, seed=seed0 + i, randomize=i > 0)
        if r["max_length"] > probe_len:
            probe_len, probe_path = r["max_length"], r["paths"][0]
        if not r["timed_out"]:
            break  # exhausted: nothing longer exists from this start
    if probe_len > best_len:
        best_len, best_path = probe_len, probe_path
    return start, best_len, best_path, probe_path


LNS_PARAMS = (0.45, 50000, 5000, 0.05, 200)  # segment fraction, node budget, slack prob, stall


def _lns_worker(args):
    """Phase 2: large-neighbourhood search. Repeatedly cut a random segment out of the best
    tour through `start` (never the start itself) and search, with a small node budget, for a
    replacement that closes the tour with at least as many squares. Equal-length replacements
    are accepted too, so the tour keeps drifting instead of getting stuck."""
    import random
    piece, size, time_limit, start, tour, seed = args[:6]
    kfrac, node_base, node_per, p_slack, stall = args[6] if len(args) > 6 else LNS_PARAMS
    if not tour:
        return start, 0, None
    n = size
    rnd = random.Random(seed)
    solver = PalisadesSolver(piece, n, time_limit, max_stored_paths=1)
    best = list(tour)
    cur = list(tour)
    deadline = time.time() + time_limit
    it = since_best = 0
    while time.time() < deadline:
        it += 1
        L = len(cur)
        kmax = max(1, min(L - 2, 6 + int(L * kfrac)))
        k = rnd.randint(min(4, kmax), kmax)
        i = rnd.randrange(0, L - k)              # remove cur[i+1 .. i+k]; index 0 stays
        prefix = cur[i + k + 1:] + cur[:i + 1]   # kept path, closing back to cur[i+k+1]
        if since_best > stall and rnd.random() < 0.5:
            cur, since_best = list(best), 0     # stagnating away from best: go back to it
            continue
        # occasionally accept a slightly shorter tour to escape plateaus
        slack = 2 if rnd.random() < p_slack else 0
        r = solver.solve_from_start(None, lower_bound=L - slack, seed=seed * 7919 + it, randomize=True,
                                    prefix=prefix, max_nodes=node_base + node_per * k)
        since_best += 1
        if r["max_length"] >= L - slack and r["paths"]:
            p = r["paths"][0]
            j = p.index(cur[0])
            cur = p[j:] + p[:j]
            if len(cur) > len(best):
                best, since_best = list(cur), 0
    return start, len(best), best


def _solve_worker(args):
    """Phases 3/4: deterministic search for tours of length >= lower_bound."""
    piece, size, time_limit, start, lower_bound = args
    return PalisadesSolver(piece, size, time_limit).solve_from_start(start, lower_bound=lower_bound)


class CycleBank:
    """Best known closed tour through every square. A closed tour is a cycle, so one tour
    gives a lower bound for every square on it, and for its 8 board-symmetric images."""

    def __init__(self, n: int):
        self.n = n
        self.syms = board_symmetries(n)
        self.best = [0] * (n * n)
        self.tour: List[Optional[List[int]]] = [None] * (n * n)

    def add(self, cycle: List[int]):
        n, L = self.n, len(cycle)
        for f in self.syms:
            img = [f(c // n, c % n) for c in cycle]
            img = [r * n + c for r, c in img]
            for i, sq in enumerate(img):
                if L > self.best[sq]:
                    self.best[sq] = L
                    self.tour[sq] = img[i:] + img[:i]  # rotated to start at sq


# =============================================================================
# JSON EXPORTER & CLI
# =============================================================================

def custom_format_json(obj, indent=1) -> str:
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
        filename = f"{piece_name}_closed_tour_{board_size}.json"
    output_data = {piece_name: {str(board_size): results_dict}}
    with open(filename, "w", encoding="utf-8") as f:
        f.write(custom_format_json(output_data, indent=1))
    print(f"\nSuccessfully exported formatted closed tour results to '{filename}'")


def run(selected_piece: str, board_size: int, time_limit: float, workers: int,
        fractions: Tuple[float, float, float, float] = (0.15, 0.45, 0.25, 0.15),
        export: bool = True):
    """`time_limit` is the budget per canonical start square, split over four phases:
      1. seeds: symmetric-tour searches + randomized restarts
      2. local search (LNS) on the best tour through each start
      3. target search: exhaustive search for a tour strictly longer than the best known one;
         if it finishes without finding one, the best known length is proven optimal
      4. enumerate tours tying the best length (for the path list/count)
    After every phase each tour found is shared with all squares on it (and their
    symmetric images), so one good tour lifts the lower bound of many starts at once."""
    n = board_size
    starts = get_canonical_start_squares(n)
    bank = CycleBank(n)
    t1, t2, t3, t4 = (time_limit * f for f in fractions)
    get_graph(selected_piece, n)
    PalisadesSolver(selected_piece, 5, 0.01).solve_from_start((0, 0))  # JIT warm-up

    def show():
        vals = {f"{r},{c}": bank.best[r * n + c] for r, c in starts}
        print(f"  best known: max {max(vals.values())}  per start {vals}")

    with ProcessPoolExecutor(max_workers=workers) as pool:
        print(f"Phase 1: seed tours ({t1:.1f}s per start)...")
        jobs = [(selected_piece, n, t1, s, 4, 1000 * i) for i, s in enumerate(starts)]
        probe_tours = {}
        for start, _, tour, probe in pool.map(_seed_worker, jobs):
            if tour:
                bank.add(tour)
            probe_tours[start] = probe
        show()

        print(f"Phase 2: local search ({t2:.1f}s per start)...")
        # alternate starting points: the best shared tour, or this start's own probe tour
        # (diversity: the best tour is often a symmetric local optimum)
        jobs = [(selected_piece, n, t2, s,
                 (i % 2 and probe_tours[s]) or bank.tour[s[0] * n + s[1]], 7 + i)
                for i, s in enumerate(starts)]
        for _, _, tour in pool.map(_lns_worker, jobs):
            if tour:
                bank.add(tour)
        show()

        print(f"Phase 3: searching for longer tours ({t3:.1f}s per start)...")
        proven = {}
        jobs = [(selected_piece, n, t3, s, bank.best[s[0] * n + s[1]] + 1) for s in starts]
        for r in pool.map(_solve_worker, jobs):
            if r["paths"]:
                bank.add(r["paths"][0])
            proven[r["start_square"]] = not r["timed_out"] and not r["paths"]
        show()

        print(f"\nPhase 4: collecting best tours ({t4:.1f}s per start)")
        print("-" * 75)
        print(f"{'Start Square':<15} | {'Tour Length':<10} | {'Tour Count':<12} | {'Status':<12} | {'Time (s)':<8}")
        print("-" * 75)
        known_starts_data, estimated_starts_data = {}, {}
        overall_max = 0
        total_tours_found = 0
        jobs = [(selected_piece, n, t4, s, bank.best[s[0] * n + s[1]]) for s in starts]
        for result in pool.map(_solve_worker, jobs):
            start_sq = result["start_square"]
            sq = start_sq[0] * n + start_sq[1]
            paths = result["paths"]
            length = result["max_length"]
            if paths:
                bank.add(paths[0])
            if bank.best[sq] > length or not paths:  # fall back to the shared tour
                length = bank.best[sq]
                paths = [bank.tour[sq]] if bank.tour[sq] else []
                result["path_count"] = len(paths)
            # proven optimal if phase 3 or phase 4 ran to completion
            exhausted = not result["timed_out"] or (proven[start_sq] and length == bank.best[sq])

            overall_max = max(overall_max, length)
            total_tours_found += result["path_count"]
            status = "EXHAUSTED" if exhausted else "TIMEOUT"
            if length == 0 and exhausted:
                status = "NO TOUR"
            elif length == n * n:
                status = "HAMILTONIAN"
            print(f"{str(start_sq):<15} | {length:<10} | {result['path_count']:<12} | "
                  f"{status:<12} | {result['elapsed_sec']:<8}")

            sq_entry = {"length": length, "paths": paths}
            target = known_starts_data if exhausted else estimated_starts_data
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
    if export:
        export_results_to_json(selected_piece, n, board_output_section)

    print("-" * 75)
    print(f"Overall Longest Closed Tour for {selected_piece} on {n}x{n}: {overall_max} squares")
    print(f"Total Unique Longest Closed Tour Variations: {total_tours_found}")
    print("=" * 75)
    return overall_max, {s: bank.best[s[0] * n + s[1]] for s in starts}


def main():
    print("=" * 75)
    print("PALISADES — LONGEST CLOSED TOUR SOLVER")
    print("=" * 75)

    print("\nPlayable Pieces:")
    pieces = list(PLAYABLE_PIECES.keys())
    for i, name in enumerate(pieces, 1):
        vec_str = ", ".join([f"({a},{b})" for a, b in PLAYABLE_PIECES[name]])
        print(f"  [{i:2d}] {name:<12} Vectors: {vec_str}")

    piece_idx = int(input(f"Enter Piece Number [1-{len(pieces)}] (default 1 - knight): ") or "1") - 1
    selected_piece = pieces[piece_idx]
    board_size = int(input("Enter Board Size [5-10] (default 5): ") or "5")
    time_limit = float(input("Enter Time Limit per start square in seconds (default 5.0): ") or "5.0")
    workers = int(input(f"Parallel worker processes (default {os.cpu_count() or 4}): ") or str(os.cpu_count() or 4))

    print(f"\nRunning Closed Tour Search for '{selected_piece}' on {board_size}x{board_size} board...")
    run(selected_piece, board_size, time_limit, workers)


if __name__ == "__main__":
    main()