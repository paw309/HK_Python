import random

BOARD_SIZE = 8
KNIGHT_MOVES = [
    (1, 2), (2, 1), (-1, 2), (-2, 1),
    (1, -2), (2, -1), (-1, -2), (-2, -1)
]

def is_valid_square(r, c):
    return 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE

def random_square():
    return (random.randint(0, BOARD_SIZE-1), random.randint(0, BOARD_SIZE-1))

def segments_from_path(path):
    return [(path[i][0], path[i][1], path[i+1][0], path[i+1][1])
            for i in range(len(path)-1)]

def segments_cross(seg1, seg2):
    def ccw(A,B,C):
        return (C[1]-A[1])*(B[0]-A[0]) > (B[1]-A[1])*(C[0]-A[0])
    A, B = (seg1[0],seg1[1]), (seg1[2],seg1[3])
    C, D = (seg2[0],seg2[1]), (seg2[2],seg2[3])
    if A == C or A == D or B == C or B == D:
        return False
    return (ccw(A,C,D) != ccw(B,C,D)) and (ccw(A,B,C) != ccw(A,B,D))

def crosses_any(new_seg, all_segs):
    for seg in all_segs:
        if segments_cross(new_seg, seg):
            return True
    return False

def knight_legal_moves(pos, visited, all_segs):
    moves = []
    for dr, dc in KNIGHT_MOVES:
        nr, nc = pos[0]+dr, pos[1]+dc
        if not is_valid_square(nr, nc):
            continue
        if (nr, nc) in visited:
            continue
        new_seg = (pos[0], pos[1], nr, nc)
        if crosses_any(new_seg, all_segs):
            continue
        moves.append((nr, nc))
    return moves

# Heuristic functions for Knight 2
def heuristic_max_mobility(pos, visited, all_segs, **kwargs):
    moves = knight_legal_moves(pos, visited, all_segs)
    if not moves:
        return None
    next_counts = [len(knight_legal_moves(m, visited | {m}, all_segs + [(pos[0], pos[1], m[0], m[1])])) for m in moves]
    max_count = max(next_counts)
    for m, cnt in zip(moves, next_counts):
        if cnt == max_count:
            return m
    return moves[0]

def heuristic_warnsdorff(pos, visited, all_segs, **kwargs):
    moves = knight_legal_moves(pos, visited, all_segs)
    if not moves:
        return None
    next_counts = [len(knight_legal_moves(m, visited | {m}, all_segs + [(pos[0], pos[1], m[0], m[1])])) for m in moves]
    min_count = min(next_counts)
    for m, cnt in zip(moves, next_counts):
        if cnt == min_count:
            return m
    return moves[0]

def heuristic_blocking(pos, visited, all_segs, opp_pos=None, opp_visited=None, **kwargs):
    moves = knight_legal_moves(pos, visited, all_segs)
    if not moves:
        return None
    opp_next_counts = []
    for m in moves:
        new_visited = visited | {m}
        new_segs = all_segs + [(pos[0], pos[1], m[0], m[1])]
        opp_moves = knight_legal_moves(opp_pos, opp_visited | new_visited, new_segs)
        opp_next_counts.append(len(opp_moves))
    min_opp_count = min(opp_next_counts)
    for m, cnt in zip(moves, opp_next_counts):
        if cnt == min_opp_count:
            return m
    return moves[0]

def heuristic_random(pos, visited, all_segs, **kwargs):
    moves = knight_legal_moves(pos, visited, all_segs)
    if not moves:
        return None
    return random.choice(moves)

def heuristic_center_control(pos, visited, all_segs, **kwargs):
    # Prefer moves closer to the board center (3.5, 3.5)
    moves = knight_legal_moves(pos, visited, all_segs)
    if not moves:
        return None
    center = (3.5, 3.5)
    dists = [-(abs(m[0] - center[0]) + abs(m[1] - center[1])) for m in moves]
    max_dist = max(dists)
    for m, d in zip(moves, dists):
        if d == max_dist:
            return m
    return moves[0]

def heuristic_edge_avoidance(pos, visited, all_segs, **kwargs):
    # Avoid edges: penalize moves close to the board sides
    moves = knight_legal_moves(pos, visited, all_segs)
    if not moves:
        return None
    edge_penalties = [min(m[0], BOARD_SIZE-1-m[0], m[1], BOARD_SIZE-1-m[1]) for m in moves]
    max_penalty = max(edge_penalties)
    for m, p in zip(moves, edge_penalties):
        if p == max_penalty:
            return m
    return moves[0]

def heuristic_lookahead2(pos, visited, all_segs, **kwargs):
    moves = knight_legal_moves(pos, visited, all_segs)
    if not moves:
        return None
    # For each move, look ahead 2 turns: pick move maximizing min of possible second moves
    best_move = moves[0]
    best_score = -1
    for m in moves:
        new_visited = visited | {m}
        new_segs = all_segs + [(pos[0], pos[1], m[0], m[1])]
        next_moves = knight_legal_moves(m, new_visited, new_segs)
        if not next_moves:
            score = 0
        else:
            # For each next-move, how many onward moves?
            next_scores = [len(knight_legal_moves(nm, new_visited | {nm}, new_segs + [(m[0], m[1], nm[0], nm[1])])) for nm in next_moves]
            score = min(next_scores)
        if score > best_score:
            best_score = score
            best_move = m
    return best_move

def heuristic_mirror(pos, visited, all_segs, opp_pos=None, **kwargs):
    # Try to mirror Knight 1's move if possible (if symmetric square is available)
    moves = knight_legal_moves(pos, visited, all_segs)
    if not moves:
        return None
    # Calculate knight 1's offset from board center, try to copy that offset
    center = (3.5, 3.5)
    opp_offset = (opp_pos[0] - center[0], opp_pos[1] - center[1])
    mirror_pos = (int(center[0] - opp_offset[0]), int(center[1] - opp_offset[1]))
    if mirror_pos in moves:
        return mirror_pos
    # If not possible, just use max-mobility
    return heuristic_max_mobility(pos, visited, all_segs)

def duel_once(k1_start, k2_start, k2_heuristic_func):
    k1_path = [k1_start]
    k2_path = [k2_start]
    k1_visited = set([k1_start])
    k2_visited = set([k2_start])
    while True:
        made_move = False
        # K1 always uses max-mobility
        pos = k1_path[-1]
        all_segs = segments_from_path(k1_path) + segments_from_path(k2_path)
        moves = knight_legal_moves(pos, k1_visited | k2_visited, all_segs)
        if moves:
            next_counts = [len(knight_legal_moves(m, k1_visited | k2_visited | {m}, all_segs + [(pos[0], pos[1], m[0], m[1])])) for m in moves]
            max_count = max(next_counts)
            for m, cnt in zip(moves, next_counts):
                if cnt == max_count:
                    best_move = m
                    break
            k1_path.append(best_move)
            k1_visited.add(best_move)
            made_move = True
        # K2 uses variable heuristic
        pos2 = k2_path[-1]
        all_segs = segments_from_path(k1_path) + segments_from_path(k2_path)
        moves2 = knight_legal_moves(pos2, k1_visited | k2_visited, all_segs)
        if moves2:
            params = {"opp_pos": k1_path[-1], "opp_visited": k1_visited}
            best_move2 = k2_heuristic_func(pos2, k1_visited | k2_visited, all_segs, **params)
            k2_path.append(best_move2)
            k2_visited.add(best_move2)
            made_move = True
        if not made_move:
            break
    return len(k1_path), len(k2_path)

def run_experiment(trials=100):
    heuristics = [
        ("Max-mobility", heuristic_max_mobility),
        ("Warnsdorff (Min-mobility)", heuristic_warnsdorff),
        ("Blocking", heuristic_blocking),
        ("Random", heuristic_random),
        ("Center Control", heuristic_center_control),
        ("Edge Avoidance", heuristic_edge_avoidance),
        ("Lookahead 2-ply", heuristic_lookahead2),
        ("Mirror", heuristic_mirror),
    ]
    results = {}
    random.seed(42)
    for display, func in heuristics:
        k1_counts = []
        k2_counts = []
        win_k1 = 0
        win_k2 = 0
        draws = 0
        for trial in range(trials):
            while True:
                k1_start = random_square()
                k2_start = random_square()
                if k1_start != k2_start:
                    break
            k1len, k2len = duel_once(k1_start, k2_start, k2_heuristic_func=func)
            k1_counts.append(k1len)
            k2_counts.append(k2len)
            if k1len > k2len:
                win_k1 += 1
            elif k2len > k1len:
                win_k2 += 1
            else:
                draws += 1
        results[display] = {
            "k1_counts": k1_counts,
            "k2_counts": k2_counts,
            "win_k1": win_k1,
            "win_k2": win_k2,
            "draws": draws,
            "avg_k1": sum(k1_counts)/trials,
            "avg_k2": sum(k2_counts)/trials,
        }
    # Print table
    print("\nKnight 1 always uses Max-mobility heuristic.\n")
    print("Heuristic               | K1 Avg | K2 Avg | K1 Win% | K2 Win% | Draw%")
    print("-----------------------------------------------------------------------")
    for display, _ in heuristics:
        r = results[display]
        print(f"{display:<22} | {r['avg_k1']:6.2f} | {r['avg_k2']:6.2f} | {r['win_k1']/trials*100:7.2f} | {r['win_k2']/trials*100:7.2f} | {r['draws']/trials*100:6.2f}")
    print("\nDistribution of move counts (number of times each length was reached):")
    print("\nHeuristic               | Moves | K1 Count | K2 Count")
    print("------------------------------------------------------")
    from collections import Counter
    for display, _ in heuristics:
        r = results[display]
        all_lengths = sorted(set(r['k1_counts'] + r['k2_counts']))
        k1_count = Counter(r['k1_counts'])
        k2_count = Counter(r['k2_counts'])
        for moves in all_lengths:
            print(f"{display:<22} | {moves:5} | {k1_count.get(moves,0):8} | {k2_count.get(moves,0):8}")
        print("------------------------------------------------------")
    print("\nDone.")

if __name__ == "__main__":
    run_experiment(trials=1000)