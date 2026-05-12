import logging
from typing import Dict, Any, AsyncGenerator, List, Optional
from langchain_core.tools import BaseTool

from .tool_registry import langchain_tool_registry

logger = logging.getLogger(__name__)


class LangChainToolExecutor:
    """
    LangChain 工具执行器
    替换原有的 ToolHandler，使用 LangChain 工具系统
    """

    def __init__(self):
        self.tool_registry = langchain_tool_registry
        self.tool_registry.initialize()

    async def handle_tool_calls(
        self,
        tool_calls: List[Any],
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理 LangChain 原生工具调用

        Args:
            tool_calls: LangChain ToolCall 对象列表
            messages: 消息列表，用于追加工具响应

        Yields:
            工具执行事件 (start, result, error)
        """
        if not tool_calls:
            return

        for tool_call in tool_calls:
            # 处理 LangChain 原生 ToolCall 对象
            if (
                hasattr(tool_call, "name")
                and hasattr(tool_call, "args")
                and hasattr(tool_call, "id")
            ):
                function_name = tool_call.name
                tool_call_id = tool_call.id
                arguments = tool_call.args  # LangChain 已经是字典格式
            else:
                # 处理字典格式的工具调用
                function_name = None
                tool_call_id = None
                arguments = None

                if isinstance(tool_call, dict):
                    function_name = tool_call.get("name")
                    tool_call_id = tool_call.get("id")
                    arguments = tool_call.get("args", {})

                    # 修复：如果参数为空，但对象中包含其他参数字段，尝试提取
                    if (not arguments or arguments == {}) and "args" in tool_call:
                        # 检查是否有其他可能包含参数的字段
                        potential_args = tool_call.get("args", {})
                        if (
                            potential_args
                            and isinstance(potential_args, dict)
                            and len(potential_args) > 0
                        ):
                            arguments = potential_args
                            logger.info(
                                f"Recovered arguments from tool_call args field for '{function_name}': {arguments}"
                            )
            if not function_name or not tool_call_id:
                logger.error(
                    f"Invalid tool call object: missing name='{function_name}' or id='{tool_call_id}', full_object={tool_call}"
                )
                continue

            # 验证参数完整性
            if not arguments or arguments == {}:
                logger.error(
                    f"Invalid tool call arguments: arguments is empty for tool '{function_name}' (ID: {tool_call_id}), full_object={tool_call}"
                )
                continue

            # 获取工具实例
            tool: Optional[BaseTool] = self.tool_registry.get_tool(function_name)

            if not tool:
                logger.warning(
                    f"Tool '{function_name}' (ID: {tool_call_id}) not found."
                )
                error_message = f"Error: Tool '{function_name}' not found."

                yield {
                    "type": "tool_error",
                    "name": function_name,
                    "id": tool_call_id,
                    "error": error_message,
                }

                tool_response_content = error_message
            else:
                try:
                    logger.info(
                        f"Executing tool '{function_name}' (ID: {tool_call_id}) with arguments: {arguments}"
                    )

                    # 发送工具开始事件
                    yield {
                        "type": "tool_start",
                        "name": function_name,
                        "id": tool_call_id,
                        "args": arguments,
                    }

                    # 执行工具
                    try:
                        # 调用 LangChain 工具
                        result = await tool.ainvoke(arguments)
                        tool_response_content = str(result)

                        # 特殊处理掷骰子工具的返回格式，保持兼容性
                        if (
                            function_name == "roll_dice"
                            and "roll" not in tool_response_content.lower()
                        ):
                            # 如果返回的是单个数字，保持原有格式
                            try:
                                single_result = int(tool_response_content)
                                tool_response_content = str(single_result)
                            except ValueError:
                                pass

                        logger.info(
                            f"Tool '{function_name}' (ID: {tool_call_id}) executed. Result: {tool_response_content}"
                        )

                        yield {
                            "type": "tool_result",
                            "name": function_name,
                            "id": tool_call_id,
                            "result": tool_response_content,
                        }

                    except Exception as e:
                        error_message = (
                            f"Error executing tool {function_name}: {str(e)}"
                        )
                        logger.error(
                            f"Error executing tool '{function_name}' (ID: {tool_call_id}): {e}",
                            exc_info=True,
                        )

                        yield {
                            "type": "tool_error",
                            "name": function_name,
                            "id": tool_call_id,
                            "error": str(e),
                        }

                        tool_response_content = error_message

                except Exception as e:
                    # 捕获工具执行过程中的所有其他异常
                    error_message = f"Unexpected error in tool execution: {str(e)}"
                    logger.error(
                        f"Unexpected error in tool '{function_name}' (ID: {tool_call_id}): {e}",
                        exc_info=True,
                    )

                    yield {
                        "type": "tool_error",
                        "name": function_name,
                        "id": tool_call_id,
                        "error": str(e),
                    }

                    tool_response_content = error_message

            # 追加工具响应到消息列表，保持与原有格式的兼容性
            if messages is not None:
                messages.append(
                    {
                        "tool_call_id": tool_call_id,
                        "role": "tool",
                        "name": function_name,
                        "content": tool_response_content,
                    }
                )

    def get_available_tools(self) -> List[BaseTool]:
        """获取所有可用的工具"""
        return self.tool_registry.get_all_tools()

    def get_tool_schemas(self) -> List[BaseTool]:
        """
        获取所有工具的 LangChain schema
        用于 LangChain 工具绑定
        """
        tools = self.get_available_tools()
        # 直接返回 LangChain 工具，让 LangChain 自己处理 schema
        return tools


# 全局工具执行器实例
langchain_tool_executor = LangChainToolExecutor()
