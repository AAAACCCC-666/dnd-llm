"""
LangChain 服务 - 简化重构版本

Linus原则：
- 删除所有配置复杂性
- 一个函数做一件事，做好
- 直接操作，无适配器地狱
"""

import logging
from typing import Any, AsyncGenerator, Dict

from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from sqlalchemy.orm import Session

from . import settings_service
from .langchain_tools.tool_executor import langchain_tool_executor
from .message_builder import build_messages_direct
from ..utils.read_data import load_system_prompt

logger = logging.getLogger(__name__)


async def get_langchain_stream(
    session_id: str,
    db: Session,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    简化的 LangChain 流式处理

    删除所有配置复杂性，直接使用数据库构建消息
    """

    try:
        # 1. 直接构建消息 - 无中间转换
        system_prompt = load_system_prompt()
        messages = build_messages_direct(session_id, db, system_prompt)

        # 2. 配置 LLM - 简化配置
        llm_config = settings_service.build_openai_client_config(db)
        api_key = llm_config.get("api_key")
        if not api_key:
            yield {
                "event": "stream_end",
                "reason": "config_error",
                "error": "OPENAI_API_KEY 未配置，无法调用模型。",
            }
            return

        llm = ChatOpenAI(
            model=llm_config.get("model") or "gpt-4o-mini",
            temperature=0.7,
            streaming=True,
            api_key=SecretStr(api_key),
            base_url=llm_config.get("base_url"),
        )

        # 3. 绑定工具
        tools = langchain_tool_executor.get_available_tools()
        if tools:
            llm = llm.bind_tools(tools)

        # 4. 流式处理循环 - 简化逻辑
        max_iterations = 5

        for _ in range(max_iterations):
            try:
                response_stream = llm.astream(messages)

                gathered_chunk = None
                full_content = ""

                async for chunk in response_stream:
                    # 逐步输出文本增量，保持 SSE 行为与原实现兼容
                    if hasattr(chunk, "content") and chunk.content:
                        delta_text = ""
                        if isinstance(chunk.content, str):
                            delta_text = chunk.content
                        elif isinstance(chunk.content, list):
                            # LangChain 将文本分片存在列表中
                            for part in chunk.content:
                                if isinstance(part, str):
                                    delta_text += part
                                elif (
                                    isinstance(part, dict)
                                    and part.get("type") == "text"
                                ):
                                    delta_text += part.get("text", "")
                        if delta_text:
                            full_content += delta_text
                            yield {"delta": delta_text}

                    # 累积 AIMessageChunk，遵循 LangChain 官方推荐做法
                    if gathered_chunk is None:
                        gathered_chunk = chunk
                    else:
                        gathered_chunk = gathered_chunk + chunk

                if gathered_chunk is None:
                    logger.warning("Received empty stream chunk from LLM")
                    yield {"event": "stream_end", "reason": "empty"}
                    return

                # 使用 LangChain 聚合结果获取完整工具调用信息
                tool_calls = getattr(gathered_chunk, "tool_calls", []) or []

                # 处理工具调用或保存最终消息
                if tool_calls:
                    from langchain_core.messages import AIMessage, ToolMessage

                    messages.append(
                        AIMessage(content=full_content, tool_calls=tool_calls)
                    )

                    async for tool_event in langchain_tool_executor.handle_tool_calls(
                        tool_calls
                    ):
                        yield tool_event

                        if tool_event.get("type") == "tool_result":
                            messages.append(
                                ToolMessage(
                                    content=tool_event["result"],
                                    tool_call_id=tool_event["id"],
                                    name=tool_event["name"],
                                )
                            )
                    continue
                else:
                    if full_content:
                        from langchain_core.messages import AIMessage

                        messages.append(AIMessage(content=full_content))

                    yield {"event": "stream_end", "reason": "stop"}
                    return

            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield {"event": "stream_end", "reason": "error", "error": str(e)}
                return

        yield {"event": "stream_end", "reason": "max_iterations"}

    except Exception as e:
        logger.error(f"LangChain stream error: {e}")
        yield {"event": "stream_end", "reason": "error", "error": str(e)}
