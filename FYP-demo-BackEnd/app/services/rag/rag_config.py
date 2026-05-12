"""RAG 向量化初始化的配置解析模块。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Sequence, Tuple
import os

DEFAULT_HEADERS: List[Tuple[str, str]] = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
    ("####", "h4"),
    ("#####", "h5"),
]


@dataclass(frozen=True)
class RagConfig:
    enabled: bool
    dm_source_path: Path
    chroma_dir: Path
    collection_name: str
    embedding_model: str
    embedding_api_key: str | None
    embedding_base_url: str | None
    embedding_batch_size: int
    embedding_concurrency: int
    chunk_size: int
    chunk_overlap: int
    headers_to_split_on: Sequence[Tuple[str, str]]
    search_top_k: int


def load_rag_config(
    value_resolver: Callable[[str], str | None] | None = None,
) -> RagConfig:
    """
    从配置源加载 RAG 向量化参数。

    Args:
        value_resolver: 可选的取值函数，优先于环境变量，用于支持数据库优先策略。
    """

    resolver = value_resolver or os.getenv

    raw_embedding_model = resolver("RAG_EMBEDDING_MODEL")
    if raw_embedding_model:
        trimmed_embedding_model = raw_embedding_model.strip()
    else:
        trimmed_embedding_model = ""

    has_embedding_model = bool(trimmed_embedding_model)
    embedding_model = trimmed_embedding_model or "text-embedding-3-large"

    enabled = _bool_env("RAG_ENABLED", resolver, default=True) and has_embedding_model
    dm_source_path = _path_env("RAG_DM_SOURCE_PATH", resolver, Path("assets/DM.md"))
    chroma_dir = _path_env("RAG_CHROMA_DIR", resolver, Path("data/chromadb"))
    collection_name = _str_env("RAG_CHROMA_COLLECTION", resolver, "dm_guide_2024")
    embedding_api_key = _optional_str_env(
        "RAG_EMBEDDING_API_KEY", resolver, fallback="OPENAI_API_KEY"
    )
    embedding_base_url = _optional_str_env(
        "RAG_EMBEDDING_BASE_URL", resolver, fallback="OPENAI_BASE_URL"
    )

    batch_size = _positive_int_env("RAG_EMBEDDING_BATCH_SIZE", resolver, default=16)
    concurrency = _positive_int_env("RAG_EMBEDDING_CONCURRENCY", resolver, default=4)
    chunk_size = _positive_int_env("RAG_SPLIT_CHUNK_SIZE", resolver, default=4000)
    chunk_overlap = _non_negative_int_env(
        "RAG_SPLIT_CHUNK_OVERLAP", resolver, default=400
    )
    headers = _headers_env("RAG_SPLIT_HEADERS", resolver, DEFAULT_HEADERS)
    search_top_k = _positive_int_env("RAG_SEARCH_TOP_K", resolver, default=4)

    return RagConfig(
        enabled=enabled,
        dm_source_path=dm_source_path,
        chroma_dir=chroma_dir,
        collection_name=collection_name,
        embedding_model=embedding_model,
        embedding_api_key=embedding_api_key,
        embedding_base_url=embedding_base_url,
        embedding_batch_size=batch_size,
        embedding_concurrency=concurrency,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        headers_to_split_on=headers,
        search_top_k=search_top_k,
    )


def _str_env(name: str, resolver: Callable[[str], str | None], default: str) -> str:
    value = resolver(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _optional_str_env(
    name: str, resolver: Callable[[str], str | None], fallback: str | None = None
) -> str | None:
    value = resolver(name)
    if value:
        trimmed = value.strip()
        return trimmed or None
    if fallback:
        fb_value = resolver(fallback)
        if fb_value:
            trimmed = fb_value.strip()
            return trimmed or None
    return None


def _path_env(name: str, resolver: Callable[[str], str | None], default: Path) -> Path:
    raw = resolver(name)
    if not raw or raw.strip() == "":
        return default
    return Path(raw.strip()).expanduser()


def _bool_env(name: str, resolver: Callable[[str], str | None], default: bool) -> bool:
    raw = resolver(name)
    if raw is None or raw.strip() == "":
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def _positive_int_env(
    name: str, resolver: Callable[[str], str | None], default: int
) -> int:
    raw = resolver(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _non_negative_int_env(
    name: str, resolver: Callable[[str], str | None], default: int
) -> int:
    raw = resolver(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= 0 else default


def _headers_env(
    name: str,
    resolver: Callable[[str], str | None],
    default: Sequence[Tuple[str, str]],
) -> Sequence[Tuple[str, str]]:
    raw = resolver(name)
    if not raw:
        return tuple(default)

    headers: list[Tuple[str, str]] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" in item:
            prefix, alias = item.split("=", maxsplit=1)
            prefix = prefix.strip()
            alias = alias.strip()
            if prefix and alias:
                headers.append((prefix, alias))
        else:
            headers.append((item, item.lstrip("#") or item))

    return tuple(headers) if headers else tuple(default)
