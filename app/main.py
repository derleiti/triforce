from contextlib import asynccontextmanager
import secrets
import hashlib
import time
import redis.asyncio as redis
from fastapi import FastAPI, Request, status, HTTPException, Depends, Form, Cookie, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pathlib import Path
from fastapi_limiter import FastAPILimiter
from typing import Optional

# Prometheus metrics integration
try:
    from prometheus_fastapi_instrumentator import Instrumentator  # optional
    _HAS_INSTRUMENTATOR = True
except Exception:
    _HAS_INSTRUMENTATOR = False

try:
    from .utils.metrics import MetricsMiddleware, get_metrics_response
    _HAS_CUSTOM_METRICS = True
except Exception:
    _HAS_CUSTOM_METRICS = False

# TriForce Central Logging
try:
    from .utils.triforce_logging import (
        central_logger,
        TriForceLoggingMiddleware,
        setup_triforce_logging,
    )
    _HAS_TRIFORCE_LOGGING = True
except Exception:
    _HAS_TRIFORCE_LOGGING = False

# Central Logging (all logs to ./triforce/logs/)
try:
    from .utils.central_logging import setup_central_logging, LOG_DIR
    setup_central_logging()
    _HAS_CENTRAL_LOGGING = True
except Exception:
    _HAS_CENTRAL_LOGGING = False

from .config import get_settings

# Import the router object from each route module
from .routes.admin import router as admin_router
from .routes.admin_crawler import router as admin_crawler_router
from .routes.agents import router as agents_router
from .routes.chat import router as chat_router
from .routes.crawler import router as crawler_router
from .routes.health import router as health_router
from .routes.mcp import router as mcp_router
from .routes.mcp_remote import router as mcp_remote_router
from .routes.models import router as models_router
from .routes.openai_compat import router as openai_compat_router
from .routes.orchestration import router as orchestration_router
from .routes.posts import router as posts_router
from .routes.settings import router as settings_router
from .routes.vision import router as vision_router_v1
from .routes.text_analysis import router as text_router
from .routes.triforce import router as triforce_router
from .routes.tristar import router as tristar_router
from .routes.tristar_settings import router as tristar_settings_router
from .routes.mesh import router as mesh_router
from .routes.oauth_service import router as oauth_router

# Import routers from the top-level app directory
from .routes_sd3 import router as sd3_router
from .routes_vision import router as vision_router


async def _delayed_bootstrap():
    """Verzögerter Bootstrap der CLI Agents nach Server-Start"""
    import asyncio
    import logging
    # Warte bis Server vollständig gestartet ist
    await asyncio.sleep(5)
    try:
        from .services.agent_bootstrap import bootstrap_service
        result = await bootstrap_service.bootstrap_all(sequential_lead=True)
        logging.info(f"Agent Bootstrap complete: {result.get('success_count', 0)} agents started")
    except Exception as e:
        logging.error(f"Agent Bootstrap failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Connect to Redis and initialize the rate limiter
    redis_connection = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis_connection)

    # Start periodic model registry refresh (every hour)
    from .services.model_registry import registry
    registry.start_periodic_refresh(interval_seconds=3600.0)

    # Initialize TriStar services
    try:
        from .services.tristar.memory_controller import memory_controller
        from .services.tristar.model_init import model_init_service
        from .services.tristar.agent_controller import agent_controller
        from .services.tristar.settings_controller import settings_controller
        await memory_controller.initialize()
        await model_init_service.initialize()
        await agent_controller.initialize()
        await settings_controller.initialize()
    except Exception as e:
        import logging
        logging.warning(f"Failed to initialize TriStar services: {e}")

    # Start TriForce Central Logger
    if _HAS_TRIFORCE_LOGGING:
        try:
            await central_logger.start()
            setup_triforce_logging()
            import logging
            logging.info("TriForce Central Logging initialized")
        except Exception as e:
            import logging
            logging.warning(f"Failed to initialize TriForce logging: {e}")

    # Start Mesh Coordinator
    try:
        from .services.mesh_coordinator import mesh_coordinator
        await mesh_coordinator.start()
        import logging
        logging.info("Mesh Coordinator started")
    except Exception as e:
        import logging
        logging.warning(f"Failed to start Mesh Coordinator: {e}")

    # Start MCP Server Brain (Mitdenk-Funktion)
    try:
        from .services.init_service import mcp_brain
        await mcp_brain.start()
        import logging
        logging.info("MCP Server Brain started")
    except Exception as e:
        import logging
        logging.warning(f"Failed to start MCP Brain: {e}")

    # Auto-Bootstrap CLI Agents (wenn konfiguriert)
    try:
        from .services.agent_bootstrap import bootstrap_service
        import os
        auto_bootstrap = os.environ.get("AUTO_BOOTSTRAP_AGENTS", "false").lower() == "true"
        if auto_bootstrap:
            import logging
            logging.info("Auto-bootstrapping CLI Agents...")
            import asyncio
            # Verzögert starten um Server hochfahren zu lassen
            asyncio.create_task(_delayed_bootstrap())
        else:
            import logging
            logging.info("Agent Bootstrap available (AUTO_BOOTSTRAP_AGENTS=true to enable)")
    except Exception as e:
        import logging
        logging.warning(f"Failed to setup Agent Bootstrap: {e}")

    yield

    # Clean up resources on shutdown
    await registry.stop_periodic_refresh()

    # Stop TriForce Central Logger
    if _HAS_TRIFORCE_LOGGING:
        try:
            await central_logger.stop()
        except Exception:
            pass

    try:
        from .services.tristar.agent_controller import agent_controller
        await agent_controller.shutdown()
    except Exception:
        pass

    # Stop Mesh Coordinator
    try:
        from .services.mesh_coordinator import mesh_coordinator
        await mesh_coordinator.stop()
    except Exception:
        pass

    # Stop MCP Server Brain
    try:
        from .services.init_service import mcp_brain
        await mcp_brain.stop()
    except Exception:
        pass

    await FastAPILimiter.close()

def create_app() -> FastAPI:
    import logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    app = FastAPI(title="AILinux AI Server", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        import json
        logging.error("Request validation error: %s", json.dumps(exc.errors()))
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors(), "body": exc.body},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.detail,
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        import traceback
        logging.error(f"Global Unhandled Exception on {request.url.path}: {exc}")
        logging.error(traceback.format_exc())
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal Server Error",
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred."
                }
            }
        )

    settings = get_settings()
    allowed_origins = [origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()]

    # Only add CORS middleware if origins are configured
    # If empty, assume nginx/reverse proxy handles CORS
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # =========================================================================
    # Primary Routes (/v1 prefix)
    # Note: MCP health check is now handled by mcp_router with transport detection
    # =========================================================================
    app.include_router(admin_router, prefix="/v1", tags=["Admin"])
    app.include_router(admin_crawler_router, prefix="/v1", tags=["Admin Crawler"])
    app.include_router(agents_router, prefix="/v1", tags=["Agents"])
    app.include_router(chat_router, prefix="/v1", tags=["Chat"])
    app.include_router(crawler_router, prefix="/v1", tags=["Crawler"])
    app.include_router(health_router, tags=["Monitoring"])
    app.include_router(mcp_router, prefix="/v1", tags=["MCP"])
    app.include_router(mcp_remote_router, tags=["MCP Remote Server"])
    app.include_router(oauth_router, tags=["OAuth 2.0"])
    app.include_router(models_router, prefix="/v1", tags=["Models"])
    app.include_router(openai_compat_router, prefix="/v1/openai", tags=["OpenAI Compatibility"])
    app.include_router(orchestration_router, prefix="/v1", tags=["Orchestration"])
    app.include_router(posts_router, prefix="/v1", tags=["Posts"])
    app.include_router(settings_router, prefix="/v1", tags=["Settings"])
    app.include_router(vision_router_v1, prefix="/v1", tags=["Vision V1"])
    app.include_router(text_router, prefix="/v1", tags=["Text Analysis"])
    app.include_router(triforce_router, prefix="/v1", tags=["TriForce"])
    app.include_router(tristar_router, prefix="/v1", tags=["TriStar"])
    app.include_router(tristar_settings_router, prefix="/v1", tags=["TriStar Settings"])
    app.include_router(mesh_router, prefix="/v1", tags=["Mesh AI"])

    # =========================================================================
    # Translation Layer - Alternative Path Aliases
    # =========================================================================
    # Note: tristar_router and triforce_router have internal prefixes
    # (/tristar and /triforce), so we register them without additional prefix
    # for the root aliases, and with empty prefix for cross-links

    # Legacy /mcp aliases removed - use /v1/mcp instead
    # Standard MCP endpoint: /v1/mcp (registered above in line 256)

    # TriStar Aliases: Register at root (router has prefix="/tristar")
    # This gives us: /tristar/..., /v1/tristar/... (primary)
    app.include_router(tristar_router, prefix="", tags=["TriStar Root"])

    # TriForce Aliases: Register at root (router has prefix="/triforce")
    # This gives us: /triforce/..., /v1/triforce/... (primary)
    app.include_router(triforce_router, prefix="", tags=["TriForce Root"])

    # MCP under TriStar/TriForce namespaces
    app.include_router(mcp_router, prefix="/tristar/mcp", tags=["TriStar MCP"])
    app.include_router(mcp_router, prefix="/triforce/mcp", tags=["TriForce MCP"])

    # Mesh AI Routes (additional aliases)
    app.include_router(mesh_router, prefix="", tags=["Mesh Root"])  # /mesh/...
    app.include_router(mesh_router, prefix="/triforce", tags=["TriForce Mesh"])  # /triforce/mesh/...

    # Legacy /mcp namespace aliases removed - use /v1/tristar and /v1/triforce instead

    # Include routers from the top-level app directory (prefixes are in the files)
    app.include_router(sd3_router, prefix="/v1", tags=["Stable Diffusion 3"])
    app.include_router(vision_router, tags=["Vision"])

    # Import and include txt2img router
    try:
        from .routes.txt2img import router as txt2img_router
        app.include_router(txt2img_router, prefix="/v1", tags=["Text-to-Image"])
    except ImportError as e:
        import logging
        logging.warning(f"Could not import txt2img router: {e}")

    # Prometheus Metrics Setup
    if _HAS_INSTRUMENTATOR:
        Instrumentator().instrument(app).expose(app, include_in_schema=False)

    # Custom AILinux Metrics Middleware (LLM calls, circuit breaker, memory, etc.)
    if _HAS_CUSTOM_METRICS:
        @app.middleware("http")
        async def metrics_middleware(request: Request, call_next):
            middleware = MetricsMiddleware()
            return await middleware(request, call_next)

    # TriForce Central Logging Middleware - logs ALL API traffic
    if _HAS_TRIFORCE_LOGGING:
        app.add_middleware(TriForceLoggingMiddleware, central_logger=central_logger)

    # Mount static files for GUI
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # =========================================================================
    # Session-based Authentication for TriStar GUI
    # Credentials from .env: TRISTAR_GUI_USER, TRISTAR_GUI_PASSWORD
    # =========================================================================

    # Simple in-memory session store (sessions expire after 24 hours)
    _sessions: dict = {}
    _SESSION_DURATION = 86400  # 24 hours in seconds

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
    @app.get("/tristar/login", response_class=HTMLResponse, tags=["GUI"], include_in_schema=False)
    async def tristar_login_page(error: Optional[str] = None):
        """Show login page"""
        error_html = ""
        if error:
            error_html = '<div class="error-msg">Ungültige Anmeldedaten</div>'
        return HTMLResponse(LOGIN_PAGE_HTML.replace("{error}", error_html))

    # Login POST handler
    @app.post("/tristar/login", response_class=HTMLResponse, tags=["GUI"], include_in_schema=False)
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
    @app.get("/tristar/logout", tags=["GUI"], include_in_schema=False)
    async def tristar_logout(tristar_session: Optional[str] = Cookie(None)):
        """Logout and clear session"""
        if tristar_session and tristar_session in _sessions:
            del _sessions[tristar_session]
        redirect = RedirectResponse(url="/tristar/login", status_code=303)
        redirect.delete_cookie("tristar_session")
        return redirect

    # TriStar Control Center GUI endpoint (Protected with Session)
    @app.get("/tristar", response_class=HTMLResponse, tags=["GUI"], include_in_schema=False)
    @app.get("/tristar/", response_class=HTMLResponse, tags=["GUI"], include_in_schema=False)
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
    @app.get("/control", response_class=HTMLResponse, tags=["GUI"], include_in_schema=False)
    @app.get("/gui", response_class=HTMLResponse, tags=["GUI"], include_in_schema=False)
    async def gui_redirect(tristar_session: Optional[str] = Cookie(None)):
        """Redirect to TriStar GUI (geschützt)"""
        username = verify_session(tristar_session)
        if not username:
            return RedirectResponse(url="/tristar/login", status_code=303)
        gui_file = static_dir / "tristar-control.html"
        if gui_file.exists():
            return FileResponse(gui_file, media_type="text/html")
        return HTMLResponse("<h1>TriStar GUI not found</h1>", status_code=404)

    return app

# Uvicorn Entry
app = create_app()
