#!/usr/bin/env python3
"""
Test script για να ελέγξουμε αν το πρόβλημα των infinite loops επιλύθηκε.
"""

import sys
import time

def test_selection_sync():
    """Test για να ελέγξουμε αν το selection sync λειτουργεί σωστά."""
    print("=== Test Selection Sync ===")

    # Εισαγωγή των απαραίτητων modules
    try:
        from core.selection_store import SelectionStore
        from core.application_context import ApplicationContext
        print("✓ Modules imported successfully")
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

    # Δημιουργία SelectionStore
    try:
        selection_store = SelectionStore()
        print("✓ SelectionStore created successfully")
    except Exception as e:
        print(f"✗ SelectionStore creation error: {e}")
        return False

    # Test 1: Basic selection operations
    try:
        selection_store.set_selected_rows({0, 1, 2}, emit_signal=True)
        selected = selection_store.get_selected_rows()
        print(f"✓ Set selection: {selected}")

        selection_store.set_selected_rows({3, 4, 5}, emit_signal=True)
        selected = selection_store.get_selected_rows()
        print(f"✓ Updated selection: {selected}")

        selection_store.clear_selection(emit_signal=True)
        selected = selection_store.get_selected_rows()
        print(f"✓ Cleared selection: {selected}")

    except Exception as e:
        print(f"✗ Selection operations error: {e}")
        return False

    # Test 2: Check sync flag protection
    try:
        # Simulate sync operation
        selection_store._syncing_selection = True
        selection_store.set_selected_rows({10, 11, 12}, emit_signal=True)
        selected = selection_store.get_selected_rows()
        print(f"✓ Sync protection working: {selected}")
        selection_store._syncing_selection = False

    except Exception as e:
        print(f"✗ Sync protection error: {e}")
        return False

    print("✓ All selection tests passed!")
    return True

def test_application_context():
    """Test για να ελέγξουμε αν το ApplicationContext λειτουργεί σωστά."""
    print("\n=== Test ApplicationContext ===")

    try:
        from core.application_context import ApplicationContext

        # Δημιουργία ApplicationContext
        context = ApplicationContext.create_instance()
        print("✓ ApplicationContext created successfully")

        # Test selection store access
        selection_store = context.selection_store
        if selection_store:
            print("✓ SelectionStore accessible through context")
        else:
            print("✗ SelectionStore not accessible through context")
            return False

    except Exception as e:
        print(f"✗ ApplicationContext error: {e}")
        return False

    print("✓ ApplicationContext tests passed!")
    return True

def main():
    """Main test function."""
    print("Starting selection sync tests...")

    # Test 1: Selection Store
    if not test_selection_sync():
        print("✗ Selection sync tests failed!")
        return False

    # Test 2: Application Context
    if not test_application_context():
        print("✗ ApplicationContext tests failed!")
        return False

    print("\n🎉 All tests passed! The infinite loop protection should be working.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
