import json
import logging
import os
from typing import Optional, Dict, Any, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from .. import schemas
from ..utils.read_data import load_revision_agent_prompt

logger = logging.getLogger(__name__)


class RevisionAgent:
    """根据玩家反馈修改剧情列表与简介的 Agent"""

    def __init__(self) -> None:
        self.enabled = os.getenv("PLOT_REVISION_ENABLED", "true").lower() == "true"
        self.model = os.getenv("PLOT_REVISION_MODEL") or os.getenv(
            "OPENAI_MODEL", "gpt-4o-mini"
        )

        self.llm: Optional[ChatOpenAI] = None
        self.structured_llm = None

        if self.enabled:
            llm_config: Dict[str, Any] = {
                "model": self.model,
                "temperature": 0.7,
                "api_key": os.getenv("OPENAI_API_KEY"),
            }
            base_url = os.getenv("OPENAI_BASE_URL")
            if base_url:
                llm_config["base_url"] = base_url

            self.llm = ChatOpenAI(**llm_config)

            # 是否尝试使用 OpenAI 的结构化输出能力
            # 一些兼容 OpenAI 的第三方目前不支持 response_format，会返回 400
            use_structured = True
            if base_url and "api.deepseek.com" in base_url:
                use_structured = False

            if use_structured:
                try:
                    self.structured_llm = self.llm.with_structured_output(
                        schemas.RevisionOutput
                    )
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "Failed to enable structured output for RevisionAgent, "
                        "fallback to JSON parsing: %s",
                        e,
                    )
                    self.structured_llm = None

        logger.info(
            "RevisionAgent initialized: enabled=%s, model=%s, structured=%s",
            self.enabled,
            self.model,
            bool(self.structured_llm),
        )

    def get_system_prompt(self) -> str:
        """系统提示：根据玩家反馈调整剧情结构和简介"""
        return load_revision_agent_prompt()

    def _extract_text_from_response(self, response: Any) -> str:
        """从 LLM 响应中提取纯文本内容，兼容多种结果结构"""
        if response is None:
            return ""

        content = getattr(response, "content", response)
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            parts: List[str] = []
            for part in content:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict) and part.get("type") == "text":
                    parts.append(str(part.get("text", "")))
            return "".join(parts)

        return str(content)

    async def _ainvoke_with_retry(
        self, llm, messages: List[Any], max_retries: int = 3
    ) -> Optional[Any]:
        """对 LLM 调用增加简单重试，避免偶发网络抖动直接失败"""
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                return await llm.ainvoke(messages)
            except Exception as e:  # noqa: BLE001
                last_error = e
                logger.error(
                    "Error in RevisionAgent LLM call (attempt %s/%s): %s",
                    attempt,
                    max_retries,
                    e,
                    exc_info=True,
                )
        logger.error("All retries failed in RevisionAgent: %s", last_error)
        return None

    async def revise(
        self,
        original_outline: schemas.PlotOutlineSchema,
        original_synopsis: str | None,
        feedback_text: str,
        task_type: str,
    ) -> Optional[schemas.RevisionOutput]:
        """
        根据玩家反馈修改剧情与简介

        Args:
            original_outline: 原始剧情列表
            original_synopsis: 原始简介文本（可为空）
            feedback_text: 玩家反馈
            task_type: 'ModifyExisting' 或 'CreateNew'
        """
        if not self.enabled:
            logger.info("RevisionAgent is disabled")
            return None

        if not self.llm:
            logger.error("RevisionAgent LLM is not initialized")
            return None

        try:
            outline_payload = [node.dict() for node in original_outline.nodes]

            payload: Dict[str, Any] = {
                "original_outline_nodes": outline_payload,
                "original_synopsis": original_synopsis or "",
                "player_feedback": feedback_text,
                "task_type": task_type,
            }

            messages: List[Any] = [
                SystemMessage(content=self.get_system_prompt()),
                HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
            ]

            # 优先使用结构化输出
            if self.structured_llm is not None:
                result = await self._ainvoke_with_retry(self.structured_llm, messages)
                if result is None:
                    return None
                if isinstance(result, schemas.RevisionOutput):
                    return result
                if isinstance(result, dict):
                    return schemas.RevisionOutput(**result)
                logger.error(
                    "Unexpected revision result type (structured mode): %s",
                    type(result),
                )
                return None

            # 退化为通用 Chat 调用 + JSON 解析
            raw = await self._ainvoke_with_retry(self.llm, messages)
            if raw is None:
                return None

            text = self._extract_text_from_response(raw).strip()

            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                text = text[start : end + 1]

            data = json.loads(text)
            return schemas.RevisionOutput(**data)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error in RevisionAgent.revise: {e}", exc_info=True)
            return None


revision_agent = RevisionAgent()


async def run_revision(
    original_outline: schemas.PlotOutlineSchema,
    original_synopsis: str | None,
    feedback_text: str,
    task_type: str,
) -> Optional[schemas.RevisionOutput]:
    """便利函数：运行 RevisionAgent 完成一次剧情修改"""
    return await revision_agent.revise(
        original_outline=original_outline,
        original_synopsis=original_synopsis,
        feedback_text=feedback_text,
        task_type=task_type,
    )
