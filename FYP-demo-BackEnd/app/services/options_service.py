import os
import json
import logging
from typing import List, Optional, Dict
from pydantic import SecretStr
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from .. import schemas
from ..db import crud, models
from ..utils.read_data import load_options_prompt
from . import settings_service

logger = logging.getLogger(__name__)


class OptionsGenerationService:
    """对话选项生成服务"""

    def __init__(self):
        # 从环境变量读取配置
        self.enabled = os.getenv("SUGGEST_OPTIONS_ENABLED", "true").lower() == "true"
        self.history_limit = int(os.getenv("SUGGEST_OPTIONS_HISTORY_LIMIT", "5"))

        logger.info(
            f"OptionsGenerationService initialized: enabled={self.enabled}, "
            f"history_limit={self.history_limit}"
        )

    def _build_llm(self, db: Session):
        """根据数据库/环境配置构建 LLM 客户端。"""
        llm_config = settings_service.build_openai_client_config(
            db, model_key="SUGGEST_OPTIONS_MODEL"
        )
        api_key = llm_config.get("api_key")
        if not api_key:
            logger.warning("OPENAI_API_KEY 未配置，无法生成对话选项。")
            return None, None

        llm = ChatOpenAI(
            model=llm_config.get("model") or "gpt-4o-mini",
            temperature=0.7,
            api_key=SecretStr(api_key),
            base_url=llm_config.get("base_url"),
        )
        structured_llm = llm.with_structured_output(schemas.StructuredSuggestionsOutput)
        return llm, structured_llm

    def get_system_prompt(self) -> str:
        """Get system prompt for option generation"""
        return load_options_prompt()

    async def generate_suggestions(
        self, session_id: str, db: Session, assistant_message_id: int
    ) -> Optional[List[str]]:
        """
        为指定会话生成对话选项

        Args:
            session_id: 会话ID
            db: 数据库会话
            assistant_message_id: 助手消息ID（作为选项的关联消息）

        Returns:
            生成的选项列表，如果生成失败返回None
        """
        if not self.enabled:
            logger.info("Options generation is disabled")
            return None

        llm, structured_llm = self._build_llm(db)
        if llm is None or structured_llm is None:
            return None

        try:
            # 获取最近的对话历史
            recent_messages = self._get_recent_messages(session_id, db)

            if len(recent_messages) < 2:  # 至少需要一轮对话
                logger.info("Not enough messages for suggestion generation")
                return None

            # 构建提示词
            context = self._build_context(recent_messages)

            # 使用 JSON 格式构建用户消息
            context_data = {
                "conversation_history": context,
                "instruction": "Based on the above conversation history, generate suitable options for the player to choose from.",
            }

            # 生成选项
            messages = [
                SystemMessage(content=self.get_system_prompt()),
                HumanMessage(content=json.dumps(context_data, ensure_ascii=False)),
            ]

            result = await structured_llm.ainvoke(messages)
            # 类型安全地访问结果
            if isinstance(result, schemas.StructuredSuggestionsOutput):
                suggestions = result.chooses
            else:
                # 处理字典格式返回
                suggestions = (
                    result.get("chooses", []) if isinstance(result, dict) else []
                )

            # 限制选项数量
            if len(suggestions) > 5:
                suggestions = suggestions[:5]

            logger.info(
                f"Generated {len(suggestions)} suggestions for session {session_id}"
            )

            # 保存到数据库
            if suggestions:
                crud.create_conversation_suggestions(
                    db, assistant_message_id, suggestions
                )

            return suggestions

        except Exception as e:
            logger.error(
                f"Error generating suggestions for session {session_id}: {e}",
                exc_info=True,
            )
            return None

    def _get_recent_messages(
        self, session_id: str, db: Session
    ) -> List[models.ChatMessage]:
        """Get recent messages"""
        # Get all messages
        all_messages = crud.get_messages_by_session(db, session_id)

        if not all_messages:
            return []

        # Calculate recent messages by rounds
        # One round = user message + assistant response (may include tool calls)
        rounds = []
        current_round = []

        for message in all_messages:
            # 使用 getattr 来确保类型安全
            message_role = str(getattr(message, "role", ""))
            if message_role == "user":
                # New round begins
                if current_round:
                    rounds.append(current_round)
                current_round = [message]
            else:
                # Add to current round
                current_round.append(message)

        # Add the last round
        if current_round:
            rounds.append(current_round)

        # Get recent rounds
        recent_rounds = (
            rounds[-self.history_limit :]
            if len(rounds) > self.history_limit
            else rounds
        )

        # Flatten to message list
        recent_messages = []
        for round_messages in recent_rounds:
            recent_messages.extend(round_messages)

        return recent_messages

    def _build_context(
        self, messages: List[models.ChatMessage]
    ) -> List[Dict[str, str]]:
        """Build context for option generation"""
        context_messages = []

        for message in messages:
            # 使用 getattr 来确保类型安全
            message_role = str(getattr(message, "role", ""))
            message_content = getattr(message, "content", None)

            role_display = {
                "user": "player",
                "assistant": "DM",
                "system": "system",
                "tool": "tool_result",
            }.get(message_role, message_role)

            if message_content:
                content = str(message_content).strip()
                if content:
                    context_messages.append({"role": role_display, "message": content})

        return context_messages


# 全局实例
options_service = OptionsGenerationService()


async def generate_conversation_options(
    session_id: str, db: Session, assistant_message_id: int
) -> Optional[List[str]]:
    """
    便利函数：生成对话选项

    Args:
        session_id: 会话ID
        db: 数据库会话
        assistant_message_id: 助手消息ID

    Returns:
        生成的选项列表
    """
    return await options_service.generate_suggestions(
        session_id, db, assistant_message_id
    )
