#!/usr/bin/env python3
"""
Debug script for font loading issues
"""

import sys
import logging

# Setup basic logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

print("🔍 Debug: Testing font loading step by step...")

try:
    print("1. Testing basic PyQt5 imports...")
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtGui import QFontDatabase
    print("✅ PyQt5 imports successful")

    print("\n2. Creating QApplication...")
    app = QApplication([])
    print("✅ QApplication created")

    print("\n3. Testing filesystem font loading...")
    font_path = "resources/fonts/inter/Inter-Regular.ttf"
    import os
    if os.path.exists(font_path):
        print(f"✅ Font file exists: {font_path}")

        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            print(f"✅ Font loaded successfully: ID={font_id}, Families={families}")
        else:
            print("❌ Failed to load font from filesystem")
    else:
        print(f"❌ Font file not found: {font_path}")

    print("\n4. Testing utils.fonts import...")
    from utils.fonts import inter_fonts
    print("✅ utils.fonts imported successfully")

    print(f"   Loaded fonts: {list(inter_fonts.loaded_fonts.keys())}")
    print(f"   Font families: {inter_fonts.font_families}")

    print("\n5. Testing font creation...")
    from utils.fonts import get_inter_font
    test_font = get_inter_font('base', 12)
    print(f"✅ Font creation successful: {test_font.family()}, {test_font.pointSize()}pt")

    print("\n🎉 All tests passed!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
