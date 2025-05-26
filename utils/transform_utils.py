"""
transform_utils.py

Author: Michael Economou
Date: 2025-05-18

Utility functions for applying text transformations to filenames,
including Greeklish transliteration, case formatting, and separators.
"""

import re
import unicodedata

# Base Greeklish mapping (letters only)
GREEKLISH_MAP = {
    'α': 'a', 'β': 'v', 'γ': 'g', 'δ': 'd', 'ε': 'e', 'ζ': 'z',
    'η': 'i', 'θ': 'th', 'ι': 'i', 'κ': 'k', 'λ': 'l', 'μ': 'm',
    'ν': 'n', 'ξ': 'x', 'ο': 'o', 'π': 'p', 'ρ': 'r', 'σ': 's',
    'ς': 's', 'τ': 't', 'υ': 'y', 'φ': 'f', 'χ': 'ch', 'ψ': 'ps', 'ω': 'w',
    'Α': 'A', 'Β': 'V', 'Γ': 'G', 'Δ': 'D', 'Ε': 'E', 'Ζ': 'Z',
    'Η': 'I', 'Θ': 'TH', 'Ι': 'I', 'Κ': 'K', 'Λ': 'L', 'Μ': 'M',
    'Ν': 'N', 'Ξ': 'X', 'Ο': 'O', 'Π': 'P', 'Ρ': 'R', 'Σ': 'S',
    'Τ': 'T', 'Υ': 'Y', 'Φ': 'F', 'Χ': 'CH', 'Ψ': 'PS', 'Ω': 'W'
}

# Diphthongs mapping (used before letter-level map)
DIPHTHONGS = {
    'μπ': 'b', 'Μπ': 'B', 'ΜΠ': 'B',
    'ντ': 'd', 'Ντ': 'D', 'ΝΤ': 'D',
    'γκ': 'g', 'Γκ': 'G', 'ΓΚ': 'G',
    'γγ': 'g', 'Γγ': 'G', 'ΓΓ': 'G'
}

def strip_accents(text: str) -> str:
    """Remove accents from Greek characters using Unicode normalization."""
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')

def safe_upper(text: str) -> str:
    """
    Convert Greek text to uppercase.
    If the first letter is a stressed vowel, preserve the accent.
    All other accents are removed.
    """
    if not text:
        return text

    initial_tonos_map = {
        'ά': 'Ά', 'έ': 'Έ', 'ή': 'Ή', 'ί': 'Ί', 'ό': 'Ό', 'ύ': 'Ύ', 'ώ': 'Ώ',
        'Ά': 'Ά', 'Έ': 'Έ', 'Ή': 'Ή', 'Ί': 'Ί', 'Ό': 'Ό', 'Ύ': 'Ύ', 'Ώ': 'Ώ',
    }

    first = text[0]
    rest = text[1:]

    if first in initial_tonos_map:
        first = initial_tonos_map[first]
    else:
        first = strip_accents(first).upper()

    return first + strip_accents(rest).upper()

def to_greeklish(text: str) -> str:
    """Convert Greek text to Greeklish (Latinized)."""
    text = strip_accents(text)
    for gr, gl in DIPHTHONGS.items():
        text = text.replace(gr, gl)
    return ''.join(GREEKLISH_MAP.get(c, c) for c in text)

def apply_transform(name: str, transform: str) -> str:
    """
    Apply string transformation to a name.

    Args:
        name (str): Input name (base filename, no extension)
        transform (str): One of 'original', 'lower', 'UPPER',
                         'snake_case', 'kebab-case', 'space', 'greeklish'

    Returns:
        str: Transformed name
    """
    if not name.strip():
        return ''

    if transform == "original":
        return name

    if transform == "lower":
        return name.lower()

    if transform == "UPPER":
        return safe_upper(name)

    if transform == "capitalize":
        return ' '.join(w.capitalize() for w in name.split())

    if transform == "snake_case":
        name = re.sub(r"[^\w\s_-]", "", name, flags=re.UNICODE)
        name = re.sub(r"[\s\-]+", "_", name)
        return name.strip("_")

    if transform == "kebab-case":
        name = re.sub(r"[^\w\s_-]", "", name, flags=re.UNICODE)
        name = re.sub(r"[\s_]+", "-", name)
        return name.strip("-")

    if transform == "space":
        # Replace underscores and dashes with space
        return re.sub(r"[_\-]+", " ", name)

    if transform == "greeklish":
        return to_greeklish(name)

    return name
