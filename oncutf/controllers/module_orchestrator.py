"""Module: module_orchestrator.py

Author: Michael Economou
Date: 2025-12-27

Controller for rename module orchestration.
Separates module business logic from UI concerns to enable future node editor implementation.

Responsibilities:
- Module registry (available module types)
- Module instance management (current modules in pipeline)
- Data collection and serialization
- Validation
- Dynamic module discovery (Phase 3)
"""

import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Any

from oncutf.models.file_item import FileItem
from oncutf.modules.base_module import BaseRenameModule
from oncutf.modules.counter_module import CounterModule
from oncutf.modules.metadata_module import MetadataModule
from oncutf.modules.original_name_module import OriginalNameModule
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ModuleDescriptor:
    """Describes a module type and its metadata."""

    def __init__(
        self,
        name: str,
        display_name: str,
        module_class: type,
        ui_widget_class: type | None = None,
        ui_rows: int = 1,
        description: str = "",
    ):
        self.name = name  # Internal ID
        self.display_name = display_name  # UI label
        self.module_class = module_class  # Pure logic class
        self.ui_widget_class = ui_widget_class  # UI widget (can be None for pure modules)
        self.ui_rows = ui_rows  # Height hint for UI
        self.description = description


class ModuleOrchestrator:
    """Orchestrates rename modules without UI dependencies.
    
    This controller manages the module pipeline, providing clean separation
    between business logic and UI. Designed to work with both current widget-based
    UI and future node editor implementations.
    """

    def __init__(self):
        """Initialize orchestrator with module registry."""
        self._module_registry: dict[str, ModuleDescriptor] = {}
        self._module_instances: list[dict[str, Any]] = []
        self.discover_modules()  # Auto-discover modules (Phase 3)

    def discover_modules(self) -> None:
        """Auto-discover and register all modules from oncutf/modules/.
        
        Phase 3.1: Read metadata from class attributes instead of hardcoded dict.
        Scans oncutf/modules/ for *_module.py files and auto-registers classes
        that inherit from BaseRenameModule or have apply_from_data() method.
        
        Module metadata extracted from class attributes:
        - DISPLAY_NAME: UI label (fallback to class name)
        - UI_ROWS: Number of UI rows (fallback to 1)
        - DESCRIPTION: Module description (fallback to first docstring line)
        - CATEGORY: Grouping for node editor (fallback to "Other")
        """
        import oncutf.modules

        modules_package = oncutf.modules
        modules_path = Path(modules_package.__file__).parent

        logger.debug("[ModuleOrchestrator] Discovering modules in: %s", modules_path)

        discovered_count = 0

        # Scan all *_module.py files
        for _importer, module_name, _is_pkg in pkgutil.iter_modules([str(modules_path)]):
            if not module_name.endswith("_module") or module_name == "base_module":
                continue

            try:
                # Import module
                full_module_name = f"oncutf.modules.{module_name}"
                module = importlib.import_module(full_module_name)

                # Find classes with apply_from_data method
                for _name, obj in inspect.getmembers(module, inspect.isclass):
                    if not hasattr(obj, "apply_from_data"):
                        continue

                    class_name = obj.__name__

                    # Phase 3.1: Read metadata from class attributes
                    display_name = getattr(
                        obj, "DISPLAY_NAME", class_name.replace("Module", "")
                    )
                    ui_rows = getattr(obj, "UI_ROWS", 1)
                    category = getattr(obj, "CATEGORY", "Other")

                    # Get description from class attribute or docstring
                    description = getattr(obj, "DESCRIPTION", "")
                    if not description and obj.__doc__:
                        description = obj.__doc__.strip().split("\n")[0]

                    # Register the module
                    descriptor = ModuleDescriptor(
                        name=module_name.replace("_module", ""),
                        display_name=display_name,
                        module_class=obj,
                        ui_widget_class=obj,  # Most modules are both logic + UI
                        ui_rows=ui_rows,
                        description=description,
                    )

                    self.register_module(descriptor)
                    discovered_count += 1
                    logger.debug(
                        "[ModuleOrchestrator] Discovered: %s (%s) - Category: %s, Rows: %d",
                        display_name,
                        class_name,
                        category,
                        ui_rows,
                    )

            except Exception as e:
                logger.warning(
                    "[ModuleOrchestrator] Failed to discover module %s: %s",
                    module_name,
                    e,
                )

        logger.info(
            "[ModuleOrchestrator] Module discovery complete: %d modules registered",
            discovered_count,
        )

    def register_module(self, descriptor: ModuleDescriptor) -> None:
        """Register a module type.
        
        Args:
            descriptor: Module metadata
        """
        self._module_registry[descriptor.name] = descriptor
        logger.debug("[ModuleOrchestrator] Registered module: %s", descriptor.name)

    def get_module_descriptor(self, name: str) -> ModuleDescriptor | None:
        """Get module descriptor by name.
        
        Args:
            name: Module internal name
            
        Returns:
            ModuleDescriptor or None if not found
        """
        return self._module_registry.get(name)

    def get_available_modules(self) -> list[ModuleDescriptor]:
        """Get all available module types.
        
        Returns:
            List of module descriptors
        """
        return list(self._module_registry.values())

    def get_display_names(self) -> list[str]:
        """Get display names for UI combo boxes.
        
        Returns:
            List of display names
        """
        return [desc.display_name for desc in self._module_registry.values()]

    def create_module_instance(
        self, name: str, config: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a new module instance with configuration.
        
        Args:
            name: Module type name
            config: Optional configuration dict
            
        Returns:
            Module instance data
        """
        descriptor = self._module_registry.get(name)
        if not descriptor:
            logger.warning("[ModuleOrchestrator] Unknown module type: %s", name)
            return {}

        instance = {
            "type": name,
            "descriptor": descriptor,
            "config": config or {},
        }

        return instance

    def add_module(self, name: str, config: dict[str, Any] | None = None) -> int:
        """Add a module to the pipeline.
        
        Args:
            name: Module type name
            config: Optional configuration
            
        Returns:
            Index of added module
        """
        instance = self.create_module_instance(name, config)
        self._module_instances.append(instance)
        logger.debug(
            "[ModuleOrchestrator] Added module: %s (total: %d)",
            name,
            len(self._module_instances),
        )
        return len(self._module_instances) - 1

    def remove_module(self, index: int) -> bool:
        """Remove a module from the pipeline.
        
        Args:
            index: Module index
            
        Returns:
            True if removed successfully
        """
        if 0 <= index < len(self._module_instances):
            removed = self._module_instances.pop(index)
            logger.debug(
                "[ModuleOrchestrator] Removed module at %d: %s",
                index,
                removed.get("type"),
            )
            return True
        return False

    def reorder_module(self, from_index: int, to_index: int) -> bool:
        """Reorder a module in the pipeline.
        
        Args:
            from_index: Current index
            to_index: Target index
            
        Returns:
            True if reordered successfully
        """
        if from_index == to_index:
            return False

        if not (0 <= from_index < len(self._module_instances)):
            return False

        if not (0 <= to_index < len(self._module_instances)):
            return False

        module = self._module_instances.pop(from_index)
        self._module_instances.insert(to_index, module)
        logger.debug(
            "[ModuleOrchestrator] Reordered module from %d to %d", from_index, to_index
        )
        return True

    def get_module_count(self) -> int:
        """Get number of modules in pipeline.
        
        Returns:
            Module count
        """
        return len(self._module_instances)

    def get_module_at(self, index: int) -> dict[str, Any] | None:
        """Get module instance at index.
        
        Args:
            index: Module index
            
        Returns:
            Module instance or None
        """
        if 0 <= index < len(self._module_instances):
            return self._module_instances[index]
        return None

    def collect_all_data(self) -> dict[str, Any]:
        """Collect data from all modules for rename engine.
        
        Returns:
            Dict with 'modules' list
        """
        modules_data = []
        for instance in self._module_instances:
            module_data = instance.get("config", {}).copy()
            module_data["type"] = instance["type"]
            modules_data.append(module_data)

        return {"modules": modules_data}

    def validate_module(self, index: int) -> tuple[bool, str]:
        """Validate module configuration.
        
        Args:
            index: Module index
            
        Returns:
            (is_valid, error_message)
        """
        module = self.get_module_at(index)
        if not module:
            return False, "Module not found"

        descriptor = module.get("descriptor")
        if not descriptor:
            return False, "Invalid module descriptor"

        # Check if module class has is_effective_data method
        if hasattr(descriptor.module_class, "is_effective_data"):
            config = module.get("config", {})
            config["type"] = module["type"]
            if not descriptor.module_class.is_effective_data(config):
                return False, "Module configuration incomplete"

        return True, ""

    def clear_all_modules(self) -> None:
        """Remove all modules from pipeline."""
        count = len(self._module_instances)
        self._module_instances.clear()
        logger.debug("[ModuleOrchestrator] Cleared %d modules", count)
