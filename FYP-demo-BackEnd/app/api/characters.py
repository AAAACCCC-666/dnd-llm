# app/api/characters.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import schemas
from ..db import crud, database
from ..utils.logger import get_logger

# from ..utils.read_data import load_dnd_data  # No longer needed

router = APIRouter()
logger = get_logger(__name__)


@router.get("/dnd-data", response_model=schemas.DndDataResponse)
def get_all_dnd_choices(db: Session = Depends(database.get_db)):
    """
    提供给前端用于构建角色创建表单的所有选项数据。
    """
    dnd_data = crud.get_all_dnd_static_data(db)
    if not dnd_data:
        raise HTTPException(
            status_code=500,
            detail="Failed to load D&D data from database. Check server logs.",
        )
    # The data from crud function should already be in the correct format.
    return schemas.DndDataResponse(**dnd_data)


@router.post("", response_model=schemas.Character, status_code=201)
def create_new_character(
    character_in: schemas.CharacterCreate, db: Session = Depends(database.get_db)
):
    """
    接收前端收集的所有信息，创建一个新角色。
    """
    # 检查 session_id 是否存在
    session = crud.get_session(db, session_id=character_in.session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session with id {character_in.session_id} not found.",
        )

    # dnd_data is now fetched inside the create_character function or passed differently
    # For now, let's assume create_character will be adapted or we fetch it here.
    # 调用 crud 函数处理所有复杂的创建逻辑
    new_character = crud.create_character(db=db, character_data=character_in)
    return new_character


@router.get("", response_model=List[schemas.Character])
def get_all_characters(
    skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)
):
    """
    获取所有已创建的角色列表。
    """
    characters = crud.get_characters(db, skip=skip, limit=limit)
    return characters


@router.get("/session/{session_id}", response_model=List[schemas.Character])
def get_characters_by_session(
    session_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(database.get_db),
):
    """
    获取与指定 session_id 关联的所有角色列表。
    """
    # 首先检查会话是否存在
    session = crud.get_session(db, session_id=session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found or no characters associated with this session",
        )

    characters = crud.get_characters_by_session_id(
        db, session_id=session_id, skip=skip, limit=limit
    )
    # 如果会话存在但没有角色，也应该返回404，或者根据需求返回空列表
    # 根据API文档，如果会话存在但没有角色，也应返回404
    if not characters:
        raise HTTPException(
            status_code=404,
            detail="Session not found or no characters associated with this session",
        )
    return characters


@router.get("/id/{character_id}", response_model=schemas.Character)
def get_character_by_id(character_id: str, db: Session = Depends(database.get_db)):
    """
    根据角色的 UUID 获取单个角色的详细信息。
    """
    db_character = crud.get_character_by_id(db, character_id=character_id)
    if db_character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return db_character


@router.get("/{name}", response_model=schemas.Character)
def get_character(name: str, db: Session = Depends(database.get_db)):
    """
    根据名称获取单个角色的详细信息。
    """
    logger.warning(
        "Deprecated endpoint /api/characters/{name} 被调用，角色名称: %s。请尽快迁移到 /api/characters/id/{character_id}。",
        name,
    )
    db_character = crud.get_character_by_name(db, name=name)
    if db_character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return db_character
