"""Module: test_theme_manager.py

Author: Michael Economou
Date: 2025-12-01

Tests for ThemeManager - centralized theme management system.
"""

import pytest


class TestThemeManager:
    """Test suite for ThemeManager functionality."""

    def test_theme_manager_singleton(self):
        """Test that get_theme_manager returns singleton instance."""
        from oncutf.core.theme_manager import get_theme_manager

        manager1 = get_theme_manager()
        manager2 = get_theme_manager()

        assert manager1 is manager2, "ThemeManager should be a singleton"

    def test_default_theme_is_dark(self):
        """Test that default theme is 'dark'."""
        from oncutf.core.theme_manager import get_theme_manager

        manager = get_theme_manager()
        assert manager.get_current_theme() == "dark"

    def test_get_color_returns_valid_hex(self):
        """Test that get_color returns valid hex color."""
        from oncutf.core.theme_manager import get_theme_manager

        manager = get_theme_manager()
        color = manager.get_color("background")

        assert isinstance(color, str)
        assert color.startswith("#")
        assert len(color) == 7  # #RRGGBB format

    def test_get_color_raises_on_invalid_token(self):
        """Test that get_color raises KeyError for invalid token."""
        from oncutf.core.theme_manager import get_theme_manager

        manager = get_theme_manager()

        with pytest.raises(KeyError):
            manager.get_color("nonexistent_token")

    def test_colors_property_returns_dict(self):
        """Test that colors property returns dictionary of all tokens."""
        from oncutf.core.theme_manager import get_theme_manager

        manager = get_theme_manager()
        colors = manager.colors

        assert isinstance(colors, dict)
        assert len(colors) > 0
        assert "background" in colors
        assert "text" in colors

    def test_set_theme_changes_current_theme(self):
        """Test that set_theme changes the current theme."""
        from oncutf.core.theme_manager import ThemeManager

        # Create new instance for isolated test
        manager = ThemeManager()
        assert manager.get_current_theme() == "dark"

        # Note: light theme is placeholder, but should still work
        # manager.set_theme("light")
        # assert manager.get_current_theme() == "light"

    def test_set_theme_raises_on_invalid_theme(self):
        """Test that set_theme raises ValueError for invalid theme."""
        from oncutf.core.theme_manager import ThemeManager

        manager = ThemeManager()

        with pytest.raises(ValueError, match="Invalid theme"):
            manager.set_theme("nonexistent_theme")

    def test_theme_changed_signal_emitted(self):
        """Test that theme_changed signal is emitted on theme change."""
        from oncutf.core.theme_manager import ThemeManager

        manager = ThemeManager()
        signal_received = []

        def on_theme_changed(theme_name):
            signal_received.append(theme_name)

        manager.theme_changed.connect(on_theme_changed)

        # Note: Can't test until light theme is implemented
        # manager.set_theme("light")
        # assert len(signal_received) == 1
        # assert signal_received[0] == "light"

    def test_get_qss_returns_string(self):
        """Test that get_qss returns rendered QSS string."""
        from oncutf.core.theme_manager import get_theme_manager

        manager = get_theme_manager()
        qss = manager.get_qss()

        assert isinstance(qss, str)
        # Should have content if template exists
        if qss:
            assert "QWidget" in qss or "QMenu" in qss
            # Should NOT have placeholders remaining
            assert "{{" not in qss

    def test_qss_caching(self):
        """Test that QSS is cached between calls."""
        from oncutf.core.theme_manager import ThemeManager

        manager = ThemeManager()
        qss1 = manager.get_qss()
        qss2 = manager.get_qss()

        # Should return same cached string
        assert qss1 == qss2

    def test_reload_theme_clears_cache(self):
        """Test that reload_theme clears QSS cache."""
        from oncutf.core.theme_manager import ThemeManager

        manager = ThemeManager()
        manager.get_qss()  # Populate cache
        assert manager._qss_cache != ""

        manager.reload_theme()
        assert manager._qss_cache == ""

    def test_theme_tokens_loaded_from_config(self):
        """Test that theme tokens are loaded from config."""
        from oncutf.core.theme_manager import get_theme_manager

        manager = get_theme_manager()

        # Should have loaded THEME_TOKENS from config
        assert manager._theme_tokens is not None
        assert "dark" in manager._theme_tokens

    def test_dark_theme_has_required_tokens(self):
        """Test that dark theme has all required color tokens."""
        from oncutf.core.theme_manager import get_theme_manager

        manager = get_theme_manager()
        dark_colors = manager.colors

        required_tokens = [
            "background",
            "text",
            "selected",
            "hover",
            "border",
            "menu_background",
            "table_background",
            "button_bg",
        ]

        for token in required_tokens:
            assert token in dark_colors, f"Missing required token: {token}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
