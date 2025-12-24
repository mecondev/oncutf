"""
Module: status_manager.py

Author: Michael Economou
Date: 2025-05-31

status_manager.py
Enhanced Status Manager for OnCutF Application
Manages status bar updates and UI feedback with specialized methods for different operations,
progress integration, status history tracking, and smart context awareness.
Key Features:
- Specialized status methods for different operation types
- Progress dialog integration and coordination
- Status history tracking for debugging
- Bulk operation status management
- Smart context awareness for better user feedback
- Automatic status categorization and prioritization
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from oncutf.config import STATUS_COLORS
from oncutf.core.pyqt_imports import QTimer
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class StatusPriority(Enum):
    """Priority levels for status messages."""

    LOW = 1  # General info, auto-reset quickly
    NORMAL = 2  # Standard operations
    HIGH = 3  # Important operations, user actions
    CRITICAL = 4  # Errors, warnings that need attention
    SYSTEM = 5  # System-level messages, always visible


class StatusCategory(Enum):
    """Categories of status messages for better organization."""

    GENERAL = "general"
    FILE_OPERATIONS = "file_ops"
    METADATA = "metadata"
    HASH = "hash"
    RENAME = "rename"
    SELECTION = "selection"
    VALIDATION = "validation"
    PROGRESS = "progress"
    SYSTEM = "system"


@dataclass
class StatusEntry:
    """Represents a status message with metadata."""

    message: str
    color: str
    category: StatusCategory
    priority: StatusPriority
    timestamp: datetime = field(default_factory=datetime.now)
    auto_reset: bool = False
    reset_delay: int = None  # Will be set from config if None
    operation_id: str | None = None  # For tracking related operations

    def __post_init__(self):
        """Initialize reset_delay from config if not provided."""
        if self.reset_delay is None:
            from oncutf.config import STATUS_AUTO_RESET_DELAY

            self.reset_delay = STATUS_AUTO_RESET_DELAY


class StatusManager:
    """Enhanced status manager with specialized methods and smart context awareness."""

    def __init__(self, status_label=None) -> None:
        """Initialize StatusManager with status label reference."""
        self.status_label = status_label
        self._status_timer: QTimer | None = None
        self._status_history: list[StatusEntry] = []
        self._max_history_size: int = 100
        self._current_operation: str | None = None
        self._operation_contexts: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

        logger.info("[StatusManager] Enhanced status manager initialized")

    # =====================================
    # Core Status Methods (Enhanced)
    # =====================================

    def set_status(
        self,
        text: str,
        color: str = "",
        auto_reset: bool = False,
        reset_delay: int = None,
        category: StatusCategory = StatusCategory.GENERAL,
        priority: StatusPriority = StatusPriority.NORMAL,
        operation_id: str | None = None,
    ) -> None:
        """
        Enhanced status setting with categorization and priority.

        Args:
            text: Status text to display
            color: Optional color (CSS color string)
            auto_reset: Whether to auto-reset to "Ready" after delay
            reset_delay: Delay in milliseconds before reset (uses config default if None)
            category: Category of the status message
            priority: Priority level of the message
            operation_id: Optional operation identifier for tracking
        """
        if not self.status_label:
            logger.warning("[StatusManager] No status label set")
            return

        # Create status entry for history
        status_entry = StatusEntry(
            message=text,
            color=color,
            category=category,
            priority=priority,
            auto_reset=auto_reset,
            reset_delay=reset_delay,
            operation_id=operation_id or self._current_operation,
        )

        # Add to history
        self._add_to_history(status_entry)

        # Set text and color
        self.status_label.setText(text)
        if color:
            self.status_label.setStyleSheet(f"color: {color};")
        else:
            self.status_label.setStyleSheet("")

        # Handle auto-reset
        if auto_reset:
            self._start_auto_reset(reset_delay)

        # Log based on priority
        if priority.value >= StatusPriority.HIGH.value or text != "Ready":
            log_level = "warning" if priority == StatusPriority.CRITICAL else "info"
            getattr(logger, log_level)(
                f"[StatusManager] {category.value.upper()}: '{text}' "
                f"(priority: {priority.name}, auto_reset: {auto_reset})"
            )

    def set_ready(self) -> None:
        """Clear status bar to show clean empty state instead of 'Ready'."""
        if self.status_label and self.status_label.text() == "":
            return
        self.set_status(
            "",  # Empty string instead of "Ready"
            color=STATUS_COLORS["ready"],
            auto_reset=False,
            category=StatusCategory.GENERAL,
            priority=StatusPriority.LOW,
        )

    # =====================================
    # Specialized Status Methods
    # =====================================

    def set_file_operation_status(
        self,
        message: str,
        success: bool = True,
        auto_reset: bool = True,
        operation_id: str | None = None,
    ) -> None:
        """Set status for file operations (load, save, rename, etc.)."""
        color = STATUS_COLORS["operation_success"] if success else STATUS_COLORS["error"]
        priority = StatusPriority.HIGH if not success else StatusPriority.NORMAL

        self.set_status(
            message,
            color=color,
            auto_reset=auto_reset,
            category=StatusCategory.FILE_OPERATIONS,
            priority=priority,
            operation_id=operation_id,
        )

    def set_metadata_status(
        self,
        message: str,
        operation_type: str = "basic",
        file_count: int = 0,
        auto_reset: bool = True,
    ) -> None:
        """Set status for metadata operations with smart formatting."""
        # Determine color based on operation type
        color_map = {
            "basic": STATUS_COLORS["metadata_basic"],
            "extended": STATUS_COLORS["metadata_extended"],
            "skipped": STATUS_COLORS["metadata_skipped"],
            "success": STATUS_COLORS["metadata_success"],
            "error": STATUS_COLORS["error"],
        }

        color = color_map.get(operation_type, STATUS_COLORS["info"])

        # Smart message formatting
        if file_count > 0 and not message.startswith("Loaded"):
            if operation_type == "skipped":
                formatted_message = f"{message} — {file_count} files (metadata skipped)"
            elif operation_type == "extended":
                formatted_message = f"{message} — {file_count} files (extended metadata)"
            else:
                formatted_message = f"{message} — {file_count} files (basic metadata)"
        else:
            formatted_message = message

        self.set_status(
            formatted_message,
            color=color,
            auto_reset=auto_reset,
            category=StatusCategory.METADATA,
            priority=StatusPriority.NORMAL,
        )

    def set_hash_status(
        self,
        message: str,
        file_count: int = 0,
        operation_type: str = "calculation",
        auto_reset: bool = True,
    ) -> None:
        """Set status for hash operations with progress context."""
        color_map = {
            "calculation": STATUS_COLORS["info"],
            "success": STATUS_COLORS["hash_success"],
            "duplicate_found": STATUS_COLORS["duplicate_found"],
            "no_duplicates": STATUS_COLORS["operation_success"],
            "error": STATUS_COLORS["error"],
        }

        color = color_map.get(operation_type, STATUS_COLORS["info"])

        # Smart message formatting for hash operations
        if file_count > 0 and "files" not in message:
            formatted_message = f"{message} ({file_count} files)"
        else:
            formatted_message = message

        self.set_status(
            formatted_message,
            color=color,
            auto_reset=auto_reset,
            category=StatusCategory.HASH,
            priority=StatusPriority.NORMAL,
        )

    def set_rename_status(
        self, message: str, renamed_count: int = 0, success: bool = True, auto_reset: bool = True
    ) -> None:
        """Set status for rename operations with count information."""
        if success:
            color = STATUS_COLORS["rename_success"]
            formatted_message = f"Renamed {renamed_count} file(s)" if renamed_count > 0 else message
        else:
            color = STATUS_COLORS["error"]
            formatted_message = f"Rename failed: {message}"

        self.set_status(
            formatted_message,
            color=color,
            auto_reset=auto_reset,
            category=StatusCategory.RENAME,
            priority=StatusPriority.HIGH if not success else StatusPriority.NORMAL,
        )

    def set_selection_status(
        self, message: str, selected_count: int = 0, total_count: int = 0, auto_reset: bool = True
    ) -> None:
        """Set status for selection operations with count information."""
        if selected_count == 0 and "No" not in message:
            color = STATUS_COLORS["no_action"]
            formatted_message = f"No files to {message.lower()}"
        elif total_count > 0:
            color = STATUS_COLORS["operation_success"]
            formatted_message = f"{message} ({selected_count}/{total_count} files)"
        else:
            color = STATUS_COLORS["neutral_info"]
            formatted_message = message

        self.set_status(
            formatted_message,
            color=color,
            auto_reset=auto_reset,
            category=StatusCategory.SELECTION,
            priority=StatusPriority.LOW,
        )

    def set_validation_status(
        self, message: str, validation_type: str = "info", auto_reset: bool = True
    ) -> None:
        """Set status for validation operations."""
        color_map = {
            "info": STATUS_COLORS["info"],
            "warning": STATUS_COLORS["warning"],
            "error": STATUS_COLORS["error"],
            "success": STATUS_COLORS["operation_success"],
        }

        priority_map = {
            "info": StatusPriority.LOW,
            "warning": StatusPriority.HIGH,
            "error": StatusPriority.CRITICAL,
            "success": StatusPriority.NORMAL,
        }

        self.set_status(
            message,
            color=color_map.get(validation_type, STATUS_COLORS["info"]),
            auto_reset=auto_reset,
            category=StatusCategory.VALIDATION,
            priority=priority_map.get(validation_type, StatusPriority.NORMAL),
        )

    def set_progress_status(
        self, message: str, progress_percent: int = 0, operation_id: str | None = None
    ) -> None:
        """Set status for progress operations with percentage."""
        if 0 < progress_percent < 100:
            formatted_message = f"{message} ({progress_percent}%)"
        else:
            formatted_message = message

        self.set_status(
            formatted_message,
            color=STATUS_COLORS["info"],
            auto_reset=False,
            category=StatusCategory.PROGRESS,
            priority=StatusPriority.NORMAL,
            operation_id=operation_id,
        )

    # =====================================
    # Operation Context Management
    # =====================================

    def start_operation(
        self, operation_id: str, operation_type: str, description: str = ""
    ) -> None:
        """Start tracking a new operation context."""
        with self._lock:
            self._current_operation = operation_id
            self._operation_contexts[operation_id] = {
                "type": operation_type,
                "description": description,
                "start_time": datetime.now(),
                "status_count": 0,
                "last_update": datetime.now(),
            }

        logger.debug("[StatusManager] Started operation: %s (%s)", operation_id, operation_type)

    def update_operation(self, operation_id: str, **kwargs) -> None:
        """Update operation context with additional information."""
        with self._lock:
            if operation_id in self._operation_contexts:
                self._operation_contexts[operation_id].update(kwargs)
                self._operation_contexts[operation_id]["last_update"] = datetime.now()

    def finish_operation(
        self, operation_id: str, success: bool = True, final_message: str = ""
    ) -> None:
        """Finish an operation and clean up context."""
        # First, prepare the status data without holding the lock
        status_data = None

        with self._lock:
            if operation_id in self._operation_contexts:
                context = self._operation_contexts[operation_id]
                duration = (datetime.now() - context["start_time"]).total_seconds()

                if final_message:
                    category_map = {
                        "metadata": StatusCategory.METADATA,
                        "hash": StatusCategory.HASH,
                        "rename": StatusCategory.RENAME,
                        "file": StatusCategory.FILE_OPERATIONS,
                    }

                    category = category_map.get(context["type"], StatusCategory.GENERAL)

                    # Prepare status data to call set_status outside the lock
                    status_data = {
                        "message": final_message,
                        "color": (
                            STATUS_COLORS["operation_success"]
                            if success
                            else STATUS_COLORS["error"]
                        ),
                        "auto_reset": True,
                        "category": category,
                        "priority": StatusPriority.HIGH if not success else StatusPriority.NORMAL,
                        "operation_id": operation_id,
                    }

                logger.info(
                    "[StatusManager] Finished operation: %s (duration: %.1fs, success: %s)",
                    operation_id,
                    duration,
                    success,
                )

                # Clean up old operation context
                del self._operation_contexts[operation_id]

                if self._current_operation == operation_id:
                    self._current_operation = None

        # Call set_status outside the lock to avoid deadlock
        if status_data:
            self.set_status(
                status_data["message"],
                color=status_data["color"],
                auto_reset=status_data["auto_reset"],
                category=status_data["category"],
                priority=status_data["priority"],
                operation_id=status_data["operation_id"],
            )

    # =====================================
    # Bulk Operations Support
    # =====================================

    def set_bulk_operation_status(
        self,
        operation_type: str,
        processed: int,
        total: int,
        current_item: str = "",
        operation_id: str | None = None,
    ) -> None:
        """Set status for bulk operations with progress tracking."""
        progress_percent = int((processed / total) * 100) if total > 0 else 0

        if current_item:
            message = f"{operation_type} {current_item} ({processed}/{total})"
        else:
            message = f"{operation_type} ({processed}/{total})"

        self.set_progress_status(message, progress_percent, operation_id)

    def set_batch_completion_status(
        self, operation_type: str, _total_processed: int, successful: int, failed: int = 0
    ) -> None:
        """Set status for completed batch operations with summary."""
        if failed == 0:
            message = f"{operation_type} completed: {successful} files processed"
            color = STATUS_COLORS["operation_success"]
        else:
            message = f"{operation_type} completed: {successful} successful, {failed} failed"
            color = STATUS_COLORS["warning"]

        category_map = {
            "Metadata loading": StatusCategory.METADATA,
            "Hash calculation": StatusCategory.HASH,
            "File rename": StatusCategory.RENAME,
            "File validation": StatusCategory.VALIDATION,
        }

        category = category_map.get(operation_type, StatusCategory.FILE_OPERATIONS)

        self.set_status(
            message,
            color=color,
            auto_reset=True,
            category=category,
            priority=StatusPriority.HIGH if failed > 0 else StatusPriority.NORMAL,
        )

    # =====================================
    # Legacy Compatibility Methods
    # =====================================

    def set_error(self, message: str, auto_reset: bool = True) -> None:
        """Set error status with red color."""
        self.set_status(
            message,
            color=STATUS_COLORS["error"],
            auto_reset=auto_reset,
            category=StatusCategory.SYSTEM,
            priority=StatusPriority.CRITICAL,
        )

    def set_success(self, message: str, auto_reset: bool = True) -> None:
        """Set success status with green color."""
        self.set_status(
            message,
            color=STATUS_COLORS["success"],
            auto_reset=auto_reset,
            category=StatusCategory.GENERAL,
            priority=StatusPriority.NORMAL,
        )

    def set_warning(self, message: str, auto_reset: bool = True) -> None:
        """Set warning status with orange color."""
        self.set_status(
            message,
            color=STATUS_COLORS["warning"],
            auto_reset=auto_reset,
            category=StatusCategory.SYSTEM,
            priority=StatusPriority.HIGH,
        )

    def set_info(self, message: str, auto_reset: bool = True) -> None:
        """Set info status with blue color."""
        self.set_status(
            message,
            color=STATUS_COLORS["info"],
            auto_reset=auto_reset,
            category=StatusCategory.GENERAL,
            priority=StatusPriority.LOW,
        )

    def set_loading(self, message: str = "Loading...") -> None:
        """Set loading status with gray color."""
        self.set_status(
            message,
            color=STATUS_COLORS["loading"],
            auto_reset=False,
            category=StatusCategory.PROGRESS,
            priority=StatusPriority.NORMAL,
        )

    # =====================================
    # Files Label Management (Enhanced)
    # =====================================

    def update_files_label(self, files_label, total_files: int, selected_files: int) -> None:
        """Enhanced files count label update with smart formatting."""
        if not files_label:
            return

        if total_files == 0:
            files_label.setText("Files (0)")
        # Smart formatting based on selection
        elif selected_files == 0:
            files_label.setText(f"Files ({total_files} loaded)")
        elif selected_files == total_files:
            files_label.setText(f"Files ({total_files} all selected)")
        else:
            files_label.setText(f"Files ({total_files} loaded, {selected_files} selected)")

        # Also update status if significant selection change
        if selected_files > 0:
            selection_percent = int((selected_files / total_files) * 100) if total_files > 0 else 0
            if selection_percent in [25, 50, 75, 100]:  # Milestone percentages
                self.set_selection_status(
                    f"Selected {selection_percent}% of files",
                    selected_files,
                    total_files,
                    auto_reset=True,
                )

        logger.debug(
            "[StatusManager] Files label updated: %d total, %d selected",
            total_files,
            selected_files,
            extra={"dev_only": True},
        )

    def clear_file_table_status(self, files_label, message: str = "No folder selected") -> None:
        """Enhanced file table clear status with context."""
        if files_label:
            files_label.setText("Files (0)")

        self.set_status(
            message,
            color=STATUS_COLORS["loading"],
            auto_reset=False,
            category=StatusCategory.FILE_OPERATIONS,
            priority=StatusPriority.LOW,
        )

    def show_metadata_status(self, num_files: int, force_extended_metadata: bool) -> None:
        """Enhanced metadata status with operation tracking."""
        operation_type = "extended" if force_extended_metadata else "basic"

        self.set_metadata_status(
            f"Loaded {num_files} files",
            operation_type=operation_type,
            file_count=num_files,
            auto_reset=True,
        )

    def update_status_from_preview(self, status_html: str) -> None:
        """Enhanced preview status update with HTML handling."""
        if not self.status_label:
            return

        # Clean HTML for logging
        import re

        clean_text = re.sub("<[^<]+?>", "", status_html)

        self.status_label.setText(status_html)

        # Add to history as preview category
        self._add_to_history(
            StatusEntry(
                message=clean_text,
                color="",
                category=StatusCategory.PROGRESS,
                priority=StatusPriority.LOW,
                operation_id=self._current_operation,
            )
        )

        logger.debug(
            "[StatusManager] Preview status: %s...",
            clean_text[:50],
            extra={"dev_only": True},
        )

    # =====================================
    # Status History and Analytics
    # =====================================

    def _add_to_history(self, status_entry: StatusEntry) -> None:
        """Add status entry to history with size management."""
        with self._lock:
            self._status_history.append(status_entry)

            # Trim history if too large
            if len(self._status_history) > self._max_history_size:
                self._status_history = self._status_history[-self._max_history_size :]

    def get_status_history(
        self, category: StatusCategory | None = None, limit: int = 20
    ) -> list[StatusEntry]:
        """Get recent status history, optionally filtered by category."""
        with self._lock:
            history = self._status_history.copy()

        if category:
            history = [entry for entry in history if entry.category == category]

        return history[-limit:]

    def get_operation_summary(self, operation_id: str) -> dict[str, Any] | None:
        """Get summary of a specific operation."""
        with self._lock:
            if operation_id in self._operation_contexts:
                context = self._operation_contexts[operation_id].copy()

                # Add status history for this operation
                operation_statuses = [
                    entry for entry in self._status_history if entry.operation_id == operation_id
                ]
                context["status_history"] = operation_statuses
                context["status_count"] = len(operation_statuses)

                return context

        return None

    def clear_status_history(self) -> None:
        """Clear status history (useful for debugging)."""
        with self._lock:
            self._status_history.clear()
        logger.debug("[StatusManager] Status history cleared")

    # =====================================
    # Timer Management (Enhanced)
    # =====================================

    def _start_auto_reset(self, delay: int) -> None:
        """Enhanced auto-reset timer with better cleanup."""  # If delay is None or invalid, don't start timer
        if delay is None or delay <= 0:
            return
            # Stop existing timer if running
        if self._status_timer:
            self._status_timer.stop()
            self._status_timer.deleteLater()
            self._status_timer = None

        # Create new timer
        self._status_timer = QTimer()
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self.set_ready)
        self._status_timer.start(delay)

    def stop_auto_reset(self) -> None:
        """Stop any running auto-reset timer."""
        if self._status_timer:
            self._status_timer.stop()
            self._status_timer.deleteLater()
            self._status_timer = None

    def cleanup(self) -> None:
        """Cleanup resources when shutting down."""
        self.stop_auto_reset()
        with self._lock:
            self._operation_contexts.clear()
            self._status_history.clear()
        logger.debug("[StatusManager] Cleanup completed")
