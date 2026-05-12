from typing import Any, Optional
from abc import ABC, abstractmethod
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from ...db.database import SessionLocal
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class ToolResult(BaseModel):
    """标准化的工具返回结果格式"""

    success: bool = Field(description="工具执行是否成功")
    message: str = Field(description="执行结果的描述信息")
    data: Optional[Any] = Field(default=None, description="额外的返回数据")
    error_code: Optional[str] = Field(default=None, description="错误代码（如果有）")


class BaseDnDTool(BaseTool, ABC):
    """
    D&D 工具基类，提供统一的接口标准和错误处理
    所有 D&D 工具都应该继承此类
    """

    def _run(self, *args, **kwargs) -> str:
        """
        同步执行工具的入口点
        处理数据库会话管理和错误处理
        """
        db = SessionLocal()
        try:
            result = self._execute_tool(db, *args, **kwargs)

            # 统一返回格式处理
            if isinstance(result, ToolResult):
                return result.message
            elif isinstance(result, str):
                return result
            else:
                return str(result)

        except Exception as e:
            logger.error(f"Error executing tool {self.name}: {e}", exc_info=True)
            return self._format_error(e)
        finally:
            db.close()

    async def _arun(self, *args, **kwargs) -> str:
        """异步执行工具（暂时使用同步实现）"""
        return self._run(*args, **kwargs)

    @abstractmethod
    def _execute_tool(self, db: Session, *args, **kwargs) -> ToolResult | str:
        """
        子类需要实现的具体工具逻辑

        Args:
            db: 数据库会话
            *args, **kwargs: 工具参数

        Returns:
            ToolResult 或 str: 执行结果
        """
        pass

    def _format_error(self, error: Exception) -> str:
        """格式化错误信息"""
        error_message = str(error)
        if "not found" in error_message.lower():
            return f"Error: {error_message}"
        elif "invalid" in error_message.lower():
            return f"Error: {error_message}"
        else:
            return f"Internal error occurred: {error_message}"

    def _validate_character_exists(self, db: Session, character_id: str) -> bool:
        """验证角色是否存在"""
        from ...db import crud

        character = crud.get_character_by_id(db=db, character_id=character_id)
        return character is not None

    def _get_character_name(self, db: Session, character_id: str) -> str:
        """获取角色名称"""
        from ...db import crud

        character = crud.get_character_by_id(db=db, character_id=character_id)
        if character and hasattr(character, "name"):
            name = getattr(character, "name", None)
            return str(name) if name is not None else "Unknown"
        return "Unknown"


class ToolValidationError(Exception):
    """工具参数验证错误"""

    pass


class ToolExecutionError(Exception):
    """工具执行错误"""

    pass
