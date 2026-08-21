import json
import os
import random
from typing import List, Tuple, Set, Dict, Optional

BOARD_W = 8
BOARD_H = 8
Coord = Tuple[int, int]


def bit(x: int, y: int) -> int:
    return 1 << (y * BOARD_W + x)


def load_16_pool(path: str) -> List[Dict]:
    """
    Load tours_16.json with schema:
    {
      "16-001": [[x,y], [x,y], ...],
      ...
    }
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    polys = []
    for pid, coords in data.items():
        tour = [(int(x), int(y)) for x, y in coords]
        cells = set(tour)
        xs = [x for x, _ in cells]
        ys = [y for _, y in cells]
        minx, miny = min(xs), min(ys)
        # normalize to (0,0)
        norm_cells = {(x - minx, y - miny) for x, y in cells}
        norm_tour = [(x - minx, y - miny) for x, y in tour]

        # compute mask + bbox
        mask = 0
        xs2 = [x for x, _ in norm_cells]
        ys2 = [y for _, y in norm_cells]
        for x, y in norm_cells:
            mask |= bit(x, y)
        bbox = (min(xs2), min(ys2), max(xs2), max(ys2))

        polys.append({
            "id": pid,
            "cells": norm_cells,
            "tour": norm_tour,
            "mask": mask,
            "bbox": bbox
        })

    return polys


def translate_cells(cells: Set[Coord], dx: int, dy: int) -> Optional[Set[Coord]]:
    new = set()
    for x, y in cells:
        nx, ny = x + dx, y + dy
        if not (0 <= nx < BOARD_W and 0 <= ny < BOARD_H):
            return None
        new.add((nx, ny))
    return new


def translate_tour(tour: List[Coord], dx: int, dy: int) -> Optional[List[Coord]]:
    new = []
    for x, y in tour:
        nx, ny = x + dx, y + dy
        if not (0 <= nx < BOARD_W and 0 <= ny < BOARD_H):
            return None
        new.append((nx, ny))
    return new


def orth_connected(cells: Set[Coord]) -> bool:
    if not cells:
        return False
    start = next(iter(cells))
    stack = [start]
    visited = {start}
    while stack:
        x, y = stack.pop()
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx, ny = x + dx, y + dy
            if (nx, ny) in cells and (nx, ny) not in visited:
                visited.add((nx, ny))
                stack.append((nx, ny))
    return len(visited) == len(cells)


KNIGHT = [(1,2),(2,1),(2,-1),(1,-2),(-1,-2),(-2,-1),(-2,1),(-1,2)]


def knight_can_move(a: Coord, b: Coord) -> bool:
    ax, ay = a
    bx, by = b
    return (bx - ax, by - ay) in KNIGHT


def stitch_two_16ominoes(pool: List[Dict], max_attempts: int = 50000):
    """
    Pick two 16-omino tours and stitch them into a 32-square superomino.
    """
    for _ in range(max_attempts):
        A = random.choice(pool)
        B = random.choice(pool)
        if A["id"] == B["id"]:
            continue

        # Try placing A at (0,0) normalized
        Acells = A["cells"]
        Atour = A["tour"]

        # Try all translations of B
        minx, miny, maxx, maxy = B["bbox"]
        w = maxx - minx + 1
        h = maxy - miny + 1
        max_dx = BOARD_W - w
        max_dy = BOARD_H - h

        for dx in range(0, max_dx + 1):
            for dy in range(0, max_dy + 1):
                Bcells = translate_cells(B["cells"], dx - minx, dy - miny)
                if Bcells is None:
                    continue
                # no overlap
                if Acells & Bcells:
                    continue

                combined = Acells | Bcells
                # must be orthogonally contiguous
                if not orth_connected(combined):
                    continue

                Btour = translate_tour(B["tour"], dx - minx, dy - miny)
                if Btour is None:
                    continue

                # stitch condition: end(A) -> start(B)
                if knight_can_move(Atour[-1], Btour[0]):
                    # success
                    stitched_tour = Atour + Btour
                    return combined, stitched_tour, (A["id"], B["id"])

    raise RuntimeError("Failed to stitch two 16-ominoes within attempt limit")


def ascii_visualize(cells: Set[Coord], tour: List[Coord]) -> str:
    order = {c: i for i, c in enumerate(tour)}
    lines = []
    for y in range(BOARD_H):
        row = []
        for x in range(BOARD_W):
            c = (x, y)
            if c in cells:
                row.append(str(order[c] % 10))
            else:
                row.append(".")
        lines.append("".join(row))
    return "\n".join(lines)

def svg_visualize_tour(tour: List[Tuple[int,int]], cell: int = 40) -> str:
    """
    Render an 8×8 knight's tour as an SVG string.
    - tour: list of (x,y) coordinates in order
    - cell: pixel size of each board square
    """
    w = BOARD_W * cell
    h = BOARD_H * cell

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
               f'viewBox="0 0 {w} {h}">')

    # background
    svg.append(f'<rect x="0" y="0" width="{w}" height="{h}" fill="white" />')

    # grid lines
    for x in range(BOARD_W + 1):
        X = x * cell
        svg.append(f'<line x1="{X}" y1="0" x2="{X}" y2="{h}" stroke="#ccc" />')
    for y in range(BOARD_H + 1):
        Y = y * cell
        svg.append(f'<line x1="0" y1="{Y}" x2="{w}" y2="{Y}" stroke="#ccc" />')

    # path
    if tour:
        path_cmds = []
        for i, (x, y) in enumerate(tour):
            cx = x * cell + cell/2
            cy = y * cell + cell/2
            if i == 0:
                path_cmds.append(f"M {cx} {cy}")
            else:
                path_cmds.append(f"L {cx} {cy}")
        svg.append(f'<path d="{" ".join(path_cmds)}" stroke="blue" stroke-width="3" fill="none" />')

    # nodes + labels
    for i, (x, y) in enumerate(tour):
        cx = x * cell + cell/2
        cy = y * cell + cell/2
        svg.append(f'<circle cx="{cx}" cy="{cy}" r="{cell/6}" fill="red" />')
        svg.append(
            f'<text x="{cx}" y="{cy}" font-size="{cell/3}" '
            f'text-anchor="middle" dominant-baseline="central" fill="white">{i}</text>'
        )

    svg.append("</svg>")
    return "\n".join(svg)


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pool = load_16_pool(os.path.join(base_dir, "tours_16.json"))

    cells, tour, (idA, idB) = stitch_two_16ominoes(pool)

    print("Stitched polyominoes:", idA, "→", idB)
    print("Tour length:", len(tour))
    # print("\nASCII visualization:")
    # print(ascii_visualize(cells, tour))

    svg = svg_visualize_tour(tour)
    with open("../stitches/stitched_superomino.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print("SVG written to stitched_superomino.svg")


if __name__ == "__main__":
    main()
