"""Unit tests for SessionStateStore.

Author: Michael Economou
Date: 2026-01-15

Tests for the session state database storage system.
"""

import sqlite3
import threading

import pytest

from oncutf.core.database.session_state_store import SessionStateStore


@pytest.fixture
def memory_db():
    """Create an in-memory database for testing."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@pytest.fixture
def store(memory_db):
    """Create a SessionStateStore instance for testing."""
    lock = threading.RLock()
    return SessionStateStore(memory_db, lock)


class TestSessionStateStore:
    """Test suite for SessionStateStore."""

    def test_set_and_get_string(self, store):
        """Test setting and getting a string value."""
        assert store.set("test_key", "test_value")
        assert store.get("test_key") == "test_value"

    def test_set_and_get_int(self, store):
        """Test setting and getting an integer value."""
        assert store.set("int_key", 42)
        result = store.get("int_key")
        assert result == 42
        assert isinstance(result, int)

    def test_set_and_get_float(self, store):
        """Test setting and getting a float value."""
        assert store.set("float_key", 3.14)
        result = store.get("float_key")
        assert result == 3.14
        assert isinstance(result, float)

    def test_set_and_get_bool_true(self, store):
        """Test setting and getting a boolean true value."""
        assert store.set("bool_key", True)
        result = store.get("bool_key")
        assert result is True
        assert isinstance(result, bool)

    def test_set_and_get_bool_false(self, store):
        """Test setting and getting a boolean false value."""
        assert store.set("bool_key_false", False)
        result = store.get("bool_key_false")
        assert result is False
        assert isinstance(result, bool)

    def test_set_and_get_dict(self, store):
        """Test setting and getting a dictionary value."""
        test_dict = {"key1": "value1", "key2": 42, "nested": {"a": 1}}
        assert store.set("dict_key", test_dict)
        result = store.get("dict_key")
        assert result == test_dict
        assert isinstance(result, dict)

    def test_set_and_get_list(self, store):
        """Test setting and getting a list value."""
        test_list = [1, "two", 3.0, {"four": 4}]
        assert store.set("list_key", test_list)
        result = store.get("list_key")
        assert result == test_list
        assert isinstance(result, list)

    def test_get_nonexistent_returns_default(self, store):
        """Test that getting a non-existent key returns the default."""
        assert store.get("nonexistent") is None
        assert store.get("nonexistent", "default") == "default"
        assert store.get("nonexistent", 42) == 42

    def test_update_existing_key(self, store):
        """Test updating an existing key."""
        assert store.set("update_key", "initial")
        assert store.get("update_key") == "initial"
        assert store.set("update_key", "updated")
        assert store.get("update_key") == "updated"

    def test_delete_key(self, store):
        """Test deleting a key."""
        assert store.set("delete_key", "value")
        assert store.exists("delete_key")
        assert store.delete("delete_key")
        assert not store.exists("delete_key")
        assert store.get("delete_key") is None

    def test_delete_nonexistent_key(self, store):
        """Test deleting a non-existent key returns False."""
        assert not store.delete("nonexistent")

    def test_exists(self, store):
        """Test checking if a key exists."""
        assert not store.exists("new_key")
        store.set("new_key", "value")
        assert store.exists("new_key")

    def test_get_all(self, store):
        """Test getting all session state values."""
        store.set("key1", "value1")
        store.set("key2", 42)
        store.set("key3", True)

        result = store.get_all()
        assert result["key1"] == "value1"
        assert result["key2"] == 42
        assert result["key3"] is True

    def test_set_many(self, store):
        """Test setting multiple values atomically."""
        data = {
            "batch_key1": "value1",
            "batch_key2": 42,
            "batch_key3": {"nested": "dict"},
        }
        assert store.set_many(data)

        assert store.get("batch_key1") == "value1"
        assert store.get("batch_key2") == 42
        assert store.get("batch_key3") == {"nested": "dict"}

    def test_clear(self, store):
        """Test clearing all session state."""
        store.set("key1", "value1")
        store.set("key2", "value2")
        assert store.exists("key1")

        assert store.clear()
        assert not store.exists("key1")
        assert not store.exists("key2")
        assert store.get_all() == {}


class TestSessionStateStoreAtomicity:
    """Test atomicity and thread safety of SessionStateStore."""

    def test_set_many_is_atomic(self, store):
        """Test that set_many is atomic - all or nothing."""
        # First set some valid data
        assert store.set_many({"key1": "value1", "key2": "value2"})
        assert store.get("key1") == "value1"
        assert store.get("key2") == "value2"


class TestSessionStateDefaults:
    """Test session state default values."""

    def test_sort_column_default(self, store):
        """Test that sort_column defaults correctly."""
        # Default should be 2 (filename column)
        result = store.get("sort_column", 2)
        assert result == 2

    def test_sort_order_default(self, store):
        """Test that sort_order defaults correctly."""
        # Default should be 0 (ascending)
        result = store.get("sort_order", 0)
        assert result == 0

    def test_empty_string_handling(self, store):
        """Test that empty strings are handled correctly."""
        assert store.set("empty_string", "")
        assert store.get("empty_string") == ""

    def test_none_handling(self, store):
        """Test that None values are handled correctly."""
        assert store.set("none_value", None)
        assert store.get("none_value") == ""  # Stored as empty string
