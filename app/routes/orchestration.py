from fastapi import APIRouter, Depends, BackgroundTasks, Request, HTTPException
from typing import Dict, Any, Optional
from app.services.orchestrator import OrchestratorService, CrawlerManager, ChatService, WordPressService
# Annahme: Abhängigkeiten für Orchestrator-Service
# from app.services.crawler.manager import CrawlerManager
# from app.services.chat import ChatService
# from app.services.wordpress import WordPressService

router = APIRouter()

# Dependency Injection für den Orchestrator
def get_orchestrator_service() -> OrchestratorService:
    # Hier müssten die tatsächlichen Instanzen der Services übergeben werden
    # Dies ist eine vereinfachte Darstellung
    crawler_manager = CrawlerManager() # Oder aus einem globalen App-State holen
    chat_service = ChatService()
    wordpress_service = WordPressService()
    return OrchestratorService(crawler_manager, chat_service, wordpress_service)

@router.post("/orchestrate/crawl-summarize-post", tags=["Orchestration"], summary="Starts a crawl, summarize, and post workflow")
async def start_crawl_summarize_post(
    request_data: Dict[str, Any],
    orchestrator: OrchestratorService = Depends(get_orchestrator_service),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    url = request_data.get("url")
    title = request_data.get("title")
    correlation_id = request_data.get("correlation_id")
    idempotency_key = request_data.get("idempotency_key")

    if not url:
        raise HTTPException(status_code=400, detail="URL is required.")

    # Führe den Workflow im Hintergrund aus, um den Request schnell zu beantworten
    background_tasks.add_task(orchestrator.crawl_summarize_and_post, url, title, correlation_id, idempotency_key)

    return {"message": "Workflow started in background.", "url": url, "correlation_id": correlation_id}

@router.get("/orchestrate/status/{correlation_id}", tags=["Orchestration"], summary="Gets the status of an orchestration workflow")
async def get_workflow_status(correlation_id: str):
    # Hier müsste der tatsächliche Status aus einem persistenten Speicher (DB, Redis) gelesen werden
    # Für dieses Beispiel simulieren wir einen Status
    # In einer echten Anwendung würde der Orchestrator den Status aktualisieren
    # und dieser Endpunkt würde ihn abrufen.
    # Beispiel: status_info = await workflow_status_store.get_status(correlation_id)
    # Wenn kein Status gefunden, dann 404
    if correlation_id == "simulated-completed-id":
        return {"correlation_id": correlation_id, "status": "completed", "progress": 100, "result": {"post_id": 123, "url": "..."}}
    elif correlation_id == "simulated-processing-id":
        return {"correlation_id": correlation_id, "status": "processing", "progress": 75, "message": "Creating post draft..."}
    else:
        raise HTTPException(status_code=404, detail="Workflow not found or still initializing.")
