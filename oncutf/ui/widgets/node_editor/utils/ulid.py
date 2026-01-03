"""ULID generator utilities.

This module provides a dependency-free ULID generator suitable for stable,
portable identifiers in serialized snapshots.

The generated ULID is a 26-character, Crockford base32 encoded string:
- 48 bits timestamp (milliseconds since Unix epoch)
- 80 bits randomness

Notes:
- This implementation is not monotonic across calls within the same ms.
- It is designed to be pure-Python and IO-free.

Author:
    Michael Economou

Date:
    2025-12-14
"""

from __future__ import annotations

import os
import time

_CROCKFORD_BASE32_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _encode_crockford_base32(value: int, length: int) -> str:
    if value < 0:
        raise ValueError("value must be non-negative")

    chars: list[str] = []
    for _ in range(length):
        chars.append(_CROCKFORD_BASE32_ALPHABET[value & 31])
        value >>= 5

    if value != 0:
        raise ValueError("value too large to encode with requested length")

    return "".join(reversed(chars))


def new_ulid() -> str:
    """Generate a new ULID string."""
    timestamp_ms = int(time.time() * 1000)
    time_part = _encode_crockford_base32(timestamp_ms, 10)

    randomness = int.from_bytes(os.urandom(10), "big")  # 80 bits
    rand_part = _encode_crockford_base32(randomness, 16)

    return f"{time_part}{rand_part}"


def is_ulid(value: str) -> bool:
    """Return True if the given string looks like a ULID."""
    if not isinstance(value, str) or len(value) != 26:
        return False
    return all(ch in _CROCKFORD_BASE32_ALPHABET for ch in value)
