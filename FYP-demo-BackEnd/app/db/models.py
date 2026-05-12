from __future__ import annotations

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Text,
    Integer,
    JSON,
    Boolean,
    Table,  # Added Table for association tables
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from typing import List
import uuid

Base = declarative_base()


class ConfigEntry(Base):
    """通用配置存储表，用于保存敏感或可变的运行参数。"""

    __tablename__ = "config_entries"

    key: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    value: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )


# Association table for Character and Spell (many-to-many)
character_spell_association = Table(
    "character_spells",
    Base.metadata,
    Column("character_id", String, ForeignKey("characters.id"), primary_key=True),
    Column("spell_id", Integer, ForeignKey("spells.id"), primary_key=True),
    Column("is_prepared", Boolean, default=False),
)

# Association table for Character and Feature (many-to-many)
character_feature_association = Table(
    "character_features",
    Base.metadata,
    Column("character_id", String, ForeignKey("characters.id"), primary_key=True),
    Column("feature_id", Integer, ForeignKey("features.id"), primary_key=True),
)

# Association table for Character and Proficiency (many-to-many)
character_proficiency_association = Table(
    "character_proficiencies",
    Base.metadata,
    Column("character_id", String, ForeignKey("characters.id"), primary_key=True),
    Column("proficiency_id", Integer, ForeignKey("proficiencies.id"), primary_key=True),
)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=True)  # Add name field
    created_at = Column(DateTime, default=datetime.now)

    messages = relationship("ChatMessage", back_populates="session")
    characters = relationship(
        "Character", back_populates="session"
    )  # 新增：与 Character 的关联


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # "user", "assistant", "system", "tool"
    content = Column(Text, nullable=True)  # Content can be null for tool calls
    name = Column(String, nullable=True)  # For function/tool name
    tool_call_id = Column(
        String, nullable=True
    )  # ID of the tool call (for assistant request or tool response)
    tool_arguments = Column(
        JSON, nullable=True
    )  # Arguments for the tool call, if role is assistant
    created_at = Column(DateTime, default=datetime.now)

    session = relationship("ChatSession", back_populates="messages")


class Character(Base):
    __tablename__ = "characters"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(
        String, ForeignKey("chat_sessions.id"), nullable=False
    )  # 新增：关联的会话ID
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    gold = Column(Integer, default=0)
    experience = Column(Integer, default=0)
    level = Column(Integer, default=1)
    armor = Column(Integer, default=10)
    speed = Column(Integer, default=30)
    health = Column(Integer, default=10)
    temp_health = Column(Integer, default=0)
    race_id = Column(Integer, ForeignKey("races.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("dnd_classes.id"), nullable=False)
    # spells = Column(JSON, default=[]) # Replaced by many-to-many relationship
    # features = Column(JSON, default=[]) # Replaced by many-to-many relationship
    # proficiencies = Column( # Replaced by many-to-many relationship
    #     JSON, default=lambda: []
    # )  # Stores actual proficiency details/names # Replaced by many-to-many relationship
    equipment = Column(
        JSON, nullable=True, default=lambda: {}
    )  # Stores actual equipment details
    inventory_items = Column(JSON, nullable=True, default=lambda: {})

    # Fields based on CharacterCreate schema
    ability_scores = Column(
        JSON, nullable=False, default=lambda: {}
    )  # e.g., {"strength": 15, ...}
    proficiency_ids = Column(
        JSON, nullable=False, default=lambda: []
    )  # List of proficiency IDs
    equipment_ids = Column(
        JSON, nullable=False, default=lambda: []
    )  # List of equipment IDs
    half_elf_choices = Column(JSON, nullable=True)  # Specific choices for half-elf race

    # Derived stats (calculated by backend)
    strength = Column(Integer, default=10)
    strength_proficiency = Column(Boolean, default=False)
    dexterity = Column(Integer, default=10)
    dexterity_proficiency = Column(Boolean, default=False)
    constitution = Column(Integer, default=10)
    constitution_proficiency = Column(Boolean, default=False)
    intelligence = Column(Integer, default=10)
    intelligence_proficiency = Column(Boolean, default=False)
    wisdom = Column(Integer, default=10)
    wisdom_proficiency = Column(Boolean, default=False)
    charisma = Column(Integer, default=10)
    charisma_proficiency = Column(Boolean, default=False)
    is_player = Column(Boolean, default=False)  # 角色是否为玩家控制
    is_male = Column(Boolean, default=False)  # 角色性别，默认为女

    # Relationships
    session = relationship(
        "ChatSession", back_populates="characters"
    )  # 新增：与 ChatSession 的关联
    race = relationship("Race", back_populates="characters")
    dnd_class = relationship("DndClass", back_populates="characters")

    spells_rel = relationship(
        "Spell",
        secondary=character_spell_association,
        back_populates="characters_with_spell",
    )
    features_rel = relationship(
        "Feature",
        secondary=character_feature_association,
        back_populates="characters_with_feature",
    )
    proficiencies_known = relationship(
        "Proficiency",
        secondary=character_proficiency_association,
        back_populates="characters_with_proficiency",
    )

    @property
    def spells(self) -> List[str]:
        return [s.name for s in self.spells_rel] if self.spells_rel else []

    @property
    def features(self) -> List[str]:
        return [f.name for f in self.features_rel] if self.features_rel else []

    @property
    def proficiencies(self) -> List[str]:
        return (
            [p.name for p in self.proficiencies_known]
            if self.proficiencies_known
            else []
        )


# D&D Static Data Tables


class Race(Base):
    __tablename__ = "races"
    id = Column(
        Integer, primary_key=True, index=True
    )  # Corresponds to keys in dnd_data.json
    name = Column(String, unique=True, nullable=False)

    characters = relationship("Character", back_populates="race")


class DndClass(Base):  # Renamed from Class to avoid keyword conflict
    __tablename__ = "dnd_classes"
    id = Column(
        Integer, primary_key=True, index=True
    )  # Corresponds to keys in dnd_data.json
    name = Column(String, unique=True, nullable=False)

    characters = relationship("Character", back_populates="dnd_class")


class Spell(Base):
    __tablename__ = "spells"
    id = Column(
        Integer, primary_key=True, index=True
    )  # Corresponds to keys in dnd_data.json
    name = Column(String, unique=True, nullable=False)
    level = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)

    characters_with_spell = relationship(
        "Character", secondary=character_spell_association, back_populates="spells_rel"
    )


class Feature(Base):
    __tablename__ = "features"
    id = Column(
        Integer, primary_key=True, index=True
    )  # Corresponds to keys in dnd_data.json
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)

    characters_with_feature = relationship(
        "Character",
        secondary=character_feature_association,
        back_populates="features_rel",
    )


class Proficiency(Base):
    __tablename__ = "proficiencies"
    id = Column(
        Integer, primary_key=True, index=True
    )  # Corresponds to keys in dnd_data.json
    name = Column(String, unique=True, nullable=False)
    type = Column(String, nullable=True)  # e.g., "Skill", "Tool", "Language"

    characters_with_proficiency = relationship(
        "Character",
        secondary=character_proficiency_association,
        back_populates="proficiencies_known",
    )


class ConversationSuggestions(Base):
    __tablename__ = "conversation_suggestions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=False)
    suggestions = Column(JSON, nullable=False)  # 存储选项数组
    created_at = Column(DateTime, default=datetime.now)

    # 关系
    message = relationship("ChatMessage", backref="suggestions_rel")


# --- Story & Plot Outline Models ---


class Story(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, nullable=False)
    theme = Column(String, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    outlines = relationship("PlotOutline", back_populates="story")
    synopses = relationship("Synopsis", back_populates="story")
    feedbacks = relationship("PlayerFeedback", back_populates="story")


class PlotOutline(Base):
    __tablename__ = "plot_outlines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    nodes = Column(JSON, nullable=False)  # 序列化后的 PlotNode 列表
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    story = relationship("Story", back_populates="outlines")


class Synopsis(Base):
    __tablename__ = "synopses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    outline_version = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    story = relationship("Story", back_populates="synopses")
    feedbacks = relationship("PlayerFeedback", back_populates="synopsis")


class PlayerFeedback(Base):
    __tablename__ = "player_feedback"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    outline_version = Column(Integer, nullable=True)
    synopsis_id = Column(Integer, ForeignKey("synopses.id"), nullable=True)
    feedback_text = Column(Text, nullable=False)
    type = Column(String, nullable=False)  # ModifyExisting | CreateNew
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    story = relationship("Story", back_populates="feedbacks")
    synopsis = relationship("Synopsis", back_populates="feedbacks")
