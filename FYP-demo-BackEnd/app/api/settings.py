from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.db import database
from app.services import settings_service

router = APIRouter()


@router.get("", response_model=schemas.ConfigUpdateRequest)
def list_settings(db: Session = Depends(database.get_db)):
    """
    获取当前的可配置项（数据库优先，缺失时回退环境变量）。
    """
    settings_map = settings_service.get_settings_map(db, settings_service.CONFIG_KEYS)
    return schemas.ConfigUpdateRequest(**settings_map)


@router.put("", response_model=schemas.ConfigUpdateRequest)
def update_settings(
    payload: schemas.ConfigUpdateRequest, db: Session = Depends(database.get_db)
):
    """
    更新指定配置项；允许传入 None 清空对应值。
    返回更新后的完整配置列表。
    """
    values = payload.model_dump(exclude_unset=True, exclude_none=False)
    settings_service.update_settings(db, values)
    latest = settings_service.get_settings_map(db, settings_service.CONFIG_KEYS)
    return schemas.ConfigUpdateRequest(**latest)
