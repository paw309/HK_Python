"""
chess_clock.py

Standalone chess clock engine for various game timing modes.

Supports:
- Infinity clock (count up, unbounded in logic; formatted display clamps to 24:59:59)
- Simple countdown timer (count down to zero)
- Moves per time unit (X moves in Y time)
- Time units per move (Y time per move) - resets to base time each move
- Two-player chess clock (linked clocks: when one runs, the other is stopped)
- Optional per-move bonus time (increment) on TIMER, MOVES_PER_TIME, and CHESS_CLOCK modes

Usage notes
-----------
- This module is UI-agnostic. It does not read input or draw graphics.
- The game code is responsible for:
  - Choosing clock types and initial times
  - Calling `start()`, `stop()`, `switch_player()`, and `on_move_completed()`
  - Calling `update()` periodically with the current real time, or using
    `tick(delta_seconds)` to advance virtual time
  - Displaying the formatted time strings (`format_time()`)

Time representation
-------------------
- Internally uses seconds (int or float) from an epoch or game start.
- Display uses the format `h:mm:ss` or `m:ss` or `s` depending on magnitude:
  * hours and minutes without leading zeros
  * seconds always two digits when there is at least 1 minute
  * formatted time is clamped to a maximum of 24h 59m 59s
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Dict


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

MAX_DISPLAY_SECONDS = 24 * 3600 + 59 * 60 + 59  # 24:59:59


def clamp_display_seconds(seconds: float) -> int:
    """
    Clamp a time value in seconds to the display maximum and ceil to an int.
    Negative values are clamped to 0.
    Uses ceil (round up) so that remaining time displays accurately - e.g.,
    59.1 seconds remaining should show as 1:00 (1 minute), not 0:59.
    """
    if seconds < 0:
        return 0
    if seconds > MAX_DISPLAY_SECONDS:
        return MAX_DISPLAY_SECONDS
    return math.ceil(seconds)


def format_hms(total_seconds: float) -> str:
    """
    Format a duration in seconds as a string with:
      - hours and minutes without leading zeros
      - seconds always at least two digits in "m:ss" format
      - Uses ceil() for remaining time, so 59.9s shows as "1:00", not "0:59"
      - Example outputs:
          0.1s   -> "0:01"
          5s     -> "0:05"
          59s    -> "0:59"
          59.9s  -> "1:00"
          60s    -> "1:00"
          61s    -> "1:01"
          3599s  -> "59:59"
          3600s  -> "1:00:00"
          3661s  -> "1:01:01"
    """
    secs = clamp_display_seconds(total_seconds)
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60

    if h > 0:
        # h:mm:ss, hours and minutes without leading zeros, seconds 2 digits
        return f"{h}:{m:02d}:{s:02d}"
    else:
        # m:ss, minutes without leading zero, seconds 2 digits
        return f"{m}:{s:02d}"


# ---------------------------------------------------------------------------
# Clock types and configuration
# ---------------------------------------------------------------------------

class ClockType(Enum):
    INFINITY = auto()           # Counts up from an initial value, unbounded logically
    TIMER = auto()              # Counts down to zero
    MOVES_PER_TIME = auto()     # X moves in Y time
    TIME_PER_MOVE = auto()      # Y time per move
    CHESS_CLOCK = auto()        # Two Players; one timer runs at a time


@dataclass
class ClockSettings:
    """
    Configuration of a single logical clock.

    Attributes:
        clock_type: One of ClockType
        initial_time_s: Base time for the clock (in seconds).
                        - For INFINITY, this is the starting offset (usually 0).
                        - For TIMER, this is the starting time to count down from.
                        - For MOVES_PER_TIME, total time for the phase.
                        - For TIME_PER_MOVE, base time per move (resets to this value each move).
        moves_required: For MOVES_PER_TIME mode, how many moves must be made
                        within initial_time_s. For other modes, ignored.
        time_per_move_s: For TIME_PER_MOVE mode, per-move time allocation
                         (if None, initial_time_s is used).
        bonus_per_move_s: Increment added at the end of each move.
                          - For TIME_PER_MOVE: NOT USED (clock always resets to base time)
                          - For TIMER / MOVES_PER_TIME / CHESS_CLOCK:
                            bonus is simply added to remaining time after move.
    """
    clock_type: ClockType
    initial_time_s: float = 0.0
    moves_required: int = 0
    time_per_move_s: Optional[float] = None
    bonus_per_move_s: float = 0.0


# ---------------------------------------------------------------------------
# Core single-clock timer
# ---------------------------------------------------------------------------

@dataclass
class GameClock:
    """
    Single-player clock implementing different timing modes.

    The clock is "time-source agnostic": you must advance it either by:
      - Calling update(now_seconds) with monotonically increasing "now"
      - OR calling tick(delta_seconds) manually.

    For two-player chess clocks, see ChessClock, which coordinates two GameClock
    instances and ensures only one is ticking at a time.
    """

    settings: ClockSettings

    # Internal state (seconds)
    remaining_time_s: float = field(init=False)
    elapsed_time_s: float = field(init=False, default=0.0)
    running: bool = field(init=False, default=False)
    _last_update_time: Optional[float] = field(init=False, default=None)
    moves_completed: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        # Initialize remaining_time depending on clock type
        ct = self.settings.clock_type

        if ct == ClockType.INFINITY:
            # For infinity, we keep elapsed_time and ignore remaining_time for logic.
            self.remaining_time_s = 0.0
            self.elapsed_time_s = self.settings.initial_time_s
        elif ct == ClockType.TIME_PER_MOVE:
            base = (
                self.settings.time_per_move_s
                if self.settings.time_per_move_s is not None
                else self.settings.initial_time_s
            )
            self.remaining_time_s = max(0.0, base)
        else:
            self.remaining_time_s = max(0.0, self.settings.initial_time_s)

    # ----------------- Time progression -----------------

    def start(self, now_seconds: Optional[float] = None) -> None:
        """
        Start or resume the clock.
        """
        if self.running:
            return
        self.running = True
        self._last_update_time = now_seconds

    def stop(self, now_seconds: Optional[float] = None) -> None:
        """
        Stop / pause the clock.
        """
        if not self.running:
            return
        # Update once more up to now, if time is provided
        if now_seconds is not None:
            self.update(now_seconds)
        self.running = False
        self._last_update_time = None

    def reset(self) -> None:
        """Reset clock to its initial state."""
        self.__post_init__()
        self.running = False
        self._last_update_time = None
        self.moves_completed = 0

    def update(self, now_seconds: float) -> None:
        """
        Advance the clock based on real time.
        Call periodically with monotonically increasing 'now_seconds'.
        """
        if not self.running:
            return

        if self._last_update_time is None:
            self._last_update_time = now_seconds
            return

        delta = now_seconds - self._last_update_time
        if delta < 0:
            # Ignore time going backwards
            self._last_update_time = now_seconds
            return

        self._last_update_time = now_seconds
        self.tick(delta)

    def tick(self, delta_seconds: float) -> None:
        """
        Advance the clock by delta_seconds (virtual time).
        Useful for z_testing or deterministic simulations.
        """
        if delta_seconds <= 0 or not self.running:
            return

        ct = self.settings.clock_type

        if ct == ClockType.INFINITY:
            self.elapsed_time_s += delta_seconds

        elif ct in (ClockType.TIMER, ClockType.MOVES_PER_TIME, ClockType.CHESS_CLOCK):
            self.remaining_time_s -= delta_seconds
            if self.remaining_time_s <= 0:
                self.remaining_time_s = 0
                self.running = False  # flag as expired

        elif ct == ClockType.TIME_PER_MOVE:
            self.remaining_time_s -= delta_seconds
            if self.remaining_time_s <= 0:
                self.remaining_time_s = 0
                self.running = False

    # ----------------- Move and bonus handling -----------------

    def on_move_completed(self) -> None:
        """
        Notify the clock that a move has been completed.
        Applies bonus time or resets time according to the mode and updates move counters.

        TIME_PER_MOVE: Always resets to base time (no bonus accumulation).
        Other modes: Adds bonus_per_move_s to remaining time (if bonus > 0).
        """
        self.moves_completed += 1
        bonus = self.settings.bonus_per_move_s
        ct = self.settings.clock_type

        if ct == ClockType.TIME_PER_MOVE:
            # For TIME_PER_MOVE mode, always reset to base time after each move.
            # The clock simply resets to the configured time - no bonus accumulation.
            # Each move gets the same amount of time.
            #
            # Example: base=60s -> Move 1: 60s, Move 2: 60s, Move 3: 60s, ...

            # Determine the base time for this mode:
            # time_per_move_s takes precedence if set, otherwise use initial_time_s
            if self.settings.time_per_move_s is not None:
                base = self.settings.time_per_move_s
            else:
                base = self.settings.initial_time_s

            # Reset to base time for the next move
            self.remaining_time_s = max(0.0, base)
            # Restart the clock for the next move
            self.running = True
            # Reset the reference time so the next update() call starts fresh
            # Without this, the old _last_update_time causes incorrect time deltas
            self._last_update_time = None

        else:
            # For TIMER, MOVES_PER_TIME, CHESS_CLOCK:
            # simply add bonus to remaining time (as an increment).
            # Only apply if bonus > 0
            if bonus > 0:
                self.remaining_time_s = max(0.0, self.remaining_time_s + bonus)

    # ----------------- Status queries -----------------

    def is_expired(self) -> bool:
        """
        Returns True if the clock has reached zero (for countdown modes).
        Infinity mode is never expired.
        """
        ct = self.settings.clock_type

        if ct == ClockType.INFINITY:
            return False

        return self.remaining_time_s <= 0

    def get_time_seconds(self) -> float:
        """
        Return the current logical time depending on clock type:
        - INFINITY: elapsed time
        - all others: remaining time
        """
        if self.settings.clock_type == ClockType.INFINITY:
            return self.elapsed_time_s
        return self.remaining_time_s

    def format_time(self) -> str:
        """
        Return a displayable string in hh:mm:ss-style format,
        with suppressed leading zeros for hours and minutes.
        """
        return format_hms(self.get_time_seconds())


# ---------------------------------------------------------------------------
# Two-player chess clock
# ---------------------------------------------------------------------------

@dataclass
class ChessClock:
    """
    Two-player chess clock.

    Maintains two GameClock instances (one per player) using the CHESS_CLOCK
    type with shared semantics:
      - Only one player's clock can run at a time.
      - When switching players, the active clock is stopped and the other
        player's clock is started.
      - Bonus time (increment) can be applied per move on each player's clock
        separately.

    Example:
        settings = ClockSettings(
            clock_type=ClockType.CHESS_CLOCK,
            initial_time_s=60*60,         # 60 minutes per player
            bonus_per_move_s=10           # 10-second increment
        )
        chess_clock = ChessClock(settings)
        chess_clock.start_game(starting_player="A", now_seconds=time.time())
    """

    settings: ClockSettings

    clocks: Dict[str, GameClock] = field(init=False)
    active_player: Optional[str] = field(init=False, default=None)

    def __post_init__(self) -> None:
        if self.settings.clock_type != ClockType.CHESS_CLOCK:
            raise ValueError("ChessClock requires settings.clock_type = CHESS_CLOCK")

        # Two identical clocks, one per player
        self.clocks = {
            "A": GameClock(self.settings),
            "B": GameClock(self.settings),
        }

    def start_game(self, starting_player: str, now_seconds: Optional[float] = None) -> None:
        """
        Initialize both clocks (reset) and start the given player's clock.
        starting_player must be "A" or "B".
        """
        if starting_player not in self.clocks:
            raise ValueError("starting_player must be 'A' or 'B'")

        # Reset both clocks
        for c in self.clocks.values():
            c.reset()

        self.active_player = starting_player
        self.clocks[starting_player].start(now_seconds=now_seconds)

    def switch_player(self, now_seconds: Optional[float] = None) -> None:
        """
        Simulate pressing the chess clock button:
          - Stop the current player's clock.
          - Apply per-move bonus to the player who just moved.
          - Start the opponent's clock.
        """
        if self.active_player is None:
            # Game hasn't been started yet
            return

        current = self.active_player
        other = "B" if current == "A" else "A"

        current_clock = self.clocks[current]
        other_clock = self.clocks[other]

        # Stop current, update to 'now'
        current_clock.stop(now_seconds=now_seconds)
        # Mark move completed on current player's clock (apply bonus)
        current_clock.on_move_completed()

        # If current clock has expired, do not start the other one
        if current_clock.is_expired():
            self.active_player = None
            return

        # Start opponent clock
        self.active_player = other
        other_clock.start(now_seconds=now_seconds)

    def update(self, now_seconds: float) -> None:
        """
        Advance only the active player's clock (if any).
        """
        if self.active_player is None:
            return
        self.clocks[self.active_player].update(now_seconds)

    def tick(self, delta_seconds: float) -> None:
        """
        Virtually advance only the active player's clock (for z_testing or
        simulations).
        """
        if self.active_player is None:
            return
        self.clocks[self.active_player].tick(delta_seconds)

    def is_player_flagged(self, player: str) -> bool:
        """
        True if the specified player's clock has expired.
        """
        return self.clocks[player].is_expired()

    def get_player_time_seconds(self, player: str) -> float:
        return self.clocks[player].get_time_seconds()

    def format_player_time(self, player: str) -> str:
        return self.clocks[player].format_time()