"""
PPTX Projects Router
PPT 프로젝트 CRUD + 콘텐츠/버전 API
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from schemas.pptx import (
    PptxProjectCreate,
    PptxProjectUpdate,
    PptxProjectResponse,
    PptxProjectListResponse,
    PptxContentSave,
    PptxContentResponse,
    PptxContentListResponse,
    PptxVersionInfo,
    SuccessResponse,
)
from services.pptx_db import (
    create_pptx_project,
    list_pptx_projects,
    get_pptx_project,
    update_pptx_project,
    delete_pptx_project,
    update_pptx_project_status,
    get_pptx_file_count,
    get_next_pptx_version,
    save_pptx_content,
    get_pptx_content,
    get_pptx_versions,
    delete_pptx_content,
)
from services.ftp import Cafe24FTP

router = APIRouter(prefix="/api/pptx", tags=["pptx-projects"])


# ============================================================
# Project CRUD
# ============================================================

@router.post("/projects", response_model=PptxProjectResponse)
async def create_project(data: PptxProjectCreate):
    """프로젝트 생성 + FTP 폴더 생성"""
    try:
        project = create_pptx_project(data.model_dump())
        if not project:
            raise HTTPException(status_code=500, detail="프로젝트 생성 실패")

        # FTP 폴더 생성
        try:
            with Cafe24FTP() as ftp:
                ftp.ensure_dir(f"{project['ftp_path']}/files")
        except Exception as ftp_err:
            print(f"PPTX FTP folder creation warning: {ftp_err}")

        file_count = get_pptx_file_count(project["id"])
        return PptxProjectResponse(
            id=project["id"],
            name=project["name"],
            description=project.get("description"),
            style_id=project.get("style_id", 3),
            slide_count=project.get("slide_count", 15),
            ftp_path=project.get("ftp_path"),
            status=project.get("status", "draft"),
            user_id=project["user_id"],
            created_at=project.get("created_at"),
            updated_at=project.get("updated_at"),
            file_count=file_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects", response_model=PptxProjectListResponse)
async def get_projects(
    user_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    """프로젝트 목록 조회"""
    try:
        projects = list_pptx_projects(user_id, search, status)
        project_list = []
        for p in projects:
            project_list.append(PptxProjectResponse(
                id=p["id"],
                name=p["name"],
                description=p.get("description"),
                style_id=p.get("style_id", 3),
                slide_count=p.get("slide_count", 15),
                ftp_path=p.get("ftp_path"),
                status=p.get("status", "draft"),
                user_id=p["user_id"],
                created_at=p.get("created_at"),
                updated_at=p.get("updated_at"),
                file_count=p.get("file_count", 0),
            ))
        return PptxProjectListResponse(projects=project_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}", response_model=PptxProjectResponse)
async def get_project_detail(project_id: str):
    """프로젝트 상세 조회"""
    try:
        project = get_pptx_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        file_count = get_pptx_file_count(project_id)
        return PptxProjectResponse(
            id=project["id"],
            name=project["name"],
            description=project.get("description"),
            style_id=project.get("style_id", 3),
            slide_count=project.get("slide_count", 15),
            ftp_path=project.get("ftp_path"),
            status=project.get("status", "draft"),
            user_id=project["user_id"],
            created_at=project.get("created_at"),
            updated_at=project.get("updated_at"),
            file_count=file_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/projects/{project_id}", response_model=PptxProjectResponse)
async def update_project(project_id: str, data: PptxProjectUpdate):
    """프로젝트 수정"""
    try:
        existing = get_pptx_project(project_id)
        if not existing:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        updated = update_pptx_project(project_id, data.model_dump(exclude_none=True))
        file_count = get_pptx_file_count(project_id)
        return PptxProjectResponse(
            id=updated["id"],
            name=updated["name"],
            description=updated.get("description"),
            style_id=updated.get("style_id", 3),
            slide_count=updated.get("slide_count", 15),
            ftp_path=updated.get("ftp_path"),
            status=updated.get("status", "draft"),
            user_id=updated["user_id"],
            created_at=updated.get("created_at"),
            updated_at=updated.get("updated_at"),
            file_count=file_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/projects/{project_id}", response_model=SuccessResponse)
async def delete_project_endpoint(project_id: str):
    """프로젝트 삭제 + FTP 폴더 재귀 삭제"""
    try:
        project = get_pptx_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        # FTP 폴더 삭제
        ftp_path = project.get("ftp_path")
        if ftp_path:
            try:
                with Cafe24FTP() as ftp:
                    ftp.delete_directory(ftp_path)
            except Exception as ftp_err:
                print(f"PPTX FTP delete warning: {ftp_err}")

        # DB 삭제 (CASCADE로 files, contents 자동 삭제)
        delete_pptx_project(project_id)

        return SuccessResponse(success=True, message="프로젝트가 삭제되었습니다")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Content / Version API
# ============================================================

@router.get("/projects/{project_id}/content", response_model=PptxContentListResponse)
async def get_content(
    project_id: str,
    version: Optional[int] = Query(None),
):
    """콘텐츠 조회 (최신 or 특정 버전) + 버전 목록"""
    try:
        project = get_pptx_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        # 현재 콘텐츠
        content_data = get_pptx_content(project_id, version)
        current = None
        if content_data:
            current = PptxContentResponse(
                id=content_data["id"],
                project_id=content_data["project_id"],
                version=content_data.get("version", 1),
                pptx_ftp_url=content_data.get("pptx_ftp_url"),
                config_json=content_data.get("config_json"),
                prompt=content_data.get("prompt"),
                style_id=content_data.get("style_id"),
                slide_count=content_data.get("slide_count"),
                created_at=content_data.get("created_at"),
                updated_at=content_data.get("updated_at"),
            )

        # 버전 목록
        versions_data = get_pptx_versions(project_id)
        versions = [
            PptxVersionInfo(
                version=v["version"],
                created_at=v.get("created_at"),
                pptx_ftp_url=v.get("pptx_ftp_url"),
            )
            for v in versions_data
        ]

        return PptxContentListResponse(current=current, versions=versions)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/content", response_model=PptxContentResponse)
async def save_content(project_id: str, data: PptxContentSave):
    """새 버전 저장"""
    try:
        project = get_pptx_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        version = get_next_pptx_version(project_id)

        # DB 저장
        content = save_pptx_content(
            project_id=project_id,
            version=version,
            pptx_ftp_url=data.pptx_ftp_url,
            config_json=data.config_json,
            prompt=data.prompt,
            style_id=data.style_id,
            slide_count=data.slide_count,
        )

        # 프로젝트 상태 업데이트
        update_pptx_project_status(project_id, "generated")

        return PptxContentResponse(
            id=content["id"],
            project_id=content["project_id"],
            version=content.get("version", version),
            pptx_ftp_url=content.get("pptx_ftp_url"),
            config_json=content.get("config_json"),
            prompt=content.get("prompt"),
            style_id=content.get("style_id"),
            slide_count=content.get("slide_count"),
            created_at=content.get("created_at"),
            updated_at=content.get("updated_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/projects/{project_id}/content/{version}", response_model=SuccessResponse)
async def delete_content_version(project_id: str, version: int):
    """특정 버전 콘텐츠 삭제 + FTP 파일 삭제"""
    try:
        project = get_pptx_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        content_data = get_pptx_content(project_id, version)
        if not content_data:
            raise HTTPException(status_code=404, detail="해당 버전을 찾을 수 없습니다")

        # FTP 버전 폴더 삭제
        ftp_path = project.get("ftp_path")
        if ftp_path:
            try:
                with Cafe24FTP() as ftp:
                    ftp.delete_directory(f"{ftp_path}/v{version}")
            except Exception as ftp_err:
                print(f"PPTX content FTP delete warning: {ftp_err}")

        # DB 삭제
        delete_pptx_content(project_id, version)

        return SuccessResponse(success=True, message=f"V{version}이 삭제되었습니다")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
