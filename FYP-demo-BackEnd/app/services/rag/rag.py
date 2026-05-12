"""确保 D&D DM 指南向量库存在的入口模块。"""

from __future__ import annotations

import asyncio
import time
from typing import Sequence

import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from pydantic import SecretStr

from app.services.rag.rag_config import RagConfig, load_rag_config
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def ensure_dm_vectorstore(config: RagConfig | None = None) -> None:
    """在应用启动时保证 DM 指南向量库已经构建。"""
    cfg = config or load_rag_config()

    if not cfg.enabled:
        logger.info(
            "RAG feature disabled (RAG_ENABLED=False or missing RAG_EMBEDDING_MODEL); skipping vector store initialization."
        )
        return

    if not cfg.dm_source_path.exists():
        logger.warning(
            "RAG source file missing; expected path: %s. Skipping embedding.",
            cfg.dm_source_path.resolve(),
        )
        return

    chroma_dir = cfg.chroma_dir
    chroma_dir.mkdir(parents=True, exist_ok=True)

    embedding_client = _build_embedding_client(cfg)
    vector_store = _build_vector_store(cfg, embedding_client)
    collection = getattr(vector_store, "_collection", None)

    existing_count = 0
    if collection is not None:
        try:
            existing_count = collection.count()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Failed to read Chroma collection document count: %s", exc)

    if existing_count > 0:
        logger.info(
            "Chroma collection %s already has %s records; skipping rebuild.",
            cfg.collection_name,
            existing_count,
        )
        return

    documents = _load_and_split(cfg)
    if not documents:
        logger.warning(
            "No valid documents after splitting the DM guide; skipping embedding."
        )
        return

    logger.info(
        "Starting Chroma collection %s build: %s documents, batch size %s, concurrency %s.",
        cfg.collection_name,
        len(documents),
        cfg.embedding_batch_size,
        cfg.embedding_concurrency,
    )

    ingest_start = time.perf_counter()
    inserted = await _run_async_ingest(vector_store, documents, cfg, embedding_client)
    ingest_elapsed = time.perf_counter() - ingest_start

    _persist_vector_store(vector_store)

    logger.info(
        "Finished building Chroma collection %s; inserted %s records in %.2fs.",
        cfg.collection_name,
        inserted,
        ingest_elapsed,
    )


def _build_embedding_client(cfg: RagConfig) -> OpenAIEmbeddings:
    """初始化嵌入客户端，支持自定义 base_url 与 api_key。"""
    api_key = SecretStr(cfg.embedding_api_key) if cfg.embedding_api_key else None
    base_url = cfg.embedding_base_url.rstrip("/") if cfg.embedding_base_url else None

    if api_key is not None and base_url is not None:
        return OpenAIEmbeddings(
            model=cfg.embedding_model, api_key=api_key, base_url=base_url
        )
    if api_key is not None:
        return OpenAIEmbeddings(model=cfg.embedding_model, api_key=api_key)
    if base_url is not None:
        return OpenAIEmbeddings(model=cfg.embedding_model, base_url=base_url)
    return OpenAIEmbeddings(model=cfg.embedding_model)


def _build_vector_store(cfg: RagConfig, embedding_client: OpenAIEmbeddings) -> Chroma:
    """创建或获取持久化的 Chroma 向量库。"""
    client_settings = Settings(
        anonymized_telemetry=False,
        is_persistent=True,
        persist_directory=str(cfg.chroma_dir),
    )
    chroma_client = chromadb.PersistentClient(
        path=str(cfg.chroma_dir), settings=client_settings
    )
    return Chroma(
        client=chroma_client,
        collection_name=cfg.collection_name,
        embedding_function=embedding_client,
    )


def _load_and_split(cfg: RagConfig) -> Sequence[Document]:
    """读取 Markdown 文档并切分成可嵌入的文档片段。"""
    read_start = time.perf_counter()
    markdown_text = cfg.dm_source_path.read_text(encoding="utf-8")
    read_elapsed = time.perf_counter() - read_start

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=list(cfg.headers_to_split_on),
        strip_headers=False,
    )
    header_chunks = markdown_splitter.split_text(markdown_text)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=cfg.chunk_size,
        chunk_overlap=cfg.chunk_overlap,
    )
    documents = text_splitter.split_documents(header_chunks)

    logger.info(
        "Finished reading and splitting DM guide: %s original sections, %s split documents, read took %.2fs.",
        len(header_chunks),
        len(documents),
        read_elapsed,
    )
    return documents


async def _run_async_ingest(
    vector_store: Chroma,
    documents: Sequence[Document],
    cfg: RagConfig,
    embedding_client: OpenAIEmbeddings,
) -> int:
    """运行异步向量化流程，必要时退回同步模式。"""
    try:
        return await _ingest_documents_async(
            vector_store, documents, cfg, embedding_client
        )
    except Exception:  # noqa: BLE001
        logger.warning(
            "Async ingest failed; falling back to synchronous writes.",
            exc_info=True,
        )
        return await asyncio.to_thread(
            _ingest_documents_sync,
            vector_store,
            documents,
            cfg,
            embedding_client,
        )


async def _ingest_documents_async(
    vector_store: Chroma,
    documents: Sequence[Document],
    cfg: RagConfig,
    embedding_client: OpenAIEmbeddings,
) -> int:
    """并发批量写入嵌入向量。"""
    collection = getattr(vector_store, "_collection", None)
    if collection is None:
        raise RuntimeError("Chroma 实例未暴露底层 collection。")

    total_docs = len(documents)
    if total_docs == 0:
        return 0

    batch_size = max(1, cfg.embedding_batch_size)
    max_concurrency = max(1, cfg.embedding_concurrency)
    batch_starts = list(range(0, total_docs, batch_size))
    total_batches = len(batch_starts)
    semaphore = asyncio.Semaphore(max_concurrency)
    store_lock = asyncio.Lock()

    async def embed_and_add(batch_index: int, start: int) -> dict[str, float | int]:
        docs = documents[start : start + batch_size]
        if not docs:
            return {"batch_index": batch_index, "docs": 0, "elapsed": 0.0}

        ids = [f"{cfg.collection_name}-{start + offset}" for offset in range(len(docs))]
        texts = [doc.page_content for doc in docs]
        metadatas = [doc.metadata for doc in docs]

        batch_timer = time.perf_counter()
        async with semaphore:
            embeddings = await embedding_client.aembed_documents(texts)

        async with store_lock:
            await asyncio.to_thread(
                collection.add,
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=texts,
            )
        elapsed = time.perf_counter() - batch_timer
        return {"batch_index": batch_index, "docs": len(docs), "elapsed": elapsed}

    tasks = [
        asyncio.create_task(embed_and_add(idx, start))
        for idx, start in enumerate(batch_starts)
    ]
    if not tasks:
        return 0

    total_inserted = 0
    completed = 0
    log_every = 10

    for task in asyncio.as_completed(tasks):
        result = await task
        total_inserted += int(result["docs"])
        completed += 1

        if completed == 1 or completed % log_every == 0 or completed == total_batches:
            logger.info(
                "Batch %s/%s wrote %s documents in %.2fs.",
                result["batch_index"] + 1,
                total_batches,
                result["docs"],
                result["elapsed"],
            )

    return total_inserted


def _ingest_documents_sync(
    vector_store: Chroma,
    documents: Sequence[Document],
    cfg: RagConfig,
    embedding_client: OpenAIEmbeddings,
) -> int:
    """同步批量写入嵌入向量（异步不可用时的退路）。"""
    collection = getattr(vector_store, "_collection", None)
    if collection is None:
        raise RuntimeError("Chroma 实例未暴露底层 collection。")

    total_docs = len(documents)
    batch_size = max(1, cfg.embedding_batch_size)
    total_inserted = 0

    for batch_index, start in enumerate(range(0, total_docs, batch_size), start=1):
        batch_docs = documents[start : start + batch_size]
        ids = [
            f"{cfg.collection_name}-{start + offset}"
            for offset in range(len(batch_docs))
        ]
        texts = [doc.page_content for doc in batch_docs]
        metadatas = [doc.metadata for doc in batch_docs]

        batch_timer = time.perf_counter()
        embeddings = embedding_client.embed_documents(texts)
        collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=texts,
        )
        elapsed = time.perf_counter() - batch_timer
        total_inserted += len(batch_docs)

        if batch_index == 1 or batch_index % 10 == 0 or total_inserted == total_docs:
            logger.info(
                "Batch %s/%s wrote %s documents in %.2fs (sync mode).",
                batch_index,
                (total_docs + batch_size - 1) // batch_size,
                len(batch_docs),
                elapsed,
            )

    return total_inserted


def _persist_vector_store(vector_store: Chroma) -> None:
    """触发 Chroma 落盘。"""
    persist_start = time.perf_counter()
    persist_fn = getattr(vector_store, "persist", None)

    if callable(persist_fn):
        persist_fn()
    else:
        client = getattr(vector_store, "_client", None)
        if client is not None:
            client_persist = getattr(client, "persist", None)
            if callable(client_persist):
                client_persist()

    persist_elapsed = time.perf_counter() - persist_start
    logger.info("Chroma data persisted in %.2fs.", persist_elapsed)
