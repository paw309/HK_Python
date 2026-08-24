"""
turing_engine.py

Core simulation engine for the Turing Machine with Chess Pieces.

Rules:
- A single chess piece traverses a board following Hamiltonian path rules
  (no square may be visited more than once).
- After each move the piece transforms according to a rule set.
- The simulation halts when the current piece has no legal unvisited squares.
- A simulation is "successful" if it halts at exactly the target path length.

Public API:
    PIECE_POOL          – list of piece names available for selection
    TuringRule          – one transformation rule
    RuleSet             – collection of rules with apply() / describe()
    build_ruleset1()    – simple cycle, no colour condition
    build_ruleset2()    – colour-based rules (max 4 rules)
    simulate_once()     – run one simulation; return (path_length, path)
"""

import os
import random
import sys
from typing import List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from piecekeeper import PIECE_DATA, get_move_func

# ---------------------------------------------------------------------------
# Piece pool
# ---------------------------------------------------------------------------

# Only single-move-set leapers are eligible: pieces whose entire move set is
# derived from a single (a, b) displacement pair.  That covers every piece in
# the "leaper" group (wazir, ferz, dabbaba, camel, alfil, zebra, giraffe,
# antelope, gazelle, flamingo, bharal) plus the knight, which is a (1,2) leaper
# classified as "canon".
PIECE_POOL: List[str] = [
    name for name, data in PIECE_DATA.items()
    if data.get("piece_group") == "leaper"
    or name == "knight"
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def square_color(row: int, col: int) -> str:
    """Return 'black' or 'white' for the square at (row, col).

    Light squares (where (row + col) is even) are 'white';
    dark squares (where (row + col) is odd) are 'black'.
    This matches the standard chess convention: dark = black, light = white.
    """
    return "white" if (row + col) % 2 == 0 else "black"


# ---------------------------------------------------------------------------
# Rule representation
# ---------------------------------------------------------------------------

class TuringRule:
    """One piece-transformation rule.

    When *from_piece* lands on a square whose colour matches *color*
    (or any colour when *color* is None) and the move number parity matches
    *parity* (or any parity when *parity* is None), the piece becomes
    *to_piece*.
    """

    def __init__(self, from_piece: str, to_piece: str,
                 color: Optional[str] = None,
                 parity: Optional[str] = None) -> None:
        self.from_piece = from_piece
        self.to_piece   = to_piece
        self.color      = color    # None → applies to any square color
        self.parity     = parity   # None → any; 'odd' or 'even' for move parity

    def matches(self, piece: str, sq_color: str, move_number: int = 0) -> bool:
        if self.from_piece != piece:
            return False
        if self.color is not None and self.color != sq_color:
            return False
        if self.parity is not None:
            is_odd = (move_number % 2 == 1)
            if self.parity == "odd" and not is_odd:
                return False
            if self.parity == "even" and is_odd:
                return False
            # flip/flop: used by the flip-flop rule set to count piece-0 moves.
            # piece-0 always moves on odd move numbers (1, 3, 5, …) because
            # pieces[1] and pieces[2] each return to pieces[0] in exactly one
            # move.  The n-th piece-0 move occurs at move_number = 2n-1, so
            # move_number // 2 gives (n-1), whose parity selects the target.
            #   "flip": 1st, 3rd, 5th … piece-0 move  → (move_number // 2) % 2 == 0
            #   "flop": 2nd, 4th, 6th … piece-0 move  → (move_number // 2) % 2 == 1
            if self.parity == "flip" and (move_number // 2) % 2 != 0:
                return False
            if self.parity == "flop" and (move_number // 2) % 2 != 1:
                return False
        return True

    def describe(self) -> str:
        color_str  = f" on {self.color}" if self.color else ""
        parity_str = f" (move {self.parity})" if self.parity else ""
        return f"when {self.from_piece}{color_str}{parity_str} moves → {self.to_piece}"

    def __repr__(self) -> str:
        return (f"TuringRule({self.from_piece!r}, {self.to_piece!r}, "
                f"{self.color!r}, {self.parity!r})")


class RuleSet:
    """A collection of TuringRules."""

    def __init__(self, rules: List[TuringRule], ruleset_id: int) -> None:
        self.rules      = rules
        self.ruleset_id = ruleset_id

    def apply(self, piece: str, row: int, col: int,
              move_number: int = 0) -> str:
        """Return the new piece after landing on (row, col).

        The first matching rule is applied.  If no rule matches, the piece
        is unchanged.

        Args:
            piece:       Current piece name before transformation.
            row, col:    Destination square coordinates.
            move_number: 1-based move counter (used for parity-based rules).
        """
        sq = square_color(row, col)
        for rule in self.rules:
            if rule.matches(piece, sq, move_number):
                return rule.to_piece
        return piece

    def describe(self) -> List[str]:
        return [r.describe() for r in self.rules]


# ---------------------------------------------------------------------------
# Rule-set builders
# ---------------------------------------------------------------------------

def build_ruleset1(pieces: List[str]) -> RuleSet:
    """Rule set 1 – simple cycle, no color condition.

    pieces[0] → pieces[1] → … → pieces[n-1] → pieces[0]
    """
    n = len(pieces)
    rules = [TuringRule(pieces[i], pieces[(i + 1) % n]) for i in range(n)]
    return RuleSet(rules, 1)


def build_ruleset2(pieces: List[str]) -> RuleSet:
    """Rule set 2 – color-based transformation (maximum 4 rules).

    2 pieces  A, B
        A → B  (black),  A → B  (white),  B → A
    3 pieces  A, B, C
        A → B  (black),  A → C  (white),  B → A,  C → A
    4 pieces  A, B, C, D
        A → B  (black),  A → C  (white),  B → D,  C → D
        (D has no outgoing rule; once the piece becomes D it stays D until
        it can no longer move, creating an early-halt opportunity)
    """
    rules: List[TuringRule] = []
    n = len(pieces)

    if n == 2:
        rules.append(TuringRule(pieces[0], pieces[1], "black"))
        rules.append(TuringRule(pieces[0], pieces[1], "white"))
        rules.append(TuringRule(pieces[1], pieces[0]))

    elif n == 3:
        rules.append(TuringRule(pieces[0], pieces[1], "black"))
        rules.append(TuringRule(pieces[0], pieces[2], "white"))
        rules.append(TuringRule(pieces[1], pieces[0]))
        rules.append(TuringRule(pieces[2], pieces[0]))

    elif n == 4:
        # 4 rules (maximum)
        rules.append(TuringRule(pieces[0], pieces[1], "black"))
        rules.append(TuringRule(pieces[0], pieces[2], "white"))
        rules.append(TuringRule(pieces[1], pieces[3]))
        rules.append(TuringRule(pieces[2], pieces[3]))
        # pieces[3] intentionally has no outgoing rule (acts as a "terminal"
        # state that will eventually halt when it runs out of moves)

    return RuleSet(rules, 2)


def build_flip_flop_ruleset(pieces: List[str]) -> RuleSet:
    """Rule set 3 – flip-flop transformation (exactly 3 pieces).

    Every other time pieces[0] moves it alternates between pieces[1] and
    pieces[2], producing the sequence:
        pieces[0] → pieces[1] → pieces[0] → pieces[2] → pieces[0] → …

    pieces[0] → pieces[1]  on the 1st, 3rd, 5th … piece-0 move  ("flip")
    pieces[0] → pieces[2]  on the 2nd, 4th, 6th … piece-0 move  ("flop")
    pieces[1] → pieces[0]  always
    pieces[2] → pieces[0]  always
    """
    rules: List[TuringRule] = [
        TuringRule(pieces[0], pieces[1], parity="flip"),
        TuringRule(pieces[0], pieces[2], parity="flop"),
        TuringRule(pieces[1], pieces[0]),
        TuringRule(pieces[2], pieces[0]),
    ]
    return RuleSet(rules, 3)


def build_ruleset6(pieces: List[str]) -> RuleSet:
    """Rule set 6 – specialized 3-piece color cycling:
        piece1: [knight, wazir, threeleaper, giraffe, zebra]
        piece2: [ferz, dabbaba, alfil, tripper, camel]
        piece3: [king]
    Rules:
        - piece 1: white → piece 2, black → piece 3
        - piece 2: white → piece 3
        - piece 3: white → piece 1
        - piece 3: black → piece 2
    """
    p1, p2, p3 = pieces
    rules = [
        TuringRule(p1, p2, "white"),
        TuringRule(p1, p3, "black"),
        TuringRule(p2, p3, "white"),
        TuringRule(p3, p1, "white"),
        TuringRule(p3, p2, "black"),
    ]
    return RuleSet(rules, 6)


def _count_onward(pos: Tuple[int, int], piece: str,
                  visited: Set[Tuple[int, int]], board_size: int) -> int:
    """Count unvisited squares reachable from *pos* with *piece*."""
    moves = get_move_func(piece)(pos[0], pos[1], board_size)
    return sum(1 for m in moves if m not in visited)


def simulate_once(
    board_size: int,
    start_pos: Tuple[int, int],
    start_piece: str,
    ruleset: RuleSet,
    max_steps: int,
    use_warnsdorff: bool = False,
) -> Tuple[int, List[Tuple[int, int, str]]]:
    """Run one simulation of the Turing machine.

    Args:
        board_size:     Side length of the square board.
        start_pos:      (row, col) of the starting square.
        start_piece:    Name of the piece placed at the start.
        ruleset:        Rule set governing piece transformations.
        max_steps:      Hard upper limit on moves (prevents infinite loops).
        use_warnsdorff: When True, use Warnsdorff's heuristic (prefer moves
                        with fewest onward options) instead of a pure random
                        walk.

    Returns:
        path_length:  Number of moves completed (= len(path) - 1).
        path:         List of (row, col, piece) at each position, starting
                      with the initial square.
    """
    n        = board_size
    visited: Set[Tuple[int, int]] = {start_pos}
    path: List[Tuple[int, int, str]] = [
        (start_pos[0], start_pos[1], start_piece)
    ]
    current_pos   = start_pos
    current_piece = start_piece

    while len(path) - 1 < max_steps:
        legal = [
            m for m in get_move_func(current_piece)(current_pos[0], current_pos[1], n)
            if m not in visited
        ]
        if not legal:
            break   # Path halts naturally here

        if use_warnsdorff and len(legal) > 1:
            best: List[Tuple[int, int]] = []
            min_cnt = float("inf")
            # path starts with 1 element (the start square), so len(path) gives
            # the 1-based move number for the upcoming move.
            move_num = len(path)
            for m in legal:
                next_piece = ruleset.apply(current_piece, m[0], m[1], move_num)
                visited.add(m)
                cnt = _count_onward(m, next_piece, visited, n)
                visited.remove(m)
                if cnt < min_cnt:
                    min_cnt = cnt
                    best = [m]
                elif cnt == min_cnt:
                    best.append(m)
            chosen = random.choice(best)
        else:
            chosen = random.choice(legal)

        # path starts with 1 element (the start square), so len(path) gives
        # the 1-based move number for the upcoming move.
        move_num      = len(path)
        new_piece     = ruleset.apply(current_piece, chosen[0], chosen[1], move_num)
        current_pos   = chosen
        current_piece = new_piece
        visited.add(current_pos)
        path.append((current_pos[0], current_pos[1], current_piece))

    return len(path) - 1, path