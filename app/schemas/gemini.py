from typing import Any, List, Optional
from pydantic import BaseModel


class GeminiMessage(BaseModel):
    role: str
    parts: List[Any]