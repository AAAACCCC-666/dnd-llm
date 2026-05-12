"""角色数据转换工具函数。"""

import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from ..db import models

logger = logging.getLogger(__name__)


def character_to_dict(
    character: Optional[models.Character], db: Session
) -> Optional[Dict[str, Any]]:
    """将角色模型转换为字典格式"""
    if not character:
        return None

    try:
        return {
            "id": character.id,
            "name": character.name,
            "level": character.level,
            "race": character.race.name if character.race else "Unknown",
            "class": character.dnd_class.name if character.dnd_class else "Unknown",
            "health": character.health,
            "temp_health": character.temp_health,
            "armor": character.armor,
            "speed": character.speed,
            "gold": character.gold,
            "experience": character.experience,
            "ability_scores": character.ability_scores or {},
            "strength": character.strength,
            "dexterity": character.dexterity,
            "constitution": character.constitution,
            "intelligence": character.intelligence,
            "wisdom": character.wisdom,
            "charisma": character.charisma,
            "strength_proficiency": character.strength_proficiency,
            "dexterity_proficiency": character.dexterity_proficiency,
            "constitution_proficiency": character.constitution_proficiency,
            "intelligence_proficiency": character.intelligence_proficiency,
            "wisdom_proficiency": character.wisdom_proficiency,
            "charisma_proficiency": character.charisma_proficiency,
            "spells": character.spells,
            "features": character.features,
            "proficiencies": character.proficiencies,
            "equipment": character.equipment or {},
            "inventory_items": character.inventory_items or {},
            "is_player": character.is_player,
            "is_male": character.is_male,
        }
    except Exception as e:
        logger.error(f"Error converting character to dict: {e}")
        return None


def character_to_string(character: models.Character, db: Session) -> str:
    """兼容性函数 - 将角色信息转换为 JSON 格式字符串"""
    character_data = character_to_dict(character, db)
    return json.dumps(character_data, ensure_ascii=False, indent=2)
