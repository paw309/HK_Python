"""
megalomino_codec.py

Codec for dynamically generated polyominoes.

Encodes a pair of base shape IDs (e.g., "09-219" and "07-043") into a
compact, human-readable code such as "16-4RH0B-00017", and decodes it back to
the original component IDs so the larger polyomino can be reconstructed
deterministically.

Code format
-----------
  "<target_size>-<encoded_id_A>-<encoded_id_B>"

  * target_size  – integer, always equals size_A + size_B
  * encoded_id   – 5-character base-36 string derived from the component's
                   (size, index) pair as described in encode_shape_id().

Examples
--------
  >>> code = encode("09-219", "07-043")
  >>> decode(code)
  (16, '09-219', '07-043')

Extension points
----------------
Additional parameters (transformations, anchor points) can be appended to the
code as extra '-' segments.  decode() ignores segments beyond the two required
groups, and callers may parse them separately.
"""

from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Base-36 helpers
# ---------------------------------------------------------------------------

_BASE36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_CODE_WIDTH = 5   # Characters per encoded shape ID group

# Encoding parameters
# value = (size - _SIZE_OFFSET) * _INDEX_STRIDE + raw_index
# Maximum size offset:  15 - 7 = 8
# Maximum raw_index for any tour dictionary: ~3,424,869  (size-15 shapes)
# Maximum value: 8 * 4_000_000 + 3_424_869 = 35_424_869
# 36 ** 5 = 60_466_176 > 35_424_869  =>  5 characters always sufficient
_SIZE_OFFSET = 7
_INDEX_STRIDE = 4_000_000


def _int_to_base36(n: int, width: int = _CODE_WIDTH) -> str:
    """Convert a non-negative integer to an upper-case base-36 string of *width* chars."""
    if n < 0:
        raise ValueError(f"Cannot encode negative integer: {n}")
    chars = []
    while n:
        chars.append(_BASE36[n % 36])
        n //= 36
    result = "".join(reversed(chars)) if chars else "0"
    return result.zfill(width).upper()


def _base36_to_int(s: str) -> int:
    """Convert a base-36 string (any case) to a non-negative integer."""
    return int(s.upper(), 36)


# ---------------------------------------------------------------------------
# Shape-ID encoding/decoding
# ---------------------------------------------------------------------------
# Shape IDs have the format  "<size>-<index>"  e.g. "07-043", "15-29727".
# Sizes range from 7 to 15 for static shapes; the index is the raw catalog
# number (not zero-padded, can be up to ~3.4 million for size-15 shapes).
#
# We pack (size, index) into a single integer:
#   value = (size - 7) * 4_000_000 + index
#
# Maximum value:  (15 - 7) * 4_000_000 + 3_424_869  =  35_424_869
# 36 ** 5 = 60_466_176  >  35_424_869,  so 5 characters are always sufficient.


def encode_shape_id(shape_id: str) -> str:
    """
    Encode a static shape ID like ``"07-043"`` or ``"15-29727"`` to a 5-character
    upper-case base-36 string.

    Raises ValueError if the shape_id cannot be parsed.
    """
    parts = shape_id.split("-")
    if len(parts) != 2:
        raise ValueError(f"Malformed shape_id: {shape_id!r}")
    size = int(parts[0])
    idx = int(parts[1])
    if size < 7 or size > 15:
        raise ValueError(f"size {size} out of encodable range [7, 15]")
    if idx < 0 or idx >= _INDEX_STRIDE:
        raise ValueError(f"index {idx} out of range [0, {_INDEX_STRIDE})")
    value = (size - _SIZE_OFFSET) * _INDEX_STRIDE + idx
    return _int_to_base36(value, _CODE_WIDTH)


def decode_shape_id(code: str) -> Tuple[int, int]:
    """
    Decode a 5-character base-36 string back to ``(size, raw_index)``.

    Raises ValueError if *code* represents an out-of-range combination.
    """
    value = _base36_to_int(code.strip())
    size = value // _INDEX_STRIDE + _SIZE_OFFSET
    idx = value % _INDEX_STRIDE
    if size < 7 or size > 15:
        raise ValueError(f"Decoded size {size} out of range [7, 15]")
    return size, idx


def _canonical_shape_id(size: int, idx: int) -> str:
    """
    Reconstruct the canonical shape ID string for *size* and *idx*.

    The tour dictionary keys use ``"{size:02d}-{idx:03d}"`` which zero-pads
    the index to at least 3 digits (e.g. "07-043", "09-219", "15-29727").
    """
    return f"{size:02d}-{idx:03d}"


# ---------------------------------------------------------------------------
# Public codec API
# ---------------------------------------------------------------------------

def encode(shape_id_a: str, shape_id_b: str) -> str:
    """
    Encode two component shape IDs into a combined polyomino code.

    Parameters
    ----------
    shape_id_a, shape_id_b
        Static shape IDs of the two components, e.g. ``"09-219"`` and
        ``"07-043"``.

    Returns
    -------
    str
        A code like ``"16-XXXXX-YYYYY"`` where the first group is the combined
        size and the following groups are the base-36-encoded component IDs.
    """
    size_a = int(shape_id_a.split("-")[0])
    size_b = int(shape_id_b.split("-")[0])
    target = size_a + size_b
    enc_a = encode_shape_id(shape_id_a)
    enc_b = encode_shape_id(shape_id_b)
    return f"{target}-{enc_a}-{enc_b}"


def decode(code: str) -> Optional[Tuple[int, str, str]]:
    """
    Decode a polyomino code into ``(target_size, shape_id_a, shape_id_b)``.

    Parameters
    ----------
    code
        A string in the format ``"NN-AAAAA-BBBBB"`` (case-insensitive).
        Extra ``'-'``-delimited segments after the third group are ignored to
        allow forward-compatible extension.

    Returns
    -------
    tuple or None
        ``(target_size, shape_id_a, shape_id_b)`` on success, ``None`` on
        any parse error.
    """
    parts = code.strip().upper().split("-")
    if len(parts) < 3:
        return None
    try:
        target = int(parts[0])
        size_a, idx_a = decode_shape_id(parts[1])
        size_b, idx_b = decode_shape_id(parts[2])
        # Sanity-check: sizes must add up to target
        if size_a + size_b != target:
            return None
        id_a = _canonical_shape_id(size_a, idx_a)
        id_b = _canonical_shape_id(size_b, idx_b)
        return target, id_a, id_b
    except (ValueError, IndexError):
        return None


def is_dynamic_code(s: str) -> bool:
    """
    Return True if *s* looks like a dynamic polyomino code
    (``"NN-CCCCC-CCCCC"``), False otherwise.

    This is a format-only check; it does not verify that the embedded shape
    IDs actually exist in any tour dictionary.
    """
    parts = s.strip().upper().split("-")
    if len(parts) < 3:
        return False
    try:
        int(parts[0])           # target size must be an integer
        if len(parts[1]) != _CODE_WIDTH or len(parts[2]) != _CODE_WIDTH:
            return False
        _base36_to_int(parts[1])  # must be valid base-36
        _base36_to_int(parts[2])
        return True
    except (ValueError, IndexError):
        return False


def derive_seed(shape_id_a: str, shape_id_b: str) -> int:
    """
    Derive a deterministic integer seed from two component shape IDs.

    The same pair of IDs always yields the same seed, enabling reproducible
    tour combination.  The order of arguments matters (A then B).
    """
    import hashlib
    digest = hashlib.sha256(f"{shape_id_a}:{shape_id_b}".encode()).hexdigest()
    return int(digest[:8], 16)