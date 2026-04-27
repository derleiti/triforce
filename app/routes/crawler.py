from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from fastapi.responses import FileResponse

from ..schemas import (
    CrawlFeedbackRequest,
    CrawlJobRequest,
    CrawlJobResponse,
    CrawlPublicationRequest,
    CrawlResultResponse,
)
from ..services.crawler.manager import crawler_manager
from ..services.crawler.user_crawler import user_crawler

router = APIRouter()

class CrawlerSearchRequest(BaseModel):
    query: str
    limit: int = 20
    min_score: float = 0.35
    freshness_days: int = 7

class CrawlerSearchResult(BaseModel):
    url: str
    title: str
    excerpt: str
    score: float
    ts: str
    source_domain: str

class CrawlerTrainIndex(BaseModel):
    shards: List[dict]

def _serialize_job(job) -> dict:
    payload = job.to_dict()
    payload["allowed_domains"] = list(job.allowed_domains)
    return payload


def _serialize_result(result, *, include_content: bool = True) -> dict:
    payload = result.to_dict(include_content=include_content)
    if "keywords_matched" in payload and "tags" not in payload:
        payload["tags"] = payload["keywords_matched"]
    return payload


@router.post("/jobs", response_model=CrawlJobResponse)
async def create_job(payload: CrawlJobRequest):
    """
    Create crawler job.

    IMPORTANT: User-initiated jobs (e.g., from /crawl prompt) automatically use
    the fast user_crawler instance with dedicated workers for quick processing.
    """
    # Determine if this is a user request (from /crawl prompt)
    is_user_request = payload.requested_by == "user" or payload.priority == "high"

    if is_user_request and len(payload.seeds) == 1:
        # Use fast user_crawler for single-URL user requests
        job = await user_crawler.crawl_url(
            url=str(payload.seeds[0]),
            keywords=payload.keywords,
            max_pages=payload.max_pages,
            idempotency_key=payload.idempotency_key,
        )
    else:
        # Use main crawler_manager for bulk/auto jobs
        job = await crawler_manager.create_job(
            keywords=payload.keywords,
            seeds=[str(url) for url in payload.seeds],
            max_depth=payload.max_depth,
            max_pages=payload.max_pages,
            rate_limit=payload.rate_limit,
            relevance_threshold=payload.relevance_threshold,
            allow_external=payload.allow_external,
            user_context=payload.user_context,
            requested_by=payload.requested_by,
            metadata=payload.metadata or {},
            priority=payload.priority,
            idempotency_key=payload.idempotency_key,
        )
    return _serialize_job(job)


@router.get("/crawler/jobs", response_model=List[CrawlJobResponse])
async def list_jobs():
    jobs = await crawler_manager.list_jobs()
    return [_serialize_job(job) for job in jobs]


@router.get("/crawler/jobs/{job_id}", response_model=CrawlJobResponse)
async def get_job(job_id: str):
    job = await crawler_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"error": {"code": "job_not_found", "message": "Crawler job not found"}})
    return _serialize_job(job)


@router.get("/crawler/results/ready", response_model=List[CrawlResultResponse])
async def ready_results(
    limit: int = Query(10, ge=1, le=50),
    min_age_minutes: int = Query(60, ge=15, le=720),
):
    results = await crawler_manager.ready_for_publication(limit=limit, min_age_minutes=min_age_minutes)
    return [_serialize_result(result, include_content=True) for result in results]


@router.get("/crawler/results/{result_id}", response_model=CrawlResultResponse)
async def get_result(result_id: str, include_content: bool = True):
    result = await crawler_manager.get_result(result_id)
    if not result:
        raise HTTPException(status_code=404, detail={"error": {"code": "result_not_found", "message": "Crawl result not found"}})
    return _serialize_result(result, include_content=include_content)


@router.post("/crawler/results/{result_id}/feedback", response_model=CrawlResultResponse)
async def submit_feedback(result_id: str, payload: CrawlFeedbackRequest):
    result = await crawler_manager.add_feedback(
        result_id,
        score=payload.score,
        comment=payload.comment,
        confirmed=payload.confirmed,
        source=payload.source,
    )
    if not result:
        raise HTTPException(status_code=404, detail={"error": {"code": "result_not_found", "message": "Crawl result not found"}})
    return _serialize_result(result)


@router.post("/crawler/results/{result_id}/mark-posted", response_model=CrawlResultResponse)
async def mark_posted(result_id: str, payload: CrawlPublicationRequest):
    result = await crawler_manager.mark_posted(
        result_id,
        post_id=payload.post_id,
        topic_id=payload.topic_id,
    )
    if not result:
        raise HTTPException(status_code=404, detail={"error": {"code": "result_not_found", "message": "Crawl result not found"}})
    return _serialize_result(result)


@router.post("/crawler/search", response_model=List[CrawlerSearchResult])
async def search_crawler_results(payload: CrawlerSearchRequest):
    results = await crawler_manager.search(
        query=payload.query,
        limit=payload.limit,
        min_score=payload.min_score,
        freshness_days=payload.freshness_days,
    )
    return results


@router.get("/crawler/train/shards", response_model=CrawlerTrainIndex)
async def list_train_shards():
    return crawler_manager._train_index


@router.get("/crawler/train/shards/{name}")
async def get_train_shard(name: str):
    shard_path = crawler_manager._train_dir / name
    if not shard_path.exists():
        raise HTTPException(status_code=404, detail={"error": {"code": "shard_not_found", "message": "Training data shard not found"}})
    return FileResponse(str(shard_path), media_type="application/x-gzip")
