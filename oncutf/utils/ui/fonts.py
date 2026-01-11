"""Module: fonts.py

Author: Michael Economou
Date: 2025-05-31

Font utilities for Inter fonts
Manages loading and providing access to the Inter font family
"""

import logging
from typing import TYPE_CHECKING

from oncutf.core.pyqt_imports import QFont, QFontDatabase, QResource

if TYPE_CHECKING:
    from oncutf.ui import resources_rc  # noqa: F401

logger = logging.getLogger(__name__)


class InterFonts:
    """Manager for Inter font family with predefined use cases"""

    # Font file mappings
    FONT_FILES = {
        "regular": "Inter-Regular.ttf",
        "medium": "Inter-Medium.ttf",
        "semibold": "InterDisplay-SemiBold.ttf",
        "italic": "Inter-Italic.ttf",
        "display_semibold": "InterDisplay-SemiBold.ttf",
    }

    # CSS weight mappings for styling
    CSS_WEIGHTS = {
        "regular": 400,
        "medium": 500,
        "semibold": 600,
        "italic": 400,
        "display_semibold": 600,
    }

    def __init__(self) -> None:
        """Initialize the Inter fonts manager and load all font variants."""
        self.loaded_fonts: dict[str, int] = {}
        self.font_families: dict[str, str] = {}
        self._load_fonts_from_resources()

    def _load_fonts_from_resources(self) -> None:
        """Load all Inter fonts from filesystem or QResource based on configuration"""
        import os

        from oncutf.config import USE_EMBEDDED_FONTS
        from oncutf.utils.filesystem.path_utils import get_fonts_dir

        if USE_EMBEDDED_FONTS:
            # Use QRC embedded fonts
            self._load_from_qresource()
        else:
            # Try to load from filesystem first (more stable)
            fonts_dir = str(get_fonts_dir())

            if os.path.exists(fonts_dir):
                for font_key, font_file in self.FONT_FILES.items():
                    font_path = os.path.join(fonts_dir, font_file)

                    if os.path.exists(font_path):
                        # Load font from file path (more stable than QResource data)
                        font_id = QFontDatabase.addApplicationFont(font_path)
                        if font_id != -1:
                            families = QFontDatabase.applicationFontFamilies(font_id)
                            if families:
                                self.loaded_fonts[font_key] = font_id
                                self.font_families[font_key] = families[0]
                                logger.debug(
                                    "Loaded %s: %s from %s",
                                    font_key,
                                    families[0],
                                    font_path,
                                    extra={"dev_only": True},
                                )
                            else:
                                logger.warning("No families found for %s", font_key)
                        else:
                            logger.error("Failed to load font %s from %s", font_key, font_path)
                    else:
                        logger.error("Font file not found: %s", font_path)
            else:
                logger.error("Fonts directory not found: %s", fonts_dir)

        # Fallback: try QResource if filesystem loading failed
        if not self.loaded_fonts and not USE_EMBEDDED_FONTS:
            logger.debug("Trying QResource fallback...", extra={"dev_only": True})
            try:
                # Import is used for side effects to register resources
                import oncutf.utils.ui.fonts_rc  # noqa: F401

                for font_key, font_file in self.FONT_FILES.items():
                    if font_key not in self.loaded_fonts:
                        resource_path = f":/fonts/{font_file}"

                        # Load font from Qt resources (may cause issues on some systems)
                        font_data = QResource(resource_path).data()
                        if font_data:
                            # Use temporary file approach for problematic systems
                            import tempfile

                            with tempfile.NamedTemporaryFile(
                                suffix=".ttf", delete=False
                            ) as tmp_file:
                                tmp_file.write(font_data)
                                tmp_path = tmp_file.name

                            font_id = QFontDatabase.addApplicationFont(tmp_path)
                            os.unlink(tmp_path)  # Clean up temp file

                            if font_id != -1:
                                families = QFontDatabase.applicationFontFamilies(font_id)
                                if families:
                                    self.loaded_fonts[font_key] = font_id
                                    self.font_families[font_key] = families[0]
                                    logger.debug(
                                        "Loaded %s: %s from resources",
                                        font_key,
                                        families[0],
                                        extra={"dev_only": True},
                                    )

            except ImportError as e:
                logger.error("Could not import fonts_rc: %s", e)
                logger.info("Run: pyrcc5 resources/fonts.qrc -o resources/fonts_rc.py")

    def _load_from_qresource(self) -> None:
        """Load fonts from QResource (embedded mode)"""
        import os
        import tempfile

        logger.debug("Loading fonts from embedded QResource...", extra={"dev_only": True})
        try:
            # Import is used for side effects to register resources
            import oncutf.utils.ui.fonts_rc  # noqa: F401

            for font_key, font_file in self.FONT_FILES.items():
                resource_path = f":/fonts/{font_file}"

                # Load font from Qt resources
                font_data = QResource(resource_path).data()
                if font_data:
                    # Use temporary file approach for problematic systems
                    with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as tmp_file:
                        tmp_file.write(font_data)
                        tmp_path = tmp_file.name

                    font_id = QFontDatabase.addApplicationFont(tmp_path)
                    os.unlink(tmp_path)  # Clean up temp file

                    if font_id != -1:
                        families = QFontDatabase.applicationFontFamilies(font_id)
                        if families:
                            self.loaded_fonts[font_key] = font_id
                            self.font_families[font_key] = families[0]
                            logger.debug(
                                "Loaded %s: %s from embedded resources",
                                font_key,
                                families[0],
                                extra={"dev_only": True},
                            )
                        else:
                            logger.warning("No families found for embedded %s", font_key)
                    else:
                        logger.error("Failed to load embedded font %s", font_key)
                else:
                    logger.error(
                        "No data found for embedded font %s at %s", font_key, resource_path
                    )

        except ImportError as e:
            logger.error("Could not import fonts_rc for embedded fonts: %s", e)
            logger.info("Run: pyrcc5 resources/fonts.qrc -o utils/fonts_rc.py")

    def get_font(self, use_case: str, size: int = 10) -> QFont:
        """Get a QFont for specific use case with DPI scaling

        Args:
            use_case: One of 'base', 'buttons', 'headers', 'titles', 'emphasis', 'medium'
            size: Font size in points (will be scaled for DPI)

        Returns:
            QFont object configured for the use case

        """
        font_mapping = {
            "base": "regular",
            "buttons": "medium",
            "interface": "medium",
            "medium": "medium",
            "headers": "semibold",
            "emphasis": "italic",
            "titles": "display_semibold",
        }

        font_key = font_mapping.get(use_case, "regular")

        # Apply DPI scaling to font size
        try:
            from oncutf.utils.ui.dpi_helper import scale_font_size

            scaled_size = scale_font_size(size)
        except ImportError:
            # Fallback if DPI helper not available
            scaled_size = size

        if font_key in self.font_families:
            family = self.font_families[font_key]
            font = QFont(family, scaled_size)

            # Set italic style if needed
            if font_key == "italic":
                font.setItalic(True)

            return font
        else:
            logger.warning("Font key '%s' not loaded, using system default", font_key)
            return QFont("Arial", scaled_size)

    def get_css_weight(self, use_case: str) -> int:
        """Get CSS font-weight value for use case"""
        font_mapping = {
            "base": "regular",
            "buttons": "medium",
            "interface": "medium",
            "medium": "medium",
            "headers": "semibold",
            "emphasis": "italic",
            "titles": "display_semibold",
        }

        font_key = font_mapping.get(use_case, "regular")
        return self.CSS_WEIGHTS.get(font_key, 400)

    def get_font_family(self, use_case: str) -> str:
        """Get font family name for use case"""
        font_mapping = {
            "base": "regular",
            "buttons": "medium",
            "interface": "medium",
            "medium": "medium",
            "headers": "semibold",
            "emphasis": "italic",
            "titles": "display_semibold",
        }

        font_key = font_mapping.get(use_case, "regular")

        if font_key in self.font_families:
            return self.font_families[font_key]
        else:
            return "Arial"  # Fallback

    def create_stylesheet_fonts(self) -> str:
        """Create CSS stylesheet with font definitions"""
        styles = []

        for use_case in ["base", "buttons", "medium", "headers", "emphasis", "titles"]:
            family = self.get_font_family(use_case)
            weight = self.get_css_weight(use_case)
            style = "italic" if use_case == "emphasis" else "normal"

            css_class = f".font-{use_case.replace('_', '-')}"
            style_def = f"""
            {css_class} {{
                font-family: '{family}', Arial, sans-serif;
                font-weight: {weight};
                font-style: {style};
            }}"""
            styles.append(style_def)

        return "\n".join(styles)


# Global instance (lazy loaded)
inter_fonts = None


def _get_inter_fonts() -> InterFonts:
    """Get or create the global Inter fonts instance"""
    global inter_fonts
    if inter_fonts is None:
        inter_fonts = InterFonts()
    return inter_fonts


# Convenience functions
def get_inter_font(use_case: str, size: int = 10) -> QFont:
    """Get Inter font for specific use case"""
    return _get_inter_fonts().get_font(use_case, size)


def get_inter_css_weight(use_case: str) -> int:
    """Get CSS weight for Inter font use case"""
    return _get_inter_fonts().get_css_weight(use_case)


def get_inter_family(use_case: str) -> str:
    """Get Inter font family name for use case"""
    return _get_inter_fonts().get_font_family(use_case)


class JetBrainsFonts:
    """Manager for JetBrains Mono font family."""

    # Font file mappings
    FONT_FILES = {
        "regular": "JetBrainsMono-Regular.ttf",
        "bold": "JetBrainsMono-Bold.ttf",
        "italic": "JetBrainsMono-Italic.ttf",
        "bold_italic": "JetBrainsMono-BoldItalic.ttf",
    }

    def __init__(self) -> None:
        """Initialize the JetBrains Mono fonts manager and load all font variants."""
        self.loaded_fonts: dict[str, int] = {}
        self.font_families: dict[str, str] = {}
        self._load_fonts_from_resources()

    def _load_fonts_from_resources(self) -> None:
        """Load all JetBrains Mono fonts from embedded QRC resources."""
        try:
            # Import is used for side effects to register resources
            import oncutf.ui.resources_rc  # noqa: F401

            for font_key, font_file in self.FONT_FILES.items():
                resource_path = f":/fonts/fonts/jetbrains/{font_file}"

                # Load font from Qt resources
                font_id = QFontDatabase.addApplicationFont(resource_path)
                if font_id != -1:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    if families:
                        self.loaded_fonts[font_key] = font_id
                        self.font_families[font_key] = families[0]
                        logger.debug(
                            "Loaded %s: %s from %s",
                            font_key,
                            families[0],
                            resource_path,
                            extra={"dev_only": True},
                        )
                    else:
                        logger.warning("No families found for %s", font_key)
                else:
                    logger.error("Failed to load font %s from %s", font_key, resource_path)

            if self.loaded_fonts:
                logger.info(
                    "Loaded %d JetBrains Mono font variants",
                    len(self.loaded_fonts),
                )
            else:
                logger.error("Failed to load any JetBrains Mono fonts")

        except Exception as e:
            logger.error("Failed to load JetBrains Mono fonts: %s", str(e))

    def get_font(self, style: str = "regular", size: int = 10) -> QFont:
        """Get a QFont instance for JetBrains Mono.

        Args:
            style: Font style ('regular', 'bold', 'italic', 'bold_italic')
            size: Font size in points

        Returns:
            QFont instance configured for JetBrains Mono

        """
        font_family = self.font_families.get(style, "JetBrains Mono")
        font = QFont(font_family)
        font.setPointSize(size)

        if style in {"bold", "bold_italic"}:
            font.setBold(True)
        if style in {"italic", "bold_italic"}:
            font.setItalic(True)

        return font


# Singleton instance for JetBrains Mono fonts
jetbrains_fonts: JetBrainsFonts | None = None


def _get_jetbrains_fonts() -> JetBrainsFonts:
    """Get or create the global JetBrains Mono fonts instance."""
    global jetbrains_fonts
    if jetbrains_fonts is None:
        jetbrains_fonts = JetBrainsFonts()
    return jetbrains_fonts


# Convenience functions for JetBrains Mono
def get_jetbrains_font(style: str = "regular", size: int = 10) -> QFont:
    """Get JetBrains Mono font for specific style.

    Args:
        style: Font style ('regular', 'bold', 'italic', 'bold_italic')
        size: Font size in points

    Returns:
        QFont instance

    """
    return _get_jetbrains_fonts().get_font(style, size)


def get_default_ui_font(size: int = 10, style: str = "regular") -> QFont:
    """Get the default UI font based on configuration.

    Automatically applies size adjustments based on the selected font
    to maintain visual consistency.

    Args:
        size: Base font size in points
        style: Font style ('regular', 'bold', 'italic', 'bold_italic')
                Only applies to JetBrains, ignored for Inter

    Returns:
        QFont instance configured as default UI font with size adjustment

    """
    from oncutf.config.ui import DEFAULT_UI_FONT, FONT_SIZE_ADJUSTMENTS

    # Get size adjustment for the selected font
    adjustment = FONT_SIZE_ADJUSTMENTS.get(DEFAULT_UI_FONT, 0)
    adjusted_size = size + adjustment

    if DEFAULT_UI_FONT == "jetbrains":
        return get_jetbrains_font(style=style, size=adjusted_size)
    else:
        # Default to Inter
        return get_inter_font(use_case="body", size=adjusted_size)


