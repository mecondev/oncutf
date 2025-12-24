"""Hash operations module.

This module provides file hash calculation functionality including:
- HashManager: Main hash operations coordination
- HashOperationsManager: Batch hash operations
- HashWorker: Individual hash calculations
- ParallelHashWorker: Parallel hash processing

Author: Michael Economou
Date: 2025-12-20
"""

from __future__ import annotations

from oncutf.core.hash.hash_manager import HashManager
from oncutf.core.hash.hash_operations_manager import HashOperationsManager
from oncutf.core.hash.hash_worker import HashWorker
from oncutf.core.hash.parallel_hash_worker import ParallelHashWorker

__all__ = [
    "HashManager",
    "HashOperationsManager",
    "HashWorker",
    "ParallelHashWorker",
]
