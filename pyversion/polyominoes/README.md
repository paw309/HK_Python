Polyomino & Duelomino

Polyomino is a single-player puzzle: navigate a board with a chess piece, visiting each square only once (a Hamiltonian path), and discover as many hidden polyomino shapes as you can before you run out of legal moves.

Duelomino is the competitive variant of Polyomino — human versus bot. Both players share the same board, alternating turns to claim more polyomino units than their opponent before neither can move.

Both games are built on the same engine and share the same core mechanics. This README covers both.
Table of Contents

    Overview
        Polyomino — Solo Puzzle
        Duelomino — Competitive
    Getting Started
    Game Configuration
        Board Size
        Piece Selection
        Shapes
        Density
        Colors
        Game Mode (Polyomino only)
        First Move (Duelomino only)
        Opponent & Level (Duelomino only)
        Clock (Duelomino only)
    How to Play
        Polyomino
        Duelomino
    Scoring
        Polyomino Scoring
        Duelomino Scoring
    Square Color Guide
    In-Game Controls
        Mouse
        Keyboard Shortcuts
    HUD & Overlays
        Move Guide
        Move Track (Polyomino)
        Warnsdorff Degrees
        Peek Mode
        Reveal All Shapes
    Bot AI (Duelomino)
    Endgame
        Win & Loss Conditions
        Retry
        Undo
        Replay Mode
    Share Codes
    Strategy
        Polyomino Strategy
        Duelomino Strategy
    Architecture & Technical Notes
    Known Limitations
    Credits

Overview
Polyomino — Solo Puzzle

A polyomino puzzle is scattered — invisibly — across the board before the game starts. The puzzle is made up of one or more shapes (monominos, dominoes, trominoes, tetrominoes, pentominoes, or larger), each composed of several connected unit squares. The shapes are hidden; you only learn where a unit is when you land on it.

You move a single chess piece across the grid, visiting each square only once (a Hamiltonian path). Every polyomino unit you land on is discovered and added to your score. The game ends when you have no legal moves remaining or all shapes have been found.

Two game modes are available:

    Freestyle — choose all settings, preview the puzzle layout in real time, and replay the same puzzle after completion.
    Blind Draw — all settings except piece choice are randomised; board size, shapes, density, and colors are hidden until the game ends.

Duelomino — Competitive

Duelomino puts two players on the same board with the same rules: visit each square only once and claim polyomino units by landing on them. The player who claims more units when neither player can move wins.

Every move one player makes permanently removes that square from both players' legal move sets. This creates a second strategic layer — beyond routing yourself through shapes, you must also track and impede your opponent.

Play against a friend (hot-seat) or challenge the built-in AI at one of five difficulty levels.
Getting Started

Requirements

    Python 3.7 or later
    pygame (pip install pygame)
    The full Hamiltonian-Knights repository (shared libraries are loaded from sharedlib/ and polyominoes/)

Run Polyomino

cd Hamiltonian-Knights
python polyominoes/polyomino_v16.py

Run Duelomino

cd Hamiltonian-Knights
python duelominoes/duelomino_v01.py

The window opens at your current display resolution and is fully resizable. On Windows the window is automatically maximised.
Game Configuration

All settings are adjusted from the Menu screen using the < and > buttons on each row. In Polyomino, a live preview updates instantly as you change settings. Duelomino uses the same row-based menu with additional competitive settings.
Board Size
Setting 	Range 	Default
Board 	5 × 5 to 16 × 16 	8 × 8

Larger boards allow longer paths and more room for polyominoes, but also dilute shape density and increase game length. The minimum valid board size adjusts automatically depending on the piece chosen.
Piece Selection

Both games draw pieces from the piecekeeper module. Colour-bound pieces (bishop, ferz, alfil, dabbaba) are excluded because they cannot reach all squares on the board.

Available pieces include:

    Standard: knight, rook, queen, king, and variants
    Exotic leapers: gamma, sigma, phi, psi, omega, camel, ceres, pallas, juno, vesta, chiron, and more
    Multi-range: aries, gemini, virgo, libra, scorpio, sagittarius, capricorn, aquarius, pisces, fibonacci, gunkan, and more

In Duelomino, even-parity pieces (delta, theta, lambda, xi) are also excluded to ensure both players have fair access to the full board.

Pieces are rated on two dimensions relevant to Polyomino's challenge rating:

    Mobility Rating (0–5): How effectively the piece covers the board at a given size.
    Agility Rating (0–5): How well the piece navigates around a specific shape type.

Piece group 	Best board size
King, Wazir (short-range) 	5–8
Knight, Camel, Ceres, Pallas, Juno, Vesta, Chiron 	8–12
Rook, Queen (long-range sliders) 	11–16
Multi-range pieces 	Varies by piece
Shapes

Controls which polyomino size (or mix) is used to build the puzzle layout.
Choice 	Cell count 	Description
monomino 	1 	Single-unit squares
domino 	2 	2-unit shapes
triomino 	3 	3-unit shapes
tetromino 	4 	4-unit shapes (5 distinct shapes)
pentomino 	5 	5-unit shapes (12 distinct shapes) — default
hexomino 	6 	6-unit shapes (35 distinct shapes)
heptomino 	7 	7-unit shapes (108 distinct shapes)
octomino 	8 	8-unit shapes (Duelomino only)
mixed 	1–7 (or 1–8) 	Random mix of sizes

Each shape can appear in multiple orientations through rotation and reflection. Larger polyomino types create denser clusters of units that reward tactical pathing.
Density

Controls how much of the board is covered by polyomino units.
Choice 	Polyomino coverage 	Duelomino coverage
low 	~10% of squares 	Sparse
medium 	~20% of squares 	Moderate — default
high 	~25% of squares 	Dense

Higher density increases scoring opportunities but also makes routing more constrained. In Duelomino, higher density also makes the opponent's interference more punishing.
Colors

Controls how polyomino shapes are colored on the board.
Choice 	Description 	Difficulty
unique 	Each shape gets a distinct color — default 	Easiest
random 	Colors assigned randomly (may repeat between shapes) 	Moderate
same 	All shapes share one color 	Hardest

unique is recommended for beginners as it makes shape boundaries immediately visible once a unit is revealed.
Game Mode (Polyomino only)
Mode 	Description
Freestyle 	Choose all settings; live preview shows a sample layout; retry available after completion
Blind Draw 	All settings except piece are randomised and hidden; revealed at game end; guaranteed to be a playable combination
First Move (Duelomino only)
Choice 	Who moves first
human 	The human player (Player 1 / Blue) moves first — default
bot 	The bot (Player 2 / Red) moves first

In human-vs-human mode this setting is ignored and Player 1 always goes first.
Opponent & Level (Duelomino only)
Opponent 	Description
Human 	Both players share the same keyboard and screen (hot-seat)
Bot 	Player 2 is controlled by the AI at the selected difficulty level (1–5)
Level 	Strategy summary
1 	Random legal move
2 	Avoids dead-end squares
3 	Warnsdorff's rule + dead-end avoidance
4 	Warnsdorff + two-ply lookahead + centre proximity + polyomino scoring
5 	All of Level 4 + opponent modelling

See Bot AI for the full breakdown of each level's strategy.
Clock (Duelomino only)

Sets a time budget per player in seconds. 0 means unlimited (an elapsed timer is shown instead).
Range 	Default
0 to 31 minutes (in 60-second increments) 	0 (no limit)

When a player's clock reaches zero they lose immediately.
How to Play
Polyomino

    Configure your game on the Menu screen: choose mode, piece, board size, shapes, density, and colors.
    In Freestyle mode, observe the live preview updating as you adjust settings. Check the challenge rating for difficulty.
    Press start to generate a new puzzle.
    Choose a starting square by clicking any cell — you cannot return to it, so choose wisely.
    Click a highlighted square to move your piece there. Only legal, unvisited moves are shown.
    When you land on a polyomino unit it is revealed and scored.
    Continue until you have no legal moves remaining or all shapes are found.

Duelomino

    Configure your game on the Menu screen: choose piece, board size, shapes, density, colors, opponent, level, and clock.
    Press Start.
    Each player chooses a starting square by clicking anywhere on the board. Players alternate placing their start squares.
    Players alternate turns. On your turn, click any highlighted square — squares visited by either player are never legal targets.
    When you land on a polyomino unit it is revealed and claimed by you permanently.
    The bot takes its turn automatically after a short delay (500–800 ms).
    When one player runs out of legal moves, the other continues until they too are trapped or time expires.
    The player with more units when both are trapped (or time expires) wins.

Scoring
Polyomino Scoring
Component 	Points
Unit Score (max 1000) 	Based on polyomino cells discovered; partial credit for incomplete shapes
Shape Score (max 1000) 	Based on complete shapes found; bonus for finishing entire shapes
Completion Score 	Unit Score + Shape Score (max 2000)
Challenge Rating 	Multiplier based on piece mobility, agility, board size, shape complexity, density, and color scheme
Final Score 	Completion Score × Challenge Rating

High scores require both thorough exploration and choosing challenging settings.
Duelomino Scoring

    Each polyomino unit square claimed is worth 1 point.
    The player with more units when the game ends wins.
    If unit counts are equal at game end, the result is a draw.
    Squares with no polyomino unit score nothing.

Square Color Guide
Color 	Polyomino meaning 	Duelomino meaning
Ivory / Tan 	Unvisited square (light/dark board pattern) 	Unvisited square
Gray 	Visited — no unit on that square 	Visited by either player — no unit
Blue (light/dark) 	— 	Visited by Player 1 — no unit found
Red (light/dark) 	— 	Visited by Player 2 — no unit found
Shape color 	Discovered polyomino unit 	—
Shape color (tinted blue) 	— 	Polyomino unit claimed by Player 1
Shape color (tinted red) 	— 	Polyomino unit claimed by Player 2
In-Game Controls
Mouse
Action 	Effect
Click a start square (setup phase) 	Commit your starting position
Click a highlighted legal-move square 	Move your piece there
Click a menu < / > button 	Cycle through that setting's values
Click any button 	Activate that button's action
Keyboard Shortcuts
Key 	Context 	Action
G 	Any 	Toggle Move Guide overlay
T 	Any 	Toggle Move Track overlay (Polyomino)
H 	In-game 	Toggle Warnsdorff Degrees hint overlay
P 	Any 	Toggle Peek mode (full puzzle thumbnail)
U 	In-game 	Undo last move
ESC 	In-game 	Resign current game
ESC 	Endgame 	Go to main menu
M 	Any 	Minimise window
HUD & Overlays
Move Guide

Displays directional arrows from the active player's current square to every legal destination. Helpful for scanning the board quickly. Toggle with G or the show / hide move guide button.
Move Track (Polyomino)

Overlays each visited square with the move number on which you visited it. Useful for reviewing your path and identifying where routing went wrong. Toggle with T or the show / hide move #'s button. (Not available in Duelomino.)
Warnsdorff Degrees

Overlays each legal destination with its degree — the number of unvisited squares reachable from that square after moving there. Lower degrees indicate squares that will become dead ends sooner. Preferring higher-degree moves preserves mobility. Toggle with H or the show / hide degrees button.
Peek Mode

Reveals a miniature thumbnail of the entire board in the side panel, showing the full puzzle layout (all polyomino shapes and their positions). Use this to plan multistep routes through dense shape clusters. Toggle with P or the peek / hide button.
Reveal All Shapes

A separate toggle that overlays the complete puzzle on the main board at full size, making all hidden units visible. Useful for post-game analysis or accessibility. Toggle via the reveal / hide shapes button.
Bot AI (Duelomino)

The bot AI lives in duelomino_bot.py and exposes five difficulty levels via make_bot_move(). Each level builds on the previous.
Level 1 — Random

Selects a uniformly random legal move. No strategy. Good for very young players or as a baseline.
Level 2 — Dead-End Avoidance

Filters out moves that would leave the bot with zero onward options (dead ends). Chooses randomly among the remaining safe moves. Falls back to any legal move if all options are dead ends.
Level 3 — Warnsdorff's Rule

Applies Warnsdorff's heuristic: among non-dead-end moves, prefer the square with the fewest onward moves from that position. This tends to keep large connected regions of the board accessible for longer.
Level 4 — Multi-Heuristic

Combines several heuristics applied in priority order:

    Dead-end avoidance — eliminate immediately fatal moves.
    Polyomino domain score — prefer moves that reveal new polyomino units.
    Warnsdorff degree — among equal-scoring moves, prefer lower degree.
    Two-ply lookahead — simulate the bot's next move from each candidate and pick the one that leaves the best position.
    Centre proximity — prefer central squares (more future connectivity).
    Random tie-breaking — uniform random among equals.

No opponent modelling at this level — the bot optimises purely for its own position.
Level 5 — Opponent Modelling

All of Level 4, plus:

    Opponent modelling — after scoring each candidate by the Level 4 criteria, additionally evaluates how many legal moves the opponent would have after the bot moves there. Prefers moves that minimise the opponent's options (interference strategy).

This level plays aggressively, trading its own positional quality to cut off the opponent from productive regions of the board. The bot may also resign when it determines it cannot improve its position.
Endgame
Win & Loss Conditions

Polyomino
Outcome 	Condition
✅ All shapes found 	Every polyomino unit discovered
✅ / ❌ Trapped 	No legal moves — scored based on units found
❌ Resign 	You press resign / ESC

Duelomino
Outcome 	Condition
✅ Win 	More polyomino units claimed than the opponent when play ends
🤝 Draw 	Equal unit counts at game end
❌ Timeout 	Your clock expires
❌ Trapped 	You have no legal moves (the other player continues)
❌ Resign 	You press resign / ESC
❌ Bot resigns 	Bot (Level 5) determines it cannot improve its position

When one Duelomino player runs out of legal moves, the other player continues until they too are trapped or time expires.
Retry

The retry button regenerates the exact same puzzle (same seed, same layout) so you can attempt a better strategy. In Polyomino, retry is only available in Freestyle mode.
Undo

The undo last move button (or U) steps back one half-move at a time. There is no undo limit. In Duelomino, undoing during a bot game reverts the bot's last move and your last move together, returning the turn to you.
Replay Mode

After a game ends, start replay enters a step-by-step review. Use the + and - buttons to step forward and backward through the move history. Board state, visited squares, and discovered units all update to reflect the selected move.
Share Codes

Every generated puzzle receives a compact share code (base-32 encoded) that captures the board parameters and RNG seed.

Sharing a puzzle

    After starting a game the share code is shown in the side panel.
    Press copy share code to copy it to your clipboard.
    Send the code to a friend.

Loading a shared puzzle

    On the Menu screen press enter share code.
    Type or paste the code.
    Press start — the identical puzzle layout is reproduced.

Encoded fields: board size, shape type, density, colors, and RNG seed. Piece selection is not encoded — players can try different pieces on the same puzzle layout.
Strategy
Polyomino Strategy

Think Ahead — Path Management

You can only visit each square once. Plan 3–5 moves ahead to avoid getting trapped, and always maintain multiple exit options. Dead ends are game over.

Piece Choice

    King / Wazir: Methodical coverage on small boards (5–8). Low challenge but good for learning.
    Knight and similar: Excellent balance of challenge and coverage on medium boards (8–12). Plan 2–3 moves ahead to avoid dead-end parity issues.
    Rook / Queen: Fast coverage on large boards (11–16). Must balance speed with thoroughness — long slides can accidentally isolate unvisited regions.
    Exotic / multi-range pieces: Variable; study the piece's movement pattern before committing to a large board.

Warnsdorff's Heuristic

Enable show degrees (H) and prioritise moves to the square with the lowest non-zero degree. This delays dead ends and keeps more of the board accessible.

Shape Sweeping

Use Peek mode (P) to identify large polyomino clusters. Route your piece to enter a cluster and sweep as many connected units as possible in consecutive moves. Sometimes it is better to leave a shape 90% complete and move on than to finish it and close off your path.

Density Considerations

    Low density: Finding shapes is the main challenge. Plan systematic coverage patterns.
    High density: Each completed shape creates barriers. Think like a puzzle solver — work backward from corners and plan which shapes to prioritise.

Game Mode Tips

    Freestyle: Use the live preview to understand how density and color settings look before committing.
    Blind Draw: Trust Warnsdorff degrees — without knowing shape positions you must rely on mobility heuristics.

Duelomino Strategy

Core Concepts

Every square visited by either player is gone forever. Think of each move not just as "where am I going?" but as "what am I cutting off — for myself and for my opponent?"

Mobility First

Running out of legal moves ends your scoring. Use Warnsdorff Degrees (H) to keep your degree high and avoid stranding yourself in a corner while the opponent still has room.

Shape Sweeping

Use Peek mode (P) to identify large polyomino clusters. Route your piece to enter a cluster and sweep as many connected units as possible in consecutive moves — this denies the entire cluster to the opponent.

Interference

At higher bot levels, the bot will deliberately move into squares that restrict your future options. Counter this by maintaining multiple viable corridors and never allowing yourself to be funnelled into a single escape route.

Opening

Choosing a starting square adjacent to a cluster of shapes gives early tempo. Prefer starting squares with high onward connectivity (central squares) rather than corners or edges.

Endgame

When the board is heavily visited, count your remaining legal moves and your opponent's. If you are ahead on units, play defensively — preserve your movement options. If you are behind, accept more risk and pursue units even at the cost of onward connectivity.

Bot-Specific Tips

    Level 1: Exploitable by simply moving toward shapes as fast as possible.
    Level 2: Avoids dead ends; contest shapes aggressively before the bot reaches them.
    Level 3: Applies Warnsdorff. Routing the bot into a dead end is more effective than racing it to individual units.
    Level 4: Plans two moves ahead. Start with a strong starting square and high initial connectivity.
    Level 5: Actively minimises your options. Prioritise positional play over immediate unit capture.

Architecture & Technical Notes
Polyomino
Module 	Role
polyomino_v16.py 	Entry point — Pygame init, window setup, main loop
polyomino_controller.py 	Game state machine, move logic, rendering, event handling
polyomino_data.py 	155 polyomino shape definitions
polyomino_ratings.py 	Challenge rating system (mobility × agility × complexity)

Scoring and statistics

Game statistics are automatically appended to endgamestats.csv after each game, including configuration, challenge rating, completion metrics, moves, elapsed time, and final score. Use this data to analyse which settings work best for different pieces and track personal improvement.
Duelomino
Module 	Role
duelomino_v01.py 	Entry point — Pygame init, window setup, main loop
duelomino_controller.py 	Game state machine, two-player logic, move handling, rendering
duelomino_bot.py 	AI move selection at five difficulty levels

Two-player state management

The controller maintains separate state for each player:

    player_pos[1], player_pos[2] — current positions
    visited[1], visited[2] — squares each player has visited
    found_units[1], found_units[2] — polyomino units claimed
    legal_moves[1], legal_moves[2] — cached legal moves (recomputed after each half-move)

all_visited is the union of both players' visited sets and is used to compute legal moves for either player.

Bot integration

make_bot_move() is called from _execute_bot_move() with a configurable delay (500–800 ms). domain_data passes (puzzle_layout, bot_found_units) to Levels 4 and 5 so the polyomino scorer can evaluate how many new units each candidate move would reveal.
Shared Libraries

Both games draw from sharedlib/ and polyominoes/:
Module 	Role
base_game_controller.py 	Undo stack, replay, clock, codec, button handling
gameboard.py 	BoardModel + BoardRenderer
piecekeeper.py 	Piece definitions and legal move generation
bot_utils.py 	get_legal_moves, select_warnsdorff_move, select_with_heuristics, filter_non_dead_ends
puzzle_codec.py 	Share code encoder/decoder
polyomino_data.py 	Shape definitions shared by both games

Codec system

Puzzle parameters are packed into a compact base-32 share code using a fixed schema:
Field 	Values
board 	5–16
shapes 	monomino … octomino / mixed
density 	low / medium / high
colors 	unique / random / same
Known Limitations

    Even-parity / colour-bound pieces excluded — bishop, ferz, alfil, dabbaba (and in Duelomino, delta, theta, lambda, xi) cannot visit every square and are removed from the piece list.
    Bot think time is fixed — the artificial delay (500–800 ms) is not configurable from the Duelomino menu.
    Two-ply lookahead only — Duelomino Level 4/5 lookahead is limited to two plies; deeper search would improve play quality but increases CPU cost.
    Replay memory is unbounded — long games accumulate many state snapshots.
    Clipboard fallback — on Linux, clipboard copy may silently fail if xclip / xsel are not installed.
    No path optimality guarantee — the random walk may produce shorter-than-ideal paths on congested boards; rare failures fall back gracefully.

Credits

Developed by paw309. Built with Python and pygame. Inspired by polyomino puzzles, chess movement, and competitive board games.

    Polyomino — Every square counts, and you can only visit each once. Duelomino — Outscore your opponent. Outsmart the board. Can you claim the most?

Table of Contents

    Overview
    Getting Started
    Game Configuration
        Board Size
        Piece Selection
        Shapes
        Density
        Colors
        First Move
        Level (Bot Difficulty)
        Clock
    How to Play
        Start Squares
        Taking Turns
        Discovering Polyomino Units
    Scoring
    Square Color Guide
    In-Game Controls
        Mouse
        Keyboard Shortcuts
    HUD & Overlays
        Move Guide
        Warnsdorff Degrees
        Peek Mode
        Reveal All Shapes
    Endgame
        Win & Loss Conditions
        Retry
        Undo
        Replay Mode
    Share Codes
    Bot AI
        Level 1 — Random
        Level 2 — Dead-End Avoidance
        Level 3 — Warnsdorff's Rule
        Level 4 — Multi-Heuristic
        Level 5 — Opponent Modeling
    Advanced Strategy
    Architecture & Technical Notes
    Known Limitations
    Credits

Overview

A polyomino puzzle is scattered — invisibly — across the board before the game starts. The puzzle is made up of one or more shapes (monominos, dominoes, trominoes, tetrominoes, pentominoes, or larger), each composed of several connected unit squares. The shapes are hidden; players only learn where a unit is when they land on it.

Both players share the same board and move the same type of chess piece. On each turn the active player steps to any legal, unvisited square. If that square contains a polyomino unit, the player claims it. The player who claims the most units when the game ends wins.

Key tensions:

    Exploration vs. exploitation — do you hunt for new polyomino units, or block the opponent from reaching known clusters?
    Mobility preservation — straying into corners or isolated regions costs you future options.
    Information asymmetry — you see what units you have found, but not yet where the rest of the puzzle lies.

Getting Started

Requirements

    Python 3.7 or later
    pygame (pip install pygame)
    The full Hamiltonian-Knights repository (shared libraries are loaded from sharedlib/ and polyominoes/)

Run the game

cd Hamiltonian-Knights
python duelominoes/duelomino_v01.py

The window opens at your current display resolution and is fully resizable. On Windows the window is automatically maximised.
Game Configuration

All settings are adjusted from the Menu screen using the < and > buttons on each row.
Board Size
Setting 	Range 	Default
Board 	5 × 5 to 16 × 16 	8 × 8

Larger boards allow longer paths and more room for polyominoes, but also dilute flag density and increase game length.
Piece Selection

Both players move the same piece type. Pieces are drawn from the piecekeeper module. Even-parity pieces (bishop, delta, theta, lambda, xi) are excluded because they cannot visit every square on a standard chessboard and would leave large unreachable regions.

All remaining piece types are available, including:

    Standard: knight, rook, queen, king, and variants
    Exotic: gamma, sigma, phi, psi, omega, gunkan, planetary, zodiac, fibonacci, and more

Shapes

Controls which polyomino size (or mix) is used to build the puzzle layout.
Choice 	Description
monomino 	Single-unit squares
domino 	2-unit shapes
triomino 	3-unit shapes
tetromino 	4-unit shapes
pentomino 	5-unit shapes (default)
hexomino 	6-unit shapes
heptomino 	7-unit shapes
octomino 	8-unit shapes
mixed 	Random mix of sizes

Larger polyomino types create denser clusters of units that reward tactical pathing to sweep an entire shape in one run.
Density

Controls how much of the board is covered by polyomino units.
Choice 	Coverage
low 	Sparse — few units scattered across the board
medium 	Moderate coverage (default)
high 	Dense — large portions of the board contain units

Higher density increases scoring opportunities but also makes the opponent's interference more punishing.
Colors

Controls how polyomino shapes are colored on the board.
Choice 	Description
unique 	Each shape gets a distinct color (default)
random 	Colors assigned randomly (may repeat)
same 	All shapes share one color

unique is recommended for beginners as it makes shape boundaries immediately visible once a unit is revealed.
First Move
Choice 	Who moves first
human 	The human player (Player 1 / Blue) moves first (default)
bot 	The bot (Player 2 / Red) moves first

In human-vs-human mode this setting is ignored and Player 1 always goes first.
Level (Bot Difficulty)

Sets the AI difficulty from 1 (easiest) to 5 (hardest). See Bot AI for a full breakdown of each level's strategy.
Level 	Strategy summary
1 	Random legal move
2 	Avoids dead-end squares
3 	Warnsdorff's rule + dead-end avoidance
4 	Warnsdorff + two-ply lookahead + center proximity + polyomino scoring
5 	All of Level 4 + opponent modeling
Clock

Sets a time budget per player in seconds. 0 means unlimited (an elapsed timer is shown instead).
Range 	Default
0 to 31 minutes (in 60-second increments) 	0 (no limit)

When the clock reaches zero, that player loses immediately.
How to Play
Start Squares

Before the first move each player must choose a starting square by clicking anywhere on the board. Players alternate placing their start squares. Once both starts are committed, turns begin.
Taking Turns

The active player's legal moves are highlighted on the board. Click any highlighted square to move there. Squares already visited by either player are never legal move targets — the path is always open, never revisiting a square.

The bot takes its turn automatically after a short delay (500–800 ms) to feel natural.
Discovering Polyomino Units

When a player lands on a square that belongs to the hidden puzzle, the square is revealed and scored to that player. The unit is permanently claimed — the opponent cannot score it. Each player's running unit count is shown in the side panel throughout the game.

Partially completed shapes are tracked; collecting all units of a shape in one continuous run is a strong play, as it denies the opponent every remaining unit in that cluster.
Scoring

    Each polyomino unit square claimed is worth 1 point.
    The player with more units when the game ends wins.
    If unit counts are equal at game end, the result is a draw.
    Squares with no polyomino unit score nothing.

Square Color Guide
Color 	Meaning
Ivory / Tan 	Unvisited square (light / dark board pattern)
Blue (light / dark) 	Square visited by Player 1 (Blue) — no unit found
Red (light / dark) 	Square visited by Player 2 (Red) — no unit found
Gray (light / dark) 	Square visited by either player — no unit on that square
Shape color (tinted blue) 	Polyomino unit claimed by Player 1
Shape color (tinted red) 	Polyomino unit claimed by Player 2
In-Game Controls
Mouse
Action 	Effect
Click a start-square (setup phase) 	Commit your starting position
Click a highlighted legal-move square 	Move your piece there
Click a menu < / > button 	Cycle through that setting's values
Click any button 	Activate that button's action
Keyboard Shortcuts
Key 	Context 	Action
G 	Any 	Toggle Move Guide overlay
H 	In-game 	Toggle Warnsdorff Degrees hint overlay
P 	Any 	Toggle Peek mode (full puzzle thumbnail)
U 	In-game 	Undo last move
ESC 	In-game 	Resign current game
ESC 	Endgame 	Go to main menu
M 	Any 	Minimise window
HUD & Overlays
Move Guide

Displays directional arrows from the active player's current square to every legal destination. Helpful for scanning the board quickly. Toggle with G or the show / hide move guide button.
Warnsdorff Degrees

Overlays each legal destination with its degree — the number of unvisited squares reachable from that square after moving there. Lower degrees indicate squares that will become dead ends sooner. Preferring higher-degree moves preserves mobility for longer. Toggle with H or the show / hide degrees button.
Peek Mode

Reveals a miniature thumbnail of the entire board in the side panel, showing the full puzzle layout (all polyomino shapes and their positions). Use this to plan multistep routes through dense shape clusters. Toggle with P or the peek / hide button.
Reveal All Shapes

A separate toggle that overlays the complete puzzle on the main board (not just the thumbnail), making all hidden units visible at full size. Useful for post-game analysis or accessibility. Toggle via the reveal / hide shapes button.
Endgame
Win & Loss Conditions
Outcome 	Condition
✅ Win 	More polyomino units claimed than the opponent when play ends
🤝 Draw 	Equal unit counts at game end
❌ Timeout 	Your clock expires
❌ Trapped 	You have no legal moves
❌ Resign 	You press resign / ESC
❌ Bot resigns 	Bot determines it cannot improve its position

When one player runs out of legal moves, the other player continues until they too are trapped or time expires — so a trapped player does not immediately end the game.
Retry

The retry button regenerates the exact same puzzle (same seed, same layout) so you can attempt a better strategy. Available as long as a puzzle seed was recorded.
Undo

The undo last move button (or U) steps back one half-move at a time (one player's turn). There is no undo limit. Undoing during a bot game reverts the bot's last move and your last move together, returning the turn to you.
Replay Mode

After a game ends, start replay enters a step-by-step review. Use the + and - buttons to step forward and backward through the move history. Board state, visited squares, and discovered units all update to reflect the selected move.
Share Codes

Every generated puzzle receives a compact share code (base-32 encoded) that captures:

    Board size
    Shape type
    Density
    Colors

Sharing a puzzle

    After starting a game the share code is shown in the side panel.
    Press copy share code to copy it to your clipboard.
    Send the code to a friend.

Loading a shared puzzle

    On the Menu screen press enter share code.
    Type or paste the code.
    Press start — the identical puzzle layout is reproduced.

Bot AI

The bot AI lives in duelomino_bot.py and exposes five difficulty levels via make_bot_move(). Each level builds on the previous.
Level 1 — Random

Selects a uniformly random legal move. No strategy. Good for very young players or as a baseline.
Level 2 — Dead-End Avoidance

Filters out moves that would leave the bot with zero onward options (dead ends). Chooses randomly among the remaining safe moves. Falls back to any legal move if all options are dead ends.
Level 3 — Warnsdorff's Rule

Applies Warnsdorff's heuristic: among non-dead-end moves, prefer the square with the fewest onward moves from that position. This tends to keep large connected regions of the board accessible for longer and is the classical strategy for finding long knight tours.
Level 4 — Multi-Heuristic

Combines several heuristics applied in priority order:

    Dead-end avoidance — eliminate immediately fatal moves.
    Polyomino domain score — prefer moves that reveal new polyomino units.
    Warnsdorff degree — among equal-scoring moves, prefer lower degree.
    Two-ply lookahead — simulate the bot's next move from each candidate and pick the one that leaves the best position.
    Center proximity — prefer central squares (more future connectivity).
    Random tie-breaking — uniform random among equals.

No opponent modeling at this level — the bot optimises purely for its own position.
Level 5 — Opponent Modeling

All of Level 4, plus:

    Opponent modeling — after scoring each candidate by the Level 4 criteria, additionally evaluates how many legal moves the opponent would have after the bot moves there. Prefers moves that minimise the opponent's options (interference strategy).

This level plays aggressively, trading its own positional quality to cut off the opponent from productive regions of the board.
Advanced Strategy
Mobility First

Running out of legal moves is fatal. Use the Warnsdorff Degrees overlay (H) to keep your degree high and avoid stranding yourself in a corner while the opponent still has plenty of room.
Shape Sweeping

Use Peek mode (P) to identify large polyomino clusters. Route your piece to enter a cluster and sweep as many connected units as possible in consecutive moves — this denies the entire cluster to the opponent before they can reach it.
Interference

At higher levels the bot will deliberately move into squares that restrict your future options. Counter this by maintaining multiple viable corridors and never allowing yourself to be funnelled into a single escape route.
Piece Choice

    Knight: Non-linear movement creates complex, unpredictable paths. Hard to anticipate and hard to block.
    King / Queen: High mobility gives many options each turn but makes long-term planning harder.
    Exotic pieces: Unfamiliar move sets benefit the human player who studies them — the bot applies the same heuristics regardless.

Clock Management

If using the clock, take note of your opponent's remaining time. Forcing the opponent to make many suboptimal moves under time pressure is a valid strategy at high density settings.
Architecture & Technical Notes
Module 	Role
duelomino_v01.py 	Entry point — Pygame init, window setup, main loop
duelomino_controller.py 	Game state machine, two-player logic, move handling, rendering
duelomino_bot.py 	AI move selection at five difficulty levels

Two-player state management

The controller maintains separate state for each player:

    player_pos[1], player_pos[2] — current positions
    visited[1], visited[2] — squares each player has visited
    found_units[1], found_units[2] — polyomino units claimed
    legal_moves[1], legal_moves[2] — cached legal moves (recomputed after each half-move)

all_visited is the union of both players' visited sets and is used to compute legal moves for either player.

Polyomino placement

place_puzzle_layout() places polyomino shapes onto the board using random rotation and reflection. Each PuzzleShape stores:

    puzzle_units: the set of board squares occupied by this shape
    id: unique identifier for color/tracking purposes

Shapes are placed without overlap. Density settings control the target coverage fraction.

Bot integration

make_bot_move() is called from _execute_bot_move() with a configurable delay (500–800 ms). domain_data passes (puzzle_layout, bot_found_units) to Levels 4 and 5 so the polyomino scorer can evaluate how many new units each candidate move would reveal.

Codec system

Puzzle parameters are packed into a compact base-32 share code using a fixed schema:
Field 	Values
board 	5–16
shapes 	monomino … octomino / mixed
density 	low / medium / high
colors 	unique / random / same
Known Limitations

    Even-parity pieces excluded — bishop, delta, theta, lambda, and xi cannot visit every square and are removed from the piece list.
    Bot think time is fixed — the artificial delay (500–800 ms) is not configurable from the menu.
    Two-ply lookahead only — Level 4/5 lookahead is limited to two plies; deeper search would improve play quality but increases CPU cost.
    Replay memory is unbounded — long games accumulate many state snapshots.
    Clipboard fallback — on Linux, clipboard copy may silently fail if xclip / xsel are not installed.

Credits

Developed by paw309.
Built with Python and pygame.
Inspired by polyomino puzzles, chess movement, and competitive board games.

    Outscore your opponent. Outsmart the board. Can you claim the most?
