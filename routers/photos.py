"""
Photos Router
사진 관리 API 엔드포인트
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional

from schemas.blog import (
    PhotoResponse,
    PhotoListResponse,
    PhotoUpdate,
    SuccessResponse,
)
from services.database import (
    add_photo,
    get_photos,
    get_photo,
    update_photo,
    delete_photo,
    get_project,
    update_project_status,
)
from services.ftp import Cafe24FTP, generate_filename

router = APIRouter(prefix="/api/blog", tags=["photos"])


@router.post("/projects/{project_id}/photos", response_model=PhotoResponse)
async def upload_photo(
    project_id: str,
    file: UploadFile = File(...),
    caption: Optional[str] = Form(""),
    category: Optional[str] = Form("기타"),
):
    """사진 업로드"""
    try:
        # 프로젝트 확인
        project = get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        ftp_path = project.get("ftp_path", "")
        if not ftp_path:
            raise HTTPException(status_code=400, detail="FTP 경로가 설정되지 않았습니다")

        # 파일 읽기
        content = await file.read()
        original_name = file.filename or "photo.jpg"

        # 기존 사진 수 조회 (파일명 생성용)
        existing_photos = get_photos(project_id)
        photo_number = len(existing_photos) + 1

        # 파일명 생성 및 FTP 업로드
        filename = generate_filename(original_name, f"photo{photo_number}")
        remote_path = f"{ftp_path}/images/{filename}"

        with Cafe24FTP() as ftp:
            ftp_url = ftp.upload_bytes(content, remote_path)

        # DB 저장
        photo = add_photo(project_id, filename, ftp_url, caption, category)

        # 프로젝트 상태 업데이트
        update_project_status(project_id, "photos_uploaded")

        return PhotoResponse(
            id=photo["id"],
            project_id=photo["project_id"],
            filename=photo["filename"],
            ftp_url=photo.get("ftp_url"),
            caption=photo.get("caption", ""),
            category=photo.get("category", "기타"),
            display_order=photo.get("display_order", 0),
            created_at=photo.get("created_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/photos", response_model=PhotoListResponse)
async def get_project_photos(project_id: str):
    """프로젝트 사진 목록 조회"""
    try:
        # 프로젝트 확인
        project = get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        photos = get_photos(project_id)
        photo_list = [
            PhotoResponse(
                id=p["id"],
                project_id=p["project_id"],
                filename=p["filename"],
                ftp_url=p.get("ftp_url"),
                caption=p.get("caption", ""),
                category=p.get("category", "기타"),
                display_order=p.get("display_order", 0),
                created_at=p.get("created_at"),
            )
            for p in photos
        ]
        return PhotoListResponse(photos=photo_list)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/photos/{photo_id}", response_model=PhotoResponse)
async def update_photo_endpoint(photo_id: str, data: PhotoUpdate):
    """사진 수정 (캡션, 카테고리)"""
    try:
        # 사진 확인
        photo = get_photo(photo_id)
        if not photo:
            raise HTTPException(status_code=404, detail="사진을 찾을 수 없습니다")

        # 업데이트
        updated = update_photo(photo_id, caption=data.caption, category=data.category)

        # 업데이트된 정보 반환
        return PhotoResponse(
            id=photo["id"],
            project_id=photo["project_id"],
            filename=photo["filename"],
            ftp_url=photo.get("ftp_url"),
            caption=data.caption if data.caption is not None else photo.get("caption", ""),
            category=data.category if data.category is not None else photo.get("category", "기타"),
            display_order=photo.get("display_order", 0),
            created_at=photo.get("created_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/photos/{photo_id}", response_model=SuccessResponse)
async def delete_photo_endpoint(photo_id: str):
    """사진 삭제"""
    try:
        # 사진 확인
        photo = get_photo(photo_id)
        if not photo:
            raise HTTPException(status_code=404, detail="사진을 찾을 수 없습니다")

        # 프로젝트 정보로 FTP 경로 구성
        project = get_project(photo["project_id"])
        ftp_path = project.get("ftp_path", "") if project else ""

        # FTP에서 파일 삭제
        if ftp_path and photo.get("filename"):
            try:
                with Cafe24FTP() as ftp:
                    remote_path = f"{ftp_path}/images/{photo['filename']}"
                    ftp.delete_file(remote_path)
            except Exception as ftp_err:
                print(f"FTP delete warning: {ftp_err}")

        # DB에서 삭제
        delete_photo(photo_id)

        return SuccessResponse(success=True, message="사진이 삭제되었습니다")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
