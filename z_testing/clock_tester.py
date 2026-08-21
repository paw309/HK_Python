#!/usr/bin/env python3
"""
Minimal CLI wrapper around chess_clock.py for quick z_testing.

Supported modes
---------------
- infinity       : counts up from an initial offset
- timer          : one countdown timer
- chess          : two-player chess clock with optional per-move increment
- time_per_move  : single-player, Y time units per move with optional bonus
- moves_per_time : single-player, X moves in Y time with optional bonus

General controls
----------------
- For single-clock modes (infinity, timer, time_per_move, moves_per_time):
    q + Enter : quit
    (for time_per_move/moves_per_time) m + Enter : report a move completed

- For chess mode:
    a + Enter : active player completes a move (switches clock)
    q + Enter : quit
"""

import argparse
import sys
import time

from chess_clock import (
    ClockSettings,
    ClockType,
    GameClock,
    ChessClock,
)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Minimal chess clock CLI tester.")

    subparsers = parser.add_subparsers(dest="mode", required=True)

    # Infinity mode
    p_inf = subparsers.add_parser("infinity", help="Infinity clock (count up)")
    p_inf.add_argument(
        "--start-seconds",
        type=float,
        default=0.0,
        help="Starting offset in seconds (default: 0)",
    )

    # Timer mode
    p_timer = subparsers.add_parser("timer", help="Simple countdown timer")
    p_timer.add_argument("--hours", type=int, default=0, help="Hours")
    p_timer.add_argument("--minutes", type=int, default=0, help="Minutes")
    p_timer.add_argument("--seconds", type=int, default=0, help="Seconds")

    # Chess mode
    p_chess = subparsers.add_parser("chess", help="Two-player chess clock")
    p_chess.add_argument("--hours", type=int, default=0, help="Hours per player")
    p_chess.add_argument("--minutes", type=int, default=5, help="Minutes per player")
    p_chess.add_argument("--seconds", type=int, default=0, help="Seconds per player")
    p_chess.add_argument(
        "--increment",
        type=int,
        default=0,
        help="Increment (bonus) per move in seconds (default: 0)",
    )
    p_chess.add_argument(
        "--start-player",
        choices=["A", "B"],
        default="A",
        help="Which player starts (default: A)",
    )

    # TIME_PER_MOVE mode
    p_tpm = subparsers.add_parser(
        "time_per_move",
        help="Single-player: Y time units per move, optional growing bonus",
    )
    p_tpm.add_argument("--hours", type=int, default=0, help="Base hours per move")
    p_tpm.add_argument("--minutes", type=int, default=2, help="Base minutes per move")
    p_tpm.add_argument("--seconds", type=int, default=0, help="Base seconds per move")
    p_tpm.add_argument(
        "--bonus",
        type=int,
        default=0,
        help=(
            "Bonus per move in seconds, added cumulatively: "
            "move 1: base + 1*bonus, move 2: base + 2*bonus, ... (default: 0)"
        ),
    )

    # MOVES_PER_TIME mode
    p_mpt = subparsers.add_parser(
        "moves_per_time",
        help="Single-player: X moves in Y time units, optional bonus",
    )
    p_mpt.add_argument(
        "--moves-required",
        type=int,
        default=40,
        help="Number of moves to be completed within the time (default: 40)",
    )
    p_mpt.add_argument("--hours", type=int, default=1, help="Hours for the phase")
    p_mpt.add_argument("--minutes", type=int, default=30, help="Minutes for the phase")
    p_mpt.add_argument("--seconds", type=int, default=0, help="Seconds for the phase")
    p_mpt.add_argument(
        "--bonus",
        type=int,
        default=0,
        help="Bonus (increment) in seconds added at the end of each move (default: 0)",
    )

    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Mode implementations
# ---------------------------------------------------------------------------

def run_infinity(args):
    settings = ClockSettings(
        clock_type=ClockType.INFINITY,
        initial_time_s=args.start_seconds,
    )
    clock = GameClock(settings)
    now = time.time()
    clock.start(now_seconds=now)

    print("Infinity clock running.")
    print("Controls:")
    print("  q + Enter : quit")
    print()

    try:
        last_display = ""
        while True:
            time.sleep(0.1)
            now = time.time()
            clock.update(now)
            t_str = clock.format_time()
            status = f"Elapsed: {t_str:>8}"
            if status != last_display:
                print("\r" + status + " " * 5, end="", flush=True)
                last_display = status

            if sys.stdin in select_inputs():
                line = sys.stdin.readline().strip().lower()
                if line == "q":
                    print("\nExiting.")
                    break
    except KeyboardInterrupt:
        print("\nInterrupted, exiting.")


def run_timer(args):
    total_seconds = args.hours * 3600 + args.minutes * 60 + args.seconds
    if total_seconds <= 0:
        print("Total time must be > 0.")
        return

    settings = ClockSettings(
        clock_type=ClockType.TIMER,
        initial_time_s=total_seconds,
    )
    clock = GameClock(settings)
    now = time.time()
    clock.start(now_seconds=now)

    print("Timer running.")
    print("Controls:")
    print("  q + Enter : quit early")
    print()

    try:
        last_display = ""
        while True:
            time.sleep(0.1)
            now = time.time()
            clock.update(now)
            t_str = clock.format_time()
            status = f"Remaining: {t_str:>8}"
            if status != last_display:
                print("\r" + status + " " * 5, end="", flush=True)
                last_display = status

            if clock.is_expired():
                print(f"\nTime expired at displayed time {t_str}.")
                break

            if sys.stdin in select_inputs():
                line = sys.stdin.readline().strip().lower()
                if line == "q":
                    print("\nExiting early.")
                    break
    except KeyboardInterrupt:
        print("\nInterrupted, exiting.")


def run_chess(args):
    total_seconds = args.hours * 3600 + args.minutes * 60 + args.seconds
    if total_seconds <= 0:
        print("Total time per player must be > 0.")
        return

    settings = ClockSettings(
        clock_type=ClockType.CHESS_CLOCK,
        initial_time_s=total_seconds,
        bonus_per_move_s=args.increment,
    )
    chess = ChessClock(settings)
    now = time.time()
    chess.start_game(starting_player=args.start_player, now_seconds=now)

    print("Chess clock running.")
    print("Controls:")
    print("  a + Enter : active player completes a move (switch clock)")
    print("  q + Enter : quit")
    print()

    try:
        last_display = ""
        while True:
            time.sleep(0.1)
            now = time.time()
            chess.update(now)

            a_time = chess.format_player_time("A")
            b_time = chess.format_player_time("B")
            active = chess.active_player or "-"
            status = f"A: {a_time:>8} | B: {b_time:>8} | Active: {active}"
            if status != last_display:
                print("\r" + status + " " * 5, end="", flush=True)
                last_display = status

            # End if anyone flags
            a_flagged = chess.is_player_flagged("A")
            b_flagged = chess.is_player_flagged("B")
            if a_flagged or b_flagged:
                print()
                if a_flagged and b_flagged:
                    print("Both players flagged (probably due to simultaneous expiry).")
                elif a_flagged:
                    print(f"Player A flagged at displayed time {a_time}.")
                else:
                    print(f"Player B flagged at displayed time {b_time}.")
                break

            if sys.stdin in select_inputs():
                line = sys.stdin.readline().strip().lower()
                if line == "q":
                    print("\nExiting.")
                    break
                elif line == "a":
                    if chess.active_player is None:
                        print("\nGame already ended (no active player).")
                    else:
                        chess.switch_player(now_seconds=time.time())
    except KeyboardInterrupt:
        print("\nInterrupted, exiting.")


def run_time_per_move(args):
    """
    Single-player: Y time units per move, with optional growing bonus.

    At each completed move:
      - call on_move_completed(), which will:
          next move time = base + moves_completed * bonus
    """
    base_seconds = args.hours * 3600 + args.minutes * 60 + args.seconds
    if base_seconds <= 0:
        print("Base time per move must be > 0.")
        return

    settings = ClockSettings(
        clock_type=ClockType.TIME_PER_MOVE,
        initial_time_s=base_seconds,
        time_per_move_s=base_seconds,
        bonus_per_move_s=args.bonus,
    )

    clock = GameClock(settings)
    now = time.time()
    clock.start(now_seconds=now)

    print("TIME_PER_MOVE mode (single-player).")
    print(f"Base per move: {args.hours}h {args.minutes}m {args.seconds}s")
    if args.bonus:
        print(f"Bonus per move: {args.bonus}s (growing: base + n*bonus)")
    else:
        print("No bonus per move.")
    print("Controls:")
    print("  m + Enter : move completed (apply bonus and reset for next move)")
    print("  q + Enter : quit")
    print()

    try:
        last_display = ""
        while True:
            time.sleep(0.1)
            now = time.time()
            clock.update(now)

            t_str = clock.format_time()
            status = f"Move #{clock.moves_completed + 1} | Remaining for this move: {t_str:>8}"
            if status != last_display:
                print("\r" + status + " " * 5, end="", flush=True)
                last_display = status

            if clock.is_expired():
                print(
                    f"\nFlagged on move #{clock.moves_completed + 1} "
                    f"at displayed time {t_str}."
                )
                break

            if sys.stdin in select_inputs():
                line = sys.stdin.readline().strip().lower()
                if line == "q":
                    print("\nExiting.")
                    break
                elif line == "m":
                    if clock.is_expired():
                        print("\nClock already expired.")
                    else:
                        # End of move: stop, apply bonus, restart
                        clock.stop(now_seconds=time.time())
                        clock.on_move_completed()
                        clock.start(now_seconds=time.time())
    except KeyboardInterrupt:
        print("\nInterrupted, exiting.")


def run_moves_per_time(args):
    """
    Single-player: X moves in Y time units, optional bonus increment per move.
    """
    total_seconds = args.hours * 3600 + args.minutes * 60 + args.seconds
    if total_seconds <= 0:
        print("Total phase time must be > 0.")
        return
    if args.moves_required <= 0:
        print("moves_required must be > 0.")
        return

    settings = ClockSettings(
        clock_type=ClockType.MOVES_PER_TIME,
        initial_time_s=total_seconds,
        moves_required=args.moves_required,
        bonus_per_move_s=args.bonus,
    )

    clock = GameClock(settings)
    now = time.time()
    clock.start(now_seconds=now)

    print("MOVES_PER_TIME mode (single-player).")
    print(f"Phase: {args.moves_required} moves in {args.hours}h {args.minutes}m {args.seconds}s")
    if args.bonus:
        print(f"Bonus increment per move: {args.bonus}s (added to remaining time).")
    else:
        print("No bonus per move.")
    print("Controls:")
    print("  m + Enter : move completed (apply bonus, increment move counter)")
    print("  q + Enter : quit")
    print()

    try:
        last_display = ""
        while True:
            time.sleep(0.1)
            now = time.time()
            clock.update(now)

            t_str = clock.format_time()
            status = (
                f"Moves: {clock.moves_completed}/{args.moves_required} "
                f"| Remaining phase time: {t_str:>8}"
            )
            if status != last_display:
                print("\r" + status + " " * 5, end="", flush=True)
                last_display = status

            if clock.is_expired():
                print(
                    f"\nFlagged with {clock.moves_completed} moves completed "
                    f"(required {args.moves_required}) at displayed time {t_str}."
                )
                break

            if clock.moves_completed >= args.moves_required:
                print(
                    f"\nTarget achieved: {clock.moves_completed} moves completed "
                    f"with {t_str} remaining."
                )
                break

            if sys.stdin in select_inputs():
                line = sys.stdin.readline().strip().lower()
                if line == "q":
                    print("\nExiting.")
                    break
                elif line == "m":
                    if clock.is_expired():
                        print("\nClock already expired.")
                    else:
                        # Stop, mark move, apply bonus, continue
                        clock.stop(now_seconds=time.time())
                        clock.on_move_completed()
                        clock.start(now_seconds=time.time())
    except KeyboardInterrupt:
        print("\nInterrupted, exiting.")


# ---------------------------------------------------------------------------
# Simple "select" helper to poll stdin for input
# ---------------------------------------------------------------------------

def select_inputs():
    """
    Return a list of file descriptors that are ready for reading.
    This is a small wrapper so that the main loops stay simple.
    """
    import select
    rlist, _, _ = select.select([sys.stdin], [], [], 0.0)
    return rlist


def main(argv=None):
    args = parse_args(argv)

    if args.mode == "infinity":
        run_infinity(args)
    elif args.mode == "timer":
        run_timer(args)
    elif args.mode == "chess":
        run_chess(args)
    elif args.mode == "time_per_move":
        run_time_per_move(args)
    elif args.mode == "moves_per_time":
        run_moves_per_time(args)
    else:
        raise SystemExit(f"Unknown mode: {args.mode}")


if __name__ == "__main__":
    main()
