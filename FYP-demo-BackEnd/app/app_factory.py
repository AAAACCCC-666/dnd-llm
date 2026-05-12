from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from lmnr import Laminar
import os
from contextlib import asynccontextmanager

# Load environment variables from .env file
load_dotenv()

# Initialize file logging
from app.utils.logger import setup_file_logging, get_logger, cleanup_old_logs
from app.utils.read_data import load_system_prompt, load_options_prompt

# 设置文件日志
setup_file_logging()

# Ensure critical prompt files exist at startup
load_system_prompt()
load_options_prompt()

# 清理旧日志文件（保留30天，只在主进程执行）
import multiprocessing

if multiprocessing.current_process().name == "MainProcess":
    try:
        cleanup_old_logs()
    except Exception as e:
        print(f"Error cleaning old log files: {e}")

logger = get_logger(__name__)

# Initialize Laminar for LLM interactions
lmnr_project_api_key = os.getenv("LMNR_PROJECT_API_KEY")
lmnr_base_url = os.getenv("LMNR_BASE_URL", "http://localhost")
lmnr_http_port = int(os.getenv("LMNR_HTTP_PORT", 8000))
lmnr_grpc_port = int(os.getenv("LMNR_GRPC_PORT", 8001))

# Only initialize Laminar if the project API key is set
if lmnr_project_api_key:
    Laminar.initialize(
        project_api_key=lmnr_project_api_key,
        base_url=lmnr_base_url,
        http_port=lmnr_http_port,
        grpc_port=lmnr_grpc_port,
    )
    logger.info("Laminar initialized")
else:
    logger.info("LMNR_PROJECT_API_KEY not set, skipping Laminar initialization")

from app.db.database import engine, SessionLocal  # Import engine & session
from app.db import models  # Ensure models are imported
from app.db.init_db import (
    try_initialize_static_data,
)  # Import the initialization function
from app.services.rag.rag import ensure_dm_vectorstore
from app.services import settings_service

# Create database tables on startup
# This should happen before any modules that query the DB are imported
logger.info("Creating database tables...")
models.Base.metadata.create_all(bind=engine)
logger.info("Database tables created.")

# Seed configuration from environment on first run (database has higher priority)
with SessionLocal() as seed_db:
    settings_service.seed_settings_from_env(seed_db)

# Warn if critical secrets are missing
with SessionLocal() as check_db:
    if not settings_service.get_setting(check_db, "OPENAI_API_KEY"):
        logger.warning(
            "OPENAI_API_KEY 未配置，LLM 相关功能将不可用。"
            "请通过 /api/settings 接口或直接更新数据库进行配置。"
        )

# Initialize static D&D data
# This should be called after tables are created
logger.info("Attempting to initialize D&D static data...")
try_initialize_static_data()
logger.info("D&D static data initialization process finished.")

# Now, import API modules after the database is ready
from app.api import chat, sessions, characters, stories, settings


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    """FastAPI 生命周期，用于在启动时构建 RAG 资源。"""
    logger.info("Ensuring DM guide vector store is ready (lifespan)...")
    rag_config = None
    with SessionLocal() as db:
        try:
            rag_config = settings_service.build_rag_config(db)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to build RAG config from settings")

    try:
        await ensure_dm_vectorstore(config=rag_config)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to ensure DM guide vector store")
    yield


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(lifespan=app_lifespan)

    # CORS Configuration
    origins_str = os.getenv("CORS_ORIGINS")
    origins = []
    if origins_str:
        origins = [origin.strip() for origin in origins_str.split(",")]

    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Include API routers
    app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
    app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
    app.include_router(characters.router, prefix="/api/characters", tags=["Characters"])
    app.include_router(stories.router, prefix="/api/stories", tags=["Stories"])
    app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])

    @app.get("/api")
    async def root():
        return {"message": "Welcome to the LLM Interaction API"}

    return app
