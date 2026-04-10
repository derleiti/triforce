from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from ..schemas.posts import Post, CreatePostRequest
from ..services.posts import posts_service

router = APIRouter(prefix="/posts", tags=["posts"])
logger = logging.getLogger("ailinux.posts")

@router.post("/", response_model=Post)
async def create_post_endpoint(payload: CreatePostRequest):
    try:
        post = await posts_service.create_post(payload)
        return post
    except Exception as e:
        logger.error("Post creation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e
