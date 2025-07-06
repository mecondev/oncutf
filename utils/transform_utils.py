"""
Module: transform_utils.py

Author: Michael Economou
Date: 2025-05-31

transform_utils.py
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
        transform (str): One of 'original', 'lower', 'UPPER', 'Capitalize',
                         'camelCase', 'PascalCase', 'Title Case',
                         'snake_case', 'kebab-case', 'space', 'greeklish'

    Returns:
        str: Transformed name
    """
    if not name.strip():
        return ''

    if transform == "original":
        # Remove leading/trailing spaces, preserve everything else
        return name.strip()

    if transform == "lower":
        return name.lower()

    if transform == "UPPER":
        return safe_upper(name)

    if transform == "Capitalize":
        return ' '.join(w.capitalize() for w in name.split())

    if transform == "camelCase":
        words = name.split()
        if not words:
            return ''
        # First word lowercase, rest capitalized
        return words[0].lower() + ''.join(w.capitalize() for w in words[1:])

    if transform == "PascalCase":
        words = name.split()
        if not words:
            return ''
        # All words capitalized, no spaces
        return ''.join(w.capitalize() for w in words)

    if transform == "Title Case":
        # Similar to Capitalize but handles articles/prepositions better
        return name.title()

    if transform in ("snake_case", "kebab-case"):
        # Correct 3-step process:
        # Step 1: Convert ALL spaces to separators (including leading/trailing)
        # Step 2: Remove duplicate separators
        # Step 3: Strip any remaining leading/trailing spaces

        # Step 1: Convert all spaces to separators
        if transform == "snake_case":
            result = re.sub(r"\s+", "_", name)
        else:  # kebab-case
            result = re.sub(r"\s+", "-", name)

        # Step 2: Remove duplicate separators
        # Remove duplicate underscores and dashes
        result = re.sub(r"_+", "_", result)  # Multiple _ → single _
        result = re.sub(r"-+", "-", result)  # Multiple - → single -

        # Step 3: Strip any remaining leading/trailing spaces (shouldn't be any, but safety)
        result = result.strip()

        return result

    if transform == "space":
        # Find first and last non-space character
        m_first = re.search(r'[^\s]', name)
        if not m_first:
            return ''  # All spaces, return empty
        first = m_first.start()
        m_last = re.search(r'[^\s](?!.*[^\s])', name)
        if not m_last:
            return ''  # No valid content found
        last = m_last.start()

        # Extract leading/trailing separators and body content
        leading_part = name[:first]  # Only separators before first non-space
        trailing_part = name[last+1:]  # Only separators after last non-space
        body = name[first:last+1]  # Content without leading/trailing spaces

        # In leading/trailing: keep separators, remove spaces
        leading_result = re.sub(r'[_\-]+', ' ', leading_part).strip()
        trailing_result = re.sub(r'[_\-]+', ' ', trailing_part).strip()

        # In body: convert separators to spaces
        body_result = re.sub(r"[_\-]+", " ", body)

        # Combine
        result = f"{leading_result}{body_result}{trailing_result}".strip()
        return result

    if transform == "greeklish":
        return to_greeklish(name)

    return name
