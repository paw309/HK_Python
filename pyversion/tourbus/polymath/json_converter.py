import json
from octomino_data import SAMPLE_POLYOMINOES  # Import your dict

# JSON requires key-value structures; tuple coordinates become lists/arrays in JSON
json_output_path = "../../../../Hamiltonian-Knights/web/public/polyominoes/octomino_data.json"

with open(json_output_path, "w", encoding="utf-8") as f:
    json.dump(SAMPLE_POLYOMINOES, f, separators=(",", ":"))

print(f"Exported polyomino coordinates to {json_output_path}")
