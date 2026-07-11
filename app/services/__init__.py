"""Service layer exports.

Avoid importing submodules at package import time to keep test imports lightweight.
Import submodules directly where needed (e.g., `from app.services import model_registry`).
"""

__all__ = ["agents", "chat", "model_registry", "text_analysis", "vision"]
