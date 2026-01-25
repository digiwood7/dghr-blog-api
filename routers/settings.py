"""
Settings Router
사용자 설정 및 참고 URL 관리 API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Optional

from services.database import (
    get_settings,
    save_settings,
    get_reference_urls,
    add_reference_url,
    update_reference_url,
    delete_reference_url,
)

router = APIRouter(prefix="/api/blog", tags=["settings"])


# ============================================================
# Settings Models
# ============================================================

class SettingsUpdate(BaseModel):
    user_id: str
    value: Any


class ReferenceUrlCreate(BaseModel):
    user_id: str
    url: str
    title: Optional[str] = ""
    description: Optional[str] = ""


class ReferenceUrlUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


# ============================================================
# Settings Endpoints
# ============================================================

@router.get("/settings/{key}")
async def read_settings(key: str, user_id: str):
    """설정 조회"""
    value = get_settings(user_id, key, None)
    return {"key": key, "value": value}


@router.put("/settings/{key}")
async def update_settings(key: str, data: SettingsUpdate):
    """설정 저장"""
    try:
        save_settings(data.user_id, key, data.value)
        return {"success": True, "key": key, "value": data.value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"설정 저장 실패: {str(e)}")


# ============================================================
# Reference URL Endpoints
# ============================================================

@router.get("/reference-urls")
async def list_reference_urls(user_id: str):
    """참고 URL 목록 조회"""
    urls = get_reference_urls(user_id)
    return {"urls": urls}


@router.post("/reference-urls")
async def create_reference_url(data: ReferenceUrlCreate):
    """참고 URL 추가"""
    try:
        url = add_reference_url(
            user_id=data.user_id,
            url=data.url,
            title=data.title or "",
            description=data.description or "",
        )
        return url
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"URL 추가 실패: {str(e)}")


@router.put("/reference-urls/{url_id}")
async def modify_reference_url(url_id: str, data: ReferenceUrlUpdate):
    """참고 URL 수정"""
    try:
        url = update_reference_url(
            url_id=url_id,
            title=data.title,
            description=data.description,
            is_active=data.is_active,
        )
        return url
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"URL 수정 실패: {str(e)}")


@router.delete("/reference-urls/{url_id}")
async def remove_reference_url(url_id: str):
    """참고 URL 삭제"""
    try:
        delete_reference_url(url_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"URL 삭제 실패: {str(e)}")
