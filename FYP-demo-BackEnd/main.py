import os

import uvicorn

from app.app_factory import create_app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    keep_alive = int(os.getenv("UVICORN_KEEP_ALIVE", 180))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        reload_dirs=["app/", "main.py"],
        timeout_keep_alive=keep_alive,
    )
