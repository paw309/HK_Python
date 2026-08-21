import json

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

def has_2x2_block(poly):
    """Return True if the polyomino contains ANY 2×2 solid block."""
    s = set(poly)
    for x, y in s:
        if (x+1, y) in s and (x, y+1) in s and (x+1, y+1) in s:
            return True
    return False

def add_square(poly, seen):
    polys = []
    for x, y in poly:
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            np = (x+dx, y+dy)
            if np not in poly:
                new_poly = poly + (np,)
                norm_variants = all_orientations(new_poly)
                key = min(norm_variants)
                if key not in seen:
                    seen.add(key)
                    polys.append(key)
    return polys

def enumerate_only_15_skinny():
    """Enumerate ONLY 15-square polyominoes with NO 2×2 blocks."""
    start = ((0,0),)
    stack = [normalize(start)]

    for size in range(1, 15):
        nxt = []
        local_seen = set()
        for poly in stack:
            children = add_square(poly, local_seen)
            nxt.extend(children)
        stack = nxt
        print(f"grown to size {size+1}, frontier count = {len(stack)}")

    # Now filter out blocky shapes
    skinny = [p for p in stack if not has_2x2_block(p)]
    return skinny

# Generate skinny 15-ominoes
hexadecominoes = enumerate_only_15_skinny()
print(f"generated {len(hexadecominoes)} skinny hexadecominoes")

# Build JSON dict
output_dict = {}
count = 0

for idx, poly in enumerate(sorted(hexadecominoes)):
    key = f"15-{idx+1:03d}"
    output_dict[key] = list(poly)

    count += 1
    if count % 1000 == 0:
        print(f"processed {count} polyominoes...")

# Print JSON to stdout
# print(json.dumps(output_dict, separators=(",", ":")))

# Write JSON to a file instead of printing it
with open("skinny_15ominoes.json", "w") as f:
    json.dump(output_dict, f, separators=(",", ":"))

