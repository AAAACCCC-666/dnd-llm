import json
import logging
import os
from typing import Optional, Dict, Any, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from .. import schemas
from ..utils.read_data import load_outline_planner_agent_prompt

logger = logging.getLogger(__name__)


class OutlinePlannerAgent:
    """负责生成完整剧情列表的 Agent"""

    def __init__(self) -> None:
        # 是否启用，可通过环境变量关闭
        self.enabled = os.getenv("PLOT_OUTLINE_ENABLED", "true").lower() == "true"
        self.model = os.getenv("PLOT_OUTLINE_MODEL") or os.getenv(
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
                        schemas.PlotOutlineSchema
                    )
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "Failed to enable structured output for OutlinePlannerAgent; "
                        "outline generation will be unavailable: %s",
                        e,
                    )
                    self.structured_llm = None

        logger.info(
            "OutlinePlannerAgent initialized: enabled=%s, model=%s, structured=%s",
            self.enabled,
            self.model,
            bool(self.structured_llm),
        )

    def get_system_prompt(self) -> str:
        """生成系统提示，约束剧情列表输出形态"""
        return load_outline_planner_agent_prompt()

    async def generate_outline(
        self,
        theme: str = "dnd world",
        min_nodes: int = 4,
        style: Optional[str] = None,
        player_character: Optional[Dict[str, Any]] = None,
    ) -> Optional[schemas.PlotOutlineSchema]:
        """
        生成剧情列表

        Args:
            theme: Story theme / Worldview / Brief setting
            min_nodes: Minimum number of plot nodes required
            style: Story style (such as "light adventure", "dark Cthulhu", etc.), optional
            player_character: Optional serialized player character info
        """
        if not self.enabled:
            logger.info("Outline planner is disabled")
            return None

        if not self.llm:
            logger.error("Outline planner LLM is not initialized")
            return None

        if self.structured_llm is None:
            logger.error(
                "Structured output client is unavailable; outline generation cannot proceed without it."
            )
            return None

        try:
            payload: Dict[str, Any] = {
                "theme": theme or "dnd world",
                "min_nodes": max(int(min_nodes), 1),
                "style": style,
                "player_character": player_character,
            }

            messages: List[Any] = [
                SystemMessage(content=self.get_system_prompt()),
                HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
            ]

            result = await self.structured_llm.ainvoke(messages)

            # LangChain 结构化输出优先返回 Pydantic 模型
            if isinstance(result, schemas.PlotOutlineSchema):
                nodes_count = len(result.nodes)
                if nodes_count < min_nodes:
                    logger.warning(
                        "Generated outline has fewer nodes (%s) than requested (%s)",
                        nodes_count,
                        min_nodes,
                    )
                return result

            # 兼容字典格式返回
            if isinstance(result, dict):
                outline = schemas.PlotOutlineSchema(**result)
                nodes_count = len(outline.nodes)
                if nodes_count < min_nodes:
                    logger.warning(
                        "Generated outline (dict) has fewer nodes (%s) than requested (%s)",
                        nodes_count,
                        min_nodes,
                    )
                return outline

            logger.error(
                "Unexpected outline planner result type (structured mode): %s",
                type(result),
            )
            return None
        except Exception as e:
            logger.error(f"Error generating plot outline: {e}", exc_info=True)
            return None


# 全局实例，方便直接调用
outline_planner_agent = OutlinePlannerAgent()


async def generate_plot_outline(
    theme: str = "dnd world",
    min_nodes: int = 4,
    style: Optional[str] = None,
    player_character: Optional[Dict[str, Any]] = None,
) -> Optional[schemas.PlotOutlineSchema]:
    """
    便利函数：生成剧情列表
    使用示例：
        outline = await generate_plot_outline("现代都市打工人穿越到异世界", min_nodes=6)
    """
    return await outline_planner_agent.generate_outline(
        theme=theme,
        min_nodes=min_nodes,
        style=style,
        player_character=player_character,
    )
