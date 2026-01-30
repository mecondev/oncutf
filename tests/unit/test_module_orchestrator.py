"""Tests for ModuleOrchestrator controller.

Author: Michael Economou
Date: 2025-12-27

Tests the module pipeline management logic independently of UI.
"""

from oncutf.controllers.module_orchestrator import ModuleDescriptor, ModuleOrchestrator
from oncutf.modules.counter_module import CounterModule


class TestModuleDescriptor:
    """Test ModuleDescriptor metadata container."""

    def test_creation(self):
        """Test descriptor creation."""
        desc = ModuleDescriptor(
            name="test",
            display_name="Test Module",
            module_class=CounterModule,
            ui_rows=2,
            description="Test description",
        )

        assert desc.name == "test"
        assert desc.display_name == "Test Module"
        assert desc.module_class == CounterModule
        assert desc.ui_rows == 2
        assert desc.description == "Test description"


class TestModuleOrchestrator:
    """Test ModuleOrchestrator pipeline management."""

    def test_initialization(self):
        """Test orchestrator initializes with core modules."""
        orch = ModuleOrchestrator()

        # Should have core modules registered
        modules = orch.get_available_modules()
        assert len(modules) > 0

        # Should have counter module
        counter_desc = orch.get_module_descriptor("counter")
        assert counter_desc is not None
        assert counter_desc.display_name == "Counter"

    def test_get_display_names(self):
        """Test getting UI display names."""
        orch = ModuleOrchestrator()
        names = orch.get_display_names()

        assert "Counter" in names
        assert "Metadata" in names
        assert "Specified Text" in names

    def test_add_module(self):
        """Test adding module to pipeline."""
        orch = ModuleOrchestrator()
        assert orch.get_module_count() == 0

        idx = orch.add_module("counter", {"start": 1, "digits": 3})
        assert idx == 0
        assert orch.get_module_count() == 1

        module = orch.get_module_at(0)
        assert module is not None
        assert module["type"] == "counter"
        assert module["config"]["start"] == 1

    def test_add_multiple_modules(self):
        """Test adding multiple modules."""
        orch = ModuleOrchestrator()

        orch.add_module("counter")
        orch.add_module("metadata")
        orch.add_module("specified_text")

        assert orch.get_module_count() == 3
        assert orch.get_module_at(0)["type"] == "counter"
        assert orch.get_module_at(1)["type"] == "metadata"
        assert orch.get_module_at(2)["type"] == "specified_text"

    def test_remove_module(self):
        """Test removing module from pipeline."""
        orch = ModuleOrchestrator()
        orch.add_module("counter")
        orch.add_module("metadata")
        orch.add_module("specified_text")

        # Remove middle module
        success = orch.remove_module(1)
        assert success is True
        assert orch.get_module_count() == 2
        assert orch.get_module_at(0)["type"] == "counter"
        assert orch.get_module_at(1)["type"] == "specified_text"

    def test_remove_invalid_index(self):
        """Test removing with invalid index."""
        orch = ModuleOrchestrator()
        orch.add_module("counter")

        # Try to remove invalid indices
        assert orch.remove_module(-1) is False
        assert orch.remove_module(5) is False
        assert orch.get_module_count() == 1

    def test_reorder_module(self):
        """Test reordering modules in pipeline."""
        orch = ModuleOrchestrator()
        orch.add_module("counter")
        orch.add_module("metadata")
        orch.add_module("specified_text")

        # Move first to last
        success = orch.reorder_module(0, 2)
        assert success is True
        assert orch.get_module_at(0)["type"] == "metadata"
        assert orch.get_module_at(1)["type"] == "specified_text"
        assert orch.get_module_at(2)["type"] == "counter"

    def test_reorder_same_position(self):
        """Test reordering to same position (no-op)."""
        orch = ModuleOrchestrator()
        orch.add_module("counter")
        orch.add_module("metadata")

        # Try to move to same position
        success = orch.reorder_module(0, 0)
        assert success is False
        assert orch.get_module_at(0)["type"] == "counter"

    def test_reorder_invalid_indices(self):
        """Test reordering with invalid indices."""
        orch = ModuleOrchestrator()
        orch.add_module("counter")

        assert orch.reorder_module(-1, 0) is False
        assert orch.reorder_module(0, 5) is False
        assert orch.reorder_module(5, 0) is False

    def test_collect_all_data(self):
        """Test collecting data from all modules."""
        orch = ModuleOrchestrator()
        orch.add_module("counter", {"start": 1, "digits": 3})
        orch.add_module("specified_text", {"text": "test"})

        data = orch.collect_all_data()

        assert "modules" in data
        assert len(data["modules"]) == 2

        # Check first module
        assert data["modules"][0]["type"] == "counter"
        assert data["modules"][0]["start"] == 1
        assert data["modules"][0]["digits"] == 3

        # Check second module
        assert data["modules"][1]["type"] == "specified_text"
        assert data["modules"][1]["text"] == "test"

    def test_collect_empty_pipeline(self):
        """Test collecting data from empty pipeline."""
        orch = ModuleOrchestrator()
        data = orch.collect_all_data()

        assert "modules" in data
        assert len(data["modules"]) == 0

    def test_validate_module(self):
        """Test module validation."""
        orch = ModuleOrchestrator()
        orch.add_module("counter", {"start": 1, "digits": 3})

        # Valid module
        is_valid, error = orch.validate_module(0)
        assert is_valid is True
        assert error == ""

    def test_validate_invalid_index(self):
        """Test validating invalid index."""
        orch = ModuleOrchestrator()
        orch.add_module("counter")

        is_valid, error = orch.validate_module(5)
        assert is_valid is False
        assert "not found" in error.lower()

    def test_clear_all_modules(self):
        """Test clearing all modules."""
        orch = ModuleOrchestrator()
        orch.add_module("counter")
        orch.add_module("metadata")
        orch.add_module("specified_text")

        assert orch.get_module_count() == 3

        orch.clear_all_modules()
        assert orch.get_module_count() == 0

    def test_get_module_at_bounds(self):
        """Test getting module at boundary indices."""
        orch = ModuleOrchestrator()
        orch.add_module("counter")
        orch.add_module("metadata")

        # Valid indices
        assert orch.get_module_at(0) is not None
        assert orch.get_module_at(1) is not None

        # Invalid indices
        assert orch.get_module_at(-1) is None
        assert orch.get_module_at(2) is None

    def test_register_custom_module(self):
        """Test registering a custom module type."""
        orch = ModuleOrchestrator()

        # Register custom module
        custom_desc = ModuleDescriptor(
            name="custom",
            display_name="Custom Module",
            module_class=CounterModule,  # Reuse for testing
            ui_rows=1,
        )
        orch.register_module(custom_desc)

        # Verify registration
        desc = orch.get_module_descriptor("custom")
        assert desc is not None
        assert desc.display_name == "Custom Module"

        # Can add instance
        idx = orch.add_module("custom", {"test": "value"})
        assert idx == 0
        assert orch.get_module_at(0)["type"] == "custom"


class TestModuleDiscovery:
    """Test Phase 3: Dynamic module discovery."""

    def test_discover_modules(self):
        """Test auto-discovery finds all modules."""
        orch = ModuleOrchestrator()

        # Should discover core modules
        modules = orch.get_available_modules()
        display_names = [m.display_name for m in modules]

        assert "Counter" in display_names
        assert "Metadata" in display_names
        assert "Original Name" in display_names
        assert "Specified Text" in display_names
        assert "Remove Text from Original Name" in display_names
        assert "Name Transform" in display_names

    def test_discovered_modules_have_metadata(self):
        """Test discovered modules have proper metadata."""
        orch = ModuleOrchestrator()

        counter_desc = orch.get_module_descriptor("counter")
        assert counter_desc is not None
        assert counter_desc.display_name == "Counter"
        assert counter_desc.ui_rows == 3
        assert counter_desc.module_class is not None
        assert hasattr(counter_desc.module_class, "apply_from_data")

    def test_all_discovered_modules_usable(self):
        """Test all discovered modules can be added to pipeline."""
        orch = ModuleOrchestrator()

        for descriptor in orch.get_available_modules():
            idx = orch.add_module(descriptor.name, {})
            assert idx >= 0, f"Failed to add module: {descriptor.display_name}"

        # Should have added all modules
        assert orch.get_module_count() == len(orch.get_available_modules())

    def test_module_discovery_count(self):
        """Test expected number of modules discovered."""
        orch = ModuleOrchestrator()
        modules = orch.get_available_modules()

        # Should discover at least 6 modules (can be more if new ones added)
        # Counter, Metadata, Original Name, Specified Text, Text Removal, Name Transform
        assert len(modules) >= 6, f"Expected >= 6 modules, found {len(modules)}"

    def test_discovery_excludes_base_module(self):
        """Test discovery skips base_module.py."""
        orch = ModuleOrchestrator()
        names = [m.name for m in orch.get_available_modules()]

        assert "base" not in names
        assert "base_module" not in names


class TestClassLevelMetadata:
    """Test Phase 3.1: Class-level metadata attributes."""

    def test_modules_have_display_name(self):
        """Test all modules have DISPLAY_NAME attribute."""
        from oncutf.modules.counter_module import CounterModule
        from oncutf.modules.metadata_module import MetadataModule
        from oncutf.modules.specified_text_module import SpecifiedTextModule

        assert hasattr(CounterModule, "DISPLAY_NAME")
        assert CounterModule.DISPLAY_NAME == "Counter"

        assert hasattr(MetadataModule, "DISPLAY_NAME")
        assert MetadataModule.DISPLAY_NAME == "Metadata"

        assert hasattr(SpecifiedTextModule, "DISPLAY_NAME")
        assert SpecifiedTextModule.DISPLAY_NAME == "Specified Text"

    def test_modules_have_ui_rows(self):
        """Test all modules have UI_ROWS attribute."""
        from oncutf.modules.counter_module import CounterModule
        from oncutf.modules.original_name_module import OriginalNameModule

        assert hasattr(CounterModule, "UI_ROWS")
        assert CounterModule.UI_ROWS == 3

        assert hasattr(OriginalNameModule, "UI_ROWS")
        assert OriginalNameModule.UI_ROWS == 1

    def test_modules_have_category(self):
        """Test all modules have CATEGORY attribute."""
        from oncutf.modules.counter_module import CounterModule
        from oncutf.modules.metadata_module import MetadataModule
        from oncutf.modules.specified_text_module import SpecifiedTextModule

        assert hasattr(CounterModule, "CATEGORY")
        assert CounterModule.CATEGORY == "Numbering"

        assert hasattr(MetadataModule, "CATEGORY")
        assert MetadataModule.CATEGORY == "Metadata"

        assert hasattr(SpecifiedTextModule, "CATEGORY")
        assert SpecifiedTextModule.CATEGORY == "Text"

    def test_modules_have_description(self):
        """Test all modules have DESCRIPTION attribute."""
        from oncutf.modules.counter_module import CounterModule
        from oncutf.modules.text_removal_module import TextRemovalModule

        assert hasattr(CounterModule, "DESCRIPTION")
        assert "numbering" in CounterModule.DESCRIPTION.lower()

        assert hasattr(TextRemovalModule, "DESCRIPTION")
        assert "remove" in TextRemovalModule.DESCRIPTION.lower()

    def test_orchestrator_uses_class_metadata(self):
        """Test orchestrator reads metadata from class attributes."""
        orch = ModuleOrchestrator()

        # Get Counter module descriptor
        counter_desc = orch.get_module_descriptor("counter")
        assert counter_desc is not None

        # Verify metadata comes from class attributes
        from oncutf.modules.counter_module import CounterModule

        assert counter_desc.display_name == CounterModule.DISPLAY_NAME
        assert counter_desc.ui_rows == CounterModule.UI_ROWS

    def test_all_discovered_modules_have_metadata(self):
        """Test all discovered modules have required metadata."""
        orch = ModuleOrchestrator()

        for descriptor in orch.get_available_modules():
            # All should have display_name
            assert descriptor.display_name, f"Module {descriptor.name} missing display_name"

            # All should have ui_rows >= 1
            assert descriptor.ui_rows >= 1, f"Module {descriptor.name} has invalid ui_rows"

            # All should have module_class with required method
            assert hasattr(descriptor.module_class, "apply_from_data"), (
                f"Module {descriptor.name} missing apply_from_data method"
            )
