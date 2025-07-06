"""
Module: __init__.py

Author: Michael Economou
Date: 2025-05-31

"""
# SVG Icon System
from .svg_icon_generator import (
    SVGIconGenerator,
    generate_hash_icon,
    generate_metadata_icons,
)

# Add to __all__ if it exists
__all__ = [
    'SVGIconGenerator',
    'generate_metadata_icons',
    'generate_hash_icon',
]
