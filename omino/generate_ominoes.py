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
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            np = (x+dx, y+dy)
            if np not in poly:
                new_poly = poly + (np,)
                # Check for equivalence
                norm_variants = all_orientations(new_poly)
                key = min(norm_variants)
                if key not in seen:
                    seen.add(key)
                    polys.append(key)
    return polys

def enumerate_polyominoes(n):
    """Generate all n-ominoes up to symmetries."""
    seen = set()
    polyominoes = set()
    start = ((0,0),)
    seen.add(normalize(start))
    stack = [normalize(start)]
    for _ in range(n-1):
        nxt = []
        local_seen = set()
        for poly in stack:
            children = add_square(poly, local_seen)
            nxt.extend(children)
        stack = nxt
    for poly in stack:
        polyominoes.add(poly)
    return list(polyominoes)

# Generate free x-ominoes
tridecominoes = enumerate_polyominoes(13)
print(f"generated {len(tridecominoes)} tridecominoes")

# Build output dict to match polyomino_data.py style
output = "SAMPLE_POLYOMINOES = {\n"
for idx, poly in enumerate(sorted(tridecominoes)):
    coords = ", ".join(str(pt) for pt in poly)
    output += f'    "13-{idx+1:03d}": [{coords}],\n'
output += "}\n"

with open("../pyversion/tourbus/polymath/tridecomino_data.py", "w") as f:
    f.write('"""\nAuto-generated tridecominoes data.\n"""\n\n')
    f.write(output)

print("tridecomino_data.py written")