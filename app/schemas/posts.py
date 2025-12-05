from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Post(BaseModel):
    id: str
    title: str
    content: str
    crawl_result_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CreatePostRequest(BaseModel):
    crawl_result_id: str
    prompt: Optional[str] = None
