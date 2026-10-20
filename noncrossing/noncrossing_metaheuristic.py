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

# --- Heuristics for metaheuristic ---
def heuristic_max_mobility(pos, visited, all_segs, **kwargs):
    moves = knight_legal_moves(pos, visited, all_segs)
    if not moves:
        return None
    next_counts = [len(knight_legal_moves(m, visited | {m}, all_segs + [(pos[0], pos[1], m[0], m[1])])) for m in moves]
    max_count = max(next_counts)
    candidates = [m for m, cnt in zip(moves, next_counts) if cnt == max_count]
    return random.choice(candidates)

def heuristic_warnsdorff(pos, visited, all_segs, **kwargs):
    moves = knight_legal_moves(pos, visited, all_segs)
    if not moves:
        return None
    next_counts = [len(knight_legal_moves(m, visited | {m}, all_segs + [(pos[0], pos[1], m[0], m[1])])) for m in moves]
    min_count = min(next_counts)
    candidates = [m for m, cnt in zip(moves, next_counts) if cnt == min_count]
    return random.choice(candidates)

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
    candidates = [m for m, cnt in zip(moves, opp_next_counts) if cnt == min_opp_count]
    return random.choice(candidates)

def heuristic_center_control(pos, visited, all_segs, **kwargs):
    moves = knight_legal_moves(pos, visited, all_segs)
    if not moves:
        return None
    center = (3.5, 3.5)
    dists = [-(abs(m[0] - center[0]) + abs(m[1] - center[1])) for m in moves]
    max_dist = max(dists)
    candidates = [m for m, d in zip(moves, dists) if d == max_dist]
    return random.choice(candidates)

def heuristic_edge_avoidance(pos, visited, all_segs, **kwargs):
    moves = knight_legal_moves(pos, visited, all_segs)
    if not moves:
        return None
    edge_penalties = [min(m[0], BOARD_SIZE-1-m[0], m[1], BOARD_SIZE-1-m[1]) for m in moves]
    max_penalty = max(edge_penalties)
    candidates = [m for m, p in zip(moves, edge_penalties) if p == max_penalty]
    return random.choice(candidates)

def heuristic_lookahead3(pos, visited, all_segs, **kwargs):
    moves = knight_legal_moves(pos, visited, all_segs)
    if not moves:
        return None
    best_move = moves[0]
    best_score = -1
    for m1 in moves:
        v1 = visited | {m1}
        s1 = all_segs + [(pos[0], pos[1], m1[0], m1[1])]
        moves2 = knight_legal_moves(m1, v1, s1)
        if not moves2:
            score = 0
        else:
            min_third_ply = float('inf')
            for m2 in moves2:
                v2 = v1 | {m2}
                s2 = s1 + [(m1[0], m1[1], m2[0], m2[1])]
                moves3 = knight_legal_moves(m2, v2, s2)
                third_ply_score = len(moves3)
                if third_ply_score < min_third_ply:
                    min_third_ply = third_ply_score
            score = min_third_ply
        if score > best_score:
            best_score = score
            best_move = m1
    return best_move

def heuristic_mirror(pos, visited, all_segs, opp_pos=None, **kwargs):
    moves = knight_legal_moves(pos, visited, all_segs)
    if not moves:
        return None
    center = (3.5, 3.5)
    opp_offset = (opp_pos[0] - center[0], opp_pos[1] - center[1])
    mirror_pos = (int(center[0] - opp_offset[0]), int(center[1] - opp_offset[1]))
    if mirror_pos in moves:
        return mirror_pos
    return heuristic_max_mobility(pos, visited, all_segs)

def heuristic_random(pos, visited, all_segs, **kwargs):
    moves = knight_legal_moves(pos, visited, all_segs)
    if not moves:
        return None
    return random.choice(moves)

# --- Metaheuristic ---
def metaheuristic(pos, visited, all_segs, opp_pos, opp_visited):
    moves = knight_legal_moves(pos, visited, all_segs)
    if not moves:
        return None

    # Run all heuristics, collect unique candidate moves
    heuristics = [
        heuristic_max_mobility,
        heuristic_warnsdorff,
        heuristic_blocking,
        heuristic_center_control,
        heuristic_edge_avoidance,
        heuristic_lookahead3,
        heuristic_mirror,
        heuristic_random,
    ]
    candidate_moves = set()
    for heuristic in heuristics:
        move = heuristic(pos, visited, all_segs, opp_pos=opp_pos, opp_visited=opp_visited)
        if move is not None and move in moves:
            candidate_moves.add(move)

    # Score each candidate move based on combination of features
    scored_moves = []
    for move in candidate_moves:
        # Mobility
        own_future = len(knight_legal_moves(move, visited | {move}, all_segs + [(pos[0], pos[1], move[0], move[1])]))
        # Opponent restriction
        opp_future = len(knight_legal_moves(opp_pos, opp_visited | visited | {move}, all_segs + [(pos[0], pos[1], move[0], move[1])]))
        # Center control
        center_score = -abs(move[0]-3.5) - abs(move[1]-3.5)
        # Edge avoidance
        edge_score = min(move[0], BOARD_SIZE-1-move[0], move[1], BOARD_SIZE-1-move[1])
        # Path parity (prefer moves that keep parity with Knight 1)
        parity_score = 1 if (move[0]+move[1])%2 == (opp_pos[0]+opp_pos[1])%2 else 0
        # Combine weights (tuneable)
        score = (
            2.0*own_future
            - 1.0*opp_future
            + 0.5*center_score
            + 0.5*edge_score
            + 0.25*parity_score
        )
        scored_moves.append((score, move))

    scored_moves.sort(reverse=True)
    # Choose the move with the highest score; if tie, pick randomly among best
    max_score = scored_moves[0][0]
    best_moves = [move for score, move in scored_moves if score == max_score]
    return random.choice(best_moves)

def duel_once(k1_start, k2_start):
    k1_path = [k1_start]
    k2_path = [k2_start]
    k1_visited = set([k1_start])
    k2_visited = set([k2_start])
    while True:
        made_move = False
        # Knight 1: max-mobility
        pos1 = k1_path[-1]
        all_segs = segments_from_path(k1_path) + segments_from_path(k2_path)
        moves1 = knight_legal_moves(pos1, k1_visited | k2_visited, all_segs)
        if moves1:
            next_counts1 = [len(knight_legal_moves(m, k1_visited | k2_visited | {m}, all_segs + [(pos1[0], pos1[1], m[0], m[1])])) for m in moves1]
            max_count1 = max(next_counts1)
            candidates1 = [m for m, cnt in zip(moves1, next_counts1) if cnt == max_count1]
            best_move1 = random.choice(candidates1)
            k1_path.append(best_move1)
            k1_visited.add(best_move1)
            made_move = True
        # Knight 2: metaheuristic
        pos2 = k2_path[-1]
        all_segs = segments_from_path(k1_path) + segments_from_path(k2_path)
        moves2 = knight_legal_moves(pos2, k1_visited | k2_visited, all_segs)
        if moves2:
            best_move2 = metaheuristic(pos2, k1_visited | k2_visited, all_segs, opp_pos=k1_path[-1], opp_visited=k1_visited)
            k2_path.append(best_move2)
            k2_visited.add(best_move2)
            made_move = True
        if not made_move:
            break
    return len(k1_path), len(k2_path)

def main():
    random.seed(32)
    TRIALS = 10000
    results_k1 = []
    results_k2 = []
    for trial in range(TRIALS):
        while True:
            k1_start = random_square()
            k2_start = random_square()
            if k1_start != k2_start:
                break
        k1len, k2len = duel_once(k1_start, k2_start)
        results_k1.append(k1len)
        results_k2.append(k2len)
    from collections import Counter
    hist_k1 = Counter(results_k1)
    hist_k2 = Counter(results_k2)
    all_lengths = sorted(set(hist_k1.keys()) | set(hist_k2.keys()))
    print("Moves | Knight 1 | Knight 2")
    print("----------------------------")
    for moves in all_lengths:
        print(f"{moves:5} | {hist_k1.get(moves,0):8} | {hist_k2.get(moves,0):8}")
    avg_k1 = sum(results_k1)/TRIALS
    avg_k2 = sum(results_k2)/TRIALS
    win_k1 = sum(1 for k1, k2 in zip(results_k1, results_k2) if k1 > k2)
    win_k2 = sum(1 for k1, k2 in zip(results_k1, results_k2) if k2 > k1)
    draws = TRIALS - win_k1 - win_k2
    print("----------------------------")
    print(f"Average moves:")
    print(f"Knight 1: {avg_k1:.2f}")
    print(f"Knight 2: {avg_k2:.2f}")
    print("----------------------------")
    print(f"Win percentage (out of {TRIALS} trials):")
    print(f"Knight 1 win%: {100.0*win_k1/TRIALS:.2f}")
    print(f"Knight 2 win%: {100.0*win_k2/TRIALS:.2f}")
    print(f"Draw%:        {100.0*draws/TRIALS:.2f}")

if __name__ == "__main__":
    main()