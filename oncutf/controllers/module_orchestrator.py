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
"""

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
        self._register_core_modules()

    def _register_core_modules(self) -> None:
        """Register core module types with lazy UI imports."""
        # Lazy imports to avoid circular dependencies
        from oncutf.modules.specified_text_module import SpecifiedTextModule
        from oncutf.modules.text_removal_module import TextRemovalModule

        # Register pure logic modules
        self.register_module(
            ModuleDescriptor(
                name="counter",
                display_name="Counter",
                module_class=CounterModule,
                ui_widget_class=CounterModule,  # CounterModule is both logic + UI
                ui_rows=3,
                description="Sequential numbering",
            )
        )

        self.register_module(
            ModuleDescriptor(
                name="metadata",
                display_name="Metadata",
                module_class=MetadataModule,
                ui_widget_class=None,  # Will be set via lazy import
                ui_rows=2,
                description="Extract file metadata (dates, hash, EXIF)",
            )
        )

        self.register_module(
            ModuleDescriptor(
                name="original_name",
                display_name="Original Name",
                module_class=OriginalNameModule,
                ui_widget_class=None,  # Will be set via lazy import
                ui_rows=1,
                description="Keep original filename",
            )
        )

        self.register_module(
            ModuleDescriptor(
                name="text_removal",
                display_name="Remove Text from Original Name",
                module_class=TextRemovalModule,
                ui_widget_class=TextRemovalModule,
                ui_rows=2,
                description="Remove text patterns from filename",
            )
        )

        self.register_module(
            ModuleDescriptor(
                name="specified_text",
                display_name="Specified Text",
                module_class=SpecifiedTextModule,
                ui_widget_class=SpecifiedTextModule,
                ui_rows=1,
                description="Insert custom text",
            )
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
