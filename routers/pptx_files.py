"""
PPTX Files Router
PPT 파일 업로드/관리 API
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pathlib import Path
from datetime import datetime

from schemas.pptx import (
    PptxFileResponse,
    PptxFileListResponse,
    SuccessResponse,
)
from services.pptx_db import (
    get_pptx_project,
    add_pptx_file,
    get_pptx_files,
    get_pptx_file,
    delete_pptx_file,
)
from services.ftp import Cafe24FTP

# 이미지 최적화 함수 재사용
from routers.photos import optimize_image

router = APIRouter(prefix="/api/pptx", tags=["pptx-files"])

# 이미지 확장자
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"}
# 문서 확장자
DOC_EXTENSIONS = {".pdf", ".doc", ".docx", ".pptx", ".ppt", ".xlsx", ".xls", ".hwp", ".txt", ".svg"}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | DOC_EXTENSIONS


def generate_pptx_filename(original: str, file_number: int) -> str:
    """파일명 생성: file{N}_{timestamp}.{ext}"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = Path(original).suffix.lower()
    return f"file{file_number}_{ts}{ext}"


@router.post("/projects/{project_id}/files", response_model=PptxFileResponse)
async def upload_file(
    project_id: str,
    file: UploadFile = File(...),
):
    """파일 업로드 (이미지: Pillow 최적화, 문서: 그대로)"""
    try:
        project = get_pptx_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        ftp_path = project.get("ftp_path", "")
        if not ftp_path:
            raise HTTPException(status_code=400, detail="FTP 경로가 설정되지 않았습니다")

        content = await file.read()
        original_name = file.filename or "file"
        ext = Path(original_name).suffix.lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 파일 형식입니다: {ext}"
            )

        is_image = ext in IMAGE_EXTENSIONS
        file_type = "image" if is_image else "document"

        upload_content = content
        if is_image:
            try:
                optimized_content, info = optimize_image(content, max_width=1920, quality=80)
                print(f"[PPTX Image Optimize] {original_name}: {info['original_size']:,} -> {info['optimized_size']:,} bytes ({info['size_reduction_percent']}% reduction)")
                upload_content = optimized_content
                ext = ".jpg"
            except Exception as opt_err:
                print(f"Image optimization failed, using original: {opt_err}")
                upload_content = content

        file_size = len(upload_content)

        existing_files = get_pptx_files(project_id)
        file_number = len(existing_files) + 1

        filename = generate_pptx_filename(f"file{ext}", file_number)

        remote_path = f"{ftp_path}/files/{filename}"
        with Cafe24FTP() as ftp:
            ftp_url = ftp.upload_bytes(upload_content, remote_path)

        file_record = add_pptx_file(
            project_id=project_id,
            filename=filename,
            original_name=original_name,
            ftp_url=ftp_url,
            file_type=file_type,
            file_size=file_size,
        )

        return PptxFileResponse(
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


@router.get("/projects/{project_id}/files", response_model=PptxFileListResponse)
async def get_project_files(project_id: str):
    """프로젝트 파일 목록 조회"""
    try:
        project = get_pptx_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        files = get_pptx_files(project_id)
        file_list = [
            PptxFileResponse(
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
        return PptxFileListResponse(files=file_list)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}", response_model=SuccessResponse)
async def delete_file_endpoint(file_id: str):
    """파일 삭제 (FTP + DB)"""
    try:
        file_record = get_pptx_file(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

        project = get_pptx_project(file_record["project_id"])
        ftp_path = project.get("ftp_path", "") if project else ""

        if ftp_path and file_record.get("filename"):
            try:
                with Cafe24FTP() as ftp:
                    remote_path = f"{ftp_path}/files/{file_record['filename']}"
                    ftp.delete_file(remote_path)
            except Exception as ftp_err:
                print(f"PPTX FTP file delete warning: {ftp_err}")

        delete_pptx_file(file_id)

        return SuccessResponse(success=True, message="파일이 삭제되었습니다")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
