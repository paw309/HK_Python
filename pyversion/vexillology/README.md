# 🚩 Vexillum & Vexillology

**Vexillum** is a single-player strategic puzzle: guide your chosen chess piece across a procedurally generated grid and capture every flag before you run out of legal moves or time.

**Vexillology** is the competitive variant of Vexillum — human versus bot, or human versus human. Both players share the same board, alternating turns to capture the most flags before neither can move.

Both games are built on the same engine and share the same core mechanics. This README covers both.

---

## 📋 Table of Contents

- [Overview](#-overview)
  - [Vexillum — Solo Puzzle](#vexillum--solo-puzzle)
  - [Vexillology — Competitive](#vexillology--competitive)
- [Getting Started](#-getting-started)
- [Game Configuration](#-game-configuration)
  - [Board Size](#board-size)
  - [Piece Selection](#piece-selection)
  - [Path Length](#path-length)
  - [Flag Density](#flag-density)
  - [Flag Order](#flag-order)
  - [Clock & Time Per](#clock--time-per)
  - [Opponent (Vexillology only)](#opponent-vexillology-only)
- [How to Play](#-how-to-play)
  - [Vexillum](#vexillum-1)
  - [Vexillology](#vexillology-1)
- [Flag Color Guide](#-flag-color-guide)
- [Controls](#-controls)
  - [Mouse](#mouse)
  - [Keyboard Shortcuts (Vexillum)](#keyboard-shortcuts-vexillum)
  - [Buttons (Vexillology)](#buttons-vexillology)
- [HUD & Overlays](#-hud--overlays)
  - [Move Guide](#move-guide)
  - [Move Track](#move-track)
  - [Warnsdorff Degrees](#warnsdorff-degrees)
  - [Peek Mode (Vexillum)](#peek-mode-vexillum)
- [Bot Opponent (Vexillology)](#-bot-opponent-vexillology)
- [Endgame & Replay](#-endgame--replay)
  - [Win & Loss Conditions](#win--loss-conditions)
  - [Retry](#retry)
  - [Replay Mode](#replay-mode)
  - [Undo](#undo)
- [Share Codes](#-share-codes)
- [Strategy](#-strategy)
  - [Vexillum Strategy](#vexillum-strategy)
  - [Vexillology Strategy](#vexillology-strategy)
- [Architecture & Technical Notes](#-architecture--technical-notes)
- [Known Limitations](#-known-limitations)
- [Credits](#-credits)

---

## 🎯 Overview

### Vexillum — Solo Puzzle

At its core, Vexillum is about efficiently guiding a chess piece through a procedurally generated open path on a square grid, collecting every flag square before getting trapped or running out of time.

Each game begins with a fresh puzzle: a random walkable path is generated for your chosen piece and board size, and a set of flag squares is distributed along that path. Your piece starts at the path's entry square. You must navigate — using only legal moves for your piece — to collect every flag. The path is open (not a complete Hamiltonian tour), so dead ends are possible and avoidance matters.

Three flag-order modes add layers of tactical complexity:
- **Any** — collect flags in whatever order you like.
- **Only** — all flags are visible but must be collected in their numbered order; wrong-order captures are penalised.
- **Next** — only the next required flag is revealed; future flags are hidden until needed.

### Vexillology — Competitive

Vexillology takes the same Hamiltonian path mechanic — you can only visit each square **once** — and turns it into a head-to-head competition. Flags are distributed across the board before the game begins. Each player manoeuvres their piece across the grid, capturing flags by landing on them. The shared visited-square pool means every move one player makes permanently restricts what both players can do next.

The result is a game that rewards spatial planning, positional awareness, and the ability to read your opponent's options as clearly as your own.

---

## 🚀 Getting Started

**Requirements**

- Python 3.7 or later
- pygame (`pip install pygame`)
- The full `Hamiltonian-Knights` repository (shared libraries are loaded from `sharedlib/`)

**Run Vexillum**

```bash
cd Hamiltonian-Knights
python vexillum/vexillum_v01.py
```

**Run Vexillology**

```bash
cd Hamiltonian-Knights
python vexillology/vexillology_v01.py
```

Or from the unified launcher:

```bash
python launcher.py
```

Select **Vexillum** or **Vexillology** from the game list and click **Launch**.

The window opens at your current display resolution and is fully resizable. On Windows the window is automatically maximised.

---

## ⚙️ Game Configuration

All settings are adjusted from the **Menu** screen. In Vexillum, use the `<` and `>` buttons on each row or click the board to reposition the preview piece. In Vexillology, the same row-based menu is used with an additional **Opponent** setting.

### Board Size

| Setting | Range |
|---|---|
| Minimum | 5 × 5 |
| Maximum | 16 × 16 |
| Default | 8 × 8 |

Larger boards produce longer, more complex paths. Some exotic pieces require a minimum board size; a warning is shown if the current piece cannot be used on the selected board.

### Piece Selection

Any piece from the `piecekeeper` module can be selected — this includes all standard chess pieces (knight, bishop, rook, queen, king) and a wide range of exotic variants (gamma, delta, theta, lambda, xi, pi, sigma, phi, psi, omega, planetary pieces, zodiac pieces, fibonacci, gunkan, and more).

In Vexillology, colour-bound pieces (bishop, ferz, alfil, dabbaba) are excluded because they cannot reach all squares on the board.

Minimum board sizes per piece are enforced:

| Piece | Min. Board |
|---|---|
| Most pieces | 5 × 5 |
| lambda, phi, psi, omega, pallas | 8 × 8 |
| pluto | 16 × 16 |

See [The Piece Library](../../README.md#-the-piece-library) in the main README for the full list of available pieces and their movement rules.

### Path Length

Controls the target length of the generated open path.

| Choice | Vexillum — Path Length Range | Vexillology — Multiplier |
|---|---|---|
| **short** | board_size … board_size × 4 | 2 |
| **medium** | board_size … board_size × 6 | 3 |
| **long** | board_size … board_size × 8 | 4 |
| **super** | board_size … board_size × 12 | 6 |

Longer paths produce more intricate flag distributions and routing challenges.

> **Note:** `super` path length cannot be encoded into a share code in Vexillum (only 2 bits are allocated for this field). The game will play normally but no shareable puzzle code will be generated.

### Flag Density

Determines what fraction of path squares receive a flag.

| Choice | Vexillum | Vexillology |
|---|---|---|
| **low** | ~20% of path squares | ~10% of path squares |
| **medium** | ~30% of path squares | ~25% of path squares |
| **high** | ~40% of path squares | ~60% of path squares |

In Vexillum the final square of the path always receives a flag regardless of density. Higher density means more targets and typically more constrained routing.

### Flag Order

| Mode | Vexillum | Vexillology |
|---|---|---|
| **any** | Flags may be collected in any order. Captured flags turn purple. | Flags may be captured in any order. |
| **only** | All flags are numbered and visible; must be collected in order. In-order captures turn blue; out-of-order captures turn red. | You may only capture the *next* flag in sequence; other flags cannot be captured yet. |
| **next** | Only the immediate next flag is shown (green). Future flags are hidden. | The next flag in sequence scores bonus points, but out-of-order captures are still allowed. |

### Clock & Time Per

Two fields work together to configure the time control:

- **clock** — time budget in seconds (`0` = unlimited / infinity). Values range from 0 to 330 seconds (Vexillum) or 0 to 300 seconds (Vexillology), in 30-second increments.
- **time per** — whether the clock counts down per **game** (one shared budget) or per **move** (reset after every move).

| time per | Vexillum | Vexillology |
|---|---|---|
| **game** | Clock starts on your first move and counts down until all flags are captured or it expires. | Each player has a single pool of time for the entire game. Running out of time is an immediate loss. |
| **move** | Each move must be completed within the time budget. Running out of time on a single move ends the game. | Each individual move must be made within the configured time limit. Failing to move in time ends the game for that player. |

When `clock = 0`, time is unlimited and an elapsed timer is displayed instead of a countdown. In Vexillology, the clock pauses during the start-square selection phase and during any bot move calculation.

### Opponent (Vexillology only)

| Option | Description |
|---|---|
| Human | Both players are human; players share the same keyboard and screen |
| Bot | Player 2 is controlled by an AI at the selected difficulty level (1–3) |

See [Bot Opponent](#-bot-opponent-vexillology) for full details on difficulty levels.

---

## 🎮 How to Play

### Vexillum

1. **Configure** your game on the Menu screen: choose piece, board size, path length, flag density, flag order, and clock settings.
2. Press **start** to generate a new puzzle. The board populates with your piece at the start square and flags distributed along the hidden path.
3. **Click a highlighted square** to move your piece there. Only legal moves for your piece are accepted.
4. **Collect flags** by moving onto flag squares. Colour feedback shows your progress (see [Flag Color Guide](#-flag-color-guide)).
5. Continue until you have **captured all flags** (win) or you are **trapped**, **time out**, or **resign** (loss).

### Vexillology

1. Configure your game using the menu (board size, piece, path length, flag density, flag order, clock, and opponent level).
2. Click **Start**. The board is generated with a hidden Hamiltonian-style path and flags distributed along it.
3. **Player 1** selects a starting square by clicking any cell on the board.
4. **Player 2** (human or bot) then selects their own starting square.
5. Players alternate turns. On your turn, click any **highlighted** square to move your piece there. Highlighted squares are all legal moves for your piece that have not yet been visited by either player.
6. The square you just left is permanently marked as visited and cannot be entered again by anyone.
7. The game ends when **neither player has a legal move**. The player who captured **more flags** wins. Equal flags is a **draw**.

---

## 🚩 Flag Color Guide

| Color | Vexillum meaning | Vexillology meaning |
|---|---|---|
| 🟤 Tan / Ivory | Uncaptured flag | — |
| 🔵 Blue | Flag captured **in order** | Uncaptured flag (distinct highlight) / Player 1 capture |
| 🔴 Red | Flag captured **out of order** | Player 2 capture |
| 🟣 Purple | Flag captured (in `any` mode) | — |
| 🟢 Green | The *next* required flag (`only` / `next` modes) | — |

---

## 🎮 Controls

### Mouse

| Action | Vexillum | Vexillology |
|---|---|---|
| Click a legal-move square | Move your piece there | Move your piece there |
| Click a menu `<` / `>` button | Cycle through setting values | Cycle through setting values |
| Click the board in Menu | Reposition the preview piece | — |
| Click any button | Activate that button's action | Activate that button's action |

### Keyboard Shortcuts (Vexillum)

| Key | Context | Action |
|---|---|---|
| `G` | Any | Toggle Move Guide overlay |
| `T` | Any | Toggle Move Track (move numbers) overlay |
| `H` | In-game | Toggle Warnsdorff Degrees hint overlay |
| `P` | In-game / Endgame | Toggle Peek mode (solution thumbnail) |
| `U` | In-game | Undo last move |
| `ESC` | In-game | Resign current game |
| `ESC` | Endgame | Start a new game |
| `M` | Any | Minimise window |

### Buttons (Vexillology)

| Button | Function | Available When |
|---|---|---|
| Start | Begin the game | Menu |
| Move Guide | Toggle legal move highlights | During game |
| Hint | Toggle Warnsdorff degree overlay | During game |
| Undo | Undo the last move (both players' last turn) | During game |
| Replay | Toggle replay mode to step through the game | Endgame |
| Resign | End the game immediately | During game |
| New Game | Return to the menu | Endgame |
| Retry | Replay the exact same board with the same seed | Endgame |
| Exit | Quit the application | Anytime |

---

## 🖥 HUD & Overlays

### Move Guide

Displays directional arrows from the current square to every legal move. Useful for quickly scanning available options without hunting across the board. Toggle with **G** or the *show / hide move guide* button.

### Move Track

Overlays each visited square with the move number on which you visited it. Helps trace your path and count remaining moves. Toggle with **T** or the *show / hide move #'s* button.

### Warnsdorff Degrees

Overlays each legal destination square with its **degree** — the number of unvisited squares reachable from that square after moving there (the Warnsdorff heuristic). Lower-degree squares become dead ends more quickly; preferring higher degrees tends to keep more of the board open.

Toggle with **H** (in-game only) or the *show / hide degrees* button.

### Peek Mode (Vexillum)

Reveals a miniature thumbnail of the full board inside the left panel, showing the numbered solution path and all flag positions. Use this to orient yourself when the main board becomes complex. The thumbnail updates in real time as you move.

Toggle with **P** or the *peek / hide* button.

---

## 🤖 Bot Opponent (Vexillology)

When the opponent is set to **Bot**, Player 2 is controlled by `vexillology_bot.py`. Three difficulty levels are available.

### Level 1 — Random

The bot selects uniformly at random from all legal moves. No strategy is applied. Suitable for learning the game mechanics.

### Level 2 — Flag-Seeker

The bot applies a two-stage heuristic:

1. **Immediate capture:** If any legal move lands directly on an uncaptured flag, the bot takes it.
2. **Proximity:** Among remaining moves, the bot prefers those with the shortest Manhattan distance to the nearest uncaptured flag.
3. **Dead-end avoidance:** Moves that would leave the bot with zero onward options are deprioritised when alternatives exist.

Level 2 plays tactically and will actively contest flags, but it does not consider your position or plan more than one move ahead.

### Level 3 — Warnsdorff + Opponent Modelling

The bot uses the full heuristic stack from `select_with_heuristics` in `bot_utils.py`, applied in priority order:

| Priority | Heuristic |
|---|---|
| 1 | Dead-end avoidance |
| 2 | Domain score — moves toward or onto uncaptured flags |
| 3 | Warnsdorff degree — prefer squares with fewer onward moves |
| 4 | Two-ply lookahead |
| 5 | Centre proximity |
| 6 | Opponent modelling — minimise your legal move count |
| 7 | Random tie-breaking |

Level 3 is a challenging opponent. It actively attempts to cut off your movement options while pursuing flags efficiently. It will also resign when it determines its position is hopeless.

---

## 🏁 Endgame & Replay

### Win & Loss Conditions

**Vexillum**

| Outcome | Condition | Message |
|---|---|---|
| ✅ Win | All flags captured | *all flags captured* |
| ❌ Trapped | No legal moves remain | *no legal moves* |
| ❌ Timeout | Clock expires | *time's up* |
| ❌ Resign | You press resign / ESC | *resigned* |

**Vexillology**

| Condition | Triggered By |
|---|---|
| **No legal moves** | Neither player can make a legal move — flags are counted and the winner is declared |
| **Timeout** | A player's clock expires (Game mode) or a player fails to move within the time limit (Move mode) |
| **Resign** | A player clicks the **Resign** button |
| **Bot resignation** | At Level 3, the bot may resign if it determines it cannot win — a prompt is shown before the resignation is accepted |

In all endgame states the final flag counts, elapsed time, and result are displayed.

### Retry

After any endgame the **retry** button replays the exact same puzzle (same seed, same flags) so you can attempt a better solution or rematch.

### Replay Mode

After a game ends, the **start replay** button (or **Replay** in Vexillology) enters a step-by-step review of your game. Use:
- **`+`** button (or click) to advance one move forward
- **`-`** button to step one move backward

The board state, visited squares, and flags all update to match the selected move.

### Undo

While in-game the **undo last move** button (or **U** in Vexillum) steps back one move at a time. In Vexillology, undo reverses both players' last turn. There is no undo limit. The per-move clock resets after each undo.

---

## 🔗 Share Codes

Every generated puzzle receives a **16-character share code** (base-32 encoded) that encodes the board parameters and RNG seed.

**Sharing a puzzle (Vexillum)**

1. After starting a game, the share code is displayed at the top of the left panel.
2. Press **copy share code** to copy it to your clipboard.
3. Send the code to a friend. They enter it on the Menu screen via **enter share code** to load the exact same puzzle.

Encoded fields: board size, path length, flag density, flag order, RNG seed.

**Sharing a game (Vexillology)**

- After a game, the share code for that session is displayed.
- Enter a code in the menu text box to recreate the exact same board configuration.
- Encoded fields: board size, piece, path length, flag density, flag order, clock settings, and seed.
- Piece selection and opponent level are **not** encoded — players can choose their own piece and bot difficulty when loading a shared game.

> **Note (Vexillum):** `super` path length cannot be encoded. If you start a game with `super` selected, no share code is generated and the copy button will not appear.

---

## 🧠 Strategy

### Vexillum Strategy

**Piece Choice Shapes Everything**

- **Knight**: The classic choice. Its non-linear L-shaped moves create rich, non-obvious paths.
- **Bishop / Rook**: Constrained to one colour or one axis respectively. Can produce very long corridors or very isolated regions.
- **Queen / King**: High mobility means more choices per turn, but also more rope to hang yourself with on larger boards.
- **Exotic pieces**: Try `lambda`, `phi`, `psi`, or planetary variants for completely unfamiliar movement patterns.

**Warnsdorff's Heuristic**

Enable **show degrees** to see Warnsdorff numbers. Prioritising moves to the square with the **lowest non-zero degree** tends to delay dead ends and helps collect flags before the board becomes over-fragmented. This is the same heuristic used to find Hamiltonian paths on chessboards.

**Flag Order Modes**

- **Any**: Maximum freedom. Good for beginners or speed runs.
- **Only**: Forces a specific collection order. Study the numbered flags before moving — backtracking across a large board to collect a skipped flag can be fatal.
- **Next**: Adds fog of war. You must infer where future flags might be from path length and density settings. Use Peek mode sparingly for a fair challenge.

**Clock Settings**

- **Per-game** clock rewards consistent efficiency across the whole run.
- **Per-move** clock rewards fast local decisions — useful for drilling specific piece knowledge.
- Start with `clock = 0` (unlimited) when learning a new piece or board size.

**Board Sizing**

- A 5 × 5 board with a short path and high density is a quick tactical puzzle.
- A 12 × 12 board with a long path and low density is a slow, strategic endurance test.
- Combine large boards with restricted pieces (bishop, rook) for the hardest challenges.

### Vexillology Strategy

**Core Concepts**

**Every square is finite.** Each move either player makes permanently reduces the total available board space. Think of each move not just as "where am I going?" but as "what am I cutting off — for myself and for my opponent?"

**Flags are the objective, but the path is the weapon.** Routing yourself to maximise flag captures while limiting your opponent's flag access is the central tension of the game. Capturing a flag while trapping your opponent in the same sequence is the ideal play.

**Opening**

- **Starting square placement matters enormously.** Choosing a starting square adjacent to a cluster of flags gives you early tempo. However, starting too close to your opponent can lead to early congestion.
- In general, prefer starting squares with high onward connectivity (i.e., many legal moves from that position) rather than corners or edges, which can become dead ends quickly.

**Mid-Game**

- **Use the move guide** to count your available moves and assess whether you are approaching a dead end.
- **Watch your opponent's options.** Actively restricting your opponent's legal move count is as valuable as capturing flags yourself.
- **Dead ends kill games.** Visit high-connectivity squares first and leave low-connectivity squares (corners, edges) for later.

**Endgame**

- When the board is heavily visited, count your remaining legal moves and your opponent's. The player who survives longer will have more opportunities to capture remaining flags.
- If you are ahead on flags, play defensively — preserve your own movement options.
- If you are behind on flags, accept more risk: move toward flags even if it reduces your onward connectivity.

**Bot-Specific Tips**

- **Level 1:** Exploitable by simply moving toward flags as fast as possible.
- **Level 2:** Will contest flags aggressively. Routing the bot into a dead end is more effective than racing it to individual flags.
- **Level 3:** Actively trying to minimise your options while taking flags. Start with strong positional play — a good starting square and high initial connectivity — before pursuing flags.

---

## 🏗 Architecture & Technical Notes

### Vexillum

| Module | Role |
|---|---|
| `vexillum_v01.py` | Entry point — Pygame init, window setup, main loop |
| `capturetheflag_controller.py` | Game state machine, move logic, rendering, event handling |
| `capturetheflag_generator.py` | Procedural path & flag generation |

**Generator algorithm**

A greedy random walk is attempted up to `max_attempts` times (default 500) within a `time_budget` (default 2 seconds). Each attempt picks a random starting square and extends a path by randomly choosing an unvisited legal move until the piece is trapped or the `max_length` is reached. The first attempt that meets `min_length` is accepted and flags are distributed. The same `random.Random(seed)` instance is used throughout so puzzles are fully reproducible.

**Controller architecture**

- Inherits from `BaseGameController` for common features (clipboard, error overlays, codec input, window focus handling, base replay infrastructure).
- Full game state is snapshotted into `replay_states` after every move (including visited squares, flag states, and move counts), enabling unlimited undo and post-game replay.
- Cell size is recalculated on every resize event; flag images, arrows, and piece sprites are lazily reloaded only when the cell size changes.
- Legal moves are cached in `self.legal_moves` and only recomputed after each move or undo.

### Vexillology

| Module | Role |
|---|---|
| `vexillology_v01.py` | Entry point and main loop |
| `vexillology_controller.py` | Game controller (rules, state, rendering) |
| `vexillology_bot.py` | Bot AI (Levels 1–3) |

### Shared Libraries

Both games draw from `sharedlib/`:

| Module | Role |
|---|---|
| `base_game_controller.py` | Undo stack, replay, clock, codec, button handling |
| `gameboard.py` | `BoardModel` + `BoardRenderer` |
| `piecekeeper.py` | Piece definitions and legal move generation |
| `bot_utils.py` | `get_legal_moves`, `select_warnsdorff_move`, `select_with_heuristics`, `filter_non_dead_ends` |
| `chess_clock.py` | Countdown and elapsed time clock |
| `puzzle_codec.py` | Share code encoder/decoder |

**Codec system**

Puzzle parameters are packed into a 16-character base-32 string using a fixed schema:

| Field | Bits | Values |
|---|---|---|
| board | 4 | 5–16 |
| path_length | 2 | short / medium / long |
| flag_density | 2 | low / medium / high |
| flag_order | 2 | any / only / next |

The RNG seed is embedded in the remaining bits.

---

## ⚠️ Known Limitations

1. **`super` path length is not shareable in Vexillum** — only 2 bits are allocated for path length in the codec.
2. **No path optimality guarantee** — the random walk may produce shorter-than-ideal paths on congested boards; rare failures fall back gracefully.
3. **Replay memory is unbounded** — very long games accumulate many state snapshots.
4. **Clipboard fallback chain** — on Linux, clipboard copy may silently fail if `xclip` / `xsel` are not installed.
5. **No difficulty calibration per piece** — path length targets are calculated from board size alone, not from the piece's specific dead-end risk profile.

---

## 🙏 Credits

Developed by **paw309**.
Built with [Python](https://www.python.org/) and [pygame](https://www.pygame.org/).
Special thanks to the chess, maze, and puzzle gaming communities for inspiration.

---

> **Vexillum** — *Can you capture all the flags?*
> **Vexillology** — *Where every square counts and every flag is contested.*