"""
RAM-Mode I/O Helper v1.0

Provides intelligent file I/O for RAM-mode operation:
- Write-through for critical files (prompts, configs, credentials)
- Write-back for non-critical files (logs, temp data)
- Automatic detection of RAM-mode vs disk-mode

Critical files are written to BOTH RAM and disk immediately.
Non-critical files are written to RAM only (streamed to disk by background sync).

Usage:
    from app.utils.rammode_io import write_file, read_file, is_critical_path

    # Automatically handles write-through for critical paths
    await write_file("/var/tristar/prompts/my-prompt.txt", content)

    # Check if path is critical
    if is_critical_path("/var/tristar/prompts/test.txt"):
        print("This file will be write-through!")
"""

import asyncio
import os
import shutil
from pathlib import Path
from typing import Optional, Union
import logging

# Try to use aiofiles for async I/O
try:
    import aiofiles
    _HAS_AIOFILES = True
except ImportError:
    _HAS_AIOFILES = False

logger = logging.getLogger("ailinux.rammode_io")

# Configuration
TMPFS_MOUNT = Path("/var/tristar")
PERSIST_DIR = Path("/opt/triforce/persist")

# Critical paths that need immediate disk persistence (write-through)
# These are written to BOTH RAM and disk immediately
CRITICAL_PATTERNS = [
    "prompts/",           # System prompts
    "agents/",            # Agent configurations
    "cli-config/",        # CLI credentials and configs
    "models/",            # Model configurations
    "autoprompts/",       # Auto-prompt configs
]

# Non-critical paths (write-back only, streamed by background sync)
NON_CRITICAL_PATTERNS = [
    "logs/",              # Logs (can be lost)
    "pids/",              # PID files (ephemeral)
    "jobs/",              # Job temp files
    "reports/",           # Generated reports
]


def is_rammode_active() -> bool:
    """Check if RAM-mode (tmpfs) is active"""
    try:
        import subprocess
        result = subprocess.run(
            ["mount"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return f"tmpfs on {TMPFS_MOUNT}" in result.stdout
    except Exception:
        return False


def is_critical_path(path: Union[str, Path]) -> bool:
    """
    Check if a path is critical and needs write-through.

    Args:
        path: File path to check

    Returns:
        True if path is critical (needs immediate disk write)
    """
    path_str = str(path)

    # Check if path is under TMPFS_MOUNT
    if not path_str.startswith(str(TMPFS_MOUNT)):
        return False

    # Get relative path
    rel_path = path_str[len(str(TMPFS_MOUNT)):].lstrip("/")

    # Check against critical patterns
    for pattern in CRITICAL_PATTERNS:
        if rel_path.startswith(pattern):
            return True

    return False


def get_persist_path(ram_path: Union[str, Path]) -> Path:
    """
    Convert a RAM path to its corresponding persist path.

    Args:
        ram_path: Path under /var/tristar

    Returns:
        Corresponding path under /opt/triforce/persist
    """
    ram_path = Path(ram_path)

    if not str(ram_path).startswith(str(TMPFS_MOUNT)):
        raise ValueError(f"Path not under TMPFS_MOUNT: {ram_path}")

    rel_path = ram_path.relative_to(TMPFS_MOUNT)
    return PERSIST_DIR / rel_path


async def write_file(
    path: Union[str, Path],
    content: Union[str, bytes],
    encoding: str = "utf-8",
    write_through: Optional[bool] = None,
) -> bool:
    """
    Write file with automatic write-through for critical paths.

    Args:
        path: File path to write
        content: Content to write (str or bytes)
        encoding: Encoding for string content
        write_through: Force write-through (None = auto-detect)

    Returns:
        True if successful
    """
    path = Path(path)

    # Determine if write-through is needed
    if write_through is None:
        write_through = is_critical_path(path)

    try:
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write to primary location (RAM if mounted, else disk)
        if isinstance(content, str):
            if _HAS_AIOFILES:
                async with aiofiles.open(path, "w", encoding=encoding) as f:
                    await f.write(content)
            else:
                path.write_text(content, encoding=encoding)
        else:
            if _HAS_AIOFILES:
                async with aiofiles.open(path, "wb") as f:
                    await f.write(content)
            else:
                path.write_bytes(content)

        # Write-through: also write to persist directory
        if write_through and is_rammode_active():
            persist_path = get_persist_path(path)
            persist_path.parent.mkdir(parents=True, exist_ok=True)

            if isinstance(content, str):
                if _HAS_AIOFILES:
                    async with aiofiles.open(persist_path, "w", encoding=encoding) as f:
                        await f.write(content)
                else:
                    persist_path.write_text(content, encoding=encoding)
            else:
                if _HAS_AIOFILES:
                    async with aiofiles.open(persist_path, "wb") as f:
                        await f.write(content)
                else:
                    persist_path.write_bytes(content)

            logger.debug(f"Write-through: {path} -> {persist_path}")

        return True

    except Exception as e:
        logger.error(f"Failed to write {path}: {e}")
        return False


async def read_file(
    path: Union[str, Path],
    encoding: str = "utf-8",
    binary: bool = False,
) -> Optional[Union[str, bytes]]:
    """
    Read file content.

    Args:
        path: File path to read
        encoding: Encoding for text mode
        binary: Read as bytes

    Returns:
        File content or None if not found
    """
    path = Path(path)

    if not path.exists():
        return None

    try:
        if binary:
            if _HAS_AIOFILES:
                async with aiofiles.open(path, "rb") as f:
                    return await f.read()
            else:
                return path.read_bytes()
        else:
            if _HAS_AIOFILES:
                async with aiofiles.open(path, "r", encoding=encoding) as f:
                    return await f.read()
            else:
                return path.read_text(encoding=encoding)

    except Exception as e:
        logger.error(f"Failed to read {path}: {e}")
        return None


async def delete_file(
    path: Union[str, Path],
    write_through: Optional[bool] = None,
) -> bool:
    """
    Delete file with write-through for critical paths.

    Args:
        path: File path to delete
        write_through: Force write-through (None = auto-detect)

    Returns:
        True if successful
    """
    path = Path(path)

    if write_through is None:
        write_through = is_critical_path(path)

    try:
        # Delete from primary location
        if path.exists():
            path.unlink()

        # Write-through: also delete from persist
        if write_through and is_rammode_active():
            persist_path = get_persist_path(path)
            if persist_path.exists():
                persist_path.unlink()
                logger.debug(f"Write-through delete: {persist_path}")

        return True

    except Exception as e:
        logger.error(f"Failed to delete {path}: {e}")
        return False


def sync_to_persist(path: Union[str, Path]) -> bool:
    """
    Synchronously copy a file/directory to persist.
    Use for immediate backup of important changes.

    Args:
        path: Path to sync

    Returns:
        True if successful
    """
    if not is_rammode_active():
        return True  # Not in RAM mode, nothing to sync

    path = Path(path)

    if not str(path).startswith(str(TMPFS_MOUNT)):
        return False

    try:
        persist_path = get_persist_path(path)

        if path.is_dir():
            if persist_path.exists():
                shutil.rmtree(persist_path)
            shutil.copytree(path, persist_path)
        else:
            persist_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, persist_path)

        logger.info(f"Synced to persist: {path}")
        return True

    except Exception as e:
        logger.error(f"Failed to sync {path}: {e}")
        return False


async def force_sync_all() -> bool:
    """
    Force sync all critical paths to persist.
    Call this before shutdown or on important changes.
    """
    if not is_rammode_active():
        return True

    success = True

    for pattern in CRITICAL_PATTERNS:
        source = TMPFS_MOUNT / pattern.rstrip("/")
        if source.exists():
            if not sync_to_persist(source):
                success = False

    return success


# Convenience functions for common operations

async def write_prompt(name: str, content: str) -> bool:
    """Write a system prompt (always write-through)"""
    path = TMPFS_MOUNT / "prompts" / f"{name}.txt"
    return await write_file(path, content, write_through=True)


async def read_prompt(name: str) -> Optional[str]:
    """Read a system prompt"""
    path = TMPFS_MOUNT / "prompts" / f"{name}.txt"
    return await read_file(path)


async def write_agent_config(agent_id: str, config: dict) -> bool:
    """Write agent config (always write-through)"""
    try:
        import json
        path = TMPFS_MOUNT / "agents" / agent_id / "config.json"
        content = json.dumps(config, indent=2, ensure_ascii=False)
        return await write_file(path, content, write_through=True)
    except Exception as e:
        logger.error(f"Failed to write agent config: {e}")
        return False


async def write_log(category: str, content: str) -> bool:
    """Write to log file (write-back only, not critical)"""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    path = TMPFS_MOUNT / "logs" / category / f"{today}.log"

    # Append mode
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if _HAS_AIOFILES:
            async with aiofiles.open(path, "a", encoding="utf-8") as f:
                await f.write(content + "\n")
        else:
            with open(path, "a", encoding="utf-8") as f:
                f.write(content + "\n")
        return True
    except Exception as e:
        logger.error(f"Failed to write log: {e}")
        return False
