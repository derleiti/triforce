from fastapi import APIRouter, Depends, Request, Response, Form, Cookie, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from typing import Optional
import secrets
import time
from pathlib import Path
from ..config import get_settings

router = APIRouter(tags=["GUI"])

# =========================================================================
# Session-based Authentication for TriStar GUI
# Credentials from .env: TRISTAR_GUI_USER, TRISTAR_GUI_PASSWORD
# =========================================================================

# Simple in-memory session store (sessions expire after 24 hours)
_sessions: dict = {}
_SESSION_DURATION = 86400  # 24 hours in seconds

# Resolve static directory relative to this file (app/routes/tristar_gui.py -> app/static)
static_dir = Path(__file__).parent.parent / "static"

def create_session(username: str) -> str:
    """Create a new session token"""
    token = secrets.token_urlsafe(32)
    _sessions[token] = {
        "username": username,
        "created": time.time(),
        "expires": time.time() + _SESSION_DURATION
    }
    # Clean up expired sessions
    now = time.time()
    expired = [k for k, v in _sessions.items() if v["expires"] < now]
    for k in expired:
        del _sessions[k]
    return token

def verify_session(token: Optional[str]) -> Optional[str]:
    """Verify session token and return username if valid"""
    if not token or token not in _sessions:
        return None
    session = _sessions[token]
    if session["expires"] < time.time():
        del _sessions[token]
        return None
    return session["username"]

def verify_credentials(username: str, password: str) -> bool:
    """Verify login credentials against .env settings"""
    settings = get_settings()
    correct_user = secrets.compare_digest(
        username.encode("utf8"),
        settings.tristar_gui_user.encode("utf8")
    )
    correct_pass = secrets.compare_digest(
        password.encode("utf8"),
        settings.tristar_gui_password.encode("utf8")
    )
    return correct_user and correct_pass

# Login page HTML
LOGIN_PAGE_HTML = '''<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TriStar Login</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .login-container {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 25px 50px rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.1);
        }
        .logo {
            text-align: center;
            margin-bottom: 30px;
        }
        .logo h1 {
            color: #00d4ff;
            font-size: 2.5rem;
            font-weight: 700;
            text-shadow: 0 0 20px rgba(0,212,255,0.5);
        }
        .logo p {
            color: rgba(255,255,255,0.6);
            margin-top: 5px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            color: rgba(255,255,255,0.8);
            margin-bottom: 8px;
            font-weight: 500;
        }
        .form-group input {
            width: 100%;
            padding: 15px;
            border: 2px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            background: rgba(0,0,0,0.3);
            color: #fff;
            font-size: 16px;
            transition: all 0.3s;
        }
        .form-group input:focus {
            outline: none;
            border-color: #00d4ff;
            box-shadow: 0 0 15px rgba(0,212,255,0.3);
        }
        .form-group input::placeholder {
            color: rgba(255,255,255,0.3);
        }
        .btn-login {
            width: 100%;
            padding: 15px;
            border: none;
            border-radius: 10px;
            background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);
            color: #fff;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            margin-top: 10px;
        }
        .btn-login:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0,212,255,0.4);
        }
        .btn-login:active {
            transform: translateY(0);
        }
        .error-msg {
            background: rgba(255,50,50,0.2);
            border: 1px solid rgba(255,50,50,0.5);
            color: #ff6b6b;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            color: rgba(255,255,255,0.4);
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">
            <h1>⚡ TriStar</h1>
            <p>Kontrollzentrum</p>
        </div>
        {error}
        <form method="POST" action="/tristar/login">
            <div class="form-group">
                <label for="username">Benutzer</label>
                <input type="text" id="username" name="username" placeholder="Benutzername" required autofocus>
            </div>
            <div class="form-group">
                <label for="password">Passwort</label>
                <input type="password" id="password" name="password" placeholder="Passwort" required>
            </div>
            <button type="submit" class="btn-login">Anmelden</button>
        </form>
        <div class="footer">
            AILinux TriForce Backend v2.80
        </div>
    </div>
</body>
</html>'''

# Login page route
@router.get("/tristar/login", response_class=HTMLResponse, include_in_schema=False)
async def tristar_login_page(error: Optional[str] = None):
    """Show login page"""
    error_html = ""
    if error:
        error_html = '<div class="error-msg">Ungültige Anmeldedaten</div>'
    return HTMLResponse(LOGIN_PAGE_HTML.replace("{error}", error_html))

# Login POST handler
@router.post("/tristar/login", response_class=HTMLResponse, include_in_schema=False)
async def tristar_login_submit(
    response: Response,
    username: str = Form(...),
    password: str = Form(...)
):
    """Process login form"""
    if verify_credentials(username, password):
        token = create_session(username)
        redirect = RedirectResponse(url="/tristar", status_code=303)
        redirect.set_cookie(
            key="tristar_session",
            value=token,
            max_age=_SESSION_DURATION,
            httponly=True,
            samesite="lax"
        )
        return redirect
    else:
        return RedirectResponse(url="/tristar/login?error=1", status_code=303)

# Logout route
@router.get("/tristar/logout", include_in_schema=False)
async def tristar_logout(tristar_session: Optional[str] = Cookie(None)):
    """Logout and clear session"""
    if tristar_session and tristar_session in _sessions:
        del _sessions[tristar_session]
    redirect = RedirectResponse(url="/tristar/login", status_code=303)
    redirect.delete_cookie("tristar_session")
    return redirect

# TriStar Control Center GUI endpoint (Protected with Session)
@router.get("/tristar", response_class=HTMLResponse, include_in_schema=False)
@router.get("/tristar/", response_class=HTMLResponse, include_in_schema=False)
async def tristar_gui(tristar_session: Optional[str] = Cookie(None)):
    """TriStar Kontrollzentrum GUI (geschützt)"""
    username = verify_session(tristar_session)
    if not username:
        return RedirectResponse(url="/tristar/login", status_code=303)
    gui_file = static_dir / "tristar-control.html"
    if gui_file.exists():
        return FileResponse(gui_file, media_type="text/html")
    return HTMLResponse("<h1>TriStar GUI not found</h1>", status_code=404)

# Alias routes for convenience (also protected)
@router.get("/control", response_class=HTMLResponse, include_in_schema=False)
@router.get("/gui", response_class=HTMLResponse, include_in_schema=False)
async def gui_redirect(tristar_session: Optional[str] = Cookie(None)):
    """Redirect to TriStar GUI (geschützt)"""
    username = verify_session(tristar_session)
    if not username:
        return RedirectResponse(url="/tristar/login", status_code=303)
    gui_file = static_dir / "tristar-control.html"
    if gui_file.exists():
        return FileResponse(gui_file, media_type="text/html")
    return HTMLResponse("<h1>TriStar GUI not found</h1>", status_code=404)
