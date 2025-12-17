"""
AILinux MCP Node
================

MCP Node ermöglicht dem Server, MCP-Tools auf dem CLIENT-Rechner auszuführen.

Architektur:
1. Client (MCP Node) verbindet sich zum Server via WebSocket
2. Server sendet Tool-Calls an Client
3. Client führt Tools lokal aus (Dateisystem, Shell, etc.)
4. Ergebnis wird an Server zurückgesendet
5. KI verarbeitet Ergebnis und kann weitere Tools aufrufen

Protokoll:
- WebSocket für bidirektionale Kommunikation
- JSON-RPC 2.0 Format (MCP-kompatibel)
- Client meldet verfügbare Tools an Server
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import asyncio
import json
import logging
import uuid
from datetime import datetime
from enum import Enum

from ..services.user_tiers import tier_service, UserTier
from ..routes.client_auth import decode_jwt_token

logger = logging.getLogger("ailinux.mcp_node")

router = APIRouter(prefix="/mcp/node", tags=["MCP Node"])


# =============================================================================
# Connected Clients Registry
# =============================================================================

class ClientConnection:
    """Repräsentiert eine aktive Client-Verbindung"""

    def __init__(self, client_id: str, user_id: str, websocket: WebSocket, tier: UserTier):
        self.client_id = client_id
        self.user_id = user_id
        self.websocket = websocket
        self.tier = tier
        self.connected_at = datetime.now()
        self.last_seen = datetime.now()
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.supported_tools: List[str] = []
        self.client_info: Dict[str, Any] = {}  # Platform, hostname, version etc.
        
        # Telemetrie (read-only Status)
        self.mode: str = "full"  # "full" oder "telemetry_only"
        self.tool_usage: List[Dict[str, Any]] = []  # Letzte Tool-Aufrufe
        self.total_tool_calls: int = 0
        self.successful_tool_calls: int = 0
        self.failed_tool_calls: int = 0

    async def send_tool_call(self, tool: str, params: Dict[str, Any], timeout: float = 60.0) -> Dict[str, Any]:
        """
        Sendet Tool-Call an Client und wartet auf Antwort

        Returns:
            Tool-Ergebnis vom Client
        """
        request_id = str(uuid.uuid4())

        # JSON-RPC Request
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool,
                "arguments": params
            },
            "id": request_id
        }

        # Future für Antwort erstellen
        future = asyncio.get_event_loop().create_future()
        self.pending_requests[request_id] = future

        try:
            # Request senden
            await self.websocket.send_json(request)

            # Auf Antwort warten (mit Timeout)
            result = await asyncio.wait_for(future, timeout=timeout)
            return result

        except asyncio.TimeoutError:
            logger.error(f"Tool call timeout: {tool} for {self.client_id}")
            raise HTTPException(504, f"Client timeout für Tool: {tool}")

        finally:
            self.pending_requests.pop(request_id, None)

    def handle_response(self, response: Dict[str, Any]):
        """Verarbeitet Response vom Client"""
        request_id = response.get("id")
        if request_id and request_id in self.pending_requests:
            future = self.pending_requests[request_id]
            if not future.done():
                if "error" in response:
                    future.set_exception(Exception(response["error"].get("message", "Unknown error")))
                else:
                    future.set_result(response.get("result", {}))


# Aktive Client-Verbindungen
CONNECTED_CLIENTS: Dict[str, ClientConnection] = {}

# Heartbeat-Timeout: Clients die länger als X Sekunden kein Ping gesendet haben werden entfernt
HEARTBEAT_TIMEOUT_SECONDS = 90  # 90 Sekunden ohne Ping = disconnect
HEARTBEAT_CHECK_INTERVAL = 30   # Alle 30 Sekunden prüfen

_heartbeat_task = None


async def _heartbeat_monitor():
    """Background-Task der inaktive Verbindungen entfernt"""
    while True:
        await asyncio.sleep(HEARTBEAT_CHECK_INTERVAL)
        
        now = datetime.now()
        stale_clients = []
        
        for client_id, conn in list(CONNECTED_CLIENTS.items()):
            # Zeit seit letztem Lebenszeichen
            inactive_seconds = (now - conn.last_seen).total_seconds()
            
            if inactive_seconds > HEARTBEAT_TIMEOUT_SECONDS:
                stale_clients.append(client_id)
                logger.warning(f"Client {client_id} inactive for {inactive_seconds:.0f}s, marking as stale")
        
        # Stale Clients entfernen
        for client_id in stale_clients:
            conn = CONNECTED_CLIENTS.pop(client_id, None)
            if conn:
                try:
                    await conn.websocket.close(code=4002, reason="Heartbeat timeout")
                except Exception:
                    pass  # Verbindung ist wahrscheinlich schon tot
                logger.info(f"Removed stale client: {client_id}")


def start_heartbeat_monitor():
    """Startet den Heartbeat-Monitor (einmal beim App-Start aufrufen)"""
    global _heartbeat_task
    if _heartbeat_task is None:
        _heartbeat_task = asyncio.create_task(_heartbeat_monitor())
        logger.info("Heartbeat monitor started")


# =============================================================================
# Client-seitige Tools (die auf dem Client laufen)
# =============================================================================

CLIENT_SIDE_TOOLS = {
    "client_file_read": {
        "description": "Liest Datei vom Client-Dateisystem",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Dateipfad auf dem Client"}
            },
            "required": ["path"]
        }
    },
    "client_file_write": {
        "description": "Schreibt Datei auf Client-Dateisystem",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Dateipfad auf dem Client"},
                "content": {"type": "string", "description": "Dateiinhalt"}
            },
            "required": ["path", "content"]
        }
    },
    "client_file_list": {
        "description": "Listet Verzeichnis auf Client",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Verzeichnispfad"},
                "recursive": {"type": "boolean", "default": False}
            },
            "required": ["path"]
        }
    },
    "client_shell_exec": {
        "description": "Führt Shell-Befehl auf Client aus",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell-Befehl"},
                "cwd": {"type": "string", "description": "Arbeitsverzeichnis"}
            },
            "required": ["command"]
        }
    },
    "client_codebase_search": {
        "description": "Durchsucht Codebase auf Client",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Suchanfrage"},
                "path": {"type": "string", "description": "Basis-Pfad"},
                "file_pattern": {"type": "string", "description": "Datei-Pattern (z.B. *.py)"}
            },
            "required": ["query"]
        }
    },
    "client_git_status": {
        "description": "Git Status auf Client",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Repository-Pfad"}
            },
            "required": ["path"]
        }
    },
    "support_call": {
        "description": "KI-Support kontaktieren - Problem wird analysiert und Ticket erstellt",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Kurzer Betreff des Problems"},
                "description": {"type": "string", "description": "Detaillierte Problembeschreibung"},
                "category": {"type": "string", "enum": ["general", "bug", "feature", "billing", "technical"], "description": "Kategorie"},
                "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"], "description": "Priorität"},
                "logs": {"type": "string", "description": "Relevante Log-Auszüge (optional)"}
            },
            "required": ["subject", "description"]
        }
    },
}


# =============================================================================
# Request/Response Models
# =============================================================================

class ProxyToolRequest(BaseModel):
    """Tool-Call über Proxy"""
    client_id: str
    tool: str
    params: Dict[str, Any] = {}


class ProxyToolResponse(BaseModel):
    """Proxy Tool Response"""
    success: bool
    tool: str
    client_id: str
    result: Any = None
    error: Optional[str] = None
    latency_ms: int = 0


# =============================================================================
# WebSocket Endpoint für Clients
# =============================================================================

@router.websocket("/connect")
async def websocket_connect(
    websocket: WebSocket,
    token: str = None,
    session_id: str = None,
    machine_id: str = None,
    user_id: str = None,
    tier: str = None,
    client_version: str = None
):
    """
    WebSocket-Verbindung für MCP Node Client

    Client sendet Query-Parameter:
    - token: JWT Token (required)
    - session_id: Persistente Session-ID
    - machine_id: Eindeutige Machine-ID
    - user_id: User-ID (aus Login)
    - tier: User-Tier (free/pro/enterprise)
    - client_version: Client-Version

    Nach Verbindung kann der Server Tools auf dem Client ausführen.
    """
    await websocket.accept()
    
    # Mode aus Query-Param
    mode = websocket.query_params.get("mode", "full")
    is_telemetry_only = mode == "telemetry"
    
    logger.info(f"WebSocket connecting: mode={mode}, session={session_id}, tier={tier}")

    # Token validieren (bei telemetry_only: toleranter)
    payload = {}
    if token:
        try:
            payload = decode_jwt_token(token)
        except Exception as e:
            if is_telemetry_only:
                # Telemetrie-Only: Token-Fehler nur loggen, nicht abbrechen
                logger.warning(f"Telemetry connection with invalid/expired token: {e}")
                payload = {"client_id": session_id}
            else:
                # Full-Mode: Token muss gültig sein
                logger.error(f"WebSocket rejected: Invalid token - {e}")
                await websocket.send_json({"error": f"Invalid token: {e}"})
                await websocket.close(code=4001)
                return
    elif not is_telemetry_only:
        # Full-Mode ohne Token: Ablehnen
        logger.error("WebSocket rejected: Token required for full mode")
        await websocket.send_json({"error": "Token required"})
        await websocket.close(code=4001)
        return

    # Client-ID aus Token, Session oder generieren
    client_id = payload.get("client_id") or session_id or str(uuid.uuid4())[:16]
    
    # User-ID: aus Token, Query-Param oder Client-ID
    resolved_user_id = payload.get("sub") or user_id or client_id
    
    # Tier: aus Query-Param oder Service abfragen
    if tier and tier in ["free", "pro", "enterprise"]:
        resolved_tier = UserTier(tier)
    else:
        resolved_tier = tier_service.get_user_tier(resolved_user_id)
    
    logger.info(f"MCP Node connecting: session={session_id}, machine={machine_id}, user={resolved_user_id}, tier={resolved_tier.value}, version={client_version}")

    # Client-Verbindung registrieren
    connection = ClientConnection(client_id, resolved_user_id, websocket, resolved_tier)
    connection.mode = "telemetry_only" if is_telemetry_only else "full"
    CONNECTED_CLIENTS[client_id] = connection
    
    # Auch unter Session-ID registrieren für schnellen Lookup
    if session_id and session_id != client_id:
        CONNECTED_CLIENTS[session_id] = connection

    logger.info(f"Client connected: {client_id} ({resolved_tier.value})")

    # Willkommensnachricht mit verfügbaren Tools
    await websocket.send_json({
        "jsonrpc": "2.0",
        "method": "connected",
        "params": {
            "client_id": client_id,
            "session_id": session_id,
            "user_id": resolved_user_id,
            "tier": resolved_tier.value,
            "available_tools": list(CLIENT_SIDE_TOOLS.keys()),
            "server_version": "2.80.0"
        }
    })

    try:
        while True:
            # Nachrichten vom Client empfangen
            data = await websocket.receive_json()

            # Response auf Tool-Call?
            if "result" in data or "error" in data:
                connection.handle_response(data)

    # Client-Info empfangen
            elif data.get("method") == "client/info":
                info_params = data.get("params", {})
                logger.info(f"Client info received: platform={info_params.get('platform')}, hostname={info_params.get('hostname')}, version={info_params.get('server_version')}, mode={info_params.get('mode')}")
                # Info speichern
                connection.client_info = info_params
                # Mode setzen (telemetry_only = keine Remote-Execution)
                if info_params.get("mode") == "telemetry_only":
                    connection.mode = "telemetry_only"
                    logger.info(f"Client {client_id} is in TELEMETRY-ONLY mode (no remote execution)")

            # Tool-Capabilities vom Client?
            elif data.get("method") == "tools/list":
                connection.supported_tools = data.get("params", {}).get("tools", [])
                logger.info(f"Client {client_id} supports {len(connection.supported_tools)} tools")

            # Telemetrie: Tool-Nutzung empfangen (für Debugging)
            elif data.get("method") == "telemetry/tool_used":
                tool_params = data.get("params", {})
                tool_name = tool_params.get("tool", "unknown")
                success = tool_params.get("success", False)
                duration_ms = tool_params.get("duration_ms", 0)
                
                # Statistiken aktualisieren
                connection.total_tool_calls += 1
                if success:
                    connection.successful_tool_calls += 1
                else:
                    connection.failed_tool_calls += 1
                
                # Letzte 50 Tool-Aufrufe speichern
                connection.tool_usage.append({
                    "tool": tool_name,
                    "success": success,
                    "duration_ms": duration_ms,
                    "timestamp": datetime.now().isoformat()
                })
                if len(connection.tool_usage) > 50:
                    connection.tool_usage = connection.tool_usage[-50:]
                
                logger.debug(f"Telemetry: {client_id} used {tool_name} (success={success}, {duration_ms}ms)")

            # Heartbeat
            elif data.get("method") == "ping":
                connection.last_seen = datetime.now()
                await websocket.send_json({"method": "pong"})

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
    finally:
        # Alle Referenzen entfernen
        CONNECTED_CLIENTS.pop(client_id, None)
        if session_id and session_id != client_id:
            CONNECTED_CLIENTS.pop(session_id, None)
        logger.info(f"Client cleanup completed: {client_id}")


# =============================================================================
# HTTP Endpoints für Tool-Calls via Proxy
# =============================================================================

@router.get("/clients")
async def list_connected_clients(authorization: str = Header(None)):
    """Liste aller verbundenen Clients"""
    if not authorization:
        raise HTTPException(401, "Authorization required")

    clients = []
    for client_id, conn in CONNECTED_CLIENTS.items():
        clients.append({
            "client_id": client_id,
            "user_id": conn.user_id,
            "tier": conn.tier.value,
            "connected_at": conn.connected_at.isoformat(),
            "last_seen": conn.last_seen.isoformat(),
            "supported_tools": conn.supported_tools,
            "client_info": conn.client_info,
        })

    return {"clients": clients, "count": len(clients)}


@router.post("/call", response_model=ProxyToolResponse)
async def call_client_tool(
    request: ProxyToolRequest,
    authorization: str = Header(None)
):
    """
    Führt Tool auf Client aus

    Der Server sendet den Tool-Call an den verbundenen Client,
    der Client führt das Tool lokal aus und sendet das Ergebnis zurück.
    """
    if not authorization:
        raise HTTPException(401, "Authorization required")

    # Validiere Caller
    try:
        token = authorization.replace("Bearer ", "")
        payload = decode_jwt_token(token)
    except Exception:
        raise HTTPException(401, "Invalid token")

    # Client finden
    client_id = request.client_id
    connection = CONNECTED_CLIENTS.get(client_id)

    if not connection:
        raise HTTPException(404, f"Client nicht verbunden: {client_id}")

    # Tool-Berechtigung prüfen
    if request.tool not in CLIENT_SIDE_TOOLS:
        raise HTTPException(400, f"Unbekanntes Client-Tool: {request.tool}")

    # Enterprise Tier für Dateisystem-Zugriff
    if connection.tier == UserTier.FREE and request.tool in ["client_file_write", "client_shell_exec"]:
        raise HTTPException(403, f"Tool '{request.tool}' erfordert Pro oder Enterprise Tier")

    start_time = datetime.now()

    try:
        result = await connection.send_tool_call(request.tool, request.params)
        latency = int((datetime.now() - start_time).total_seconds() * 1000)

        logger.info(f"Proxy call success: {request.tool} on {client_id} ({latency}ms)")

        return ProxyToolResponse(
            success=True,
            tool=request.tool,
            client_id=client_id,
            result=result,
            latency_ms=latency
        )

    except Exception as e:
        latency = int((datetime.now() - start_time).total_seconds() * 1000)
        logger.error(f"Proxy call failed: {request.tool} on {client_id} - {e}")

        return ProxyToolResponse(
            success=False,
            tool=request.tool,
            client_id=client_id,
            error=str(e),
            latency_ms=latency
        )


@router.get("/tools")
async def list_client_tools():
    """Liste aller Client-seitigen Tools"""
    return {
        "tools": [
            {
                "name": name,
                "description": tool["description"],
                "inputSchema": tool["inputSchema"]
            }
            for name, tool in CLIENT_SIDE_TOOLS.items()
        ],
        "count": len(CLIENT_SIDE_TOOLS)
    }


# =============================================================================
# KI-Integration: Tool-Calls für Chat mit Client-Dateisystem
# =============================================================================

@router.post("/chat-with-files")
async def chat_with_client_files(
    client_id: str,
    message: str,
    model: Optional[str] = None,
    authorization: str = Header(None)
):
    """
    Chat mit KI, die auf Client-Dateisystem zugreifen kann

    Die KI kann während des Chats:
    - Dateien vom Client lesen
    - Codebase durchsuchen
    - Shell-Befehle ausführen (Enterprise)

    Dies ermöglicht "Claude Code"-ähnliche Funktionalität,
    wobei der Client die Dateien bereitstellt.
    """
    if not authorization:
        raise HTTPException(401, "Authorization required")

    # Client prüfen
    connection = CONNECTED_CLIENTS.get(client_id)
    if not connection:
        raise HTTPException(404, f"Client nicht verbunden: {client_id}")

    # Tier und Model bestimmen
    tier = connection.tier
    if not model:
        from .client_chat import get_default_model
        model = get_default_model(tier)

    # System-Prompt mit Client-Tools
    system_prompt = f"""Du bist ein KI-Assistent mit Zugriff auf das Dateisystem des Benutzers.

Verfügbare Tools:
- client_file_read: Datei lesen
- client_file_list: Verzeichnis auflisten
- client_codebase_search: Code durchsuchen
{"- client_file_write: Datei schreiben (Enterprise)" if tier == UserTier.ENTERPRISE else ""}
{"- client_shell_exec: Shell-Befehl ausführen (Enterprise)" if tier == UserTier.ENTERPRISE else ""}

Wenn der Benutzer nach Dateien fragt oder Code-Hilfe benötigt,
nutze die Tools um die relevanten Dateien zu lesen.

Benutzer-Tier: {tier.value}
"""

    # Chat ausführen (mit Tool-Calling Loop)
    from .client_chat import call_ollama, call_openrouter, normalize_ollama_model

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message}
    ]

    # Erste Antwort
    if tier == UserTier.FREE:
        result = await call_ollama(model, messages)
    else:
        result = await call_openrouter(model, messages)

    response = result.get("choices", [{}])[0].get("message", {}).get("content", "")

    # TODO: Implementiere Tool-Calling Loop
    # Wenn die KI ein Tool aufrufen möchte, sende es an den Client
    # und füge das Ergebnis zur Konversation hinzu

    return {
        "response": response,
        "model": model,
        "tier": tier.value,
        "client_id": client_id,
        "tools_available": list(CLIENT_SIDE_TOOLS.keys())
    }


# =============================================================================
# Support-Call System (KI nimmt Probleme auf)
# =============================================================================

# =============================================================================

class SupportTicket(BaseModel):
    """Support-Anfrage vom Client"""
    subject: str
    description: str
    category: Optional[str] = "general"  # general, bug, feature, billing, technical
    priority: Optional[str] = "normal"   # low, normal, high, urgent
    client_info: Optional[Dict[str, Any]] = None
    logs: Optional[str] = None  # Relevante Log-Auszüge


class SupportResponse(BaseModel):
    """Antwort auf Support-Anfrage"""
    ticket_id: str
    status: str
    ai_response: str
    suggestions: List[str] = []
    escalated: bool = False
    estimated_response_time: Optional[str] = None


# In-Memory Ticket-Speicher (später: Datenbank)
SUPPORT_TICKETS: Dict[str, Dict[str, Any]] = {}


@router.post("/support/call", response_model=SupportResponse)
async def create_support_ticket(
    ticket: SupportTicket,
    authorization: str = Header(None)
):
    """
    Support-Call: KI nimmt Problem auf und gibt erste Hilfe
    
    Die KI:
    1. Analysiert das Problem
    2. Gibt sofortige Lösungsvorschläge wenn möglich
    3. Erstellt Ticket für menschlichen Support bei komplexen Fällen
    4. Speichert alle relevanten Infos für Nachverfolgung
    """
    import uuid
    from datetime import datetime
    
    # Ticket-ID generieren
    ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
    
    # Client-Info aus Token extrahieren (falls vorhanden)
    user_id = "anonymous"
    tier = "free"
    if authorization:
        try:
            token = authorization.replace("Bearer ", "")
            payload = decode_jwt_token(token)
            user_id = payload.get("sub", payload.get("client_id", "anonymous"))
            tier = payload.get("role", "free")
        except Exception:
            pass  # Anonymer Support ist OK
    
    # KI-Prompt für Support erstellen
    support_prompt = f"""Du bist der AILinux Support-Assistent. Ein Benutzer hat ein Support-Ticket erstellt.

**Ticket-Details:**
- Betreff: {ticket.subject}
- Kategorie: {ticket.category}
- Priorität: {ticket.priority}
- Benutzer-Tier: {tier}

**Problembeschreibung:**
{ticket.description}

{f"**Logs:**\n```\n{ticket.logs[:2000]}\n```" if ticket.logs else ""}

{f"**Client-Info:** {json.dumps(ticket.client_info, indent=2)}" if ticket.client_info else ""}

**Deine Aufgabe:**
1. Analysiere das Problem kurz
2. Gib 2-3 konkrete Lösungsvorschläge wenn möglich
3. Sage dem Benutzer was als nächstes passiert

Antworte freundlich und hilfsbereit auf Deutsch. Halte dich kurz (max 200 Wörter).
"""

    # KI-Antwort generieren (über Ollama oder Gemini)
    ai_response = ""
    suggestions = []
    escalated = False
    
    try:
        # Versuche lokales Modell zuerst
        from ..services.ollama_service import ollama_service
        
        result = await ollama_service.generate(
            model="cogito-2.1:671b-cloud",
            prompt=support_prompt,
            system="Du bist ein hilfsbreiter, technischer Support-Assistent für AILinux.",
            options={"temperature": 0.7, "num_predict": 500}
        )
        ai_response = result.get("response", "")
        
    except Exception as e:
        logger.warning(f"Ollama support failed: {e}, trying Gemini...")
        
        try:
            # Fallback: Gemini
            from ..services.gemini_access import gemini_service
            
            result = await gemini_service.generate_content(
                prompt=support_prompt,
                model="gemini-2.0-flash-exp"
            )
            ai_response = result.get("text", "")
            
        except Exception as e2:
            logger.error(f"Support AI failed: {e2}")
            ai_response = f"""Vielen Dank für deine Anfrage!

Dein Ticket wurde unter **{ticket_id}** erfasst.

**Problem:** {ticket.subject}

Leider konnte ich das Problem nicht automatisch analysieren. Ein Mitarbeiter wird sich zeitnah bei dir melden.

Bei dringenden Problemen erreichst du uns auch unter support@ailinux.me.
"""
            escalated = True
    
    # Lösungsvorschläge aus Antwort extrahieren (einfache Heuristik)
    if ai_response:
        lines = ai_response.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith(("1.", "2.", "3.", "-", "•", "*")) and len(line) > 10:
                suggestions.append(line.lstrip("123.-•* "))
                if len(suggestions) >= 3:
                    break
    
    # Ticket speichern
    SUPPORT_TICKETS[ticket_id] = {
        "id": ticket_id,
        "user_id": user_id,
        "tier": tier,
        "subject": ticket.subject,
        "description": ticket.description,
        "category": ticket.category,
        "priority": ticket.priority,
        "client_info": ticket.client_info,
        "logs": ticket.logs[:5000] if ticket.logs else None,
        "ai_response": ai_response,
        "suggestions": suggestions,
        "escalated": escalated,
        "status": "open",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    
    logger.info(f"Support ticket created: {ticket_id} - {ticket.subject} (user={user_id}, escalated={escalated})")
    
    # Geschätzte Antwortzeit basierend auf Priorität
    response_times = {
        "urgent": "< 1 Stunde",
        "high": "< 4 Stunden", 
        "normal": "< 24 Stunden",
        "low": "< 48 Stunden"
    }
    
    return SupportResponse(
        ticket_id=ticket_id,
        status="open",
        ai_response=ai_response,
        suggestions=suggestions,
        escalated=escalated,
        estimated_response_time=response_times.get(ticket.priority, "< 24 Stunden")
    )


@router.get("/support/tickets")
async def list_support_tickets(
    status: Optional[str] = None,
    authorization: str = Header(None)
):
    """Liste aller Support-Tickets (Admin-Funktion)"""
    if not authorization:
        raise HTTPException(401, "Authorization required")
    
    # Admin-Check (vereinfacht)
    try:
        token = authorization.replace("Bearer ", "")
        payload = decode_jwt_token(token)
        if payload.get("role") not in ["admin", "enterprise"]:
            raise HTTPException(403, "Admin access required")
    except Exception:
        raise HTTPException(401, "Invalid token")
    
    tickets = list(SUPPORT_TICKETS.values())
    
    if status:
        tickets = [t for t in tickets if t.get("status") == status]
    
    return {
        "tickets": tickets,
        "count": len(tickets),
        "open": len([t for t in SUPPORT_TICKETS.values() if t.get("status") == "open"]),
        "escalated": len([t for t in SUPPORT_TICKETS.values() if t.get("escalated")])
    }


@router.get("/support/ticket/{ticket_id}")
async def get_support_ticket(ticket_id: str):
    """Einzelnes Ticket abrufen"""
    if ticket_id not in SUPPORT_TICKETS:
        raise HTTPException(404, f"Ticket nicht gefunden: {ticket_id}")
    
    return SUPPORT_TICKETS[ticket_id]


@router.post("/support/ticket/{ticket_id}/reply")
async def reply_to_ticket(
    ticket_id: str,
    message: str,
    authorization: str = Header(None)
):
    """Antwort auf Ticket hinzufügen"""
    if ticket_id not in SUPPORT_TICKETS:
        raise HTTPException(404, f"Ticket nicht gefunden: {ticket_id}")
    
    ticket = SUPPORT_TICKETS[ticket_id]
    
    # Replies initialisieren falls nicht vorhanden
    if "replies" not in ticket:
        ticket["replies"] = []
    
    # Reply hinzufügen
    from datetime import datetime
    
    reply = {
        "message": message,
        "from": "user" if not authorization else "support",
        "timestamp": datetime.now().isoformat()
    }
    
    ticket["replies"].append(reply)
    ticket["updated_at"] = datetime.now().isoformat()
    
    # KI-Antwort auf Follow-up generieren
    if not authorization:  # Benutzer-Nachricht -> KI antwortet
        try:
            from ..services.ollama_service import ollama_service
            
            context = f"""Ticket: {ticket['subject']}
Ursprüngliches Problem: {ticket['description']}
Bisherige KI-Antwort: {ticket['ai_response'][:500]}
Neue Nachricht vom Benutzer: {message}

Antworte kurz und hilfsbereit (max 100 Wörter)."""
            
            result = await ollama_service.generate(
                model="cogito-2.1:671b-cloud",
                prompt=context,
                system="Du bist ein Support-Assistent. Antworte kurz und hilfsbereit.",
                options={"temperature": 0.7, "num_predict": 300}
            )
            
            ai_reply = {
                "message": result.get("response", "Danke für deine Nachricht. Ich leite das weiter."),
                "from": "ai",
                "timestamp": datetime.now().isoformat()
            }
            ticket["replies"].append(ai_reply)
            
            return {"status": "replied", "ai_response": ai_reply["message"]}
            
        except Exception as e:
            logger.error(f"AI reply failed: {e}")
    
    return {"status": "added", "reply": reply}
