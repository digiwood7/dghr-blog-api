"""
Settings Router
사용자 설정 관리 API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from services.database import get_settings, save_settings

router = APIRouter(prefix="/api/blog/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    user_id: str
    value: Any


@router.get("/{key}")
async def read_settings(key: str, user_id: str):
    """설정 조회"""
    value = get_settings(user_id, key, None)
    return {"key": key, "value": value}


@router.put("/{key}")
async def update_settings(key: str, data: SettingsUpdate):
    """설정 저장"""
    try:
        save_settings(data.user_id, key, data.value)
        return {"success": True, "key": key, "value": data.value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"설정 저장 실패: {str(e)}")
