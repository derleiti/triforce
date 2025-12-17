from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class CrawlJobRequest(BaseModel):
    keywords: List[str]
    seeds: List[HttpUrl]
    max_depth: int = 2
    max_pages: int = 60
    rate_limit: float = 1.0
    relevance_threshold: float = 0.35
    allow_external: bool = False
    user_context: Optional[str] = None
    requested_by: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    priority: str = "low" # New priority field
    idempotency_key: Optional[str] = None


class CrawlJobResponse(CrawlJobRequest):
    id: str
    status: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    pages_crawled: int
    results: List[str]
    error: Optional[str] = None


class CrawlResultResponse(BaseModel):
    id: str
    job_id: str
    url: str
    depth: int
    parent_url: Optional[str]
    status: str
    title: str
    summary: Optional[str]
    headline: Optional[str]
    content: str
    excerpt: str
    meta_description: Optional[str]
    keywords_matched: List[str]
    score: float
    publish_date: Optional[str]
    created_at: datetime
    updated_at: datetime
    rating_average: float
    rating_count: int
    confirmations: int
    tags: List[str]
    posted_at: Optional[datetime] = None
    post_id: Optional[int] = None
    topic_id: Optional[int] = None
    normalized_text: Optional[str] = None
    content_hash: Optional[str] = None
    source_domain: Optional[str] = None
    labels: List[str] = []
    tokens_est: Optional[int] = None


class CrawlFeedbackRequest(BaseModel):
    score: float
    comment: Optional[str] = None
    source: str
    confirmed: bool = False


class CrawlPublicationRequest(BaseModel):
    post_id: Optional[int] = None
    topic_id: Optional[int] = None


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
    ts: datetime
    source_domain: Optional[str] = None


class CrawlerTrainShard(BaseModel):
    name: str
    records: int
    size_bytes: int
    created_at: datetime


class CrawlerTrainIndex(BaseModel):
    shards: List[CrawlerTrainShard]
