from contextlib import asynccontextmanager
import logging
# import logging (centralized)
import redis.asyncio as redis
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pathlib import Path
from .config import get_settings
from .utils.rate_limit_compat import FastAPILimiter
from .utils.mcp_auth import require_mcp_auth

# Import the router object from each route module
from .routes.admin import router as admin_router
from .routes.admin_crawler import router as admin_crawler_router
from .routes.agents import router as agents_router
from .routes.chat import router as chat_router
from .routes.crawler import router as crawler_router
from .routes.health import router as health_router
from .routes.mcp import public_router as mcp_public_router, router as mcp_router
from .routes.mcp_node import router as mcp_node_router
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
from .routes.perf_monitor import router as perf_monitor_router, perf_middleware
from .routes.distributed_compute import router as distributed_compute_router
from .routes.tristar_gui import router as tristar_gui_router
from .routes.client_chat import router as client_chat_router
from .routes.client_auth import router as client_auth_router
from .routes.client_update import router as client_update_router
from .routes.client_logs import router as client_logs_router
from .routes.client_ai_search import router as client_ai_search_router
from .routes.federation import router as federation_router
from .routes.nova_frontend import router as nova_frontend_router
from .routes.nova_chat_agent import router as nova_chat_agent_router
# BUG-006 FIX 2026-03-10: user_api war nie in main.py registriert
from .routes.user_api import router as user_api_router
# BUG-013 FIX 2026-03-10: support + tiers waren definiert aber nie registriert
from .routes.support import router as support_router
from .routes.tiers import router as tiers_router
from .routes.nova_wordpress import router as nova_wordpress_router

# Import routers from the top-level app directory
from .routes_sd3 import router as sd3_router
from .routes_vision import router as vision_router
logger = logging.getLogger("app.main")

# Unified logging für alle Komponenten
try:
    from .utils.unified_logger import setup_unified_logging
    setup_unified_logging()
except ImportError:
    pass

# Prometheus metrics integration
try:
    from prometheus_fastapi_instrumentator import Instrumentator  # optional
    _HAS_INSTRUMENTATOR = True
except Exception:
    _HAS_INSTRUMENTATOR = False

try:
    from .utils.metrics import MetricsMiddleware
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
    from .utils.central_logging import setup_central_logging
    setup_central_logging()
    _HAS_CENTRAL_LOGGING = True
except Exception:
    _HAS_CENTRAL_LOGGING = False

# System Log Collector (kernel, apps, journald -> /triforce/logs/)
try:
    from .utils.system_log_collector import init_system_logging, system_log_collector
    _HAS_SYSTEM_LOG_COLLECTOR = True
except Exception:
    _HAS_SYSTEM_LOG_COLLECTOR = False

async def _delayed_bootstrap():
    """Verzögerter Bootstrap der CLI Agents nach Server-Start"""
    import asyncio
    # import logging (centralized)
    # Warte bis Server vollständig gestartet ist
    await asyncio.sleep(5)
    try:
        from .services.agent_bootstrap import bootstrap_service
        result = await bootstrap_service.bootstrap_all(sequential_lead=True)
        logger.info(f"Agent Bootstrap complete: {result.get('success_count', 0)} agents started")
    except Exception as e:
        logger.error(f"Agent Bootstrap failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # import logging (centralized)

    # === Hardware Acceleration Auto-Detection ===
    try:
        from .services.hardware_accel import init_hardware_acceleration
        hw_config = init_hardware_acceleration()
        logger.info(f"Hardware Acceleration: {hw_config.get('primary_accelerator', 'CPU')}")
        logger.info(f"  GPUs: {len(hw_config.get('gpus', []))}, Threads: {hw_config.get('recommended_threads', 4)}")
    except Exception as e:
        logger.warning(f"Hardware detection failed (using defaults): {e}")

    settings = get_settings()
    # Connect to Redis and initialize the rate limiter (best effort)
    try:
        redis_connection = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        await FastAPILimiter.init(redis_connection)
    except Exception as e:
        logger.warning(f"FastAPILimiter init skipped (Redis unavailable): {e}")

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
        # import logging (centralized)
        logger.warning(f"Failed to initialize TriStar services: {e}")

    # Start TriForce Central Logger
    if _HAS_TRIFORCE_LOGGING:
        try:
            await central_logger.start()
            setup_triforce_logging()
            # import logging (centralized)
            logger.info("TriForce Central Logging initialized")
        except Exception as e:
            # import logging (centralized)
            logger.warning(f"Failed to initialize TriForce logging: {e}")

    # Start Mesh Coordinator
    try:
        from .services.mesh_coordinator import mesh_coordinator
        await mesh_coordinator.start()
        # import logging (centralized)
        logger.info("Mesh Coordinator started")
    except Exception as e:
        # import logging (centralized)
        logger.warning(f"Failed to start Mesh Coordinator: {e}")

    # Start Federation Manager (Server-to-Server)
    try:
        from .services.server_federation import federation_manager, NodeRole
        from .services.federation_websocket import federation_lb
        import socket
        import os
        _hostname = socket.gethostname().lower()
        node_id = (
            os.getenv("FEDERATION_NODE_ID")
            or ("backup" if "backup" in _hostname else "zombie-pc" if "zombie" in _hostname else "hetzner")
        )
        role_env = (os.getenv("FEDERATION_ROLE", "node") or "node").strip().lower()
        role = NodeRole.HUB if role_env == "hub" else NodeRole.NODE
        # Redis-Lock: nur ein Worker darf Federation starten
        import redis.asyncio as _redis
        _r = _redis.from_url("redis://localhost:6379/0")
        _lock = await _r.set("federation_lock", 1, nx=True, ex=60)
        await _r.aclose()
        if _lock:
            await federation_manager.initialize(node_id=node_id, role=role)
            await federation_lb.start()
            logger.info(f"Federation Manager started (lock acquired) as {node_id}/{role.value}")
        else:
            logger.info("Federation Manager skipped (another worker holds lock)")
    except Exception as e:
        logger.warning(f"Failed to start Federation Manager: {e}")

    # Start Distributed Compute Manager
    try:
        from .services.distributed_compute import get_distributed_compute
        distributed_compute = get_distributed_compute()
        await distributed_compute.start()
        # import logging (centralized)
        logger.info("Distributed Compute Manager started")
    except Exception as e:
        # import logging (centralized)
        logger.warning(f"Failed to start Distributed Compute Manager: {e}")

    # BUG-003 FIX 2026-03-11: init_v4_handlers wurde nie aufgerufen → alle v4 Handler tot nach Restart
    try:
        from .routes.mcp import init_v4_handlers
        init_v4_handlers()
        logger.info("MCP v4 Handler Registry initialized")
    except Exception as e:
        logger.warning(f"MCP v4 Handler init failed: {e}")

    # Start MCP Server Brain (Mitdenk-Funktion)
    try:
        from .services.init_service import mcp_brain
        await mcp_brain.start()
        # import logging (centralized)
        logger.info("MCP Server Brain started")
    except Exception as e:
        # import logging (centralized)
        logger.warning(f"Failed to start MCP Brain: {e}")

    # Start MCP WebSocket Server (Port 44433)
    # In multi-worker mode, only one worker can bind the port.
    # mcp_ws_server.start() handles the port-check internally.
    try:
        from .services.mcp_ws_server import mcp_ws_server
        await mcp_ws_server.start()
        if mcp_ws_server._running:
            logger.info(f"MCP WebSocket Server started on port {settings.mcp_ws_port}")
        else:
            # Expected in multi-worker mode: another worker owns the port
            logger.info("MCP WebSocket Server: port 44433 owned by another worker — skipping")
    except Exception as e:
        logger.warning(f"Failed to start MCP WebSocket Server: {e}")

    # Auto-Bootstrap CLI Agents (wenn konfiguriert)
    try:
        import os
        auto_bootstrap = os.environ.get("AUTO_BOOTSTRAP_AGENTS", "false").lower() == "true"
        if auto_bootstrap:
            # import logging (centralized)
            logger.info("Auto-bootstrapping CLI Agents...")
            import asyncio
            # Verzögert starten um Server hochfahren zu lassen
            asyncio.create_task(_delayed_bootstrap())
        else:
            # import logging (centralized)
            logger.info("Agent Bootstrap available (AUTO_BOOTSTRAP_AGENTS=true to enable)")
    except Exception as e:
        # import logging (centralized)
        logger.warning(f"Failed to setup Agent Bootstrap: {e}")

    # Initialize System Log Collector (collects kernel, apps, journald logs)
    if _HAS_SYSTEM_LOG_COLLECTOR:
        try:
            # import logging (centralized)
            logger.info("Initializing System Log Collector...")
            result = await init_system_logging()
            sources = result.get("sources_collected", [])
            logger.info(f"System Log Collector initialized: {len(sources)} sources collected")
        except Exception as e:
            # import logging (centralized)
            logger.warning(f"Failed to initialize System Log Collector: {e}")

    # === SWARM-IMPROVEMENT #2: Redis Auto-Cleanup (DeepSeek-Vorschlag) ===
    try:
        from .services.redis_optimizer import get_cleanup
        cleanup = get_cleanup()
        import asyncio as _aio
        _aio.get_event_loop().create_task(cleanup.start_periodic(interval=3600))
        logger.info("Redis Auto-Cleanup started (hourly)")
    except Exception as e:
        logger.warning(f"Redis Auto-Cleanup init failed: {e}")

    # Task Scheduler + Agent Spawner als Background-Tasks starten
    try:
        from .services.task_scheduler import get_task_scheduler
        from .services.agent_spawner import get_agent_spawner
        _scheduler = get_task_scheduler()
        _spawner = get_agent_spawner()
        _scheduler.start()
        _spawner.start()
        logger.info("Task Scheduler + Agent Spawner gestartet")

        # Kern-Agents initialisieren (nach Delay damit MCP_HANDLERS ready)
        async def _init_core_agents():
            import asyncio as _asyncio  # explizit um UnboundLocalError zu vermeiden
            await _asyncio.sleep(15)  # MCP_HANDLERS brauchen ~10s
            try:
                from .services.agent_spawner import SYSTEM_AGENT_PROMPTS
                from .services.tristar.agent_controller import agent_controller
                await agent_controller._ensure_initialized()

                for agent_id in ("claude-mcp", "gemini-mcp", "codex-mcp"):
                    prompt_tpl = SYSTEM_AGENT_PROMPTS.get(agent_id, "")
                    if not prompt_tpl:
                        continue
                    prompt = prompt_tpl.format(
                        session_id=f"sys-{agent_id}",
                        context="System-Start — bereit für Aufgaben.",
                        custom_prompt="", topic="system_agent",
                    )
                    try:
                        await agent_controller.update_system_prompt(agent_id, prompt)
                        result = await agent_controller.start_agent(agent_id)
                        logger.info(
                            f"Kern-Agent {agent_id}: {result.get('status','?')}"
                        )
                    except Exception as _ae:
                        logger.debug(f"Kern-Agent {agent_id} init skip: {_ae}")

            except Exception as _e:
                logger.warning(f"Core-Agent-Init fehlgeschlagen (nicht kritisch): {_e}")

        import asyncio as _asyncio2
        _asyncio2.create_task(_init_core_agents())

    except Exception as e:
        logger.warning(f"Task Scheduler/Spawner init failed: {e}")

    # Group Chat Recovery: re-trigger auto-response for sessions waiting before restart
    try:
        from .services.group_chat import group_chat
        group_chat._schedule_recovery()
        logger.info("Group Chat recovery scheduled")
    except Exception as e:
        logger.warning(f"Group Chat recovery init failed: {e}")

    # ── Nova Engines ──────────────────────────────────────────────────────────
    # Content-Engine (WP alle 1h, Flarum alle 2h), Research-Loop (täglich)
    try:
        import asyncio as _asyncio_nova
        from .services.nova_content_engine import start_content_engine
        from .services.nova_research_loop import research_loop_tick
        start_content_engine()

        async def _research_loop():
            await _asyncio_nova.sleep(120)  # 2min Startup-Delay
            while True:
                try:
                    await research_loop_tick()
                except Exception as _re:
                    logger.error(f"research_loop_tick error: {_re}")
                await _asyncio_nova.sleep(300)

        _asyncio_nova.create_task(_research_loop())
        logger.info("Nova Engines gestartet: Content-Engine + Research-Loop")
    except Exception as _ne:
        logger.warning(f"Nova Engines init failed (nicht kritisch): {_ne}")
    except Exception as e:
        logger.warning(f"Group Chat recovery init failed: {e}")

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

    # Stop MCP WebSocket Server
    try:
        from .services.mcp_ws_server import mcp_ws_server
        await mcp_ws_server.stop()
    except Exception:
        pass
    try:
        from .services.init_service import mcp_brain
        await mcp_brain.stop()
    except Exception:
        pass

    # Stop Distributed Compute Manager
    try:
        from .services.distributed_compute import get_distributed_compute
        distributed_compute = get_distributed_compute()
        await distributed_compute.stop()
    except Exception:
        pass

    # Stop System Log Collector
    if _HAS_SYSTEM_LOG_COLLECTOR:
        try:
            await system_log_collector.stop()
        except Exception:
            pass

    await FastAPILimiter.close()

def create_app() -> FastAPI:
    # import logging (centralized)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # FIX: Externe HTTP-Bibliotheken auf WARNING setzen — verhindert hpack/httpcore DEBUG-Flut
    for _noisy_lib in ("hpack", "hpack.hpack", "httpcore", "httpcore.http2",
                        "httpcore.http11", "httpx", "h2", "h11", "urllib3"):
        logging.getLogger(_noisy_lib).setLevel(logging.WARNING)
    app = FastAPI(
        title="AILinux AI Server", 
        lifespan=lifespan,
        redirect_slashes=False  # Verhindert 307 Redirect bei trailing slash
    )


    public_auth_exempt_paths = {
        "/health",
        "/.well-known/mcp",
        "/.well-known/mcp/",
        "/.well-known/oauth-authorization-server",
        "/.well-known/oauth-authorization-server/",
        "/v1/.well-known/mcp",
        "/v1/.well-known/mcp/",
        "/v1/.well-known/oauth-authorization-server",
        "/v1/.well-known/oauth-authorization-server/",
        "/v1/mcp/.well-known/mcp.json",
    }

    @app.middleware("http")
    async def central_auth_middleware(request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path

        needs_auth = (
            (path.startswith("/v1") and path not in public_auth_exempt_paths)
            or path.startswith("/mcp")
        )

        if needs_auth:
            await require_mcp_auth(request)

        return await call_next(request)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        import json

        body_preview = exc.body
        try:
            if isinstance(body_preview, (dict, list)):
                body_preview = json.dumps(body_preview, ensure_ascii=False)
            else:
                body_preview = str(body_preview)
        except Exception:
            body_preview = "<unserializable>"

        logger.error(
            "Request validation error on %s %s | content-type=%s | user-agent=%s | errors=%s | body=%s",
            request.method,
            request.url.path,
            request.headers.get("content-type"),
            request.headers.get("user-agent"),
            json.dumps(exc.errors(), ensure_ascii=False),
            (body_preview[:1000] if body_preview else "<empty>"),
        )
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
        logger.error(f"Global Unhandled Exception on {request.url.path}: {exc}")
        logger.error(traceback.format_exc())
        
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
    app.include_router(mcp_public_router, prefix="/v1", tags=["MCP"])
    app.include_router(mcp_router, prefix="/v1", tags=["MCP"])
    app.include_router(mcp_node_router, prefix="/v1", tags=["MCP Node"])
    # BUG-004 CLARIFICATION 2026-03-10:
    # mcp_remote_router wird OHNE prefix registriert → Endpoint: /mcp (kein /v1)
    # Dies ist ABSICHT: /mcp  = Claude.ai Remote Connector (OAuth, SSE, extern erreichbar)
    #                  /v1/mcp = Interner/lokaler MCP Endpoint (für Clients, API-Zugriff)
    # NICHT konsolidieren — beide haben unterschiedliche Auth-Stacks und Tool-Sets.
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
    app.include_router(distributed_compute_router, tags=["Distributed Compute"])
    app.include_router(tristar_gui_router)

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
    # REDUNDANT: app.include_router(tristar_router, prefix="", tags=["TriStar Root"])  # Disabled 2025-12-26

    # TriForce Aliases: Register at root (router has prefix="/triforce")
    # This gives us: /triforce/..., /v1/triforce/... (primary)
    # REDUNDANT: app.include_router(triforce_router, prefix="", tags=["TriForce Root"])  # Disabled 2025-12-26

    # MCP under TriStar/TriForce namespaces
    # REDUNDANT: app.include_router(mcp_router, prefix="/tristar/mcp", tags=["TriStar MCP"])  # Disabled 2025-12-26
    # REDUNDANT: app.include_router(mcp_router, prefix="/triforce/mcp", tags=["TriForce MCP"])  # Disabled 2025-12-26

    # Mesh AI Routes (additional aliases)
    # REDUNDANT: app.include_router(mesh_router, prefix="", tags=["Mesh Root"])  # Disabled 2025-12-26  # /mesh/...
    # REDUNDANT: app.include_router(mesh_router, prefix="/triforce", tags=["TriForce Mesh"])  # Disabled 2025-12-26  # /triforce/mesh/...
    app.include_router(perf_monitor_router, tags=["Performance Monitor"])

    # Legacy /mcp namespace aliases removed - use /v1/tristar and /v1/triforce instead

    # Include routers from the top-level app directory (prefixes are in the files)
    app.include_router(sd3_router, prefix="/v1", tags=["Stable Diffusion 3"])
    app.include_router(vision_router, tags=["Vision"])
    app.include_router(nova_frontend_router, prefix="/v1", tags=["Nova Frontend"])
    app.include_router(nova_chat_agent_router, prefix="/v1", tags=["Nova Chat Agent"])
    # BUG-006 FIX 2026-03-10: User API Router registrieren
    app.include_router(user_api_router, prefix="/v1", tags=["User API"])
    app.include_router(client_chat_router, prefix="/v1", tags=["Client Chat"])
    app.include_router(client_auth_router, prefix="/v1", tags=["Client Auth"])
    app.include_router(client_update_router, prefix="/v1", tags=["Client Update"])
    app.include_router(client_logs_router, tags=["Client Logs"])
    app.include_router(client_ai_search_router, prefix="/v1", tags=["Client AI Search"])
    app.include_router(federation_router, prefix="/v1", tags=["Federation"])
    # BUG-013 FIX 2026-03-10: support + tiers Routen registriert
    app.include_router(support_router, prefix="/v1", tags=["Support"])
    app.include_router(tiers_router, prefix="/v1", tags=["Tiers"])
    app.include_router(nova_wordpress_router, tags=["Nova WordPress"])

    # Import and include txt2img router
    try:
        from .routes.txt2img import router as txt2img_router
        app.include_router(txt2img_router, prefix="/v1", tags=["Text-to-Image"])
    except ImportError as e:
        # import logging (centralized)
        logger.warning(f"Could not import txt2img router: {e}")

    # Prometheus Metrics Setup
    if _HAS_INSTRUMENTATOR:
        Instrumentator().instrument(app).expose(app, include_in_schema=False)

    # Custom AILinux Metrics Middleware (LLM calls, circuit breaker, memory, etc.)
    if _HAS_CUSTOM_METRICS:
        @app.middleware("http")
        async def metrics_middleware(request: Request, call_next):
            middleware = MetricsMiddleware()
            return await middleware(request, call_next)

    # Performance Monitor Middleware (Endpoint-Latenz-Tracking)
    @app.middleware("http")
    async def perf_middleware_handler(request: Request, call_next):
        return await perf_middleware(request, call_next)

    # TriForce Central Logging Middleware - logs ALL API traffic
    if _HAS_TRIFORCE_LOGGING:
        app.add_middleware(TriForceLoggingMiddleware, central_logger=central_logger)

    # Mount static files for GUI
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # =========================================================================
    # Session-based Authentication for TriStar GUI
    # Moved to app/routes/tristar_gui.py
    # =========================================================================

    return app

# Uvicorn Entry
app = create_app()


### MCP_HOST_POLICY_IMPORT ###
try:
    from app.policy.mcp_host_policy import should_convert_to_proposal, build_proposal_response
except Exception:
    should_convert_to_proposal = None
    build_proposal_response = None

