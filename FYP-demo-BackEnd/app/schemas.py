import uuid
from datetime import datetime
from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ChatSessionBase(BaseModel):
    name: str | None = None


class ChatSessionCreate(ChatSessionBase):
    name: str | None = None


class ChatSession(BaseModel):
    """会话信息模型"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    is_main_character_exist: bool = False  # 指示该会话下是否已经存在主角色

    class Config:
        from_attributes = True


# --- Chat Message Schemas ---


class ChatMessageBase(BaseModel):
    session_id: str
    role: Literal["user", "assistant", "system", "tool"]  # 移除废弃的 "function" 角色
    content: str | None = None  # Content can be None if assistant is making tool calls
    name: str | None = None  # For function/tool name
    tool_call_id: str | None = (
        None  # For assistant making a call, or tool providing a response
    )
    tool_arguments: Dict | None = (
        None  # For assistant messages requesting tool calls with arguments
    )


class ChatMessageCreate(ChatMessageBase):
    pass


class ChatMessage(ChatMessageBase):
    id: int  # Assuming an auto-incrementing ID from the database
    created_at: datetime = Field(default_factory=datetime.now)
    suggestions: List[str] | None = None  # 可选的选项列表

    class Config:
        from_attributes = True


class MessageSendRequest(BaseModel):
    content: str


# --- Character Schemas ---


class CharacterCreate(BaseModel):
    """基础模型，包含所有从前端接收的核心数据"""

    name: str
    session_id: str
    race_id: int
    class_id: int
    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int
    proficiency_ids: List[int]  # 用户选择的熟练项 ID 列表
    half_elf_choices: List[str] | None = None  # 半精灵额外属性选择
    is_player: bool = False  # 该角色是否为玩家控制
    is_male: bool = False  # 性别，True=男，False=女


class Character(BaseModel):
    """从数据库读取角色时返回的模型"""

    id: str
    name: str
    created_at: datetime
    is_male: bool
    gold: int
    experience: int
    level: int
    armor: int
    speed: int
    health: int
    temp_health: int
    race_id: int
    class_id: int
    spells: List[str]
    features: List[str]
    proficiencies: List[str]
    equipment: Dict[
        str, Dict[str, Any]
    ]  # 格式: {"装备名": {"item_name": "装备名", "item_description": "装备描述", "item_quantity": 数量}}
    inventory_items: Dict[
        str, Dict[str, Any]
    ]  # 格式: {"物品名": {"item_name": "物品名", "item_description": "物品描述", "item_quantity": 数量}}
    strength: int
    strength_proficiency: bool
    dexterity: int
    dexterity_proficiency: bool
    constitution: int
    constitution_proficiency: bool
    intelligence: int
    intelligence_proficiency: bool
    wisdom: int
    wisdom_proficiency: bool
    charisma: int
    charisma_proficiency: bool
    is_player: bool

    class Config:
        from_attributes = True


# 用于向前端提供所有 D&D 基础数据的模型
class DndDataResponse(BaseModel):
    races: Dict[str, str]
    classes: Dict[str, str]
    spells: Dict[str, str]
    features: Dict[str, str]
    proficiencies: Dict[str, str]


# --- Conversation Suggestions Schemas ---


class ConversationSuggestionsCreate(BaseModel):
    """创建对话选项的输入模型"""

    message_id: int
    suggestions: List[str]


class ConversationSuggestions(BaseModel):
    """对话选项的完整模型"""

    id: int
    message_id: int
    suggestions: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


# --- 配置项 Schemas ---


class ConfigItem(BaseModel):
    key: str
    value: Optional[str] = None

    class Config:
        from_attributes = True


class ConfigUpdateRequest(BaseModel):
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None
    OPENAI_MODEL: Optional[str] = None
    RAG_EMBEDDING_API_KEY: Optional[str] = None
    RAG_EMBEDDING_BASE_URL: Optional[str] = None
    RAG_EMBEDDING_MODEL: Optional[str] = None
    SUGGEST_OPTIONS_MODEL: Optional[str] = None

    class Config:
        extra = "forbid"


class StructuredSuggestionsOutput(BaseModel):
    """LLM 结构化输出的选项格式"""

    chooses: List[str] = Field(description="生成的选项列表，最多 5 个")


# --- Plot Outline Schemas ---


class PlotNodeSchema(BaseModel):
    """Single plot node structure"""

    index: int = Field(description="Order of this plot node, starting from 1")
    title: str = Field(description="Title of the plot node, e.g. 'Newbie Village'")
    status: str = Field(
        description="Status of the plot node, e.g. Pending / InProgress / Finish / Canceled"
    )
    is_ending: bool = Field(
        default=False,
        description="Whether this node is an ending node (final boss / final event, etc.)",
    )
    summary: str | None = Field(
        default=None,
        description="Optional short description of what happens in this node",
    )


class PlotOutlineSchema(BaseModel):
    """Overall plot outline structure"""

    nodes: List[PlotNodeSchema] = Field(
        description="Full ordered list of plot nodes, must contain at least N nodes"
    )


# --- Story & Synopsis Schemas ---


class StoryCreateRequest(BaseModel):
    """创建故事并生成剧情列表的请求体"""

    title: str = Field(description="Story title or main theme")
    theme: str | None = Field(
        default=None, description="Detailed story theme / world setting"
    )
    N: int = Field(gt=0, description="Minimum number of plot nodes to generate")
    style: str | None = Field(
        default=None, description="Story style hint, e.g. light, dark, epic"
    )
    created_by: str | None = Field(
        default=None, description="Player or system that created this story"
    )
    session_id: str | None = Field(
        default=None,
        description="Optional chat session id to pull player character for outline generation",
    )


class StorySchema(BaseModel):
    """基础 Story 信息"""

    id: int
    title: str
    theme: str | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class StoryWithOutlineResponse(BaseModel):
    """创建故事后返回：当前激活的剧情列表"""

    story_id: int
    title: str
    theme: str | None = None
    outline_version: int
    outline: PlotOutlineSchema


class SynopsisCreateRequest(BaseModel):
    """为现有故事生成剧情简介的请求体"""

    style: str | None = Field(
        default=None, description="Synopsis style hint, e.g. anime-like, dark, etc."
    )
    word_limit: int = Field(
        default=100,
        gt=0,
        description="Maximum number of English words for the synopsis",
    )
    language: str | None = Field(
        default=None,
        description="Preferred language code, e.g. 'en' or 'zh'. If omitted, model decides.",
    )


class SynopsisSchema(BaseModel):
    """Synopsis 数据返回"""

    id: int
    story_id: int
    outline_version: int
    content: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class StoryDetailResponse(BaseModel):
    """故事详情：当前激活剧情列表 + 最新简介"""

    story: StorySchema
    outline: PlotOutlineSchema | None = None
    synopsis: SynopsisSchema | None = None


class PlayerFeedbackCreateRequest(BaseModel):
    """玩家提交剧情修改意见"""

    feedback_text: str = Field(description="Player's feedback about the story / plot")
    type: Literal["ModifyExisting", "CreateNew"] = Field(
        description="Feedback type: modify existing plot or create a brand new one"
    )


class PlayerFeedbackSchema(BaseModel):
    """玩家反馈数据"""

    id: int
    story_id: int
    outline_version: int | None = None
    synopsis_id: int | None = None
    feedback_text: str
    type: str
    processed: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RevisionOutput(BaseModel):
    """RevisionAgent 的结构化输出：新的剧情列表 + 简介"""

    outline: PlotOutlineSchema
    synopsis: str = Field(description="New synopsis text after revision")


# --- DM / Plot Node Update Schemas ---


class PlotNodeStatusUpdateRequest(BaseModel):
    """DM 更新剧情节点状态的请求体"""

    status: Literal["Pending", "InProgress", "Finish", "Canceled"] = Field(
        description="New status for the plot node"
    )


class PlotNodeEndingUpdateRequest(BaseModel):
    """DM 标记/取消结局节点的请求体"""

    is_ending: bool = Field(description="Whether this node should be marked as ending")
