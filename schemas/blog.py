"""
Blog Pydantic Schemas
Request/Response 모델 정의
"""
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


# ============================================================
# Project Schemas
# ============================================================

class ProjectCreate(BaseModel):
    """프로젝트 생성 요청"""
    name: str
    user_id: str


class ProjectUpdate(BaseModel):
    """프로젝트 수정 요청"""
    name: str


class ProjectResponse(BaseModel):
    """프로젝트 응답"""
    id: str
    name: str
    user_id: str
    ftp_path: Optional[str] = None
    status: str = "draft"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    generated_at: Optional[datetime] = None
    photo_count: Optional[int] = None


class ProjectListResponse(BaseModel):
    """프로젝트 목록 응답"""
    projects: list[ProjectResponse]


# ============================================================
# Photo Schemas
# ============================================================

class PhotoCreate(BaseModel):
    """사진 생성 (FTP 업로드 후 호출)"""
    filename: str
    ftp_url: str
    caption: Optional[str] = ""
    category: Optional[str] = "기타"


class PhotoUpdate(BaseModel):
    """사진 수정 요청"""
    caption: Optional[str] = None
    category: Optional[str] = None
    display_order: Optional[int] = None


class PhotoReorderRequest(BaseModel):
    """사진 순서 변경 요청"""
    photo_ids: list[str]


class PhotoResponse(BaseModel):
    """사진 응답"""
    id: str
    project_id: str
    filename: str
    ftp_url: Optional[str] = None
    caption: Optional[str] = ""
    category: Optional[str] = "기타"
    display_order: Optional[int] = 0
    created_at: Optional[datetime] = None


class PhotoListResponse(BaseModel):
    """사진 목록 응답"""
    photos: list[PhotoResponse]


# ============================================================
# Content Schemas
# ============================================================

class ContentResponse(BaseModel):
    """생성된 글 응답"""
    id: Optional[str] = None
    project_id: Optional[str] = None
    title: Optional[str] = ""
    content_html: Optional[str] = ""
    tags: Optional[list[str]] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ============================================================
# Generation Schemas
# ============================================================

class GenerateRequest(BaseModel):
    """AI 글 생성 요청"""
    keywords: Optional[list[str]] = []


class AnalysisResponse(BaseModel):
    """이미지 분석 결과"""
    suggested_title: Optional[str] = None
    overall_theme: Optional[str] = None
    main_keywords: Optional[list[str]] = []
    images: Optional[list[dict]] = []
    error: Optional[str] = None


class DebugUrlDetail(BaseModel):
    """참고 URL 디버그 정보"""
    url: str
    title: Optional[str] = ""
    success: bool
    content_length: int
    error: Optional[str] = ""
    preview: Optional[str] = ""


class DebugReferenceUrls(BaseModel):
    """참고 URL 전체 디버그"""
    urls_found: int = 0
    urls_fetched: int = 0
    url_details: Optional[list[DebugUrlDetail]] = []


class DebugPersona(BaseModel):
    """페르소나 디버그"""
    has_persona: bool = False
    persona_text: Optional[str] = ""
    persona_length: int = 0


class DebugPromptSections(BaseModel):
    """프롬프트 구성 디버그"""
    has_persona: bool = False
    has_reference: bool = False
    persona_preview: Optional[str] = ""
    reference_preview: Optional[str] = ""


class DebugInfo(BaseModel):
    """전체 디버그 정보"""
    timestamp: Optional[str] = None
    user_id: Optional[str] = None
    persona: Optional[DebugPersona] = None
    reference_urls: Optional[DebugReferenceUrls] = None
    prompt_sections: Optional[DebugPromptSections] = None
    full_prompt_length: int = 0
    model: Optional[str] = None


class GenerateResponse(BaseModel):
    """AI 글 생성 결과"""
    title: Optional[str] = None
    content_html: Optional[str] = None
    tags: Optional[list[str]] = []
    html_url: Optional[str] = None
    error: Optional[str] = None
    debug: Optional[dict] = None  # 디버그 정보


# ============================================================
# Settings Schemas
# ============================================================

class SettingsValue(BaseModel):
    """설정 값"""
    value: Any


class SettingsResponse(BaseModel):
    """설정 응답"""
    key: str
    value: Any


# ============================================================
# Common Schemas
# ============================================================

class SuccessResponse(BaseModel):
    """성공 응답"""
    success: bool = True
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """에러 응답"""
    success: bool = False
    error: str
