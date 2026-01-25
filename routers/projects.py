"""
Projects Router
프로젝트 CRUD API 엔드포인트
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from schemas.blog import (
    ProjectCreate,
    ProjectResponse,
    ProjectListResponse,
    SuccessResponse,
)
from services.database import (
    create_project,
    list_projects,
    get_project,
    delete_project,
    get_photo_count,
)
from services.ftp import Cafe24FTP

router = APIRouter(prefix="/api/blog/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse)
async def create_new_project(data: ProjectCreate):
    """프로젝트 생성"""
    try:
        project = create_project(data.name, data.user_id)
        if not project:
            raise HTTPException(status_code=500, detail="프로젝트 생성 실패")

        # FTP 폴더 생성
        try:
            with Cafe24FTP() as ftp:
                ftp.ensure_dir(f"{project['ftp_path']}/images")
                ftp.ensure_dir(f"{project['ftp_path']}/drafts")
        except Exception as ftp_err:
            print(f"FTP folder creation warning: {ftp_err}")

        return ProjectResponse(
            id=project["id"],
            name=project["name"],
            user_id=project["user_id"],
            ftp_path=project.get("ftp_path"),
            status=project.get("status", "draft"),
            created_at=project.get("created_at"),
            updated_at=project.get("updated_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=ProjectListResponse)
async def get_projects(user_id: str = Query(..., description="사용자 ID")):
    """프로젝트 목록 조회"""
    try:
        projects = list_projects(user_id)
        project_list = []
        for p in projects:
            photo_count = get_photo_count(p.get("id", ""))
            project_list.append(ProjectResponse(
                id=p["id"],
                name=p["name"],
                user_id=p["user_id"],
                ftp_path=p.get("ftp_path"),
                status=p.get("status", "draft"),
                created_at=p.get("created_at"),
                updated_at=p.get("updated_at"),
                photo_count=photo_count,
            ))
        return ProjectListResponse(projects=project_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project_detail(project_id: str):
    """프로젝트 상세 조회"""
    try:
        project = get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        photo_count = get_photo_count(project_id)
        return ProjectResponse(
            id=project["id"],
            name=project["name"],
            user_id=project["user_id"],
            ftp_path=project.get("ftp_path"),
            status=project.get("status", "draft"),
            created_at=project.get("created_at"),
            updated_at=project.get("updated_at"),
            photo_count=photo_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}", response_model=SuccessResponse)
async def delete_project_endpoint(project_id: str):
    """프로젝트 삭제"""
    try:
        project = get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        # FTP 폴더 삭제
        ftp_path = project.get("ftp_path")
        if ftp_path:
            try:
                with Cafe24FTP() as ftp:
                    ftp.delete_directory(ftp_path)
            except Exception as ftp_err:
                print(f"FTP delete warning: {ftp_err}")

        # DB 삭제 (CASCADE로 photos, contents 자동 삭제)
        delete_project(project_id)

        return SuccessResponse(success=True, message="프로젝트가 삭제되었습니다")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
