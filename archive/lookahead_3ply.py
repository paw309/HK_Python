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

def heuristic_lookahead3(pos, visited, all_segs):
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
            # For each second move, look for third ply
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
            for m, cnt in zip(moves1, next_counts1):
                if cnt == max_count1:
                    best_move1 = m
                    break
            k1_path.append(best_move1)
            k1_visited.add(best_move1)
            made_move = True
        # Knight 2: lookahead 3-ply
        pos2 = k2_path[-1]
        all_segs = segments_from_path(k1_path) + segments_from_path(k2_path)
        moves2 = knight_legal_moves(pos2, k1_visited | k2_visited, all_segs)
        if moves2:
            best_move2 = heuristic_lookahead3(pos2, k1_visited | k2_visited, all_segs)
            k2_path.append(best_move2)
            k2_visited.add(best_move2)
            made_move = True
        if not made_move:
            break
    return len(k1_path), len(k2_path)

def main():
    random.seed(41)
    TRIALS = 1000
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