"""
Progen Projects Router
제안서 프로젝트 CRUD + 콘텐츠/버전 API
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from schemas.progen import (
    ProgenProjectCreate,
    ProgenProjectUpdate,
    ProgenProjectResponse,
    ProgenProjectListResponse,
    ProgenContentSave,
    ProgenContentResponse,
    ProgenContentListResponse,
    ProgenVersionInfo,
    SuccessResponse,
)
from services.progen_db import (
    create_progen_project,
    list_progen_projects,
    get_progen_project,
    update_progen_project,
    delete_progen_project,
    update_progen_project_status,
    get_progen_file_count,
    get_next_version,
    save_progen_content,
    get_progen_content,
    get_progen_versions,
)
from services.ftp import Cafe24FTP

router = APIRouter(prefix="/api/progen", tags=["progen-projects"])


# ============================================================
# Project CRUD
# ============================================================

@router.post("/projects", response_model=ProgenProjectResponse)
async def create_project(data: ProgenProjectCreate):
    """프로젝트 생성 + FTP 폴더 생성"""
    try:
        project = create_progen_project(data.model_dump())
        if not project:
            raise HTTPException(status_code=500, detail="프로젝트 생성 실패")

        # FTP 폴더 생성
        try:
            with Cafe24FTP() as ftp:
                ftp.ensure_dir(f"{project['ftp_path']}/files")
        except Exception as ftp_err:
            print(f"Progen FTP folder creation warning: {ftp_err}")

        file_count = get_progen_file_count(project["id"])
        return ProgenProjectResponse(
            id=project["id"],
            name=project["name"],
            client_name=project.get("client_name"),
            exhibition_name=project.get("exhibition_name"),
            booth_size=project.get("booth_size"),
            requirements=project.get("requirements"),
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


@router.get("/projects", response_model=ProgenProjectListResponse)
async def get_projects(
    user_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    """프로젝트 목록 조회"""
    try:
        projects = list_progen_projects(user_id, search, status)
        project_list = []
        for p in projects:
            file_count = get_progen_file_count(p["id"])
            project_list.append(ProgenProjectResponse(
                id=p["id"],
                name=p["name"],
                client_name=p.get("client_name"),
                exhibition_name=p.get("exhibition_name"),
                booth_size=p.get("booth_size"),
                requirements=p.get("requirements"),
                ftp_path=p.get("ftp_path"),
                status=p.get("status", "draft"),
                user_id=p["user_id"],
                created_at=p.get("created_at"),
                updated_at=p.get("updated_at"),
                file_count=file_count,
            ))
        return ProgenProjectListResponse(projects=project_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}", response_model=ProgenProjectResponse)
async def get_project_detail(project_id: str):
    """프로젝트 상세 조회"""
    try:
        project = get_progen_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        file_count = get_progen_file_count(project_id)
        return ProgenProjectResponse(
            id=project["id"],
            name=project["name"],
            client_name=project.get("client_name"),
            exhibition_name=project.get("exhibition_name"),
            booth_size=project.get("booth_size"),
            requirements=project.get("requirements"),
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


@router.put("/projects/{project_id}", response_model=ProgenProjectResponse)
async def update_project(project_id: str, data: ProgenProjectUpdate):
    """프로젝트 수정"""
    try:
        existing = get_progen_project(project_id)
        if not existing:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        updated = update_progen_project(project_id, data.model_dump(exclude_none=True))
        file_count = get_progen_file_count(project_id)
        return ProgenProjectResponse(
            id=updated["id"],
            name=updated["name"],
            client_name=updated.get("client_name"),
            exhibition_name=updated.get("exhibition_name"),
            booth_size=updated.get("booth_size"),
            requirements=updated.get("requirements"),
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
        project = get_progen_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        # FTP 폴더 삭제
        ftp_path = project.get("ftp_path")
        if ftp_path:
            try:
                with Cafe24FTP() as ftp:
                    ftp.delete_directory(ftp_path)
            except Exception as ftp_err:
                print(f"Progen FTP delete warning: {ftp_err}")

        # DB 삭제 (CASCADE로 files, contents 자동 삭제)
        delete_progen_project(project_id)

        return SuccessResponse(success=True, message="프로젝트가 삭제되었습니다")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Content / Version API
# ============================================================

@router.get("/projects/{project_id}/content", response_model=ProgenContentListResponse)
async def get_content(
    project_id: str,
    version: Optional[int] = Query(None),
):
    """콘텐츠 조회 (최신 or 특정 버전) + 버전 목록"""
    try:
        project = get_progen_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        # 현재 콘텐츠
        content_data = get_progen_content(project_id, version)
        current = None
        if content_data:
            current = ProgenContentResponse(
                id=content_data["id"],
                project_id=content_data["project_id"],
                version=content_data.get("version", 1),
                html=content_data["html"],
                raw_html=content_data["raw_html"],
                ftp_url=content_data.get("ftp_url"),
                conversation_history=content_data.get("conversation_history", []),
                created_at=content_data.get("created_at"),
                updated_at=content_data.get("updated_at"),
            )

        # 버전 목록
        versions_data = get_progen_versions(project_id)
        versions = [
            ProgenVersionInfo(
                version=v["version"],
                created_at=v.get("created_at"),
                ftp_url=v.get("ftp_url"),
            )
            for v in versions_data
        ]

        return ProgenContentListResponse(current=current, versions=versions)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/content", response_model=ProgenContentResponse)
async def save_content(project_id: str, data: ProgenContentSave):
    """새 버전 저장 + FTP 업로드"""
    try:
        project = get_progen_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        ftp_path = project.get("ftp_path", "")
        version = get_next_version(project_id)

        # FTP에 HTML 저장
        ftp_url = None
        if ftp_path:
            try:
                html_bytes = data.html.encode("utf-8")
                remote_path = f"{ftp_path}/v{version}/proposal.html"
                with Cafe24FTP() as ftp:
                    ftp_url = ftp.upload_bytes(html_bytes, remote_path)
            except Exception as ftp_err:
                print(f"Progen content FTP upload warning: {ftp_err}")

        # DB 저장
        content = save_progen_content(
            project_id=project_id,
            version=version,
            html=data.html,
            raw_html=data.raw_html,
            ftp_url=ftp_url,
            conversation_history=data.conversation_history,
        )

        # 프로젝트 상태 업데이트
        update_progen_project_status(project_id, "generated")

        return ProgenContentResponse(
            id=content["id"],
            project_id=content["project_id"],
            version=content.get("version", version),
            html=content["html"],
            raw_html=content["raw_html"],
            ftp_url=content.get("ftp_url"),
            conversation_history=content.get("conversation_history", []),
            created_at=content.get("created_at"),
            updated_at=content.get("updated_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
