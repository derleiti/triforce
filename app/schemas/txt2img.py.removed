from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class Txt2ImgRequest(BaseModel):
    """Request model for text-to-image generation via ComfyUI."""
    prompt: str = Field(..., description="The text prompt for image generation")
    negative_prompt: Optional[str] = Field("", description="Negative prompt to avoid certain elements")
    width: int = Field(512, ge=64, le=2048, description="Image width in pixels")
    height: int = Field(512, ge=64, le=2048, description="Image height in pixels")
    steps: int = Field(20, ge=1, le=100, description="Number of sampling steps")
    cfg_scale: float = Field(7.0, ge=1.0, le=30.0, description="Classifier-free guidance scale")
    seed: int = Field(-1, description="Random seed (-1 for random)")
    model: Optional[str] = Field(None, description="Model name to use")
    workflow_type: Optional[Literal["auto", "sd15", "sd35", "sdxl"]] = Field(
        "auto",
        description="Workflow type: 'auto' (recommended), 'sd15', 'sd35', or 'sdxl'"
    )

class ImageData(BaseModel):
    """Model for individual generated image data."""
    filename: str
    data: str  # Base64 encoded image data
    seed: Optional[int] = None

class Txt2ImgResponse(BaseModel):
    """Response model for text-to-image generation."""
    images: List[ImageData] = Field(default_factory=list, description="List of generated images")
    prompt_id: Optional[str] = Field(None, description="ComfyUI prompt ID for tracking")
    model: Optional[str] = Field(None, description="Model used for generation")
    error: Optional[str] = Field(None, description="Error message if generation failed")
    workflow_type: Optional[str] = Field(None, description="Workflow executed for generation")
