#!/usr/bin/env python3
"""
AILinux Federation Node Agent v1.0
===================================

Minimaler Agent für Secondary Nodes (Backup-Server).
Beantwortet Federation Health Checks und proxyt Ollama.

Usage: python3 federation_node.py
Port: 9000
"""

import asyncio
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
import psutil
from fastapi import FastAPI, HTTPException, Header, Request
from pydantic import BaseModel
import uvicorn

# =============================================================================
# Configuration
# =============================================================================

# Load from env or file
def load_psk() -> str:
    psk = os.getenv("FEDERATION_PSK", "")
    if not psk:
        psk_file = "/home/zombie/triforce/config/federation_psk.key"
        if os.path.exists(psk_file):
            with open(psk_file) as f:
                psk = f.read().strip()
    return psk

FEDERATION_PSK = load_psk()
NODE_ID = os.getenv("FEDERATION_NODE_ID", "backup")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
TIMESTAMP_TOLERANCE = 30

# =============================================================================
# Security
# =============================================================================

def generate_signature(payload: str, timestamp: int) -> str:
    message = f"{timestamp}{payload}".encode()
    return hmac.new(FEDERATION_PSK.encode(), message, hashlib.sha256).hexdigest()

def verify_signature(payload: str, timestamp: int, signature: str) -> bool:
    now = int(time.time())
    if abs(now - timestamp) > TIMESTAMP_TOLERANCE:
        return False
    expected = generate_signature(payload, timestamp)
    return hmac.compare_digest(signature, expected)

def create_signed_response(data: Dict[str, Any]) -> Dict[str, Any]:
    timestamp = int(time.time())
    payload = json.dumps(data, sort_keys=True)
    signature = generate_signature(payload, timestamp)
    return {"timestamp": timestamp, "signature": signature, "payload": data}

def verify_request(data: dict) -> Optional[Dict[str, Any]]:
    try:
        timestamp = data.get("timestamp", 0)
        signature = data.get("signature", "")
        payload = data.get("payload", {})
        payload_str = json.dumps(payload, sort_keys=True)
        if verify_signature(payload_str, timestamp, signature):
            return payload
        return None
    except:
        return None

# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(title=f"AILinux Federation Node ({NODE_ID})")

class FederationRequest(BaseModel):
    timestamp: int
    signature: str
    payload: Dict[str, Any]

@app.get("/")
async def root():
    return {"node": NODE_ID, "type": "federation_node", "status": "online"}

@app.get("/v1/federation/status")
async def federation_status():
    return {
        "federation_enabled": True,
        "node_id": NODE_ID,
        "online_nodes": 1,
        "total_nodes": 2,
        "vpn_network": "10.10.0.0/24"
    }

@app.post("/v1/federation/health")
async def federation_health(request: Request, body: FederationRequest, x_federation_node: str = Header(None)):
    source_ip = request.client.host if request.client else "unknown"
    
    # VPN Check
    if not source_ip.startswith("10.10.0."):
        raise HTTPException(403, "VPN only")
    
    # Verify signature
    payload = verify_request(body.dict())
    if not payload:
        raise HTTPException(401, "Invalid signature")
    
    # Get Ollama models
    ollama_models = []
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            if resp.status_code == 200:
                ollama_models = [m["name"] for m in resp.json().get("models", [])]
    except:
        pass
    
    return create_signed_response({
        "status": "online",
        "load": psutil.cpu_percent() / 100.0,
        "ollama_models": ollama_models,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

@app.post("/v1/federation/task/execute")
async def execute_task(request: Request, body: FederationRequest, x_federation_node: str = Header(None)):
    source_ip = request.client.host if request.client else "unknown"
    
    if not source_ip.startswith("10.10.0."):
        raise HTTPException(403, "VPN only")
    
    payload = verify_request(body.dict())
    if not payload:
        raise HTTPException(401, "Invalid signature")
    
    task_type = payload.get("task_type", "")
    task_data = payload.get("task_data", {})
    
    result = {"status": "not_implemented", "task_type": task_type}
    
    if task_type == "ollama":
        model = task_data.get("model", "llama3.2:3b")
        prompt = task_data.get("prompt", "")
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False}
                )
                if resp.status_code == 200:
                    result = {"status": "success", "response": resp.json()}
                else:
                    result = {"status": "error", "message": resp.text}
        except Exception as e:
            result = {"status": "error", "message": str(e)}
    
    return create_signed_response(result)

@app.post("/v1/federation/ollama/models")
async def ollama_models(request: Request, body: FederationRequest):
    source_ip = request.client.host if request.client else "unknown"
    
    if not source_ip.startswith("10.10.0."):
        raise HTTPException(403, "VPN only")
    
    payload = verify_request(body.dict())
    if not payload:
        raise HTTPException(401, "Invalid signature")
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                return create_signed_response({"status": "success", "models": models})
    except:
        pass
    
    return create_signed_response({"status": "error", "models": []})

# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print(f"Starting Federation Node: {NODE_ID}")
    print(f"PSK loaded: {'Yes' if FEDERATION_PSK else 'NO - CHECK CONFIG!'}")
    print(f"Ollama: {OLLAMA_URL}")
    uvicorn.run(app, host="0.0.0.0", port=9000)
