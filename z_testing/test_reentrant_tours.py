import sys
import os
# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pyversion.tourbus import HEXADECOMINO_TOURS

# Define knight moves
KNIGHT_MOVES = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                (1, -2), (1, 2), (2, -1), (2, 1)]

def is_legal_knight_move(start, end):
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    return (dx, dy) in KNIGHT_MOVES

py_filename = "tours_reentrant16.py"
reentrant_tours = {}

for key, tour in HEXADECOMINO_TOURS.items():
    first = tour[0]
    last = tour[-1]
    if is_legal_knight_move(last, first):
        # Remove leading single quote if present (since data sources use it for CSV formatting, not for code keys)
        norm_key = key if not key.startswith("'") else key[1:]
        reentrant_tours[norm_key] = tour

with open(py_filename, "w") as pyfile:
    pyfile.write("SUCCESSFUL_TOURS = {\n")
    for key, tour in reentrant_tours.items():
        # Add RE- prefix if not already present
        output_key = key if key.startswith("RE-") else f"RE-{key}"
        pyfile.write(f'    "{output_key}": {tour},\n')
    pyfile.write("}\n")