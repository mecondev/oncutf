"""
Module: conftest.py

Author: Michael Economou
Date: 2025-05-31

"""
# tests/conftest.py
import os
import sys

# Add project root to sys.path so 'widgets', 'models', etc. can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
