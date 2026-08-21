import itertools


def normalize(poly):
    min_x = min(x for x, y in poly)
    min_y = min(y for x, y in poly)
    return tuple(sorted((x - min_x, y - min_y) for x, y in poly))


def all_orientations(poly):
    variants = []
    for rx in range(4):
        for flip in [False, True]:
            p = [(x, y) for x, y in poly]
            # Rotate
            for _ in range(rx):
                p = [(-y, x) for x, y in p]
            # Flip
            if flip:
                p = [(-x, y) for x, y in p]
            variants.append(normalize(p))
    return set(variants)


def add_square(poly, seen):
    polys = []
    for x, y in poly:
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            np = (x + dx, y + dy)
            if np not in poly:
                new_poly = poly + (np,)
                # Check for equivalence
                norm_variants = all_orientations(new_poly)
                key = min(norm_variants)
                if key not in seen:
                    seen.add(key)
                    print(f"Generated polyomino #{len(seen)}")
                    polys.append(key)
    return polys


def enumerate_polyominoes(n):
    """Generate all n-ominoes up to symmetries."""
    seen = set()
    polyominoes = set()
    start = ((0, 0),)
    seen.add(normalize(start))
    stack = [normalize(start)]
    for _ in range(n - 1):
        nxt = []
        local_seen = set()
        for poly in stack:
            children = add_square(poly, local_seen)
            nxt.extend(children)
        stack = nxt
    for poly in stack:
        polyominoes.add(poly)
    return list(polyominoes)


# PARAMETERS
LINES_PER_FILE = 100000
FILE_PREFIX = "pentadecomino_data"
N = 15

# Generate all 15-square polyominoes
pentadecominoes = enumerate_polyominoes(N)
print(f"generated {len(pentadecominoes)} pentadecominoes")

file_idx = 1
line_idx = 0

outfile = open(f"{FILE_PREFIX}{file_idx}.py", "w")
outfile.write('"""\nAuto-generated pentadecominoes data.\n"""\n\n')
outfile.write("PEN_POLYOMINOES = {\n")

for idx, poly in enumerate(sorted(pentadecominoes)):
    coords = ", ".join(str(pt) for pt in poly)
    outfile.write(f'    "15-{idx + 1:03d}": [{coords}],\n')
    line_idx += 1

    if line_idx >= LINES_PER_FILE:
        # Close off current dict and file, open the next
        outfile.write("}\n")
        outfile.close()
        print(f"{FILE_PREFIX}{file_idx}.py written ({line_idx} lines)")
        file_idx += 1
        line_idx = 0
        # Start new file
        outfile = open(f"{FILE_PREFIX}{file_idx}.py", "w")
        outfile.write('"""\nAuto-generated pentadecominoes data.\n"""\n\n')
        outfile.write("PEN_POLYOMINOES = {\n")

# After loop, close the final file if it's still open
outfile.write("}\n")
outfile.close()
print(f"{FILE_PREFIX}{file_idx}.py written (final file, {line_idx} lines)")