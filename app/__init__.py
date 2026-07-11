"""App package init - lazily import heavy components.

Avoid importing app.main at package import time to keep test imports lightweight.
"""

def create_app(*args, **kwargs):
    from .main import create_app as _create_app
    return _create_app(*args, **kwargs)


def get_app():
    from .main import app as _app
    return _app


__all__ = ["create_app", "get_app"]
