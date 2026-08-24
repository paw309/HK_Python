________________________________________
Piece Suitability Per Game
Preliminary: Key Piece Properties
Parity (can the piece reach all squares?)
A leaper (a,b) is even-parity / color-bound when a+b is even — it cannot complete a Hamiltonian tour. For multi-pattern pieces, parity is broken as soon as any one pattern has an odd coordinate sum.
Status	Pieces
Even-parity (CANNOT tour)	bishop, ferz {1,1}, dabbaba {0,2}, alfil {2,2}, tripper {3,3}, camel {1,3}
Odd-parity or parity-breaking (CAN tour)	all others

Minimum board size for pieces whose range demands it: gazelle 6+, flamingo 7+, bharal 6+, pallas 6+, scorpio 6+, virgo 5+, libra 7+, capricorn 7+, pterodactyl 16+, fibonacci 14+ (for full pattern).
Move-count spectrum (open board center): wazir/ferz 4, dabbaba/alfil/threeleaper/tripper 4, camel/zebra/giraffe/antelope/gazelle/flamingo/bharal 8, king 8, knight 8, queen/rook very high, two-pattern pieces 8-16, multi-set pieces 12-20+.
________________________________________
Games Defined
1.	Knight's Tour / Knight's Trap (KT/KTrap) — solo Hamiltonian path/circuit on N×N board; Knight's Trap is the 2-player competitive race variant
2.	Knights Turing (KTuring) — Hamiltonian path puzzle where the active piece cycles through a fixed rule set (TURING_PIECES: knight, wazir, ferz, dabbaba, alfil, threeleaper, tripper, camel, zebra, giraffe); player navigates with a piece that changes each step; only these 10 pieces are supported
3.	Palisades — non-crossing Hamiltonian path; the drawn path must never intersect itself; selected pieces must be able to complete a full Hamiltonian tour without their path segments crossing
4.	Vexillum / Vexillology (Vex) — solo + competitive flag-collection along a procedurally generated sub-path; Vexillology is the 2-player competitive variant on a shared board
5.	Mined Maze / Mined Control (MM/MC) — discover a hidden path by deduction; Mined Control adds a timed competitive variant
6.	Polyomino / Duelomino (Poly/Duel) — Hamiltonian path that reveals hidden polyomino shapes; Duelomino is the 2-player competitive variant
7.	Gunkan — 2-player competitive hidden-polyomino-hunting game played via shared Hamiltonian paths; the Gunkan piece is the namesake and default
8.	Megalomino — knight's tour on a large irregular polyomino (knight only)
________________________________________
Per-Piece Ratings
Canonical Pieces
________________________________________
knight {1,2}
Game	Rating	Notes
Knight's Tour / Knight's Trap	✅ Positive	The canonical piece. Warnsdorff's heuristic and rich tour literature make it ideal — challenging but solvable on any board ≥5. Competitive interference (≤8 moves) is strategic and learnable.
Knights Turing	✅ Positive	In TURING_PIECES; the reference leaper in the cycle; distinctive L-move provides clear contrast to all other pieces in the set.
Palisades	✅ Positive	The canonical non-crossing tour piece. L-shaped moves produce naturally weaving paths that avoid self-intersection more readily than orthogonal or diagonal movement.
Vexillum / Vexillology	✅ Positive	8 moves, meaningful path choices, works across all standard board sizes; both solo flag-hunting and competitive flag-racing are engaging.
Mined Maze / Mined Control	✅ Positive	8 L-shaped moves give excellent deduction depth; geometry makes dead-ends non-obvious; timed variant is equally well-suited.
Polyomino / Duelomino	✅ Positive	Non-trivial Hamiltonian paths produce varied shape reveals; competitive interaction is rich and spatial.
Gunkan	✅ Positive	Odd-parity; 8 moves give good board coverage for shape hunting; competitive paths interact meaningfully.
Megalomino	✅ Positive	The only currently supported piece; the entire game is designed around it.
________________________________________
bishop {n,n} (slider)
Game	Rating	Notes
Knight's Tour / Knight's Trap	❌ Negative	Color-bound slider; cannot reach squares of the opposite color. No full-board tour possible.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	❌ Negative	Color-bound; cannot complete a full-board tour; excluded from game.
Vexillum / Vexillology	❌ Negative	Color-bound (even-parity); excluded from game; cannot generate a full-board path.
Mined Maze / Mined Control	✅ Positive	Long diagonal slides generate excellent deduction mazes; player must infer which diagonal is blocked; many plausible routes per square adds depth.
Polyomino / Duelomino	❌ Negative	Cannot cover all squares; excluded from game.
Gunkan	❌ Negative	Color-bound; excluded from game.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
rook {n,0} (slider)
Game	Rating	Notes
Knight's Tour / Knight's Trap	⚪ Neutral	Full-board tours exist (serpentine boustrophedon) but are trivially obvious. No strategic depth for solo or competitive play.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	❌ Negative	Excluded from game; orthogonal slide segments cross readily as the path doubles back; serpentine sweeps are forced non-crossing paths but yield trivial gameplay.
Vexillum / Vexillology	⚪ Neutral	Long slides provide many options; flag collection works but path strategy is low-depth; competitive variant lacks positional tension.
Mined Maze / Mined Control	✅ Positive	Many move options per square make the deduction challenge genuine; row/column blocking is natural maze structure.
Polyomino / Duelomino	⚪ Neutral	Tours work but any row-by-row sweep trivially solves the board; shape reveals are predictable; competitive depth is low.
Gunkan	⚪ Neutral	Trivially obvious tours reduce competitive shape-hunting depth; game resolves too quickly.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
queen {n,0}{n,n} (slider)
Game	Rating	Notes
Knight's Tour / Knight's Trap	⚪ Neutral	Tours trivially easy; extreme mobility removes strategic tension for both solo and competitive play.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	❌ Negative	Excluded from game; extremely long slide segments create immediate crossings; non-crossing constraint becomes impractical.
Vexillum / Vexillology	⚪ Neutral	Very high mobility makes flag navigation trivially easy; competitive variant lacks meaningful depth.
Mined Maze / Mined Control	✅ Positive	Maximum number of options per square creates deep deduction; many plausible paths to evaluate.
Polyomino / Duelomino	⚪ Neutral	Trivially easy tours; shapes are revealed mechanically without challenge; competitive play decided by speed alone.
Gunkan	⚪ Neutral	Extreme mobility reduces competitive shape-hunting depth; game resolved too quickly.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
king {0,1}{1,1}
Game	Rating	Notes
Knight's Tour / Knight's Trap	✅ Positive	8-direction leaper (all adjacent squares); tours require local tactical planning; spiral-avoidance challenge is genuine; competitive territory control is direct and learnable.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	❌ Negative	Excluded from game; 8 adjacent moves create crossing issues quickly as the path folds back on itself; non-crossing constraint makes tours near-impossible on most boards.
Vexillum / Vexillology	✅ Positive	Intuitive movement; 8 moves give meaningful choices; solo path navigation is clean and competitive variant has natural territorial tension.
Mined Maze / Mined Control	✅ Positive	8 adjacent moves are easy to understand but create excellent proximity-based deduction.
Polyomino / Duelomino	✅ Positive	Tours solvable and non-trivial; shape reveals are varied; local competition for territory creates engaging play.
Gunkan	✅ Positive	Local range creates direct territorial competition for shape discovery; 8 adjacent moves are well-balanced for the hunting mechanic.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
Atomic Fairy Leapers
________________________________________
wazir {0,1}
Game	Rating	Notes
Knight's Tour / Knight's Trap	⚪ Neutral	Tours exist on all boards but the optimal solution is always a serpentine sweep; very limited branching (4 moves) makes competitive play trivial.
Knights Turing	✅ Positive	In TURING_PIECES; clear orthogonal-adjacency movement contrasts well with knight and ferz; interesting part of the cycling rule set.
Palisades	❌ Negative	Excluded from game; only 4 orthogonal adjacent moves make non-crossing tours essentially forced linear paths with no real challenge.
Vexillum / Vexillology	⚪ Neutral	4 moves provide limited strategic variety; flag collection works but depth is low for both solo and competitive play.
Mined Maze / Mined Control	✅ Positive	Classic grid maze piece — 4 orthogonal moves match the mental model of most maze games; deduction is clean and accessible.
Polyomino / Duelomino	⚪ Neutral	Serpentine tours produce predictable shape reveals; not enough path variety for interesting polyomino discovery; competitive depth is minimal.
Gunkan	⚪ Neutral	Limited mobility makes board coverage slow; shape hunting is inefficient; competitive depth is minimal.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
ferz {1,1}
Game	Rating	Notes
Knight's Tour / Knight's Trap	❌ Negative	Color-bound (stays on one diagonal color); no full-board Hamiltonian tour.
Knights Turing	✅ Positive	In TURING_PIECES; diagonal-adjacency movement contrasts well with wazir and knight; adds color-restricted challenge to the cycling rule set.
Palisades	❌ Negative	Color-bound; no full-board tour; excluded from game.
Vexillum / Vexillology	❌ Negative	Color-bound (even-parity); excluded from game.
Mined Maze / Mined Control	✅ Positive	4 diagonal moves create a tilted-grid maze; the checkerboard structure provides a novel deduction experience distinct from orthogonal pieces.
Polyomino / Duelomino	❌ Negative	Cannot cover all squares; excluded from game.
Gunkan	❌ Negative	Color-bound; excluded from game.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
dabbaba {0,2}
Game	Rating	Notes
Knight's Tour / Knight's Trap	❌ Negative	Restricted to even-parity squares only; cannot complete a full tour.
Knights Turing	✅ Positive	In TURING_PIECES; orthogonal distance-2 jumps are visually distinctive; adds interesting jumping challenge to the cycling rule set.
Palisades	❌ Negative	Even-parity; no full-board tour; excluded from game.
Vexillum / Vexillology	❌ Negative	Even-parity; excluded from game.
Mined Maze / Mined Control	⚪ Neutral	4 orthogonal-jump moves create a sparse but functional deduction maze; restricted coverage limits depth.
Polyomino / Duelomino	❌ Negative	Even-parity; excluded from game.
Gunkan	❌ Negative	Even-parity; excluded from game.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
alfil {2,2}
Game	Rating	Notes
Knight's Tour / Knight's Trap	❌ Negative	Accesses only 1/4 of board squares (same color AND same parity); no full-board tour.
Knights Turing	⚪ Neutral	In TURING_PIECES; extremely restricted (1/4 of board); creates demanding solvability constraints in the piece cycle; needs careful board-size consideration to avoid dead-end sequences.
Palisades	❌ Negative	Extreme restriction; no full-board tour; excluded from game.
Vexillum / Vexillology	❌ Negative	Even-parity; excluded from game.
Mined Maze / Mined Control	⚪ Neutral	Can create exotic mazes on large boards within its accessible sub-grid; extreme restriction limits usability on typical boards.
Polyomino / Duelomino	❌ Negative	Cannot cover all squares; excluded from game.
Gunkan	❌ Negative	Even-parity; excluded from game.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
threeleaper {0,3}
Game	Rating	Notes
Knight's Tour / Knight's Trap	⚪ Neutral	Odd-parity (0+3=3); tours exist in theory but only 4 orthogonal moves per square makes tour-finding very difficult; limited competitive branching.
Knights Turing	⚪ Neutral	In TURING_PIECES; orthogonal distance-3 jumps add distinct variety to the cycle; but only 4 moves means the threeleaper step may produce dead-ends in cycles, limiting puzzle solvability.
Palisades	❌ Negative	Excluded from game; only 4 moves makes non-crossing Hamiltonian tours impractical for most starting positions.
Vexillum / Vexillology	❌ Negative	Excluded from game (very limited connectivity).
Mined Maze / Mined Control	⚪ Neutral	4 orthogonal-jump moves create an unusual sparse maze; limited deduction depth.
Polyomino / Duelomino	❌ Negative	Excluded from game; extremely limited connectivity.
Gunkan	❌ Negative	Excluded from game.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
tripper {3,3}
Game	Rating	Notes
Knight's Tour / Knight's Trap	❌ Negative	Even-parity (3+3=6); color-bound diagonal distance-3 leaper; no full-board tour.
Knights Turing	⚪ Neutral	In TURING_PIECES; color-bound but adds restricted diagonal-distance-3 variety to the cycle; creates parity challenges in piece sequences.
Palisades	❌ Negative	Color-bound; no full-board tour; excluded from game.
Vexillum / Vexillology	❌ Negative	Color-bound (even-parity); excluded from game.
Mined Maze / Mined Control	⚪ Neutral	4 diagonal-jump moves generate a color-restricted sparse maze; limited but functional deduction within accessible squares.
Polyomino / Duelomino	❌ Negative	Color-bound; excluded from game.
Gunkan	❌ Negative	Color-bound; excluded from game.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
camel {1,3}
Game	Rating	Notes
Knight's Tour / Knight's Trap	❌ Negative	Even-parity (1+3=4); color-bound; no full-board tour.
Knights Turing	✅ Positive	In TURING_PIECES; color-bound but has 8 moves and a distinctive long-diagonal jump; adds interesting color-restricted challenge to the cycle.
Palisades	❌ Negative	Color-bound; no full-board tour; excluded from game.
Vexillum / Vexillology	❌ Negative	Color-bound (even-parity); excluded from game.
Mined Maze / Mined Control	⚪ Neutral	8 long-diagonal moves create interesting deduction within accessible squares; color-bound restriction limits board coverage.
Polyomino / Duelomino	❌ Negative	Color-bound; excluded from game.
Gunkan	❌ Negative	Color-bound; excluded from game.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
zebra {2,3}
Game	Rating	Notes
Knight's Tour / Knight's Trap	✅ Positive	Odd-parity (2+3=5); tours exist on boards ≥4; similar topology to knight but different connectivity graph — excellent alternative challenge; good competitive depth.
Knights Turing	✅ Positive	In TURING_PIECES; distinctive oblique jump at medium range; adds non-trivial variation to the piece cycle.
Palisades	✅ Positive	Odd-parity; 8 moves; L-like geometry avoids self-intersections reasonably well; non-crossing challenge is interesting and solvable.
Vexillum / Vexillology	✅ Positive	8 moves; interesting path geometry for solo flag collection and competitive racing.
Mined Maze / Mined Control	✅ Positive	8 moves give good deduction game; oblique jump geometry produces non-obvious path structures.
Polyomino / Duelomino	✅ Positive	Hamiltonian paths reveal shapes in varied ways; competitive play mirrors knight in quality.
Gunkan	✅ Positive	Odd-parity; 8 moves provide good board coverage; competitive shape hunting is engaging.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
giraffe {1,4}
Game	Rating	Notes
Knight's Tour / Knight's Trap	✅ Positive	Odd-parity (1+4=5); needs board ≥5; creates interesting, less-studied tour challenge; good competitive depth.
Knights Turing	✅ Positive	In TURING_PIECES; (1,4) long-range jump adds distinct high-reach variety to the cycle; clearly distinguishable from shorter-range pieces.
Palisades	✅ Positive	Odd-parity; 8 moves; non-crossing challenge is interesting on medium-large boards; longer range creates naturally spaced path segments.
Vexillum / Vexillology	✅ Positive	Range creates interesting path geometry for flag collection; both solo and competitive play are engaging.
Mined Maze / Mined Control	✅ Positive	8 moves with good range; deduction game is interesting and non-trivial.
Polyomino / Duelomino	✅ Positive	Interesting Hamiltonian paths; varied shape reveals; good competitive experience.
Gunkan	✅ Positive	Odd-parity; longer range aids board coverage and shape hunting; competitive interaction has variety.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
antelope {3,4}
Game	Rating	Notes
Knight's Tour / Knight's Trap	✅ Positive	Odd-parity (3+4=7); needs board ≥5; long-range creates sparse, demanding tours; competition is methodical and cerebral.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	✅ Positive	Odd-parity; 8 moves; long segments create interesting non-crossing challenge; needs 5+ board; paths must thread carefully on larger boards.
Vexillum / Vexillology	✅ Positive	Range creates varied flag-collection geometry; needs 5+ board; both solo and competitive are engaging.
Mined Maze / Mined Control	✅ Positive	8 moves with good range; deduction maze is non-trivial and interesting.
Polyomino / Duelomino	✅ Positive	Good tour challenge; shape reveals interesting on larger boards; competitive experience is deliberate and strategic.
Gunkan	✅ Positive	Long-range enhances shape-hunting reach; competitive depth is good on larger boards.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
gazelle {2,5}
Game	Rating	Notes
Knight's Tour / Knight's Trap	⚪ Neutral	Odd-parity (2+5=7); requires board ≥6; on board 5 no moves exist; interesting on 8+ but board-size dependency narrows appeal.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	⚪ Neutral	Needs 6+ board; long segments can create crossing challenges; board-size sensitivity limits broad appeal.
Vexillum / Vexillology	⚪ Neutral	Needs 6+ board; works well on appropriate sizes; both modes are enjoyable but limited to larger boards.
Mined Maze / Mined Control	✅ Positive	Long-range deduction is interesting on appropriate board sizes.
Polyomino / Duelomino	⚪ Neutral	Works on larger boards; too limited on small boards.
Gunkan	⚪ Neutral	Needs 6+; longer range aids shape hunting on appropriate boards but board-size dependency limits applicability.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
flamingo {1,6}
Game	Rating	Notes
Knight's Tour / Knight's Trap	⚪ Neutral	Odd-parity (1+6=7); needs board ≥7; very sparse on most boards; interesting on 12-16 but narrow appeal.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	⚪ Neutral	Needs 7+ board; very sparse; long segments require careful crossing avoidance; board-size sensitivity limits appeal.
Vexillum / Vexillology	⚪ Neutral	Needs 7+; long-range movement creates exotic paths; works on appropriate sizes only.
Mined Maze / Mined Control	✅ Positive	Extended range creates unusual deduction challenge on appropriate board sizes.
Polyomino / Duelomino	⚪ Neutral	Only suitable on larger boards; limited applicability overall.
Gunkan	⚪ Neutral	Needs 7+; narrow board-size applicability; long-range can aid shape hunting on appropriate boards.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
bharal {4,5}
Game	Rating	Notes
Knight's Tour / Knight's Trap	✅ Positive	Odd-parity (4+5=9); up to 8 moves; needs board ≥6; similar topology to antelope/zebra but with different connectivity; creates interesting demanding tours on 8+.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	✅ Positive	Odd-parity; needs 6+; up to 8 moves; long wide-angled jumps produce naturally spaced path segments that avoid crossing; non-crossing challenge is interesting.
Vexillum / Vexillology	✅ Positive	Odd-parity; good mobility on appropriate board sizes; both solo and competitive play are engaging.
Mined Maze / Mined Control	✅ Positive	8 moves with a distinct jump geometry; deduction is non-trivial and interesting.
Polyomino / Duelomino	✅ Positive	Good tour challenge on 8+ boards; shape reveals are interesting; competitive experience is engaging.
Gunkan	✅ Positive	Odd-parity; good mobility for shape discovery; adds variety to the piece selection.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
Two-Set Fairy Pieces
________________________________________
wapiti {1,1}{1,2}
Game	Rating	Notes
Knight's Tour / Knight's Trap	✅ Positive	Ferz+knight; knight breaks ferz's color restriction; up to 12 moves; good connectivity makes tours accessible but not trivially easy; competitive branching creates real interference.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	✅ Positive	Parity-breaking; up to 12 moves give excellent non-crossing flexibility; mixed diagonal/L-move geometry is interesting and well-suited to path-weaving.
Vexillum / Vexillology	✅ Positive	Parity-breaking; 12 moves; rich movement options suit both solo flag-hunting and competitive flag-racing.
Mined Maze / Mined Control	✅ Positive	Up to 12 moves with diverse directions create excellent deduction depth.
Polyomino / Duelomino	✅ Positive	Good path variety for shape discovery; competitive interaction is rich and spatial.
Gunkan	✅ Positive	Parity-breaking; good mobility for board coverage and shape hunting; competitive play is engaging.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
gnu {1,2}{1,3}
Game	Rating	Notes
Knight's Tour / Knight's Trap	✅ Positive	Knight+camel; knight breaks camel's even-parity restriction; up to 16 moves but longer range moderates difficulty; distinctive joint topology creates interesting tours.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	✅ Positive	Parity-breaking; up to 16 moves give good non-crossing flexibility; mixed short/long oblique geometry rarely creates accidental crossings.
Vexillum / Vexillology	✅ Positive	Parity-breaking; good mobility and range create engaging flag collection; works well in competitive mode.
Mined Maze / Mined Control	✅ Positive	Up to 16 moves with diverse directions; excellent deduction depth.
Polyomino / Duelomino	✅ Positive	Good tour variety; competitive interaction is engaging.
Gunkan	✅ Positive	Parity-breaking; up to 16 moves enhance shape hunting and competitive board coverage.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
wildebeest {1,2}{2,3}
Game	Rating	Notes
Knight's Tour / Knight's Trap	✅ Positive	Knight+zebra; both odd-parity; up to 16 moves; combined geometry differs from either component alone; excellent tour challenge; rich competitive depth.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	✅ Positive	Both components odd-parity; up to 16 moves create good non-crossing flexibility; mixed L-move geometry is interesting.
Vexillum / Vexillology	✅ Positive	Parity-fine; up to 16 moves; excellent path geometry for flag collection and competitive racing.
Mined Maze / Mined Control	✅ Positive	Up to 16 diverse-direction moves create excellent deduction challenge.
Polyomino / Duelomino	✅ Positive	Rich path variety; strong competitive experience with genuine interference between players.
Gunkan	✅ Positive	Very good mobility for shape hunting; up to 16 diverse moves create strategic competitive play.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
zebu {1,3}{1,4}
Game	Rating	Notes
Knight's Tour / Knight's Trap	✅ Positive	Camel+giraffe; giraffe breaks camel's even-parity restriction; up to 16 moves but longer range means effective connectivity is moderate on typical boards; longer-range competition is more cerebral.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	✅ Positive	Parity-breaking; longer-range components create unusual non-crossing path geometry; interesting on medium-large boards.
Vexillum / Vexillology	✅ Positive	Interesting longer-range path geometry; engaging for both solo and competitive play.
Mined Maze / Mined Control	✅ Positive	Extended range creates novel deduction game.
Polyomino / Duelomino	✅ Positive	Good tour challenge; competitive longer-range play is engaging and deliberate.
Gunkan	✅ Positive	Longer-range moves aid shape hunting across the board; competitive play is strategic.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
bison {1,3}{2,3}
Game	Rating	Notes
Knight's Tour / Knight's Trap	✅ Positive	Camel+zebra; zebra breaks camel's even-parity restriction; up to 16 moves; longer range tempers difficulty on smaller boards; good competitive depth.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	✅ Positive	Parity-breaking; interesting combined oblique geometry for non-crossing paths.
Vexillum / Vexillology	✅ Positive	Good path structure; engaging for both solo and competitive play.
Mined Maze / Mined Control	✅ Positive	Good deduction game with diverse oblique directions.
Polyomino / Duelomino	✅ Positive	Interesting tours; good competitive experience.
Gunkan	✅ Positive	Good mobility for shape hunting; competitive play has genuine spatial depth.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
frog {1,1}{0,3}
Game	Rating	Notes
Knight's Tour / Knight's Trap	✅ Positive	Ferz+threeleaper; (0,3) breaks ferz's color restriction; up to 12 moves; good tour density and competitive branching.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	✅ Positive	Parity-breaking; up to 12 moves give good non-crossing flexibility; mixed diagonal/orthogonal jump geometry is interesting.
Vexillum / Vexillology	✅ Positive	Diagonal + orthogonal jumping covers many directions; engaging for both solo and competitive play.
Mined Maze / Mined Control	✅ Positive	12 possible moves from open squares create excellent deduction depth.
Polyomino / Duelomino	✅ Positive	Good tour variety for shape discovery; competitive interaction is interesting.
Gunkan	✅ Positive	Parity-breaking; 12 moves; good for competitive shape hunting.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
toad {0,2}{0,3}
Game	Rating	Notes
Knight's Tour / Knight's Trap	✅ Positive	Dabbaba+threeleaper; (0,3) breaks dabbaba's even-parity restriction; orthogonal jumping creates interesting tour constraints and competitive play.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	❌ Negative	Excluded from game; exclusively orthogonal movement makes path segments highly prone to crossing as the route doubles back on itself.
Vexillum / Vexillology	✅ Positive	Orthogonal jumping is intuitive; parity-breaking; good path geometry for solo and competitive flag collection.
Mined Maze / Mined Control	✅ Positive	Orthogonal-only piece with jumping creates an unusual but interesting deduction maze.
Polyomino / Duelomino	✅ Positive	Interesting tour structure; good competitive play; parity-breaking works across board sizes.
Gunkan	✅ Positive	Parity-breaking; orthogonal jumping gives reasonable board coverage for shape hunting.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
newt {0,2}{1,4}
Game	Rating	Notes
Knight's Tour / Knight's Trap	✅ Positive	Dabbaba+giraffe; (1,4) giraffe component breaks dabbaba's even-parity restriction; combined piece has up to 12 moves; interesting mixed-range tour challenge.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	✅ Positive	Parity-breaking; mixed orthogonal/oblique range creates interesting non-crossing challenge.
Vexillum / Vexillology	✅ Positive	Range variety makes path navigation engaging; works well for both solo and competitive play.
Mined Maze / Mined Control	✅ Positive	Good deduction game with diverse move directions.
Polyomino / Duelomino	✅ Positive	Interesting tour variety; good competitive experience.
Gunkan	✅ Positive	Parity-breaking; mixed range helps cover the board for shape hunting.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
mars {0,2}{2,3}
Game	Rating	Notes
Knight's Tour / Knight's Trap	✅ Positive	Dabbaba+zebra; zebra breaks dabbaba's even-parity restriction; good combined connectivity; interesting tour challenge and competitive depth.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	✅ Positive	Parity-breaking; orthogonal+oblique combination creates varied non-crossing path geometry.
Vexillum / Vexillology	✅ Positive	Mixed orthogonal/diagonal range creates varied paths; engaging for both solo and competitive play.
Mined Maze / Mined Control	✅ Positive	Good deduction game with orthogonal/oblique direction diversity.
Polyomino / Duelomino	✅ Positive	Interesting shape-reveal tours; competitive play is engaging.
Gunkan	✅ Positive	Parity-breaking; good for competitive shape hunting.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
jupiter {1,1}{2,3}
Game	Rating	Notes
Knight's Tour / Knight's Trap	⚪ Neutral	Ferz+zebra; up to 16 moves; tours somewhat too easy due to high connectivity; competitive tension reduced by excessive mobility.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	⚪ Neutral	Parity-breaking; 16 moves provide many non-crossing options; constraint feels too permissive to create a genuine challenge.
Vexillum / Vexillology	✅ Positive	Rich movement options make flag navigation engaging; multiple directions suit both solo and competitive play.
Mined Maze / Mined Control	✅ Positive	Many move options create deep deduction game.
Polyomino / Duelomino	⚪ Neutral	Tours somewhat easy; shape reveals found with limited strategy; competitive depth slightly diminished by mobility.
Gunkan	⚪ Neutral	Too high mobility reduces competitive shape-hunting depth; shapes found too quickly.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
saturn {0,3}{2,2}
Game	Rating	Notes
Knight's Tour / Knight's Trap	✅ Positive	Threeleaper+alfil; threeleaper breaks alfil's color-bound restriction; up to 8 moves with orthogonal/diagonal variety; interesting combined topology creates genuine tour challenge.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	✅ Positive	Parity-breaking; up to 8 orthogonal/diagonal mixed moves; non-crossing challenge is interesting without being impractical.
Vexillum / Vexillology	✅ Positive	Parity-breaking; orthogonal/diagonal variety; good path options for solo and competitive play.
Mined Maze / Mined Control	✅ Positive	8 moves with orthogonal/diagonal variety create good deduction depth.
Polyomino / Duelomino	✅ Positive	Interesting combined tour structure; good competitive experience.
Gunkan	✅ Positive	Parity-breaking; reasonable mobility for shape hunting; competitive play has spatial interest.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
ceres {2,2}{2,3}
Game	Rating	Notes
Knight's Tour / Knight's Trap	✅ Positive	Alfil+zebra; zebra breaks alfil's color-bound restriction; alfil adds diagonal leaps; interesting combined topology and good competitive depth.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	✅ Positive	Parity-breaking; oblique combination creates interesting non-crossing challenge.
Vexillum / Vexillology	✅ Positive	Mixed diagonal-pattern coverage; engaging for both solo and competitive play.
Mined Maze / Mined Control	✅ Positive	Up to 12 moves (4 alfil + 8 zebra) create good deduction depth.
Polyomino / Duelomino	✅ Positive	Varied tour structure; good competitive experience.
Gunkan	✅ Positive	Parity-breaking; good mobility for shape hunting.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
pallas {3,4}{0,5}
Game	Rating	Notes
Knight's Tour / Knight's Trap	✅ Positive	Antelope+{0,5}; both odd-parity; longer range suits 6+ boards; creates demanding tours on medium-large boards; competition is deliberate and cerebral.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	⚪ Neutral	Both odd-parity; needs 6+ board; long-range components create unusual non-crossing geometry; interesting on larger boards but board-size constraint limits general appeal.
Vexillum / Vexillology	✅ Positive	Good range for flag collection; works well on appropriate board sizes; competitive variant is deliberate and strategic.
Mined Maze / Mined Control	✅ Positive	Extended range creates challenging and unusual deduction.
Polyomino / Duelomino	⚪ Neutral	Interesting but best on larger boards only; limited applicability on small boards.
Gunkan	⚪ Neutral	Needs 6+ board; long-range pieces can be powerful for shape hunting but board-size constraint limits broad applicability.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
Multi-Set Fairy Pieces
________________________________________
pterodactyl {3,3}{5,5}{0,15}
Game	Rating	Notes
Knight's Tour / Knight's Trap	❌ Negative	Requires 16×16 board for the (0,15) component; below 16 only (3,3) and (5,5) are active, both color-bound and very sparse; tours nearly impossible on boards below 16.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	❌ Negative	Excluded from game; requires 16+ board; color-bound below 16; effectively inaccessible for most play.
Vexillum / Vexillology	⚪ Neutral	Below 16×16 the piece is color-bound; minimum 16×16 for full functionality; exotic but barely viable even then.
Mined Maze / Mined Control	⚪ Neutral	Extreme board-size dependency; very niche experience; color-bound below 16×16.
Polyomino / Duelomino	❌ Negative	Color-bound below 16×16; no full-board tour on typical boards; excluded in practice.
Gunkan	⚪ Neutral	Only playable on 16×16; very limited practical applicability.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
virgo {0,3}{1,4}{2,3}
Game	Rating	Notes
Knight's Tour / Knight's Trap	✅ Positive	Threeleaper+giraffe+zebra; all odd-parity; up to 20 moves from central squares on large boards; tours require genuine planning despite good connectivity; competitive play has real depth.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	✅ Positive	All three patterns odd-parity; good connectivity gives excellent non-crossing flexibility; needs 5+ board.
Vexillum / Vexillology	✅ Positive	Varied multi-direction coverage makes path navigation interesting; both solo and competitive modes are engaging.
Mined Maze / Mined Control	✅ Positive	Good move count with diverse directions; excellent deduction game.
Polyomino / Duelomino	✅ Positive	Tours are non-trivial despite good connectivity; interesting shape reveals; competitive play is engaging.
Gunkan	✅ Positive	3 patterns give excellent coverage for shape hunting; competitive play has strategic depth.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
libra {1,3}{3,4}{5,6}
Game	Rating	Notes
Knight's Tour / Knight's Trap	✅ Positive	Camel+antelope+{5,6}; antelope and {5,6} break camel's even-parity restriction; long-range multi-pattern; needs 7+ board; creates difficult exploratory tours; competition is deliberate.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	⚪ Neutral	Parity-breaking; needs 7+ board; long-range 3-pattern piece; interesting non-crossing challenge on larger boards but board-size sensitivity limits general appeal.
Vexillum / Vexillology	✅ Positive	Long-range pattern variety; interesting on larger boards; both solo and competitive play are engaging.
Mined Maze / Mined Control	✅ Positive	Extended range diversity creates unique deduction experience.
Polyomino / Duelomino	⚪ Neutral	Best on larger boards; tour challenge is interesting but narrow applicability on small boards.
Gunkan	⚪ Neutral	Needs 7+ board; long-range moves can be powerful for shape hunting on appropriate boards; board-size constraint limits broad use.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
scorpio {0,2}{1,4}{2,5}
Game	Rating	Notes
Knight's Tour / Knight's Trap	⚪ Neutral	Dabbaba+giraffe+{2,5}; giraffe and {2,5} break dabbaba's even-parity restriction; needs 6+ board for the {2,5} component; up to 20 moves on 8+ boards makes tours somewhat easy; board-size dependency.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	⚪ Neutral	Parity-breaking; board-size dependent (needs 6+); interesting non-crossing challenge when all patterns are active.
Vexillum / Vexillology	⚪ Neutral	Board-size dependent; works well on 6+ boards; engaging on appropriate sizes.
Mined Maze / Mined Control	✅ Positive	Long-range deduction with good direction variety when all patterns are active; interesting on 6+ boards.
Polyomino / Duelomino	⚪ Neutral	Board-size limited; interesting on 6+ boards but limited below.
Gunkan	⚪ Neutral	Needs 6+ board; good for shape hunting when all patterns active; board-size sensitive.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
capricorn {2,3}{0,4}{5,6}
Game	Rating	Notes
Knight's Tour / Knight's Trap	⚪ Neutral	Zebra+{0,4}+{5,6}; zebra and {5,6} break {0,4}'s even-parity restriction; needs 7+ for all patterns; on 7+ boards up to 20 moves makes tours somewhat easy; board-size dependency.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	⚪ Neutral	Parity-breaking; board-size dependent (needs 7+); interesting non-crossing challenge on larger boards.
Vexillum / Vexillology	⚪ Neutral	Board-size dependent; works on 7+ boards; engaging on appropriate sizes.
Mined Maze / Mined Control	✅ Positive	Good deduction on appropriate board sizes with diverse direction coverage.
Polyomino / Duelomino	⚪ Neutral	Board-size limited; best on 7+; interesting but narrow applicability.
Gunkan	⚪ Neutral	Needs 7+ board; good for shape hunting when active; board-size sensitive.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
fibonacci {0,1}{1,1}{1,2}{2,3}{3,5}{5,8}{8,13}
Game	Rating	Notes
Knight's Tour / Knight's Trap	✅ Positive	Fibonacci sequence creates naturally scaled connectivity; on boards 5-8 only first 4 patterns active (wazir+ferz+knight+zebra), which is excellent; full pattern needs 14+ board; great competitive piece on medium boards.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	✅ Positive	Multi-scale coverage adapts naturally to board size; (0,1) wazir component provides fine-grained path control useful for non-crossing navigation.
Vexillum / Vexillology	✅ Positive	Multi-scale coverage creates excellent flag navigation; scales well with board size; both solo and competitive are engaging.
Mined Maze / Mined Control	✅ Positive	Very high branching on large boards; excellent deduction game.
Polyomino / Duelomino	✅ Positive	Rich path variety across all board sizes; very competitive; scaling means it works well at all board sizes.
Gunkan	✅ Positive	Maximum flexibility for shape hunting; scales with board size; competitive play is strategically rich.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
gunkan gcd(r,s)=1
Game	Rating	Notes
Knight's Tour / Knight's Trap	⚪ Neutral	Extremely high connectivity (all coprime vectors) makes tours trivially easy; competitive play lacks strategic tension.
Knights Turing	⟖ N/A	Not in TURING_PIECES.
Palisades	❌ Negative	Excluded from game; extreme connectivity generates so many path options that non-crossing avoidance becomes trivially easy while computational cost of tracking all coprime segments is prohibitive.
Vexillum / Vexillology	⚪ Neutral	Maximum mobility; flag navigation is trivially easy; solo and competitive depth are both very low.
Mined Maze / Mined Control	✅ Positive	Maximum branching creates deep, complex deduction game; many plausible paths require careful elimination.
Polyomino / Duelomino	⚪ Neutral	Trivially easy tours; shapes are found mechanically without strategic planning; competitive play decided by speed alone.
Gunkan	✅ Positive	The designed piece for this game; extraordinary coprime mobility creates uniquely complex hidden-shape hunting; both players' paths can reach almost anywhere, making every move a real tactical decision.
Megalomino	⟖ N/A	Not currently supported.
________________________________________
Per-Game Suitability Summaries
________________________________________
Knight's Tour / Knight's Trap
General traits:
•	Positive: Can reach all squares (odd-parity or parity-breaking); connectivity supports interesting non-trivial Hamiltonian paths on boards 5-16; moderate move count (~4-16 moves) that requires strategic planning; no trivially obvious solution algorithm; meaningful blocking in competitive play
•	Neutral: Works but either trivially easy (sliders, very high-connectivity multi-set pieces) OR limited to large boards only (long-range single pieces like gazelle, flamingo); or too few moves for interesting competition
•	Negative: Even-parity / color-bound (bishop, ferz, dabbaba, alfil, tripper, camel); requires boards larger than available (pterodactyl without 16+ board); too sparse to complete tours
Rating	Pieces
✅ Positive	knight, king, zebra, giraffe, antelope, bharal, wapiti, gnu, wildebeest, zebu, bison, frog, toad, newt, mars, ceres, saturn, pallas, virgo, libra, fibonacci
⚪ Neutral	rook, queen, wazir, threeleaper, gazelle, flamingo, jupiter, scorpio, capricorn, gunkan
❌ Negative	bishop, ferz, dabbaba, alfil, tripper, camel, pterodactyl
________________________________________
Knights Turing
General traits:
•	Positive: In TURING_PIECES; distinctive enough movement pattern to create variety in the cycling rule set; sufficient connectivity to generate valid Hamiltonian paths in most piece-sequence combinations; clearly distinguishable from other pieces in the set
•	Neutral: In TURING_PIECES but very restricted (color-bound or very sparse) which creates solvability challenges in cycles; requires careful board-size tuning
•	N/A: Not in TURING_PIECES; not used in this game
Rating	Pieces
✅ Positive	knight, wazir, ferz, dabbaba, camel, zebra, giraffe
⚪ Neutral	alfil, threeleaper, tripper
⟖ N/A	all other pieces (not in TURING_PIECES)
________________________________________
Palisades
General traits:
•	Positive: Can complete a full-board Hamiltonian tour (odd-parity or parity-breaking); movement geometry produces naturally non-crossing paths or provides enough flexibility to avoid crossings; the non-crossing constraint adds genuine difficulty without making the game unsolvable
•	Neutral: Can tour but either creates very restricted non-crossing path options (board-size dependent) OR makes the non-crossing constraint too easy to satisfy (very high connectivity)
•	Negative: Cannot complete a full-board Hamiltonian tour (even-parity); excluded from game; or the geometry makes non-crossing paths practically impossible
Rating	Pieces
✅ Positive	knight, zebra, giraffe, antelope, bharal, wapiti, gnu, wildebeest, zebu, bison, frog, newt, mars, ceres, saturn, virgo, fibonacci
⚪ Neutral	gazelle, flamingo, jupiter, pallas, libra, scorpio, capricorn
❌ Negative	bishop, rook, queen, king, wazir, ferz, dabbaba, alfil, threeleaper, tripper, camel, toad, pterodactyl, gunkan (excluded from game)
________________________________________
Vexillum / Vexillology
General traits:
•	Positive: Can generate valid paths of adequate length; moderate to good branching gives the player meaningful path choices for flag collection; works well across most board sizes; the competitive variant (Vexillology) adds genuine spatial tension
•	Neutral: Either too few move options (trivially forced paths) or too many (trivially obvious navigation); limited to specific board sizes; or color-bound pieces restrict the usable portion of the board
•	Negative: Cannot generate any paths on the selected board size (even-parity, excluded from game)
Rating	Pieces
✅ Positive	knight, king, zebra, giraffe, antelope, bharal, wapiti, gnu, wildebeest, zebu, bison, frog, toad, newt, mars, ceres, saturn, pallas, virgo, libra, fibonacci
⚪ Neutral	rook, queen, wazir, gazelle, flamingo, jupiter, scorpio, capricorn, gunkan, pterodactyl
❌ Negative	bishop, ferz, dabbaba, alfil, threeleaper, tripper, camel (excluded from game)
________________________________________
Mined Maze / Mined Control
General traits:
•	Positive: Generates a valid hidden path; enough legal moves from each square that the player must genuinely deduce which is the true path; variety of directions makes the maze non-obvious; works on typical board sizes
•	Neutral: Too few moves per square (wazir, dabbaba, alfil, threeleaper, tripper - minimal deduction needed) OR requires very large boards; color-bound pieces produce interesting but sub-board mazes
•	Negative: Cannot generate useful mazes on available board sizes; piece is so restricted it produces trivially navigable paths
Rating	Pieces
✅ Positive	knight, king, rook, queen, bishop, ferz, zebra, giraffe, antelope, flamingo, bharal, wapiti, gnu, wildebeest, zebu, bison, frog, toad, newt, mars, jupiter, ceres, saturn, pallas, virgo, libra, scorpio, capricorn, fibonacci, gunkan
⚪ Neutral	wazir, dabbaba, alfil, threeleaper, tripper, camel, gazelle (board-dependent), pterodactyl (board-dependent)
❌ Negative	(none)
________________________________________
Polyomino / Duelomino
General traits:
•	Positive: Can cover all board squares (no even-parity restriction); moderate connectivity requires genuine path planning; path structure varies enough that shape reveals feel earned; the competitive variant (Duelomino) adds meaningful blocking and territorial strategy
•	Neutral: Works but tours are trivially obvious (sliders, high-connectivity multi-set pieces), removing discovery challenge; OR works only on larger boards; or very limited pieces with low strategic depth
•	Negative: Even-parity / cannot cover all squares (game premise fails); excluded from game
Rating	Pieces
✅ Positive	knight, king, zebra, giraffe, antelope, bharal, wapiti, gnu, wildebeest, zebu, bison, frog, toad, newt, mars, ceres, saturn, virgo, fibonacci
⚪ Neutral	rook, queen, wazir, gazelle, flamingo, jupiter, pallas, libra, scorpio, capricorn, gunkan, pterodactyl
❌ Negative	bishop, ferz, dabbaba, alfil, threeleaper, tripper, camel (excluded from game)
________________________________________
Gunkan
General traits:
•	Positive: Can cover all board squares (no even-parity restriction); movement creates genuine competitive tension in the hidden-shape-hunting mechanic; board coverage and directional variety make shape discovery strategic; the gunkan piece is the designed choice and most thematically appropriate
•	Neutral: Works but either trivially easy for shape hunting (very high mobility), offers limited competitive depth, or is too board-size restricted for consistent use
•	Negative: Even-parity; excluded from game
Rating	Pieces
✅ Positive	knight, king, zebra, giraffe, antelope, bharal, wapiti, gnu, wildebeest, zebu, bison, frog, toad, newt, mars, ceres, saturn, virgo, fibonacci, gunkan
⚪ Neutral	rook, queen, wazir, gazelle, flamingo, jupiter, pallas, libra, scorpio, capricorn, pterodactyl
❌ Negative	bishop, ferz, dabbaba, alfil, threeleaper, tripper, camel (excluded from game)
________________________________________
Megalomino
General traits:
•	Positive: The piece must complete a knight's tour on an irregular polyomino shape; currently only the knight is implemented and supported
•	N/A: No other piece is currently supported
Rating	Pieces
✅ Positive	knight (only supported piece)
⟖ N/A	all other pieces (not currently implemented)
________________________________________

Summary Observations
Most universally suitable pieces (positive across most or all games): knight, king, zebra, giraffe, antelope, bharal, fibonacci — they have odd parity, moderate connectivity, and work across the typical board size range.
Strong new additions: wapiti (ferz+knight), gnu (knight+camel), wildebeest (knight+zebra), saturn (threeleaper+alfil) — all parity-breaking two-set pieces that perform well across nearly all games.
Strong for non-tour games only (Mined Maze/Control): bishop, ferz, camel — color-bound so excluded from tour games but produce interesting path/maze structures in Mined Maze / Mined Control which does not require full board coverage.
Technically valid but strategically thin for tour games: queen, rook (trivially obvious), and very high-connectivity pieces like gunkan and jupiter (too many options remove strategic challenge).
Consistently negative for Hamiltonian games: ferz, dabbaba, alfil, tripper, camel (even-parity); pterodactyl across almost all games (color-bound below 16×16, practically inaccessible).
Board-size sensitive: gazelle, flamingo, bharal, pallas, libra, scorpio, capricorn — positive only when the relevant board-size constraint is satisfied; neutral or negative on smaller boards.
Knights Turing exclusive: only knight, wazir, ferz, dabbaba, alfil, threeleaper, tripper, camel, zebra, giraffe are used; all other pieces are N/A for that game.
Palisades exclusive exclusions: bishop, rook, queen, king, wazir, ferz, dabbaba, alfil, threeleaper, tripper, camel, toad, pterodactyl, gunkan are excluded by the game's design; remaining pieces provide a range of non-crossing tour challenges.