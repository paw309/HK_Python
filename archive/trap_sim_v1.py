import random
import math
from collections import defaultdict

# --- Configuration ---
TIE_STRATEGY = 'min_degree'
NUM_SIMULATIONS = 10000

# --- Build Knight Graph ---
def build_knight_adjacency(n=8):
    deltas = [(2,1),(1,2),(-1,2),(-2,1),(-2,-1),(-1,-2),(1,-2),(2,-1)]
    adj = {}
    for r in range(n):
        for c in range(n):
            nbrs = {
                (r+dr, c+dc)
                for dr, dc in deltas
                if 0 <= r+dr < n and 0 <= c+dc < n
            }
            adj[(r, c)] = nbrs
    return adj

# --- Warnsdorff Candidate Generator ---
def get_warnsdorff_moves(pos, visited, adj):
    candidates = []
    for nbr in adj[pos]:
        if nbr in visited:
            continue
        deg = sum(1 for nn in adj[nbr] if nn not in visited)
        candidates.append((deg, nbr))
    if not candidates:
        return []
    min_deg = min(deg for deg, _ in candidates)
    return [nbr for deg, nbr in candidates if deg == min_deg]

# --- Tie‐Breaker State and Helpers ---
freq_counter = defaultdict(int)

def build_weight_map(adj):
    weight = {}
    center = ( (7)/2, (7)/2 )
    for sq in adj:
        d = math.hypot(sq[0] - center[0], sq[1] - center[1])
        weight[sq] = 1.0 / (d + 1.0)
    return weight

WEIGHT_MAP = None

def tiebreak_random(cands, visited, adj):
    return random.choice(cands)

def tiebreak_min_degree(cands, visited, adj):
    deg2 = {}
    for s in cands:
        vis2 = visited | {s}
        nbrs = [n for n in adj[s] if n not in vis2]
        if not nbrs:
            deg2[s] = 0
        else:
            deg2[s] = min(
                sum(1 for nn in adj[n] if nn not in vis2)
                for n in nbrs
            )
    best = [s for s, d in deg2.items() if d == min(deg2.values())]
    return random.choice(best)

def tiebreak_max_degree(cands, visited, adj):
    deg2 = {}
    for s in cands:
        vis2 = visited | {s}
        nbrs = [n for n in adj[s] if n not in vis2]
        if not nbrs:
            deg2[s] = 0
        else:
            deg2[s] = max(
                sum(1 for nn in adj[n] if nn not in vis2)
                for n in nbrs
            )
    best = [s for s, d in deg2.items() if d == max(deg2.values())]
    return random.choice(best)

def tiebreak_center(cands, visited, adj):
    dmap = {
        s: max(abs(s[0] - 3.5), abs(s[1] - 3.5))
        for s in cands
    }
    best = [s for s, d in dmap.items() if d == min(dmap.values())]
    return random.choice(best)

def tiebreak_edge(cands, visited, adj):
    dmap = {
        s: max(abs(s[0] - 3.5), abs(s[1] - 3.5))
        for s in cands
    }
    best = [s for s, d in dmap.items() if d == max(dmap.values())]
    return random.choice(best)

def tiebreak_lex(cands, visited, adj):
    return sorted(cands)[0]

def tiebreak_freq(cands, visited, adj):
    freqs = {s: freq_counter[s] for s in cands}
    best = [s for s, f in freqs.items() if f == min(freqs.values())]
    choice = random.choice(best)
    freq_counter[choice] += 1
    return choice

def tiebreak_weighted(cands, visited, adj):
    global WEIGHT_MAP
    if WEIGHT_MAP is None:
        WEIGHT_MAP = build_weight_map(adj)
    weights = [WEIGHT_MAP[s] for s in cands]
    return random.choices(cands, weights=weights, k=1)[0]

TIE_FUNCS = {
    'random': tiebreak_random,
    'min_degree': tiebreak_min_degree,
    'max_degree': tiebreak_max_degree,
    'center': tiebreak_center,
    'edge': tiebreak_edge,
    'lex': tiebreak_lex,
    'freq': tiebreak_freq,
    'weighted': tiebreak_weighted
}

def select_warnsdorff(pos, visited, adj):
    cands = get_warnsdorff_moves(pos, visited, adj)
    if not cands:
        return None
    if len(cands) == 1:
        return cands[0]
    return TIE_FUNCS[TIE_STRATEGY](cands, visited, adj)

def choose_3ply(pos, opp_pos, visited, adj):
    S1 = get_warnsdorff_moves(pos, visited, adj)
    if not S1:
        return None

    best_score = -1
    best_moves = []

    for s1 in S1:
        vis1 = visited | {s1}
        s2 = select_warnsdorff(opp_pos, vis1, adj)
        vis2 = vis1 | {s2} if s2 else vis1
        s3 = select_warnsdorff(s1, vis2, adj)
        if s3:
            deg3 = sum(1 for n in adj[s3] if n not in vis2)
        else:
            deg3 = 0

        if deg3 > best_score:
            best_score = deg3
            best_moves = [s1]
        elif deg3 == best_score:
            best_moves.append(s1)

    if len(best_moves) == 1:
        return best_moves[0]
    return TIE_FUNCS[TIE_STRATEGY](best_moves, visited, adj)

def simulate_two_knights(adj, start1, start2):
    visited = {start1, start2}
    seq1, seq2 = [start1], [start2]
    turn, stuck1, stuck2 = 1, False, False

    while True:
        if turn == 1:
            mv = choose_3ply(seq1[-1], seq2[-1], visited, adj)
            if mv:
                seq1.append(mv)
                visited.add(mv)
                stuck1 = False
            else:
                stuck1 = True
            turn = 2
        else:
            mv = choose_3ply(seq2[-1], seq1[-1], visited, adj)
            if mv:
                seq2.append(mv)
                visited.add(mv)
                stuck2 = False
            else:
                stuck2 = True
            turn = 1

        if stuck1 and stuck2:
            break

    return seq1, seq2

def determine_result(seq1, seq2):
    # Win: knight covers more squares
    # Loss: opposite
    # Draw: same number
    n1 = len(seq1) - 1
    n2 = len(seq2) - 1
    if n1 > n2:
        return 'win', 'loss'
    elif n1 < n2:
        return 'loss', 'win'
    else:
        return 'draw', 'draw'

def update_stats(stats, result, moves):
    stats[result]['count'] += 1
    stats[result]['moves'] += moves

def print_results_table(stats1, stats2):
    print("\nResults over {} simulations:".format(NUM_SIMULATIONS))
    print("{:<7} {:<10} {:<14} {:<10} {:<14}".format(
        "", "Rate", "Avg Moves/Result", "Rate", "Avg Moves/Result"))
    print("{:<7} {:<10} {:<14} {:<10} {:<14}".format(
        "Result", "K1", "K1", "K2", "K2"))
    print("-" * 60)
    for res in ['win', 'loss', 'draw']:
        r1 = stats1[res]['count'] / NUM_SIMULATIONS
        r2 = stats2[res]['count'] / NUM_SIMULATIONS
        m1 = (stats1[res]['moves'] / stats1[res]['count']) if stats1[res]['count'] else 0
        m2 = (stats2[res]['moves'] / stats2[res]['count']) if stats2[res]['count'] else 0
        print("{:<7} {:<10.3f} {:<14.2f} {:<10.3f} {:<14.2f}".format(
            res.capitalize(), r1, m1, r2, m2))

if __name__ == "__main__":
    random.seed()
    adjacency = build_knight_adjacency(8)
    squares = list(adjacency.keys())

    stats1 = {'win': {'count': 0, 'moves': 0},
              'loss': {'count': 0, 'moves': 0},
              'draw': {'count': 0, 'moves': 0}}
    stats2 = {'win': {'count': 0, 'moves': 0},
              'loss': {'count': 0, 'moves': 0},
              'draw': {'count': 0, 'moves': 0}}

    for _ in range(NUM_SIMULATIONS):
        # Reset tiebreak freq
        freq_counter.clear()
        WEIGHT_MAP = None
        # Random distinct starts
        start1 = random.choice(squares)
        start2 = random.choice([s for s in squares if s != start1])
        seq1, seq2 = simulate_two_knights(adjacency, start1, start2)
        res1, res2 = determine_result(seq1, seq2)
        update_stats(stats1, res1, len(seq1)-1)
        update_stats(stats2, res2, len(seq2)-1)

    print_results_table(stats1, stats2)