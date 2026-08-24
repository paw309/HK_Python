# ♞ Knight's Turing Machine

> *A Hamiltonian path puzzle where every move transforms your piece — and only the right sequence will let you visit every square.*

**Knight's Turing Machine** (*knightsturing*) is a single-player puzzle game that blends the classic **Knight's Tour** with a simple automaton. Instead of moving one piece throughout the game, you choose a **cycle of 2–4 leapers**. Each time you land on a square, your active piece transforms according to a fixed rule set — either a simple round-robin cycle or a colour-dependent branching scheme. The goal is unchanged: visit every square on the board **exactly once** without retracing your steps.

The catch is that routing decisions must account not just for where you are but for *what piece you will be on the next move* — and the move after that.

Part of the [Hamiltonian Knights](https://github.com/paw309/Hamiltonian-Knights) suite.

---

## Table of Contents

- [The Mathematics](#-the-mathematics)
- [Getting Started](#-getting-started)
- [Game Configuration](#-game-configuration)
  - [Board Size](#board-size)
  - [Piece Cycle (# of Pieces)](#piece-cycle--of-pieces)
  - [Rule Set](#rule-set)
  - [First Square](#first-square)
  - [Clock & Time Per](#clock--time-per)
- [How to Play](#-how-to-play)
- [Piece Cycle & Rule Sets](#-piece-cycle--rule-sets)
  - [Rule Set 1 — Simple Cycle](#rule-set-1--simple-cycle)
  - [Rule Set 2 — Colour-Based Transitions](#rule-set-2--colour-based-transitions)
- [In-Game Controls](#-in-game-controls)
  - [Mouse](#mouse)
  - [Keyboard Shortcuts](#keyboard-shortcuts)
- [HUD & Overlays](#-hud--overlays)
  - [Move Guide](#move-guide)
  - [Move Track](#move-track)
  - [Warnsdorff Degrees](#warnsdorff-degrees)
  - [Peek](#peek)
  - [Reveal Path](#reveal-path)
- [Endgame & Replay](#-endgame--replay)
  - [Win & Loss Conditions](#win--loss-conditions)
  - [Retry](#retry)
  - [Replay Mode](#replay-mode)
  - [Undo](#undo)
- [Share Codes](#-share-codes)
- [Strategy Tips](#-strategy-tips)
- [Piece Roster](#-piece-roster)
- [Architecture & Technical Notes](#-architecture--technical-notes)
- [CLI Runner](#-cli-runner)
- [Known Limitations](#-known-limitations)
- [Credits](#-credits)

---

## ∑ The Mathematics

### Hamiltonian Paths

A **Hamiltonian path** on a graph visits every node exactly once. On an *n × n* board, each square is a node and each legal piece move is a directed edge. Finding a Hamiltonian path in a general graph is NP-complete; on structured boards, however, **Warnsdorff's heuristic** solves most cases in O(*n²*) time.

### Piece Cycling as a Finite Automaton

Knight's Turing Machine adds a twist: the active piece is the *state* of a finite automaton, and each landing square is an *input symbol* (its colour). The automaton reads the board one square at a time and outputs the next piece. This is a minimal model of Turing-machine-style computation applied to a combinatorial path problem.

- In **Rule Set 1** the automaton is a simple counter — the piece cycles through positions A → B → C → … → A regardless of where you land.
- In **Rule Set 2** the automaton branches on square colour — landing on a light square may send you to a different piece than landing on a dark square, creating a colour-sensitive decision tree.

### Why Colour-Bound Pieces Are Included

In a standard Hamiltonian path game a colour-bound piece (one that can only ever reach squares of one colour) cannot complete a full tour alone. In *knightsturing*, colour-bound pieces such as **ferz**, **dabbaba**, **alfil**, and **tripper** *can* appear in the cycle because they are not used on every step — their contribution is interleaved with non-colour-bound pieces, and the overall path can still cover the whole board.

### Warnsdorff's Heuristic

The puzzle generator uses **Warnsdorff's rule** extended to a cycling piece sequence:

> At each step, prefer the unvisited square that gives the *next piece in the cycle* the fewest onward options from that square.

This lookahead-by-one heuristic is highly effective at finding Hamiltonian paths without backtracking and is the same heuristic exposed to the player as the optional **degrees** overlay.

---

## 🚀 Getting Started

### Requirements

- Python 3.7+
- pygame

```bash
pip install pygame
```

### Run the Game

From the repository root:

```bash
python knightsturing/knightsturing_v01.py
```

Or launch from the unified launcher:

```bash
python launcher.py
```

The window opens at your current display resolution and is fully resizable. On Windows the window is automatically maximised.

---

## ⚙ Game Configuration

All settings are adjusted from the **Menu** screen using the `<` and `>` buttons on each row. The board on the right shows a live preview of the *first selected piece* and its legal moves from the highlighted square.

### Board Size

| Setting | Value |
|---|---|
| Minimum | 5 × 5 |
| Maximum | 16 × 16 |
| Default | 8 × 8 |

The engine enforces a per-piece minimum board size: each piece must be able to reach every square of the board from any starting position (verified by BFS). If you select a piece that requires a larger board, an error is shown and the game will not start until the board is enlarged.

### Piece Cycle (# of Pieces)

Three settings interact to define the piece cycle:

- **# of pieces** — how many distinct leapers participate in the cycle (2, 3, or 4).
- **Piece selectors** — N individual piece selector buttons in the right panel, one per cycle slot. Click `<` / `>` on any slot to change that leaper.
- All pieces in the cycle must be **distinct** — duplicates are rejected at start time with an error message.

The piece displayed on the board while in the menu preview is always the **first piece in the cycle**.

### Rule Set

| Value | Behaviour |
|---|---|
| **1** | Simple cycle — piece transforms in strict round-robin order after each move, regardless of square colour |
| **2** | Colour-based transitions — piece transformation depends on the colour (light / dark) of the square you land on |

See [Piece Cycle & Rule Sets](#-piece-cycle--rule-sets) for the full transition tables.

### First Square

| Mode | Behaviour |
|---|---|
| **select** | The board enters a waiting state; click any square to commit it as the starting position |
| **random** | A starting square is chosen automatically by the puzzle generator when you press **start** |

In `random` mode the generator runs a deterministic DFS (with Warnsdorff ordering) to find a start square and complete solution path before you make your first move. This guarantees the puzzle is solvable and enables **peek** and **reveal path** features.

In `select` mode no solution is pre-computed, so peek and reveal are unavailable.

### Clock & Time Per

Two fields work together:

- **clock** — your time budget (`0` = unlimited). Values run from `0` to `5:30` in 30-second steps. When `0`, an elapsed timer is shown rather than a countdown.
- **time per** — whether the budget applies to the whole game or resets after every individual move.

| `time per` | Behaviour |
|---|---|
| **game** | Clock starts on your first move and counts down until the puzzle ends or time expires |
| **move** | Clock resets after every successful move; you must complete each individual move within the budget |

Per-move mode is effective for drilling fast calculation on unfamiliar piece transitions.

---

## 🎮 How to Play

1. **Configure** your game on the Menu screen: choose board size, piece cycle, rule set, first-square mode, and time controls.
2. Press **start** (or click a square on the board if in `select` mode).
3. Your token appears at the starting square. The current active piece is highlighted in the piece panel and labelled on the token itself.
4. Legal moves from the current position are shown as guide arrows (if guide mode is on).
5. **Click a highlighted square** to move there. Only legal moves for the *currently active piece* are accepted.
6. After landing, the active piece transforms according to the rule set. The piece panel updates immediately to show the new active piece.
7. Visited squares are shaded blue. If track mode is on, each square shows the move number on which you landed there.
8. Continue until you have **visited every square** (win) or you are **trapped with no legal moves remaining** (loss).

---

## 🔁 Piece Cycle & Rule Sets

### Rule Set 1 — Simple Cycle

The piece cycles through all selected pieces in order, then repeats:

```
Step  Piece used  →  Piece after landing
  0   A           →  B
  1   B           →  C
  2   C           →  A
  3   A           →  B
  ...
```

With 2 pieces (A, B): A → B → A → B → …  
With 3 pieces (A, B, C): A → B → C → A → …  
With 4 pieces (A, B, C, D): A → B → C → D → A → …  

The transformation is always the same regardless of where you land.

### Rule Set 2 — Colour-Based Transitions

The next piece depends on the **colour** (light = white, dark = black) of the square you land on. The exact rules depend on how many pieces are in the cycle:

**2 pieces (A, B):**

| From | Lands on | Becomes |
|---|---|---|
| A | black | B |
| A | white | B |
| B | any | A |

*(Both colours send A → B; so with 2 pieces, Rule Set 2 is equivalent to Rule Set 1.)*

**3 pieces (A, B, C):**

| From | Lands on | Becomes |
|---|---|---|
| A | black | B |
| A | white | C |
| B | any | A |
| C | any | A |

A is the "hub" — it dispatches to B or C based on colour. B and C always return to A.

**4 pieces (A, B, C, D):**

| From | Lands on | Becomes |
|---|---|---|
| A | black | B |
| A | white | C |
| B | any | D |
| C | any | D |
| D | any | D (no transition) |

D is a **terminal state** — once the piece becomes D it stays D. This means the final stretch of the path is always navigated as piece D, which strongly constrains (and simplifies) the endgame routing. The puzzle is considered solved only when piece D runs out of legal moves after visiting all squares.

> **Tip:** With 4 pieces and Rule Set 2, plan your route so that the D-only endgame covers a connected cluster of remaining squares — D's move set must be compatible with threading the remaining cells.

---

## 🖱 In-Game Controls

### Mouse

| Action | Effect |
|---|---|
| Click a legal-move square (in-game) | Move your piece there |
| Click any square (WAITING state) | Commit that square as your starting position |
| Click `<` / `>` on a menu row | Cycle through that setting's values |
| Click `<` / `>` on a piece selector (right panel) | Change the piece in that cycle slot |
| Click the board in Menu | Reposition the preview piece to see legal moves from that square |
| Click any button | Activate that button's action |

### Keyboard Shortcuts

| Key | Context | Action |
|---|---|---|
| `H` | In-game | Toggle Warnsdorff Degrees hint overlay |

---

## 📊 HUD & Overlays

### Move Guide

Displays directional arrows from the current square to every legal destination for the *current active piece*. The available moves change at every step because the active piece changes. Toggle with the **show move guide** button.

### Move Track

Overlays each visited square with the move number on which you landed there. Useful for counting progress and tracing the path. Toggle with the **show move numbers** button.

### Warnsdorff Degrees

Overlays each legal destination square with its **degree** — the number of unvisited squares reachable from that square by the *next piece in the cycle* (not the current one). This is a one-step lookahead: it shows how constrained you will be on your very next turn if you go there now.

- Toggle with the **show degrees** button or press **`H`** in-game.
- Degrees are recalculated after every move and every undo.
- Lower degrees mean fewer options next turn — visit them first before they become dead ends.
- **Caveat:** The hint is computed one step ahead; it does not account for the full depth of the piece cycle. Two or three steps ahead the landscape can look very different.

### Peek

The **peek** button (available during `random`-mode games) toggles a small **thumbnail overlay** of the full solution path in the side panel. The thumbnail shows every step of the pre-computed Hamiltonian path numbered in order.

Use peek to orient yourself when lost, then hide it again to continue unaided.

### Reveal Path

The **reveal path** button (available during `random`-mode games, in-game and endgame) overlays the full solution path **directly on the board**. Each unvisited square in the solution is outlined in orange and labelled with its step number so you can see exactly where the path goes.

Reveal is the strongest hint available — it shows the complete answer. Use it for learning a new piece combination or to understand why your route failed.

---

## 🏁 Endgame & Replay

### Win & Loss Conditions

| Outcome | Condition | Message |
|---|---|---|
| ✅ Hamiltonian path | All squares visited | *Hamiltonian path complete!* (green) |
| ❌ No moves | No legal moves remain before all squares are visited | *no legal moves* |
| ❌ Timeout | Clock expires | *time's up* |
| ❌ Resign | You press the **resign** button | *resigned* |

### Retry

The **retry** button (available on the endgame screen) replays the **exact same puzzle** — same board size, piece cycle, rule set, and starting square. Use it to try a different route after a dead end.

### Replay Mode

After any game ends, the **start replay** button enters a step-by-step review of your path:

- **`+`** button — advance one step forward
- **`-`** button — step one move backward
- The board, visited squares, move numbers, and active piece display all update to match the selected step.

Use replay to find the move that caused a dead end, or to verify that an earlier branch would have worked.

### Undo

While in-game, **undo last move** steps back one move at a time. There is no undo limit — you can walk all the way back to the starting position. After each undo the active piece reverts to what it was before that move, and the legal moves are recalculated from the restored state. In per-move clock mode the clock resets after each undo.

---

## 🔗 Share Codes

Every game generates a compact **16-character share code** (displayed as four groups of four: `XXXX-XXXX-XXXX-XXXX`) that captures the complete puzzle configuration. The code is base-32 encoded and packs 80 bits:

| Field | Bits | Description |
|---|---|---|
| version | 4 | Codec version (always 1) |
| board size | 4 | Board dimension offset from 5 |
| first square | 1 | `select` or `random` |
| # of pieces | 2 | Cycle length offset from 2 (supports 2–4) |
| rule set | 1 | Rule Set 1 or 2 |
| clock index | 4 | Index into the clock-value list |
| time per | 1 | `game` or `move` |
| piece 0–3 index | 4 × 4 | Index into the 10-piece roster for each cycle slot |
| start row | 4 | Starting row (0 in `select` mode) |
| start col | 4 | Starting column (0 in `select` mode) |
| seed | 39 | RNG seed for puzzle generation |

**Sharing a puzzle:**

1. Start a game — the share code is shown in the side panel.
2. Press **copy share code** to copy it to the clipboard.
3. Send the code to another player.

**Loading a shared puzzle:**

1. On the Menu screen, press **enter share code**.
2. Type or paste the 16-character code (dashes are ignored).
3. All settings — board size, piece cycle, rule set, clock, and starting square — are restored automatically.
4. Press **start** to play the same puzzle.

---

## 🧠 Strategy Tips

### Start With the Rarest Piece

Identify which piece in your cycle has the fewest onward options from most squares. That piece is your bottleneck. Plan your route to ensure it always has a clear onward path when its turn comes around in the cycle.

### Think N Steps Ahead

With a 3-piece cycle, your move now determines what piece you will use on step +3, +6, +9, … Plan in blocks that align with the cycle length rather than one move at a time.

### Use Degrees as a Filter, Not a Rule

The Warnsdorff degrees show your options *one step ahead*. A square with degree 1 is almost always a must-visit-next emergency. A square with degree 0 means you are already stuck. But identical degrees do not mean identical futures — look at the board geometry as well.

### Rule Set 2 with 4 Pieces: Protect Your D Squares

Once the active piece becomes D (the terminal state), it stays D. Work out early which squares piece D can reach from the expected final cluster, and reserve a connected block of unvisited squares for the D-only endgame.

### Colour-Bound Pieces Need Pairing

Pieces like **ferz** (diagonal only, always same colour) or **tripper** (3,3 diagonal) can only reach half the board on their own. When they appear in your cycle, ensure the adjacent steps in the cycle use a piece that covers the *opposite colour* so that collectively the full board is accessible.

### Clock Mode Selection

- **Unlimited (clock = 0):** Recommended when learning a new piece combination or rule set.
- **Per-game:** Adds time pressure without penalising individual slow moves.
- **Per-move:** Punishing — one slow move ends the game. Best for drilling a specific piece transition you have already mastered.

---

## ♟ Piece Roster

The game uses exactly **10 leapers** drawn from the shared `piecekeeper` library. All 10 can appear in a piece cycle, including colour-bound pieces (marked †):

| Piece | Jump vector | Notes |
|---|---|---|
| **knight** | (2, 1) | The classic L-shape |
| **wazir** | (1, 0) | One square orthogonally |
| **ferz** † | (1, 1) | One square diagonally; colour-bound |
| **dabbaba** † | (2, 0) | Two squares orthogonally; colour-bound |
| **alfil** † | (2, 2) | Two squares diagonally; colour-bound |
| **threeleaper** | (3, 0) | Three squares orthogonally |
| **tripper** † | (3, 3) | Three squares diagonally; colour-bound |
| **camel** | (1, 3) | Longer variant of the knight |
| **zebra** | (2, 3) | (2, 3) leaper |
| **giraffe** | (1, 4) | (1, 4) leaper |

*† Colour-bound pieces can only reach squares of one colour when used alone. In a cycling rule set they can still contribute to a full Hamiltonian path.*

The minimum board size required for each piece is checked at game start. Pieces that cannot reach every square of the selected board (by BFS from any corner) will trigger a "need board ≥ N" error.

---

## 🏗 Architecture & Technical Notes

The game is split into five focused modules:

| Module | Role |
|---|---|
| `knightsturing_v01.py` | Entry point — pygame init, window setup, main game loop |
| `knightsturing_controller.py` | Game state machine, move logic, rendering, event handling |
| `knightsturing_generator.py` | DFS + Warnsdorff puzzle generator |
| `turing_engine.py` | Rule set definitions and single-path simulation |
| `turing_runner.py` | CLI exhaustive permutation tester (offline research tool) |

### Generator (`knightsturing_generator.py`)

`generate_puzzle()` finds a Hamiltonian path for the given board size, piece cycle, and rule set:

1. **Start square selection** — squares are tried in order starting from `seed % n²`, wrapping around.
2. **DFS with Warnsdorff ordering** — at each step, legal moves for the current piece are sorted by the degree of the *next piece* from that square (ascending), then by position for determinism.
3. **Deadline** — the whole search is bounded by a 10-second wall-clock limit; if no path is found, `generate_puzzle()` returns `None` and the game displays an error.

The path returned is a list of `(row, col, piece_to_use_next)` tuples of length *n²*. The piece stored at position *i* is the piece that will be active when the player stands on square *i*, i.e. the piece that will be used to make the move *from* that square.

### Rule Engine (`turing_engine.py`)

`TuringRule` represents a single transformation: *from_piece* + optional *colour condition* → *to_piece*.  
`RuleSet` holds a list of rules and exposes `apply(piece, row, col)` which returns the next piece by matching the first applicable rule.

Two factory functions build the two rule sets:

- `build_ruleset1(pieces)` — one rule per piece, no colour condition.
- `build_ruleset2(pieces)` — 2–4 colour-sensitive rules depending on cycle length.

### Controller Architecture (`knightsturing_controller.py`)

`KnightsTuringController` inherits from `BaseGameController` and implements eight abstract methods:

| Method | Purpose |
|---|---|
| `_get_min_board_size()` | Returns the maximum minimum board size across all selected pieces |
| `_get_encode_params()` | Not used — the codec is fully custom |
| `_validate_codec()` | Decodes a 16-char share code and applies all settings |
| `_game_specific_start_setup()` | Builds the rule set, runs the generator, and sets the start state |
| `_game_specific_make_move()` | Applies the rule set transformation after each landing |
| `_validate_move()` | Checks the clicked square against the current legal-moves list |
| `_check_endgame_conditions()` | Detects full board coverage or no-move stalemate |
| `_capture_game_state()` / `_restore_game_state()` | Snapshots and restores position, visited set, move count, and active piece for undo/replay |

All UI infrastructure (panels, buttons, clock, codec input, error overlays, clipboard) is inherited from `BaseGameController`.

### Codec

The 80-bit payload is packed into 10 bytes, base-32 encoded to 16 characters, and grouped as `XXXX-XXXX-XXXX-XXXX`. The version nibble (bits 79–76) is set to `1`; codes with any other version are rejected by the decoder.

### State Snapshots

After every move (and at game start), `_capture_game_state()` records:

- `pos` — current player position
- `visited` — set of all visited squares
- `visited_moves` — dict mapping square → move number
- `move_count` — integer move counter
- `current_piece` — active piece name

This list powers both the unlimited undo stack and the post-game step-through replay.

---

## 🖥 CLI Runner

`turing_runner.py` is an offline research tool for exploring which piece combinations produce valid Hamiltonian paths:

```bash
python knightsturing/turing_runner.py
```

It prompts for four parameters:

| Parameter | Range | Description |
|---|---|---|
| Board size | 5–16 | Side length of the square board |
| Number of pieces | 2, 3, 4 | Cycle length |
| Target length | 5–255 | Path length to count as a "hit" |
| Rule set | 1, 2 | Rule set to apply |

The runner exhaustively tests every ordered permutation P(*pool*, *k*) from the full leaper pool, running 1,000 simulation attempts per permutation. Each attempt alternates between a random walk and a Warnsdorff-guided walk. Permutations that produce at least one path that **genuinely halts** at the target length (piece has no legal moves remaining at exactly the target step) are printed and saved as a JSON file.

The JSON output includes the piece sequence, exact path count, rule descriptions, and the (column, row) coordinate sequences for all qualifying paths — useful for visualising which board regions the different cycles tend to traverse.

---

## ⚠ Known Limitations

1. **Generator may fail** — for unusual piece combinations or small boards, the 10-second DFS budget may expire without finding a Hamiltonian path. Choose a different piece combination or a larger board.
2. **No backtracking in generator** — the Warnsdorff heuristic is greedy; it does not exhaustively explore all branches. A path may exist that the generator misses within the time budget.
3. **Select mode has no guarantee** — when `first square = select`, no solution path is computed in advance. There is no guarantee that a Hamiltonian path exists from your chosen starting square with the current piece cycle. Peek and reveal are unavailable.
4. **Replay memory is unbounded** — very long games on large boards (e.g. 16×16 = 256 moves) accumulate many state snapshots.
5. **Clipboard fallback** — on Linux, clipboard copy may silently fail if `xclip` or `xsel` are not installed.
6. **Minimum board size is a hard floor** — the BFS reachability check used for the minimum board size is a necessary but not sufficient condition for a Hamiltonian path to exist. A piece may pass the BFS check but still fail to complete a full tour on a specific board and cycle.

---

## Credits

Developed by **paw309**.  
Built with [Python](https://www.python.org/) and [pygame](https://www.pygame.org/).  
Warnsdorff's heuristic described by H. C. von Warnsdorff (1823).  
Fairy chess piece definitions from the *Piececlopedia* and *The Classified Encyclopedia of Chess Variants*.

---

> *Every square, every piece — in the right order.*
