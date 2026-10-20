import random

BOARD_SIZE = 16
KNIGHT_MOVES = [
    (1, 2), (2, 1), (-1, 2), (-2, 1),
    (1, -2), (2, -1), (-1, -2), (-2, -1)
]

def is_valid_square(r, c):
    return 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE

def random_square():
    return random.randint(0, BOARD_SIZE - 1), random.randint(0, BOARD_SIZE - 1)

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

def duel_once(k1_start, k2_start):
    k1_path = [k1_start]
    k2_path = [k2_start]
    k1_visited = {k1_start}
    k2_visited = {k2_start}
    while True:
        made_move = False
        for path, visited, other_path, other_visited in [
            (k1_path, k1_visited, k2_path, k2_visited),
            (k2_path, k2_visited, k1_path, k1_visited)
        ]:
            pos = path[-1]
            all_segs = segments_from_path(k1_path) + segments_from_path(k2_path)
            moves = knight_legal_moves(pos, visited | other_visited, all_segs)
            if moves:
                best_move = max(moves, key=lambda m:
                    len(knight_legal_moves(m, visited | other_visited | {m},
                        all_segs + [(pos[0], pos[1], m[0], m[1])])
                ))
                path.append(best_move)
                visited.add(best_move)
                made_move = True
        if not made_move:
            break
    return len(k1_path), len(k2_path)

def main():
    random.seed(42)
    TRIALS = 10000
    results = []
    for trial in range(TRIALS):
        while True:
            k1_start = random_square()
            k2_start = random_square()
            if k1_start != k2_start:
                break
        k1len, k2len = duel_once(k1_start, k2_start)
        results.append((k1len, k2len))
    # Aggregate stats for number of moves for each knight
    from collections import Counter, defaultdict
    k1_moves_counter = Counter()
    k2_moves_counter = Counter()
    stats = defaultdict(lambda: {"k1_win": 0, "k2_win": 0, "draw": 0, "total": 0})
    k1_total_win = 0
    k2_total_win = 0
    total_draw = 0
    for k1len, k2len in results:
        k1_moves_counter[k1len] += 1
        k2_moves_counter[k2len] += 1
        max_moves = max(k1len, k2len)
        if k1len > k2len:
            stats[max_moves]["k1_win"] += 1
            k1_total_win += 1
        elif k2len > k1len:
            stats[max_moves]["k2_win"] += 1
            k2_total_win += 1
        else:
            stats[max_moves]["draw"] += 1
            total_draw += 1
        stats[max_moves]["total"] += 1
    # Table header
    print("Moves | K1 count | K2 count | K1 Win% | K2 Win% | Draw%")
    print("---------------------------------------------------------")
    all_lengths = sorted(set(list(k1_moves_counter.keys()) + list(k2_moves_counter.keys()) + list(stats.keys())))
    for moves in all_lengths:
        k1c = k1_moves_counter.get(moves, 0)
        k2c = k2_moves_counter.get(moves, 0)
        s = stats[moves]
        denom = s["total"]
        k1_wp = 100.0 * s["k1_win"] / denom if denom else 0.0
        k2_wp = 100.0 * s["k2_win"] / denom if denom else 0.0
        drawp = 100.0 * s["draw"] / denom if denom else 0.0
        print(f"{moves:5} | {k1c:8} | {k2c:8} | {k1_wp:7.2f} | {k2_wp:7.2f} | {drawp:6.2f}")
    print("---------------------------------------------------------")
    print(f"Overall win percentage (out of {TRIALS} trials):")
    print(f"Knight 1 win%: {100.0*k1_total_win/TRIALS:.2f}")
    print(f"Knight 2 win%: {100.0*k2_total_win/TRIALS:.2f}")
    print(f"Draw%:        {100.0*total_draw/TRIALS:.2f}")
    avg_k1 = sum(k1_moves_counter.elements())/TRIALS
    avg_k2 = sum(k2_moves_counter.elements())/TRIALS
    print(f"Average moves:")
    print(f"Knight 1: {avg_k1:.2f}")
    print(f"Knight 2: {avg_k2:.2f}")

if __name__ == "__main__":
    main()