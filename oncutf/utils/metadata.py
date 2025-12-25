#!/usr/bin/env python3
"""Module: metadata.py

Author: Michael Economou
Date: 2025-05-01

This module provides utilities for handling metadata, including functions to
format datetime objects as filename-safe strings and to normalize timezone offsets.

Functions:
    datetime_to_filename: Convert a datetime to a filename-safe string.
    _format_tz_offset_for_filename: Format a timezone offset timedelta as +HH_MM or -HH_MM.
"""

from datetime import datetime, timedelta


def _format_tz_offset_for_filename(offset: timedelta | None) -> str:
    """Format a timezone offset timedelta as +HH_MM or -HH_MM for filenames."""
    if offset is None:
        return ""
    total_seconds = int(offset.total_seconds())
    sign = "+" if total_seconds >= 0 else "-"
    total_seconds = abs(total_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    return f"{sign}{hours:02d}_{minutes:02d}"


def datetime_to_filename(dt: datetime | None) -> str:
    """Convert a datetime to a filename-safe string using underscores for time separators.
    Format: 2024-05-12_14_23_10 (with tz: +2024-05-12_14_23_10+03_00)
    """
    if dt is None:
        return ""
    # Date part keeps dashes; time parts use underscores
    base = dt.strftime("%Y-%m-%d_%H_%M_%S")
    if dt.tzinfo is not None:
        offset = dt.utcoffset()
        if offset is not None:
            return base + _format_tz_offset_for_filename(offset)
    return base
