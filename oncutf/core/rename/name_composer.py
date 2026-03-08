"""oncutf.core.rename.name_composer.

Stateless name composition logic extracted from ``UnifiedPreviewManager``.

``NameComposer`` applies configured rename modules to a single file and
produces the final filename.  It uses the centralised
:data:`~oncutf.core.rename.module_registry.MODULE_TYPE_MAP` so that
module type resolution is consistent project-wide.

Author: Michael Economou
Date: 2026-03-08
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem

from oncutf.core.rename.module_registry import get_logic_class
from oncutf.models.counter_scope import CounterScope
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class NameComposer:
    """Compose new filenames by applying rename modules in sequence.

    This class is stateless -- all required data is passed via method
    arguments.  It replaces the ``_apply_rename_modules`` / helpers that
    previously lived inside ``UnifiedPreviewManager``.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compose_name(
        self,
        modules_data: list[dict[str, Any]],
        index: int,
        file_item: FileItem,
        metadata_cache: dict[str, Any] | None = None,
        all_files: list[FileItem] | None = None,
    ) -> str:
        """Apply rename modules and return the new basename (no extension).

        Args:
            modules_data: Ordered list of module configuration dicts.
            index: Global index of *file_item* in the file list.
            file_item: The file being renamed.
            metadata_cache: Optional metadata cache used by modules.
            all_files: Full list of files (needed for scope-aware counters).

        Returns:
            Concatenated name parts produced by each module.

        """
        file_path_obj = Path(file_item.filename)
        original_base_name = file_path_obj.stem
        new_name_parts: list[str] = []

        for data in modules_data:
            module_type = data.get("type")
            part = self._apply_single_module(
                module_type,
                data,
                file_item,
                index,
                original_base_name,
                metadata_cache,
                all_files,
            )
            new_name_parts.append(part)

        return "".join(new_name_parts)

    def compose_name_with_context(
        self,
        file: FileItem,
        modules_data: list[dict[str, Any]],
        index: int,
        metadata_cache: Any,
        hash_availability: dict[str, bool],
        metadata_availability: dict[str, bool],
        all_files: list[FileItem] | None = None,
    ) -> str:
        """Apply rename modules for a single file, checking required data.

        Modules that depend on hash or metadata availability will be
        short-circuited and a sentinel string (e.g. ``"missing_hash"``)
        returned when preconditions are not met.
        """
        for module_data in modules_data:
            if module_data.get("type") == "metadata":
                category = module_data.get("category")
                if category == "tag":
                    if not hash_availability.get(file.full_path, False):
                        return "missing_hash"
                elif category == "metadata_keys" and not metadata_availability.get(
                    file.full_path, False
                ):
                    return "missing_metadata"

        return self.compose_name(modules_data, index, file, metadata_cache, all_files)

    # ------------------------------------------------------------------
    # Filename helpers (pure functions, kept as methods for grouping)
    # ------------------------------------------------------------------

    @staticmethod
    def strip_extension(fullname: str, extension: str) -> str:
        """Strip *extension* from *fullname* if present."""
        if extension and fullname.lower().endswith(extension.lower()):
            return fullname[: -(len(extension))]
        return fullname

    @staticmethod
    def apply_post_transform(
        basename: str, post_transform: dict[str, Any], has_transform: bool
    ) -> str:
        """Apply post-transform to *basename* when active."""
        if not has_transform:
            return basename
        from oncutf.modules.name_transform_module import NameTransformModule

        return NameTransformModule.apply_from_data(post_transform, basename)

    @staticmethod
    def build_final_filename(basename: str, extension: str) -> str:
        """Build final filename from *basename* and *extension*."""
        return f"{basename}{extension}" if extension else basename

    @staticmethod
    def is_valid_filename_text(basename: str) -> bool:
        """Return ``True`` if *basename* is acceptable for a filename."""
        try:
            from oncutf.utils.naming.validate_filename_text import (
                is_valid_filename_text,
            )

            return is_valid_filename_text(basename)
        except ImportError:
            return True

    # ------------------------------------------------------------------
    # Scope-aware counter index
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_scope_aware_index(
        scope: str,
        global_index: int,
        file_item: FileItem,
        all_files: list[FileItem] | None = None,
    ) -> int:
        """Calculate the counter index adjusted for *scope*.

        Args:
            scope: One of ``'global'``, ``'per_folder'``,
                ``'per_extension'``, ``'per_filegroup'``.
            global_index: Index in the full file list.
            file_item: Current file being processed.
            all_files: Full list of files.

        Returns:
            The scope-adjusted index.

        """
        try:
            scope_enum = CounterScope(scope)
        except ValueError:
            logger.warning("[NameComposer] Unknown counter scope: %s, using GLOBAL", scope)
            return global_index

        if scope_enum == CounterScope.GLOBAL:
            return global_index

        if scope_enum == CounterScope.PER_FOLDER:
            if not all_files or not file_item:
                return global_index
            current_folder = str(Path(file_item.full_path).parent)
            folder_index = 0
            for i, f in enumerate(all_files):
                if i >= global_index:
                    break
                if str(Path(f.full_path).parent) == current_folder:
                    folder_index += 1
            return folder_index

        if scope_enum == CounterScope.PER_EXTENSION:
            if not all_files or not file_item:
                return global_index
            current_ext = Path(file_item.filename).suffix.lower()
            ext_index = 0
            for i, f in enumerate(all_files):
                if i >= global_index:
                    break
                if Path(f.filename).suffix.lower() == current_ext:
                    ext_index += 1
            return ext_index

        # CounterScope.PER_FILEGROUP
        if not all_files or not file_item:
            return global_index
        from oncutf.utils.filesystem.file_grouper import (
            calculate_filegroup_counter_index,
        )

        try:
            return calculate_filegroup_counter_index(
                file_item, all_files, global_index, groups=None
            )
        except Exception as e:
            logger.warning("[NameComposer] Error calculating filegroup index: %s", e)
            return global_index

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _apply_single_module(
        self,
        module_type: str | None,
        data: dict[str, Any],
        file_item: FileItem,
        index: int,
        original_base_name: str,
        metadata_cache: dict[str, Any] | None,
        all_files: list[FileItem] | None,
    ) -> str:
        """Dispatch a single module and return its name fragment."""
        logic_class = get_logic_class(module_type) if module_type else None

        if module_type == "counter" and logic_class is not None:
            scope = data.get("scope", CounterScope.PER_FOLDER.value)
            counter_index = self.calculate_scope_aware_index(scope, index, file_item, all_files)
            result: str = logic_class.apply_from_data(
                data, file_item, counter_index, metadata_cache
            )
            return result

        if module_type == "original_name":
            return original_base_name or "originalname"

        if module_type == "remove_text_from_original_name" and logic_class is not None:
            result_filename: str = logic_class.apply_from_data(
                data, file_item, index, metadata_cache
            )
            return Path(result_filename).stem

        if logic_class is not None:
            result_str: str = logic_class.apply_from_data(data, file_item, index, metadata_cache)
            return result_str

        return ""
