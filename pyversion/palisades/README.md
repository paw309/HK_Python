# Palisades

**Palisades** is a single-player puzzle game based on the **non-crossing Knight's Tour**. Move your chess piece across the board, visiting every square exactly once — but the path you draw must never cross itself. One extra constraint transforms a familiar puzzle into something altogether harder.

---

## Table of Contents

- [Overview](#overview)
- [Getting Started](#getting-started)
- [Game Configuration](#game-configuration)
  - [Board Size](#board-size)
  - [Piece Selection](#piece-selection)
  - [First Square](#first-square)
  - [Clock](#clock)
- [How to Play](#how-to-play)
  - [Select Mode Start](#select-mode-start)
  - [Making Moves](#making-moves)
- [Non-Crossing Constraint](#non-crossing-constraint)
  - [What Counts as a Crossing](#what-counts-as-a-crossing)
  - [Closed Tours](#closed-tours)
- [In-Game Controls](#in-game-controls)
  - [Mouse](#mouse)
  - [Keyboard Shortcuts](#keyboard-shortcuts)
- [HUD & Overlays](#hud--overlays)
  - [Move Guide](#move-guide)
  - [Move Numbers](#move-numbers)
  - [Warnsdorff Degrees (Non-Crossing)](#warnsdorff-degrees-non-crossing)
- [Endgame & Replay](#endgame--replay)
  - [Win & Loss Conditions](#win--loss-conditions)
  - [Closed vs Open Tours](#closed-vs-open-tours)
  - [Retry](#retry)
  - [Replay Mode](#replay-mode)
  - [Undo](#undo)
- [Share Codes](#share-codes)
- [Advanced Strategy](#advanced-strategy)
- [Architecture & Technical Notes](#architecture--technical-notes)
  - [Crossing Detection Algorithm](#crossing-detection-algorithm)
  - [Non-Crossing Warnsdorff Heuristic](#non-crossing-warnsdorff-heuristic)
- [Known Limitations](#known-limitations)
- [Credits](#credits)

---

## Overview

Palisades is a variant of the classic Knight's Tour with one additional rule: **the path you trace must never cross itself**. Every legal move for your piece is checked against all previously drawn segments; if moving there would cause an X-intersection or a T-intersection, that square is off-limits.

This makes Palisades significantly harder than the standard Tour. Moves that appear safe in isolation may wall you off from large regions of the board once the path starts folding back on itself. Planning ahead — particularly visualising how the path will re-enter areas already partially covered — is essential.

The game is colour-coded in green to distinguish it from the standard Knight's Tour.

---

## Getting Started

**Requirements**

- Python 3.7 or later
- pygame (`pip install pygame`)
- The full `Hamiltonian-Knights` repository (shared libraries are loaded from `sharedlib/`)

**Run the game**

```bash
cd Hamiltonian-Knights
python palisades/palisades_v01.py
```

The window opens at your current display resolution and is fully resizable. On Windows the window is automatically maximised.

---

## Game Configuration

All settings are adjusted from the **Menu** screen using the `<` and `>` buttons next to each row, or by clicking the board to reposition the preview piece.

### Board Size

| Setting | Range | Default |
|---|---|---|
| Minimum | 5 × 5 | — |
| Maximum | 16 × 16 | — |
| Default | 8 × 8 | ✓ |

Larger boards offer more room but dramatically increase the difficulty of avoiding crossings. On very large boards the path must thread through itself with significant precision to visit every square.

### Piece Selection

Any piece from the `piecekeeper` module can be selected, subject to the constraint that **even-parity (colour-bound) pieces are excluded** — they cannot visit every square on a standard board and are therefore ineligible for a Hamiltonian tour.

Excluded pieces: bishop, rook, queen, king, wazir, ferz, dabbaba, alfil, toad, virgo, sagittarius, pterodactyl, gunkan.

All remaining pieces — knights, camels, zebras, compound fairy pieces, zodiac pieces, and more — are available.

Minimum board sizes per piece are enforced:

| Piece | Min. Board |
|---|---|
| knight | 5 × 5 |
| all others | 5 × 5 (default) |

A warning is displayed if the currently selected piece cannot be used on the current board size.

### First Square

Controls how the starting square is determined at the beginning of each game.

| Mode | Description |
|---|---|
| **select** | The board is shown and you click a square to set your start position. |
| **random** | A random starting square is chosen automatically when you press start. |

`select` mode adds a strategic dimension: the non-crossing constraint makes some starting squares far more tractable than others. Corner and edge starts tend to be the hardest.

### Clock

Sets a time budget for the entire game. `0` means unlimited; an elapsed timer is displayed instead of a countdown.

| Range | Increment | Default |
|---|---|---|
| 0 to 330 seconds | 30 seconds | 0 (no limit) |

When the clock reaches zero the game ends immediately with a timeout.

---

## How to Play

### Select Mode Start

If **first square** is set to `select`, after pressing **start** the board enters a waiting state. A prompt appears: *click a square to start*. Click any square on the board to commit your starting position. The game clock starts only after you have chosen your starting square.

### Making Moves

1. **Configure** your game on the Menu screen: choose piece, board size, first square mode, and clock settings.
2. Press **start**. The board populates with your piece at the starting square.
3. **Click a highlighted square** to move your piece there. Only legal, non-crossing moves are shown.
4. Each move adds a segment to the path drawn on the board. Path segments are rendered in red.
5. Continue until you have **visited every square** (tour complete) or you are **blocked**, **time out**, or **resign**.

---

## Non-Crossing Constraint

The defining rule of Palisades: **at no point may the drawn path cross itself**.

### What Counts as a Crossing

Two types of intersection are detected and blocked:

**Proper crossing (X-intersection)**
Two segments cross at an interior point: each segment's endpoints lie on strictly opposite sides of the other segment's line. This is the most visually obvious crossing.

**T-intersection**
A new move's endpoint lands exactly on the interior of an existing segment (or vice versa — an existing path vertex falls on the interior of the proposed new segment). This catches cases where a sliding piece's drawn line passes through a previously visited position, even if the piece itself does not land on that square.

Both types are detected geometrically using cross-products and collinearity checks, so the detection is exact regardless of the piece type or board size.

A move is offered as legal only if it passes **both** the standard piece-legality test (correct move vector, unvisited target square) **and** the non-crossing test.

### Closed Tours

When you visit the final square (all squares covered), the game also checks whether the path can be **closed**: is the starting square one legal move away from the ending square, and would the closing segment be non-crossing?

- If yes: the result is a **non-crossing closed tour** — the hardest possible outcome.
- If no: the result is a **non-crossing open tour**.

Both outcomes are wins; the closed tour is displayed with a different colour and message.

---

## In-Game Controls

### Mouse

| Action | Effect |
|---|---|
| Click a legal-move square | Move your piece there |
| Click a menu `<` / `>` button | Cycle through that setting's values |
| Click the board in Menu | Reposition the preview piece |
| Click the board in Waiting state | Commit starting square (select mode) |
| Click any button | Activate that button's action |

### Keyboard Shortcuts

| Key | Context | Action |
|---|---|---|
| `H` | In-game | Toggle non-crossing Warnsdorff Degrees overlay |

---

## HUD & Overlays

### Move Guide

Displays directional arrows from the current square to every legal non-crossing move. Overlapping the path visually helps you scan available options without working out the crossing geometry yourself. Toggle with the **show / hide move guide** button (active in all game states including the menu preview).

### Move Numbers

Overlays each visited square with the move number on which it was visited. Useful for tracing the path and spotting how recently you passed through a region. Toggle with the **show / hide move #'s** button (always active).

### Warnsdorff Degrees (Non-Crossing)

Overlays each currently-legal destination square with its **non-crossing degree** — the number of non-crossing moves that would be available *from* that square after landing there.

This is an extended Warnsdorff heuristic that accounts for the crossing constraint: it does not simply count unvisited neighbours, but recomputes the crossing filter from the prospective path. Lower-degree squares tend to become inaccessible sooner; the heuristic guides you toward moves that preserve future connectivity.

Toggle with **H** (keyboard) or the **show / hide degrees** button (in-game and endgame only).

> **Note:** Because crossing detection depends on the full current path, the non-crossing Warnsdorff degree is more expensive to compute than the standard version. On large boards with many legal moves, there may be a brief recalculation pause when hint mode is toggled on.

---

## Endgame & Replay

### Win & Loss Conditions

| Outcome | Condition | Message |
|---|---|---|
| ✅ Closed tour | All squares visited; closing segment is non-crossing | *non-crossing closed tour!* |
| ✅ Open tour | All squares visited; closing not possible or would cross | *non-crossing open tour!* |
| ❌ No moves | No legal non-crossing moves remain | *no legal moves* |
| ❌ Timeout | Clock expires | *time's up* |
| ❌ Resign | You press resign | *resigned* |

### Closed vs Open Tours

After a completed tour the game automatically evaluates whether the tour can be closed:

- The final square is checked for a legal piece move back to the starting square.
- The closing segment is tested for crossings against all intermediate segments.

If both conditions are met the tour is declared **closed** and displayed in a brighter green. An open tour is still a successful completion.

### Retry

After any endgame the **retry** button replays the exact same puzzle (same random seed, same starting position if the mode was `random`). This lets you attempt the non-crossing constraint again with foreknowledge of the board layout.

### Replay Mode

After a game ends, press **start replay** to enter a step-by-step review of your game. Use:
- **`+`** button to advance one move forward
- **`-`** button to step one move backward

The path, visited squares, and move numbers all update to match the selected step. This is particularly useful for identifying the move at which the path became constrained.

### Undo

While in-game the **undo last move** button steps back one move. There is no undo limit — you can walk all the way back to the starting square. The path is fully restored after each undo, including crossing-filter state.

---

## Share Codes

Every generated puzzle receives a 16-character **share code** (base-32 encoded) that captures:
- Board size
- First square mode
- Clock setting
- The RNG seed (for `random` start mode)

**Sharing a puzzle**

1. After starting a game the share code is displayed in the side panel.
2. Press **copy share code** to copy it to your clipboard.
3. Send the code to a friend.

**Loading a shared puzzle**

1. On the Menu screen press **enter share code**.
2. Type or paste the 16-character code into the input box.
3. Press **start** — the same board configuration and starting square will be reproduced.

> **Note:** `select` mode games let the human choose their starting square, so the share code encodes settings only (no starting position). Both players will choose their own start on the same board configuration.

---

## Advanced Strategy

### The Non-Crossing Constraint Changes Everything

In the standard Knight's Tour you can often rescue a near-dead-end position by threading back through a sparse area. In Palisades, those rescue routes are frequently blocked by your own earlier segments. The path must be planned more globally from the outset.

### Starting Square Matters More Here

Some starting positions make non-crossing tours possible; others make them near-impossible on a given board. Edge and corner squares restrict early moves and force the path to re-enter the centre in tightly constrained corridors. Central squares tend to give more room. Experiment with `select` mode to find tractable starting positions.

### Use the Non-Crossing Degree Overlay

Enable **show degrees** (`H`) to see Warnsdorff numbers computed against the non-crossing filter. These are more informative than standard Warnsdorff numbers because they already exclude moves that create crossings. Prefer non-zero degrees; a degree of zero means that destination is a dead end under the crossing constraint.

### Think in Loops and Regions

Crossings most often arise when the path starts forming near-closed loops. If a cluster of moves is forming a rough circle, the route back through the interior of that circle will eventually cross the circle's perimeter. Plan to leave and re-enter regions via the same corridor to avoid enclosing areas you still need to visit.

### Piece Choice

- **Knight**: The classic choice. Its non-linear L-shaped movement produces naturally weaving paths that cross themselves less readily than orthogonal or diagonal sliding paths.
- **Camel / Zebra**: Longer leaps create wider path segments that are easier to cross at distance. Requires more foresight.
- **Exotic pieces**: Multi-vector leapers (compound pieces, zodiac pieces) can reach many destinations per turn, but the larger number of options makes it harder to anticipate future crossing constraints.

### Clock Settings

Start with `clock = 0` (unlimited) when learning the non-crossing constraint on a new piece or board size. Once you can reliably complete tours, add a clock to test efficiency.

---

## Architecture & Technical Notes

The game is built across two focused modules:

| Module | Role |
|---|---|
| `palisades_v01.py` | Entry point — pygame init, window setup, main game loop |
| `palisades_controller.py` | Game state machine, crossing detection, move logic, rendering, event handling |

`PalisadesController` inherits from `BaseGameController` (in `sharedlib/`) for undo, replay, clock, codec I/O, and UI infrastructure, and overrides eight abstract methods to implement Palisades-specific logic.

### Crossing Detection Algorithm

Crossing detection is implemented in three geometry helpers:

**`_cross_product(o, a, b)`**
Returns the signed area of triangle OAB (×2). Used to determine which side of a line a point lies on.

**`_segments_properly_intersect(p1, p2, p3, p4)`**
Returns `True` if segments p1-p2 and p3-p4 cross at an interior point: each segment's endpoints must be on strictly opposite sides of the other segment's supporting line. Shared endpoints are not considered crossings.

**`_point_on_segment_interior(p, a, b)`**
Returns `True` if point `p` is collinear with, lies between, and is not equal to either endpoint of segment a-b. Used to detect T-intersections.

**`_would_create_crossing(path, new_start, new_end)`**
Checks the proposed new segment against every existing segment in the path except the final one (which shares `new_start` as an endpoint). Tests both proper crossings and T-intersections. Also checks whether any existing path vertex falls on the interior of the new segment — relevant for pieces whose drawn segments can span previously visited squares.

**`_would_close_crossing(path, last_pos, first_pos)`**
Checks the closing segment (last position → first position) for crossings against all intermediate path segments, skipping only the first and last segments which share the closing segment's endpoints.

### Non-Crossing Warnsdorff Heuristic

`_calculate_hint_degrees()` computes hint values that account for the crossing constraint:

For each currently legal (non-crossing) move `m`:
1. Compute the hypothetical next path: `path + [m]`
2. Compute the hypothetical next visited set: `visited ∪ {m}`
3. Get standard piece moves from `m`
4. Filter these by `_would_create_crossing(next_path, m, candidate)`
5. The hint degree is the count of candidates that pass the filter

This is more expensive than standard Warnsdorff but gives accurate guidance because it incorporates the actual crossing geometry at the next step.

**Codec schema**

| Field | Bits | Values |
|---|---|---|
| board | 4 | 5–16 |
| first_square | 1 | select / random |
| clock | 6 | 0 (infinite) or 1–30 minutes |

---

## Known Limitations

1. **No guaranteed solvability** — not all (piece, board size, starting square) combinations admit a non-crossing Hamiltonian path. The game does not pre-validate whether the puzzle is solvable; if no legal non-crossing moves remain before the tour is complete, the game ends with *no legal moves*.
2. **Hint computation cost** — on large boards with many legal moves, recalculating non-crossing Warnsdorff degrees involves re-running the crossing filter for every candidate of every legal move. This is more expensive than standard Warnsdorff and may cause a brief pause on the largest boards.
3. **Replay memory is unbounded** — very long games (e.g., a successful 16×16 tour) accumulate 256 state snapshots, each storing the full path and visited set.
4. **Clipboard fallback** — on Linux, clipboard copy may silently fail if `xclip` / `xsel` are not installed.
5. **Even-parity pieces excluded** — pieces that cannot visit every square of a standard chessboard (bishop, rook, queen, etc.) are removed from the piece list and are not available in Palisades.

---

## Credits

Developed by **paw309**.  
Built with [Python](https://www.python.org/) and [pygame](https://www.pygame.org/).  
Inspired by the mathematics of Hamiltonian paths, non-crossing partitions, and the geometry of self-avoiding walks.

---

> **Every move draws a line. Don't let your lines cross.**
