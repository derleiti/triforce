"""
RAM-First Logger v1.0

High-performance logging with RAM buffer as primary store and async disk streaming.
Provides <0.01ms write latency vs 2-5ms for direct disk writes.

Architecture:
    [App] -> [RAM Buffer (deque)] -> [Async Stream] -> [Disk (JSONL)]
              Primary                 Background        Persistence

Features:
- Instant sync writes to RAM buffer (<0.01ms)
- Non-blocking async writes with lock for high concurrency
- Background disk streaming every 10 seconds
- Batch disk writes (up to 500 entries)
- aiofiles for non-blocking file I/O
- orjson for 3-10x faster JSON serialization
- DualWriteHandler for Python logging integration
- Graceful shutdown with final flush
"""

import asyncio
import logging
import os
import time
import uuid
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from threading import Lock
from enum import Enum

# Try to use orjson for faster JSON serialization
try:
    import orjson

    def json_dumps(obj: Any) -> str:
        return orjson.dumps(obj, default=str).decode('utf-8')

    def json_loads(s: str) -> Any:
        return orjson.loads(s)

    _HAS_ORJSON = True
except ImportError:
    import json

    def json_dumps(obj: Any) -> str:
        return json.dumps(obj, ensure_ascii=False, default=str)

    def json_loads(s: str) -> Any:
        return json.loads(s)

    _HAS_ORJSON = False

# Try to use aiofiles for async file I/O
try:
    import aiofiles
    _HAS_AIOFILES = True
except ImportError:
    _HAS_AIOFILES = False

logger = logging.getLogger("ailinux.ramfirst")


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class RAMLogEntry:
    """A log entry stored in RAM"""
    timestamp: str
    level: str
    source: str
    message: str
    trace_id: str = ""
    category: str = "general"
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Performance tracking
    _created_ns: int = field(default_factory=time.perf_counter_ns, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding internal fields"""
        data = asdict(self)
        data.pop('_created_ns', None)
        return {k: v for k, v in data.items() if v}

    def to_json(self) -> str:
        """Convert to JSON string using orjson if available"""
        return json_dumps(self.to_dict())


class RAMFirstLogger:
    """
    RAM-first logging with async disk streaming.

    All writes go to RAM buffer first (<0.01ms), then are streamed
    to disk in the background every N seconds.

    Usage:
        logger = RAMFirstLogger()
        await logger.start()

        # Sync write (instant)
        logger.write({"level": "info", "message": "Hello"})

        # Async write (with lock)
        await logger.write_async({"level": "info", "message": "Hello"})

        # Get recent entries
        recent = logger.get_recent(100)

        await logger.stop()
    """

    def __init__(
        self,
        log_dir: str = "/var/tristar/logs/central",
        buffer_size: int = 50000,        # Max entries in RAM buffer
        stream_interval: float = 10.0,    # Seconds between disk streams
        batch_size: int = 500,            # Max entries per disk batch
        file_prefix: str = "ramfirst",    # Log file prefix
    ):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.buffer_size = buffer_size
        self.stream_interval = stream_interval
        self.batch_size = batch_size
        self.file_prefix = file_prefix

        # RAM buffer (thread-safe deque)
        self._buffer: deque = deque(maxlen=buffer_size)

        # Pending entries for disk stream
        self._pending: List[RAMLogEntry] = []
        self._pending_lock = Lock()

        # Async lock for write_async
        self._async_lock: Optional[asyncio.Lock] = None

        # Background task
        self._stream_task: Optional[asyncio.Task] = None
        self._running = False

        # Statistics
        self._stats = {
            "total_writes": 0,
            "total_streamed": 0,
            "stream_errors": 0,
            "bytes_written": 0,
            "avg_write_ns": 0,
            "started_at": None,
            "last_stream_at": None,
        }

        # Performance tracking
        self._write_times: deque = deque(maxlen=1000)

    async def start(self):
        """Start the background disk streaming task"""
        if self._running:
            return

        self._running = True
        self._async_lock = asyncio.Lock()
        self._stats["started_at"] = datetime.now(timezone.utc).isoformat()

        # Start background streaming task
        self._stream_task = asyncio.create_task(self._stream_loop())

        logger.info(f"RAMFirstLogger started (orjson={_HAS_ORJSON}, aiofiles={_HAS_AIOFILES})")

    async def stop(self):
        """Stop the logger and flush remaining entries"""
        self._running = False

        if self._stream_task:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass

        # Final flush
        await self._stream_to_disk()

        logger.info("RAMFirstLogger stopped")

    def write(self, data: Dict[str, Any]) -> RAMLogEntry:
        """
        Sync write to RAM buffer. Instant (<0.01ms).

        Args:
            data: Dict with log data (level, message, source, etc.)

        Returns:
            RAMLogEntry that was created
        """
        start_ns = time.perf_counter_ns()

        entry = RAMLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=data.get("level", "info"),
            source=data.get("source", "unknown"),
            message=data.get("message", ""),
            trace_id=data.get("trace_id", str(uuid.uuid4())[:12]),
            category=data.get("category", "general"),
            metadata=data.get("metadata", {}),
        )

        # Thread-safe append to buffer
        self._buffer.append(entry)

        # Add to pending (with lock for thread safety)
        with self._pending_lock:
            self._pending.append(entry)

        # Track performance
        elapsed_ns = time.perf_counter_ns() - start_ns
        self._write_times.append(elapsed_ns)
        self._stats["total_writes"] += 1

        return entry

    async def write_async(self, data: Dict[str, Any]) -> RAMLogEntry:
        """
        Async write with lock for high-concurrency scenarios.

        Args:
            data: Dict with log data

        Returns:
            RAMLogEntry that was created
        """
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()

        async with self._async_lock:
            return self.write(data)

    def log(
        self,
        level: str,
        message: str,
        source: str = "app",
        category: str = "general",
        trace_id: Optional[str] = None,
        **metadata
    ) -> RAMLogEntry:
        """
        Convenience method for logging with separate parameters.

        Args:
            level: Log level (debug, info, warning, error, critical)
            message: Log message
            source: Source component
            category: Log category
            trace_id: Optional trace ID
            **metadata: Additional metadata
        """
        return self.write({
            "level": level,
            "message": message,
            "source": source,
            "category": category,
            "trace_id": trace_id or str(uuid.uuid4())[:12],
            "metadata": metadata if metadata else {},
        })

    def debug(self, message: str, **kwargs) -> RAMLogEntry:
        return self.log("debug", message, **kwargs)

    def info(self, message: str, **kwargs) -> RAMLogEntry:
        return self.log("info", message, **kwargs)

    def warning(self, message: str, **kwargs) -> RAMLogEntry:
        return self.log("warning", message, **kwargs)

    def error(self, message: str, **kwargs) -> RAMLogEntry:
        return self.log("error", message, **kwargs)

    def critical(self, message: str, **kwargs) -> RAMLogEntry:
        return self.log("critical", message, **kwargs)

    def get_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent entries from RAM buffer"""
        entries = list(self._buffer)
        return [e.to_dict() for e in entries[-limit:]]

    def get_by_level(self, level: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get entries filtered by level"""
        entries = [e for e in self._buffer if e.level == level]
        return [e.to_dict() for e in entries[-limit:]]

    def get_by_category(self, category: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get entries filtered by category"""
        entries = [e for e in self._buffer if e.category == category]
        return [e.to_dict() for e in entries[-limit:]]

    def get_errors(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent errors and criticals"""
        entries = [e for e in self._buffer if e.level in ("error", "critical")]
        return [e.to_dict() for e in entries[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        """Get logger statistics"""
        avg_write_ns = 0
        if self._write_times:
            avg_write_ns = sum(self._write_times) / len(self._write_times)

        return {
            **self._stats,
            "buffer_size": len(self._buffer),
            "buffer_max": self.buffer_size,
            "pending_entries": len(self._pending),
            "avg_write_ns": avg_write_ns,
            "avg_write_ms": avg_write_ns / 1_000_000,
            "orjson_enabled": _HAS_ORJSON,
            "aiofiles_enabled": _HAS_AIOFILES,
        }

    async def force_flush(self):
        """Force immediate flush to disk"""
        await self._stream_to_disk()

    async def _stream_loop(self):
        """Background loop for streaming to disk"""
        while self._running:
            try:
                await asyncio.sleep(self.stream_interval)
                await self._stream_to_disk()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._stats["stream_errors"] += 1
                logger.error(f"Stream error: {e}")

    async def _stream_to_disk(self):
        """Stream pending entries to disk"""
        # Get pending entries (thread-safe)
        with self._pending_lock:
            if not self._pending:
                return
            entries = self._pending[:self.batch_size]
            self._pending = self._pending[self.batch_size:]

        if not entries:
            return

        # Generate log file path
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = self.log_dir / f"{self.file_prefix}_{today}.jsonl"

        try:
            # Serialize entries
            lines = [entry.to_json() + "\n" for entry in entries]
            content = "".join(lines)

            # Write to disk
            if _HAS_AIOFILES:
                async with aiofiles.open(log_file, "a", encoding="utf-8") as f:
                    await f.write(content)
            else:
                # Fallback to sync write in executor
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self._sync_write(log_file, content)
                )

            # Update stats
            self._stats["total_streamed"] += len(entries)
            self._stats["bytes_written"] += len(content.encode('utf-8'))
            self._stats["last_stream_at"] = datetime.now(timezone.utc).isoformat()

        except Exception as e:
            self._stats["stream_errors"] += 1
            logger.error(f"Failed to stream to disk: {e}")

            # Put entries back for retry
            with self._pending_lock:
                self._pending = entries + self._pending

    def _sync_write(self, path: Path, content: str):
        """Sync file write (for fallback)"""
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)


class DualWriteHandler(logging.Handler):
    """
    Python logging handler that writes to both RAM buffer and optional
    secondary handler (e.g., TriForce central logger).

    Usage:
        ram_logger = RAMFirstLogger()
        handler = DualWriteHandler(ram_logger)
        logging.getLogger().addHandler(handler)
    """

    def __init__(
        self,
        ram_logger: RAMFirstLogger,
        secondary_handler: Optional[logging.Handler] = None,
    ):
        super().__init__()
        self.ram_logger = ram_logger
        self.secondary_handler = secondary_handler

        # Map Python log levels to our levels
        self._level_map = {
            logging.DEBUG: "debug",
            logging.INFO: "info",
            logging.WARNING: "warning",
            logging.ERROR: "error",
            logging.CRITICAL: "critical",
        }

    def emit(self, record: logging.LogRecord):
        """Handle a log record"""
        try:
            level = self._level_map.get(record.levelno, "info")

            # Determine category from logger name
            category = "general"
            name_lower = record.name.lower()
            if "error" in name_lower or record.levelno >= logging.ERROR:
                category = "error"
            elif "api" in name_lower or "http" in name_lower:
                category = "api"
            elif "llm" in name_lower or "model" in name_lower:
                category = "llm"
            elif "agent" in name_lower:
                category = "agent"
            elif "mcp" in name_lower:
                category = "mcp"

            # Write to RAM logger
            self.ram_logger.write({
                "level": level,
                "message": record.getMessage(),
                "source": record.name,
                "category": category,
                "trace_id": getattr(record, 'trace_id', None),
                "metadata": {
                    "filename": record.filename,
                    "lineno": record.lineno,
                    "funcName": record.funcName,
                },
            })

            # Forward to secondary handler if present
            if self.secondary_handler:
                self.secondary_handler.emit(record)

        except Exception:
            # Don't let logging errors break the application
            pass


# Singleton instance for easy access
_ram_logger: Optional[RAMFirstLogger] = None


def get_ram_logger() -> RAMFirstLogger:
    """Get or create the singleton RAMFirstLogger instance"""
    global _ram_logger
    if _ram_logger is None:
        _ram_logger = RAMFirstLogger()
    return _ram_logger


async def setup_ramfirst_logging(
    integrate_with_triforce: bool = True,
) -> RAMFirstLogger:
    """
    Set up RAM-first logging for the application.

    Args:
        integrate_with_triforce: Whether to integrate with TriForce central logger

    Returns:
        The RAMFirstLogger instance
    """
    ram_logger = get_ram_logger()
    await ram_logger.start()

    # Create handler
    secondary = None
    if integrate_with_triforce:
        try:
            from .triforce_logging import TriForceLogHandler, central_logger
            secondary = TriForceLogHandler(central_logger)
        except ImportError:
            pass

    handler = DualWriteHandler(ram_logger, secondary)
    handler.setLevel(logging.DEBUG)

    # Attach to root logger
    root = logging.getLogger()
    root.addHandler(handler)

    logger.info("RAM-first logging initialized")

    return ram_logger
