"""
Client Logs Route - DevOps Syslog Endpoint
===========================================
Empfängt Logs von AILinux Clients für zentrales Monitoring.

Endpoints:
- POST /v1/client/logs - Log-Batch empfangen
- GET /v1/client/logs - Logs abfragen (Admin)
- GET /v1/client/logs/stats - Statistiken
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
import logging
from collections import deque
from threading import Lock

from app.routes.client_auth import get_current_client, require_admin


router = APIRouter(prefix="/v1/client", tags=["client-logs"])
logger = logging.getLogger("ailinux.client_logs")


# === In-Memory Log Buffer ===
class ClientLogBuffer:
    """Ring-Buffer für Client-Logs"""
    
    def __init__(self, max_size: int = 50000):
        self._buffer: deque = deque(maxlen=max_size)
        self._lock = Lock()
        self._stats = {
            "total_received": 0,
            "by_level": {"DEBUG": 0, "INFO": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0},
            "by_client": {},
            "errors_last_hour": 0,
            "started_at": datetime.utcnow().isoformat()
        }
    
    def add(self, entries: List[Dict], client_info: Dict = None):
        """Fügt Log-Einträge hinzu"""
        with self._lock:
            client_id = client_info.get("client_id", "unknown") if client_info else "unknown"
            
            for entry in entries:
                # Parse JSON-String falls nötig
                if isinstance(entry, str):
                    try:
                        entry = json.loads(entry)
                    except json.JSONDecodeError:
                        entry = {"message": entry, "level": "INFO"}
                
                # Timestamp hinzufügen falls nicht vorhanden
                if "received_at" not in entry:
                    entry["received_at"] = datetime.utcnow().isoformat() + "Z"
                
                entry["client_id"] = client_id
                entry["client_info"] = client_info
                
                self._buffer.append(entry)
                self._stats["total_received"] += 1
                
                # Level-Stats
                level = entry.get("level", "INFO").upper()
                if level in self._stats["by_level"]:
                    self._stats["by_level"][level] += 1
                
                # Client-Stats
                if client_id not in self._stats["by_client"]:
                    self._stats["by_client"][client_id] = {"count": 0, "last_seen": None}
                self._stats["by_client"][client_id]["count"] += 1
                self._stats["by_client"][client_id]["last_seen"] = datetime.utcnow().isoformat()
    
    def get_recent(
        self,
        limit: int = 100,
        level: str = None,
        client_id: str = None,
        since: datetime = None
    ) -> List[Dict]:
        """Holt gefilterte Logs"""
        with self._lock:
            result = []
            
            for entry in reversed(self._buffer):
                if len(result) >= limit:
                    break
                
                # Filter
                if level and entry.get("level", "").upper() != level.upper():
                    continue
                if client_id and entry.get("client_id") != client_id:
                    continue
                if since:
                    try:
                        entry_time = datetime.fromisoformat(
                            entry.get("timestamp", entry.get("received_at", "")).replace("Z", "+00:00")
                        )
                        if entry_time < since:
                            continue
                    except (ValueError, TypeError):
                        pass
                
                result.append(entry)
            
            return result
    
    def get_stats(self) -> Dict:
        """Gibt Statistiken zurück"""
        with self._lock:
            stats = self._stats.copy()
            stats["buffer_size"] = len(self._buffer)
            stats["buffer_max"] = self._buffer.maxlen
            stats["active_clients"] = len(self._stats["by_client"])
            return stats
    
    def get_errors(self, hours: int = 24) -> List[Dict]:
        """Holt Errors der letzten X Stunden"""
        since = datetime.utcnow() - timedelta(hours=hours)
        return self.get_recent(limit=500, level="ERROR", since=since)
    
    def clear(self):
        """Leert Buffer"""
        with self._lock:
            self._buffer.clear()


# Singleton Buffer
log_buffer = ClientLogBuffer()


# === Pydantic Models ===

class ClientLogEntry(BaseModel):
    timestamp: Optional[str] = None
    level: str = "INFO"
    source: Optional[str] = None
    message: str
    client_id: Optional[str] = None
    user_id: Optional[str] = None
    tier: Optional[str] = None
    version: Optional[str] = None
    platform: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    traceback: Optional[str] = None


class ClientLogBatch(BaseModel):
    logs: List[Any] = Field(..., description="Log entries (JSON strings or objects)")
    client_info: Optional[Dict[str, Any]] = None


class LogQueryParams(BaseModel):
    limit: int = Field(100, ge=1, le=1000)
    level: Optional[str] = None
    client_id: Optional[str] = None
    hours: Optional[int] = Field(None, ge=1, le=168)


# === Endpoints ===

@router.post("/logs", status_code=202)
async def receive_client_logs(
    batch: ClientLogBatch,
    user: dict = Depends(get_current_client)
):
    """
    Empfängt Log-Batch von Client.
    
    Erwartet JSON:
    {
        "logs": ["json_string", {"level": "ERROR", "message": "..."}],
        "client_info": {"client_id": "abc", "version": "4.2.0", ...}
    }
    """
    try:
        # User-Info in client_info
        client_info = batch.client_info or {}
        client_info["user_id"] = user.get("client_id")
        client_info["tier"] = user.get("role", "guest")
        
        log_buffer.add(batch.logs, client_info)
        
        # Bei Errors: zusätzlich loggen
        for entry in batch.logs:
            if isinstance(entry, str):
                try:
                    entry = json.loads(entry)
                except:
                    continue
            
            level = entry.get("level", "").upper()
            if level in ("ERROR", "CRITICAL"):
                logger.warning(
                    f"CLIENT_{level}: {entry.get('message', 'no message')} "
                    f"[client={client_info.get('client_id')}, user={client_info.get('user_id')}]"
                )
        
        return {
            "status": "accepted",
            "received": len(batch.logs)
        }
        
    except Exception as e:
        logger.error(f"Log receive error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs")
async def get_client_logs(
    limit: int = Query(100, ge=1, le=1000),
    level: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    hours: Optional[int] = Query(None, ge=1, le=168),
    user: dict = Depends(require_admin)
):
    """
    Holt Client-Logs (Admin only).
    
    Query-Parameter:
    - limit: Max Anzahl (default: 100)
    - level: Filter nach Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - client_id: Filter nach Client
    - hours: Nur Logs der letzten X Stunden
    """
    since = None
    if hours:
        since = datetime.utcnow() - timedelta(hours=hours)
    
    logs = log_buffer.get_recent(
        limit=limit,
        level=level,
        client_id=client_id,
        since=since
    )
    
    return {
        "logs": logs,
        "count": len(logs),
        "filters": {
            "limit": limit,
            "level": level,
            "client_id": client_id,
            "hours": hours
        }
    }


@router.get("/logs/stats")
async def get_client_log_stats(
    user: dict = Depends(require_admin)
):
    """Gibt Log-Statistiken zurück (Admin only)"""
    return log_buffer.get_stats()


@router.get("/logs/errors")
async def get_client_errors(
    hours: int = Query(24, ge=1, le=168),
    user: dict = Depends(require_admin)
):
    """Holt alle Errors der letzten X Stunden (Admin only)"""
    errors = log_buffer.get_errors(hours=hours)
    
    return {
        "errors": errors,
        "count": len(errors),
        "hours": hours
    }


@router.delete("/logs")
async def clear_client_logs(
    user: dict = Depends(require_admin)
):
    """Leert Log-Buffer (Admin only)"""
    stats_before = log_buffer.get_stats()
    log_buffer.clear()
    
    return {
        "status": "cleared",
        "cleared_count": stats_before["buffer_size"]
    }
