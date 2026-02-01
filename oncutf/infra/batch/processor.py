"""Module: batch_processor.py.

Author: Michael Economou
Date: 2025-05-01

Batch Processor - Simple but effective batch processing for speed and reliability.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, cast

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class BatchProcessor:
    """Simple batch processor for speed optimization."""

    def __init__(self, batch_size: int = 100, max_workers: int = 4):
        """Initialize batch processor with size, workers, and executor."""
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.stats = {
            "total_batches": 0,
            "total_items": 0,
            "total_time": 0.0,
            "successful_batches": 0,
            "failed_batches": 0,
        }

    def process_batches(self, items: list[Any], processor_func: Any) -> list[Any]:
        """Process items in batches with parallel execution."""
        if not items:
            return []

        start_time = time.time()

        # Split items into batches
        batches = self._split_into_batches(items)
        self.stats["total_batches"] = len(batches)
        self.stats["total_items"] = len(items)

        logger.debug(
            "[BatchProcessor] Processing %d items in %d batches",
            len(items),
            len(batches),
        )

        # Process batches
        results = []
        successful_batches = 0
        failed_batches = 0

        try:
            # Submit all batches to thread pool
            future_to_batch = {
                self.executor.submit(processor_func, batch): batch for batch in batches
            }

            # Collect results
            for future in as_completed(future_to_batch):
                batch = future_to_batch[future]
                try:
                    batch_result = future.result()
                    results.extend(batch_result)
                    successful_batches += 1
                except Exception as e:
                    logger.exception("[BatchProcessor] Batch failed")
                    failed_batches += 1
                    # Add original items as fallback
                    results.extend(batch)

        except Exception as e:
            logger.exception("[BatchProcessor] Processing failed")
            # Return original items as fallback
            results = items

        # Update stats
        self.stats["total_time"] = time.time() - start_time
        self.stats["successful_batches"] = successful_batches
        self.stats["failed_batches"] = failed_batches

        logger.debug("[BatchProcessor] Completed in %.3fs", self.stats["total_time"])
        return results

    def _split_into_batches(self, items: list[Any]) -> list[list[Any]]:
        """Split items into optimal batches."""
        batches = []
        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]
            batches.append(batch)
        return batches

    def get_stats(self) -> dict[str, Any]:
        """Get processing statistics."""
        if self.stats["total_batches"] > 0:
            avg_batch_time = self.stats["total_time"] / self.stats["total_batches"]
            success_rate = (self.stats["successful_batches"] / self.stats["total_batches"]) * 100
        else:
            avg_batch_time = 0
            success_rate = 100

        return {
            "total_batches": self.stats["total_batches"],
            "total_items": self.stats["total_items"],
            "total_time": self.stats["total_time"],
            "successful_batches": self.stats["successful_batches"],
            "failed_batches": self.stats["failed_batches"],
            "avg_batch_time": avg_batch_time,
            "success_rate": success_rate,
            "items_per_second": (
                self.stats["total_items"] / self.stats["total_time"]
                if self.stats["total_time"] > 0
                else 0
            ),
        }

    def reset_stats(self) -> None:
        """Reset processing statistics."""
        self.stats = {
            "total_batches": 0,
            "total_items": 0,
            "total_time": 0.0,
            "successful_batches": 0,
            "failed_batches": 0,
        }

    def shutdown(self) -> None:
        """Shutdown thread pool."""
        self.executor.shutdown(wait=True)


class SmartBatchProcessor(BatchProcessor):
    """Smart batch processor with dynamic optimization."""

    def __init__(
        self, initial_batch_size: int = 100, max_workers: int = 4, **kwargs: object
    ) -> None:
        """Initialize smart processor with dynamic batch size optimization."""
        super().__init__(initial_batch_size, max_workers)
        self.initial_batch_size = initial_batch_size
        self.performance_history: list[float] = []
        self.optimization_threshold = 0.5  # 500ms

    def process_batches_optimized(self, items: list[Any], processor_func: Any) -> list[Any]:
        """Process items with dynamic batch size optimization."""
        if not items:
            return []

        # Start with initial batch size
        current_batch_size = self.batch_size

        # Process first few batches to measure performance
        sample_size = min(3, max(1, len(items) // current_batch_size))
        sample_items = items[: sample_size * current_batch_size]

        start_time = time.time()
        sample_results = self.process_batches(sample_items, processor_func)
        sample_time = time.time() - start_time

        # Optimize batch size based on performance
        if sample_time > self.optimization_threshold:
            # Reduce batch size if too slow
            new_batch_size = max(10, current_batch_size // 2)
            logger.debug(
                "[SmartBatchProcessor] Reducing batch size from %d to %d",
                current_batch_size,
                new_batch_size,
            )
            self.batch_size = new_batch_size
        elif sample_time < self.optimization_threshold / 4:
            # Increase batch size if very fast
            new_batch_size = min(500, current_batch_size * 2)
            logger.debug(
                "[SmartBatchProcessor] Increasing batch size from %d to %d",
                current_batch_size,
                new_batch_size,
            )
            self.batch_size = new_batch_size

        # Process remaining items
        remaining_items = items[sample_size * current_batch_size :]
        if remaining_items:
            remaining_results = self.process_batches(remaining_items, processor_func)
            sample_results.extend(remaining_results)

        return sample_results

    def optimize_batch_size(self, target_time: float = 0.1) -> None:
        """Optimize batch size for target processing time."""
        if not self.performance_history:
            return

        # Calculate average performance
        avg_time = sum(self.performance_history) / len(self.performance_history)

        if avg_time > target_time * 1.5:
            # Too slow, reduce batch size
            self.batch_size = max(10, self.batch_size // 2)
            logger.debug("[SmartBatchProcessor] Optimized batch size to %d", self.batch_size)
        elif avg_time < target_time * 0.5:
            # Too fast, increase batch size
            self.batch_size = min(500, self.batch_size * 2)
            logger.debug("[SmartBatchProcessor] Optimized batch size to %d", self.batch_size)


class BatchProcessorFactory:
    """Factory for creating batch processors."""

    @staticmethod
    def create_processor(processor_type: str = "simple", **kwargs: object) -> BatchProcessor:
        """Create batch processor based on type."""
        # Cast kwargs to Any to allow unpacking into typed constructors
        # The type:ignore was here because object type doesn't match int parameters
        kwargs_any = cast("dict[str, Any]", kwargs)
        if processor_type == "smart":
            return SmartBatchProcessor(**kwargs_any)
        return BatchProcessor(**kwargs_any)

    @staticmethod
    def get_optimal_config(item_count: int, _item_type: str = "file") -> dict[str, Any]:
        """Get optimal configuration for item count and type."""
        if item_count < 100:
            return {"batch_size": 50, "max_workers": 2}
        if item_count < 1000:
            return {"batch_size": 100, "max_workers": 4}
        if item_count < 10000:
            return {"batch_size": 200, "max_workers": 6}
        return {"batch_size": 500, "max_workers": 8}
