import os
import json
from pathlib import Path
# app/routes/client_auth.py
"""
Client Authentication Routes
Authentifizierung für Desktop-Clients und Mobile-Apps

Implementierung für TriForce Backend
Stand: 2025-12-13
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import secrets
import jwt
import logging

logger = logging.getLogger(__name__)

# Pfad zur User-Datenbank
USERS_FILE_PATH = Path(__file__).parent.parent.parent / "config" / "users.json"

ALLOW_AUTO_REGISTER = os.environ.get("ALLOW_AUTO_REGISTER", "false").lower() in (
    "1", "true", "yes", "on"
)
if ALLOW_AUTO_REGISTER:
    logger.warning("ALLOW_AUTO_REGISTER is enabled - unknown login emails may create accounts")

router = APIRouter(prefix="/auth", tags=["Client Auth"])

# JWT Secret (in Produktion aus ENV laden!)
JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    import secrets
    JWT_SECRET = secrets.token_hex(32)
    logger.warning("JWT_SECRET not set, using random secret (sessions won't persist across restarts)")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24


class ClientRole(str, Enum):
    ADMIN = "admin"          # Voller Zugriff (Markus)
    CLI_AGENT = "cli_agent"  # Server-Side Agents
    DESKTOP = "desktop"      # Desktop Clients
    MOBILE = "mobile"        # Mobile Clients (eingeschränkt)
    WEB = "web"              # Web Clients


# =============================================================================
# Client Registry
# =============================================================================

# In Produktion: Datenbank statt Dict
# Client Registry - dynamisch über API befüllt
# Keine hartcodierten Clients mehr - Registrierung erfolgt über /auth/register-client
CLIENT_REGISTRY: Dict[str, dict] = {}

# Default-Berechtigungen für neue Clients nach Rolle
DEFAULT_CLIENT_PERMISSIONS = {
    ClientRole.DESKTOP: {
        "allowed_tools": [
            "chat", "chat_smart", "weather", "current_time",
            "web_search", "smart_search", "multi_search",
            "client_*", "tristar_memory_*",
        ],
        "blocked_tools": [
            "codebase_*", "restart_*", "tristar_shell_exec", "vault_*",
        ]
    },
    ClientRole.CLI_AGENT: {
        "allowed_tools": ["chat", "chat_smart"],
        "blocked_tools": ["*"]  # Sehr eingeschränkt
    },
    ClientRole.WEB: {
        "allowed_tools": ["chat", "chat_smart", "web_search"],
        "blocked_tools": ["codebase_*", "restart_*", "tristar_shell_exec", "vault_*"]
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


def normalize_tier(tier: Optional[str]) -> str:
    """Normalize legacy/client tier names to the server-side tier contract."""
    raw = (tier or "guest").strip().lower()
    aliases = {
        "free": "guest",
        "basic": "guest",
        "paid": "pro",
        "premium": "pro",
        "admin": "enterprise",
        "unlimited": "enterprise",
    }
    normalized = aliases.get(raw, raw)
    if normalized in {"guest", "registered", "pro", "enterprise"}:
        return normalized
    logger.warning("Unknown user tier %r, falling back to guest", tier)
    return "guest"


def get_user_entitlements(user: Optional[dict]) -> Dict[str, Any]:
    """Return Nova/Copa product entitlements in a stable dict form."""
    if not user:
        return {}
    entitlements = user.get("nova_entitlements") or user.get("entitlements") or {}
    if isinstance(entitlements, dict):
        return entitlements
    if isinstance(entitlements, list):
        return {str(item): True for item in entitlements}
    return {}


def permissions_for_tier(tier: str) -> Tuple[ClientRole, List[str], List[str]]:
    """Map a user tier to client role and MCP tool permissions."""
    tier = normalize_tier(tier)
    if tier == "enterprise":
        return ClientRole.ADMIN, ["*"], []
    if tier == "pro":
        return (
            ClientRole.DESKTOP,
            [
                "chat", "chat_smart", "weather", "current_time",
                "web_search", "smart_search", "client_*", "tristar_memory_*",
            ],
            ["codebase_*", "restart_*", "vault_*", "tristar_shell_exec"],
        )
    if tier == "registered":
        return (
            ClientRole.DESKTOP,
            ["chat", "chat_smart", "weather", "current_time", "web_search", "client_*"],
            ["codebase_*", "restart_*", "vault_*", "tristar_shell_exec"],
        )
    return (
        ClientRole.DESKTOP,
        ["chat", "weather", "current_time", "web_search"],
        ["codebase_*", "restart_*", "vault_*", "tristar_*"],
    )


def create_jwt_token(
    client_id: str, 
    role: str, 
    email: str = None,
    entitlements: Optional[Dict[str, Any]] = None,
    name: Optional[str] = None,
    expires_hours: int = JWT_EXPIRY_HOURS
) -> str:
    """JWT Token erstellen - enthält Email für Tier-Lookup"""
    client_roles = {item.value for item in ClientRole}
    is_client_role = role in client_roles
    role = role if is_client_role else normalize_tier(role)
    payload = {
        "client_id": client_id,
        "role": role,  # tier: guest, registered, pro, enterprise
        "exp": datetime.utcnow() + timedelta(hours=expires_hours),
        "iat": datetime.utcnow()
    }
    if not is_client_role:
        payload["tier"] = role
    # Email im Token speichern für Tier-Service
    if email:
        payload["email"] = email
        payload["sub"] = email  # Standard JWT subject claim
    if name:
        payload["name"] = name
    if entitlements:
        payload["nova_entitlements"] = entitlements
        payload["entitlements"] = entitlements
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> dict:
    """JWT Token dekodieren"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


def decode_authorization_header(authorization: Optional[str]) -> dict:
    """Decode a Bearer Authorization header."""
    if not authorization:
        raise HTTPException(401, "Authorization header required")
    parts = authorization.strip().split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1]
    else:
        token = authorization.replace("Bearer ", "", 1).strip()
    if not token:
        raise HTTPException(401, "Authorization header required")
    return decode_jwt_token(token)


def build_verified_session(payload: dict) -> Dict[str, Any]:
    """Build the public auth session shape used by ai-coder and Copa."""
    email = (payload.get("email") or payload.get("sub") or "").lower()
    user = USER_REGISTRY.get(email, {}) if email else {}
    tier_source = payload.get("tier") or user.get("tier")
    if not tier_source and payload.get("role") in {"guest", "registered", "pro", "enterprise", "free"}:
        tier_source = payload.get("role")
    tier = normalize_tier(tier_source)
    entitlements = (
        payload.get("nova_entitlements")
        or payload.get("entitlements")
        or get_user_entitlements(user)
    )
    if not isinstance(entitlements, dict):
        entitlements = {}

    client_id = payload.get("client_id")
    return {
        "valid": True,
        "user_id": email or client_id,
        "email": email,
        "client_id": client_id,
        "tier": tier,
        "role": tier,
        "name": payload.get("name") or user.get("name"),
        "nova_entitlements": entitlements,
        "entitlements": entitlements,
        "expires_at": payload.get("exp"),
        "issued_at": payload.get("iat"),
    }


# =============================================================================
# User Registry (Simple User/Pass Auth)
# =============================================================================

# In Produktion: Datenbank!
# Tiers: guest (free), registered, pro, enterprise
# User Registry - dynamisch über Datenbank/API befüllt
# Keine hartcodierten User mehr - Authentifizierung erfolgt über /auth/login mit Client-Daten
# User-Daten werden vom Client bei Login mitgesendet und validiert
USER_REGISTRY: Dict[str, dict] = {}

def load_users_from_file() -> dict:
    """Lade alle User aus users.json"""
    users = {}
    
    # 1. Lade Admin aus ENV (falls gesetzt)
    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if admin_email and admin_password:
        users[admin_email.lower()] = {
            "password_hash": hash_secret(admin_password),
            "tier": "enterprise",
            "name": "Admin",
            "billing": False,
        }
    
    # 2. Lade registrierte User aus users.json
    if USERS_FILE_PATH.exists():
        try:
            with open(USERS_FILE_PATH, 'r') as f:
                saved_users = json.load(f)
                for email, data in saved_users.items():
                    # Überschreibe nicht den Admin
                    if email.lower() not in users:
                        users[email.lower()] = data
            logger.info(f"Loaded {len(saved_users)} users from {USERS_FILE_PATH}")
        except Exception as e:
            logger.error(f"Failed to load users: {e}")
    
    return users


def save_user_to_file(email: str, user_data: dict) -> bool:
    """Speichere neuen User in users.json"""
    try:
        # Lade existierende User
        users = {}
        if USERS_FILE_PATH.exists():
            with open(USERS_FILE_PATH, 'r') as f:
                users = json.load(f)
        
        # Füge neuen User hinzu
        users[email.lower()] = user_data
        
        # Speichere zurück
        USERS_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(USERS_FILE_PATH, 'w') as f:
            json.dump(users, f, indent=2)
        
        logger.info(f"Saved user {email} to {USERS_FILE_PATH}")
        return True
    except Exception as e:
        logger.error(f"Failed to save user {email}: {e}")
        return False


def register_new_user(email: str, password: str, name: str = None, tier: str = "guest") -> dict:
    """Registriere einen neuen User und speichere in users.json"""
    email = email.lower().strip()
    
    # Prüfe ob User bereits existiert
    if email in USER_REGISTRY:
        return None
    
    # Erstelle User-Daten
    user_data = {
        "password_hash": hash_secret(password),
        "tier": normalize_tier(tier),
        "name": name or email.split("@")[0],
        "billing": False,
        "nova_entitlements": {},
        "created_at": datetime.now().isoformat(),
    }
    
    # Speichere in Datei
    if save_user_to_file(email, user_data):
        # Füge zu Registry hinzu
        USER_REGISTRY[email] = user_data
        return user_data
    
    return None


# Lade User beim Start
USER_REGISTRY.update(load_users_from_file())


# =============================================================================
# Request/Response Models
# =============================================================================

class UserLoginRequest(BaseModel):
    """User Login Request - email/password (auto-registers new users)"""
    email: str = Field(..., description="Email address")
    password: str = Field(..., description="Password")
    name: Optional[str] = Field(None, description="Display name (optional, for new users)")


class UserLoginResponse(BaseModel):
    """User Login Response"""
    user_id: str
    token: str
    token_type: str = "Bearer"
    expires_in: int = JWT_EXPIRY_HOURS * 3600
    tier: str
    client_id: str  # Server-assigned per login
    email: str
    name: Optional[str] = None
    nova_entitlements: Dict[str, Any] = Field(default_factory=dict)
    entitlements: Dict[str, Any] = Field(default_factory=dict)



# User Register Models (für explizite Registrierung mit Beta-Code)
class UserRegisterRequest(BaseModel):
    """User Registration Request"""
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=6, description="Password (min 6 chars)")
    name: Optional[str] = Field(None, description="Display name")
    beta_code: Optional[str] = Field(None, description="Beta code for tier upgrade")


class UserRegisterResponse(BaseModel):
    """User Registration Response"""
    success: bool
    message: str
    tier: str
    email: str


# Beta codes für Tier-Upgrades
BETA_CODES = {
    "AILINUX2026": "pro",
    "TRIFORCE": "pro",
    "MARKUS": "enterprise",
    "ADMIN": "enterprise",
}

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

@router.post("/login", response_model=UserLoginResponse)
async def user_login(request: UserLoginRequest):
    """
    User Login with email/password
    Server assigns a new client_id per login
    """
    email = request.email.lower().strip()
    user = USER_REGISTRY.get(email)

    # Login darf standardmäßig keine Accounts erzeugen.
    # Registrierung läuft ausschließlich über /register bzw. WordPress/login.ailinux.me.
    if not user:
        if not ALLOW_AUTO_REGISTER:
            logger.warning(f"Login attempt for unknown email: {email}")
            raise HTTPException(401, "Invalid email or password")

        logger.warning(f"Auto-registering unknown email via login because ALLOW_AUTO_REGISTER=true: {email}")
        user = register_new_user(
            email=email,
            password=request.password,
            name=request.name if hasattr(request, 'name') and request.name else None,
            tier="guest"
        )
        if not user:
            logger.error(f"Failed to register new user: {email}")
            raise HTTPException(500, "Failed to register user")
        logger.warning(f"New user auto-registered via login: {email} (tier: guest)")
    else:
        # Existierender User - Passwort prüfen
        if not verify_secret(request.password, user["password_hash"]):
            logger.warning(f"Invalid password for: {email}")
            raise HTTPException(401, "Invalid email or password")

    # Generate new client_id for this login session
    email_prefix = email.split("@")[0][:10]
    client_id = f"client-{email_prefix}-{secrets.token_hex(8)}"

    tier = normalize_tier(user.get("tier"))
    entitlements = get_user_entitlements(user)
    role, allowed, blocked = permissions_for_tier(tier)

    # Create JWT token MIT EMAIL (wichtig für Tier-Service!)
    token = create_jwt_token(
        client_id,
        tier,
        email=email,
        entitlements=entitlements,
        name=user.get("name"),
    )

    # Register client session
    CLIENT_REGISTRY[client_id] = {
        "secret_hash": "",
        "name": f"{user['name']}'s Client",
        "role": role,
        "created_at": datetime.now().isoformat(),
        "email": email,
        "allowed_tools": allowed,
        "blocked_tools": blocked
    }

    # Track session
    ACTIVE_SESSIONS[client_id] = {
        "email": email,
        "connected_at": datetime.now().isoformat(),
        "last_seen": datetime.now().isoformat()
    }

    logger.info(f"User logged in: {email} ({tier}) -> {client_id}")

    return UserLoginResponse(
        user_id=email,
        token=token,
        tier=tier,
        client_id=client_id,
        email=email,
        name=user.get("name"),
        nova_entitlements=entitlements,
        entitlements=entitlements,
    )


@router.get("/verify")
async def verify_auth(authorization: str = Header(None)):
    """
    Validate a user/client JWT and return the session contract used by desktop clients.
    """
    payload = decode_authorization_header(authorization)
    return build_verified_session(payload)


@router.get("/client/handshake")
async def client_handshake(authorization: str = Header(None)):
    """
    Return client capabilities and canonical endpoint paths after authentication.
    """
    payload = decode_authorization_header(authorization)
    session = build_verified_session(payload)
    tier = session["tier"]
    default_role, default_allowed, default_blocked = permissions_for_tier(tier)

    client_id = session.get("client_id")
    client = CLIENT_REGISTRY.get(client_id, {}) if client_id else {}
    allowed_tools = client.get("allowed_tools") or default_allowed
    blocked_tools = client.get("blocked_tools") or default_blocked
    role = client.get("role") or default_role
    role_value = role.value if isinstance(role, ClientRole) else role

    if client_id in ACTIVE_SESSIONS:
        ACTIVE_SESSIONS[client_id]["last_seen"] = datetime.now().isoformat()

    return {
        "ok": True,
        "valid": True,
        "client_id": client_id,
        "user_id": session.get("user_id"),
        "email": session.get("email"),
        "tier": tier,
        "role": role_value,
        "allowed_tools": allowed_tools,
        "blocked_tools": blocked_tools,
        "capabilities": {
            "chat": True,
            "models": True,
            "mcp": True,
            "ocr": bool(session.get("nova_entitlements", {}).get("copa_ocr")) or tier in {"pro", "enterprise"},
        },
        "endpoints": {
            "auth_verify": "/v1/auth/verify",
            "chat": "/v1/client/chat",
            "models": "/v1/client/models",
            "mcp": "/v1/mcp",
            "ocr_mistral": "/v1/client/ocr/mistral",
            "ocr_status": "/v1/client/ocr/status",
        },
        "nova_entitlements": session.get("nova_entitlements", {}),
        "entitlements": session.get("entitlements", {}),
    }


@router.post("/register", response_model=UserRegisterResponse)
async def user_register(request: UserRegisterRequest):
    """
    Register a new user account.
    Beta phase: All accounts get PRO tier automatically!
    """
    email = request.email.lower().strip()
    
    # Prüfe ob User bereits existiert
    if email in USER_REGISTRY:
        raise HTTPException(400, "Email already registered. Please login instead.")
    
    # Bestimme Tier basierend auf Beta-Code
    tier = "pro"  # Beta: Alle bekommen PRO!
    if request.beta_code:
        beta_tier = BETA_CODES.get(request.beta_code.upper())
        if beta_tier:
            tier = beta_tier
            logger.info(f"Beta code used: {request.beta_code} -> {tier}")
    
    # Registriere neuen User
    user = register_new_user(
        email=email,
        password=request.password,
        name=request.name,
        tier=tier
    )
    
    if not user:
        raise HTTPException(500, "Failed to register user")
    
    logger.info(f"New user registered: {email} (tier: {tier})")
    
    return UserRegisterResponse(
        success=True,
        message=f"Account created! Tier: {tier.upper()}",
        tier=tier,
        email=email
    )



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
