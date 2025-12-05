from __future__ import annotations

import uuid
from typing import Dict, Optional

from .crawler.manager import crawler_manager
from . import chat as chat_service
from ..schemas.posts import Post, CreatePostRequest
from ..utils.errors import api_error
from ..services.model_registry import registry

class PostsService:
    def __init__(self) -> None:
        self._posts: Dict[str, Post] = {}

    async def create_post(self, payload: CreatePostRequest) -> Post:
        crawl_result = await crawler_manager.get_result(payload.crawl_result_id)
        if not crawl_result:
            raise api_error("Crawl result not found", status_code=404, code="crawl_result_not_found")

        model_id = "gpt-oss:cloud/120b"
        model = await registry.get_model(model_id)
        if not model:
            raise api_error(f"Model {model_id} not found", status_code=404, code="model_not_found")

        prompt = payload.prompt or f"Write a news article based on the following crawled content:\n\nTitle: {crawl_result.title}\n\nSummary: {crawl_result.summary}\n\nContent: {crawl_result.content}"

        messages = [
            {"role": "system", "content": "You are a news writer. Your task is to write a news article based on the provided content."},
            {"role": "user", "content": prompt},
        ]

        chunks = []
        async for chunk in chat_service.stream_chat(
            model,
            model_id,
            messages,
            stream=True,
        ):
            chunks.append(chunk)
        
        article_content = "".join(chunks)

        post = Post(
            id=str(uuid.uuid4()),
            title=crawl_result.title,
            content=article_content,
            crawl_result_id=payload.crawl_result_id,
        )
        self._posts[post.id] = post
        return post

posts_service = PostsService()
