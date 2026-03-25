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


# ═══ WordPress Auth Bridge ═══════════════════════════════════════════════════
# Swarm-Clients melden sich über login.ailinux.me (WordPress) an.
# Validierung über WP-CLI check-password im wordpress_fpm Container.

WP_CONTAINER = "wordpress_fpm"
WP_CLI = "php /var/www/html/wp-cli.phar --allow-root --path=/var/www/html"

def _wp_cmd(cmd: str, json_output: bool = False) -> str:
    """WP-CLI im Docker-Container ausführen."""
    import subprocess
    fmt = " --format=json" if json_output else ""
    full = f"docker exec {WP_CONTAINER} {WP_CLI} {cmd}{fmt}"
    try:
        r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=10)
        out = r.stdout.strip()
        # WP-CLI Notices filtern
        lines = [l for l in out.splitlines()
                 if not l.startswith("Notice:") and not l.startswith("Warning:")
                 and "sendmail" not in l and "textdomain" not in l.lower()]
        return "\n".join(lines).strip()
    except Exception as e:
        logger.warning(f"WP-CLI failed: {e}")
        return ""


def wp_verify_password(login: str, password: str) -> bool:
    """WordPress-Passwort validieren via WP-CLI check-password."""
    import shlex
    safe_login = shlex.quote(login)
    safe_pass = shlex.quote(password)
    result = _wp_cmd(f"user check-password {safe_login} {safe_pass}")
    # check-password gibt nichts aus bei Erfolg (exit 0), "Error" bei Fehler
    return "Error" not in result and "error" not in result.lower()


def wp_get_user(login_or_email: str) -> Optional[dict]:
    """WordPress-Userdaten holen (ID, login, email, roles, display_name)."""
    import shlex, json as _json
    safe = shlex.quote(login_or_email)
    raw = _wp_cmd(f"user get {safe} --fields=ID,user_login,user_email,display_name,roles", json_output=True)
    if not raw:
        return None
    try:
        data = _json.loads(raw)
        return data
    except Exception:
        return None


def wp_authenticate(email: str, password: str) -> Optional[dict]:
    """
    Kompletter WordPress-Auth-Flow:
    1. Passwort prüfen (erst per email, dann per login)
    2. Userdaten holen
    3. Tier + account_role ableiten

    Returns: {"email": ..., "name": ..., "tier": ..., "account_role": ..., "wp_roles": ...}
    """
    # Erst als Email probieren, dann als Username
    verified = wp_verify_password(email, password)
    if not verified:
        # Vielleicht ist es der Username statt Email
        user_data = wp_get_user(email)
        if user_data:
            verified = wp_verify_password(user_data.get("user_login", email), password)
        if not verified:
            return None

    # Userdaten holen
    user = wp_get_user(email)
    if not user:
        return None

    wp_roles = user.get("roles", "subscriber").lower()

    # Role-Mapping: WP → TriForce
    if "administrator" in wp_roles:
        account_role = "admin"
        tier = "subscription"  # Admin = voller Zugang
    elif "editor" in wp_roles or "author" in wp_roles:
        account_role = "client"
        tier = "subscription"
    else:
        # subscriber / contributor / default
        account_role = "client"
        tier = "free"  # Free bis Abo abgeschlossen

    return {
        "email": user.get("user_email", email),
        "name": user.get("display_name", email.split("@")[0]),
        "tier": tier,
        "account_role": account_role,
        "wp_roles": wp_roles,
        "wp_id": user.get("ID"),
    }


def _wp_create_user(
    email: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
    display_name: str = "",
    role: str = "subscriber",
) -> bool:
    """Neuen WordPress-User anlegen via WP-CLI.
    Gibt True zurück wenn erfolgreich."""
    import shlex
    safe_email = shlex.quote(email)
    safe_pass = shlex.quote(password)
    login = email.split("@")[0][:20].replace(".", "").replace("+", "")
    safe_login = shlex.quote(login)
    safe_display = shlex.quote(display_name or f"{first_name} {last_name}".strip() or login)
    safe_first = shlex.quote(first_name)
    safe_last = shlex.quote(last_name)

    cmd = (
        f"user create {safe_login} {safe_email}"
        f" --user_pass={safe_pass}"
        f" --display_name={safe_display}"
        f" --first_name={safe_first}"
        f" --last_name={safe_last}"
        f" --role={role}"
    )
    result = _wp_cmd(cmd)
    if "Success" in result or "Created" in result or "already exists" in result.lower():
        logger.info(f"WordPress user created: {email} ({role})")
        return True
    if "already exists" in result.lower():
        logger.info(f"WordPress user already exists: {email}")
        return True
    logger.warning(f"WordPress user creation unclear: {result}")
    return "error" not in result.lower()



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
    expires_hours: int = JWT_EXPIRY_HOURS,
    account_role: str = "admin",
) -> str:
    """JWT Token erstellen mit account_role für RBAC (HS256, ohne externe Lib)
    
    role = Tier/Plan (free/subscription/software) — für Model-Zugang
    account_role = RBAC-Rolle (admin/client) — für Server-Verwaltung
    Bestehende Tokens ohne account_role → default "admin" (Markus nie aussperren)
    """
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "client_id": client_id,
        "role": role,  # tier: free/subscription/software
        "account_role": account_role,  # RBAC: "admin" oder "client"
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
    # SWARM RBAC: bestehende Tokens ohne account_role → "admin" (backward compat)
    if "account_role" not in payload:
        payload["account_role"] = "admin"
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


def register_new_user(
    email: str,
    password: str,
    name: str = None,
    tier: str = "free",
    first_name: str = "",
    last_name: str = "",
    date_of_birth: str = "",
    street: str = "",
    zip_code: str = "",
    city: str = "",
    country: str = "DE",
) -> dict:
    """Registriere einen neuen User und speichere in users.json"""
    email = email.lower().strip()
    
    # Prüfe ob User bereits existiert
    if email in USER_REGISTRY:
        return None
    
    # Erstelle User-Daten
    display_name = name or f"{first_name} {last_name}".strip() or email.split("@")[0]
    user_data = {
        "password_hash": hash_secret(password),
        "tier": tier,
        "name": display_name,
        "first_name": first_name,
        "last_name": last_name,
        "date_of_birth": date_of_birth,
        "address": {
            "street": street,
            "zip_code": zip_code,
            "city": city,
            "country": country,
        },
        "billing": False,
        "account_role": "client",
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
    tier: str                        # free/subscription/software
    plan: str                        # free/subscription/software
    is_paid: bool                    # Abo aktiv?
    client_id: str                   # Server-assigned per login
    account_role: str = "client"     # RBAC: admin/client



# User Register Models (für explizite Registrierung mit Beta-Code)
class UserRegisterRequest(BaseModel):
    """User Registration Request — Pflichtfelder für Vermarktung + Recovery"""
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=6, description="Password (min 6 chars)")
    first_name: str = Field(..., min_length=1, description="Vorname")
    last_name: str = Field(..., min_length=1, description="Nachname")
    date_of_birth: str = Field(..., description="Geburtsdatum (YYYY-MM-DD) — Pflicht für Account-Recovery")
    street: str = Field(..., min_length=1, description="Straße + Hausnummer")
    zip_code: str = Field(..., min_length=3, description="Postleitzahl")
    city: str = Field(..., min_length=1, description="Stadt")
    country: str = Field("DE", description="Land (ISO 3166-1 alpha-2, z.B. DE, AT, CH)")
    beta_code: Optional[str] = Field(None, description="Beta code for tier upgrade")
    accept_terms: bool = Field(False, description="AGB + Datenschutz akzeptiert")


class UserRegisterResponse(BaseModel):
    """User Registration Response"""
    success: bool
    message: str
    tier: str
    email: str
    user_id: Optional[str] = None
    wp_synced: bool = False


# Beta codes für Tier-Upgrades
BETA_CODES = {
    "AILINUX2026": "subscription",
    "TRIFORCE": "subscription",
    "SWARM2026": "subscription",
    "MARKUS": "subscription",   # Admin-Rolle wird separat über account_role gesetzt
    "ADMIN": "subscription",
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

    # ═══ SCHRITT 1: WordPress-Auth (login.ailinux.me) ═══
    # Swarm-Clients melden sich über WordPress an
    wp_user = None
    try:
        wp_user = wp_authenticate(email, request.password)
    except Exception as e:
        logger.warning(f"WordPress auth unavailable: {e}")

    if wp_user:
        # WordPress-User gefunden und Passwort korrekt
        logger.info(f"WordPress auth OK: {email} (wp_roles={wp_user['wp_roles']})")
        user = {
            "password_hash": "",  # nicht nötig, WP hat validiert
            "tier": wp_user["tier"],
            "name": wp_user["name"],
            "billing": wp_user["tier"] == "subscription",
            "_account_role": wp_user["account_role"],
            "_source": "wordpress",
        }
    else:
        # ═══ SCHRITT 2: Fallback auf lokale users.json ═══
        USER_REGISTRY.update(load_users_from_file())
        user = USER_REGISTRY.get(email)

        if not user:
            # Auto-Registrierung: neuer lokaler User
            logger.info(f"New local user registration: {email}")
            user = register_new_user(
                email=email,
                password=request.password,
                name=request.name if hasattr(request, 'name') and request.name else None,
                tier="free"
            )
            if not user:
                logger.error(f"Failed to register new user: {email}")
                raise HTTPException(500, "Failed to register user")
            logger.info(f"New local user registered: {email} (tier: free)")
        else:
            # Lokaler User — Passwort prüfen
            if not verify_secret(request.password, user["password_hash"]):
                logger.warning(f"Invalid password for: {email}")
                raise HTTPException(401, "Invalid email or password")

    # Generate new client_id for this login session
    email_prefix = email.split("@")[0][:10]
    client_id = f"client-{email_prefix}-{secrets.token_hex(8)}"

    # Determine role: Admin (WP admin / enterprise) vs Desktop (alle anderen)
    # Alle Tools offen für jeden — kein Tool-Filtering
    from ..services.user_tiers import has_full_access
    _is_admin = user.get("_account_role") == "admin" or user["tier"] in ("enterprise", "admin")
    role = ClientRole.ADMIN if _is_admin else ClientRole.DESKTOP
    allowed = ["*"]  # Alle Tools offen
    blocked = []

    # Create JWT token MIT EMAIL + account_role
    from ..services.user_tiers import normalize_tier
    _norm_tier = normalize_tier(user["tier"]).value  # → "free"/"subscription"/"software"
    # SWARM RBAC: WP-Rolle hat Vorrang, sonst aus Tier ableiten
    _account_role = user.get("_account_role") or ("admin" if user["tier"] in ("enterprise", "admin") else "client")
    token = create_jwt_token(client_id, _norm_tier, email=email, account_role=_account_role)

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
        tier=_norm_tier,
        plan=_plan.value,
        is_paid=_plan.value == "subscription",
        client_id=client_id,
        account_role=_account_role,
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
    _acct_role = payload.get("account_role", "admin")  # backward compat

    return {
        "valid": True,
        "email": email,
        "tier": role,
        "plan": _vplan.value,
        "is_paid": _vplan.value == "subscription",
        "account_role": _acct_role,
        "client_id": client_id,
        "exp": payload.get("exp"),
        "iat": payload.get("iat"),
    }


@router.post("/register", response_model=UserRegisterResponse)
async def user_register(request: UserRegisterRequest):
    """
    Register a new user account.
    Erweitert mit Name, Geburtsdatum, Anschrift für Vermarktung.
    """
    email = request.email.lower().strip()

    # AGB-Check
    if not request.accept_terms:
        raise HTTPException(400, "Du musst die AGB und Datenschutzerklärung akzeptieren.")

    # Alters-Check (optional, wenn Geburtsdatum angegeben)
    if request.date_of_birth:
        try:
            from datetime import date
            dob = date.fromisoformat(request.date_of_birth)
            age = (date.today() - dob).days // 365
            if age < 16:
                raise HTTPException(400, "Mindestalter: 16 Jahre.")
        except ValueError:
            raise HTTPException(400, "Ungültiges Geburtsdatum. Format: YYYY-MM-DD")

    # Prüfe ob User bereits existiert
    USER_REGISTRY.update(load_users_from_file())
    if email in USER_REGISTRY:
        raise HTTPException(400, "Email already registered. Please login instead.")

    # WordPress-User prüfen
    wp_exists = wp_get_user(email)
    if wp_exists:
        raise HTTPException(400, "Email bereits bei login.ailinux.me registriert. Bitte dort einloggen.")

    # Bestimme Tier basierend auf Beta-Code
    tier = "free"  # Default: Free
    if request.beta_code:
        beta_tier = BETA_CODES.get(request.beta_code.upper())
        if beta_tier:
            from ..services.user_tiers import normalize_tier
            tier = normalize_tier(beta_tier).value
            logger.info(f"Beta code used: {request.beta_code} -> {tier}")

    # Registriere lokal
    user = register_new_user(
        email=email,
        password=request.password,
        first_name=request.first_name,
        last_name=request.last_name,
        date_of_birth=request.date_of_birth or "",
        street=request.street or "",
        zip_code=request.zip_code or "",
        city=request.city or "",
        country=request.country or "DE",
        tier=tier,
    )

    if not user:
        raise HTTPException(500, "Failed to register user")

    # WordPress-User anlegen (Sync)
    wp_synced = False
    try:
        wp_synced = _wp_create_user(
            email=email,
            password=request.password,
            first_name=request.first_name,
            last_name=request.last_name,
            display_name=user["name"],
        )
    except Exception as e:
        logger.warning(f"WordPress user sync failed (nicht kritisch): {e}")

    logger.info(f"New user registered: {email} (tier: {tier}, wp_synced={wp_synced})")

    return UserRegisterResponse(
        success=True,
        message=f"Account erstellt! Willkommen bei AILinux.",
        tier=tier,
        email=email,
        user_id=email,
        wp_synced=wp_synced,
    )




# =============================================================================
# Identity-based Account Recovery (kein Email-Zugang nötig)
# =============================================================================

class IdentityRecoveryRequest(BaseModel):
    """Account-Recovery über persönliche Daten — wenn Email-Zugang verloren."""
    email: str = Field(..., description="Email des Accounts")
    first_name: str = Field(..., description="Vorname (wie bei Registrierung)")
    last_name: str = Field(..., description="Nachname")
    date_of_birth: str = Field(..., description="Geburtsdatum (YYYY-MM-DD)")
    zip_code: str = Field(..., description="PLZ (wie bei Registrierung)")
    new_password: str = Field(..., min_length=6, description="Neues Passwort")
    new_email: Optional[str] = Field(None, description="Neue Email (optional, wenn alte nicht mehr erreichbar)")


@router.post("/recover-identity")
async def recover_by_identity(request: IdentityRecoveryRequest):
    """
    Account-Recovery über Identitätsverifizierung.
    Prüft: Email + Vorname + Nachname + Geburtsdatum + PLZ.
    Alle 5 müssen übereinstimmen → neues Passwort setzen.
    """
    email = request.email.lower().strip()

    # User laden
    USER_REGISTRY.update(load_users_from_file())
    user = USER_REGISTRY.get(email)

    if not user:
        # Kein User-Enumeration: gleiche Antwort wie bei Mismatch
        logger.warning(f"Identity recovery: user not found {email}")
        raise HTTPException(400, "Identität konnte nicht verifiziert werden.")

    # Alle 5 Felder müssen matchen (case-insensitive, stripped)
    checks = [
        (user.get("first_name", "").strip().lower(), request.first_name.strip().lower(), "first_name"),
        (user.get("last_name", "").strip().lower(), request.last_name.strip().lower(), "last_name"),
        (user.get("date_of_birth", "").strip(), request.date_of_birth.strip(), "dob"),
        (user.get("address", {}).get("zip_code", "").strip(), request.zip_code.strip(), "zip"),
    ]

    mismatches = [name for stored, given, name in checks if stored != given]
    if mismatches:
        logger.warning(f"Identity recovery failed for {email}: mismatches={mismatches}")
        raise HTTPException(400, "Identität konnte nicht verifiziert werden.")

    # Verifiziert → Passwort ändern
    user["password_hash"] = hash_secret(request.new_password)

    # Optional: Email ändern
    if request.new_email and request.new_email.lower().strip() != email:
        new_email = request.new_email.lower().strip()
        if new_email in USER_REGISTRY:
            raise HTTPException(400, "Die neue Email ist bereits vergeben.")
        # Alten Eintrag entfernen, neuen anlegen
        save_user_to_file(new_email, user)
        USER_REGISTRY[new_email] = user
        # Alten löschen
        users = {}
        if USERS_FILE_PATH.exists():
            with open(USERS_FILE_PATH, 'r') as f:
                users = json.load(f)
        if email in users:
            del users[email]
            with open(USERS_FILE_PATH, 'w') as f:
                json.dump(users, f, indent=2)
        if email in USER_REGISTRY:
            del USER_REGISTRY[email]
        logger.info(f"Identity recovery: email changed {email} → {new_email}")
        email = new_email
    else:
        save_user_to_file(email, user)
        USER_REGISTRY[email] = user

    # WordPress-Passwort auch updaten
    try:
        import shlex
        safe_email = shlex.quote(email)
        safe_pass = shlex.quote(request.new_password)
        _wp_cmd(f"user update {safe_email} --user_pass={safe_pass}")
        logger.info(f"WordPress password updated for {email}")
    except Exception as e:
        logger.warning(f"WordPress password sync failed: {e}")

    logger.info(f"Identity recovery successful for {email}")
    return {
        "ok": True,
        "email": email,
        "message": "Identität verifiziert. Passwort wurde zurückgesetzt.",
    }


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
async def client_handshake(
    authorization: str = Header(None),
    user_agent: str = Header(None, alias="User-Agent"),
):
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
    from ..routes.client_mcp import get_tools_for_tier, FREE_TIER_TOOLS, ENTERPRISE_TIER_TOOLS, CODING_SCOPE_TOOLS
    from ..services.user_tiers import UserTier
    try:
        tier_obj = UserTier(role)
    except ValueError:
        tier_obj = UserTier.FREE
    tools = get_tools_for_tier(tier_obj)

    # Option A: User-Agent-basierter Scope für ai-coder Coding-Client
    # ALLE User (inkl. Admin) bekommen READ-ONLY MCP-Scope.
    # Execution (shell, code_edit etc.) läuft LOKAL auf der User-Maschine via subprocess.
    _ua = (user_agent or "").lower()
    if _ua.startswith("ai-coder"):
        tools = [t for t in tools if t in CODING_SCOPE_TOOLS]
        if not tools:
            tools = CODING_SCOPE_TOOLS  # fallback

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
