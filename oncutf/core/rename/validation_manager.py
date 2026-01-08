"""oncutf.core.rename.validation_manager

Validation management for the unified rename engine.

This module provides the UnifiedValidationManager class that validates
preview results and detects duplicates.

Author: Michael Economou
Date: 2026-01-01
"""

import os

from oncutf.core.rename.data_classes import ValidationItem, ValidationResult
from oncutf.core.rename.query_managers import SmartCacheManager
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class UnifiedValidationManager:
    """Validate preview results and detect duplicates.

    The class produces a :class:`ValidationResult` that contains per-file
    validation results and a set of duplicated target filenames.
    """

    def __init__(self, cache_manager: SmartCacheManager):
        """Initialize the validation manager with a smart cache manager."""
        self.cache_manager = cache_manager

    def validate_preview(self, preview_pairs: list[tuple[str, str]]) -> ValidationResult:
        """Validate a sequence of (old_name, new_name) pairs.

        Performs filename validation, duplicate detection and returns a
        :class:`ValidationResult` containing the findings.
        """
        # Generate cache key
        cache_key = self._generate_validation_cache_key(preview_pairs)

        # Check cache first
        cached_result = self.cache_manager.get_cached_validation(cache_key)
        if cached_result:
            logger.debug("[UnifiedValidationManager] Using cached validation")
            return cached_result

        results = []
        duplicates: set[str] = set()
        seen_names: set[str] = set()

        for old_name, new_name in preview_pairs:
            # Filename validation
            is_valid, error = self._validate_filename(new_name)

            # Duplicate detection
            is_duplicate = new_name in seen_names
            if is_duplicate:
                duplicates.add(new_name)
            else:
                seen_names.add(new_name)

            # No change detection
            is_unchanged = old_name == new_name

            results.append(
                ValidationItem(
                    old_name=old_name,
                    new_name=new_name,
                    is_valid=is_valid,
                    is_duplicate=is_duplicate,
                    is_unchanged=is_unchanged,
                    error_message=error,
                )
            )

        result = ValidationResult(results, duplicates)

        # Cache result
        self.cache_manager.cache_validation(cache_key, result)

        return result

    def _generate_validation_cache_key(self, preview_pairs: list[tuple[str, str]]) -> str:
        """Generate cache key for validation results."""
        return str(hash(tuple(preview_pairs)))

    def _validate_filename(self, filename: str) -> tuple[bool, str]:
        """Validate `filename` and return (is_valid, error_message).

        The implementation delegates to :mod:`utils.filename_validator`.
        """
        try:
            from oncutf.utils.naming.filename_validator import validate_filename_part

            basename = os.path.splitext(filename)[0]
            is_valid, error = validate_filename_part(basename)
            return is_valid, error or ""
        except Exception as e:
            return False, f"Validation error: {e}"
