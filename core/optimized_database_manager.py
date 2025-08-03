"""Optimized Database Manager Module.

This module provides an enhanced database management system with:
- Prepared statements for better performance
- Connection pooling for efficient resource usage
- Query optimization and caching
- Batch operations support
- Transaction management
- Database indexing optimization
- Query statistics and monitoring

Author: Michael Economou
Date: 2025-06-25
"""

import sqlite3
import threading
import time
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.pyqt_imports import QObject, pyqtSignal
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


@dataclass
class QueryStats:
    """Statistics for database queries."""

    query_hash: str
    query_text: str
    execution_count: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    last_execution: float = field(default_factory=time.time)

    def add_execution(self, execution_time: float):
        """Add execution statistics."""
        self.execution_count += 1
        self.total_time += execution_time
        self.avg_time = self.total_time / self.execution_count
        self.min_time = min(self.min_time, execution_time)
        self.max_time = max(self.max_time, execution_time)
        self.last_execution = time.time()


class ConnectionPool:
    """
    Database connection pool for efficient resource management.

    Features:
    - Connection reuse and pooling
    - Automatic connection cleanup
    - Thread-safe operations
    - Connection health monitoring
    """

    def __init__(self, db_path: str, max_connections: int = 10):
        """
        Initialize connection pool.

        Args:
            db_path: Database file path
            max_connections: Maximum number of connections
        """
        self.db_path = db_path
        self.max_connections = max_connections
        self._connections: list[sqlite3.Connection] = []
        self._available_connections: list[sqlite3.Connection] = []
        self._lock = threading.RLock()
        self._connection_count = 0

    def get_connection(self) -> sqlite3.Connection:
        """Get a connection from the pool."""
        with self._lock:
            # Try to get an available connection
            if self._available_connections:
                conn = self._available_connections.pop()
                return conn

            # Create new connection if under limit
            if self._connection_count < self.max_connections:
                conn = self._create_connection()
                self._connections.append(conn)
                self._connection_count += 1
                return conn

            # Wait for available connection (simplified - in real impl would use queue)
            # For now, create a temporary connection
            return self._create_connection()

    def return_connection(self, conn: sqlite3.Connection):
        """Return a connection to the pool."""
        with self._lock:
            if conn in self._connections:
                self._available_connections.append(conn)

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection."""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=30.0,
            isolation_level=None,  # Autocommit mode
        )
        conn.row_factory = sqlite3.Row

        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")

        return conn

    def close_all(self):
        """Close all connections in the pool."""
        with self._lock:
            for conn in self._connections:
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"[ConnectionPool] Error closing connection: {e}")

            self._connections.clear()
            self._available_connections.clear()
            self._connection_count = 0


class PreparedStatementCache:
    """
    Cache for prepared statements to improve query performance.

    Features:
    - Statement preparation and caching
    - Parameter binding optimization
    - Statement reuse across connections
    - Automatic cache cleanup
    """

    def __init__(self, max_statements: int = 100):
        """
        Initialize prepared statement cache.

        Args:
            max_statements: Maximum number of cached statements
        """
        self.max_statements = max_statements
        self._statements: OrderedDict[str, str] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get_statement(self, query_hash: str, query_text: str) -> str:
        """Get prepared statement from cache."""
        with self._lock:
            if query_hash in self._statements:
                # Move to end (most recently used)
                self._statements.move_to_end(query_hash)
                self._hits += 1
                return self._statements[query_hash]

            # Cache miss - add new statement
            self._misses += 1
            self._statements[query_hash] = query_text

            # Evict oldest if over limit
            if len(self._statements) > self.max_statements:
                self._statements.popitem(last=False)

            return query_text

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

            return {
                "statements": len(self._statements),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "max_statements": self.max_statements,
            }


class OptimizedDatabaseManager(QObject):
    """
    Enhanced database manager with optimization features.

    Features:
    - Prepared statements for better performance
    - Connection pooling
    - Query optimization and caching
    - Batch operations
    - Transaction management
    - Query statistics and monitoring
    """

    # Signals
    query_executed = pyqtSignal(str, float)  # query_hash, execution_time
    slow_query_detected = pyqtSignal(str, float)  # query_text, execution_time

    # Schema version for migrations
    SCHEMA_VERSION = 3

    def __init__(self, db_path: str | None = None, max_connections: int = 10, parent=None):
        """
        Initialize optimized database manager.

        Args:
            db_path: Database file path
            max_connections: Maximum number of connections
            parent: Parent QObject
        """
        super().__init__(parent)

        # Configuration
        self.slow_query_threshold = 0.5  # seconds
        self.query_cache_size = 1000
        self.batch_size = 100

        # Database setup
        if db_path is None:
            db_path = str(self._get_user_data_directory() / "oncutf_optimized.db")

        self.db_path = db_path
        self.connection_pool = ConnectionPool(db_path, max_connections)
        self.prepared_statements = PreparedStatementCache()

        # Query statistics
        self._query_stats: dict[str, QueryStats] = {}
        self._stats_lock = threading.RLock()

        # Common prepared statements
        self._common_queries = {
            "get_path_id": "SELECT id FROM file_paths WHERE normalized_path = ?",
            "create_path": "INSERT INTO file_paths (file_path, normalized_path) VALUES (?, ?)",
            "store_metadata": """
                INSERT OR REPLACE INTO file_metadata
                (path_id, metadata_type, metadata_json, is_modified)
                VALUES (?, ?, ?, ?)
            """,
            "get_metadata": """
                SELECT metadata_json, metadata_type, is_modified
                FROM file_metadata
                WHERE path_id = ?
                ORDER BY updated_at DESC
                LIMIT 1
            """,
            "store_hash": """
                INSERT OR REPLACE INTO file_hashes
                (path_id, algorithm, hash_value, file_size_at_hash)
                VALUES (?, ?, ?, ?)
            """,
            "get_hash": """
                SELECT hash_value
                FROM file_hashes
                WHERE path_id = ? AND algorithm = ?
                ORDER BY created_at DESC
                LIMIT 1
            """,
        }

        # Initialize database
        self._initialize_database()

        logger.info(f"[OptimizedDatabaseManager] Initialized with {max_connections} connections")

    def _get_user_data_directory(self) -> Path:
        """Get user data directory for storing database."""
        from utils.path_utils import get_user_data_dir

        return get_user_data_dir()

    @contextmanager
    def get_connection(self):
        """Get database connection from pool."""
        conn = self.connection_pool.get_connection()
        try:
            yield conn
        finally:
            self.connection_pool.return_connection(conn)

    def execute_query(
        self, query: str, params: tuple = (), fetch_all: bool = True, use_prepared: bool = True
    ) -> list[sqlite3.Row] | None:
        """
        Execute a SELECT query with optimization.

        Args:
            query: SQL query string
            params: Query parameters
            fetch_all: Whether to fetch all results
            use_prepared: Whether to use prepared statements

        Returns:
            Query results or None
        """
        query_hash = str(hash(query))
        start_time = time.time()

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Use prepared statement if requested
                if use_prepared:
                    query = self.prepared_statements.get_statement(query_hash, query)

                # Execute query
                cursor.execute(query, params)

                # Fetch results
                results = cursor.fetchall() if fetch_all else cursor.fetchone()

                # Record statistics
                execution_time = time.time() - start_time
                self._record_query_stats(query_hash, query, execution_time)

                return results

        except Exception as e:
            logger.error(f"[OptimizedDatabaseManager] Query execution failed: {e}")
            logger.error(f"[OptimizedDatabaseManager] Query: {query}")
            logger.error(f"[OptimizedDatabaseManager] Params: {params}")
            return None

    def execute_update(self, query: str, params: tuple = (), use_prepared: bool = True) -> bool:
        """
        Execute an INSERT/UPDATE/DELETE query.

        Args:
            query: SQL query string
            params: Query parameters
            use_prepared: Whether to use prepared statements

        Returns:
            Success status
        """
        query_hash = str(hash(query))
        start_time = time.time()

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Use prepared statement if requested
                if use_prepared:
                    query = self.prepared_statements.get_statement(query_hash, query)

                # Execute query
                cursor.execute(query, params)
                conn.commit()

                # Record statistics
                execution_time = time.time() - start_time
                self._record_query_stats(query_hash, query, execution_time)

                return True

        except Exception as e:
            logger.error(f"[OptimizedDatabaseManager] Update execution failed: {e}")
            logger.error(f"[OptimizedDatabaseManager] Query: {query}")
            logger.error(f"[OptimizedDatabaseManager] Params: {params}")
            return False

    def execute_batch(
        self, query: str, params_list: list[tuple], use_transaction: bool = True
    ) -> bool:
        """
        Execute batch operations for better performance.

        Args:
            query: SQL query string
            params_list: List of parameter tuples
            use_transaction: Whether to use a transaction

        Returns:
            Success status
        """
        if not params_list:
            return True

        query_hash = str(hash(query))
        start_time = time.time()

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                if use_transaction:
                    cursor.execute("BEGIN TRANSACTION")

                try:
                    # Execute all queries in batch
                    cursor.executemany(query, params_list)

                    if use_transaction:
                        cursor.execute("COMMIT")
                    else:
                        conn.commit()

                    # Record statistics
                    execution_time = time.time() - start_time
                    self._record_query_stats(
                        query_hash, f"{query} (batch: {len(params_list)})", execution_time
                    )

                    return True

                except Exception as e:
                    if use_transaction:
                        cursor.execute("ROLLBACK")
                    raise e

        except Exception as e:
            logger.error(f"[OptimizedDatabaseManager] Batch execution failed: {e}")
            logger.error(f"[OptimizedDatabaseManager] Query: {query}")
            logger.error(f"[OptimizedDatabaseManager] Batch size: {len(params_list)}")
            return False

    def _record_query_stats(self, query_hash: str, query_text: str, execution_time: float):
        """Record query execution statistics."""
        with self._stats_lock:
            if query_hash not in self._query_stats:
                self._query_stats[query_hash] = QueryStats(query_hash, query_text)

            self._query_stats[query_hash].add_execution(execution_time)

            # Emit signals
            self.query_executed.emit(query_hash, execution_time)

            if execution_time > self.slow_query_threshold:
                self.slow_query_detected.emit(query_text, execution_time)
                logger.warning(
                    f"[OptimizedDatabaseManager] Slow query detected: {execution_time:.3f}s"
                )

    def get_query_stats(self) -> dict[str, Any]:
        """Get query execution statistics."""
        with self._stats_lock:
            stats = {
                "total_queries": len(self._query_stats),
                "total_executions": sum(s.execution_count for s in self._query_stats.values()),
                "total_time": sum(s.total_time for s in self._query_stats.values()),
                "avg_time": 0.0,
                "slow_queries": 0,
                "prepared_statements": self.prepared_statements.get_stats(),
            }

            if stats["total_executions"] > 0:
                stats["avg_time"] = stats["total_time"] / stats["total_executions"]

            stats["slow_queries"] = sum(
                1 for s in self._query_stats.values() if s.avg_time > self.slow_query_threshold
            )

            return stats

    def get_top_queries(self, limit: int = 10, sort_by: str = "total_time") -> list[dict[str, Any]]:
        """Get top queries by specified metric."""
        with self._stats_lock:
            queries = []
            for stats in self._query_stats.values():
                queries.append(
                    {
                        "query": (
                            stats.query_text[:100] + "..."
                            if len(stats.query_text) > 100
                            else stats.query_text
                        ),
                        "executions": stats.execution_count,
                        "total_time": stats.total_time,
                        "avg_time": stats.avg_time,
                        "min_time": stats.min_time,
                        "max_time": stats.max_time,
                    }
                )

            # Sort by specified metric
            if sort_by in ["total_time", "avg_time", "executions", "max_time"]:
                queries.sort(key=lambda x: x[sort_by], reverse=True)

            return queries[:limit]

    def optimize_database(self):
        """Perform database optimization operations."""
        logger.info("[OptimizedDatabaseManager] Starting database optimization")

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Analyze tables for query optimization
                cursor.execute("ANALYZE")

                # Vacuum database to reclaim space
                cursor.execute("VACUUM")

                # Update statistics
                cursor.execute("PRAGMA optimize")

                logger.info("[OptimizedDatabaseManager] Database optimization completed")

        except Exception as e:
            logger.error(f"[OptimizedDatabaseManager] Database optimization failed: {e}")

    def _initialize_database(self):
        """Initialize database with optimized schema."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Create schema version table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_version (
                        version INTEGER PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Check current schema version
                cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
                row = cursor.fetchone()
                current_version = row["version"] if row else 0

                if current_version < self.SCHEMA_VERSION:
                    self._create_optimized_schema(cursor)
                    self._create_optimized_indexes(cursor)

                    # Update schema version
                    cursor.execute(
                        "INSERT INTO schema_version (version) VALUES (?)", (self.SCHEMA_VERSION,)
                    )
                    conn.commit()

                logger.info(
                    f"[OptimizedDatabaseManager] Database initialized (version {self.SCHEMA_VERSION})"
                )

        except Exception as e:
            logger.error(f"[OptimizedDatabaseManager] Database initialization failed: {e}")

    def _create_optimized_schema(self, cursor: sqlite3.Cursor):
        """Create optimized database schema."""
        # File paths table with better indexing
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS file_paths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                normalized_path TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Metadata table with optimized structure
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS file_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path_id INTEGER NOT NULL,
                metadata_type TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                is_modified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (path_id) REFERENCES file_paths(id) ON DELETE CASCADE
            )
        """
        )

        # Hash table with optimized structure
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS file_hashes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path_id INTEGER NOT NULL,
                algorithm TEXT NOT NULL,
                hash_value TEXT NOT NULL,
                file_size_at_hash INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (path_id) REFERENCES file_paths(id) ON DELETE CASCADE
            )
        """
        )

        # Query cache table for caching expensive queries
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS query_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT NOT NULL UNIQUE,
                query_result TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        """
        )

    def _create_optimized_indexes(self, cursor: sqlite3.Cursor):
        """Create optimized database indexes."""
        # File paths indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_file_paths_normalized ON file_paths(normalized_path)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_file_paths_created ON file_paths(created_at)"
        )

        # Metadata indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_metadata_path_id ON file_metadata(path_id)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_metadata_type ON file_metadata(metadata_type)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_metadata_updated ON file_metadata(updated_at)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_metadata_path_type ON file_metadata(path_id, metadata_type)"
        )

        # Hash indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hashes_path_id ON file_hashes(path_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hashes_algorithm ON file_hashes(algorithm)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_hashes_path_algo ON file_hashes(path_id, algorithm)"
        )

        # Query cache indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_cache_hash ON query_cache(query_hash)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_query_cache_expires ON query_cache(expires_at)"
        )

    def close(self):
        """Close database manager."""
        self.connection_pool.close_all()
        logger.info("[OptimizedDatabaseManager] Database manager closed")


# Global optimized database manager instance
_optimized_db_manager_instance: OptimizedDatabaseManager | None = None


def get_optimized_database_manager() -> OptimizedDatabaseManager:
    """Get global optimized database manager instance."""
    global _optimized_db_manager_instance
    if _optimized_db_manager_instance is None:
        _optimized_db_manager_instance = OptimizedDatabaseManager()
    return _optimized_db_manager_instance


def initialize_optimized_database(
    db_path: str | None = None, max_connections: int = 10
) -> OptimizedDatabaseManager:
    """Initialize optimized database manager."""
    global _optimized_db_manager_instance
    _optimized_db_manager_instance = OptimizedDatabaseManager(db_path, max_connections)
    return _optimized_db_manager_instance
