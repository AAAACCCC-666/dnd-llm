from sqlalchemy.orm import Session, attributes
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, Any, List
from . import models
from .. import schemas  # Use .. to go up one level to app directory


def get_session(db: Session, session_id: str):
    session = (
        db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    )
    if session:
        # 仅当会话下存在 is_player=True 的角色时，才认为主角色已创建
        main_character_exists = (
            db.query(models.Character)
            .filter(models.Character.session_id == session_id)
            .filter(models.Character.is_player.is_(True))
            .first()
        )
        session.is_main_character_exist = main_character_exists is not None
    return session


def get_sessions(db: Session, skip: int = 0, limit: int = 100):
    sessions = db.query(models.ChatSession).offset(skip).limit(limit).all()
    for session in sessions:
        main_character_exists = (
            db.query(models.Character)
            .filter(models.Character.session_id == session.id)
            .filter(models.Character.is_player.is_(True))
            .first()
        )
        session.is_main_character_exist = main_character_exists is not None
    return sessions


def create_chat_session(db: Session, session: schemas.ChatSessionCreate):
    db_session = models.ChatSession(
        name=session.name
    )  # id and created_at are auto-generated
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


def delete_session_with_dependencies(db: Session, session_id: str) -> bool:
    """Delete a chat session and every record depending on it."""

    session = (
        db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    )
    if session is None:
        return False

    try:
        message_ids = [
            message_id
            for (message_id,) in db.query(models.ChatMessage.id)
            .filter(models.ChatMessage.session_id == session_id)
            .all()
        ]

        if message_ids:
            db.query(models.ConversationSuggestions).filter(
                models.ConversationSuggestions.message_id.in_(message_ids)
            ).delete(synchronize_session=False)

        character_ids = [
            character_id
            for (character_id,) in db.query(models.Character.id)
            .filter(models.Character.session_id == session_id)
            .all()
        ]

        if character_ids:
            db.execute(
                models.character_spell_association.delete().where(
                    models.character_spell_association.c.character_id.in_(character_ids)
                )
            )
            db.execute(
                models.character_feature_association.delete().where(
                    models.character_feature_association.c.character_id.in_(
                        character_ids
                    )
                )
            )
            db.execute(
                models.character_proficiency_association.delete().where(
                    models.character_proficiency_association.c.character_id.in_(
                        character_ids
                    )
                )
            )

            db.query(models.Character).filter(
                models.Character.session_id == session_id
            ).delete(synchronize_session=False)

        db.query(models.ChatMessage).filter(
            models.ChatMessage.session_id == session_id
        ).delete(synchronize_session=False)

        db.delete(session)
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise


def get_messages_by_session(
    db: Session,
    session_id: str,
    skip: int = 0,
    limit: int = 0,  # Default limit 0 means all
) -> List[models.ChatMessage]:
    """
    简化的消息查询 - 直接使用时间戳排序
    """
    query = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session_id)
        .order_by(models.ChatMessage.created_at.asc())
    )

    if skip > 0:
        query = query.offset(skip)

    if limit > 0:
        query = query.limit(limit)

    return query.all()


def create_chat_message(db: Session, message: schemas.ChatMessageCreate):
    """
    简化的消息创建 - 直接插入，无链表维护
    """
    db_message = models.ChatMessage(
        session_id=message.session_id,
        role=message.role,
        content=message.content,
        name=message.name,
        tool_call_id=message.tool_call_id,
        tool_arguments=message.tool_arguments,
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message


# --- Character CRUD Functions ---


def get_character_by_id(db: Session, character_id: str) -> models.Character | None:
    """
    Retrieves a character by its ID.
    If the character does not exist, returns None.
    """
    return (
        db.query(models.Character).filter(models.Character.id == character_id).first()
    )


def get_character_by_name(db: Session, name: str):
    return db.query(models.Character).filter(models.Character.name == name).first()


def get_characters(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Character).offset(skip).limit(limit).all()


def get_characters_by_session_id(
    db: Session, session_id: str, skip: int = 0, limit: int = 100
):
    """
    Retrieves a list of characters associated with a specific session_id, with pagination.
    """
    return (
        db.query(models.Character)
        .filter(models.Character.session_id == session_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_character(db: Session, character_data: schemas.CharacterCreate):
    """
    接收前端选择的所有数据，计算并创建一个完整的角色。
    """
    # --- 1. 属性计算 ---
    race_id = character_data.race_id
    class_id = character_data.class_id
    final_ability_scores = {
        "strength": character_data.strength,
        "dexterity": character_data.dexterity,
        "constitution": character_data.constitution,
        "intelligence": character_data.intelligence,
        "wisdom": character_data.wisdom,
        "charisma": character_data.charisma,
    }

    # 种族加成规则
    racial_bonuses_map = {
        1: {"constitution": 2},
        2: {"dexterity": 2},
        4: {
            "strength": 1,
            "dexterity": 1,
            "constitution": 1,
            "intelligence": 1,
            "wisdom": 1,
            "charisma": 1,
        },
        5: {"strength": 2, "charisma": 1},
        8: {"strength": 2, "constitution": 1},
    }
    bonus = racial_bonuses_map.get(race_id, {})
    for ability, value in bonus.items():
        if ability in final_ability_scores:
            final_ability_scores[ability] += value
    # 半精灵逻辑 (需要前端配合)
    if race_id == 7:
        final_ability_scores["charisma"] += 2
        if character_data.half_elf_choices:
            for choice in character_data.half_elf_choices:
                if choice in final_ability_scores and choice != "charisma":
                    final_ability_scores[choice] += 1

    # --- 2. 豁免熟练项计算 ---
    class_saves_map = {
        1: ["strength", "constitution"],
        2: ["dexterity", "charisma"],
        12: ["intelligence", "wisdom"],
    }
    ability_proficiencies = {
        f"{ability}_proficiency": False for ability in final_ability_scores.keys()
    }
    for save in class_saves_map.get(class_id, []):
        ability_proficiencies[f"{save}_proficiency"] = True

    # --- 3. HP 计算 ---
    class_hit_dice_map = {1: 12, 2: 8, 12: 6}
    hit_die = class_hit_dice_map.get(class_id, 8)
    con_modifier = (final_ability_scores["constitution"] - 10) // 2
    health = hit_die + con_modifier
    if race_id == 1:
        health += 1

    # --- 4. AC 和 Speed 计算 ---
    race_speeds_map = {1: 25, 2: 30, 4: 30, 5: 30, 7: 30, 8: 30}
    speed = race_speeds_map.get(race_id, 30)
    dex_modifier = (final_ability_scores["dexterity"] - 10) // 2
    armor = 10 + dex_modifier
    # 装备AC加成现在应该在创建角色后，通过其他逻辑处理，或者在前端选择装备时就计算好AC
    # if 4 in character_data.equipment_ids: # 皮甲
    #     armor = 11 + dex_modifier
    # elif 5 in character_data.equipment_ids: # 链甲
    #     armor = 16

    # --- 5. 从ID转换到名称 ---
    # proficiencies_list is no longer directly used for Character model construction.
    # Instead, we'll fetch Proficiency objects and assign them to the relationship.
    # equipment_list 不再需要，因为装备直接以JSON形式存储

    # --- 6. 创建数据库对象 ---
    db_character = models.Character(
        session_id=character_data.session_id,  # 新增：处理 session_id
        name=character_data.name,
        race_id=race_id,  # Renamed from race
        class_id=class_id,
        gold=15,
        experience=0,
        level=1,
        health=health,
        armor=armor,
        speed=speed,
        temp_health=0,
        # spells 和 features 是 relationships, 不应在构造函数中用列表初始化
        # SQLAlchemy 会处理它们。如果需要关联对象，在创建并提交后进行。
        proficiency_ids=character_data.proficiency_ids,  # 存储原始的 ID 列表
        equipment={},  # 初始化为空字典
        inventory_items={
            "packsack": {
                "item_name": "packsack",
                "item_description": "A sturdy canvas backpack for carrying supplies",
                "item_quantity": 1,
            },
            "food (1day)": {
                "item_name": "food (1day)",
                "item_description": "Basic rations sufficient for one day",
                "item_quantity": 1,
            },
            "water bag": {
                "item_name": "water bag",
                "item_description": "A leather water bag capable of holding water for a day",
                "item_quantity": 1,
            },
        },  # 使用新的物品格式
        **final_ability_scores,  # 使用 ** 优雅地解包字典
        **ability_proficiencies,  # 同上
        is_player=character_data.is_player,  # 新增：处理 is_player
        is_male=character_data.is_male,  # 新增性别
    )

    # --- 7. 关联熟练项 ---
    if character_data.proficiency_ids:
        selected_proficiencies = (
            db.query(models.Proficiency)
            .filter(models.Proficiency.id.in_(character_data.proficiency_ids))
            .all()
        )
        db_character.proficiencies_known = selected_proficiencies
    else:
        db_character.proficiencies_known = []

    db.add(db_character)
    db.commit()
    db.refresh(db_character)

    return db_character


def update_character_integer_attribute(
    db: Session, character_id: str, attribute: str, value: int
) -> models.Character | None:
    """
    Updates a single integer attribute for a given character.

    Args:
        db: The database session.
        character_id: The ID of the character to update.
        attribute: The name of the integer attribute to update.
        value: The new integer value.

    Returns:
        The updated character object or None if not found or attribute is invalid.
    """
    character = (
        db.query(models.Character).filter(models.Character.id == character_id).first()
    )
    if not character:
        return None

    # Validate that the attribute exists and is an integer field
    if hasattr(character, attribute) and isinstance(getattr(character, attribute), int):
        setattr(character, attribute, value)
        db.commit()
        db.refresh(character)
        return character
    else:
        # Invalid attribute name or not an integer field
        db.rollback()  # Rollback any potential changes if validation fails mid-transaction
        return None


def update_character_boolean_attribute(
    db: Session, character_id: str, attribute: str, value: bool
) -> models.Character | None:
    """
    Updates a single boolean attribute for a given character.

    Args:
        db: The database session.
        character_id: The ID of the character to update.
        attribute: The name of the boolean attribute to update.
        value: The new boolean value.

    Returns:
        The updated character object or None if not found or attribute is invalid.
    """
    character = (
        db.query(models.Character).filter(models.Character.id == character_id).first()
    )
    if not character:
        return None

    # Validate that the attribute exists and is a boolean field
    if hasattr(character, attribute) and isinstance(
        getattr(character, attribute), bool
    ):
        setattr(character, attribute, value)
        db.commit()
        db.refresh(character)
        return character
    else:
        # Invalid attribute name or not a boolean field
        db.rollback()
        return None


# --- Get DND Data ---


def get_dnd_race_name_by_id(db: Session, race_id: int):
    """
    根据 race_id 获取 DND 种族的名称。
    如果找不到对应的种族，则返回 None。
    """
    return db.query(models.Race.name).filter(models.Race.id == race_id).scalar()


def get_dnd_class_name_by_id(db: Session, class_id: int):
    """
    根据 class_id 获取 DND 职业的名称。
    如果找不到对应的职业，则返回 None。
    """
    return (
        db.query(models.DndClass.name).filter(models.DndClass.id == class_id).scalar()
    )


def update_character_race_and_class(
    db: Session, character_id: str, race_id: int, class_id: int
) -> models.Character | None:
    """
    Updates the race and class for a given character.

    Args:
        db: The database session.
        character_id: The ID of the character to update.
        race_id: The new race ID.
        class_id: The new class ID.

    Returns:
        The updated character object or None if not found.
    """
    character = (
        db.query(models.Character).filter(models.Character.id == character_id).first()
    )
    if not character:
        return None

    setattr(character, "race_id", race_id)
    setattr(character, "class_id", class_id)

    db.commit()
    db.refresh(character)
    return character


def update_character_items(
    db: Session, character_id: str, items_to_modify: list[dict]
) -> models.Character | None:
    """
    Updates a character's equipment and inventory items.

    Args:
        db: The database session.
        character_id: The ID of the character to update.
        items_to_modify: A list of dictionaries, each with "name", "quantity", "description",
                         and "type" ('equipment' or 'inventory').

    Returns:
        The updated character object or None if not found.
    """
    character = (
        db.query(models.Character).filter(models.Character.id == character_id).first()
    )
    if not character:
        return None

    # Ensure equipment and inventory are dictionaries
    equipment_dict: Dict[str, Any] = {}
    inventory_dict: Dict[str, Any] = {}

    # Get current values safely
    current_equipment = getattr(character, "equipment", None)
    current_inventory = getattr(character, "inventory_items", None)

    if current_equipment is not None:
        equipment_dict.update(current_equipment)
    if current_inventory is not None:
        inventory_dict.update(current_inventory)

    for item in items_to_modify:
        item_name = item.get("name")
        quantity = item.get("quantity")
        description = item.get("description", "")
        item_type = item.get("type")

        if not all([item_name, isinstance(quantity, int), item_type]):
            continue  # Skip invalid item data

        # Type guard to ensure item_name is string
        if not isinstance(item_name, str):
            continue

        if item_type == "equipment":
            if quantity is not None and quantity > 0:
                equipment_dict[item_name] = {
                    "item_name": item_name,
                    "item_description": description,
                    "item_quantity": quantity,
                }
            elif item_name in equipment_dict:
                del equipment_dict[item_name]
        elif item_type == "inventory":
            if quantity is not None and quantity > 0:
                inventory_dict[item_name] = {
                    "item_name": item_name,
                    "item_description": description,
                    "item_quantity": quantity,
                }
            elif item_name in inventory_dict:
                del inventory_dict[item_name]

    # Update the character's attributes with the modified dictionaries
    setattr(character, "equipment", equipment_dict)
    setattr(character, "inventory_items", inventory_dict)

    # Mark the JSON fields as modified to ensure SQLAlchemy detects the change
    attributes.flag_modified(character, "equipment")
    attributes.flag_modified(character, "inventory_items")

    db.commit()
    db.refresh(character)
    return character


def get_all_dnd_static_data(db: Session) -> Dict[str, Dict[str, str]]:
    """
    Retrieves all static D&D data from the database.
    """
    races = {str(race.id): str(race.name) for race in db.query(models.Race).all()}
    classes = {str(cls.id): str(cls.name) for cls in db.query(models.DndClass).all()}
    spells = {str(spell.id): str(spell.name) for spell in db.query(models.Spell).all()}
    features = {
        str(feature.id): str(feature.name) for feature in db.query(models.Feature).all()
    }
    proficiencies = {
        str(prof.id): str(prof.name) for prof in db.query(models.Proficiency).all()
    }

    return {
        "races": races,
        "classes": classes,
        "spells": spells,
        "features": features,
        "proficiencies": proficiencies,
    }


# --- Conversation Suggestions CRUD Functions ---


def create_conversation_suggestions(
    db: Session, message_id: int, suggestions: List[str]
) -> models.ConversationSuggestions:
    """
    为指定消息创建对话选项记录

    Args:
        db: 数据库会话
        message_id: 消息ID
        suggestions: 选项列表

    Returns:
        创建的对话选项记录
    """
    db_suggestions = models.ConversationSuggestions(
        message_id=message_id, suggestions=suggestions
    )
    db.add(db_suggestions)
    db.commit()
    db.refresh(db_suggestions)
    return db_suggestions


def get_suggestions_by_message_id(
    db: Session, message_id: int
) -> models.ConversationSuggestions | None:
    """
    根据消息ID获取对话选项

    Args:
        db: 数据库会话
        message_id: 消息ID

    Returns:
        对话选项记录或None
    """
    return (
        db.query(models.ConversationSuggestions)
        .filter(models.ConversationSuggestions.message_id == message_id)
        .first()
    )


def get_messages_with_suggestions_by_session(
    db: Session,
    session_id: str,
    skip: int = 0,
    limit: int = 0,  # Default limit 0 means all
):
    """
    获取带有选项的会话消息列表

    Args:
        db: 数据库会话
        session_id: 会话ID
        skip: 跳过的消息数
        limit: 限制返回的消息数 (0表示全部)

    Returns:
        消息列表，每个消息包含关联的选项
    """
    # 首先获取所有消息
    messages = get_messages_by_session(db, session_id, skip, limit)

    # 为每个消息加载关联的选项
    for message in messages:
        message_id = getattr(message, "id", None)
        if message_id is not None:
            suggestions = get_suggestions_by_message_id(db, message_id)
            # 直接在消息对象上添加 suggestions 属性
            message.suggestions = suggestions.suggestions if suggestions else None

    return messages


# --- Story, PlotOutline, Synopsis CRUD Functions ---


def create_story(
    db: Session,
    title: str,
    theme: str | None = None,
    created_by: str | None = None,
) -> models.Story:
    """Create a new Story record."""
    story = models.Story(title=title, theme=theme, created_by=created_by)
    db.add(story)
    db.commit()
    db.refresh(story)
    return story


def get_story(db: Session, story_id: int) -> models.Story | None:
    """Get Story by ID."""
    return db.query(models.Story).filter(models.Story.id == story_id).first()


def create_plot_outline_for_story(
    db: Session,
    story_id: int,
    outline: schemas.PlotOutlineSchema,
    version: int = 1,
    is_active: bool = True,
) -> models.PlotOutline:
    """
    Persist PlotOutline for a story.

    Nodes are stored as JSON list of dicts.
    """
    nodes_data = [node.dict() for node in outline.nodes]

    # If this outline is active, mark existing outlines for this story as inactive
    if is_active:
        db.query(models.PlotOutline).filter(
            models.PlotOutline.story_id == story_id,
            models.PlotOutline.is_active.is_(True),
        ).update({"is_active": False})

    db_outline = models.PlotOutline(
        story_id=story_id,
        version=version,
        nodes=nodes_data,
        is_active=is_active,
    )
    db.add(db_outline)
    db.commit()
    db.refresh(db_outline)
    return db_outline


def get_active_plot_outline(db: Session, story_id: int) -> models.PlotOutline | None:
    """Get the active PlotOutline for a story."""
    return (
        db.query(models.PlotOutline)
        .filter(
            models.PlotOutline.story_id == story_id,
            models.PlotOutline.is_active.is_(True),
        )
        .order_by(models.PlotOutline.version.desc())
        .first()
    )


def create_synopsis_for_story(
    db: Session,
    story_id: int,
    outline_version: int,
    content: str,
    is_active: bool = True,
) -> models.Synopsis:
    """
    Create a Synopsis for a story.

    If is_active is True, any previous active synopsis for this story
    will be marked as inactive.
    """
    if is_active:
        db.query(models.Synopsis).filter(
            models.Synopsis.story_id == story_id,
            models.Synopsis.is_active.is_(True),
        ).update({"is_active": False})

    synopsis = models.Synopsis(
        story_id=story_id,
        outline_version=outline_version,
        content=content,
        is_active=is_active,
    )
    db.add(synopsis)
    db.commit()
    db.refresh(synopsis)
    return synopsis


def create_player_feedback(
    db: Session,
    story_id: int,
    outline_version: int | None,
    synopsis_id: int | None,
    feedback_text: str,
    feedback_type: str,
    processed: bool = False,
) -> models.PlayerFeedback:
    """Create a PlayerFeedback record."""
    feedback = models.PlayerFeedback(
        story_id=story_id,
        outline_version=outline_version,
        synopsis_id=synopsis_id,
        feedback_text=feedback_text,
        type=feedback_type,
        processed=processed,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def mark_feedback_processed(
    db: Session, feedback_id: int, outline_version: int, synopsis_id: int
) -> models.PlayerFeedback | None:
    """Mark feedback as processed and attach resulting outline_version/synopsis_id."""
    feedback = (
        db.query(models.PlayerFeedback)
        .filter(models.PlayerFeedback.id == feedback_id)
        .first()
    )
    if not feedback:
        return None

    # 使用 setattr 避免静态类型检查器将 ORM 字段视为 Column[...] 而报错
    setattr(feedback, "processed", True)
    setattr(feedback, "outline_version", outline_version)
    setattr(feedback, "synopsis_id", synopsis_id)
    db.commit()
    db.refresh(feedback)
    return feedback


def get_latest_outline_for_story(
    db: Session, story_id: int
) -> models.PlotOutline | None:
    """Get latest outline (by version) for story."""
    return (
        db.query(models.PlotOutline)
        .filter(models.PlotOutline.story_id == story_id)
        .order_by(models.PlotOutline.version.desc())
        .first()
    )


# --- Plot Node Update Helpers (for DM tools / APIs) ---


ALLOWED_NODE_STATUSES = {"Pending", "InProgress", "Finish", "Canceled"}


def update_plot_node_status(
    db: Session,
    story_id: int,
    node_index: int,
    new_status: str,
) -> models.PlotOutline | None:
    """
    Update status for a specific plot node in the active outline of a story.
    """
    if new_status not in ALLOWED_NODE_STATUSES:
        raise ValueError(f"Invalid node status '{new_status}'")

    outline = get_active_plot_outline(db, story_id=story_id)
    if outline is None:
        return None

    nodes_raw = outline.nodes or []
    if not isinstance(nodes_raw, list):
        return None

    nodes = list(nodes_raw)
    found = False
    for node in nodes:
        if int(node.get("index", 0)) == int(node_index):
            node["status"] = new_status
            found = True
            break

    if not found:
        return None

    setattr(outline, "nodes", nodes)
    attributes.flag_modified(outline, "nodes")
    db.commit()
    db.refresh(outline)
    return outline


def mark_plot_node_as_ending(
    db: Session,
    story_id: int,
    node_index: int,
    is_ending: bool,
) -> models.PlotOutline | None:
    """
    Mark / unmark a specific plot node as an ending node in the active outline.
    """
    outline = get_active_plot_outline(db, story_id=story_id)
    if outline is None:
        return None

    nodes_raw = outline.nodes or []
    if not isinstance(nodes_raw, list):
        return None

    nodes = list(nodes_raw)
    found = False
    for node in nodes:
        if int(node.get("index", 0)) == int(node_index):
            node["is_ending"] = bool(is_ending)
            found = True
            break

    if not found:
        return None

    setattr(outline, "nodes", nodes)
    attributes.flag_modified(outline, "nodes")
    db.commit()
    db.refresh(outline)
    return outline


# --- 配置存取 ---


def get_config_entry(db: Session, key: str) -> models.ConfigEntry | None:
    """按键名读取配置项。"""
    return db.query(models.ConfigEntry).filter(models.ConfigEntry.key == key).first()


def upsert_config_entry(db: Session, key: str, value: str | None) -> models.ConfigEntry:
    """
    新增或更新配置项。

    Args:
        db: 数据库会话
        key: 配置键
        value: 配置值，可为 None
    """
    entry = get_config_entry(db, key)
    if entry:
        entry.value = value
    else:
        entry = models.ConfigEntry(key=key, value=value)
        db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_config_entries(db: Session):
    """返回所有配置项列表。"""
    return db.query(models.ConfigEntry).all()
