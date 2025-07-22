"""
Database Connection Pool Module

This module provides efficient database connection management through
connection pooling to reduce overhead and improve performance.
"""

import sqlite3
import threading
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager
from queue import Queue, Empty, Full
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PooledConnection:
    """Wrapper for a pooled SQLite connection with usage tracking"""
    
    def __init__(self, connection: sqlite3.Connection, pool: 'ConnectionPool'):
        self.connection = connection
        self.pool = pool
        self.created_at = datetime.now()
        self.last_used = datetime.now()
        self.in_use = False
        self.use_count = 0
    
    def execute(self, sql: str, parameters: tuple = ()) -> sqlite3.Cursor:
        """Execute SQL with automatic usage tracking"""
        self.last_used = datetime.now()
        self.use_count += 1
        return self.connection.execute(sql, parameters)
    
    def executemany(self, sql: str, parameters) -> sqlite3.Cursor:
        """Execute many SQL statements with automatic usage tracking"""
        self.last_used = datetime.now()
        self.use_count += 1
        return self.connection.executemany(sql, parameters)
    
    def commit(self):
        """Commit transaction"""
        self.connection.commit()
    
    def rollback(self):
        """Rollback transaction"""
        self.connection.rollback()
    
    def close(self):
        """Close the underlying connection"""
        self.connection.close()
    
    def is_expired(self, max_age_minutes: int = 30) -> bool:
        """Check if connection is expired"""
        age = datetime.now() - self.created_at
        return age > timedelta(minutes=max_age_minutes)
    
    def is_stale(self, max_idle_minutes: int = 5) -> bool:
        """Check if connection has been idle too long"""
        idle_time = datetime.now() - self.last_used
        return idle_time > timedelta(minutes=max_idle_minutes)


class ConnectionPool:
    """SQLite connection pool for improved performance"""
    
    def __init__(self, 
                 db_path: Path,
                 pool_size: int = 10,
                 max_connections: int = 20,
                 connection_timeout: float = 30.0,
                 max_connection_age_minutes: int = 30,
                 max_idle_minutes: int = 5):
        """
        Initialize connection pool
        
        Args:
            db_path: Path to SQLite database
            pool_size: Initial number of connections to create
            max_connections: Maximum number of connections allowed
            connection_timeout: Timeout for getting connection from pool
            max_connection_age_minutes: Maximum age of connections before replacement
            max_idle_minutes: Maximum idle time before connection cleanup
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.max_connection_age_minutes = max_connection_age_minutes
        self.max_idle_minutes = max_idle_minutes
        
        self._pool = Queue(maxsize=max_connections)
        self._all_connections = set()
        self._lock = threading.RLock()
        self._stats = {
            'created': 0,
            'borrowed': 0,
            'returned': 0,
            'expired': 0,
            'failed': 0
        }
        
        # Initialize pool with initial connections
        self._initialize_pool()
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_connections, daemon=True)
        self._cleanup_thread.start()
    
    def _initialize_pool(self):
        """Create initial pool connections"""
        for _ in range(self.pool_size):
            try:
                conn = self._create_connection()
                if conn:
                    self._pool.put(conn, block=False)
            except Full:
                break
            except Exception as e:
                logger.error(f"Failed to initialize connection: {e}")
    
    def _create_connection(self) -> Optional[PooledConnection]:
        """Create a new database connection"""
        try:
            # Import here to avoid circular imports
            from .init_db import init_db
            
            raw_conn = init_db(self.db_path)
            
            # Configure connection for optimal performance
            raw_conn.execute("PRAGMA journal_mode=WAL")
            raw_conn.execute("PRAGMA synchronous=NORMAL") 
            raw_conn.execute("PRAGMA cache_size=2000")
            raw_conn.execute("PRAGMA temp_store=MEMORY")
            raw_conn.execute("PRAGMA mmap_size=268435456")  # 256MB
            
            pooled_conn = PooledConnection(raw_conn, self)
            
            with self._lock:
                self._all_connections.add(pooled_conn)
                self._stats['created'] += 1
            
            logger.debug(f"Created new pooled connection (total: {len(self._all_connections)})")
            return pooled_conn
            
        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            with self._lock:
                self._stats['failed'] += 1
            return None
    
    def get_connection(self) -> Optional[PooledConnection]:
        """Get a connection from the pool"""
        try:
            # Try to get from pool first
            try:
                conn = self._pool.get(block=True, timeout=self.connection_timeout)
                
                # Check if connection is still valid and not expired
                if conn.is_expired(self.max_connection_age_minutes):
                    logger.debug("Connection expired, creating new one")
                    self._close_connection(conn)
                    conn = self._create_connection()
                
                if conn:
                    conn.in_use = True
                    with self._lock:
                        self._stats['borrowed'] += 1
                    
                return conn
                
            except Empty:
                # Pool is empty, try to create new connection if under limit
                with self._lock:
                    if len(self._all_connections) < self.max_connections:
                        conn = self._create_connection()
                        if conn:
                            conn.in_use = True
                            self._stats['borrowed'] += 1
                        return conn
                
                logger.warning("Connection pool exhausted and max connections reached")
                return None
                
        except Exception as e:
            logger.error(f"Error getting connection from pool: {e}")
            return None
    
    def return_connection(self, conn: PooledConnection):
        """Return a connection to the pool"""
        if not conn:
            return
        
        try:
            # Reset connection state
            conn.in_use = False
            
            # Check if connection is still valid
            if conn.is_expired(self.max_connection_age_minutes):
                logger.debug("Closing expired connection")
                self._close_connection(conn)
                return
            
            # Return to pool if space available
            try:
                self._pool.put(conn, block=False)
                with self._lock:
                    self._stats['returned'] += 1
                logger.debug("Connection returned to pool")
                
            except Full:
                # Pool is full, close the connection
                logger.debug("Pool full, closing connection")
                self._close_connection(conn)
                
        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}")
            self._close_connection(conn)
    
    def _close_connection(self, conn: PooledConnection):
        """Close and remove connection from tracking"""
        try:
            conn.close()
        except Exception as e:
            logger.warning(f"Error closing connection: {e}")
        finally:
            with self._lock:
                self._all_connections.discard(conn)
                self._stats['expired'] += 1
    
    def _cleanup_connections(self):
        """Background thread to clean up stale connections"""
        import time
        
        while True:
            try:
                time.sleep(60)  # Run cleanup every minute
                
                with self._lock:
                    stale_connections = [
                        conn for conn in self._all_connections 
                        if not conn.in_use and conn.is_stale(self.max_idle_minutes)
                    ]
                
                for conn in stale_connections:
                    logger.debug("Cleaning up stale connection")
                    self._close_connection(conn)
                    
                    # Remove from pool if present
                    try:
                        # Create a new temporary queue to filter out the stale connection
                        temp_queue = Queue(maxsize=self.max_connections)
                        while not self._pool.empty():
                            try:
                                pool_conn = self._pool.get_nowait()
                                if pool_conn != conn:
                                    temp_queue.put_nowait(pool_conn)
                            except Empty:
                                break
                        
                        # Replace the pool with the filtered queue
                        self._pool = temp_queue
                        
                    except Exception as e:
                        logger.warning(f"Error during pool cleanup: {e}")
                
            except Exception as e:
                logger.error(f"Error in connection cleanup thread: {e}")
    
    @contextmanager
    def get_db_connection(self):
        """Context manager for getting and automatically returning connections"""
        conn = self.get_connection()
        if not conn:
            raise RuntimeError("Could not obtain database connection")
        
        try:
            yield conn
        finally:
            self.return_connection(conn)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        with self._lock:
            return {
                **self._stats,
                'pool_size': self._pool.qsize(),
                'total_connections': len(self._all_connections),
                'max_connections': self.max_connections,
                'connections_in_use': sum(1 for c in self._all_connections if c.in_use)
            }
    
    def close_all(self):
        """Close all connections in the pool"""
        logger.info("Closing all pooled connections")
        
        # Close all connections in pool
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Empty:
                break
        
        # Close all tracked connections
        with self._lock:
            for conn in list(self._all_connections):
                conn.close()
            self._all_connections.clear()


# Global connection pool instance
_connection_pools = {}
_pool_lock = threading.Lock()


def get_connection_pool(db_path: Path) -> ConnectionPool:
    """Get or create a connection pool for the given database path"""
    db_key = str(db_path.resolve())
    
    with _pool_lock:
        if db_key not in _connection_pools:
            logger.info(f"Creating connection pool for database: {db_path}")
            _connection_pools[db_key] = ConnectionPool(db_path)
        
        return _connection_pools[db_key]


@contextmanager
def get_db_connection(db_path: Path):
    """Get a database connection from the appropriate pool"""
    pool = get_connection_pool(db_path)
    with pool.get_db_connection() as conn:
        yield conn


def close_all_pools():
    """Close all connection pools (useful for shutdown)"""
    with _pool_lock:
        for pool in _connection_pools.values():
            pool.close_all()
        _connection_pools.clear()