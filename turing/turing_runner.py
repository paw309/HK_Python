"""
turing_runner.py

CLI runner for the Turing Machine with Chess Pieces simulation.

Prompts the user for four parameters, then exhaustively tests every ordered
permutation of pieces drawn from PIECE_POOL (P(pool,k) permutations for k
pieces).  For each permutation, ATTEMPTS_PER_COMBO simulations are run.
A path qualifies only when it reaches the target length **and** the current
piece has no legal moves remaining (genuine halt, not just the step-limit
being hit).

The target length is computed automatically as board_size² - 1.

Two output-file formats are available:
  1 – JSON file containing every permutation that produced ≥ 1 exact path
      (with full path data).
  2 – CSV file listing every permutation (including zero-path ones) with
      columns: #, Pieces, Exact paths.

Usage:
    python turing_runner.py
"""

import itertools
import json
import math
import os
import random
import sys
from datetime import datetime
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyversion.knightsturing import (
    PIECE_POOL,
    RuleSet,
    build_ruleset1,
    build_ruleset2,
    simulate_once,
    build_ruleset6,
)
from piecekeeper import get_move_func

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ATTEMPTS_PER_COMBO = 100000   # Simulation attempts per piece combination

# ---------------------------------------------------------------------------
# User input helpers
# ---------------------------------------------------------------------------

def _prompt_range(prompt: str, lo: int, hi: int) -> int:
    """Prompt until the user enters an integer in [lo, hi]."""
    while True:
        try:
            val = int(input(f"{prompt} ({lo}-{hi}): ").strip())
            if lo <= val <= hi:
                return val
        except (ValueError, EOFError):
            pass
        print(f"  Please enter an integer between {lo} and {hi}.")


def _prompt_choice(prompt: str, choices: List[int]) -> int:
    """Prompt until the user enters one of the given choices."""
    choices_str = "/".join(str(c) for c in choices)
    while True:
        try:
            val = int(input(f"{prompt} ({choices_str}): ").strip())
            if val in choices:
                return val
        except (ValueError, EOFError):
            pass
        print(f"  Please enter one of: {choices_str}")


def get_user_inputs() -> Tuple[int, int, int, int, int]:
    """Collect the run parameters from stdin.

    Returns:
        board_size, num_pieces, rule_set_id, output_file_choice, target_length
        (target_length is derived automatically as board_size² - 1)
    """
    print("=" * 60)
    print("  Turing Machine with Chess Pieces")
    print("=" * 60)
    print()
    board_size         = _prompt_range("Board size",       5,  8)
    target_length      = board_size * board_size - 1
    print(f"  Target length set to {target_length} ({board_size}×{board_size} - 1)")
    num_pieces         = _prompt_choice("Number of pieces", [2, 3, 4])
    rule_set_id        = _prompt_choice("Rule set",         [1, 2, 3, 6])
    output_file_choice = _prompt_choice(
        "Output file format  [1=JSON with paths, 2=CSV summary]", [1, 2]
    )
    return board_size, num_pieces, rule_set_id, output_file_choice, target_length


# ---------------------------------------------------------------------------
# Per-combination logic
# ---------------------------------------------------------------------------

def _collect_exact_paths(
    pieces: List[str],
    board_size: int,
    target_length: int,
    rule_set_id: int,
    attempts: int,
) -> Tuple[RuleSet, int, List[List[Tuple[int, int]]]]:
    """Run *attempts* simulations for *pieces* and collect exact-length paths.

    A path is counted only when it both reaches *target_length* **and** halts
    there with no legal moves remaining for the current piece (genuine halt).
    Paths that reach the length while still having legal moves are discarded.

    Returns:
        ruleset     – the RuleSet object used
        exact_count – number of attempts that genuinely halted at *target_length*
        paths       – list of (x, y) coordinate sequences for each such path
                      (x = column, y = row)
    """
    if rule_set_id == 1:
        ruleset = build_ruleset1(pieces)
    elif rule_set_id == 2:
        ruleset = build_ruleset2(pieces)
    elif rule_set_id == 6:
        ruleset = build_ruleset6(pieces)
    else:
        raise ValueError(f"Unknown rule set id: {rule_set_id}")

    max_steps = board_size * board_size
    exact_count = 0
    paths: List[List[Tuple[int, int]]] = []

    for attempt in range(attempts):
        start_r     = random.randint(0, board_size - 1)
        start_c     = random.randint(0, board_size - 1)
        start_piece = pieces[0]

        # Alternate: even attempts → random walk, odd → Warnsdorff's heuristic
        use_w = (attempt % 2 == 1)

        path_len, path = simulate_once(
            board_size, (start_r, start_c), start_piece,
            ruleset, max_steps=max_steps, use_warnsdorff=use_w,
        )

        if path_len == target_length:
            # Only count paths that genuinely halted: the next piece must have
            # no legal moves remaining (not merely stopped by max_steps).
            final_row, final_col, final_piece = path[-1]
            visited_set = {(r, c) for r, c, _ in path}
            still_has_moves = any(
                m not in visited_set
                for m in get_move_func(final_piece)(final_row, final_col, board_size)
            )
            if still_has_moves:
                continue
            exact_count += 1
            # Convert (row, col, piece) → (x, y) = (col, row)
            paths.append([(col, row) for row, col, _piece in path])

    return ruleset, exact_count, paths


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_tests(
    board_size: int,
    num_pieces: int,
    target_length: int,
    rule_set_id: int,
    output_file_choice: int,
) -> None:
    """Test every P(pool, num_pieces) piece permutation and record exact-path counts."""
    results: List[Dict[str, Any]] = []
    csv_rows: List[Tuple[int, List[str], int]] = []
    if rule_set_id == 6:
        # Piece groups for Rule 6
        piece1_group = ["wazir", "threeleaper"]
        piece2_group = ["knight", "camel", "zebra", "giraffe"]
        piece3_group = ["king"]
        if num_pieces != 3:
            print("Rule set 6 only supports exactly 3 pieces (1 from each of 3 groups).")
            return
        perms = []
        for p1 in piece1_group:
            for p2 in piece2_group:
                for p3 in piece3_group:
                    perms.append([p1, p2, p3])
        total_perms = len(perms)
        idx_start = 1
        print()
        print(f"Piece pools : 1={piece1_group}, 2={piece2_group}, 3={piece3_group}  →  {total_perms} permutations")
        print(f"Board      : {board_size}×{board_size}  |  target length: {target_length}  |  rule set: {rule_set_id}")
        print(f"Attempts   : {ATTEMPTS_PER_COMBO} per permutation")
        print("-" * 80)
        print(f"{'#':>5}  {'Pieces':<60}  {'Exact paths':>11}")
        print("-" * 80)
        for idx, pieces_list in enumerate(perms, start=idx_start):
            ruleset, exact_count, paths = _collect_exact_paths(
                pieces_list, board_size, target_length, rule_set_id, ATTEMPTS_PER_COMBO
            )
            csv_rows.append((idx, pieces_list, exact_count))

            if exact_count == 0:
                continue

            pieces_str = " → ".join(pieces_list)
            print(f"{idx:5d}  {pieces_str:<60}  {exact_count:>11d}")

            results.append({
                "perm_num":      idx,
                "board_size":    board_size,
                "pieces":        pieces_list,
                "target_length": target_length,
                "exact_paths":   exact_count,
                "attempts":      ATTEMPTS_PER_COMBO,
                "rule_set":      rule_set_id,
                "rules_used":    ruleset.describe(),
                "paths":         paths,
            })
    else:
        total_perms = math.perm(len(PIECE_POOL), num_pieces)
        print()
        print(f"Piece pool : {len(PIECE_POOL)} pieces  →  P({len(PIECE_POOL)},{num_pieces}) = {total_perms} permutations")
        print(f"Board      : {board_size}×{board_size}  |  target length: {target_length}  |  rule set: {rule_set_id}")
        print(f"Attempts   : {ATTEMPTS_PER_COMBO} per permutation")
        print("-" * 80)
        print(f"{'#':>5}  {'Pieces':<60}  {'Exact paths':>11}")
        print("-" * 80)
        for idx, pieces in enumerate(itertools.permutations(PIECE_POOL, num_pieces), start=1):
            pieces_list = list(pieces)
            ruleset, exact_count, paths = _collect_exact_paths(
                pieces_list, board_size, target_length, rule_set_id,
                ATTEMPTS_PER_COMBO,
            )

            csv_rows.append((idx, pieces_list, exact_count))
            if exact_count == 0:
                continue

            pieces_str = " → ".join(pieces_list)
            print(f"{idx:5d}  {pieces_str:<60}  {exact_count:>11d}")

            results.append({
                "perm_num":      idx,
                "board_size":    board_size,
                "pieces":        pieces_list,
                "target_length": target_length,
                "exact_paths":   exact_count,
                "attempts":      ATTEMPTS_PER_COMBO,
                "rule_set":      rule_set_id,
                "rules_used":    ruleset.describe(),
                "paths":         paths,
            })

    # Summary ----------------------------------------------------------------
    total_exact = sum(r["exact_paths"] for r in results)
    nonzero     = len(results)
    print("-" * 80)
    print(f"\nPermutations with ≥1 exact path : {nonzero} / {total_perms}")
    print(f"Total exact-length paths found  : {total_exact}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = (
        f"turing_perms_{board_size}x{board_size}"
        f"_len{target_length}_rs{rule_set_id}_{timestamp}"
    )
    out_dir = os.path.dirname(os.path.abspath(__file__))

    if output_file_choice == 1:
        output_file = os.path.join(out_dir, base_name + ".json")
        with open(output_file, "w") as fh:
            json.dump(results, fh, indent=2)
        print(f"\n{nonzero} matching permutations (with paths) saved to:\n  {output_file}")

    else:  # output_file_choice == 2
        output_file = os.path.join(out_dir, base_name + ".csv")
        piece_headers = ",".join(f"piece{i + 1}" for i in range(num_pieces))
        with open(output_file, "w", newline="") as fh:
            fh.write(f"#,{piece_headers},Exact paths\n")
            for row_num, pieces_list, exact_count in csv_rows:
                fh.write(f"{row_num},{','.join(pieces_list)},{exact_count}\n")
        print(f"\nAll {total_perms} permutations saved to:\n  {output_file}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    board_size, num_pieces, rule_set_id, output_file_choice, target_length = get_user_inputs()
    run_tests(board_size, num_pieces, target_length, rule_set_id, output_file_choice)


if __name__ == "__main__":
    main()