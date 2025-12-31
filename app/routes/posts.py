from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas.posts import Post, CreatePostRequest
from ..services.posts import posts_service

router = APIRouter(prefix="/posts", tags=["posts"])

@router.post("/", response_model=Post)
async def create_post_endpoint(payload: CreatePostRequest):
    try:
        post = await posts_service.create_post(payload)
        return post
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
