from typing import List, Dict
from langchain_core.tools import BaseTool
from ...db import database, crud
from sqlalchemy.orm import Session


class LangChainToolRegistry:
    """
    LangChain 工具注册系统
    负责管理和注册所有 D&D 工具，支持工具发现和加载机制
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._initialized = False

    def initialize(self):
        """初始化工具注册表，从数据库加载 D&D 静态数据"""
        if self._initialized:
            return

        # 获取 D&D 静态数据用于工具配置
        db: Session = database.SessionLocal()
        try:
            dnd_data = crud.get_all_dnd_static_data(db)
            self._races = dnd_data.get("races", {})
            self._classes = dnd_data.get("classes", {})
        finally:
            db.close()

        self._initialized = True

    def register_tool(self, tool: BaseTool) -> None:
        """注册一个 LangChain 工具"""
        if not self._initialized:
            self.initialize()

        # 避免重复注册
        if tool.name in self._tools:
            return

        self._tools[tool.name] = tool
        print(f"LangChain tool '{tool.name}' registered.")

    def get_tool(self, name: str) -> BaseTool | None:
        """获取指定名称的工具"""
        return self._tools.get(name)

    def get_all_tools(self) -> List[BaseTool]:
        """获取所有注册的工具列表"""
        return list(self._tools.values())

    def get_tool_names(self) -> List[str]:
        """获取所有工具名称"""
        return list(self._tools.keys())

    @property
    def races(self) -> Dict[str, str]:
        """获取种族数据"""
        if not self._initialized:
            self.initialize()
        return self._races

    @property
    def classes(self) -> Dict[str, str]:
        """获取职业数据"""
        if not self._initialized:
            self.initialize()
        return self._classes


# 全局工具注册表实例
langchain_tool_registry = LangChainToolRegistry()
