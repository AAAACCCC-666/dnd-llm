"""
消息构建服务 - 简化重构版

Linus 原则：
- 数据库是真理的唯一来源
- 消除所有特殊情况和重复逻辑
- 直接操作，无中间转换
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..db import crud, models
from sqlalchemy.orm import Session
from .rag.retriever import build_rag_context
from ..utils.character_utils import character_to_dict

# LangChain 消息类型导入
from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)
from langchain_core.messages.tool import ToolCall

logger = logging.getLogger(__name__)


def build_messages_direct(
    session_id: str, db: Session, system_prompt: str
) -> List[BaseMessage]:
    """
    直接从数据库构建 LangChain 消息 - 无中间转换

    这是唯一的消息构建入口点
    """
    messages: List[BaseMessage] = [SystemMessage(content=system_prompt)]

    # 直接查询数据行 - 使用简化后的 CRUD 函数
    db_messages = crud.get_messages_by_session(db, session_id)

    for db_msg in db_messages:
        langchain_msg = _convert_db_message_direct(db_msg, session_id, db)
        if langchain_msg:
            messages.append(langchain_msg)

    return messages


def _convert_db_message_direct(
    db_msg: models.ChatMessage, session_id: str, db: Session
) -> Optional[BaseMessage]:
    """直接转换数据库消息到 LangChain 格式，无中间格式"""

    # 安全获取属性值
    role = getattr(db_msg, "role", None)
    content = getattr(db_msg, "content", None) or ""
    name = getattr(db_msg, "name", None)
    tool_call_id = getattr(db_msg, "tool_call_id", None)
    tool_arguments = getattr(db_msg, "tool_arguments", None)

    if role == "user":
        # 动态构建用户上下文
        user_content = _build_user_context_on_demand(db_msg, session_id, db)
        return HumanMessage(content=user_content)

    elif role == "assistant":
        if tool_call_id and name and tool_arguments:
            # 助手工具调用消息 - 使用 LangChain 格式
            # 确保工具参数是字典格式
            if isinstance(tool_arguments, str):
                try:
                    args_dict = json.loads(tool_arguments)
                except json.JSONDecodeError:
                    args_dict = {}
            else:
                args_dict = tool_arguments or {}

            # 创建 LangChain 原生 ToolCall
            tool_call = ToolCall(name=name, args=args_dict, id=tool_call_id)
            return AIMessage(content=content or "", tool_calls=[tool_call])
        else:
            # 普通助手回复
            return AIMessage(content=content or "")

    elif role == "tool":
        # 工具执行结果
        return ToolMessage(
            content=content,
            tool_call_id=tool_call_id or "",
            name=name or "",
        )

    return None


def _build_user_context_on_demand(
    db_msg: models.ChatMessage, session_id: str, db: Session
) -> str:
    """动态构建用户消息上下文"""

    # 获取所有用户消息并找到最新的
    all_messages = crud.get_messages_by_session(db, session_id)
    user_messages = [
        msg for msg in all_messages if getattr(msg, "role", None) == "user"
    ]

    is_latest = False
    if user_messages:
        # 安全获取创建时间并找到最新消息
        latest_user_msg = max(
            user_messages, key=lambda m: getattr(m, "created_at", datetime.min)
        )
        is_latest = getattr(db_msg, "id", None) == getattr(latest_user_msg, "id", None)

    if is_latest:
        # 最新用户消息，添加完整上下文
        characters = crud.get_characters_by_session_id(db, session_id)
        player_char = next(
            (c for c in characters if getattr(c, "is_player", False)), None
        )
        npc_chars = [c for c in characters if not getattr(c, "is_player", False)]

        rag_context = build_rag_context(getattr(db_msg, "content", ""))

        # 尝试加载当前故事及其激活的剧情列表（用于驱动 DM 按剧情节点推进）
        active_story_meta: Optional[Dict[str, Any]] = None
        active_story_outline: Optional[List[Dict[str, Any]]] = None
        try:
            # 简单策略：使用最新创建的 Story 作为当前故事
            active_story = (
                db.query(models.Story).order_by(models.Story.created_at.desc()).first()
            )
            if active_story is not None:
                active_story_meta = {
                    "id": int(getattr(active_story, "id", 0)),
                    "title": getattr(active_story, "title", None),
                    "theme": getattr(active_story, "theme", None),
                }
                outline_record = crud.get_active_plot_outline(
                    db, story_id=int(getattr(active_story, "id", 0))
                )
                if outline_record is not None:
                    nodes_raw = getattr(outline_record, "nodes", []) or []
                    if isinstance(nodes_raw, list):
                        # 直接把 PlotNode 的字典列表给到 LLM
                        active_story_outline = nodes_raw
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error loading active story outline for context: {e}")

        context = {
            "DND_related_rules": rag_context["results"],
            "player_character": (
                character_to_dict(player_char, db) if player_char else None
            ),
            "npc_character": [character_to_dict(c, db) for c in npc_chars],
            "story_meta": active_story_meta,
            "active_story_outline": active_story_outline,
            "player_choose": getattr(db_msg, "content", ""),
        }
    else:
        # 历史消息，简化上下文
        context = {"player_choose": getattr(db_msg, "content", "")}

    return json.dumps(context, ensure_ascii=False)
