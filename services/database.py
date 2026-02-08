"""
Database Service
Supabase DB 작업 함수
"""
import os
from supabase import create_client, Client
from .ftp import generate_ftp_path


def get_supabase() -> Client:
    """Supabase 클라이언트 생성"""
    url = os.getenv("NEXT_PUBLIC_SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
    return create_client(url, key)


# ============================================================
# Project Operations
# ============================================================

def create_project(name: str, user_id: str) -> dict:
    """프로젝트 생성"""
    supabase = get_supabase()
    # 먼저 프로젝트 생성 (ftp_path 없이)
    data = {
        "name": name,
        "user_id": user_id,
        "status": "draft",
    }
    result = supabase.table("blog_projects").insert(data).execute()
    if not result.data:
        return {}

    # 생성된 project_id로 ftp_path 생성 후 업데이트
    project = result.data[0]
    project_id = project["id"]
    ftp_path = generate_ftp_path(project_id)

    supabase.table("blog_projects").update({"ftp_path": ftp_path}).eq("id", project_id).execute()
    project["ftp_path"] = ftp_path
    return project


def list_projects(user_id: str = None) -> list[dict]:
    """프로젝트 목록 조회 (photo_count 포함, 단일 쿼리)"""
    supabase = get_supabase()
    query = supabase.table("blog_projects").select("*, blog_photos(count)")
    if user_id:
        query = query.eq("user_id", user_id)
    result = query.order("created_at", desc=True).execute()
    projects = result.data or []
    # blog_photos(count) → photo_count로 변환
    for p in projects:
        photos_agg = p.pop("blog_photos", None)
        if photos_agg and isinstance(photos_agg, list) and len(photos_agg) > 0:
            p["photo_count"] = photos_agg[0].get("count", 0)
        else:
            p["photo_count"] = 0
    return projects


def get_project(project_id: str) -> dict:
    """프로젝트 상세 조회"""
    supabase = get_supabase()
    result = supabase.table("blog_projects").select("*").eq("id", project_id).single().execute()
    return result.data or {}


def delete_project(project_id: str) -> bool:
    """프로젝트 삭제 (photos, contents는 CASCADE로 자동 삭제)"""
    supabase = get_supabase()
    supabase.table("blog_projects").delete().eq("id", project_id).execute()
    return True


def update_project_status(project_id: str, status: str):
    """프로젝트 상태 업데이트"""
    supabase = get_supabase()
    supabase.table("blog_projects").update({"status": status}).eq("id", project_id).execute()


# ============================================================
# Photo Operations
# ============================================================

def add_photo(project_id: str, filename: str, ftp_url: str, caption: str = "", category: str = "기타") -> dict:
    """사진 추가 (display_order 자동 설정)"""
    supabase = get_supabase()
    # 기존 사진의 최대 display_order 조회
    existing = supabase.table("blog_photos").select("display_order").eq("project_id", project_id).order("display_order", desc=True).limit(1).execute()
    max_order = existing.data[0]["display_order"] if existing.data and existing.data[0].get("display_order") else 0
    data = {
        "project_id": project_id,
        "filename": filename,
        "ftp_url": ftp_url,
        "caption": caption,
        "category": category,
        "display_order": max_order + 1,
    }
    result = supabase.table("blog_photos").insert(data).execute()
    return result.data[0] if result.data else {}


def get_photos(project_id: str) -> list[dict]:
    """프로젝트 사진 목록 조회 (display_order 순)"""
    supabase = get_supabase()
    result = supabase.table("blog_photos").select("*").eq("project_id", project_id).order("display_order").order("created_at").execute()
    return result.data or []


def get_photo_count(project_id: str) -> int:
    """프로젝트 사진 수 조회"""
    supabase = get_supabase()
    result = supabase.table("blog_photos").select("id", count="exact").eq("project_id", project_id).execute()
    return result.count or 0


def get_photo(photo_id: str) -> dict:
    """사진 상세 조회"""
    supabase = get_supabase()
    result = supabase.table("blog_photos").select("*").eq("id", photo_id).single().execute()
    return result.data or {}


def update_photo(photo_id: str, caption: str = None, category: str = None, display_order: int = None) -> dict:
    """사진 캡션/카테고리/순서 업데이트"""
    supabase = get_supabase()
    data = {}
    if caption is not None:
        data["caption"] = caption
    if category is not None:
        data["category"] = category
    if display_order is not None:
        data["display_order"] = display_order
    if data:
        result = supabase.table("blog_photos").update(data).eq("id", photo_id).execute()
        return result.data[0] if result.data else {}
    return {}


def reorder_photos(project_id: str, photo_ids: list[str]) -> bool:
    """사진 순서 일괄 업데이트"""
    supabase = get_supabase()
    for index, photo_id in enumerate(photo_ids):
        supabase.table("blog_photos").update({"display_order": index + 1}).eq("id", photo_id).eq("project_id", project_id).execute()
    return True


def search_photos(category: str = None, keyword: str = None, date_from: str = None, date_to: str = None, page: int = 1, page_size: int = 20) -> dict:
    """사진 검색 (카테고리, 키워드, 날짜 범위, 페이징)

    Returns: {"photos": list[dict], "total": int, "page": int, "page_size": int, "total_pages": int}
    """
    supabase = get_supabase()
    query = supabase.table("blog_photos").select("*, blog_projects(name)", count="exact")
    if category:
        query = query.eq("category", category)
    if keyword:
        query = query.or_(f"caption.ilike.*{keyword}*,filename.ilike.*{keyword}*")
    if date_from:
        query = query.gte("created_at", f"{date_from}T00:00:00")
    if date_to:
        query = query.lte("created_at", f"{date_to}T23:59:59")

    # 총 개수 조회를 위해 먼저 실행
    offset = (page - 1) * page_size
    result = query.order("created_at", desc=True).range(offset, offset + page_size - 1).execute()
    total = result.count or 0
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return {
        "photos": result.data or [],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def delete_photo(photo_id: str) -> bool:
    """사진 삭제"""
    supabase = get_supabase()
    supabase.table("blog_photos").delete().eq("id", photo_id).execute()
    return True


# ============================================================
# Content Operations
# ============================================================

def save_content(project_id: str, title: str, content_html: str, tags: list) -> dict:
    """생성된 글 저장 (upsert)"""
    supabase = get_supabase()
    # 기존 콘텐츠가 있으면 업데이트, 없으면 삽입
    existing = supabase.table("blog_contents").select("id").eq("project_id", project_id).execute()
    data = {
        "project_id": project_id,
        "title": title,
        "content_html": content_html,
        "tags": tags,
    }
    if existing.data:
        result = supabase.table("blog_contents").update(data).eq("project_id", project_id).execute()
    else:
        result = supabase.table("blog_contents").insert(data).execute()
    return result.data[0] if result.data else {}


def get_content(project_id: str) -> dict:
    """프로젝트의 생성된 글 조회"""
    supabase = get_supabase()
    result = supabase.table("blog_contents").select("*").eq("project_id", project_id).execute()
    if result.data:
        return {
            "id": result.data[0].get("id"),
            "project_id": result.data[0].get("project_id"),
            "title": result.data[0].get("title", ""),
            "content_html": result.data[0].get("content_html", ""),
            "tags": result.data[0].get("tags", []),
            "created_at": result.data[0].get("created_at"),
            "updated_at": result.data[0].get("updated_at"),
        }
    return {}


# ============================================================
# Settings Operations
# ============================================================

def get_settings(user_id: str, key: str, default=None):
    """사용자 설정 조회"""
    try:
        supabase = get_supabase()
        result = supabase.table("blog_settings").select("setting_value").eq("user_id", user_id).eq("setting_key", key).execute()
        if result.data:
            return result.data[0].get("setting_value", default)
    except:
        pass
    return default


def save_settings(user_id: str, key: str, value):
    """사용자 설정 저장 (upsert)"""
    supabase = get_supabase()
    data = {
        "user_id": user_id,
        "setting_key": key,
        "setting_value": value,
    }
    # upsert 사용 (있으면 업데이트, 없으면 삽입)
    supabase.table("blog_settings").upsert(data, on_conflict="user_id,setting_key").execute()


# ============================================================
# Reference URL Operations
# ============================================================

def get_reference_urls(user_id: str) -> list[dict]:
    """사용자의 참고 URL 목록 조회"""
    try:
        supabase = get_supabase()
        result = supabase.table("blog_reference_urls").select("*").eq("user_id", user_id).eq("is_active", True).order("created_at").execute()
        return result.data or []
    except:
        return []


def add_reference_url(user_id: str, url: str, title: str = "", description: str = "") -> dict:
    """참고 URL 추가"""
    supabase = get_supabase()
    data = {
        "user_id": user_id,
        "url": url,
        "title": title,
        "description": description,
        "is_active": True,
    }
    result = supabase.table("blog_reference_urls").insert(data).execute()
    return result.data[0] if result.data else {}


def update_reference_url(url_id: str, title: str = None, description: str = None, is_active: bool = None) -> dict:
    """참고 URL 수정"""
    supabase = get_supabase()
    data = {}
    if title is not None:
        data["title"] = title
    if description is not None:
        data["description"] = description
    if is_active is not None:
        data["is_active"] = is_active
    if data:
        result = supabase.table("blog_reference_urls").update(data).eq("id", url_id).execute()
        return result.data[0] if result.data else {}
    return {}


def delete_reference_url(url_id: str) -> bool:
    """참고 URL 삭제"""
    supabase = get_supabase()
    supabase.table("blog_reference_urls").delete().eq("id", url_id).execute()
    return True
