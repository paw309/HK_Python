import random

BOARD_SIZE = 8
TRIALS = 5000

# Define symmetry σ mapping (e.g., vertical reflection)
def sigma(pos):
    r, c = pos
    return (r, 9 - c)

class Game:
    def __init__(self, blockade_seq):
        self.visited = set()
        self.p1_pos = blockade_seq[0]
        self.p2_pos = sigma(self.p1_pos)
        self.blockade_seq = blockade_seq
        self.turn = 0

    def step(self):
        # P1 move
        if self.turn < len(self.blockade_seq):
            new_p1 = self.blockade_seq[self.turn]
        else:
            new_p1 = random.choice(self.legal_knight_moves(self.p1_pos))
        self.visited.add(new_p1)
        self.p1_pos = new_p1

        # P2 mirror or pass
        mirror_target = sigma(self.p1_pos)
        if mirror_target in self.visited or mirror_target not in self.legal_knight_moves(self.p2_pos):
            return self.turn  # mirror broken
        self.visited.add(mirror_target)
        self.p2_pos = mirror_target

        self.turn += 1
        return None

    def legal_knight_moves(self, pos):
        r, c = pos
        deltas = [(2,1),(2,-1),(-2,1),(-2,-1),(1,2),(1,-2),(-1,2),(-1,-2)]
        moves = []
        for dr, dc in deltas:
            nr, nc = r + dr, c + dc
            if 1 <= nr <= BOARD_SIZE and 1 <= nc <= BOARD_SIZE and (nr, nc) not in self.visited:
                moves.append((nr, nc))
        return moves

def run_simulation(blockade_seq):
    failures = []
    for _ in range(TRIALS):
        game = Game(blockade_seq)
        while True:
            result = game.step()
            if result is not None:
                failures.append(result)
                break
    return sum(failures) / len(failures)

# Example blockade sequences (must be defined as lists of coords)
bridge_block_seq       = [(4,4),(5,6),(6,4)]  # fill in
parity_flip_loop_seq   = [(3,3),(5,4),(4,6),(6,5)]
corridor_cutting_seq   = [(2,3),(4,4),(6,3),(8,4)]
sacrificial_choke_seq  = [(4,5),(5,7),(3,6),(2,4)]

results = {
    "Bridge-Block": run_simulation(bridge_block_seq),
    "Parity-Flip Loop": run_simulation(parity_flip_loop_seq),
    "Corridor-Cutting": run_simulation(corridor_cutting_seq),
    "Sacrificial Chokepoint": run_simulation(sacrificial_choke_seq),
}

print(results)