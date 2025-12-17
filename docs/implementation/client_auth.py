# app/routes/client_auth.py
"""
Client Authentication Routes
Authentifizierung für Desktop-Clients und Mobile-Apps

Implementierung für TriForce Backend
Stand: 2025-12-13
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import secrets
import jwt
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/auth", tags=["Client Auth"])

# JWT Secret (in Produktion aus ENV laden!)
JWT_SECRET = "triforce_jwt_secret_change_in_production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24


class ClientRole(str, Enum):
    ADMIN = "admin"          # Voller Zugriff (Markus)
    CLI_AGENT = "cli_agent"  # Server-Side Agents
    DESKTOP = "desktop"      # Desktop Clients
    MOBILE = "mobile"        # Mobile Clients (eingeschränkt)


# =============================================================================
# Client Registry
# =============================================================================

# In Produktion: Datenbank statt Dict
CLIENT_REGISTRY: Dict[str, dict] = {
    # Beispiel-Clients
    "desktop-markus-main": {
        "secret_hash": "",  # Wird beim ersten Start generiert
        "name": "Markus Gaming PC",
        "role": ClientRole.DESKTOP,
        "created_at": "2025-12-13",
        "allowed_tools": [
            "chat", "chat_smart", "weather", "current_time",
            "web_search", "smart_search", "multi_search",
            "client_*",  # Alle Client-Tools
            "tristar_memory_*",  # Memory-Zugriff
        ],
        "blocked_tools": [
            "codebase_*",  # Kein Server-Code-Zugriff
            "restart_*",
            "tristar_shell_exec",
            "vault_*",  # Kein Vault-Zugriff
        ]
    }
}

# Aktive Sessions
ACTIVE_SESSIONS: Dict[str, dict] = {}


def hash_secret(secret: str) -> str:
    """Secret hashen für Speicherung"""
    return hashlib.sha256(secret.encode()).hexdigest()


def verify_secret(secret: str, secret_hash: str) -> bool:
    """Secret gegen Hash prüfen"""
    return hash_secret(secret) == secret_hash


def generate_client_secret() -> str:
    """Neues Client-Secret generieren"""
    return secrets.token_urlsafe(32)


def create_jwt_token(client_id: str, role: str, expires_hours: int = JWT_EXPIRY_HOURS) -> str:
    """JWT Token erstellen"""
    payload = {
        "client_id": client_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=expires_hours),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> dict:
    """JWT Token dekodieren"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


# =============================================================================
# Request/Response Models
# =============================================================================

class ClientAuthRequest(BaseModel):
    """Client Auth Request"""
    client_id: str = Field(..., description="Client-ID")
    client_secret: str = Field(..., description="Client-Secret")
    device_name: Optional[str] = Field(None, description="Gerätename")
    capabilities: Optional[List[str]] = Field(default=[], description="Client-Fähigkeiten")


class ClientAuthResponse(BaseModel):
    """Client Auth Response"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int  # Sekunden
    role: str
    client_id: str
    allowed_tools: List[str]


class ClientRegisterRequest(BaseModel):
    """Neuen Client registrieren (nur Admin)"""
    client_id: str
    name: str
    role: ClientRole = ClientRole.DESKTOP
    allowed_tools: List[str] = []
    blocked_tools: List[str] = []


class ClientRegisterResponse(BaseModel):
    """Response mit generiertem Secret"""
    client_id: str
    client_secret: str  # Nur einmal angezeigt!
    message: str


# =============================================================================
# Auth Endpoints
# =============================================================================

@router.post("/client", response_model=ClientAuthResponse)
async def client_auth(request: ClientAuthRequest):
    """
    Client authentifizieren
    
    Gibt JWT Token zurück für weitere API-Calls
    """
    client = CLIENT_REGISTRY.get(request.client_id)
    
    if not client:
        logger.warning(f"Unknown client: {request.client_id}")
        raise HTTPException(401, "Unknown client")
    
    # Secret prüfen (falls bereits gesetzt)
    if client.get("secret_hash"):
        if not verify_secret(request.client_secret, client["secret_hash"]):
            logger.warning(f"Invalid secret for client: {request.client_id}")
            raise HTTPException(401, "Invalid credentials")
    else:
        # Erstes Login - Secret setzen
        client["secret_hash"] = hash_secret(request.client_secret)
        logger.info(f"First login for client: {request.client_id}, secret set")
    
    # Token generieren
    token = create_jwt_token(request.client_id, client["role"].value)
    
    # Session tracken
    ACTIVE_SESSIONS[request.client_id] = {
        "device_name": request.device_name,
        "capabilities": request.capabilities,
        "connected_at": datetime.now().isoformat(),
        "last_seen": datetime.now().isoformat()
    }
    
    logger.info(f"Client authenticated: {request.client_id} ({client['role'].value})")
    
    return ClientAuthResponse(
        access_token=token,
        expires_in=JWT_EXPIRY_HOURS * 3600,
        role=client["role"].value,
        client_id=request.client_id,
        allowed_tools=client.get("allowed_tools", [])
    )


@router.post("/client/register", response_model=ClientRegisterResponse)
async def register_client(
    request: ClientRegisterRequest,
    authorization: str = Header(None)
):
    """
    Neuen Client registrieren (nur Admin)
    
    Generiert ein neues Client-Secret das nur einmal angezeigt wird!
    """
    # Admin-Check
    if not authorization:
        raise HTTPException(401, "Authorization header required")
    
    try:
        token = authorization.replace("Bearer ", "")
        payload = decode_jwt_token(token)
        if payload.get("role") != "admin":
            raise HTTPException(403, "Admin access required")
    except:
        raise HTTPException(403, "Admin access required")
    
    # Prüfen ob Client schon existiert
    if request.client_id in CLIENT_REGISTRY:
        raise HTTPException(400, f"Client already exists: {request.client_id}")
    
    # Secret generieren
    client_secret = generate_client_secret()
    
    # Client registrieren
    CLIENT_REGISTRY[request.client_id] = {
        "secret_hash": hash_secret(client_secret),
        "name": request.name,
        "role": request.role,
        "created_at": datetime.now().isoformat(),
        "allowed_tools": request.allowed_tools or [
            "chat", "weather", "current_time", "web_search"
        ],
        "blocked_tools": request.blocked_tools or [
            "codebase_*", "restart_*", "vault_*"
        ]
    }
    
    logger.info(f"New client registered: {request.client_id}")
    
    return ClientRegisterResponse(
        client_id=request.client_id,
        client_secret=client_secret,
        message="WICHTIG: Speichere das Secret sicher - es wird nur einmal angezeigt!"
    )


@router.get("/client/me")
async def get_client_info(authorization: str = Header(None)):
    """Eigene Client-Info abrufen"""
    if not authorization:
        raise HTTPException(401, "Authorization header required")
    
    token = authorization.replace("Bearer ", "")
    payload = decode_jwt_token(token)
    
    client_id = payload.get("client_id")
    client = CLIENT_REGISTRY.get(client_id)
    
    if not client:
        raise HTTPException(404, "Client not found")
    
    session = ACTIVE_SESSIONS.get(client_id, {})
    
    return {
        "client_id": client_id,
        "name": client.get("name"),
        "role": client.get("role").value if isinstance(client.get("role"), ClientRole) else client.get("role"),
        "allowed_tools": client.get("allowed_tools", []),
        "blocked_tools": client.get("blocked_tools", []),
        "session": session
    }


@router.get("/client/list")
async def list_clients(authorization: str = Header(None)):
    """
    Alle Clients auflisten (nur Admin)
    """
    if not authorization:
        raise HTTPException(401, "Authorization header required")
    
    token = authorization.replace("Bearer ", "")
    payload = decode_jwt_token(token)
    
    if payload.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    
    clients = []
    for client_id, client in CLIENT_REGISTRY.items():
        session = ACTIVE_SESSIONS.get(client_id, {})
        clients.append({
            "client_id": client_id,
            "name": client.get("name"),
            "role": client.get("role").value if isinstance(client.get("role"), ClientRole) else client.get("role"),
            "created_at": client.get("created_at"),
            "is_online": client_id in ACTIVE_SESSIONS,
            "last_seen": session.get("last_seen")
        })
    
    return {"clients": clients, "count": len(clients)}


@router.delete("/client/{client_id}")
async def delete_client(client_id: str, authorization: str = Header(None)):
    """
    Client entfernen (nur Admin)
    """
    if not authorization:
        raise HTTPException(401, "Authorization header required")
    
    token = authorization.replace("Bearer ", "")
    payload = decode_jwt_token(token)
    
    if payload.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    
    if client_id not in CLIENT_REGISTRY:
        raise HTTPException(404, f"Client not found: {client_id}")
    
    del CLIENT_REGISTRY[client_id]
    
    if client_id in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[client_id]
    
    logger.info(f"Client deleted: {client_id}")
    
    return {"deleted": True, "client_id": client_id}


# =============================================================================
# Tool Permission Check
# =============================================================================

def is_tool_allowed(client_id: str, tool_name: str) -> bool:
    """
    Prüft ob ein Client ein Tool nutzen darf
    
    Wildcards werden unterstützt:
    - "client_*" erlaubt alle Tools die mit "client_" beginnen
    - "codebase_*" in blocked_tools blockiert alle codebase-Tools
    """
    client = CLIENT_REGISTRY.get(client_id)
    if not client:
        return False
    
    allowed = client.get("allowed_tools", [])
    blocked = client.get("blocked_tools", [])
    
    # Blocked hat Vorrang
    for pattern in blocked:
        if pattern.endswith("*"):
            if tool_name.startswith(pattern[:-1]):
                return False
        elif pattern == tool_name:
            return False
    
    # Allowed prüfen
    for pattern in allowed:
        if pattern.endswith("*"):
            if tool_name.startswith(pattern[:-1]):
                return True
        elif pattern == tool_name:
            return True
    
    return False


# =============================================================================
# Dependency für geschützte Routen
# =============================================================================

async def get_current_client(authorization: str = Header(None)) -> dict:
    """
    FastAPI Dependency für Client-Auth
    
    Verwendung:
    @router.get("/protected")
    async def protected_route(client: dict = Depends(get_current_client)):
        ...
    """
    if not authorization:
        raise HTTPException(401, "Authorization header required")
    
    token = authorization.replace("Bearer ", "")
    payload = decode_jwt_token(token)
    
    client_id = payload.get("client_id")
    client = CLIENT_REGISTRY.get(client_id)
    
    if not client:
        raise HTTPException(401, "Client not found")
    
    # Last seen aktualisieren
    if client_id in ACTIVE_SESSIONS:
        ACTIVE_SESSIONS[client_id]["last_seen"] = datetime.now().isoformat()
    
    return {
        "client_id": client_id,
        "role": payload.get("role"),
        "client": client
    }


async def require_admin(authorization: str = Header(None)) -> dict:
    """
    Dependency für Admin-Only Routen
    """
    client = await get_current_client(authorization)
    
    if client.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    
    return client
