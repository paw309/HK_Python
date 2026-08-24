# Megalomino

**Megalomino** is a single-player puzzle game that reimagines the Knight's Tour on an irregular canvas. Instead of a rectangular chessboard, your piece must visit every cell of a single connected **polyomino** — an island of squares — exactly once.

---

## Table of Contents

- [Overview](#overview)
- [Getting Started](#getting-started)
- [Game Configuration](#game-configuration)
  - [Board Color](#board-color)
  - [Shape Class](#shape-class)
  - [Clock](#clock)
  - [Time Per](#time-per)
- [Shape Library](#shape-library)
  - [Static Shapes (7–15 Cells)](#static-shapes-715-cells)
  - [Dynamic Shapes (16–20 Cells)](#dynamic-shapes-1620-cells)
  - [Hippomino (4-Piece Mode)](#hippomino-4-piece-mode)
- [How to Play](#how-to-play)
- [Square Color Guide](#square-color-guide)
- [In-Game Controls](#in-game-controls)
  - [Mouse](#mouse)
  - [Keyboard Shortcuts](#keyboard-shortcuts)
- [HUD & Overlays](#hud--overlays)
  - [Move Guide](#move-guide)
  - [Move Track](#move-track)
  - [Warnsdorff Degrees](#warnsdorff-degrees)
  - [Peek Mode](#peek-mode)
  - [Tour Path](#tour-path)
- [Endgame & Replay](#endgame--replay)
  - [Win & Loss Conditions](#win--loss-conditions)
  - [Retry](#retry)
  - [Replay Mode](#replay-mode)
  - [Undo](#undo)
- [Share Codes](#share-codes)
- [Statistics](#statistics)
- [Advanced Strategy](#advanced-strategy)
  - [Warnsdorff First, Always](#warnsdorff-first-always)
  - [Parity Awareness](#parity-awareness)
  - [Peninsula Priority](#peninsula-priority)
  - [Shape Class Progression](#shape-class-progression)
  - [Dynamic Shape Approach (16–20 Cells)](#dynamic-shape-approach-1620-cells)
  - [Hippomino Approach (4-Piece Mode)](#hippomino-approach-4-piece-mode)
  - [Clock Settings](#clock-settings)
- [Architecture & Technical Notes](#architecture--technical-notes)
  - [Module Overview](#module-overview)
  - [Tour Catalogue](#tour-catalogue)
  - [Dynamic Tour Generation (16–20 Cells)](#dynamic-tour-generation-1620-cells)
  - [Hippomino Puzzle Generation (4-Piece Mode)](#hippomino-puzzle-generation-4-piece-mode)
  - [Megalomino Codec](#megalomino-codec)
  - [Controller Architecture](#controller-architecture)
- [Known Limitations](#known-limitations)
- [Credits](#credits)

---

## Overview

A **polyomino** is a connected shape made of unit squares joined edge-to-edge — think Tetris pieces, but without the rectangular bounding box. Megalomino presents you with one such shape and asks a deceptively simple question: can your piece visit every cell exactly once?

This is the **Hamiltonian path problem** on an irregular graph. Unlike a standard chessboard, where many tour solutions exist, a specific polyomino may have only a handful of valid tours — or none at all. Choosing where to start, which direction to go, and when to sacrifice a short-term option for long-term connectivity is at the heart of every puzzle.

**What sets Megalomino apart from the classic Knight's Tour:**

- The board has a **non-rectangular boundary** — edge effects and isolated peninsulas change the parity landscape completely
- A verified solution path is stored for every catalogued shape and can be revealed via **toggle tour path**
- For shapes of 16+ cells, tours are assembled on-the-fly from two smaller validated shapes, so the puzzle is genuinely hard (no guaranteed path exists)
- **Reentrant tours** — where the final cell is one legal move from the start — are only possible on even-cell shapes with equal light and dark square counts, mirroring the classical parity constraint

---

## Getting Started

**Requirements**

- Python 3.7 or later
- pygame (`pip install pygame`)
- The full `Hamiltonian-Knights` repository (shared libraries are loaded from `sharedlib/` and tour data from `tourbus/`)

**Run the game**

```bash
cd Hamiltonian-Knights
python hippomino/megalomino_v02.py
```

The window opens at your current display resolution and is fully resizable. On Windows the window is automatically maximised.

---

## Game Configuration

All settings are adjusted from the **Menu** screen using the `<` and `>` buttons on each row.

### Board Color

Controls the visual appearance of the polyomino squares.

| Choice | Description |
|---|---|
| **chessboard** | Alternating light and dark squares, as on a standard chessboard |
| **monochrome** | All squares rendered in a single uniform tone |

Chessboard coloring makes parity constraints immediately visible and is recommended for experienced players.

### Shape Class

Selects which size category of polyomino to play on.

| Class | Cells | Tourable Shapes | Reentrant Tours |
|---|---|---|---|
| Heptomino | 7 | 2 | 0 |
| Octomino | 8 | 10 | 1 |
| Nonomino | 9 | 57 | 0 |
| Decomino | 10 | 194 | 14 |
| Undecamino | 11 | 617 | 0 |
| Dodecamino | 12 | 1,580 | 61 |
| Tridecamino | 13 | 4,858 | 0 |
| Tetradecamino | 14 | 13,124 | 305 |
| Pentadecamino | 15 | 43,487 | 0 |
| Hexadecamino | 16 | dynamic | — |
| Heptadecamino | 17 | dynamic | — |
| Octadecamino | 18 | dynamic | — |
| Nonadecamino | 19 | dynamic | — |
| Icosomino | 20 | dynamic | — |
| **Hippomino** | **varies** | **4-piece** | — |

A random shape is drawn from the selected class each time a new game starts. Larger classes contain many more shapes and therefore a much wider variety of puzzle structures.

**Hippomino** is a special multi-shape mode. Rather than a single polyomino, four separate shapes are placed across a 9×9 grid and your piece must chain through all of them in one continuous knight's tour. See [Hippomino (4-Piece Mode)](#hippomino-4-piece-mode) for full details.

### Clock

Sets a time budget in seconds. `0` means unlimited — an elapsed timer is shown instead of a countdown.

| Range | Increment | Default |
|---|---|---|
| 0 (unlimited) to 300 s | 30 s steps | 0 |

When the clock reaches zero, the game ends immediately as a loss.

### Time Per

Determines whether the clock is shared across the whole game or reset after each individual move.

| Mode | Behaviour |
|---|---|
| **per game** | One shared countdown from start to finish |
| **per move** | Clock resets after every successful move; running out of time on a single move ends the game |

`per move` is the harder setting — it rewards fast pattern recognition and punishes long deliberation.

---

## Shape Library

### Static Shapes (7–15 Cells)

Shapes in the heptomino through pentadecamino classes are drawn from a pre-validated catalogue stored in `tourbus/megalotours/`. Every shape in the catalogue has at least one confirmed knight's tour, and the solution path is available for post-game reveal.

Each shape is identified by a canonical ID in the format `"<size>-<index>"`, for example:
- `"07-043"` — heptomino, index 43
- `"12-22155"` — dodecamino, index 22155
- `"15-29727"` — pentadecamino, index 29727

The index is the shape's position in the size-specific tour dictionary. Zero-padding ensures lexicographic sort order matches catalogue order.

### Dynamic Shapes (16–20 Cells)

For hexadecamino through icosomino, shapes are assembled **on-the-fly** at game start by combining two smaller validated shapes using the `tour_builder` module. Because the combination depends on random placement, a valid tour is not guaranteed — but the construction algorithm is seeded from the component IDs, so the same pair always produces the same result.

Dynamic shapes are identified by a compact codec string rather than a catalogue index:

```
"16-4RH6I-00017"
"18-758NH-2DQJ1"
```

See [Megalomino Codec](#megalomino-codec) for the full format.

---

### Hippomino (4-Piece Mode)

The **Hippomino** class is a unique multi-shape mode that places four independent polyomino shapes across a shared 9×9 grid, then asks you to complete a single Hamiltonian knight's tour visiting every cell of every shape without ever revisiting a square.

**How the board is arranged:**

- The 9×9 grid is divided into four **quadrant slots** at offsets (0, 0), (0, 5), (5, 0), and (5, 5).
- Each slot holds one polyomino shape drawn from the decomino (10-cell) or dodecamino (12-cell) catalogues, limited to shapes that fit within a 4×4 bounding box.
- A one-square gap separates every pair of shapes so they are never orthogonally adjacent.
- The four shapes are chained into a single continuous knight's tour: the last cell of each sub-shape must be a valid knight's move away from the first cell of the next.

**Shape codes for hippomino puzzles** use the format:

```
"mega-<id_1>,<id_2>,<id_3>,<id_4>"
```

For example: `"mega-10-042,12-0103,10-117,12-0821"`

Each ID refers to a shape from the static tour catalogue. The same four-ID combination always reproduces the same puzzle.

---

## How to Play

1. **Configure** your game on the Menu screen: choose board color, shape class, clock, and time mode.
2. Press **start**. A shape is drawn at random from the selected class, placed on the board, and your piece appears at the starting cell.
3. **Click a highlighted cell** to move your piece there. Only knight-move destinations that lie within the polyomino and have not yet been visited are legal.
4. Continue until you have **visited every cell** (win) or you have **no legal moves remaining** (loss).
5. After the game ends, toggle **tour path** to reveal the verified solution sequence.

---

## Square Color Guide

| Color | Meaning |
|---|---|
| Ivory / Tan (alternating) | Unvisited cell — chessboard pattern |
| Light / Dark Blue | Visited cell (light and dark square variants) |
| Light / Dark Red | Cell the piece could not reach (missed — loss only) |
| Highlighted border | Legal move destination |
| Green (tour path overlay) | Solution path sequence numbers |

---

## In-Game Controls

### Mouse

| Action | Effect |
|---|---|
| Click a highlighted legal-move cell | Move your piece there |
| Click a menu `<` / `>` button | Cycle through that setting's values |
| Click any button | Activate that button's action |

### Keyboard Shortcuts

| Key | Context | Action |
|---|---|---|
| `G` | Any | Toggle Move Guide overlay |
| `T` | Any | Toggle Move Track (move numbers) overlay |
| `H` | In-game | Toggle Warnsdorff Degrees hint overlay |
| `P` | In-game / Endgame | Toggle Peek mode (shape thumbnail) |
| `U` | In-game | Undo last move |
| `ESC` | In-game | Resign current game |
| `ESC` | Endgame | Start a new game |
| `M` | Any | Minimise window |

---

## HUD & Overlays

### Move Guide

Displays directional arrows from the current cell to every legal move destination. Useful for quickly scanning the reachable set across an irregular boundary without mentally tracing each L-shape. Toggle with **G** or the *show / hide move guide* button.

### Move Track

Overlays each visited cell with the move number on which it was visited. Helps trace your path history and count how many cells remain. Toggle with **T** or the *show / hide track* button.

### Warnsdorff Degrees

Overlays each legal destination with its **degree** — the number of unvisited cells reachable from that cell after moving there. Prioritising the square with the **lowest non-zero degree** (Warnsdorff's heuristic) is the most effective general-purpose strategy for completing a tour on an irregular shape.

Toggle with **H** (in-game only) or the *show / hide degrees* button.

### Peek Mode

Reveals a miniature thumbnail of the full polyomino in the side panel, showing the complete shape outline and all cell positions. Use this to orient yourself when the shape is large or asymmetric. Toggle with **P** or the *peek / hide* button.

### Tour Path

After a game ends (win or loss), the **toggle tour path** button overlays the verified solution sequence on the board — each cell is numbered in tour order. For dynamic (16–20 cell) shapes, the pre-computed solution derived from the codec seed is shown if one was found; otherwise, the overlay is unavailable.

---

## Endgame & Replay

### Win & Loss Conditions

| Outcome | Condition | Message |
|---|---|---|
| ✅ Win | All cells visited | *tour complete* |
| ❌ Trapped | No legal moves remain with cells unvisited | *no legal moves* |
| ❌ Timeout | Clock expires | *time's up* |
| ❌ Resign | You press resign / ESC | *resigned* |

### Retry

After any endgame the **retry** button replays the exact same shape (same seed) so you can attempt a better route. Retry is available as long as a puzzle seed was recorded.

### Replay Mode

After a game ends, **start replay** enters a step-by-step review. Use:
- **`+`** button (or click) to advance one move forward
- **`-`** button to step one move backward

The board state updates to match each step, making it straightforward to identify where your path diverged from a winning line.

### Undo

While in-game, the **undo last move** button (or **U**) steps back one move at a time. There is no undo limit. The per-move clock resets on undo when playing in `per move` mode.

---

## Share Codes

Every generated game receives a **share code** that encodes the shape identity and settings, allowing you to return to the same puzzle or challenge another player.

- For **static shapes**, the code encodes the shape class, specific shape ID, and board color choice.
- For **dynamic shapes**, the code is the megalomino codec string directly (e.g., `"16-4RH6I-00017"`), which encodes the two component shape IDs and combined size.
- For **hippomino** puzzles, the code uses the format `"mega-<id_1>,<id_2>,<id_3>,<id_4>"`, listing the four component shape IDs in chain order.

**Sharing a puzzle**

1. After starting a game, the share code is displayed in the side panel.
2. Press **copy share code** to copy it to your clipboard.
3. Send the code to a friend.

**Loading a shared puzzle**

1. On the Menu screen, press **enter share code**.
2. Type or paste the code into the input box.
3. Press **start** — the identical shape and configuration is reconstructed.

---

## Statistics

Game results are appended to `megalominoes/megalomino_stats.csv` after each completed game.

| Column | Description |
|---|---|
| `shape_id` | The shape identifier (e.g., `"12-22155"` or `"16-4RH6I-00017"`) |
| `squares_completed` | Number of cells visited before the game ended |

A `squares_completed` value equal to the shape's cell count indicates a successful complete tour. This log can be used to track personal progress across shape classes or identify which shapes you find most difficult.

---

## Advanced Strategy

### Warnsdorff First, Always

Enable **show degrees** (**H**) from the first move. The core principle: prefer the destination with the **lowest non-zero degree**. On a standard chessboard this heuristic produces a valid tour from almost any starting square. On a polyomino — especially one with peninsulas and narrow corridors — it is even more critical, because getting cut off from a small isolated cluster is an immediate loss.

### Parity Awareness

On a chessboard-colored polyomino, count the light and dark squares before you start. If they are unequal, a reentrant (closed) tour is impossible, and the starting cell must be on the majority color for any open tour to succeed. This eliminates roughly half of possible starting positions from consideration immediately.

### Peninsula Priority

Identify any "peninsulas" — narrow arms of the shape with only one or two entry points. These must be visited at specific moments in the tour: too early and you waste your only way in; too late and you cannot reach the exit. The Warnsdorff degree hint naturally flags these (low degree = few exit options), but pattern recognition speeds up the identification considerably.

### Shape Class Progression

Start with **Decomino** (10 cells) or **Undecamino** (11 cells) to build intuition before moving to the much larger catalogues of 12–15 cell shapes. The heptomino and octomino classes have very few tourable shapes, so you will see the same shapes repeatedly — useful for memorisation but limited in variety.

### Dynamic Shape Approach (16–20 Cells)

Dynamic shapes are constructed by joining two smaller shapes at a knight's move. The seam — where the two component shapes meet — is typically the most constrained region. Identify it early (the join point is a knight's move connecting the endpoints of the two sub-tours) and plan your crossing carefully. There is no guaranteed solution, so if no valid tour exists for the constructed shape, you cannot win regardless of play — retry to get a different combination.

### Hippomino Approach (4-Piece Mode)

The hippomino challenge is fundamentally different from single-shape modes: your piece must leap **between four disconnected shapes**, crossing blank space via knight moves to chain them together.

- **Find the seams first.** The four shapes are arranged so that exactly one knight-move leap connects consecutive shapes. Before you start moving, scan the borders of each shape to locate the cells that can jump to another shape — these transition points are your only bridges and must be used at precisely the right moment.
- **Plan the chain order.** The puzzle generator guarantees a valid traversal order through the four quadrants, but you need to honour it. Entering a shape early and exhausting it before establishing an exit is an immediate loss.
- **Treat each shape as a sub-puzzle.** Apply Warnsdorff's heuristic within each shape independently, but reserve the bridge cell (the entry/exit point) for last within each sub-shape.
- **Use the move guide overlay.** Press **G** to toggle directional arrows. On a hippomino board this is especially valuable because legal moves that cross blank squares to reach another shape are easy to miss visually.

### Clock Settings

- Start with `clock = 0` (unlimited) when learning a new shape class.
- `per move` mode at 30–60 seconds is an excellent drill format for shape classes you know well.
- `per game` mode rewards consistency and penalises backtracking into dead reconsideration loops.

---

## Architecture & Technical Notes

### Module Overview

| Module | Role |
|---|---|
| `megalomino_v02.py` | Entry point — pygame init, window setup, main loop |
| `megalomino_controller.py` | Game state machine, shape setup, move logic, rendering, event handling |
| `megalomino_codec.py` | Encodes/decodes dynamic shape IDs into compact share codes |
| `tour_builder.py` | Generates large (16–20 cell) tours by combining two smaller shapes |
| `tour_combiner.py` | Low-level tour combination with constraint validation |
| `megalomino_stats.csv` | Persistent game result log |

Shared infrastructure from `sharedlib/`:

| Module | Role |
|---|---|
| `base_game_controller.py` | Abstract controller: undo stack, replay, clock, codec I/O, button handling |
| `gameboard.py` | `BoardModel` + `BoardRenderer` (pixel↔grid mapping, drawing) |
| `move_hint.py` | Warnsdorff heuristic — `calculate_hint_degrees()` |
| `chess_clock.py` | Countdown and elapsed time clock |
| `uipanel.py` | Layout manager for split left/right panel UI |
| `widgets.py` | `Button` with hover and click detection |

### Tour Catalogue

Static tour data for sizes 7–15 is stored in `tourbus/megalotours/`:

| Module | Content |
|---|---|
| `tours_heptomino.py` | `HEPTOMINO_TOURS` — 2 shapes |
| `tours_octomino.py` | `OCTOMINO_TOURS` — 10 shapes |
| `tours_nonomino.py` | `NONOMINO_TOURS` — 57 shapes |
| `tours_decomino.py` | `DECOMINO_TOURS` — 194 shapes |
| `tours_undecomino.py` | `UNDECOMINO_TOURS` — 617 shapes |
| `tours_dodecomino.py` | `DODECOMINO_TOURS` — 1,580 shapes |
| `tours_tridecomino.py` | `TRIDECOMINO_TOURS` — 4,858 shapes |
| `tours_tetradecomino.py` | `TETRADECOMINO_TOURS` — 13,124 shapes |
| `tours_pentadecomino.py` | `PENTADECOMINO_TOURS` — 43,487 shapes |

Each dictionary maps shape IDs (e.g. `"12-22155"`) to `List[Tuple[int, int]]` — an ordered sequence of (row, col) coordinates representing the verified tour.

### Dynamic Tour Generation (16–20 Cells)

`tour_builder.py` assembles larger shapes at runtime using `DynamicTourProvider` instances, one per size:

```
HEXADECOMINO_PROVIDER  (16 cells)
HEPTADECOMINO_PROVIDER (17 cells)
OCTADECOMINO_PROVIDER  (18 cells)
NONADECOMINO_PROVIDER  (19 cells)
ICOSOMINO_PROVIDER     (20 cells)
```

`build_tour(target_size)` picks a random valid pair `(size_a, size_b)` where `size_a + size_b == target_size` and both sizes have available tour dictionaries (sizes 7–15). It then calls `combine_tours()` from `tour_combiner.py`, which must satisfy five constraints:

1. **Size** — `len(tour_a) + len(tour_b) == target_size`
2. **Knight connectivity** — the first or last cell of one sub-tour must be a valid knight's move from the first or last cell of the other
3. **No overlap** — the two shapes share no cells after placement
4. **Orthogonal adjacency** — at least one cell of each sub-shape must share an edge with a cell of the other (the combined shape is a single connected polyomino)
5. **Coordinate bounds** — no coordinate value (x or y) exceeds 8

`build_tour_from_ids(id_a, id_b)` reconstructs the same tour deterministically from the component IDs using a SHA-256-derived seed, enabling reproducible replay from share codes.

Providers maintain an LRU cache of up to 50 generated tours per size, with a 30% chance of serving a cached tour to improve response time on repeated requests.

### Hippomino Puzzle Generation (4-Piece Mode)

Hippomino puzzles are generated entirely within `megalomino_controller.py` by the `build_megalomino_puzzle()` function.

**Algorithm:**

1. **Candidate pool** — shapes are drawn from the decomino and dodecamino static catalogues, filtered to those whose cells all fall within a 4×4 bounding box (`_get_mega_candidates()`).
2. **Shape selection** — four distinct candidate IDs are sampled at random using the game seed.
3. **Quadrant placement** — each shape is assigned to one of four quadrant slots at offsets (0, 0), (0, 5), (5, 0), (5, 5) on the 9×9 grid. Each slot's shape may be placed in any of up to 8 rotation/reflection variants (`_mega_shape_variants()`), and the tour may run forward or in reverse.
4. **Chain search** — the algorithm tries all valid Hamiltonian traversal orderings through the four slots (`_MEGA_ORDERINGS`), checking that consecutive shapes are connected by a standard knight's move from the exit cell of one to the entry cell of the next.
5. **Result** — on success, the four placed paths are concatenated into a single combined tour and the shape code is returned as `"mega-<id_1>,<id_2>,<id_3>,<id_4>"`.

Up to 200 attempts are made (different random shape selections) before returning `None` and prompting a retry.

**Constraints satisfied:**

| Constraint | Detail |
|---|---|
| Grid bounds | All cells within coordinates 0–8 on both axes |
| No adjacency | Quadrant gaps of one square prevent orthogonal contact between shapes |
| Knight connectivity | Each inter-shape transition is a valid (±1, ±2) or (±2, ±1) knight move |
| Unique cells | Combined tour visits each cell exactly once |

### Megalomino Codec

`megalomino_codec.py` provides a compact, human-readable encoding for dynamic shape pairs.

**Format:** `"<target_size>-<encoded_id_a>-<encoded_id_b>"`

Each component ID is packed into a single integer:

```
value = (size - 7) * 4_000_000 + raw_index
```

This integer is then encoded as a 5-character upper-case base-36 string. The scheme supports sizes 7–15 and indices 0–3,999,999 within each size, and always fits within 5 characters (36⁵ = 60,466,176 > maximum value 35,424,869).

**Examples:**

```python
#>>> encode("09-219", "07-043")
#'16-4RH0B-00017'

#>>> decode("16-4RH0B-00017")
#(16, '09-219', '07-043')

#>>> is_dynamic_code("16-4RH6I-00017")
True
```

`derive_seed(id_a, id_b)` generates a deterministic integer seed from the component IDs using SHA-256, guaranteeing that the same pair always produces the same combined tour.

### Controller Architecture

`MegalominoController` inherits from `BaseGameController` and overrides the eight abstract methods:

| Method | Role |
|---|---|
| `_get_min_board_size()` | Returns 7 (minimum bounding box for any supported shape) |
| `_get_encode_params()` | Packs shape ID, class name, and board color into codec parameters |
| `_validate_codec()` | Decodes a share code or dynamic codec string and applies settings |
| `_game_specific_start_setup()` | Selects a shape, builds or loads its tour, places piece at start cell |
| `_game_specific_make_move()` | Marks cell as visited, advances position, updates legal moves |
| `_validate_move()` | Checks the target is within the polyomino, unvisited, and a legal knight move |
| `_check_endgame_conditions()` | Returns win/loss/timeout state |
| `_capture/_restore_game_state()` | Serialises/deserialises full board state for undo and replay |

`_setup_polyomino()` handles shape normalization, random rotation (0°/90°/180°/270°), and optional horizontal flip — ensuring shapes appear in varied orientations while remaining structurally identical for tour purposes.

---

## Known Limitations

1. **No tour guarantee for dynamic shapes** — hexadecamino through icosomino combinations may occasionally fail to satisfy all five combination constraints; the game falls back to a retry prompt if no valid combination is found within the attempt budget.
2. **No tour guarantee for hippomino** — `build_megalomino_puzzle()` makes up to 200 attempts to chain four shapes; if none succeed, the game falls back to a retry prompt.
3. **Shape catalogue is fixed** — the 7–15 cell catalogues include only shapes with at least one knight's tour; non-tourable shapes are not present and cannot be selected.
4. **No multi-piece support** — each game uses a single knight; alternative fairy pieces are not yet supported for Megalomino (unlike the classic Knight's Tour mode).
5. **Replay memory is unbounded** — very long games accumulate many state snapshots.
6. **Clipboard fallback** — on Linux, clipboard copy may silently fail if `xclip` / `xsel` are not installed.
7. **Dynamic shape tour path reveal** — for 16–20 cell shapes, the post-game tour path overlay requires that `build_tour_from_ids()` succeeds on the same seed; on extremely rare pathological combinations it may return `None` and the overlay will be unavailable.

---

## Credits

Developed by **paw309**.  
Built with [Python](https://www.python.org/) and [pygame](https://www.pygame.org/).  
Tour catalogues derived from exhaustive Hamiltonian path enumeration across all free polyomino shapes of each size class.

---

> **Can you complete the tour — on a board that was never meant to be square?**
