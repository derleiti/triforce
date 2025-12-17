"""
Distributed Compute Routes
==========================

WebSocket und REST-Endpoints für verteiltes Computing.
Ermöglicht Clients, ihre Rechenleistung dem Netzwerk zur Verfügung zu stellen.
"""

import logging
from typing import Any, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..services.distributed_compute import (
    get_distributed_compute,
    TaskPriority,
)

router = APIRouter(prefix="/v1/distributed", tags=["Distributed Compute"])
logger = logging.getLogger("ailinux.distributed_compute")


# === Pydantic Models ===

class WorkerRegistration(BaseModel):
    """Worker-Registrierung"""
    capability: str = "WEBGPU"
    gpu_vendor: str = ""
    gpu_name: str = ""
    estimated_tflops: float = 0.0
    supported_models: List[str] = []


class TaskSubmission(BaseModel):
    """Task-Einreichung"""
    task_type: str
    input_data: Any
    model_id: str
    priority: str = "normal"
    timeout_seconds: float = 60.0


class BatchTaskSubmission(BaseModel):
    """Batch-Task-Einreichung"""
    task_type: str
    input_items: List[Any]
    model_id: str
    batch_size: int = 10
    priority: str = "normal"


# === WebSocket Endpoint ===

@router.websocket("/worker")
async def worker_websocket(
    websocket: WebSocket,
    capability: str = Query("WEBGPU"),
    gpu_name: str = Query(""),
    tflops: float = Query(0.0),
):
    """
    WebSocket für Compute Workers.

    Clients verbinden sich hier, um Tasks zu empfangen und Ergebnisse zu melden.

    Query Parameters:
    - capability: WEBGPU, WEBGL2, WEBGL, WASM_SIMD, WASM, JS_ONLY
    - gpu_name: Name der GPU (z.B. "NVIDIA RTX 3080")
    - tflops: Geschätzte TFLOPS

    Protocol:
    1. Client verbindet sich mit GPU-Info
    2. Server sendet `worker_registered` mit Session-ID
    3. Server sendet `task_assignment` wenn Task verfügbar
    4. Client sendet `task_result` nach Bearbeitung
    5. Client sendet `heartbeat` alle 30 Sekunden
    """
    await websocket.accept()

    manager = get_distributed_compute()
    session_id = None

    try:
        # Auf Registrierungsnachricht warten
        init_msg = await websocket.receive_json()

        if init_msg.get("type") != "register":
            await websocket.close(code=4001, reason="Expected register message")
            return

        # Client registrieren
        supported_models = init_msg.get("supported_models", [
            "embedding_small",
            "sentiment",
            "clip_embed",
        ])

        # Validate and generate session_id if empty or duplicate
        requested_session_id = init_msg.get("session_id", "").strip()
        
        # Generate new unique session_id if empty or already exists (prevent overwriting)
        if not requested_session_id or requested_session_id in manager._clients:
            import secrets
            requested_session_id = secrets.token_urlsafe(16)
            logger.info(f"Generated new session_id: {requested_session_id}")

        client = await manager.register_client(
            websocket=websocket,
            session_id=requested_session_id,
            capability=capability,
            gpu_name=gpu_name,
            estimated_tflops=tflops,
            supported_models=supported_models,
        )
        session_id = client.session_id

        # Bestätigung senden
        await websocket.send_json({
            "type": "worker_registered",
            "session_id": session_id,
            "supported_models": supported_models,
            "message": "Successfully registered as compute worker",
        })

        logger.info(f"Worker connected: {session_id} ({capability})")

        # Message Loop
        while True:
            try:
                message = await websocket.receive_json()
                msg_type = message.get("type")

                if msg_type == "heartbeat":
                    await manager.client_heartbeat(session_id)
                    await websocket.send_json({"type": "heartbeat_ack"})

                elif msg_type == "task_result":
                    await manager.report_task_result(
                        session_id=session_id,
                        task_id=message.get("task_id"),
                        success=message.get("success", False),
                        result=message.get("result"),
                        error=message.get("error"),
                        compute_time=message.get("compute_time", 0.0),
                    )

                elif msg_type == "task_progress":
                    # Progress-Update vom Client - Task Status aktualisieren
                    task_id = message.get("task_id")
                    progress = message.get("progress", 0)  # 0-100
                    if task_id and session_id in manager._clients:
                        task = manager._task_queue.get(task_id)
                        if task and task.assigned_to == session_id:
                            # Update task status to PROCESSING when progress is received
                            from ..services.distributed_compute import TaskStatus
                            task.status = TaskStatus.PROCESSING
                            # Log progress for monitoring
                            logger.debug(f"Task {task_id} progress: {progress}%")

                elif msg_type == "capability_update":
                    # Client kann Models hinzufügen/entfernen
                    if session_id in manager._clients:
                        manager._clients[session_id].supported_models = message.get("supported_models", [])

                elif msg_type == "disconnect":
                    break

            except Exception as e:
                logger.error(f"Worker message error: {e}")

    except WebSocketDisconnect:
        logger.info(f"Worker disconnected: {session_id}")
    except Exception as e:
        logger.error(f"Worker error: {e}")
    finally:
        if session_id:
            await manager.unregister_client(session_id)


# === REST Endpoints ===

@router.post("/submit")
async def submit_task(task: TaskSubmission):
    """
    Reicht einen Task zur verteilten Berechnung ein.

    Der Task wird an einen verfügbaren Worker zugewiesen.
    """
    manager = get_distributed_compute()

    priority_map = {
        "low": TaskPriority.LOW,
        "normal": TaskPriority.NORMAL,
        "high": TaskPriority.HIGH,
        "urgent": TaskPriority.URGENT,
    }

    task_id = await manager.submit_task(
        task_type=task.task_type,
        input_data=task.input_data,
        model_id=task.model_id,
        priority=priority_map.get(task.priority.lower(), TaskPriority.NORMAL),
        timeout_seconds=task.timeout_seconds,
    )

    return JSONResponse(content={
        "task_id": task_id,
        "status": "pending",
        "message": "Task submitted for distributed processing",
    })


@router.post("/submit/batch")
async def submit_batch_task(batch: BatchTaskSubmission):
    """
    Reicht mehrere Items als Batch-Tasks ein.

    Die Items werden in Batches aufgeteilt und parallel verarbeitet.
    """
    manager = get_distributed_compute()

    priority_map = {
        "low": TaskPriority.LOW,
        "normal": TaskPriority.NORMAL,
        "high": TaskPriority.HIGH,
        "urgent": TaskPriority.URGENT,
    }

    task_ids = await manager.submit_batch_task(
        task_type=batch.task_type,
        input_items=batch.input_items,
        model_id=batch.model_id,
        batch_size=batch.batch_size,
        priority=priority_map.get(batch.priority.lower(), TaskPriority.NORMAL),
    )

    return JSONResponse(content={
        "task_ids": task_ids,
        "batch_count": len(task_ids),
        "total_items": len(batch.input_items),
        "message": "Batch submitted for distributed processing",
    })


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """Gibt Status eines Tasks zurück."""
    manager = get_distributed_compute()
    status = await manager.get_task_status(task_id)

    if not status:
        raise HTTPException(status_code=404, detail="Task not found")

    return JSONResponse(content=status)


@router.get("/task/{task_id}/result")
async def get_task_result(
    task_id: str,
    wait: bool = Query(True, description="Warten bis Ergebnis verfügbar"),
    timeout: float = Query(30.0, description="Max. Wartezeit in Sekunden"),
):
    """
    Holt das Ergebnis eines Tasks.

    Mit `wait=true` blockiert der Request bis das Ergebnis verfügbar ist.
    """
    manager = get_distributed_compute()

    try:
        result = await manager.get_task_result(task_id, wait=wait, timeout=timeout)

        if result is None:
            return JSONResponse(content={
                "task_id": task_id,
                "status": "pending",
                "result": None,
            })

        return JSONResponse(content={
            "task_id": task_id,
            "status": "completed",
            "result": result,
        })

    except TimeoutError:
        return JSONResponse(
            content={"error": "Timeout waiting for result"},
            status_code=408,
        )
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500,
        )


@router.delete("/task/{task_id}")
async def cancel_task(task_id: str):
    """Bricht einen Task ab."""
    manager = get_distributed_compute()
    success = await manager.cancel_task(task_id)

    if not success:
        raise HTTPException(status_code=404, detail="Task not found or already completed")

    return JSONResponse(content={
        "task_id": task_id,
        "status": "cancelled",
    })


@router.get("/stats")
async def get_stats():
    """
    Gibt Statistiken über das Distributed Compute Network zurück.

    Inkludiert:
    - Queue-Status
    - Verbundene Workers
    - Gesamt-Statistiken
    - Top Contributors
    """
    manager = get_distributed_compute()
    return JSONResponse(content=manager.get_stats())


@router.get("/workers")
async def get_workers():
    """Liste aller verbundenen Workers."""
    manager = get_distributed_compute()

    workers = []
    for client in manager._clients.values():
        workers.append({
            "session_id": client.session_id[:8] + "...",
            "capability": client.capability,
            "gpu_name": client.gpu_name,
            "estimated_tflops": client.estimated_tflops,
            "is_available": client.is_available,
            "tasks_completed": client.tasks_completed,
            "credits_earned": round(client.credits_earned, 2),
        })

    return JSONResponse(content={
        "workers": workers,
        "total": len(workers),
        "available": sum(1 for w in workers if w["is_available"]),
    })


@router.get("/credits/{session_id}")
async def get_client_credits(session_id: str):
    """
    Gibt Credits eines Workers zurück.

    Credits werden für erfolgreich abgeschlossene Tasks vergeben.
    """
    manager = get_distributed_compute()
    credits = manager.get_client_credits(session_id)

    if not credits:
        raise HTTPException(status_code=404, detail="Worker not found")

    return JSONResponse(content=credits)


# === Convenience Endpoints ===

@router.post("/embed")
async def distributed_embed(
    texts: List[str],
    model_id: str = "embedding_small",
    priority: str = "normal",
):
    """
    Convenience-Endpoint für verteilte Embedding-Berechnung.

    Verteilt die Texte auf verfügbare Workers.
    """
    manager = get_distributed_compute()

    if len(texts) <= 10:
        # Kleine Batches als einzelnen Task
        task_id = await manager.submit_task(
            task_type="embedding",
            input_data=texts,
            model_id=model_id,
            priority=TaskPriority.NORMAL,
        )
        return JSONResponse(content={"task_id": task_id, "batch_count": 1})
    else:
        # Größere Mengen als Batch
        task_ids = await manager.submit_batch_task(
            task_type="embedding",
            input_items=texts,
            model_id=model_id,
            batch_size=10,
        )
        return JSONResponse(content={"task_ids": task_ids, "batch_count": len(task_ids)})


@router.post("/sentiment")
async def distributed_sentiment(
    texts: List[str],
    model_id: str = "sentiment",
    priority: str = "normal",
):
    """Convenience-Endpoint für verteilte Sentiment-Analyse."""
    manager = get_distributed_compute()

    task_ids = await manager.submit_batch_task(
        task_type="sentiment",
        input_items=texts,
        model_id=model_id,
        batch_size=20,
    )

    return JSONResponse(content={"task_ids": task_ids, "batch_count": len(task_ids)})
