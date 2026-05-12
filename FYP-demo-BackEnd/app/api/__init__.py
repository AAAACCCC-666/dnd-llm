"""API package for FastAPI routers.

Expose submodules so tools like Pylance can resolve
`from app.api import chat, sessions, characters, stories` without报红.
"""

from . import chat, sessions, characters, stories

__all__ = ["chat", "sessions", "characters", "stories"]
