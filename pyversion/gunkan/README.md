# ⚔️ Gunkan

> *Two players. Hidden polyominoes. A race to destroy your opponent's fleet before they destroy yours.*

**Gunkan** is a two-player competitive strategy game that fuses the hidden-information tension of *Battleship* with the combinatorial depth of Hamiltonian path puzzles. Each player commands a fleet of secret polyomino shapes embedded in the board. You cannot see your opponent's shapes — only the squares you have visited. Move your piece, explore the board, and hunt down every cell of your opponent's fleet before they find yours.

The game is named after the **Gunkan piece** — a fairy chess leaper that can jump to *any* square reachable by a coprime vector `(r, s)` where `gcd(r, s) = 1`. It is one of the most mobile pieces in the library, threading across the board in patterns no standard chess piece can match.

---

## 🎯 Objective

Each player has a hidden set of polyomino shapes placed on their side of the board. Your goal is to **land on every cell of your opponent's shapes** before they land on every cell of yours.

- You win by **fully discovering all of your opponent's shape units**
- You lose if your opponent discovers all of yours first
- If neither player can make a legal move, the player with more **opponent units discovered** wins

Because both players are simultaneously building Hamiltonian paths on the same board, every move has two dimensions: keeping your own path alive *and* hunting down the enemy fleet.

---

## 🗺️ How It Works

### The Board

The game is played on a shared square grid (8×8 to 16×16, default 14×14). Both players start on separately chosen starting squares and alternate turns, each extending their own Hamiltonian path — visiting squares **exactly once**.

### Hidden Shapes

Before the game begins, the engine secretly places a set of polyomino shapes on the board for each player. These shapes are **invisible** to the opponent. As you move your piece, you **discover** enemy shape cells when you land on them — they light up, revealing part of the hidden fleet.

Your own shapes are also hidden from *you* — the board is symmetric in secrecy. You know where your piece has been; you do not know the full layout until the game ends.

### Discovery

Landing on a square that belongs to your opponent's fleet **reveals that cell**. Completed shapes (all cells found) are fully highlighted. The stats panel tracks how many units and complete shapes you have found.

### Endgame

The game ends when:
- One player has discovered **all opponent shape units** → that player wins
- A player has **no legal moves** remaining → the player with more opponent units discovered wins
- A player **resigns** → the opponent wins
- The **chess clock** expires for one player → that player loses on time
- The **bot resigns** when it determines its position is unwinnable → you are offered to accept

---

## 🧩 Shape Sets

Two shape modes are available:

### Classic
A fixed, deterministic set of five polyominoes:

| Shape | Size | Cells |
|-------|------|-------|
| Domino (dom-001) | 2 | 2 |
| Triomino (tri-001) | 3 | 3 |
| Triomino (tri-001) | 3 | 3 |
| Tetromino (tet-001) | 4 | 4 |
| Pentomino (pen-001) | 5 | 5 |

Total: **17 cells** per player's fleet, placed in randomised positions and orientations each game.

### Mixed
A procedurally generated selection of polyominoes drawn from the full piece library, subject to a **maximum combined board density of 34%**. Shapes are chosen randomly from all valid polyominoes (excluding even-parity pieces: bishop, delta, theta, lambda, xi). The result is a different fleet composition every game — you may face anything from a cluster of dominoes to a spread of hexominoes.

---

## ♞ The Gunkan Piece

The Gunkan piece leaps to any square `(r, s)` away where `gcd(r, s) = 1` — all *coprime* jump vectors. This includes:

- The knight's (2,1) jump
- The camel's (3,1) jump
- The zebra's (3,2) jump
- Every other coprime leaper simultaneously

On large boards, the Gunkan piece has extraordinary reach and mobility. This makes routing decisions tactically rich: the piece can thread almost anywhere, but the Hamiltonian constraint (no revisits) means every move permanently closes off a square.

---

## ⚙️ Settings

| Setting | Options | Default |
|---------|---------|---------|
| **Board size** | 8 × 8 – 16 × 16 | 14 × 14 |
| **Shapes** | Classic · Mixed | Classic |
| **First move** | Human · Bot | Human |
| **Bot level** | 1 – 5 | 1 |
| **Clock** | Off · 30 s – 5 min (in 30 s steps) | Off |

---

## 🤖 Bot Opponent

Gunkan includes a five-level AI opponent (`duelomino_bot.py`), each level building on the last:

| Level | Strategy |
|-------|----------|
| **1 – Random** | Picks any legal move at random |
| **2 – Safe** | Avoids moves that lead to immediate dead ends; falls back to any legal move if all are dead-ends |
| **3 – Warnsdorff** | Applies Warnsdorff's heuristic (prefer moves with fewest onward options) after filtering dead-ends |
| **4 – Tactical** | Warnsdorff + two-ply lookahead + centre proximity + **polyomino domain scorer** (prioritises moves that reveal opponent shape units) |
| **5 – Strategic** | All of Level 4 + **opponent modelling** (minimises your future legal options while maximising its own shape discoveries) |

> **Tip:** Level 3 plays a solid Hamiltonian path but ignores your shapes. Level 4 actively hunts your fleet. Level 5 does both while trying to cut off your routes.

### Bot Resignation

At higher levels, the bot evaluates whether its position is recoverable. If it determines the gap in shape discoveries is too large to close, it will offer to resign rather than play out a lost game. You can **accept** to end the game or **decline** to continue playing.

---

## 🎮 Controls

### Mouse
| Action | Result |
|--------|--------|
| Left-click a highlighted square | Move your piece to that square |
| Left-click your starting square (game start) | Commit your starting position |
| Left-click buttons | Activate UI functions |

### Buttons (during game)

| Button | Function |
|--------|----------|
| **Hint** | Toggle Warnsdorff degree overlay on legal moves |
| **Guide** | Toggle legal move arrows |
| **Reveal Shapes** | Show all shape positions (endgame) |
| **Undo** | Retract last move (returns to previous board state) |
| **Resign** | Concede the game |
| **Replay** | Step through the completed game move by move |
| **New Game** | Return to the menu |
| **Codec** | Enter or copy a puzzle share code |

### Keyboard
| Key | Action |
|-----|--------|
| `ESC` | Quit |

---

## 🔢 Puzzle Share Codes

Every Gunkan game configuration can be encoded into a **compact alphanumeric share code**. The code encodes:

- Board size
- Shape set (classic / mixed)

Enter a code in the codec input on the menu screen to reproduce an exact board layout. Share codes let you and a friend play on identical shape configurations and compare results.

---

## 🕹️ Game Modes

### Standard Game
Configure your settings and click **Start**. Both players choose their starting squares, then alternate turns until the game ends.

### Blind Draw
Settings are hidden until the game concludes — you do not know the board size or shape set until the final screen. Tests your adaptability with the Gunkan piece across unknown configurations.

### Replay Mode
After a game ends, step through every move in sequence to review decisions. Useful for identifying the turning point where the hunt succeeded or failed.

---

## 💡 Strategy Guide

### Opening: Choosing Your Start Square

Your starting square determines the regions you can reach early. Consider:
- **Central starts** give the Gunkan piece maximum early reach across the board.
- **Edge starts** can be efficient for sweeping a section of the board but may leave the opposite corner unreachable late in the game.
- Your starting square is also your first revealed position — the opponent will orient their path around it.

### Hunting the Fleet

You cannot see the opponent's shapes, but you can infer their location:
- **Revealed units** show which cells are part of a shape. Use adjacent movement patterns to find remaining cells of a partially discovered shape.
- **Shape geometry**: in Classic mode, you know there are exactly two triominoes, one tetromino, and one pentomino. When you find a cell, you know which shapes are still unaccounted for.
- **High-traffic zones**: shapes are placed with placement constraints — they will not overlap the edge in certain configurations. The centre of the board tends to have higher shape density.

### Path vs. Hunt Trade-offs

Every move is simultaneously:
1. **A routing decision** — keeping your Hamiltonian path viable
2. **A hunting decision** — maximising the chance of hitting opponent shape cells

At low bot levels, you can afford to route freely and hunt opportunistically. At Level 4–5, the bot prioritises your shape cells actively — you must balance exploration with keeping your path alive.

### Endgame Squeeze

As the board fills up, dead-end threats become critical. Use the **Hint** overlay (Warnsdorff degrees) to spot squares with low onward options — avoid routing yourself into a corner while your opponent still has open space to hunt.

---

## 🏗️ Architecture

Gunkan inherits from the shared `BaseGameController` in `sharedlib/`, implementing eight game-specific methods:

| Method | Role |
|--------|------|
| `_game_specific_start_setup()` | Generates and places hidden shape sets for both players |
| `_game_specific_make_move()` | Applies a move, checks for unit discovery |
| `_validate_move()` | Confirms the target square is a legal Gunkan leap from the current position |
| `_check_endgame_conditions()` | Detects fleet completion, no legal moves, resignation, or timeout |
| `_check_bot_resignation_condition()` | Evaluates whether the bot's position is unwinnable |
| `_capture_game_state()` | Serialises board state for undo / replay |
| `_restore_game_state()` | Restores a serialised board state |
| `_render_game_specific_board()` | Draws the board with player paths, discovered shapes, and overlays |

The bot AI lives in `duelomino_bot.py` and is shared with the Duelomino game. Domain-specific scoring (polyomino unit discovery) is injected via a `domain_scorer` callable passed to the shared `select_with_heuristics()` function in `bot_utils.py`.

### Layout Generation

**Classic layout** places the fixed five-shape set using constrained random placement with up to 2,000 attempts per shape to find a valid non-overlapping position.

**Mixed layout** selects shapes from the globally valid piece pool (excluding even-parity pieces) and places them iteratively with per-shape attempt limits (400 per shape), subject to a combined density ceiling of 34%.

---

## 🚀 Running the Game

From the repository root:

```bash
python gunkan/gunkan_v01.py
```

Or launch from the unified launcher:

```bash
python launcher_v01.py
```

Select **Gunkan** from the game list and click **Launch**.

### Requirements

- Python 3.7+
- pygame

```bash
pip install pygame
```

---

## 📁 File Structure

```
gunkan/
├── gunkan_v01.py          # Entry point and main loop
├── gunkan_controller.py   # GunkanController, layout generators, Polyomino/PuzzleShape classes
├── README.md              # This file
```

Shared dependencies (in `sharedlib/`):

| Module | Role |
|--------|------|
| `base_game_controller.py` | Abstract controller: undo, replay, clock, codec, UI |
| `gameboard.py` | `BoardModel` + `BoardRenderer` |
| `piecekeeper.py` | Piece definitions and legal move generation |
| `bot_utils.py` | `get_legal_moves`, `select_warnsdorff_move`, `select_with_heuristics`, `filter_non_dead_ends` |
| `puzzle_codec.py` | Share code encoding/decoding |
| `chess_clock.py` | Countdown and elapsed clock |

Bot AI (in `duelominoes/`):

| Module | Role |
|--------|------|
| `duelomino_bot.py` | Five-level bot: `make_bot_move()`, level dispatch, polyomino domain scorer |

---

*Gunkan — hide your fleet, hunt theirs, and never revisit a square.*
