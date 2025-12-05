from pydantic import BaseModel


class GeminiMessage(BaseModel):
    role: str
    parts: list[str]
