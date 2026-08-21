import csv
from pyversion.tourbus import HEXADECOMINO_TOURS

def normalize(coords):
    minx = min(x for x, y in coords)
    miny = min(y for x, y in coords)
    return tuple(sorted((x - minx, y - miny) for x, y in coords))

def rotated(coords):
    shapes = []
    current = list(coords)
    for _ in range(4):
        current = [(y, -x) for x, y in current]  # 90 degree rotation
        shapes.append(normalize(current))
    return shapes

def reflected(coords):
    coords_ref = [(-x, y) for x, y in coords]
    return normalize(coords_ref)

def all_orientations(coords):
    orientations = set()
    base = normalize(coords)
    # Four rotations
    for shape in rotated(base):
        orientations.add(shape)
    # Four rotations of the reflection
    reflected_shape = normalize([(-x, y) for x, y in base])
    for shape in rotated(reflected_shape):
        orientations.add(shape)
    return orientations

csv_filename = "orientation_count.csv"
total_orientations = 0

with open(csv_filename, "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["key", "unique_orientations"])
    for key, coords in HEXADECOMINO_TOURS.items():
        unique_shapes = all_orientations(coords)
        count = len(unique_shapes)
        total_orientations += count
        print(f"{key} {count}")
        writer.writerow([key, count])

print(f"Total unique orientations: {total_orientations}")
with open(csv_filename, "a", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow([])
    writer.writerow(["Total", total_orientations])