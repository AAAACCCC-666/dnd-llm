from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List

from .. import schemas
from ..db import crud, database

router = APIRouter()


@router.post("", response_model=schemas.ChatSession)
def create_session(
    session_create: schemas.ChatSessionCreate, db: Session = Depends(database.get_db)
):
    return crud.create_chat_session(db=db, session=session_create)


@router.get("", response_model=List[schemas.ChatSession])
def read_sessions(
    skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)
):
    sessions = crud.get_sessions(db, skip=skip, limit=limit)
    return sessions


@router.get("/{session_id}", response_model=schemas.ChatSession)
def read_session(session_id: str, db: Session = Depends(database.get_db)):
    db_session = crud.get_session(db, session_id=session_id)
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    # The is_main_character_exist field is now handled in crud.get_session
    return db_session


@router.delete("/{session_id}")
def delete_session(session_id: str, db: Session = Depends(database.get_db)):
    try:
        deleted = crud.delete_session_with_dependencies(db, session_id=session_id)
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="删除失败")

    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"message": "Session deleted successfully"}
