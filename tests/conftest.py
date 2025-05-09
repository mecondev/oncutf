# tests/conftest.py
import sys
import os

# Add project root to sys.path so 'widgets', 'models', etc. can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
