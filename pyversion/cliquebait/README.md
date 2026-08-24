# Cliquebait

**avoid monochromatic cliques in a colored complete graph**

## Overview

Cliquebait is a geometric, move-based graph coloring game.
You move a single chess piece around a square board.
Every visited square becomes a **vertex**.
The game automatically draws an **edge** between every pair of visited vertices,
colored by distance:

- 🔵 **Blue** — distance ≤ threshold T  
- 🔴 **Red** — distance > threshold T  

The game ends the moment a move creates a **monochromatic k-clique** — a set of k
vertices all connected by edges of the same color.
Your score is the number of squares visited before that happens.

**Goal:** visit as many squares as possible without forming a monochromatic k-clique!

## How to Play

1. Choose your piece, board size, and clique settings.
2. Click any square to place your piece — that is your first vertex.
3. Move the piece to an unvisited square using legal piece moves.
   Each new square adds a vertex and edges to all previous vertices.
4. Watch the edges: blue = close pairs, red = far pairs.
5. The game ends when a k-clique of one color appears.

## Settings

| Setting | Range | Description |
|---------|-------|-------------|
| Board size | 5–16 | Grid dimensions |
| Piece | any leaper | Determines legal moves |
| Clique size k | 3–6 | Game-over clique size (larger = harder to trigger) |
| Threshold T | 3–6 | Distance cutoff for edge coloring |
| Distance method | air / taxi | Euclidean or Manhattan distance |

**All three clique/threshold/distance settings remain active during gameplay.**
You can change them at any time to explore how they affect the current position.

## Background — Ramsey Theory

Cliquebait is inspired by **Ramsey theory**.
The classical Ramsey number R(k, k) is the smallest n such that any 2-coloring
of the complete graph K_n must contain a monochromatic k-clique.

Known values: R(3,3) = 6, R(4,4) = 18, R(5,5) ∈ [43, 48].

In Cliquebait the coloring is geometric and determined by your piece path —
so the board layout and piece movement give you some control over which edges
get which color. Can you find patterns that delay the inevitable clique?
