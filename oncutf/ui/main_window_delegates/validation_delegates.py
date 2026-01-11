"""Validation operation delegates for MainWindow.

Author: Michael Economou
Date: 2026-01-10
"""


class ValidationDelegates:
    """Delegate class for validation operations.

    All methods delegate to app_service or validation managers.
    """

    def confirm_large_folder(self, file_list: list[str], folder_path: str) -> bool:
        """Confirm large folder via FileValidationManager and DialogManager."""
        return self.app_service.confirm_large_folder(file_list, folder_path)

    def check_large_files(self, files: list) -> list:
        """Check large files via FileValidationManager and DialogManager."""
        return self.app_service.check_large_files(files)

    def confirm_large_files(self, files: list) -> bool:
        """Confirm large files via FileValidationManager and DialogManager."""
        return self.app_service.confirm_large_files(files)

    def prompt_file_conflict(self, target_path: str) -> str:
        """Prompt file conflict via Application Service."""
        return self.app_service.prompt_file_conflict(target_path)

    def validate_operation_for_user(self, files: list[str], operation_type: str) -> dict:
        """Validate operation for user via Application Service."""
        return self.app_service.validate_operation_for_user(files, operation_type)

    def identify_moved_files(self, file_paths: list[str]) -> dict:
        """Identify moved files via FileValidationManager."""
        return self.app_service.identify_moved_files(file_paths)
