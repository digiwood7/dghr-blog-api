"""
PPTX Generator Pydantic Schemas
PPT 자동생성 Request/Response 모델
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ============================================================
# Project Schemas
# ============================================================

class PptxProjectCreate(BaseModel):
    """프로젝트 생성 요청"""
    name: str
    description: Optional[str] = None
    style_id: Optional[int] = 3
    slide_count: Optional[int] = 15
    user_id: str


class PptxProjectUpdate(BaseModel):
    """프로젝트 수정 요청"""
    name: Optional[str] = None
    description: Optional[str] = None
    style_id: Optional[int] = None
    slide_count: Optional[int] = None
    status: Optional[str] = None


class PptxProjectResponse(BaseModel):
    """프로젝트 응답"""
    id: str
    name: str
    description: Optional[str] = None
    style_id: Optional[int] = 3
    slide_count: Optional[int] = 15
    ftp_path: Optional[str] = None
    status: str = "draft"
    user_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    file_count: Optional[int] = None


class PptxProjectListResponse(BaseModel):
    """프로젝트 목록 응답"""
    projects: list[PptxProjectResponse]


# ============================================================
# File Schemas
# ============================================================

class PptxFileResponse(BaseModel):
    """파일 응답"""
    id: str
    project_id: str
    filename: str
    original_name: str
    ftp_url: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    created_at: Optional[datetime] = None


class PptxFileListResponse(BaseModel):
    """파일 목록 응답"""
    files: list[PptxFileResponse]


# ============================================================
# Content / Version Schemas
# ============================================================

class PptxContentSave(BaseModel):
    """콘텐츠 저장 요청"""
    pptx_ftp_url: Optional[str] = None
    config_json: Optional[dict] = None
    prompt: Optional[str] = None
    style_id: Optional[int] = None
    slide_count: Optional[int] = None


class PptxContentResponse(BaseModel):
    """콘텐츠 응답"""
    id: str
    project_id: str
    version: int
    pptx_ftp_url: Optional[str] = None
    config_json: Optional[dict] = None
    prompt: Optional[str] = None
    style_id: Optional[int] = None
    slide_count: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PptxVersionInfo(BaseModel):
    """버전 목록용 경량 모델"""
    version: int
    created_at: Optional[datetime] = None
    pptx_ftp_url: Optional[str] = None


class PptxContentListResponse(BaseModel):
    """현재 콘텐츠 + 버전 목록"""
    current: Optional[PptxContentResponse] = None
    versions: list[PptxVersionInfo] = []


# ============================================================
# Common Schemas (progen과 공유 가능하나 독립 유지)
# ============================================================

class SuccessResponse(BaseModel):
    """성공 응답"""
    success: bool = True
    message: Optional[str] = None
