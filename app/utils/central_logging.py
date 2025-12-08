"""
Central Logging Configuration for AILinux/TriForce
===================================================

All logs are stored in ./triforce/logs/

Log Structure:
- triforce/logs/all.log          - ALL logs combined
- triforce/logs/auth.log         - Authentication events
- triforce/logs/mcp.log          - MCP protocol traffic
- triforce/logs/api.log          - REST API traffic
- triforce/logs/llm.log          - LLM/AI calls
- triforce/logs/agents.log       - Agent events
- triforce/logs/errors.log       - Errors only
- triforce/logs/security.log     - Security events
- triforce/logs/system.log       - System events
"""

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Optional

# Base log directory
_BASE_DIR = Path(__file__).parent.parent.parent
LOG_DIR = _BASE_DIR / "triforce" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Log format
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
LOG_FORMAT_DETAILED = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(filename)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Rotation settings
MAX_BYTES = 50 * 1024 * 1024  # 50 MB
BACKUP_COUNT = 10

# Track if already initialized
_initialized = False
_root_handler = None


class TriForceFormatter(logging.Formatter):
    """Custom formatter with color support for console and clean format for files."""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def __init__(self, use_colors: bool = False):
        super().__init__(LOG_FORMAT, DATE_FORMAT)
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        # Add custom fields if not present
        if not hasattr(record, 'client_ip'):
            record.client_ip = '-'

        formatted = super().format(record)

        if self.use_colors and record.levelname in self.COLORS:
            return f"{self.COLORS[record.levelname]}{formatted}{self.RESET}"
        return formatted


def get_file_handler(
    filename: str,
    level: int = logging.DEBUG,
    max_bytes: int = MAX_BYTES,
    backup_count: int = BACKUP_COUNT
) -> RotatingFileHandler:
    """Create a rotating file handler."""
    handler = RotatingFileHandler(
        LOG_DIR / filename,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT_DETAILED, DATE_FORMAT))
    return handler


def get_daily_handler(
    filename: str,
    level: int = logging.DEBUG
) -> TimedRotatingFileHandler:
    """Create a daily rotating file handler."""
    handler = TimedRotatingFileHandler(
        LOG_DIR / filename,
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT_DETAILED, DATE_FORMAT))
    return handler


def setup_central_logging(
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    enable_console: bool = True
) -> None:
    """
    Initialize central logging for the entire application.
    Call this once at application startup.
    """
    global _initialized, _root_handler

    if _initialized:
        return

    # Get root logger
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Clear existing handlers
    root.handlers.clear()

    # === File Handlers ===

    # 1. ALL logs combined
    all_handler = get_file_handler("all.log", logging.DEBUG)
    root.addHandler(all_handler)
    _root_handler = all_handler

    # 2. Errors only
    error_handler = get_file_handler("errors.log", logging.ERROR)
    root.addHandler(error_handler)

    # === Console Handler ===
    if enable_console:
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(console_level)
        console.setFormatter(TriForceFormatter(use_colors=True))
        root.addHandler(console)

    # === Category-specific loggers ===

    # Auth logger
    auth_logger = logging.getLogger("ailinux.auth")
    auth_logger.addHandler(get_file_handler("auth.log"))
    auth_logger.propagate = True  # Also goes to all.log

    # MCP logger
    mcp_logger = logging.getLogger("ailinux.mcp")
    mcp_logger.addHandler(get_file_handler("mcp.log"))
    mcp_logger.propagate = True

    # API logger
    api_logger = logging.getLogger("ailinux.api")
    api_logger.addHandler(get_file_handler("api.log"))
    api_logger.propagate = True

    # LLM logger
    llm_logger = logging.getLogger("ailinux.llm")
    llm_logger.addHandler(get_file_handler("llm.log"))
    llm_logger.propagate = True

    # Agents logger
    agents_logger = logging.getLogger("ailinux.agents")
    agents_logger.addHandler(get_file_handler("agents.log"))
    agents_logger.propagate = True

    # Security logger
    security_logger = logging.getLogger("ailinux.security")
    security_logger.addHandler(get_file_handler("security.log"))
    security_logger.propagate = True

    # System logger
    system_logger = logging.getLogger("ailinux.system")
    system_logger.addHandler(get_file_handler("system.log"))
    system_logger.propagate = True

    # TriStar logger
    tristar_logger = logging.getLogger("ailinux.tristar")
    tristar_logger.addHandler(get_file_handler("tristar.log"))
    tristar_logger.propagate = True

    # TriForce logger
    triforce_logger = logging.getLogger("ailinux.triforce")
    triforce_logger.addHandler(get_file_handler("triforce.log"))
    triforce_logger.propagate = True

    # === Third-party loggers ===

    # Uvicorn
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers.clear()
    uvicorn_logger.addHandler(get_file_handler("uvicorn.log"))
    uvicorn_logger.propagate = True

    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers.clear()
    uvicorn_access.addHandler(get_file_handler("access.log"))
    uvicorn_access.propagate = True

    # FastAPI
    fastapi_logger = logging.getLogger("fastapi")
    fastapi_logger.propagate = True

    # HTTPX
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(logging.WARNING)  # Reduce noise

    # Mark as initialized
    _initialized = True

    # Log startup
    root.info("=" * 60)
    root.info("TriForce Central Logging initialized")
    root.info(f"Log directory: {LOG_DIR}")
    root.info("=" * 60)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the ailinux prefix.

    Usage:
        logger = get_logger("mcp.handler")
        # Returns logger named "ailinux.mcp.handler"
    """
    if not _initialized:
        setup_central_logging()

    if not name.startswith("ailinux."):
        name = f"ailinux.{name}"

    return logging.getLogger(name)


# Convenience loggers
def get_auth_logger() -> logging.Logger:
    return get_logger("auth")

def get_mcp_logger() -> logging.Logger:
    return get_logger("mcp")

def get_api_logger() -> logging.Logger:
    return get_logger("api")

def get_llm_logger() -> logging.Logger:
    return get_logger("llm")

def get_agents_logger() -> logging.Logger:
    return get_logger("agents")

def get_security_logger() -> logging.Logger:
    return get_logger("security")

def get_system_logger() -> logging.Logger:
    return get_logger("system")

def get_tristar_logger() -> logging.Logger:
    return get_logger("tristar")

def get_triforce_logger() -> logging.Logger:
    return get_logger("triforce")


# Auto-initialize when imported (optional, can be disabled)
# setup_central_logging()
