#!/usr/bin/env python3
"""
Module: metadata_module.py

Author: Michael Economou
Date: 2025-05-01

This module provides metadata extraction and formatting utilities for the oncutf application.
It includes functions to extract and format metadata from media files, with a focus on
image and video files. The module also provides date and time formatting utilities for
consistency in file naming and logging.

Functions:
    extract_metadata: Extract metadata from a media file.
    format_metadata_for_filename: Format metadata for use in file names.
    format_datetime_for_metadata: Canonical formatting for date/time used by the library/tests.
"""

from datetime import datetime, timezone, timedelta
from .metadata import datetime_to_filename  # reuse the canonical formatter

# Find all strftime calls and update them to use underscores for time separators
# Example patterns to replace:
# "%Y-%m-%d_%H-%M-%S" → "%Y-%m-%d_%H_%M_%S"
# "%Y_%m_%d_%H_%M_%S" → keep as is
# Any timezone offset formatting: replace ":" with "_"

# The exact changes depend on the current code.
# Post the current metadata_module.py file so I can provide exact replacements.

def format_datetime_for_metadata(dt_or_str) -> str:
	"""
	Canonical formatting used by the library/tests:
	- date part keeps dashes as in YYYY-MM-DD
	- time parts use underscores: HH_MM_SS
	- timezone offsets use underscores: +03_00
	"""
	# If already a datetime, delegate
	if isinstance(dt_or_str, datetime):
		return datetime_to_filename(dt_or_str)

	# If it's a date/time string that we parse, normalize and then format
	# ...existing parsing code...
	try:
		# attempt common ISO parse first
		dt = datetime.fromisoformat(dt_or_str)
		return datetime_to_filename(dt)
	except Exception:
		# last resort: try to parse known formats, then convert using datetime_to_filename
		# ...existing parsing alternatives...
		# Example fallback: keep date part but ensure time separators are underscores
		parts = dt_or_str.split("+")
		main = parts[0].replace(":", "_").replace("-", "-")  # keep date dashes
		main = main.replace(" ", "_").replace("T", "_")
		if len(parts) > 1:
			tz = parts[1].replace(":", "_").replace("-", "_")
			return f"{main}+{tz}"
		return main

# ...existing code...
