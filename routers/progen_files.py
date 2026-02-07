"""
Progen Files Router
제안서 파일 업로드/관리 API
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pathlib import Path
from datetime import datetime

from schemas.progen import (
    ProgenFileResponse,
    ProgenFileListResponse,
    SuccessResponse,
)
from services.progen_db import (
    get_progen_project,
    add_progen_file,
    get_progen_files,
    get_progen_file,
    delete_progen_file,
)
from services.ftp import Cafe24FTP

# 이미지 최적화 함수 재사용 (photos.py에서)
from routers.photos import optimize_image

router = APIRouter(prefix="/api/progen", tags=["progen-files"])

# 이미지 확장자
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"}
# 문서 확장자
DOC_EXTENSIONS = {".pdf", ".doc", ".docx", ".pptx", ".ppt", ".xlsx", ".xls", ".hwp", ".txt"}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | DOC_EXTENSIONS


def generate_progen_filename(original: str, file_number: int) -> str:
    """파일명 생성: file{N}_{timestamp}.{ext}"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = Path(original).suffix.lower()
    return f"file{file_number}_{ts}{ext}"


@router.post("/projects/{project_id}/files", response_model=ProgenFileResponse)
async def upload_file(
    project_id: str,
    file: UploadFile = File(...),
):
    """파일 업로드 (이미지: Pillow 최적화, 문서: 그대로)"""
    try:
        # 프로젝트 확인
        project = get_progen_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        ftp_path = project.get("ftp_path", "")
        if not ftp_path:
            raise HTTPException(status_code=400, detail="FTP 경로가 설정되지 않았습니다")

        # 파일 읽기
        content = await file.read()
        original_name = file.filename or "file"
        ext = Path(original_name).suffix.lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 파일 형식입니다: {ext}"
            )

        # 파일 타입 판별
        is_image = ext in IMAGE_EXTENSIONS
        file_type = "image" if is_image else "document"

        # 이미지: Pillow 최적화
        upload_content = content
        if is_image:
            try:
                optimized_content, info = optimize_image(content, max_width=1920, quality=80)
                print(f"[Progen Image Optimize] {original_name}: {info['original_size']:,} -> {info['optimized_size']:,} bytes ({info['size_reduction_percent']}% reduction)")
                upload_content = optimized_content
                # 이미지는 최적화 후 항상 .jpg
                ext = ".jpg"
            except Exception as opt_err:
                print(f"Image optimization failed, using original: {opt_err}")
                upload_content = content

        file_size = len(upload_content)

        # 기존 파일 수 조회 (번호 생성용)
        existing_files = get_progen_files(project_id)
        file_number = len(existing_files) + 1

        # 파일명 생성
        filename = generate_progen_filename(f"file{ext}", file_number)

        # FTP 업로드
        remote_path = f"{ftp_path}/files/{filename}"
        with Cafe24FTP() as ftp:
            ftp_url = ftp.upload_bytes(upload_content, remote_path)

        # URL is already public from upload_bytes

        # DB 저장
        file_record = add_progen_file(
            project_id=project_id,
            filename=filename,
            original_name=original_name,
            ftp_url=ftp_url,
            file_type=file_type,
            file_size=file_size,
        )

        return ProgenFileResponse(
            id=file_record["id"],
            project_id=file_record["project_id"],
            filename=file_record["filename"],
            original_name=file_record["original_name"],
            ftp_url=file_record.get("ftp_url", ""),
            file_type=file_record.get("file_type"),
            file_size=file_record.get("file_size"),
            created_at=file_record.get("created_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/files", response_model=ProgenFileListResponse)
async def get_project_files(project_id: str):
    """프로젝트 파일 목록 조회"""
    try:
        project = get_progen_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        files = get_progen_files(project_id)
        file_list = [
            ProgenFileResponse(
                id=f["id"],
                project_id=f["project_id"],
                filename=f["filename"],
                original_name=f["original_name"],
                ftp_url=f.get("ftp_url", ""),
                file_type=f.get("file_type"),
                file_size=f.get("file_size"),
                created_at=f.get("created_at"),
            )
            for f in files
        ]
        return ProgenFileListResponse(files=file_list)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}", response_model=SuccessResponse)
async def delete_file_endpoint(file_id: str):
    """파일 삭제 (FTP + DB)"""
    try:
        file_record = get_progen_file(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

        # 프로젝트 정보로 FTP 경로 구성
        project = get_progen_project(file_record["project_id"])
        ftp_path = project.get("ftp_path", "") if project else ""

        # FTP에서 파일 삭제
        if ftp_path and file_record.get("filename"):
            try:
                with Cafe24FTP() as ftp:
                    remote_path = f"{ftp_path}/files/{file_record['filename']}"
                    ftp.delete_file(remote_path)
            except Exception as ftp_err:
                print(f"Progen FTP file delete warning: {ftp_err}")

        # DB에서 삭제
        delete_progen_file(file_id)

        return SuccessResponse(success=True, message="파일이 삭제되었습니다")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
