"""配置存取与优先级控制：数据库优先，其次环境变量。"""

from __future__ import annotations

import os
from typing import Dict, Iterable, Mapping, Optional
from sqlalchemy.orm import Session

from app.db import crud
from app.services.rag.rag_config import load_rag_config, RagConfig

CONFIG_KEYS = [
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "RAG_EMBEDDING_API_KEY",
    "RAG_EMBEDDING_BASE_URL",
    "RAG_EMBEDDING_MODEL",
    "SUGGEST_OPTIONS_MODEL",
]


def _clean_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed if trimmed else None


def seed_settings_from_env(db: Session) -> None:
    """
    首次启动时从环境变量写入数据库；若未配置则写入空值。
    仅在不存在对应记录时执行，避免覆盖已有用户配置。
    """
    for key in CONFIG_KEYS:
        if crud.get_config_entry(db, key):
            continue
        env_value = _clean_value(os.getenv(key))
        crud.upsert_config_entry(db, key, env_value)


def get_setting(db: Session, key: str) -> Optional[str]:
    """
    获取配置项：若数据库存在记录（即便为None）则返回数据库值；否则回退环境变量。
    """
    entry = crud.get_config_entry(db, key)
    if entry is not None:
        return _clean_value(entry.value)
    return _clean_value(os.getenv(key))


def get_settings_map(db: Session, keys: Iterable[str]) -> Dict[str, Optional[str]]:
    """批量获取配置项。"""
    return {key: get_setting(db, key) for key in keys}


def update_settings(db: Session, values: Mapping[str, Optional[str]]):
    """
    批量更新配置项；缺省的键不会被写入。
    返回更新后的全部配置列表。
    """
    for key, value in values.items():
        if key not in CONFIG_KEYS:
            continue
        crud.upsert_config_entry(db, key, _clean_value(value))
    return crud.list_config_entries(db)


def build_openai_client_config(
    db: Session, model_key: str = "OPENAI_MODEL", default_model: str = "gpt-4o-mini"
) -> Dict[str, Optional[str]]:
    """
    组装 OpenAI 客户端配置，确保数据库优先。
    """
    api_key = get_setting(db, "OPENAI_API_KEY")
    base_url = get_setting(db, "OPENAI_BASE_URL")
    model = (
        get_setting(db, model_key) or get_setting(db, "OPENAI_MODEL") or default_model
    )

    config: Dict[str, Optional[str]] = {"api_key": api_key, "model": model}
    if base_url:
        config["base_url"] = base_url
    return config


def build_rag_config(db: Session) -> RagConfig:
    """
    基于数据库/环境配置生成 RAG 配置。
    使用 RagConfig 现有的解析逻辑，通过自定义 resolver 注入优先级规则。
    """

    def resolver(name: str) -> Optional[str]:
        # 仅对目标键应用“数据库优先”规则；其他键仍支持从环境获取。
        if name in CONFIG_KEYS:
            entry = crud.get_config_entry(db, name)
            if entry is not None:
                return _clean_value(entry.value)
        return _clean_value(os.getenv(name))

    return load_rag_config(value_resolver=resolver)
