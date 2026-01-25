"""JetBrains Mono Font Resources

This directory contains the JetBrains Mono font variants embedded in the application.

The fonts are managed via:
- `oncutf/utils/ui/fonts.py` - JetBrainsFonts class (singleton pattern)
- `resources/fonts.qrc` - Qt resource definition
- `oncutf/ui/resources_rc.py` - Auto-generated resource file

Usage:
    from oncutf.utils.ui.fonts import get_jetbrains_font
    
    font = get_jetbrains_font(style="regular", size=11)
    label.setFont(font)

Available styles: regular, bold, italic, bold_italic

Auto-loading:
    Fonts are automatically loaded in main.py via _get_jetbrains_fonts()

Regenerating resources:
    cd resources
    pyrcc5 fonts.qrc -o oncutf/ui/resources_rc.py
"""
