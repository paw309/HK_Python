import json
import os
import random
from typing import List, Tuple, Set, Dict, Optional

BOARD_W = 8
BOARD_H = 8
Coord = Tuple[int, int]

KNIGHT = [(1,2),(2,1),(2,-1),(1,-2),(-1,-2),(-2,-1),(-2,1),(-1,2)]


def bit(x: int, y: int) -> int:
    return 1 << (y * BOARD_W + x)


def load_pool(base_dir: str, n: int) -> List[Dict]:
    """
    Load tours_n.json with schema:
    {
      "n-XXX": [[x,y],[x,y],...],
      ...
    }
    Normalize each shape so its min (x,y) is at (0,0).
    """
    path = os.path.join(base_dir, f"tours_{n}.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    polys = []
    for pid, coords in data.items():
        tour = [(int(x), int(y)) for x, y in coords]
        cells = set(tour)
        xs = [x for x, _ in cells]
        ys = [y for _, y in cells]
        minx, miny = min(xs), min(ys)

        norm_cells = {(x - minx, y - miny) for x, y in cells}
        norm_tour = [(x - minx, y - miny) for x, y in tour]

        xs2 = [x for x, _ in norm_cells]
        ys2 = [y for _, y in norm_cells]
        bbox = (min(xs2), min(ys2), max(xs2), max(ys2))

        polys.append({
            "id": pid,
            "cells": norm_cells,
            "tour": norm_tour,
            "bbox": bbox
        })
    return polys


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


def knight_can_move(a: Coord, b: Coord) -> bool:
    ax, ay = a
    bx, by = b
    return (bx - ax, by - ay) in KNIGHT


def rotate(coord: Coord, k: int) -> Coord:
    x, y = coord
    if k == 0:
        return x, y
    elif k == 1:
        return y, -x
    elif k == 2:
        return -x, -y
    elif k == 3:
        return -y, x
    else:
        raise ValueError


def reflect_x(coord: Coord) -> Coord:
    x, y = coord
    return -x, y


def apply_symmetry(cells: Set[Coord], tour: List[Coord], rot: int, refl: bool) -> Tuple[Set[Coord], List[Coord]]:
    def transform(c: Coord) -> Coord:
        c2 = rotate(c, rot)
        if refl:
            c2 = reflect_x(c2)
        return c2

    scells = {transform(c) for c in cells}
    stour = [transform(c) for c in tour]

    xs = [x for x, _ in scells]
    ys = [y for _, y in scells]
    minx, miny = min(xs), min(ys)
    scells2 = {(x - minx, y - miny) for x, y in scells}
    stour2 = [(x - minx, y - miny) for x, y in stour]
    return scells2, stour2


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


def stitch_pair_mn(poolA: List[Dict], poolB: List[Dict], max_attempts: int = 50000):
    """
    Stitch one shape from poolA (size m) with one from poolB (size n)
    into a single knight's tour over the union.
    """
    for _ in range(max_attempts):
        A = random.choice(poolA)
        B = random.choice(poolB)

        # allow same ID if pools differ; avoid if same pool
        if poolA is poolB and A["id"] == B["id"]:
            continue

        for rotA in range(4):
            for reflA in [False, True]:
                Acells, Atour = apply_symmetry(A["cells"], A["tour"], rotA, reflA)

                for rotB in range(4):
                    for reflB in [False, True]:
                        Bcells0, Btour0 = apply_symmetry(B["cells"], B["tour"], rotB, reflB)

                        xs = [x for x, _ in Bcells0]
                        ys = [y for _, y in Bcells0]
                        minx, miny = min(xs), min(ys)
                        maxx, maxy = max(xs), max(ys)
                        w = maxx - minx + 1
                        h = maxy - miny + 1
                        max_dx = BOARD_W - w
                        max_dy = BOARD_H - h

                        for dx in range(0, max_dx + 1):
                            for dy in range(0, max_dy + 1):
                                Bcells = translate_cells(Bcells0, dx - minx, dy - miny)
                                if Bcells is None:
                                    continue
                                if Acells & Bcells:
                                    continue
                                combined = Acells | Bcells
                                if not orth_connected(combined):
                                    continue
                                Btour = translate_tour(Btour0, dx - minx, dy - miny)
                                if Btour is None:
                                    continue

                                candidates = [
                                    (Atour, Btour, Atour[-1], Btour[0]),
                                    (Atour, list(reversed(Btour)), Atour[-1], Btour[-1]),
                                    (list(reversed(Atour)), Btour, Atour[0], Btour[0]),
                                    (list(reversed(Atour)), list(reversed(Btour)), Atour[0], Btour[-1]),
                                ]

                                for tourA, tourB, a_end, b_start in candidates:
                                    if knight_can_move(a_end, b_start):
                                        stitched = tourA + tourB
                                        return combined, stitched, (A["id"], B["id"])

    raise RuntimeError("Failed to stitch m×n pair within attempt limit")


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


def svg_visualize_tour(tour: List[Coord], cell: int = 40) -> str:
    w = BOARD_W * cell
    h = BOARD_H * cell
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">')

    # NEW: alternating background squares
    light_beige = "#f4e4c3"
    light_green = "#d8f5d0"
    for y in range(BOARD_H):
        for x in range(BOARD_W):
            color = light_beige if (x + y) % 2 == 0 else light_green
            svg.append(
                f'<rect x="{x*cell}" y="{y*cell}" width="{cell}" height="{cell}" fill="{color}" />'
            )

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
            f'<text x="{cx}" y="{cy}" font-size="{cell/3}" text-anchor="middle" '
            f'dominant-baseline="central" fill="white">{i}</text>'
        )

    svg.append("</svg>")
    return "\n".join(svg)

def generate_stitched_mn(base_dir: str, m: int, n: int):
    poolA = load_pool(base_dir, m)
    poolB = load_pool(base_dir, n)
    cells, tour, (idA, idB) = stitch_pair_mn(poolA, poolB)
    return cells, tour, idA, idB


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    pairs = [
        (10, 10), (10, 11), (10, 12), (10, 13), (10, 14), (10, 15), (10, 16),
        (11, 11), (11, 12), (11, 13), (11, 14), (11, 15), (11, 16),
        (12, 12), (12, 13), (12, 14), (12, 15), (12, 16),
        (13, 13), (13, 14), (13, 15), (13, 16),
        (14, 14), (14, 15), (14, 16),
        (15, 15), (15, 16),
        (16, 16),
    ]

    for m, n in pairs:
        try:
            cells, tour, idA, idB = generate_stitched_mn(base_dir, m, n)
        except Exception as e:
            print(f"{m}+{n}: failed ({e})")
            continue

        print(f"\n{m}+{n}: stitched {idA} + {idB}, tour length={len(tour)}")
        print(ascii_visualize(cells, tour))

        svg = svg_visualize_tour(tour)
        out_path = os.path.join(base_dir, f"stitched_{m}_{n}_{idA}_{idB}.svg")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"SVG written to {out_path}")


if __name__ == "__main__":
    main()
