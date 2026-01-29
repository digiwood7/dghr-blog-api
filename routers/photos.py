"""
Photos Router
사진 관리 API 엔드포인트
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import Optional
from PIL import Image, ImageOps
import io
import httpx

from schemas.blog import (
    PhotoResponse,
    PhotoListResponse,
    PhotoUpdate,
    PhotoReorderRequest,
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
    reorder_photos,
    search_photos,
)
from services.ftp import Cafe24FTP, generate_filename

router = APIRouter(prefix="/api/blog", tags=["photos"])


def optimize_image(content: bytes, max_width: int = 1920, quality: int = 80) -> tuple[bytes, dict]:
    """
    이미지 최적화 (리사이징 + 품질 조정)

    Args:
        content: 원본 이미지 바이트
        max_width: 최대 가로 크기 (기본 1920px)
        quality: JPEG 품질 (기본 80%)

    Returns:
        (최적화된 이미지 바이트, 최적화 정보 딕셔너리)
    """
    original_size = len(content)

    # 이미지 열기
    img = Image.open(io.BytesIO(content))

    # ⭐ EXIF Orientation 자동 보정 (사진 회전 문제 해결)
    # 스마트폰으로 찍은 사진의 회전 정보(EXIF)를 읽고 자동으로 올바르게 회전
    img = ImageOps.exif_transpose(img) or img

    original_width, original_height = img.size
    original_format = img.format or "JPEG"

    # RGBA 이미지는 RGB로 변환 (JPEG 저장 위해)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # 리사이징 (가로가 max_width보다 큰 경우만)
    resized = False
    if original_width > max_width:
        ratio = max_width / original_width
        new_height = int(original_height * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
        resized = True

    new_width, new_height = img.size

    # JPEG로 저장 (품질 설정)
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=quality, optimize=True)
    optimized_content = output.getvalue()
    optimized_size = len(optimized_content)

    # 최적화 정보
    info = {
        "original_size": original_size,
        "optimized_size": optimized_size,
        "original_dimensions": f"{original_width}x{original_height}",
        "optimized_dimensions": f"{new_width}x{new_height}",
        "compression_ratio": round(original_size / optimized_size, 1) if optimized_size > 0 else 0,
        "size_reduction_percent": round((1 - optimized_size / original_size) * 100, 1) if original_size > 0 else 0,
        "resized": resized,
        "quality": quality,
    }

    return optimized_content, info


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

        # 이미지 최적화 (1920px, 품질 80%)
        optimized_content, optimize_info = optimize_image(content, max_width=1920, quality=80)
        print(f"[Image Optimize] {original_name}: {optimize_info['original_size']:,} bytes → {optimize_info['optimized_size']:,} bytes ({optimize_info['size_reduction_percent']}% 감소, {optimize_info['compression_ratio']}x 압축)")

        # 기존 사진 수 조회 (파일명 생성용)
        existing_photos = get_photos(project_id)
        photo_number = len(existing_photos) + 1

        # 파일명 생성 및 FTP 업로드 (최적화된 이미지 사용)
        # 확장자는 항상 .jpg로 (JPEG 저장하므로)
        base_name = original_name.rsplit(".", 1)[0] if "." in original_name else original_name
        filename = generate_filename(f"{base_name}.jpg", f"photo{photo_number}")
        remote_path = f"{ftp_path}/images/{filename}"

        with Cafe24FTP() as ftp:
            ftp_url = ftp.upload_bytes(optimized_content, remote_path)

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
        updated = update_photo(photo_id, caption=data.caption, category=data.category, display_order=data.display_order)

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


@router.get("/photos/{photo_id}/download")
async def download_photo(photo_id: str):
    """사진 다운로드 (FTP URL 프록시)"""
    try:
        photo = get_photo(photo_id)
        if not photo:
            raise HTTPException(status_code=404, detail="사진을 찾을 수 없습니다")

        ftp_url = photo.get("ftp_url")
        if not ftp_url:
            raise HTTPException(status_code=400, detail="다운로드 URL이 없습니다")

        async with httpx.AsyncClient() as client:
            resp = await client.get(ftp_url, timeout=30.0)
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail="이미지를 가져올 수 없습니다")

        filename = photo.get("filename", "photo.jpg")
        content_type = resp.headers.get("content-type", "image/jpeg")

        return StreamingResponse(
            io.BytesIO(resp.content),
            media_type=content_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/projects/{project_id}/photos/reorder", response_model=SuccessResponse)
async def reorder_photos_endpoint(project_id: str, data: PhotoReorderRequest):
    """사진 순서 변경"""
    try:
        project = get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        reorder_photos(project_id, data.photo_ids)
        return SuccessResponse(success=True, message="순서가 변경되었습니다")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/photos/search")
async def search_photos_endpoint(
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    """사진 검색 (카테고리, 키워드, 날짜 범위, 페이징)"""
    try:
        result = search_photos(
            category=category,
            keyword=keyword,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )
        photo_list = [
            {
                "id": p["id"],
                "project_id": p["project_id"],
                "project_name": p.get("blog_projects", {}).get("name", "") if p.get("blog_projects") else "",
                "filename": p["filename"],
                "ftp_url": p.get("ftp_url"),
                "caption": p.get("caption", ""),
                "category": p.get("category", "기타"),
                "display_order": p.get("display_order", 0),
                "created_at": p.get("created_at"),
            }
            for p in result["photos"]
        ]
        return {
            "photos": photo_list,
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
            "total_pages": result["total_pages"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
