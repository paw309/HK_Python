"""
knightsturing

Turing Machine with Chess Pieces.

A chess piece traverses a square board following Hamiltonian path rules
(no square may be visited more than once).  After each move the piece
transforms according to a configurable rule set, mimicking a simple Turing
machine.  The simulation halts when the current piece has no legal unvisited
squares.

Main entry point:
    python -m knightsturing.turing_runner
"""

from pyversion.knightsturing.turing_engine import (
    PIECE_POOL,
    RuleSet,
    TuringRule,
    build_ruleset1,
    build_ruleset2,
    simulate_once,
    square_color,
)

__all__ = [
    "PIECE_POOL",
    "RuleSet",
    "TuringRule",
    "build_ruleset1",
    "build_ruleset2",
    "simulate_once",
    "square_color",
]
