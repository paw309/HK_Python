# Mined Maze & Mined Control

**Mined Maze** is a single-player deduction puzzle: a hidden Hamiltonian-style path winds across a grid from a start square to a target square. Your piece must discover and traverse that path — but the route is invisible, and any square you step onto that lies off the path is a **mine**. Deduce the correct route through inference and elimination.

**Mined Control** is the competitive variant. Both players share the same hidden maze — a path that runs from one end of the board to the other. Player 1 (Blue) starts at one end; Player 2 (Red) starts at the other. The **target** is the exact middle of the path. The first player to reach it wins.

Both games use the same piece set, the same path generator, and the same mine-deduction mechanics. This README covers both.

Part of the [Hamiltonian Knights](https://github.com/paw309/Hamiltonian-Knights) suite.

---

## Table of Contents

- [Overview](#overview)
  - [Mined Maze — Solo Deduction](#mined-maze--solo-deduction)
  - [Mined Control — Competitive Race](#mined-control--competitive-race)
- [Getting Started](#getting-started)
- [Game Configuration](#game-configuration)
  - [Board Size](#board-size)
  - [Piece Selection](#piece-selection)
  - [Path Length](#path-length)
  - [Blocks Visibility](#blocks-visibility)
  - [Bounce Mode](#bounce-mode)
  - [Difficulty Profiles](#difficulty-profiles)
  - [Player One (Mined Control only)](#player-one-mined-control-only)
  - [Opponent Level (Mined Control only)](#opponent-level-mined-control-only)
  - [Clock](#clock)
  - [Time Per (Mined Control only)](#time-per-mined-control-only)
- [How to Play](#how-to-play)
  - [Mined Maze](#mined-maze-1)
  - [Mined Control](#mined-control-1)
- [Square Color Guide](#square-color-guide)
- [In-Game Controls](#in-game-controls)
  - [Mouse](#mouse)
  - [Keyboard Shortcuts](#keyboard-shortcuts)
- [HUD & Overlays](#hud--overlays)
  - [Move Guide](#move-guide)
  - [Move Track](#move-track)
  - [Warnsdorff Degrees](#warnsdorff-degrees)
  - [Peek Mode](#peek-mode)
- [Endgame & Replay](#endgame--replay)
  - [Win & Loss Conditions](#win--loss-conditions)
  - [Retry](#retry)
  - [Undo](#undo)
  - [Replay Mode](#replay-mode)
- [Share Codes](#share-codes)
- [Statistics Display](#statistics-display)
- [Bot AI (Mined Control)](#bot-ai-mined-control)
- [Advanced Strategy](#advanced-strategy)
  - [Mined Maze Strategy](#mined-maze-strategy)
  - [Mined Control Strategy](#mined-control-strategy)
- [Architecture & Technical Notes](#architecture--technical-notes)
- [Known Limitations](#known-limitations)
- [Credits](#credits)

---

## Overview

### Mined Maze — Solo Deduction

Before each game the engine generates a **random Hamiltonian-style path** for your chosen piece and board size. The path runs from a start square (where your piece is placed) to a highlighted target square. Embedded invisibly across the board are **obstacle squares (mines)** — any square reachable by your piece that was *not* chosen as the next step of the path when it was generated.

Your job is to navigate from start to target, stepping only onto path squares, without triggering mines. You receive no map. You reconstruct the route through:

- **Move feedback** — a failed move reveals (or flashes) a mine.
- **Logical elimination** — mines you have exposed narrow down which squares are safe.
- **Piece move knowledge** — understanding which squares your piece can and cannot reach constrains the path topology.

Two independent settings — **blocks visibility** and **bounce mode** — control how punishing mistakes are, creating four distinct difficulty profiles from forgiving to brutal.

### Mined Control — Competitive Race

Before each game the engine generates a random **odd-length** path. The path is guaranteed to have an exact middle square — the **target**. Player 1 (Blue) is placed at `path[0]` and navigates toward higher path indices. Player 2 (Red) is placed at `path[-1]` and navigates toward lower path indices. Both players race toward the same middle square from opposite ends.

Every square reachable by the piece that was *not* chosen as the next step when the path was generated is a **mine**. Stepping on a mine does not end the game — but it wastes a turn and may reset your progress. Mine knowledge is **private**: each player builds their own map of mine positions, and mine markers are player-coloured.

The race is asymmetric in information: your opponent cannot see your mine markers, and you cannot see theirs.

---

## Getting Started

**Requirements**

- Python 3.7 or later
- pygame (`pip install pygame`)
- The full `Hamiltonian-Knights` repository (shared libraries are loaded from `sharedlib/`)

**Run Mined Maze**

```bash
cd Hamiltonian-Knights
python minedmaze/minedmaze_v02.py
```

**Run Mined Control**

```bash
cd Hamiltonian-Knights
python minedcontrol/minedcontrol_v01.py
```

Or launch either from the unified launcher:

```bash
python launcher.py
```

The window opens at your current display resolution and is fully resizable. On Windows the window is automatically maximised.

---

## Game Configuration

All settings are adjusted from the **Menu** screen using the `<` and `>` buttons on each row. In Mined Maze, clicking the board in the menu repositions the preview piece.

### Board Size

| Setting | Range | Default |
|---|---|---|
| Board | 5 × 5 to 16 × 16 | 8 × 8 |

Larger boards produce longer, more complex hidden paths. Some exotic pieces require a minimum board size — a warning is displayed if the current piece cannot be used on the selected board.

### Piece Selection

Any piece from the `piecekeeper` module can be selected. The piece determines the legal move set, which in turn determines the structure of the hidden path and which squares can be mines. In Mined Control both players move the same piece type.

Minimum board sizes per piece:

| Piece | Min. Board |
|---|---|
| Most pieces | 5 × 5 |
| lambda, phi, psi, omega, pallas | 8 × 8 |
| pluto | 16 × 16 |

### Path Length

Controls the target length of the hidden path, expressed as a multiple of the board size.

| Choice | Path Length Range |
|---|---|
| **short** | board_size + 1 … board_size × 2 |
| **medium** | (board_size × 2) + 1 … board_size × 4 |
| **long** | (board_size × 3) + 1 … board_size² |

Longer paths mean more squares to traverse and more opportunities for mistakes. `long` allows the path to cover up to the entire board. In Mined Control the path is always forced to odd length so there is an exact middle square.

### Blocks Visibility

Controls whether mines (obstacle squares) remain visible on the board after you trigger them.

| Choice | Behaviour |
|---|---|
| **show** | Triggered mines are **permanently marked** on the board. In Mined Control, each player's markers are shown in their own colour (blue / red). |
| **hide** | Triggered mines **flash briefly** then disappear. You must remember which squares are mined — maximum deduction difficulty. |

In Mined Control's `show` mode, the bot at higher difficulty levels uses visible mine markers to refine its path following.

### Bounce Mode

Controls what happens when a player steps onto a mine.

| Choice | Behaviour |
|---|---|
| **stay** | A mine returns the player to their last valid position. Progress along the path is **preserved**. More forgiving — you can probe adjacent squares one at a time. |
| **bounce** | A mine returns the player all the way to their **starting square**. All path progress is lost. You must retrace the entire correct path from the beginning. |

### Difficulty Profiles

The blocks/bounce combination produces four distinct difficulty levels:

| blocks | bounce | Difficulty |
|---|---|---|
| show | stay | Easiest — mine marks persist, no progress loss |
| show | bounce | Moderate — marks persist but a single error resets everything |
| hide | stay | Hard — must remember mines, no progress loss |
| hide | bounce | Hardest — mines disappear and a single error resets everything |

### Player One (Mined Control only)

| Choice | Meaning |
|---|---|
| **human** | You play as Player 1 (Blue); the bot plays as Player 2 (Red) |
| **bot** | The bot plays both sides (demonstration / watch mode) |

### Opponent Level (Mined Control only)

Sets the bot AI difficulty from 1 (easiest) to 5 (hardest). See [Bot AI](#bot-ai-mined-control) for the full breakdown.

| Level | Strategy summary |
|---|---|
| 1 | Pure random — no path or mine awareness |
| 2 | 80 % confusion — mostly random, occasionally follows the path |
| 3 | 40 % confusion — often follows the path with frequent wrong turns |
| 4 | 25 % confusion — mostly path-following with occasional errors |
| 5 | 10 % confusion — nearly always correct; a skilled human can still beat it |

### Clock

Sets a time budget per player.

| Game | Range | Default |
|---|---|---|
| **Mined Maze** | 0 to 5 minutes 30 seconds (30-second increments) | 0 (no limit) |
| **Mined Control** | 0 to 330 seconds (30-second increments) | 0 (no limit) |

When `clock = 0`, time is unlimited and an elapsed timer is shown instead of a countdown.

### Time Per (Mined Control only)

Works together with the clock value to configure the time control.

| time per | Behaviour |
|---|---|
| **game** | The clock starts on the first move and counts down until the game ends or it expires. |
| **move** | Each move — including mine hits — must be completed within the budget. The clock resets after every turn change. |

---

## How to Play

### Mined Maze

1. **Configure** your game on the Menu screen: choose piece, board size, path length, blocks visibility, bounce mode, and clock.
2. Press **start** to generate a new puzzle. Your piece appears at the start square; the target square is highlighted with a target marker.
3. **Click a square** to attempt a move. Only squares reachable by your piece's legal move set are accepted.
4. **Correct path squares** advance your piece along the route. The square is colored to show you have visited it.
5. **Mine squares** trigger the mine response based on your blocks/bounce settings.
6. Continue until your piece **reaches the target** (win) or you **run out of path moves**, **time out**, or **resign** (loss).

> **Key insight:** Every time you step onto a mine, you learn that square is *not* on the path. Over multiple attempts you accumulate a mental or visible map of which squares are safe, progressively narrowing the correct route.

### Mined Control

1. **Configure** your game on the Menu screen: choose piece, board size, path length, blocks visibility, bounce mode, player one, opponent level, clock, and time per.
2. Press **start** to generate a new maze. Player 1 (Blue) is placed at `path[0]`; Player 2 (Red) is placed at `path[-1]`. The **target** (exact middle of the path) is highlighted. Play begins with Player 1's turn.
3. The active player **clicks a reachable square** to attempt a move. Squares already visited by your own piece cannot be revisited.
4. **Correct path squares** advance your piece in your direction of travel (Blue moves toward higher path indices; Red moves toward lower path indices).
5. **Mine hits** increment your mine count, mark or flash the square in your colour, and switch the turn to the other player (in bounce mode, your position resets to your starting square first).
6. **Continuation rule:** If the other player has no legal moves on a given turn, you take another turn rather than switching.
7. The **first player to step onto the middle target square wins**.

---

## Square Color Guide

| Color | Mined Maze meaning | Mined Control meaning |
|---|---|---|
| Ivory / Tan | Unvisited square (light / dark board pattern) | Unvisited square |
| Blue (light / dark) | Path square you have already visited | Path square visited by Player 1 |
| Red (light / dark) | — | Path square visited by Player 2 |
| Purple (light / dark) | — | Unvisited path square (visible during peek / end reveal) |
| Target marker (icon) | The goal — the final square of the hidden path | The goal — the exact middle square of the hidden path |
| Mine icon (centered) | A triggered obstacle square (show mode or flash) | — |
| Blue mine icon | — | Mine triggered by Player 1 (show mode or flash) |
| Red mine icon | — | Mine triggered by Player 2 (show mode or flash) |
| Path color (peek / reveal) | The full hidden path made visible | The full hidden path made visible |

---

## In-Game Controls

### Mouse

| Action | Effect |
|---|---|
| Click any board square | Attempt to move there |
| Click a menu `<` / `>` button | Cycle through that setting's values |
| Click the board in Menu (Mined Maze) | Reposition the preview piece |
| Click any button | Activate that button's action |

### Keyboard Shortcuts

| Key | Context | Action |
|---|---|---|
| `G` | Any | Toggle Move Guide overlay |
| `T` | Any | Toggle Move Track (move numbers) overlay |
| `H` | In-game | Toggle Warnsdorff Degrees hint overlay |
| `P` | In-game / Endgame | Toggle Peek mode (full path reveal) |
| `U` | In-game | Undo last move (Mined Maze) / last move pair (Mined Control) |
| `ESC` | In-game | Resign current game |
| `ESC` | Endgame | Start a new game (Mined Maze) / Go to main menu (Mined Control) |
| `M` | Any | Minimise window |

---

## HUD & Overlays

### Move Guide

Displays directional arrows from the active player's current square to every square the piece can legally reach. This shows *reachable* squares — not which of them are on the path. Toggle with **G** or the *show / hide move guide* button.

### Move Track

Overlays each visited square with the move number on which it was visited. In Mined Control, move numbers are colour-coded to match the visiting player (blue for Player 1, red for Player 2). Toggle with **T** or the *show / hide move track* button.

### Warnsdorff Degrees

Overlays each legal destination with its **degree** — the number of unvisited path squares reachable from that square after moving there.

- In **Mined Maze**, degrees are computed over squares confirmed as path squares and grow more informative as your knowledge grows.
- In **Mined Control**, degrees are computed over the active player's forward path, excluding known mines. On the very first move they reflect the full forward path; they become more accurate as mines are discovered.

> **Note:** Degrees are uninformative on the very first move before any safe squares have been confirmed.

Toggle with **H** (in-game only).

### Peek Mode

Reveals the full hidden path overlaid on the board, including the complete sequence of path squares numbered in order. In Mined Maze, the current piece position is also shown in the left panel thumbnail. In Mined Control, the target middle square is highlighted. Use peek sparingly — it reveals the complete solution. Toggle with **P** or the *peek / hide* button.

---

## Endgame & Replay

### Win & Loss Conditions

**Mined Maze**

| Outcome | Condition | Message |
|---|---|---|
| ✅ Win | Piece reaches the target square | *maze completed* |
| ❌ Blocked | No remaining path moves are reachable | *no legal moves* |
| ❌ Timeout | Clock expires | *time's up* |
| ❌ Resign | You press resign / ESC | *resigned* |

**Mined Control**

| Outcome | Condition | Message |
|---|---|---|
| ✅ Blue wins | Player 1 reaches the middle target square | *blue wins* |
| ✅ Red wins | Player 2 reaches the middle target square | *red wins* |
| ✅ Blue wins (stuck) | Both stuck; Blue is closer to the middle | *blue wins* |
| ✅ Red wins (stuck) | Both stuck; Red is closer to the middle | *red wins* |
| 🤝 Draw | Both stuck at equal distance from the middle | *draw* |
| ❌ Blue resigned | Player 1 presses resign / ESC | *blue resigned* |
| ❌ Red resigned | Player 2 (bot) resigns | *red resigned* |
| ❌ Timeout | Clock expires | *time's up* |

### Retry

The **retry** button replays the exact same puzzle (same seed, same hidden path) so you can apply what you learned about mine positions and attempt a cleaner run. Available as long as a puzzle seed was recorded.

### Undo

The **undo last move** button (or **U**) steps back one move at a time. There is no undo limit.

- In **Mined Maze**, undoing a move that triggered a mine in bounce mode restores your pre-bounce position.
- In **Mined Control**, undo steps back one **move pair** — the most recent half-move for each player together — to keep the turn sequence coherent. The per-move clock resets after an undo in per-move clock mode.

### Replay Mode

After any game ends, **start replay** enters a step-by-step review. Use the **`+`** button to advance one move forward and **`-`** to step one move backward. Board state, visited squares, mine markers, and piece positions all update to match each step. Combine with **peek mode** to overlay the hidden solution on your replay for a full post-mortem.

---

## Share Codes

Every generated puzzle receives a 16-character **share code** (base-32 encoded).

**Sharing a puzzle**

1. After starting a game the share code is displayed in the left panel.
2. Press **copy share code** to copy it to your clipboard.
3. Send the code to a friend — they will face the exact same hidden path and mine layout.

**Loading a shared puzzle**

1. On the Menu screen press **enter share code**.
2. Type or paste the 16-character code into the input box.
3. Press **start** — the identical path and configuration is reproduced.

**Encoded fields:**

| Field | Mined Maze | Mined Control |
|---|---|---|
| board | ✅ | ✅ |
| path length | ✅ | ✅ |
| blocks visibility | ✅ | ✅ |
| bounce mode | ✅ | ✅ |
| player one | — | ✅ |
| clock value | — | ✅ |
| RNG seed | ✅ | ✅ |

> Share codes let you challenge a friend to the same maze: in Mined Maze, whoever completes it with fewer mine triggers wins the meta-game; in Mined Control, whoever reaches the middle first wins.

---

## Statistics Display

**Mined Maze**

| Statistic | Description |
|---|---|
| **Moves** | Number of successful path steps taken this attempt (resets on bounce) |
| **Blocks** | Total number of mine squares triggered across all attempts |
| **Clock** | Countdown (if timed) or elapsed time (if untimed) |

**Mined Control**

| Statistic | Description |
|---|---|
| **Progress (blue)** | How far Player 1 has advanced along the path toward the middle (steps / total steps to middle) |
| **Progress (red)** | How far Player 2 has advanced along the path toward the middle (steps / total steps to middle) |
| **Mine hits (blue)** | Total number of mines triggered by Player 1 across all attempts |
| **Mine hits (red)** | Total number of mines triggered by Player 2 across all attempts |
| **Whose turn** | Highlighted in the active player's colour during play |
| **Clock** | Countdown (if timed) or elapsed time (if untimed) |

In **bounce** mode, progress resets each time a player is bounced back to the start. The mine hit count accumulates across all attempts and does not reset on bounce.

---

## Bot AI (Mined Control)

The bot AI is implemented in `minedcontrol_bot.py` and uses a **confusion model**: at each difficulty level the bot knows the correct next path square but deliberately ignores that knowledge — and all mine knowledge — with a fixed probability, picking a completely random move instead. This produces genuine mine hits at every level and in every mode, making the bot realistically imperfect.

The correct forward move for the bot is determined by its direction of travel:
- **Player 1 (Blue)**: moves toward squares with *higher* path index.
- **Player 2 (Red)**: moves toward squares with *lower* path index.

### Level 1 — Pure Random

Selects a random reachable square with no path or mine awareness. Hits mines constantly. Use this to learn the controls or watch a chaotic demonstration.

### Level 2 — High Confusion

**80 % confusion rate.** Most moves are random — likely to hit mines. Occasionally follows the correct path. Suitable for absolute beginners.

### Level 3 — Medium Confusion

**40 % confusion rate.** Follows the path more often than not, with a fair number of wrong turns producing mine hits. A human with basic mine-deduction skills will win consistently.

### Level 4 — Low Confusion

**25 % confusion rate.** Mostly path-following with occasional accidental mine hits. A decent human player will need to work for the win.

### Level 5 — Very Low Confusion

**10 % confusion rate.** Nearly always takes the correct path step. Still genuinely imperfect — a skilled human who has deduced the path can beat it, especially in bounce + hide mode where the bot's occasional wrong turns waste more turns.

> **Note:** The confusion model ensures that Level 5 is not a solved, always-winning opponent. The bot is designed to be beatable by any attentive player even on the hardest setting.

---

## Advanced Strategy

### Mined Maze Strategy

**Learn the Mine Map First**

In **bounce + hide** mode (hardest), treat early attempts as a reconnaissance phase. Deliberately probe adjacent squares to map out mines before committing to the full run. Your mine count will be high, but the payoff is a clean run once you know the safe route.

**Use Show Mode to Build a Logical Map**

In **show** mode, each mine marker permanently narrows down the valid path. After two or three bounce resets you may have enough information to deduce the remainder of the path purely through elimination — no guessing required.

**Warnsdorff as a Heuristic**

On the very first attempt (no mine knowledge yet), Warnsdorff Degrees can guide you toward squares that keep the most onward options open — the same heuristic used by the path generator itself. This does not guarantee a correct guess, but it biases you toward locally safer choices.

**Counting Path Length**

The stats panel shows how many squares the path has (visible as a numbered sequence in peek mode). On subsequent attempts, counting confirmed safe squares lets you estimate how far the target is — useful for deciding whether to probe a risky branch.

**Clock Management**

- Use `clock = 0` (unlimited) when learning a new piece or working through a hard bounce+hide puzzle.
- Short clocks (30–60 seconds) combined with bounce mode create a high-pressure deduction sprint.
- Timed + bounce + hide is the competitive format: fewest mines triggered, fastest time.

### Mined Control Strategy

**Racing vs. Mining**

Your primary goal is to reach the middle quickly. Your secondary constraint is avoiding mines. These two objectives conflict: the fastest path may go through unknown territory (high mine risk), while the safest path may cost extra turns of caution. Calibrate based on how much progress your opponent has made.

**Use Mine Hits as Information**

Every mine you trigger tells you a square is *not* on the path. In `show` mode these markers persist and can help you deduce which adjacent squares the path must pass through. After two or three mine hits near a branch point you may be able to eliminate all wrong turns and commit to the correct route.

**The Continuation Rule**

If your opponent is temporarily stuck (no legal path moves), the game does not switch turns — **you keep moving**. Recognise when your opponent's visible progress has stalled and use those extra turns to sprint toward the middle.

**Bounce Mode Racing**

In bounce mode a single mine hit resets your entire progress:
- **Reconnaissance is worth it.** Deliberately probe adjacent squares early, even if it triggers a mine and bounces you back, to map the safe route before committing to a full run.
- **Watch your opponent's progress.** If they are well ahead and in stay mode, you may need to take risks to close the gap. If they have been bounced back too, the race resets symmetrically.

**Clock Management**

- Use `clock = 0` (unlimited) when learning the game or a new piece.
- **Per-game** clock rewards consistent, efficient play — no single move can run you out of time.
- **Per-move** clock is punishing: a mine hit costs you a full turn-clock, giving your opponent a free move while you recover. Stay calm under pressure.

**Piece Choice**

The piece type fundamentally changes the path structure and the spacing of mines:
- **Knight**: Non-linear L-shaped moves create paths that double back and cross themselves. Mines are spread widely, making deduction genuinely challenging.
- **King**: Every adjacent square is reachable — very high mine density near any position. Local deduction is easier but there are more candidates per turn.
- **Rook / Queen**: Long-range sliders take large strides. The path covers the board in sweeping lines; probing one direction eliminates many candidates at once.
- **Exotic pieces**: Try zodiac or planetary variants for completely unfamiliar path structures. The bot's confusion model operates the same regardless of piece — human deduction of an unusual piece's path structure is a genuine advantage.

---

## Architecture & Technical Notes

### Mined Maze

| Module | Role |
|---|---|
| `minedmaze_v02.py` | Entry point — pygame init, window setup, main loop |
| `minedmaze_controller.py` | Game state machine, move logic, mine handling, rendering |
| `maze_generator.py` | Procedural path and obstacle generation |

### Mined Control

| Module | Role |
|---|---|
| `minedcontrol_v01.py` | Entry point — pygame init, window setup, main loop |
| `minedcontrol_controller.py` | Game state machine, two-player logic, mine handling, rendering, event handling |
| `minedcontrol_bot.py` | AI move selection at five difficulty levels |
| `minedmaze/maze_generator.py` | Shared path and obstacle generation (imported directly) |

### Generator Algorithm (`maze_generator.py`)

`generate_maze_path_and_obstacles()` attempts up to `max_attempts` random walks (default 200) within a `time_budget` (default 1.0 second). Each attempt:

1. Picks a random starting square on the n×n grid.
2. Extends a path by randomly choosing one of the piece's legal moves to an unvisited, unblocked square.
3. At each step, all *other* reachable squares that were not chosen become **obstacles (mines)**.
4. The walk terminates when no moves are available or the path reaches `max_length`.

If the resulting path length falls within `[min_length, max_length]`, the attempt succeeds. Otherwise the attempt is discarded and a new random start is tried. If all attempts fail, the minimum length requirement is progressively relaxed before giving up.

In Mined Control the path is forced to odd length by trimming the last square if needed — guaranteeing an exact middle square for the target.

This construction guarantees that every obstacle was explicitly *reachable but not chosen* at some step — meaning each mine is a valid move from at least one path square and is logically discoverable through gameplay.

### Controller Architecture

Both controllers inherit from `BaseGameController` and override the same abstract methods:

| Method | Responsibility |
|---|---|
| `_game_specific_start_setup()` | Generates path and obstacles, places player(s) at starting positions |
| `_validate_move()` | Checks the target square is reachable by the piece |
| `_game_specific_make_move()` | Handles mine collisions (flash / permanent mark, bounce or stay) and increments counters |
| `_check_endgame_conditions()` | Detects target reached or no-remaining-moves conditions |
| `_update_legal_moves()` | Recalculates legal moves (direction-constrained for Mined Control) |
| `_calculate_hint_degrees()` | Warnsdorff degrees over confirmed path squares |
| `_capture_game_state()` | Snapshots state for undo/replay |
| `_restore_game_state()` | Restores a snapshot |

In Mined Control, legal moves are further constrained by direction of travel:
- Player 1: only path squares with a *higher* path index than the current position.
- Player 2: only path squares with a *lower* path index than the current position.

When `blocks = show`, effective mines are all known obstacles. When `blocks = hide`, effective mines are only the squares that player has triggered personally.

**Mine flash animation** is handled in `update()`: flashing mine entries are stored as `(square, timestamp)` pairs and removed from the flash list after 2 seconds.

### Bot Architecture (`minedcontrol_bot.py`)

`make_bot_move()` dispatches to one of two internal strategies:

| Function | Purpose |
|---|---|
| `_level1_move()` | Random move from valid maze squares (path or obstacle) |
| `_leveln_move()` | Path-aware move with graduated confusion rate (Levels 2–5) |

A separate `_maze_moves()` filter ensures the bot never selects neutral squares, which would cause `make_move()` to silently ignore the input and leave the bot permanently stuck.

### Codec System

Puzzle parameters are packed into a 16-character base-32 share code:

| Field | Bits | Mined Maze | Mined Control |
|---|---|---|---|
| board | 4 | ✅ | ✅ |
| length | 2 | ✅ | ✅ |
| blocks | 1 | ✅ | ✅ |
| bounce | 1 | ✅ | ✅ |
| player_one | 1 | — | ✅ |
| clock | 6 | — | ✅ (0–330 s, stored in minutes) |

The RNG seed is embedded in the remaining bits, fully reproducing the maze on any machine.

### State Snapshots

After every successful path move, `_capture_game_state()` stores a full snapshot. In Mined Control the snapshot includes both players' positions, visited sets, visited move numbers, known mines, permanent mine markers, attempt counts, the union visited set, and the current player. This snapshot list powers both the unlimited undo stack and the post-game step-through replay.

---

## Known Limitations

1. **Path length forced to odd (Mined Control)** — if the generator produces an even-length path it is trimmed by one square, which may produce a path slightly shorter than the target minimum on congested boards.
2. **No path optimality guarantee** — the greedy random walk may produce shorter-than-ideal paths on congested boards; the generator falls back to progressively relaxed length requirements before giving up.
3. **Bot confusion is uniform (Mined Control)** — the confusion model uses a fixed per-level probability regardless of board position, path length, or proximity to the target. A smarter adaptive bot is on the wishlist.
4. **Warnsdorff Degrees are path-constrained** — hint degrees reflect only confirmed path squares, so they are uninformative on the very first attempt before any safe squares are known.
5. **Replay memory is unbounded** — long games with many undo steps accumulate many state snapshots in memory.
6. **Clipboard fallback** — on Linux, clipboard copy may silently fail if `xclip` / `xsel` are not installed.
7. **No human-vs-human local play (Mined Control)** — the `player one` setting only controls whether you play as Blue or whether the bot plays both sides. Local two-human play on separate input devices is not supported.

---

## Credits

Developed by **paw309**.  
Built with [Python](https://www.python.org/) and [pygame](https://www.pygame.org/).  
Inspired by the classic *Minefield* deduction genre and the mathematical elegance of the Knight's Tour.

---

> **Mined Maze** — *The path is there. Can you find it?*  
> **Mined Control** — *The path is there. So is your opponent. Who reaches the middle first?*