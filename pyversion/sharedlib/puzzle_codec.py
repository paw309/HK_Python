"""
Generic Puzzle Codec - Encode/decode puzzle parameters into shareable codes.

Define a parameter schema for each game with field names, bit widths, and lookup mappings.
This module can be imported and used by any game requiring deterministic configuration codes.

Example usage:
    from puzzle_codec import encode_params, decode_params, polyomino_schema

    # Encode
    code = encode_params(params, polyomino_schema, seed)
    # Decode
    decoded = decode_params(code, polyomino_schema)
"""

import base64
from typing import Dict, List, Any

# Version for future compatibility
CODEC_VERSION = 1

# --- Example mappings for Polyominoes game ---
SHAPE_MAP = {
    "monomino": 0, "domino": 1, "triomino": 2, "tetromino": 3,
    "pentomino": 4, "hexomino": 5, "heptomino": 6, "octomino": 7, "mixed": 8
}

DENSITY_MAP = {"low": 0, "medium": 1, "high": 2}
COLOR_MAP = {"unique": 0, "random": 1, "same": 2}

# --- Example generic schema for Polyominoes ---
# Each field: (name, bits, mapping OR min/max)
polyomino_schema: List = [
    ("board", 4, lambda v: int(v)),               # board size, 4 bits: 5..16
    ("shapes", 3, SHAPE_MAP),                     # shape type, 3 bits
    ("density", 2, DENSITY_MAP),                  # density, 2 bits
    ("colors", 2, COLOR_MAP),                     # color mode, 2 bits
]

# General encode/decode using schema
def encode_params(params: Dict[str, Any], schema: List, seed: int, version: int = CODEC_VERSION) -> str:
    settings = version << 12  # Assume 4 bits for version at the top (adjust as needed)
    bit_offset = 12
    for item in schema:
        name, bits, mapping = item
        value = params[name]
        if callable(mapping):
            value = mapping(value)
        elif isinstance(mapping, dict):
            value = mapping[value]
        settings |= value << (bit_offset - bits)
        bit_offset -= bits
    data = settings.to_bytes(2, 'big') + int(seed).to_bytes(8, 'big')
    encoded = base64.b32encode(data).decode('ascii').rstrip('=')
    return '-'.join([encoded[i:i + 4] for i in range(0, len(encoded), 4)])

def decode_params(code: str, schema: List) -> Dict[str, Any]:
    code = code.replace('-', '').replace(' ', '').upper()
    padding = (8 - len(code) % 8) % 8
    code += '=' * padding
    data = base64.b32decode(code)
    settings = int.from_bytes(data[:2], 'big')
    seed = int.from_bytes(data[2:], 'big')
    version = (settings >> 12) & 0xF
    bit_offset = 12
    decoded = {"seed": seed, "version": version}
    for item in schema:
        name, bits, mapping = item
        value = (settings >> (bit_offset - bits)) & (2**bits - 1)
        if callable(mapping):
            decoded[name] = value
        elif isinstance(mapping, dict):
            reverse_map = {v: k for k, v in mapping.items()}
            decoded[name] = reverse_map[value]
        bit_offset -= bits
    return decoded

class PuzzleCodeError(Exception):
    """Raised when puzzle code is invalid"""
    pass

# --- For self-z_testing ---
if __name__ == "__main__":
    print("Generic Puzzle Codec Self-Test")
    print("=" * 50)
    # Define test parameters for polyominoes
    test_params = {
        "board": 8,
        "shapes": "tetromino",
        "density": "medium",
        "colors": "unique",
    }
    test_seed = 123456789012345
    code = encode_params(test_params, polyomino_schema, test_seed)
    print(f"Encoded: {code}")
    decoded = decode_params(code, polyomino_schema)
    print(f"Decoded: {decoded}")
    assert decoded["board"] == 8
    assert decoded["shapes"] == "tetromino"
    assert decoded["density"] == "medium"
    assert decoded["colors"] == "unique"
    assert decoded["seed"] == test_seed
    print("\n✓ All tests passed!")

    # Example for another game (define your own schema and mapping!)