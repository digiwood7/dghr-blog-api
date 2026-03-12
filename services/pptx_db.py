"""
PPTX Database Service
Supabase pptx 테이블 작업 함수
"""
from datetime import datetime
from .database import get_supabase


def generate_pptx_ftp_path(project_id: str) -> str:
    """FTP 저장 경로 생성: /www/pptx/YYYY_MM_dd_{project_id}/"""
    date_prefix = datetime.now().strftime("%Y_%m_%d")
    return f"/www/pptx/{date_prefix}_{project_id}"


# ============================================================
# Project Operations
# ============================================================

def create_pptx_project(data: dict) -> dict:
    """프로젝트 생성 + ftp_path 자동 설정"""
    supabase = get_supabase()
    insert_data = {
        "name": data["name"],
        "user_id": data["user_id"],
        "status": "draft",
    }
    if data.get("description"):
        insert_data["description"] = data["description"]
    if data.get("style_id") is not None:
        insert_data["style_id"] = data["style_id"]
    if data.get("slide_count") is not None:
        insert_data["slide_count"] = data["slide_count"]

    result = supabase.table("pptx_projects").insert(insert_data).execute()
    if not result.data:
        return {}

    project = result.data[0]
    project_id = project["id"]
    ftp_path = generate_pptx_ftp_path(project_id)

    supabase.table("pptx_projects").update({"ftp_path": ftp_path}).eq("id", project_id).execute()
    project["ftp_path"] = ftp_path
    return project


def list_pptx_projects(user_id: str = None, search: str = None, status: str = None) -> list[dict]:
    """프로젝트 목록 조회 (file_count 포함)"""
    supabase = get_supabase()
    query = supabase.table("pptx_projects").select("*, pptx_files(count)")
    if user_id:
        query = query.eq("user_id", user_id)
    if search:
        query = query.or_(f"name.ilike.%{search}%,description.ilike.%{search}%")
    if status:
        query = query.eq("status", status)
    result = query.order("created_at", desc=True).execute()
    projects = result.data or []
    for p in projects:
        files_agg = p.pop("pptx_files", None)
        if files_agg and isinstance(files_agg, list) and len(files_agg) > 0:
            p["file_count"] = files_agg[0].get("count", 0)
        else:
            p["file_count"] = 0
    return projects


def get_pptx_project(project_id: str) -> dict:
    """프로젝트 상세 조회"""
    supabase = get_supabase()
    result = supabase.table("pptx_projects").select("*").eq("id", project_id).single().execute()
    return result.data or {}


def update_pptx_project(project_id: str, data: dict) -> dict:
    """프로젝트 수정"""
    supabase = get_supabase()
    updates = {}
    for key in ["name", "description", "style_id", "slide_count", "status"]:
        if key in data and data[key] is not None:
            updates[key] = data[key]
    if not updates:
        return get_pptx_project(project_id)
    supabase.table("pptx_projects").update(updates).eq("id", project_id).execute()
    return get_pptx_project(project_id)


def delete_pptx_project(project_id: str) -> bool:
    """프로젝트 삭제 (CASCADE로 files, contents 자동 삭제)"""
    supabase = get_supabase()
    supabase.table("pptx_projects").delete().eq("id", project_id).execute()
    return True


def update_pptx_project_status(project_id: str, status: str):
    """프로젝트 상태 업데이트"""
    supabase = get_supabase()
    supabase.table("pptx_projects").update({"status": status}).eq("id", project_id).execute()


# ============================================================
# File Operations
# ============================================================

def add_pptx_file(project_id: str, filename: str, original_name: str,
                  ftp_url: str, file_type: str = None, file_size: int = None) -> dict:
    """파일 메타데이터 추가"""
    supabase = get_supabase()
    data = {
        "project_id": project_id,
        "filename": filename,
        "original_name": original_name,
        "ftp_url": ftp_url,
        "file_type": file_type,
        "file_size": file_size,
    }
    result = supabase.table("pptx_files").insert(data).execute()
    return result.data[0] if result.data else {}


def get_pptx_files(project_id: str) -> list[dict]:
    """프로젝트 파일 목록 조회"""
    supabase = get_supabase()
    result = supabase.table("pptx_files").select("*").eq("project_id", project_id).order("created_at").execute()
    return result.data or []


def get_pptx_file(file_id: str) -> dict:
    """파일 상세 조회"""
    supabase = get_supabase()
    result = supabase.table("pptx_files").select("*").eq("id", file_id).single().execute()
    return result.data or {}


def get_pptx_file_count(project_id: str) -> int:
    """프로젝트 파일 수 조회"""
    supabase = get_supabase()
    result = supabase.table("pptx_files").select("id", count="exact").eq("project_id", project_id).execute()
    return result.count or 0


def delete_pptx_file(file_id: str) -> bool:
    """파일 삭제"""
    supabase = get_supabase()
    supabase.table("pptx_files").delete().eq("id", file_id).execute()
    return True


# ============================================================
# Content / Version Operations
# ============================================================

def get_next_pptx_version(project_id: str) -> int:
    """다음 버전 번호 계산"""
    supabase = get_supabase()
    result = supabase.table("pptx_contents").select("version").eq("project_id", project_id).order("version", desc=True).limit(1).execute()
    if result.data:
        return result.data[0]["version"] + 1
    return 1


def save_pptx_content(project_id: str, version: int, pptx_ftp_url: str = None,
                      config_json: dict = None, prompt: str = None,
                      style_id: int = None, slide_count: int = None) -> dict:
    """콘텐츠 새 버전 INSERT"""
    supabase = get_supabase()
    data = {
        "project_id": project_id,
        "version": version,
        "pptx_ftp_url": pptx_ftp_url,
        "config_json": config_json,
        "prompt": prompt,
        "style_id": style_id,
        "slide_count": slide_count,
    }
    result = supabase.table("pptx_contents").insert(data).execute()
    return result.data[0] if result.data else {}


def get_pptx_content(project_id: str, version: int = None) -> dict:
    """특정 버전 또는 최신 버전 조회"""
    supabase = get_supabase()
    query = supabase.table("pptx_contents").select("*").eq("project_id", project_id)
    if version is not None:
        query = query.eq("version", version)
    else:
        query = query.order("version", desc=True).limit(1)

    result = query.execute()
    if result.data:
        return result.data[0]
    return {}


def delete_pptx_content(project_id: str, version: int) -> bool:
    """특정 버전 콘텐츠 삭제"""
    supabase = get_supabase()
    supabase.table("pptx_contents").delete().eq("project_id", project_id).eq("version", version).execute()
    return True


def get_pptx_versions(project_id: str) -> list[dict]:
    """버전 목록 조회 (version, created_at, pptx_ftp_url)"""
    supabase = get_supabase()
    result = supabase.table("pptx_contents").select("version, created_at, pptx_ftp_url").eq("project_id", project_id).order("version", desc=True).execute()
    return result.data or []
