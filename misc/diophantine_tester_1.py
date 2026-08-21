from itertools import combinations, permutations

# -----------------------------------------
# CONFIGURATION
# -----------------------------------------
MAX_N = 30
LEAPERS = list(range(1, 8))   # (0,1) through (0,7)

# -----------------------------------------
# simulate a cycle of leapers
# -----------------------------------------
def simulate_cycle(leaper_cycle, max_n=MAX_N):
    """
    leaper_cycle: tuple of step sizes (e.g., (2,5) means +2, -5, +2, -5, ...)
    Returns:
        (halt_step, path) if halts before max_n
        None if no repeat within max_n
    """
    visited = {0}
    path = [0]
    pos = 0
    k = len(leaper_cycle)

    for n in range(1, max_n + 1):
        step = leaper_cycle[(n - 1) % k]
        # alternate right/left: odd steps right, even steps left
        if n % 2 == 1:
            pos += step
        else:
            pos -= step

        if pos in visited:
            return (n, path + [pos])
        visited.add(pos)
        path.append(pos)

    return None


# -----------------------------------------
# MAIN SEARCH
# -----------------------------------------
def main():
    print("Testing all 2-, 3-, and 4-leaper cycles...\n")

    for r in [2, 3, 4]:
        print(f"--- Testing {r}-leaper cycles ---")
        for combo in combinations(LEAPERS, r):
            for cycle in permutations(combo):
                result = simulate_cycle(cycle)
                if result is not None:
                    halt_step, path = result
                    print(f"HALT at step {halt_step:2d} | cycle={cycle} | path={path}")

        print()

if __name__ == "__main__":
    main()
