import random
import asyncio
from typing import List, Type, Optional, Union, Any, Dict
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .tool_base import BaseDnDTool, ToolValidationError
from .tool_registry import langchain_tool_registry
from ...db import crud
from ... import schemas
from ...services.synopsis_agent import generate_plot_synopsis


class RollDiceInput(BaseModel):
    """Input parameters for dice rolling tool"""

    sides: int = Field(
        description="Number of sides on the dice (e.g., 6 for D6, 20 for D20). Must be at least 1.",
        ge=1,
    )
    num_dice: int = Field(
        default=1, description="Number of dice to roll. Defaults to 1.", ge=1
    )


class RollDiceTool(BaseDnDTool):
    """Dice rolling tool - Simulate rolling one or more dice with specified number of sides and return results"""

    name: str = "roll_dice"
    description: str = (
        "MUST IMMEDIATELY roll dice for D&D game mechanics - NEVER manually generate dice results. "
        "MANDATORY usage for D&D rules: attack rolls, damage rolls, skill checks, saving throws, initiative rolls, "
        "ability checks, and other D&D mechanical dice requirements. "
        "ABSOLUTELY FORBIDDEN to hardcode or manually calculate dice results for D&D mechanics. "
        "Call this tool when D&D rules require dice rolls, not for general narrative randomization."
    )
    args_schema: Union[Type[BaseModel], Dict[str, Any], None] = RollDiceInput

    def _execute_tool(self, db: Session, sides: int, num_dice: int = 1) -> str:
        """Execute dice rolling logic"""
        # db parameter is required by interface but not used for dice rolling
        _ = db  # Explicitly mark as intentionally unused
        if sides < 1 or num_dice < 1:
            raise ToolValidationError(
                "Number of sides and dice count must be greater than 0"
            )

        results = [random.randint(1, sides) for _ in range(num_dice)]

        # 保持与原有实现的兼容性：单个骰子返回数值，多个骰子返回列表格式
        if num_dice == 1:
            return str(results[0])
        else:
            return f"Rolling {num_dice} D{sides}: {results}"


# 定义常量，保持与原有实现一致
ALLOWED_INT_ATTRIBUTES = [
    "gold",
    "experience",
    "level",
    "armor",
    "speed",
    "health",
    "temp_health",
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
]

ALLOWED_BOOL_ATTRIBUTES = [
    "strength_proficiency",
    "dexterity_proficiency",
    "constitution_proficiency",
    "intelligence_proficiency",
    "wisdom_proficiency",
    "charisma_proficiency",
    "is_player",
    "is_male",
]


class ModifyCharacterIntegerAttributeInput(BaseModel):
    """Input parameters for character integer attribute modification tool"""

    character_id: str = Field(description="Unique ID of the character")
    attribute: str = Field(
        description="Name of the attribute to modify, must be one of the allowed integer attributes"
    )
    value: int = Field(description="The new integer value to set")


class ModifyCharacterIntegerAttributeTool(BaseDnDTool):
    """Character integer attribute modification tool"""

    name: str = "modify_character_integer_attribute"
    description: str = (
        "MUST IMMEDIATELY modify character integer attributes when ANY numeric value changes - NEVER manually track values. "
        "MANDATORY usage for: health damage/healing, gold changes, experience gain, ability score changes, level changes, "
        "armor class changes, speed changes, temporary health, and ANY numeric character modification. "
        "ABSOLUTELY FORBIDDEN to describe attribute changes without calling this tool. "
        "Call this tool the INSTANT any numeric character value is affected by story events."
    )
    args_schema: Union[Type[BaseModel], Dict[str, Any], None] = (
        ModifyCharacterIntegerAttributeInput
    )

    def _execute_tool(
        self, db: Session, character_id: str, attribute: str, value: int
    ) -> str:
        """Execute character integer attribute modification logic"""
        if attribute not in ALLOWED_INT_ATTRIBUTES:
            raise ToolValidationError(
                f"Modification of attribute '{attribute}' is not allowed. Only allowed: {', '.join(ALLOWED_INT_ATTRIBUTES)}"
            )

        if not self._validate_character_exists(db, character_id):
            raise ToolValidationError(f"Character ID '{character_id}' does not exist")

        updated_character = crud.update_character_integer_attribute(
            db=db, character_id=character_id, attribute=attribute, value=value
        )

        if updated_character:
            return f"Success: Character {updated_character.name} (ID: {character_id}) attribute '{attribute}' has been updated to {value}."
        else:
            raise ToolValidationError(
                f"Failed to update attribute '{attribute}' for character (ID: {character_id}). Please check if the attribute name is valid."
            )


class ModifyCharacterBoolAttributeInput(BaseModel):
    """Input parameters for character boolean attribute modification tool"""

    character_id: str = Field(description="Unique ID of the character")
    attribute: str = Field(
        description="Name of the attribute to modify, must be one of the allowed boolean attributes"
    )
    value: bool = Field(description="The new boolean value to set")


class ModifyCharacterBoolAttributeTool(BaseDnDTool):
    """Character boolean attribute modification tool"""

    name: str = "modify_character_bool_attribute"
    description: str = (
        "MUST IMMEDIATELY modify character boolean attributes when ANY proficiency or flag changes - NEVER manually track status. "
        "MANDATORY usage for: skill proficiencies, saving throw proficiencies, player status, gender, and ANY boolean character trait. "
        "ABSOLUTELY FORBIDDEN to describe proficiency or status changes without calling this tool. "
        "Call this tool the INSTANT any boolean character attribute is affected by story events."
    )
    args_schema: Union[Type[BaseModel], Dict[str, Any], None] = (
        ModifyCharacterBoolAttributeInput
    )

    def _execute_tool(
        self, db: Session, character_id: str, attribute: str, value: bool
    ) -> str:
        """Execute character boolean attribute modification logic"""
        if attribute not in ALLOWED_BOOL_ATTRIBUTES:
            # Fixed error in original code: should display ALLOWED_BOOL_ATTRIBUTES instead of ALLOWED_INT_ATTRIBUTES
            raise ToolValidationError(
                f"Modification of attribute '{attribute}' is not allowed. Only allowed: {', '.join(ALLOWED_BOOL_ATTRIBUTES)}"
            )

        if not self._validate_character_exists(db, character_id):
            raise ToolValidationError(f"Character ID '{character_id}' does not exist")

        updated_character = crud.update_character_boolean_attribute(
            db=db, character_id=character_id, attribute=attribute, value=value
        )

        if updated_character:
            return f"Success: Character {updated_character.name} (ID: {character_id}) attribute '{attribute}' has been updated to {value}."
        else:
            raise ToolValidationError(
                f"Failed to update attribute '{attribute}' for character (ID: {character_id}). Please check if the attribute name is valid."
            )


class ModifyCharacterRaceAndClassInput(BaseModel):
    """Input parameters for character race and class modification tool"""

    character_id: str = Field(description="Unique ID of the character")
    race_id: int = Field(description="New race ID")
    class_id: int = Field(description="New class ID")


class ModifyCharacterRaceAndClassTool(BaseDnDTool):
    """Character race and class modification tool"""

    name: str = "modify_character_race_and_class"
    description: str = (
        "MUST IMMEDIATELY modify character race and class when ANY race/class changes occur - NEVER manually track race/class. "
        "MANDATORY usage for: character transformations, multiclassing, racial mutations, class changes, reincarnation effects. "
        "ABSOLUTELY FORBIDDEN to describe race or class changes without calling this tool. "
        "Call this tool the INSTANT any race or class modification is affected by story events."
    )
    args_schema: Union[Type[BaseModel], Dict[str, Any], None] = (
        ModifyCharacterRaceAndClassInput
    )

    def _execute_tool(
        self, db: Session, character_id: str, race_id: int, class_id: int
    ) -> str:
        """Execute character race and class modification logic"""
        if not self._validate_character_exists(db, character_id):
            raise ToolValidationError(f"Character ID '{character_id}' does not exist")

        # Validate race and class ID validity
        races = langchain_tool_registry.races
        classes = langchain_tool_registry.classes

        if str(race_id) not in races:
            available_races = ", ".join([f"{v}({k})" for k, v in races.items()])
            raise ToolValidationError(
                f"Invalid race ID '{race_id}'. Available options: {available_races}"
            )

        if str(class_id) not in classes:
            available_classes = ", ".join([f"{v}({k})" for k, v in classes.items()])
            raise ToolValidationError(
                f"Invalid class ID '{class_id}'. Available options: {available_classes}"
            )

        updated_character = crud.update_character_race_and_class(
            db=db, character_id=character_id, race_id=race_id, class_id=class_id
        )

        if updated_character:
            race_id_val = getattr(updated_character, "race_id", None)
            class_id_val = getattr(updated_character, "class_id", None)
            race_id = int(race_id_val) if race_id_val is not None else 0
            class_id = int(class_id_val) if class_id_val is not None else 0
            race_name = crud.get_dnd_race_name_by_id(db, race_id)
            class_name = crud.get_dnd_class_name_by_id(db, class_id)
            return f"Success: Character {updated_character.name} (ID: {character_id}) race has been updated to {race_name}, class has been updated to {class_name}."
        else:
            raise ToolValidationError(
                f"Failed to update race and class for character (ID: {character_id})."
            )


class ItemModification(BaseModel):
    """Item modification entry"""

    name: str = Field(description="Name of the item or equipment")
    description: str = Field(
        default="", description="Description of the item or equipment"
    )
    quantity: int = Field(
        description="Quantity of the item or equipment. If 0, will be removed from the character"
    )
    type: str = Field(
        description="Type of modification, 'equipment' for equipment, 'inventory' for items in inventory"
    )


class ModifyCharacterItemsInput(BaseModel):
    """Input parameters for character items modification tool"""

    character_id: str = Field(description="Unique ID of the character")
    items: List[ItemModification] = Field(description="List of items to modify")


class ModifyCharacterItemsTool(BaseDnDTool):
    """Character items modification tool"""

    name: str = "modify_character_items"
    description: str = (
        "MUST IMMEDIATELY modify character equipment and inventory when ANY item changes occur - NEVER manually track items. "
        "MANDATORY usage for: finding loot/treasure, buying/selling items, equipment damage/loss, item consumption, "
        "theft, drops, gifts, crafting results, and ANY inventory/equipment modification. "
        "Each item includes name, description, quantity, and type (equipment/inventory). "
        "ABSOLUTELY FORBIDDEN to describe item changes without calling this tool. "
        "Call this tool the INSTANT any equipment or inventory is affected by story events."
    )
    args_schema: Union[Type[BaseModel], Dict[str, Any], None] = (
        ModifyCharacterItemsInput
    )

    def _execute_tool(
        self, db: Session, character_id: str, items: List[ItemModification]
    ) -> str:
        """Execute character items modification logic"""
        if not self._validate_character_exists(db, character_id):
            raise ToolValidationError(f"Character ID '{character_id}' does not exist")

        # Validate item list format
        for item in items:
            if not all(hasattr(item, attr) for attr in ["name", "quantity", "type"]):
                raise ToolValidationError(
                    "Each item must contain 'name', 'quantity', and 'type' attributes"
                )
            if item.type not in ["equipment", "inventory"]:
                raise ToolValidationError(
                    f"Invalid type for item '{item.name}'. Must be 'equipment' or 'inventory'"
                )

        # Convert Pydantic objects to dictionaries for CRUD method
        items_as_dicts = [
            {
                "name": item.name,
                "description": item.description,
                "quantity": item.quantity,
                "type": item.type,
            }
            for item in items
        ]

        updated_character = crud.update_character_items(
            db=db, character_id=character_id, items_to_modify=items_as_dicts
        )

        if updated_character:
            # Create changes summary
            changes_summary = []
            for item in items:
                action = (
                    "removed"
                    if item.quantity == 0
                    else f"set quantity to {item.quantity}"
                )
                item_type_en = "Equipment" if item.type == "equipment" else "Item"
                changes_summary.append(f"{item_type_en} '{item.name}': {action}")

            # Fixed message format issue in original code
            summary_str = "; ".join(changes_summary)
            return f"Success: Character {updated_character.name} (ID: {character_id}) items have been updated. {summary_str}."
        else:
            raise ToolValidationError(
                f"Failed to update items for character (ID: {character_id})."
            )


# --- Plot / Story tools for DM ---


class UpdatePlotNodeStatusInput(BaseModel):
    """Input for updating a plot node status in the active outline."""

    story_id: int = Field(description="ID of the story")
    node_index: int = Field(description="Index of the plot node (1-based)")
    status: str = Field(
        description="New status for the node: Pending, InProgress, Finish, or Canceled"
    )


class UpdatePlotNodeStatusTool(BaseDnDTool):
    """DM tool: update the status of a specific plot node in the active outline."""

    name: str = "update_plot_node_status"
    description: str = (
        "Update the status of a specific plot node for a story's active outline. "
        "Use this whenever a story beat / scene is completed, started, or skipped. "
        "Valid statuses: Pending, InProgress, Finish, Canceled."
    )
    args_schema: Union[Type[BaseModel], Dict[str, Any], None] = (
        UpdatePlotNodeStatusInput
    )

    def _execute_tool(
        self,
        db: Session,
        story_id: int,
        node_index: int,
        status: str,
    ) -> str:
        status_normalized = status.strip()
        if status_normalized not in crud.ALLOWED_NODE_STATUSES:
            allowed = ", ".join(sorted(crud.ALLOWED_NODE_STATUSES))
            raise ToolValidationError(f"Invalid status '{status}'. Allowed: {allowed}.")

        outline = crud.update_plot_node_status(
            db=db,
            story_id=story_id,
            node_index=node_index,
            new_status=status_normalized,
        )

        if outline is None:
            raise ToolValidationError(
                "Active plot outline or specified node not found for this story."
            )

        return (
            f"Updated story {story_id} node {node_index} status to {status_normalized}."
        )


class MarkPlotNodeAsEndingInput(BaseModel):
    """Input for marking/unmarking a plot node as an ending."""

    story_id: int = Field(description="ID of the story")
    node_index: int = Field(description="Index of the plot node (1-based)")
    is_ending: bool = Field(
        description="Whether this node should be marked as an ending node"
    )


class MarkPlotNodeAsEndingTool(BaseDnDTool):
    """DM tool: mark or unmark a specific plot node as an ending."""

    name: str = "mark_plot_node_as_ending"
    description: str = (
        "Mark or unmark a specific plot node as an ending node for the story's active outline. "
        "Use this when adjusting which scenes count as possible endings."
    )
    args_schema: Union[Type[BaseModel], Dict[str, Any], None] = (
        MarkPlotNodeAsEndingInput
    )

    def _execute_tool(
        self,
        db: Session,
        story_id: int,
        node_index: int,
        is_ending: bool,
    ) -> str:
        outline = crud.mark_plot_node_as_ending(
            db=db,
            story_id=story_id,
            node_index=node_index,
            is_ending=is_ending,
        )

        if outline is None:
            raise ToolValidationError(
                "Active plot outline or specified node not found for this story."
            )

        flag = "ending" if is_ending else "non-ending"
        return f"Marked story {story_id} node {node_index} as {flag}."


class TriggerRegenerateSynopsisInput(BaseModel):
    """Input for regenerating synopsis based on the active outline."""

    story_id: int = Field(description="ID of the story")
    style: Optional[str] = Field(
        default=None,
        description="Optional style hint for the synopsis, e.g., 'light', 'dark', 'anime-like'",
    )
    word_limit: int = Field(
        default=100,
        description="Maximum number of English words for the synopsis",
        gt=0,
    )
    language: Optional[str] = Field(
        default=None,
        description="Preferred language code, e.g., 'en' or 'zh'. If omitted, model decides.",
    )


class TriggerRegenerateSynopsisTool(BaseDnDTool):
    """DM tool: regenerate the synopsis from the current active outline."""

    name: str = "trigger_regenerate_synopsis"
    description: str = (
        "Regenerate the story synopsis based on the current active plot outline. "
        "Use this after significant changes to the outline or node statuses, so players see an up-to-date summary."
    )
    args_schema: Union[Type[BaseModel], Dict[str, Any], None] = (
        TriggerRegenerateSynopsisInput
    )

    def _execute_tool(
        self,
        db: Session,
        story_id: int,
        style: Optional[str] = None,
        word_limit: int = 100,
        language: Optional[str] = None,
    ) -> str:
        # 获取当前激活的剧情列表
        outline_record = crud.get_active_plot_outline(db, story_id=story_id)
        if outline_record is None:
            raise ToolValidationError("No active plot outline found for this story.")

        try:
            nodes_raw = outline_record.nodes or []
            if not isinstance(nodes_raw, list):
                raise ToolValidationError("Stored outline nodes are not a list.")

            nodes = [schemas.PlotNodeSchema(**node_data) for node_data in nodes_raw]
            outline_schema = schemas.PlotOutlineSchema(nodes=nodes)
        except Exception as e:  # noqa: BLE001
            raise ToolValidationError(
                f"Failed to parse stored plot outline: {e}"
            ) from e

        # 调用 SynopsisAgent 生成新的简介
        synopsis_text = asyncio.run(
            generate_plot_synopsis(
                outline=outline_schema,
                style=style,
                word_limit=word_limit,
                language=language,
            )
        )

        if not synopsis_text:
            raise ToolValidationError("Failed to generate synopsis from LLM.")

        # 保存为新的 Synopsis 记录，并将旧的设为非激活
        crud.create_synopsis_for_story(
            db=db,
            story_id=story_id,
            outline_version=int(getattr(outline_record, "version", 1)),
            content=synopsis_text,
            is_active=True,
        )

        return (
            "Synopsis regenerated and saved as the active synopsis for this story.\n\n"
            "Updated synopsis:\n"
            f"{synopsis_text}"
        )


# 注册所有工具到注册表
def register_all_tools():
    """Register all D&D tools to the LangChain tool registry"""
    tools = [
        RollDiceTool(),
        ModifyCharacterIntegerAttributeTool(),
        ModifyCharacterBoolAttributeTool(),
        ModifyCharacterRaceAndClassTool(),
        ModifyCharacterItemsTool(),
        UpdatePlotNodeStatusTool(),
        MarkPlotNodeAsEndingTool(),
        TriggerRegenerateSynopsisTool(),
    ]

    for tool in tools:
        langchain_tool_registry.register_tool(tool)


# Auto-register tools
register_all_tools()
