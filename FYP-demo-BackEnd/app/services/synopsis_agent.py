import json
import logging
import os
from typing import Optional, Dict, Any, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from .. import schemas
from ..utils.read_data import load_synopsis_agent_prompt

logger = logging.getLogger(__name__)


class SynopsisAgent:
    """负责根据剧情列表生成剧情简介的 Agent"""

    def __init__(self) -> None:
        # 是否启用，可通过环境变量关闭
        self.enabled = os.getenv("PLOT_SYNOPSIS_ENABLED", "true").lower() == "true"
        self.model = os.getenv("PLOT_SYNOPSIS_MODEL") or os.getenv(
            "OPENAI_MODEL", "gpt-4o-mini"
        )

        self.llm: Optional[ChatOpenAI] = None

        if self.enabled:
            llm_config: Dict[str, Any] = {
                "model": self.model,
                "temperature": 0.7,
                "api_key": os.getenv("OPENAI_API_KEY"),
                "streaming": True,  # allow token streaming; still works for non-stream calls
            }
            base_url = os.getenv("OPENAI_BASE_URL")
            if base_url:
                llm_config["base_url"] = base_url

            self.llm = ChatOpenAI(**llm_config)

        logger.info(
            "SynopsisAgent initialized: enabled=%s, model=%s",
            self.enabled,
            self.model,
        )

    def get_system_prompt(self, word_limit: int = 80) -> str:
        """系统提示：约束剧情简介输出形态与长度"""
        template = load_synopsis_agent_prompt()
        # 模板中包含 {word_limit} 占位符
        try:
            return template.format(word_limit=word_limit)
        except KeyError:
            # 如果模板中没有占位符，直接返回模板（兼容旧格式）
            logger.warning(
                "Synopsis agent prompt template missing word_limit placeholder"
            )
            return template

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
        self, messages: List[Any], max_retries: int = 3
    ) -> Optional[Any]:
        """对 LLM 调用增加简单重试，避免偶发网络抖动直接失败"""
        if not self.enabled or self.llm is None:
            logger.error("SynopsisAgent is disabled or LLM is not initialized")
            return None

        llm = self.llm

        last_error: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                return await llm.ainvoke(messages)
            except Exception as e:  # noqa: BLE001
                last_error = e
                logger.error(
                    "Error generating synopsis (attempt %s/%s): %s",
                    attempt,
                    max_retries,
                    e,
                    exc_info=True,
                )
        logger.error("All retries failed in SynopsisAgent: %s", last_error)
        return None

    async def generate_synopsis(
        self,
        outline: schemas.PlotOutlineSchema,
        style: Optional[str] = None,
        word_limit: int = 80,
        language: Optional[str] = None,
    ) -> Optional[str]:
        """
        根据剧情列表生成剧情简介（对 LLM 输入进行了精简，提升速度）

        Args:
            outline: 当前生效的剧情列表（PlotOutlineSchema）
            style: 简介风格提示（例如：轻松、黑暗、搞笑、史诗冒险等）
            word_limit: 英文单词长度上限（默认 80）
            language: 语言偏好（例如 'zh' / 'en'），可为空表示由模型自行判断

        Returns:
            剧情简介文本，如果失败则返回 None
        """
        if not self.enabled:
            logger.info("SynopsisAgent is disabled")
            return None

        if not self.llm:
            logger.error("SynopsisAgent LLM is not initialized")
            return None

        try:
            # 1) 限制参与梗概生成的节点数量：节点太多时，只使用头尾若干节点
            nodes: List[schemas.PlotNodeSchema] = outline.nodes or []
            if len(nodes) > 7:
                nodes_to_use = nodes[:3] + nodes[-3:]
            else:
                nodes_to_use = nodes

            # 2) 精简每个节点：只保留 index/title/short summary
            nodes_payload: List[Dict[str, Any]] = []
            for node in nodes_to_use:
                short_summary = (node.summary or "").strip()
                if len(short_summary) > 120:
                    short_summary = short_summary[:117].rstrip() + "..."

                nodes_payload.append(
                    {
                        "index": node.index,
                        "title": node.title,
                        "summary": short_summary,
                    }
                )

            payload: Dict[str, Any] = {
                "plot_outline_nodes": nodes_payload,
                "style_hint": style,
                "word_limit": word_limit,
                "instruction": (
                    "Write a short synopsis for players based on the above plot outline. "
                    "Do not list all nodes one by one; compress them into a smooth, engaging description."
                    " IMPORTANT: The synopsis MUST be written in ENGLISH ONLY."
                ),
            }

            messages: List[Any] = [
                SystemMessage(content=self.get_system_prompt(word_limit=word_limit)),
                HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
            ]

            raw = await self._ainvoke_with_retry(messages)
            if raw is None:
                # 已记录详细日志，这里返回 None 让上层用更友好的错误消息处理
                return None

            text = self._extract_text_from_response(raw).strip()

            # 简单清理：去掉可能包裹的引号
            if (text.startswith('"') and text.endswith('"')) or (
                text.startswith("“") and text.endswith("”")
            ):
                text = text[1:-1].strip()

            if not text:
                logger.warning("Empty synopsis generated from SynopsisAgent")
                return None

            return text
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error generating synopsis: {e}", exc_info=True)
            return None

    async def generate_synopsis_stream(
        self,
        outline: schemas.PlotOutlineSchema,
        style: Optional[str] = None,
        word_limit: int = 80,
        language: Optional[str] = None,
    ):
        """
        流式生成剧情简介：逐 token 产出增量文本，同时返回最终完整结果。

        Yields:
            {"delta": "..."}                    增量文本
            {"event": "done", "text": "..."}    完整文本
            {"event": "error", "message": "..."} 出错时
        """
        if not self.enabled:
            yield {"event": "error", "message": "SynopsisAgent is disabled"}
            return
        if not self.llm:
            yield {"event": "error", "message": "SynopsisAgent LLM is not initialized"}
            return

        try:
            nodes: List[schemas.PlotNodeSchema] = outline.nodes or []
            if len(nodes) > 7:
                nodes_to_use = nodes[:3] + nodes[-3:]
            else:
                nodes_to_use = nodes

            nodes_payload: List[Dict[str, Any]] = []
            for node in nodes_to_use:
                short_summary = (node.summary or "").strip()
                if len(short_summary) > 120:
                    short_summary = short_summary[:117].rstrip() + "..."

                nodes_payload.append(
                    {
                        "index": node.index,
                        "title": node.title,
                        "summary": short_summary,
                    }
                )

            payload: Dict[str, Any] = {
                "plot_outline_nodes": nodes_payload,
                "style_hint": style,
                "word_limit": word_limit,
                "instruction": (
                    "Write a short synopsis for players based on the above plot outline. "
                    "Do not list all nodes one by one; compress them into a smooth, engaging description."
                    " IMPORTANT: The synopsis MUST be written in ENGLISH ONLY."
                ),
            }

            messages: List[Any] = [
                SystemMessage(content=self.get_system_prompt(word_limit=word_limit)),
                HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
            ]

            logger.info(
                f"Starting LLM stream for synopsis generation with {len(messages)} messages"
            )
            full_text_parts: List[str] = []

            # 检查LLM是否初始化
            if not self.llm:
                logger.error("LLM is not initialized for streaming")
                yield {"event": "error", "message": "LLM is not initialized"}
                return

            try:
                logger.info("Starting async LLM stream...")
                logger.info(
                    f"LLM config: model={self.model}, base_url={getattr(self.llm, 'base_url', 'default')}"
                )

                # 测试LLM是否可用
                if not hasattr(self.llm, "astream"):
                    logger.error("LLM does not support astream method")
                    yield {
                        "event": "error",
                        "message": "LLM does not support streaming",
                    }
                    return

                logger.info("Starting LLM astream iteration...")
                chunk_count = 0
                async for chunk in self.llm.astream(messages):
                    chunk_count += 1
                    logger.info(f"Received LLM chunk #{chunk_count}: {type(chunk)}")
                    try:
                        delta = self._extract_text_from_response(chunk)
                        logger.info(
                            f"Extracted delta from chunk #{chunk_count}: '{delta}' (length: {len(delta)})"
                        )
                        if delta:
                            full_text_parts.append(delta)
                            logger.info(
                                f"Yielding delta event for chunk #{chunk_count}"
                            )
                            yield {"delta": delta}
                            logger.info(
                                f"Delta event yielded successfully for chunk #{chunk_count}"
                            )
                        else:
                            logger.warning(
                                f"Empty delta extracted from chunk #{chunk_count}"
                            )
                    except Exception as e:
                        logger.error(
                            f"Error processing stream chunk #{chunk_count}: {e}",
                            exc_info=True,
                        )
                        yield {
                            "event": "error",
                            "message": f"Stream processing failed: {str(e)}",
                        }
                        return
                logger.info(
                    f"LLM stream iteration completed, processed {chunk_count} chunks"
                )
            except Exception as e:
                logger.error(f"LLM stream failed: {e}", exc_info=True)
                yield {"event": "error", "message": f"LLM stream failed: {str(e)}"}
                return

            logger.info(
                f"LLM stream completed, collected {len(full_text_parts)} chunks"
            )
            full_text = "".join(full_text_parts).strip()
            if (full_text.startswith('"') and full_text.endswith('"')) or (
                full_text.startswith("“") and full_text.endswith("”")
            ):
                full_text = full_text[1:-1].strip()

            if not full_text:
                logger.warning("Empty synopsis generated from stream")
                yield {"event": "error", "message": "Empty synopsis generated"}
                return

            logger.info(f"Synopsis generated successfully: {len(full_text)} characters")
            yield {"event": "done", "text": full_text}
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error streaming synopsis: {e}", exc_info=True)
            yield {"event": "error", "message": str(e)}


# 全局实例，方便直接调用
synopsis_agent = SynopsisAgent()


async def generate_plot_synopsis(
    outline: schemas.PlotOutlineSchema,
    style: Optional[str] = None,
    word_limit: int = 80,
    language: Optional[str] = None,
) -> Optional[str]:
    """
    便利函数：根据剧情列表生成剧情简介
    用法示例：
        synopsis = await generate_plot_synopsis(outline, style="轻松番剧风格")
    """
    return await synopsis_agent.generate_synopsis(
        outline=outline,
        style=style,
        word_limit=word_limit,
        language=language,
    )


async def generate_plot_synopsis_stream(
    outline: schemas.PlotOutlineSchema,
    style: Optional[str] = None,
    word_limit: int = 80,
    language: Optional[str] = None,
):
    """
    便利函数：流式生成剧情简介，直接复用全局 SynopsisAgent。
    """
    async for event in synopsis_agent.generate_synopsis_stream(
        outline=outline,
        style=style,
        word_limit=word_limit,
        language=language,
    ):
        yield event
