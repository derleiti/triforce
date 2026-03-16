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
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import secrets
import logging
import hmac
import base64
import json as jsonlib

# Pfad zur User-Datenbank
USERS_FILE_PATH = Path(__file__).parent.parent.parent / "config" / "users.json"
logger = logging.getLogger(__name__)

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


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_jwt_token(
    client_id: str,
    role: str,
    email: str = None,
    expires_hours: int = JWT_EXPIRY_HOURS
) -> str:
    """JWT Token erstellen - enthält Email für Tier-Lookup (HS256, ohne externe Lib)"""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "client_id": client_id,
        "role": role,  # tier: guest, registered, pro, enterprise
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=expires_hours)).timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp())
    }
    if email:
        payload["email"] = email
        payload["sub"] = email

    signing_input = ".".join([
        _b64url_encode(jsonlib.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")),
        _b64url_encode(jsonlib.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    ])
    signature = hmac.new(
        JWT_SECRET.encode("utf-8"),
        signing_input.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    return signing_input + "." + _b64url_encode(signature)


def decode_jwt_token(token: str) -> dict:
    """JWT Token dekodieren und Signatur prüfen (HS256)"""
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(401, "Invalid token")

    signing_input = ".".join(parts[:2])
    signature = parts[2]
    expected_sig = _b64url_encode(
        hmac.new(
            JWT_SECRET.encode("utf-8"),
            signing_input.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
    )
    if not hmac.compare_digest(signature, expected_sig):
        raise HTTPException(401, "Invalid token signature")

    try:
        payload = jsonlib.loads(_b64url_decode(parts[1]))
    except Exception:
        raise HTTPException(401, "Invalid token payload")

    exp = payload.get("exp")
    if exp and datetime.now(timezone.utc).timestamp() > float(exp):
        raise HTTPException(401, "Token expired")
    return payload


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


def register_new_user(email: str, password: str, name: str = None, tier: str = "free") -> dict:
    """Registriere einen neuen User und speichere in users.json"""
    email = email.lower().strip()
    
    # Prüfe ob User bereits existiert
    if email in USER_REGISTRY:
        return None
    
    # Erstelle User-Daten
    user_data = {
        "password_hash": hash_secret(password),
        "tier": tier,
        "name": name or email.split("@")[0],
        "billing": False,
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
    tier: str        # Legacy: enterprise/pro/free
    plan: str        # Klar: demo | subscriber
    is_paid: bool    # Bezahlstatus
    client_id: str   # Server-assigned per login



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
    # Immer frisch aus Datei lesen – damit Passwort-/Tier-Aenderungen ohne Restart wirksam sind
    USER_REGISTRY.update(load_users_from_file())
    user = USER_REGISTRY.get(email)

    # Auto-Registrierung: Wenn User nicht existiert, registriere neuen User
    if not user:
        # Neuen User registrieren (erster Login = Registrierung)
        logger.info(f"New user registration via login: {email}")
        user = register_new_user(
            email=email,
            password=request.password,
            name=request.name if hasattr(request, 'name') and request.name else None,
            tier="free"  # Neue User starten als "free"
        )
        if not user:
            logger.error(f"Failed to register new user: {email}")
            raise HTTPException(500, "Failed to register user")
        logger.info(f"New user registered: {email} (tier: free)")
    else:
        # Existierender User - Passwort prüfen
        if not verify_secret(request.password, user["password_hash"]):
            logger.warning(f"Invalid password for: {email}")
            raise HTTPException(401, "Invalid email or password")

    # Generate new client_id for this login session
    email_prefix = email.split("@")[0][:10]
    client_id = f"client-{email_prefix}-{secrets.token_hex(8)}"

    # Determine role based on tier
    if user["tier"] == "enterprise":
        role = ClientRole.ADMIN
        allowed = ["*"]
        blocked = []
    elif user["tier"] == "pro":
        role = ClientRole.DESKTOP
        allowed = ["chat", "chat_smart", "weather", "current_time",
                   "web_search", "smart_search", "client_*", "tristar_memory_*"]
        blocked = ["codebase_*", "restart_*", "vault_*", "tristar_shell_exec"]
    else:  # free
        role = ClientRole.DESKTOP
        allowed = ["chat", "weather", "current_time", "web_search"]
        blocked = ["codebase_*", "restart_*", "vault_*", "tristar_*"]

    # Create JWT token MIT EMAIL (wichtig für Tier-Service!)
    # FIX 2026-03-11: normalize legacy enterprise/pro to free/paid before storing in JWT
    from ..services.user_tiers import normalize_tier
    _norm_tier = normalize_tier(user["tier"]).value  # → "free" or "paid"
    token = create_jwt_token(client_id, _norm_tier, email=email)

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

    logger.info(f"User logged in: {email} ({user['tier']}) -> {client_id}")

    from ..services.subscription import tier_to_plan
    _plan = tier_to_plan(user["tier"])

    return UserLoginResponse(
        user_id=email,
        token=token,
        tier=user["tier"],
        plan=_plan.value,
        is_paid=_plan.value == "subscriber",
        client_id=client_id
    )


@router.get("/verify")
async def verify_token(authorization: str = Header(None), token: str = None):
    """
    Verify JWT tokens for external callers (WordPress, clients).
    Accepts Authorization: Bearer <token> or query/body param `token`.
    """
    raw = None
    if authorization and authorization.lower().startswith("bearer "):
        raw = authorization.split(" ", 1)[1].strip()
    elif token:
        raw = token.strip()

    if not raw:
        raise HTTPException(401, "Missing token")

    payload = decode_jwt_token(raw)
    email = payload.get("email") or payload.get("sub")
    role = payload.get("role") or payload.get("tier")
    client_id = payload.get("client_id")

    from ..services.subscription import tier_to_plan
    _vplan = tier_to_plan(role)

    return {
        "valid": True,
        "email": email,
        "tier": role,
        "plan": _vplan.value,
        "is_paid": _vplan.value == "subscriber",
        "client_id": client_id,
        "exp": payload.get("exp"),
        "iat": payload.get("iat"),
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
    
    # Token generieren (FIX 2026-03-11: normalize legacy tier to free/paid)
    from ..services.user_tiers import normalize_tier as _nt
    _role_norm = _nt(client["role"].value if hasattr(client["role"], "value") else str(client["role"])).value
    token = create_jwt_token(request.client_id, _role_norm)
    
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
    except Exception:
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


# =============================================================================
# Handshake Endpoint — Client-Init beim Connect
# =============================================================================

@router.get("/client/handshake")
async def client_handshake(authorization: str = Header(None)):
    """
    Client-Handshake beim Start.
    Gibt Plan, Quota, erlaubte Tools und Context-Limit zurueck.
    Kein zweiter Request nötig.
    """
    if not authorization:
        raise HTTPException(401, "Authorization header required")

    token = authorization.replace("Bearer ", "")
    payload = decode_jwt_token(token)

    client_id = payload.get("client_id")
    user_id   = payload.get("sub") or client_id
    role      = payload.get("role", "guest")


    from ..services.subscription import subscription_service, PlanType, tier_to_plan

    plan = tier_to_plan(role)
    quota = subscription_service.get_quota(user_id, plan)

    # Erlaubte Tools
    from ..routes.client_mcp import get_tools_for_tier, FREE_TIER_TOOLS, ENTERPRISE_TIER_TOOLS
    from ..services.user_tiers import UserTier
    try:
        tier_obj = UserTier(role)
    except ValueError:
        tier_obj = UserTier.GUEST
    tools = get_tools_for_tier(tier_obj)

    return {
        "client_id":     client_id,
        "user_id":       user_id,
        "plan":          plan.value,
        "context_limit": subscription_service.get_context_limit(plan),
        "tools":         tools,
        "tool_count":    len(tools),
        "quota":         quota.to_api(),
    }


# =============================================================================
# Password Reset (Forgot Password)
# =============================================================================

# In-Memory Reset-Token Store (Redis wäre besser, reicht für jetzt)
_RESET_TOKENS: Dict[str, dict] = {}  # token → {email, expires}


class PasswordResetRequestModel(BaseModel):
    email: str = Field(..., description="E-Mail-Adresse des Accounts")


class PasswordResetModel(BaseModel):
    token: str = Field(..., description="Reset-Token aus der E-Mail")
    new_password: str = Field(..., min_length=6, description="Neues Passwort (min 6 Zeichen)")


@router.post("/forgot-password")
async def forgot_password(request: PasswordResetRequestModel):
    """
    Passwort-Reset anfordern — sendet E-Mail mit Reset-Link an nova@ailinux.me.
    Gibt immer 200 zurück (kein User-Enumeration).
    """
    email = request.email.lower().strip()

    # Prüfe ob User existiert (still, kein 404)
    USER_REGISTRY.update(load_users_from_file())
    user = USER_REGISTRY.get(email)

    if user:
        # Reset-Token generieren (1h gültig)
        token = secrets.token_urlsafe(32)
        _RESET_TOKENS[token] = {
            "email": email,
            "expires": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
        }

        reset_url = f"https://login.ailinux.me/?reset_token={token}"

        # Mail direkt via mail_service.mail_send (SMTP)
        try:
            import asyncio as _aio
            from app.services.mail_service import mail_send as _mail_send
            _body = (
                f"Hallo,\n\n"
                f"du hast einen Passwort-Reset für deinen AILinux-Account ({email}) angefordert.\n\n"
                f"Klicke auf diesen Link um ein neues Passwort zu setzen (gültig 1 Stunde):\n"
                f"{reset_url}\n\n"
                f"Falls du das nicht warst, ignoriere diese E-Mail.\n\n"
                f"– Nova / AILinux Team\n"
                f"nova@ailinux.me | https://ailinux.me"
            )
            # mail_send ist sync — in threadpool mit Timeout
            try:
                result = await _aio.wait_for(
                    _aio.get_event_loop().run_in_executor(
                        None, lambda: _mail_send(
                            to=email,
                            subject="AILinux – Passwort zurücksetzen",
                            body=_body,
                            reply_to="nova@ailinux.me",
                        )
                    ),
                    timeout=10.0
                )
                logger.info(f"Password reset mail sent to {email}: {result}")
            except _aio.TimeoutError:
                logger.warning(f"Reset mail timeout for {email} — mail queued anyway")
        except Exception as e:
            logger.warning(f"Reset mail failed: {e}")

    return {"ok": True, "message": "Falls ein Account mit dieser E-Mail existiert, wurde ein Reset-Link gesendet."}


@router.post("/reset-password")
async def reset_password(request: PasswordResetModel):
    """
    Passwort mit Reset-Token setzen.
    """
    token_data = _RESET_TOKENS.get(request.token)
    if not token_data:
        raise HTTPException(400, "Ungültiger oder abgelaufener Reset-Token")

    if datetime.now(timezone.utc).timestamp() > token_data["expires"]:
        del _RESET_TOKENS[request.token]
        raise HTTPException(400, "Reset-Token abgelaufen (gültig 1 Stunde)")

    email = token_data["email"]

    # Neues Passwort speichern
    USER_REGISTRY.update(load_users_from_file())
    user = USER_REGISTRY.get(email)
    if not user:
        raise HTTPException(404, "User nicht gefunden")

    user["password_hash"] = hash_secret(request.new_password)
    save_user_to_file(email, user)
    USER_REGISTRY[email] = user

    # Token invalidieren
    del _RESET_TOKENS[request.token]

    logger.info(f"Password reset successful for {email}")
    return {"ok": True, "message": "Passwort erfolgreich geändert. Du kannst dich jetzt einloggen."}
