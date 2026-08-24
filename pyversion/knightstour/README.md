# ♞ Knight's Tour & Knight's Trap

> *The original and its competitive counterpart.*

This document covers two related games from the [Hamiltonian Knights](https://github.com/paw309/Hamiltonian-Knights) suite:

- **Knight's Tour** — a single-player puzzle: visit every square on the board exactly once.
- **Knight's Trap** — a two-player competitive game: trap your opponent before they trap you.

Both games use the same piece library and share the same core concepts of Hamiltonian paths and Warnsdorff's heuristic.

---

## Table of Contents

### Knight's Tour
- [The Mathematics](#-the-mathematics)
- [Getting Started — Knight's Tour](#-getting-started--knights-tour)
- [Game Configuration — Knight's Tour](#-game-configuration--knights-tour)
  - [Board Size (Tour)](#board-size-tour)
  - [Piece Selection (Tour)](#piece-selection-tour)
  - [First Square (Tour)](#first-square-tour)
  - [Clock & Time Per (Tour)](#clock--time-per-tour)
- [How to Play — Knight's Tour](#-how-to-play--knights-tour)
- [Open vs. Closed Tours](#-open-vs-closed-tours)
- [In-Game Controls — Knight's Tour](#-in-game-controls--knights-tour)
  - [Mouse (Tour)](#mouse-tour)
  - [Keyboard Shortcuts (Tour)](#keyboard-shortcuts-tour)
- [HUD & Overlays — Knight's Tour](#-hud--overlays--knights-tour)
  - [Move Guide (Tour)](#move-guide-tour)
  - [Move Track](#move-track)
  - [Warnsdorff Degrees (Tour)](#warnsdorff-degrees-tour)
- [Endgame & Replay — Knight's Tour](#-endgame--replay--knights-tour)
  - [Win & Loss Conditions (Tour)](#win--loss-conditions-tour)
  - [Retry (Tour)](#retry-tour)
  - [Replay Mode (Tour)](#replay-mode-tour)
  - [Undo (Tour)](#undo-tour)
- [Share Codes — Knight's Tour](#-share-codes--knights-tour)
- [Advanced Strategy — Knight's Tour](#-advanced-strategy--knights-tour)
- [Piece Library](#-piece-library)
- [Architecture & Technical Notes — Knight's Tour](#-architecture--technical-notes--knights-tour)
- [Known Limitations — Knight's Tour](#-known-limitations--knights-tour)

### Knight's Trap
- [Overview — Knight's Trap](#-overview--knights-trap)
- [Getting Started — Knight's Trap](#-getting-started--knights-trap)
- [Game Configuration — Knight's Trap](#-game-configuration--knights-trap)
  - [Board Size (Trap)](#board-size-trap)
  - [Piece Selection (Trap)](#piece-selection-trap)
  - [Player One](#player-one)
  - [First Square (Trap)](#first-square-trap)
  - [Opponent Level](#opponent-level)
  - [Clock & Time Per (Trap)](#clock--time-per-trap)
- [How to Play — Knight's Trap](#-how-to-play--knights-trap)
  - [Start Squares](#start-squares)
  - [Taking Turns](#taking-turns)
  - [Winning and Losing](#winning-and-losing)
- [Square Color Guide](#-square-color-guide)
- [In-Game Controls — Knight's Trap](#-in-game-controls--knights-trap)
  - [Mouse (Trap)](#mouse-trap)
  - [Keyboard Shortcuts (Trap)](#keyboard-shortcuts-trap)
- [HUD & Overlays — Knight's Trap](#-hud--overlays--knights-trap)
  - [Move Guide (Trap)](#move-guide-trap)
  - [Warnsdorff Degrees (Trap)](#warnsdorff-degrees-trap)
- [Endgame & Replay — Knight's Trap](#-endgame--replay--knights-trap)
  - [Win & Loss Conditions (Trap)](#win--loss-conditions-trap)
  - [Retry (Trap)](#retry-trap)
  - [Undo (Trap)](#undo-trap)
  - [Replay Mode (Trap)](#replay-mode-trap)
- [Share Codes — Knight's Trap](#-share-codes--knights-trap)
- [Bot AI](#-bot-ai)
  - [Level 1 — Random](#level-1--random)
  - [Level 2 — Dead-End Avoidance](#level-2--dead-end-avoidance)
  - [Level 3 — Warnsdorff's Rule](#level-3--warnsdorffs-rule)
  - [Level 4 — Multi-Heuristic](#level-4--multi-heuristic)
  - [Level 5 — Opponent Modeling](#level-5--opponent-modeling)
- [Advanced Strategy — Knight's Trap](#-advanced-strategy--knights-trap)
- [Architecture & Technical Notes — Knight's Trap](#-architecture--technical-notes--knights-trap)
- [Known Limitations — Knight's Trap](#-known-limitations--knights-trap)

### Shared
- [Credits](#-credits)

---

---

# ♞ Knight's Tour

> *The original. Visit every square on the board exactly once.*

**Knight's Tour** is a single-player puzzle game based on one of the oldest and most studied problems in recreational mathematics. Guide your chosen chess piece across an *n × n* board, visiting every square **exactly once** without retracing your steps. The game uses **Warnsdorff's heuristic** both to generate preview tours in the menu and to power an optional hint overlay during play — but following the hint blindly is no guarantee of success.

---

## ∑ The Mathematics

The **Knight's Tour** is the classic example of a **Hamiltonian path** problem on a graph: given a graph where nodes are board squares and edges connect squares reachable in one legal move, find a path that visits every node exactly once.

Two classes of solution exist:

- **Open tour** — the knight visits all *n²* squares but the final square is not a legal move away from the first. The path is a Hamiltonian *path*.
- **Closed (reentrant) tour** — the final square is exactly one legal move from the starting square, forming a Hamiltonian *cycle*. These are rarer and generally considered a higher achievement.

### Warnsdorff's Heuristic

The engine uses **Warnsdorff's rule** to generate tours and power the optional in-game hint overlay:

> At each step, move to the unvisited square that has the **fewest onward moves** (the lowest *degree*) from that position.

This greedy heuristic is highly effective on boards of 5×5 and larger — it finds complete tours almost every time in O(*n²*) steps, with no backtracking. The game enhances it slightly by **dynamically decrementing neighbor exit values** after each step, injecting variety across repeated plays.

### Why Some Pieces Are Excluded

Color-bound pieces — **bishop**, **ferz**, **dabbaba**, **alfil**, and **camel** — are excluded from Knight's Tour. These pieces can only ever reach squares of one color parity, making a full Hamiltonian path on a standard board mathematically impossible.

---

## 🚀 Getting Started — Knight's Tour

### Requirements

- Python 3.7+
- pygame

```bash
pip install pygame
```

### Run the Game

From the repository root:

```bash
python knightstour/knightstour_v02.py
```

Alternatively, launch it from the unified launcher:

```bash
python launcher.py
```

The window opens at your current display resolution and is fully resizable. On Windows the window is automatically maximised.

---

## ⚙ Game Configuration — Knight's Tour

All settings are adjusted from the **Menu** screen using the `<` and `>` buttons on each row. The board on the right updates live as you change settings, showing a preview of the piece and its legal moves.

### Board Size (Tour)

| Setting | Value |
|---|---|
| Minimum | 5 × 5 |
| Maximum | 16 × 16 |
| Default | 8 × 8 |

Larger boards create longer, more complex tours. The knight requires a minimum of 5×5; some exotic pieces require more room and will display a warning if selected on too small a board.

> **Tip:** Corner and edge starting squares are significantly harder than central squares — the fewer onward moves you have at the start, the harder it is to avoid dead ends deep into the tour.

### Piece Selection (Tour)

Any piece in the shared `piecekeeper` library can be used — provided it is not color-bound. This includes:

| Category | Examples |
|---|---|
| Standard chess | Knight, King, Queen, Rook |
| Short-range leapers | Wazir |
| Medium-range leapers | Zebra (2,3), Giraffe (1,4), Antelope (3,4) |
| Compound (Greek) | Gamma, Sigma, Phi, Psi, Omega |
| Planetary / Zodiac | Aries, Gemini, Virgo, Scorpio, etc. |
| Special | Fibonacci, Gunkan |

Substituting the knight for an exotic piece completely changes the parity landscape, the routing logic, and the tour's visual shape. The menu preview shows the selected piece's legal moves from the centre of the current board size so you can check connectivity before starting.

### First Square (Tour)

| Mode | Behaviour |
|---|---|
| **select** | The board enters a waiting state; click any square to commit as the starting position |
| **random** | A random starting square is chosen automatically when you press **start** |

`select` mode is recommended for experienced players who know that starting position matters. `random` is faster for casual play.

### Clock & Time Per (Tour)

Two fields work together:

- **clock** — your total time budget (`0` = unlimited). Values run from 0 to 330 seconds in 30-second increments. When `0`, an elapsed timer is shown instead of a countdown.
- **time per** — whether the budget applies to the whole game or resets after every individual move.

| `time per` | Behaviour |
|---|---|
| **game** | Clock starts on your first move and counts down until the tour ends or time expires |
| **move** | Clock resets after every successful move; you must complete each individual move within the budget |

Per-move mode is excellent for drilling fast pattern recognition on specific pieces.

---

## 🎮 How to Play — Knight's Tour

1. **Configure** your game on the Menu screen: choose piece, board size, starting square mode, and time controls.
2. Press **start** (or click a square if in `select` mode).
3. The board displays your piece at the starting square. All legal moves from that position are highlighted with guide arrows (if guide mode is on).
4. **Click a highlighted square** to move there. Only legal moves for your chosen piece are accepted; clicking any other square has no effect.
5. Each visited square is shaded blue and (if track mode is on) numbered with the move on which you landed there.
6. Continue until you have **visited every square** (win) or you are **trapped with no legal moves remaining** (loss).

---

## 🔄 Open vs. Closed Tours

After completing a full tour the game immediately checks whether the tour is **closed**:

- The final square must be exactly **one legal move** away from the starting square.
- A closed tour is displayed with a **green** completion message and is considered a more prestigious result.
- An open tour is displayed with a **brown** message.
- Both are tracked separately in the endgame display.

Closed tours are rarer and harder to achieve intentionally — on an 8×8 knight board roughly half of all complete tours are reentrant, but on exotic pieces this fraction varies considerably.

---

## 🖱 In-Game Controls — Knight's Tour

### Mouse (Tour)

| Action | Effect |
|---|---|
| Click a legal-move square (in-game) | Move your piece there |
| Click any square (WAITING state) | Commit that square as your starting position |
| Click a menu `<` / `>` button | Cycle through that setting's values |
| Click the board in Menu | Reposition the preview piece to see legal moves from that square |
| Click any button | Activate that button's action |

### Keyboard Shortcuts (Tour)

| Key | Context | Action |
|---|---|---|
| `H` | In-game | Toggle Warnsdorff Degrees hint overlay |

---

## 📊 HUD & Overlays — Knight's Tour

### Move Guide (Tour)

Displays directional arrows from the current square to every legal destination. Useful for quickly scanning available options without hunting across the board. Toggle with the **show / hide move guide** button (available in all game states including the menu preview).

### Move Track

Overlays each visited square with the move number on which you landed there. Helps you retrace your path and count progress. Toggle with the **show / hide move #'s** button (always available).

### Warnsdorff Degrees (Tour)

Overlays each legal destination square with its **degree** — the number of unvisited squares reachable from that square after moving there. Lower-degree squares become dead ends sooner; the heuristic says to visit them first.

- Toggle with the **show / hide degrees** button or press **`H`** in-game.
- Hint degrees are recalculated automatically after every move and after every undo.
- **Warning:** the hint is useful but not infallible. Low-degree squares near the board edge can trap you if you follow the heuristic too rigidly without considering the global structure of the remaining board.

---

## 🏁 Endgame & Replay — Knight's Tour

### Win & Loss Conditions (Tour)

| Outcome | Condition | Message |
|---|---|---|
| ✅ Closed tour | All squares visited; last square one move from first | *closed tour complete* (green) |
| ✅ Open tour | All squares visited; last square not reachable from first | *open tour complete* (brown) |
| ❌ No moves | No legal moves remain before all squares are visited | *no legal moves* |
| ❌ Timeout | Clock expires | *time's up* |
| ❌ Resign | You press the **resign** button | *resigned* |

### Retry (Tour)

The **retry** button (available in the endgame screen) replays the **exact same puzzle** — same board size, piece, and starting square — so you can attempt a better route. Available as long as the puzzle seed was recorded (all normally-started games have a seed).

### Replay Mode (Tour)

After any game ends, the **start replay** button enters a step-by-step review of your game:

- **`+`** button — advance one step forward
- **`-`** button — step one move backward
- The board, visited squares, and move numbers all update to match the selected step.

Use replay to analyse where you went wrong, identify the move that forced the dead end, or confirm whether a closed tour was possible from your route.

### Undo (Tour)

While in-game, the **undo last move** button steps back one move at a time. There is no undo limit — you can walk all the way back to the starting position. When in per-move clock mode, the clock resets after an undo. The undo stack is built from the same snapshot system used by replay.

---

## 🔗 Share Codes — Knight's Tour

Every game generates a compact **16-character share code** (base-32 encoded) that captures:

- Board size
- First square mode
- Clock setting

**Sharing a puzzle**

1. After starting a game the share code is shown in the side panel.
2. Press **copy share code** to copy it to your clipboard.
3. Send the code to another player.

**Loading a shared puzzle**

1. On the Menu screen, press **enter share code**.
2. Type or paste the 16-character code.
3. Press **start** — the same configuration is restored and the same starting square is generated.

---

## 🧠 Advanced Strategy — Knight's Tour

### Starting Square Matters

Not all squares are equal. On a standard 8×8 knight board:

- **Corner squares** (a1, h1, a8, h8) have only 2 legal knight moves — the hardest start.
- **Near-edge squares** have 3–4 moves — still restrictive.
- **Central squares** have up to 8 moves — far more flexibility.

If you are learning, start in the centre. If you want a challenge, start in a corner.

### Read the Warnsdorff Numbers

Enable **show degrees** before your first move to see the full exit-value landscape from the start. This gives you a map of which regions will become critical before you've committed to anything.

Key rules of thumb:
- Prioritise low-degree squares in **isolated regions** (corners, near-filled clusters) before they become unreachable.
- A degree of **1** is an emergency — visit it next or it becomes a dead end forever.
- A degree of **0** on a *not-yet-visited* square means you are already stuck.

### Following Warnsdorff Is Not Always Enough

The heuristic is local. It does not account for:
- **Global board topology** — a low-degree square might sit in a cluster of other low-degree squares; visiting one may strand the others.
- **Bridge squares** — some squares are the only connection between two board regions; visiting the wrong side first can isolate one half.
- **Closed tour feasibility** — if you want a closed tour, you need to manage the final approach from the first move. Pure Warnsdorff does not guarantee closure.

### Piece-Specific Tips

| Piece | Tip |
|---|---|
| **Knight** | The classic. Long-range enough to cross the board but non-linear enough to surprise. Study the corner patterns. |
| **King** | Very short range — essentially a graph-connectivity problem. Stick to spiral or boustrophedon patterns. |
| **Rook** | Long but axis-restricted. Think in rows and columns; sweep systematically. |
| **Queen** | High mobility creates many options per turn but makes planning harder. Start with Warnsdorff strictly. |
| **Zebra (2,3)** | Jumps further than a knight. The board looks sparse — remember that unreachable-looking squares may be reachable in two steps. |
| **Exotic pieces** | Study the legal moves from the menu preview before starting. Unfamiliar jump patterns are the main difficulty. |

### Clock Modes

- Start with **clock = 0** (unlimited) when learning a new piece or board size.
- **Per-game** clock rewards overall efficiency — you have time to think through critical junctions but must keep moving.
- **Per-move** clock rewards fast local pattern recognition. It is punishing: a single slow move can end an otherwise perfect game.

---

## ♟ Piece Library

The game draws from the shared `piecekeeper` library. The following pieces are valid for Knight's Tour (color-bound pieces are excluded):

### Standard Chess
| Piece | Movement |
|---|---|
| Knight | (2,1) leaper — the classic L-shape |
| King | One square in any of 8 directions |
| Rook | Unlimited orthogonal (slider) |
| Queen | Unlimited orthogonal + diagonal (slider) |

### Short-Range Leapers
| Piece | Movement |
|---|---|
| Wazir | (1,0) — one square orthogonally |

### Medium-Range Leapers
| Piece | Movement |
|---|---|
| Zebra | (2,3) leaper |
| Giraffe | (1,4) leaper |
| Antelope | (3,4) leaper |
| Gazelle | (2,5) leaper |
| Flamingo | (1,6) leaper |

### Compound Pieces (Greek / Planetary)
Gamma, Delta, Theta, Lambda, Xi, Pi, Sigma, Phi, Psi, Omega — combinations of two leaper types.

### Zodiac & Multi-Range
Aries, Gemini, Virgo, Libra, Scorpio, Sagittarius, Capricorn, Aquarius, Pisces.

### Special
| Piece | Movement |
|---|---|
| Fibonacci | Leaps at distances 1, 2, 3, 5, 8, 13 (Fibonacci sequence) |
| Gunkan | All (r,s) leaps where gcd(r,s) = 1 (all coprime jumps) |

> Pieces marked as color-bound (bishop, ferz, dabbaba, alfil, camel) are automatically excluded from the piece selector because they cannot complete a Hamiltonian path.

---

## 🏗 Architecture & Technical Notes — Knight's Tour

The game is split into three focused modules:

| Module | Role |
|---|---|
| `knightstour_v02.py` | Entry point — pygame init, window setup, main game loop |
| `knightstour_controller.py` | Game state machine, move logic, rendering, event handling |
| `knights_tour_logic.py` | Warnsdorff tour solver used for menu previews and hint degrees |

### Tour Solver (`knights_tour_logic.py`)

The `KnightsTour` class implements a randomised Warnsdorff solver:

1. **Initialise exit values** — for every square, count how many valid knight moves it has.
2. **Pick start** — random or caller-supplied.
3. **Iterate** — at each step, collect all unvisited reachable squares; sort by exit value; pick randomly among the minimum; move there.
4. **Decrement neighbors** — after each step, decrement exit values of unvisited neighbors to reflect the reduction in future onward options. This adds variety and improves tour completion rates.
5. **Terminate** — when no onward moves exist (complete tour or dead end).

The same `KnightsTour` class is used to draw the live tour preview thumbnail in the side panel during peek mode.

### Controller Architecture (`knightstour_controller.py`)

`TourController` inherits from `BaseGameController` and implements eight abstract methods:

| Method | Purpose |
|---|---|
| `_get_min_board_size()` | Returns minimum board size for the selected piece |
| `_get_encode_params()` | Supplies parameters for share code generation |
| `_validate_codec()` | Decodes a share code and applies settings |
| `_game_specific_start_setup()` | Initialises board, solver, and starting position |
| `_game_specific_make_move()` | Increments move counter |
| `_validate_move()` | Checks whether the clicked square is in `self.legal_moves` |
| `_check_endgame_conditions()` | Detects full tour completion or dead end |
| `_capture_game_state()` / `_restore_game_state()` | Snapshots and restores state for undo/replay |

All UI infrastructure (panels, buttons, clock, codec input, error overlays, clipboard) is inherited from `BaseGameController`.

### Two-Phase Start (Select Mode)

When `first square = select`:

1. `start_game()` initialises the solver and transitions to `GameState.WAITING`.
2. The board renders with a "click a square to start" overlay.
3. When the player clicks, `commit_start_square()` sets the starting position, initialises visited/move state, starts the clock, and transitions to `GameState.INGAME`.

### Codec Schema

Settings are packed into a 16-character base-32 share code:

| Field | Bits | Values |
|---|---|---|
| board | 4 | 5–16 |
| first_square | 1 | select / random |
| clock | 6 | 0–30 minutes |

The RNG seed is embedded in the remaining bits.

### State Snapshots

After every move (and at game start), `_capture_game_state()` stores:
- `pos` — current player position
- `visited` — set of all visited squares
- `visited_moves` — dict mapping square → move number
- `move_count` — integer move counter

This snapshot list powers both the unlimited undo stack and the post-game step-through replay with zero additional diffing logic.

---

## ⚠ Known Limitations — Knight's Tour

1. **Warnsdorff solver is probabilistic** — on very small boards (5×5, 6×6) or with exotic pieces, `find_tour()` may occasionally return a partial path rather than a complete tour. The preview thumbnail will show a partial-tour warning in this case.
2. **No backtracking in solver** — the heuristic solver does not backtrack; it is fast but not exhaustive. A complete tour is not guaranteed for every piece/board/start combination.
3. **Replay memory is unbounded** — very long games on large boards accumulate many state snapshots.
4. **Clipboard fallback** — on Linux, clipboard copy may silently fail if `xclip` or `xsel` are not installed.
5. **No difficulty calibration per piece** — the minimum board size check uses a fixed lookup table; exotic pieces may be impossible to tour on boards only slightly above the minimum.

---

---

# ♞♟ Knight's Trap

> *Trap your opponent. Preserve your mobility. Can you outlast them?*

**Knight's Trap** is a two-player competitive knight's tour game. Both players alternate moves on a shared board, each building their own path from their chosen starting square. A player is **trapped** — and loses — when they have no legal moves remaining. The player who visits more squares wins.

This is a combinatorial strategy game with deep connections to graph theory. Forcing your opponent into a dead end while preserving your own mobility is the core tension. Experienced players will recognise parallels to **Nim**, **Snort**, and other combinatorial games on graphs.

---

## 🔍 Overview — Knight's Trap

Two players share a single board and move the same type of chess piece. On each turn the active player steps to any legal, unvisited square. Squares already visited by **either** player are permanently off-limits — the shared history is what makes this adversarial.

The game ends when a player has no legal moves. That player loses. If both players are trapped simultaneously (they each run out of moves on the same turn), the player with more visited squares wins.

Key tensions:
- **Mobility preservation** — staying mobile is survival; every move permanently removes options from the board.
- **Interference** — cutting across your opponent's likely path can trap them early.
- **Piece knowledge** — different pieces create radically different connectivity graphs; the right instinct for a knight does not transfer directly to a camel or a king.

---

## 🚀 Getting Started — Knight's Trap

**Requirements**

- Python 3.7 or later
- pygame (`pip install pygame`)
- The full `Hamiltonian-Knights` repository (shared libraries are loaded from `sharedlib/`)

**Run the game**

```bash
cd Hamiltonian-Knights
python knightstrap/knightstrap_v01.py
```

The window opens at your current display resolution and is fully resizable. On Windows the window is automatically maximised.

---

## ⚙ Game Configuration — Knight's Trap

All settings are adjusted from the **Menu** screen using the `<` and `>` buttons on each row.

### Board Size (Trap)

| Setting | Range | Default |
|---|---|---|
| Board | 5 × 5 to 16 × 16 | 8 × 8 |

Larger boards give both players more room but also make it easier for the opponent to maintain mobility. Small boards (5 × 5 to 7 × 7) produce short, intense games where a single misstep is fatal.

### Piece Selection (Trap)

Both players move the same piece type, drawn from the `piecekeeper` module. Even-parity pieces (bishop, delta, theta, lambda, xi) are excluded because their color-binding prevents them from visiting every square on a standard board.

All remaining piece types are available, including:
- **Standard**: knight, rook, queen, king, and variants
- **Short-range leapers**: wazir, dabbaba
- **Medium-range leapers**: camel, zebra, giraffe, antelope, gazelle, flamingo
- **Compound / Planetary**: gamma, sigma, phi, psi, omega, and more
- **Zodiac and multi-range**: aries, gemini, virgo, libra, scorpio, and more
- **Special**: fibonacci, gunkan

Each piece defines its own legal move set, which fundamentally changes the connectivity of the board and therefore the entire strategic character of the game.

### Player One

| Choice | Meaning |
|---|---|
| **human** | You play as Player 1 (Blue) against the bot (Red) |
| **bot** | The bot plays both sides (demonstration / watch mode) |

In a standard game, set this to `human`.

### First Square (Trap)

| Choice | Meaning |
|---|---|
| **select** | Both players choose their own starting square by clicking the board |
| **random** | Starting squares are placed randomly at game start |

`select` mode allows both players to compete for advantageous starting positions. Central squares generally offer more onward mobility, but placing too close to the opponent can backfire.

### Opponent Level

Sets the bot AI difficulty from 1 (easiest) to 5 (hardest). See [Bot AI](#-bot-ai) for a full description of each level's strategy.

| Level | Strategy summary |
|---|---|
| 1 | Random legal move |
| 2 | Avoids dead-end squares |
| 3 | Warnsdorff's rule + dead-end avoidance |
| 4 | Warnsdorff + two-ply lookahead + center proximity |
| 5 | All of Level 4 + opponent modeling (minimise your options) |

### Clock & Time Per (Trap)

Two fields work together to configure the time control:

- **clock** — time budget in seconds (`0` = unlimited). Values range from 0 to 330 seconds in 30-second increments.
- **time per** — whether the clock counts down per **game** (one shared budget for the whole game) or per **move** (reset after every move).

| time per | Behaviour |
|---|---|
| **game** | The clock starts on your first move and counts down until the game ends or it expires. |
| **move** | Each move must be completed within the budget. The clock resets after every move. Running out of time on a single move ends the game. |

When `clock = 0`, time is unlimited and an elapsed timer is shown instead of a countdown.

---

## 🎮 How to Play — Knight's Trap

### Start Squares

When `first square = select`, each player must **choose a starting square** by clicking anywhere on the board. Players alternate placing their start squares. Once both are committed, turns begin.

When `first square = random`, the starting squares are placed automatically and play begins immediately.

### Taking Turns

The active player's legal moves are highlighted on the board. Click any highlighted square to move there. Squares already visited by either player are never legal targets — the path is always one-way.

The bot takes its turn automatically after a short delay (500–800 ms).

### Winning and Losing

- A player who has **no legal moves** at the start of their turn **loses**.
- If both players are trapped simultaneously, the player who has visited **more squares** wins.
- If square counts are equal, the result is a **draw**.

---

## 🟦 Square Color Guide

| Color | Meaning |
|---|---|
| Ivory / Tan | Unvisited square (light / dark board pattern) |
| Blue (light / dark) | Square visited by Player 1 (Blue) |
| Red (light / dark) | Square visited by Player 2 (Red) |
| Highlighted | Legal move for the active player |

---

## 🖱 In-Game Controls — Knight's Trap

### Mouse (Trap)

| Action | Effect |
|---|---|
| Click a start square (setup phase) | Commit your starting position |
| Click a highlighted legal-move square | Move your piece there |
| Click a menu `<` / `>` button | Cycle through that setting's values |
| Click any button | Activate that button's action |

### Keyboard Shortcuts (Trap)

| Key | Context | Action |
|---|---|---|
| `G` | Any | Toggle Move Guide overlay |
| `H` | In-game | Toggle Warnsdorff Degrees hint overlay |
| `U` | In-game | Undo last move |
| `ESC` | In-game | Resign current game |
| `ESC` | Endgame | Go to main menu |
| `M` | Any | Minimise window |

---

## 📊 HUD & Overlays — Knight's Trap

### Move Guide (Trap)

Displays directional arrows from the active player's current square to every legal destination. Helpful for scanning the board quickly. Toggle with **G** or the *show / hide move guide* button.

### Warnsdorff Degrees (Trap)

Overlays each legal destination with its **degree** — the number of unvisited squares reachable from that square after moving there. Lower-degree squares will become harder to escape from. Use this to:
- Avoid moves that would leave you with very few onward options next turn.
- Spot squares where the opponent might become trapped.

Toggle with **H** (in-game only) or the *show / hide degrees* button.

---

## 🏁 Endgame & Replay — Knight's Trap

### Win & Loss Conditions (Trap)

| Outcome | Condition |
|---|---|
| ✅ Win | Opponent has no legal moves — and you have visited more squares (or still have moves) |
| 🤝 Draw | Both players trapped with equal square counts |
| ❌ Trapped | You have no legal moves and the opponent visited more squares |
| ❌ Timeout | Your clock expires |
| ❌ Resign | You press resign / ESC |
| ❌ Bot resigns | Bot determines it cannot improve its position |

### Retry (Trap)

The **retry** button replays the exact same game setup (same seed, same starting squares if randomised) so you can attempt a different strategy. Available as long as a puzzle seed was recorded.

### Undo (Trap)

The **undo last move** button (or **U**) steps back one half-move at a time. There is no undo limit. Undoing during a bot game reverts the bot's last move and your last move together, returning to your previous turn.

### Replay Mode (Trap)

After a game ends, **start replay** enters a step-by-step review of the full game. Use the `+` and `-` buttons to step forward and backward through the move history. Board state and visited squares update to match each step, letting you analyse the turning points.

---

## 🔗 Share Codes — Knight's Trap

Every game setup receives a compact **share code** (16-character, base-32 encoded) that captures:
- Board size
- Piece selection
- Player One setting
- First square mode
- Opponent level
- Clock settings
- The RNG seed used for random starting squares

**Sharing a game**

1. After starting a game the share code is shown in the side panel.
2. Press **copy share code** to copy it to your clipboard.
3. Send the code to a friend — they will face the identical setup.

**Loading a shared game**

1. On the Menu screen press **enter share code**.
2. Type or paste the 16-character code into the input box.
3. Press **start** — the exact same configuration is reproduced.

---

## 🤖 Bot AI

The bot AI lives in `knightstrap_bot.py` and exposes five difficulty levels via `make_bot_move()`. Each level builds on the previous.

### Level 1 — Random

Selects a uniformly random legal move. No strategy whatsoever. Use this to learn the piece's movement before facing a real challenge.

### Level 2 — Dead-End Avoidance

Filters out moves that would leave the bot with zero onward options (dead ends). Chooses randomly among the remaining safe moves. Falls back to any legal move if all options are dead ends.

This is already a meaningful improvement over random — a bot that never voluntarily traps itself will outlast a random player by a wide margin.

### Level 3 — Warnsdorff's Rule

Applies Warnsdorff's heuristic on top of dead-end avoidance: among non-dead-end moves, prefers the square with the **fewest onward moves** from that position. This tends to keep large connected regions of the board accessible for longer, delaying the bot's eventual trapping.

Warnsdorff's rule was originally devised as a heuristic for completing a full knight's tour. In a competitive context it functions as a mobility preservation strategy.

### Level 4 — Multi-Heuristic

Combines several heuristics applied in strict priority order:

1. **Dead-end avoidance** — eliminate immediately fatal moves.
2. **Warnsdorff degree** — among surviving moves, prefer lower degree (fewer onward moves from the target square).
3. **Two-ply lookahead** — simulate the bot's next move from each candidate and pick the one that maximises the average degree of successor positions.
4. **Center proximity** — among remaining ties, prefer moves to central squares (higher long-term connectivity).
5. **Random tie-breaking** — uniform random among equals.

No opponent modeling at this level — the bot optimises purely for its own mobility.

### Level 5 — Opponent Modeling

All of Level 4, plus:

6. **Opponent modeling** — after ranking candidates by Level 4 criteria, additionally evaluates how many legal moves you (the opponent) would have after the bot moves there. Among equally-ranked candidates, the bot prefers the move that **minimises your options**.

This level plays aggressively: it will trade its own positional quality to cut you off from productive regions of the board. Playing a high-mobility piece (king, queen) at Level 5 on a small board is a serious test.

---

## 🧠 Advanced Strategy — Knight's Trap

### Start Square Selection Matters

In `select` mode, the choice of starting square is the first strategic decision. General principles:
- **Central squares** offer more initial onward moves for most pieces.
- **Mirroring or clustering near your opponent** creates earlier interference but risks mutual trapping.
- **Corner and edge starts** are risky — they begin with fewer options and tend to trap the piece that went there first.

That said, the optimal start square is highly piece-dependent. A knight's best start differs entirely from a camel's.

### Warnsdorff's Heuristic as a Survival Tool

Enable the **show degrees** overlay (press **H**) to see Warnsdorff numbers on every legal destination. As a rule of thumb:
- Avoid moves that would leave you with a degree of 1 or 2 unless no better option exists.
- Prefer moves with moderate degree (3–5 on an 8 × 8 board) — very high degree can be fine but sometimes indicates you are retreating to an uncontested corner.

Following the lowest non-zero degree strictly is Warnsdorff's rule; as a human player you have additional information (your opponent's position) that the pure heuristic ignores.

### Interference and Blocking

Because both players share the same set of blocked squares, every move you make changes what is available to your opponent:
- Moving through a narrow corridor **before** your opponent can blocks them from that route.
- Splitting the remaining board into two disconnected regions can be decisive — your opponent may be confined to the smaller region.
- Against the bot at Level 5, deliberately moving to high-degree squares can reduce the degree advantage the bot looks for, making its opponent modeling less effective.

### Piece Knowledge

- **Knight**: The classic choice. Its non-linear L-shaped jumps create complex, non-obvious paths that are hard to predict and hard to block.
- **Camel / Zebra**: Longer-range leapers that skip over intervening squares entirely. They can cross large distances unexpectedly, making interference harder.
- **King / Queen**: High mobility each turn, but on small boards the shared blocking effect becomes critical fast.
- **Wazir**: Only moves one square orthogonally — very restricted, creates very tight close-quarters games.
- **Exotic pieces**: Unfamiliar move sets (fibonacci, gunkan, zodiac pieces) reward the player who studies them. The bot applies the same heuristics regardless of piece — human positional understanding of an unusual piece can be a genuine advantage.

### Clock Settings

- **Per-game** clock rewards consistent long-term efficiency.
- **Per-move** clock rewards fast local decision-making and penalises calculating too deeply on any single turn.
- Start with `clock = 0` (unlimited) when learning a new piece or exploring the game's dynamics.

---

## 🏗 Architecture & Technical Notes — Knight's Trap

The game is split into three focused modules:

| Module | Role |
|---|---|
| `knightstrap_v01.py` | Entry point — Pygame init, window setup, main loop |
| `knightstrap_controller.py` | Game state machine, two-player logic, move handling, rendering, event handling |
| `knightstrap_bot.py` | AI move selection at five difficulty levels |

### Controller Architecture

`KnightsTrapController` inherits from `BaseGameController` (in `sharedlib/`) for common infrastructure including clipboard, codec input, undo stack, replay, and base rendering scaffolding. It overrides the required abstract methods:

- `_game_specific_start_setup()` — initialise two-player state, place pieces
- `_game_specific_make_move()` — apply a move and advance the turn
- `_validate_move()` — check move legality against shared visited set
- `_check_endgame_conditions()` — detect when a player is trapped or time expires
- `_capture_game_state()` / `_restore_game_state()` — full state snapshots for undo/replay

**Two-player state**

The controller maintains separate state for each player:
- `player_pos[1]`, `player_pos[2]` — current positions
- `visited[1]`, `visited[2]` — squares each player has visited
- `legal_moves[1]`, `legal_moves[2]` — cached legal move lists (recomputed after each half-move)

`all_visited` is the union of both players' visited sets and is used for all move legality checks and bot heuristics.

### Bot Architecture

`make_bot_move()` in `knightstrap_bot.py` dispatches to one of five private level functions (`_level1_move` through `_level5_move`). Each function calls utilities from `sharedlib/bot_utils.py`:

| Utility | Purpose |
|---|---|
| `get_legal_moves()` | Returns all legal moves from a position, excluding visited squares |
| `filter_non_dead_ends()` | Filters moves that lead to degree-0 positions |
| `select_warnsdorff_move()` | Picks minimum-degree move with optional dead-end filtering |
| `select_with_heuristics()` | Full multi-heuristic selection pipeline (Levels 4 and 5) |
| `calculate_two_ply_score()` | Computes 1-ply and 2-ply degree scores for a candidate move |
| `apply_opponent_modeling()` | Filters candidates to minimise opponent's legal move count |

The bot is invoked from `_execute_bot_move()` after a configurable delay of 500–800 ms to feel natural during play.

### Codec System

Game configuration is packed into a 16-character base-32 share code using a fixed schema stored in `knightstrap_schema`. The codec encodes:

| Field | Values |
|---|---|
| board | 5–16 |
| piece | any valid piece name |
| player_one | human / bot |
| first_square | select / random |
| opponent | 1–5 |
| clock | 0–330 seconds |
| time_per | game / move |

The RNG seed (used for random starting positions) is embedded in the remaining bits.

---

## ⚠ Known Limitations — Knight's Trap

1. **Even-parity pieces excluded** — bishop, delta, theta, lambda, and xi are removed from the piece list because color-binding prevents them from visiting every square.
2. **Bot think time is not configurable** — the 500–800 ms artificial delay is hardcoded and cannot be changed from the menu.
3. **Two-ply lookahead only** — Level 4/5 lookahead is limited to two plies; deeper search would improve play quality but increases CPU cost significantly.
4. **Replay memory is unbounded** — long games accumulate many full state snapshots in memory.
5. **Clipboard fallback** — on Linux, clipboard copy may silently fail if `xclip` or `xsel` are not installed.
6. **No human-vs-human networked play** — both players must share the same machine; networked multiplayer is on the wishlist.

---

---

## 🙏 Credits

Developed by **paw309**.
Built with [Python](https://www.python.org/) and [pygame](https://www.pygame.org/).
Warnsdorff's heuristic described by H. C. von Warnsdorff (1823).
Knight's Trap inspired by the mathematics of the Knight's Tour, combinatorial game theory, and competitive board games.

---

> *Can you visit every square? Can you outlast your opponent?*
