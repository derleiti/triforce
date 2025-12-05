from pydantic import BaseModel, Field
from typing import Optional

class ImageGenerationRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = None
    width: int = Field(default=512, ge=1, le=1024)  # Example validation
    height: int = Field(default=512, ge=1, le=1024) # Example validation
    steps: int = Field(default=20, ge=1, le=100)
    cfg_scale: float = Field(default=7.0, ge=1.0, le=30.0)
    sampler_name: str = "Euler a"
    seed: int = -1
    model: Optional[str] = None
