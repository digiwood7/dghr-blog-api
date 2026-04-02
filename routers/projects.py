"""
Projects Router
프로젝트 CRUD API 엔드포인트
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from schemas.blog import (
    ProjectCreate,
    ProjectUpdate,
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
    update_project_name,
    update_project_status,
    get_photos,
    get_content,
)
from services.ftp import Cafe24FTP
from services.webhook import send_publish_webhook

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
            generated_at=project.get("generated_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=ProjectListResponse)
async def get_projects(user_id: str = Query(None, description="사용자 ID (없으면 전체 조회)")):
    """프로젝트 목록 조회"""
    try:
        projects = list_projects(user_id)
        project_list = []
        for p in projects:
            project_list.append(ProjectResponse(
                id=p["id"],
                name=p["name"],
                user_id=p["user_id"],
                ftp_path=p.get("ftp_path"),
                status=p.get("status", "draft"),
                created_at=p.get("created_at"),
                updated_at=p.get("updated_at"),
                generated_at=p.get("generated_at"),
                photo_count=p.get("photo_count", 0),
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
            generated_at=project.get("generated_at"),
            photo_count=photo_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project_endpoint(project_id: str, data: ProjectUpdate):
    """프로젝트 수정 (이름 변경)"""
    try:
        project = get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        updated = update_project_name(project_id, data.name)
        if not updated:
            raise HTTPException(status_code=500, detail="프로젝트 수정 실패")

        photo_count = get_photo_count(project_id)
        return ProjectResponse(
            id=updated["id"],
            name=updated["name"],
            user_id=updated["user_id"],
            ftp_path=updated.get("ftp_path"),
            status=updated.get("status", "draft"),
            created_at=updated.get("created_at"),
            updated_at=updated.get("updated_at"),
            generated_at=updated.get("generated_at"),
            photo_count=photo_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/publish", response_model=SuccessResponse)
async def publish_project(project_id: str):
    """프로젝트 발행 (d-onworks 포트폴리오에 자동 연동)

    1. 프로젝트 상태 → published
    2. d-onworks webhook 전송
    """
    try:
        project = get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        # 글이 생성된 상태에서만 발행 가능
        if project.get("status") not in ("generated", "published", "completed"):
            raise HTTPException(
                status_code=400,
                detail="글 생성이 완료된 프로젝트만 발행할 수 있습니다"
            )

        content = get_content(project_id)
        if not content or not content.get("title"):
            raise HTTPException(status_code=400, detail="생성된 글이 없습니다")

        photos = get_photos(project_id)

        # 상태 업데이트
        update_project_status(project_id, "published")

        # d-onworks webhook 전송
        try:
            webhook_result = send_publish_webhook(project, content, photos)
        except Exception as webhook_err:
            # webhook 실패해도 상태는 published로 유지 (로그만 남김)
            print(f"Webhook 전송 실패: {webhook_err}")
            return SuccessResponse(
                success=True,
                message=f"발행 완료 (포트폴리오 연동 실패: {webhook_err})"
            )

        action = webhook_result.get("action", "created")
        return SuccessResponse(
            success=True,
            message=f"발행 완료 (포트폴리오 {action})"
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
