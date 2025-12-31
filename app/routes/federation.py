"""
AILinux Federation API Routes
=============================

Sichere Server-zu-Server Endpoints (nur über VPN erreichbar).
"""

from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

from ..services.server_federation import (
    federation_manager,
    verify_signed_request,
    create_signed_request,
    get_health_response,
    FEDERATION_NODES
)

logger = logging.getLogger("ailinux.federation.api")

router = APIRouter(prefix="/federation", tags=["Federation"])


# =============================================================================
# Models
# =============================================================================

class FederationRequest(BaseModel):
    timestamp: int
    signature: str
    payload: Dict[str, Any]


class NodeInfo(BaseModel):
    id: str
    name: str
    role: str
    status: str
    capabilities: List[str]
    latency_ms: float
    load: float


# =============================================================================
# Security Middleware
# =============================================================================

def verify_federation_request(request_data: dict, source_ip: str) -> Dict[str, Any]:
    """
    Verifiziert Federation Request.
    - Prüft ob Source IP im VPN-Bereich
    - Verifiziert HMAC Signatur
    """
    # VPN IP Check (10.10.0.0/24)
    if not source_ip.startswith("10.10.0."):
        logger.warning(f"Federation request from non-VPN IP: {source_ip}")
        raise HTTPException(403, "Federation only available via VPN")
    
    # Signatur Check
    payload = verify_signed_request(request_data)
    if payload is None:
        logger.warning(f"Invalid federation signature from {source_ip}")
        raise HTTPException(401, "Invalid signature")
    
    return payload


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/health")
async def federation_health(
    request: Request,
    body: FederationRequest,
    x_federation_node: str = Header(None)
):
    """
    Health Check Endpoint für Federation.
    
    Wird von anderen Nodes aufgerufen um Status zu prüfen.
    Nur über VPN (10.10.0.x) erreichbar.
    """
    # Get source IP
    source_ip = request.client.host if request.client else "unknown"
    
    # Verify request
    payload = verify_federation_request(body.dict(), source_ip)
    
    logger.debug(f"Health check from {x_federation_node} ({source_ip})")
    
    # Return signed health response
    return get_health_response()


@router.get("/nodes")
async def list_federation_nodes(request: Request):
    """
    Liste aller bekannten Federation Nodes.
    
    Nur über VPN erreichbar.
    """
    source_ip = request.client.host if request.client else "unknown"
    
    if not source_ip.startswith("10.10.0.") and source_ip not in ("127.0.0.1", "localhost"):
        raise HTTPException(403, "Federation only available via VPN")
    
    nodes = []
    
    # Eigener Node
    own_config = FEDERATION_NODES.get(federation_manager.node_id, {})
    nodes.append({
        "id": federation_manager.node_id,
        "name": own_config.get("name", "Unknown"),
        "role": own_config.get("role", "node"),
        "status": "online",  # Wir selbst sind immer online
        "capabilities": own_config.get("capabilities", []),
        "latency_ms": 0,
        "load": 0,
        "is_self": True
    })
    
    # Peer Nodes
    for node in federation_manager.nodes.values():
        nodes.append({
            **node.to_dict(),
            "is_self": False
        })
    
    return {
        "node_id": federation_manager.node_id,
        "nodes": nodes,
        "total": len(nodes)
    }


@router.post("/task/route")
async def route_task_to_node(
    request: Request,
    body: FederationRequest,
    x_federation_node: str = Header(None)
):
    """
    Route einen Task an den besten verfügbaren Node.
    
    Payload:
    - task_type: str (ollama, mcp, storage, etc.)
    - task_data: dict (Task-spezifische Daten)
    """
    source_ip = request.client.host if request.client else "unknown"
    payload = verify_federation_request(body.dict(), source_ip)
    
    task_type = payload.get("task_type", "")
    task_data = payload.get("task_data", {})
    
    if not task_type:
        raise HTTPException(400, "task_type required")
    
    # Finde besten Node
    best_node = federation_manager.get_best_node_for_task(task_type)
    
    if not best_node:
        # Kein externer Node, führe lokal aus
        return create_signed_request({
            "routed_to": "local",
            "message": f"No external node available for {task_type}, executing locally"
        })
    
    # Route zu externem Node
    result = await federation_manager.call_node(
        best_node.id,
        f"/v1/federation/task/execute",
        {"task_type": task_type, "task_data": task_data}
    )
    
    return create_signed_request({
        "routed_to": best_node.id,
        "result": result
    })


@router.post("/task/execute")
async def execute_routed_task(
    request: Request,
    body: FederationRequest,
    x_federation_node: str = Header(None)
):
    """
    Führt einen gerouteten Task lokal aus.
    """
    source_ip = request.client.host if request.client else "unknown"
    payload = verify_federation_request(body.dict(), source_ip)
    
    task_type = payload.get("task_type", "")
    task_data = payload.get("task_data", {})
    
    logger.info(f"Executing routed task: {task_type} from {x_federation_node}")
    
    result = {"status": "not_implemented", "task_type": task_type}
    
    # Task Execution basierend auf Typ
    if task_type == "ollama":
        # Ollama Inference
        model = task_data.get("model", "llama3.2:3b")
        prompt = task_data.get("prompt", "")
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "http://127.0.0.1:11434/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False}
                )
                if response.status_code == 200:
                    result = {"status": "success", "response": response.json()}
                else:
                    result = {"status": "error", "message": response.text}
        except Exception as e:
            result = {"status": "error", "message": str(e)}
    
    elif task_type == "storage":
        # Storage Operations
        result = {"status": "success", "message": "Storage task placeholder"}
    
    return create_signed_request(result)


@router.post("/ollama/models")
async def get_ollama_models_from_node(
    request: Request,
    body: FederationRequest,
    x_federation_node: str = Header(None)
):
    """
    Holt Ollama Modelle von einem spezifischen Node.
    """
    source_ip = request.client.host if request.client else "unknown"
    payload = verify_federation_request(body.dict(), source_ip)
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://127.0.0.1:11434/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                return create_signed_request({
                    "status": "success",
                    "models": [m["name"] for m in models]
                })
    except Exception as e:
        pass
    
    return create_signed_request({
        "status": "error",
        "models": []
    })


@router.get("/status")
async def federation_status(request: Request):
    """
    Öffentlicher Federation Status (ohne Signatur).
    """
    online_nodes = sum(1 for n in federation_manager.nodes.values() if n.status.value == "online")
    total_nodes = len(federation_manager.nodes) + 1  # +1 für sich selbst
    
    return {
        "federation_enabled": True,
        "node_id": federation_manager.node_id,
        "online_nodes": online_nodes + 1,  # +1 für sich selbst
        "total_nodes": total_nodes,
        "vpn_network": "10.10.0.0/24"
    }


# =============================================================================
# WebSocket Load Balancer Routes
# =============================================================================

from fastapi import WebSocket, WebSocketDisconnect
from ..services.federation_websocket import federation_lb

@router.get("/lb/status")
async def lb_status():
    """Load Balancer Cluster Status"""
    return federation_lb.get_cluster_status()

@router.get("/lb/best-node")
async def lb_best_node(task_type: str = None):
    """Gibt besten Node für Task zurück"""
    return {"best_node": federation_lb.get_best_node(task_type)}

@router.post("/lb/route-task")
async def lb_route_task(request: Request):
    """Routet Task zum besten Node"""
    body = await request.json()
    task_type = body.get("task_type", "default")
    task_data = body.get("task_data", {})
    timeout = body.get("timeout", 60.0)
    
    result = await federation_lb.route_task(task_type, task_data, timeout)
    return result
