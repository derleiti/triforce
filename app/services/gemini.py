from app.schemas.gemini import GeminiMessage


def generate_gemini_message() -> GeminiMessage:
    return GeminiMessage(role="user", parts=["Hello, Gemini!"])
