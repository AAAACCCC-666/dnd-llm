"""
LangChain 工具模块
提供基于 LangChain 的 D&D 工具系统
"""

from .tool_registry import langchain_tool_registry
from .tool_executor import langchain_tool_executor
from .tools import register_all_tools

# 确保工具在导入时自动注册
register_all_tools()

__all__ = [
    "langchain_tool_registry",
    "langchain_tool_executor",
    "register_all_tools",
]
