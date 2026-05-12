"""RAG 检索服务，提供规则查询接口。"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict, List

from langchain_core.documents import Document

from app.services.rag.rag_config import RagConfig, load_rag_config
from app.services.rag.rag import _build_embedding_client, _build_vector_store

logger = logging.getLogger(__name__)


@lru_cache(maxsize=4)
def _get_retriever(cfg: RagConfig):
    """基于配置初始化或复用 Chroma 检索器。"""
    vector_store = _build_vector_store(cfg, _build_embedding_client(cfg))
    top_k = max(1, cfg.search_top_k)
    return vector_store.as_retriever(search_kwargs={"k": top_k})


def build_rag_context(query: str) -> Dict[str, Any]:
    """构建可序列化的 RAG 上下文。"""
    query_text = (query or "").strip()
    cfg = load_rag_config()

    if not cfg.enabled:
        return {
            "enabled": False,
            "status": "disabled",
            "query": query_text,
            "results": [],
        }

    if not query_text:
        return {
            "enabled": True,
            "status": "empty_query",
            "query": query_text,
            "results": [],
        }

    try:
        retriever = _get_retriever(cfg)
    except Exception as exc:  # noqa: BLE001
        logger.error("初始化 RAG 检索器失败: %s", exc, exc_info=True)
        return {
            "enabled": True,
            "status": "error",
            "query": query_text,
            "results": [],
            "error": str(exc),
        }

    try:
        documents = retriever.invoke(query_text)
    except Exception as exc:  # noqa: BLE001
        logger.error("RAG 检索执行失败: %s", exc, exc_info=True)
        return {
            "enabled": True,
            "status": "error",
            "query": query_text,
            "results": [],
            "error": str(exc),
        }

    results = [_document_to_payload(doc, cfg) for doc in documents if doc]
    return {
        "enabled": True,
        "status": "ok" if results else "no_results",
        "query": query_text,
        "results": results,
    }


def retrieve_dm_rules(query: str) -> List[Dict[str, Any]]:
    """保留向后兼容的简化接口。"""
    context = build_rag_context(query)
    return context.get("results", [])


def _document_to_payload(document: Document, cfg: RagConfig) -> Dict[str, Any]:
    """规范化检索文档的返回结构。"""
    return {
        "collection": cfg.collection_name,
        "content": document.page_content,
        "metadata": document.metadata or {},
    }
