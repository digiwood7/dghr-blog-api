"""
Progen Pydantic Schemas
제안서 자동생성 Request/Response 모델
"""
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


# ============================================================
# Project Schemas
# ============================================================

class ProgenProjectCreate(BaseModel):
    """프로젝트 생성 요청"""
    name: str
    client_name: Optional[str] = None
    exhibition_name: Optional[str] = None
    booth_size: Optional[str] = None
    requirements: Optional[str] = None
    user_id: str


class ProgenProjectUpdate(BaseModel):
    """프로젝트 수정 요청"""
    name: Optional[str] = None
    client_name: Optional[str] = None
    exhibition_name: Optional[str] = None
    booth_size: Optional[str] = None
    requirements: Optional[str] = None
    status: Optional[str] = None


class ProgenProjectResponse(BaseModel):
    """프로젝트 응답"""
    id: str
    name: str
    client_name: Optional[str] = None
    exhibition_name: Optional[str] = None
    booth_size: Optional[str] = None
    requirements: Optional[str] = None
    ftp_path: Optional[str] = None
    status: str = "draft"
    user_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    file_count: Optional[int] = None


class ProgenProjectListResponse(BaseModel):
    """프로젝트 목록 응답"""
    projects: list[ProgenProjectResponse]


# ============================================================
# File Schemas
# ============================================================

class ProgenFileResponse(BaseModel):
    """파일 응답"""
    id: str
    project_id: str
    filename: str
    original_name: str
    ftp_url: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    created_at: Optional[datetime] = None


class ProgenFileListResponse(BaseModel):
    """파일 목록 응답"""
    files: list[ProgenFileResponse]


# ============================================================
# Content / Version Schemas
# ============================================================

class ProgenContentSave(BaseModel):
    """콘텐츠 저장 요청"""
    html: str
    raw_html: str
    conversation_history: Optional[list[dict]] = []


class ProgenContentResponse(BaseModel):
    """콘텐츠 응답"""
    id: str
    project_id: str
    version: int
    html: str
    raw_html: str
    ftp_url: Optional[str] = None
    conversation_history: Optional[list[dict]] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProgenVersionInfo(BaseModel):
    """버전 목록용 경량 모델"""
    version: int
    created_at: Optional[datetime] = None
    ftp_url: Optional[str] = None


class ProgenContentListResponse(BaseModel):
    """현재 콘텐츠 + 버전 목록"""
    current: Optional[ProgenContentResponse] = None
    versions: list[ProgenVersionInfo] = []


# ============================================================
# Common Schemas
# ============================================================

class SuccessResponse(BaseModel):
    """성공 응답"""
    success: bool = True
    message: Optional[str] = None
