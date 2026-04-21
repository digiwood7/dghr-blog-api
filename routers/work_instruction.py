"""
Work Instruction Router
작업지시서 이미지 업로드 API (Honeycomb ERP용)
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from PIL import Image, ImageOps
import io
from datetime import datetime

from services.ftp import Cafe24FTP

router = APIRouter(prefix="/api/honeyerp", tags=["work-instruction"])

# 1MB 바이패스 임계값
BYPASS_SIZE = 1 * 1024 * 1024  # 1MB


def optimize_image(content: bytes, max_width: int = 1920, quality: int = 80) -> tuple[bytes, dict]:
    """이미지 최적화 — 1MB 이하는 바이패스"""
    original_size = len(content)

    # 1MB 이하: 바이패스 (EXIF 보정만 수행)
    if original_size <= BYPASS_SIZE:
        try:
            img = Image.open(io.BytesIO(content))
            img = ImageOps.exif_transpose(img) or img
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=95, optimize=True)
            result = output.getvalue()
            return result, {
                "original_size": original_size,
                "optimized_size": len(result),
                "resized": False,
                "bypassed": True,
            }
        except Exception:
            return content, {
                "original_size": original_size,
                "optimized_size": original_size,
                "resized": False,
                "bypassed": True,
            }

    # 1MB 초과: 리사이즈 + 압축
    img = Image.open(io.BytesIO(content))
    img = ImageOps.exif_transpose(img) or img
    original_width, original_height = img.size

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    resized = False
    if original_width > max_width:
        ratio = max_width / original_width
        new_height = int(original_height * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
        resized = True

    output = io.BytesIO()
    img.save(output, format="JPEG", quality=quality, optimize=True)
    optimized = output.getvalue()

    return optimized, {
        "original_size": original_size,
        "optimized_size": len(optimized),
        "resized": resized,
        "bypassed": False,
    }


@router.post("/work-instruction/upload-image")
async def upload_instruction_image(
    file: UploadFile = File(...),
    work_order_id: str = Form(...),
):
    """작업지시서 에디터 이미지 업로드"""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="10MB 이하 이미지만 업로드 가능합니다")

    optimized, info = optimize_image(content)

    ts = datetime.now().strftime("%Y%m%d%H%M%S%f")[:18]
    remote_path = f"/www/honeyerp/{work_order_id}/images/img_{ts}.jpg"

    try:
        with Cafe24FTP() as ftp:
            url = ftp.upload_bytes(optimized, remote_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"FTP 업로드 실패: {str(e)}")

    return {"url": url, "info": info}


@router.delete("/work-instruction/delete-image")
async def delete_instruction_image(url: str):
    """작업지시서 이미지 삭제"""
    base_url = "http://jyk980.cafe24.com"
    if not url.startswith(base_url):
        raise HTTPException(status_code=400, detail="유효하지 않은 URL")

    public_path = url[len(base_url):]
    remote_path = f"/www{public_path}"

    try:
        with Cafe24FTP() as ftp:
            ftp.delete_file(remote_path)
    except Exception:
        pass  # 삭제 실패해도 무시 (최선 노력)

    return {"success": True}


@router.post("/work-instruction/upload-html")
async def upload_instruction_html(
    html: str = Form(...),
    work_order_id: str = Form(...),
    old_url: str | None = Form(None),
):
    """작업지시서 HTML 업로드 (DB egress 절감 목적 — HTML 본문은 FTP 저장, DB는 URL만 보관)"""
    if len(html.encode("utf-8")) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="20MB 이하 HTML만 업로드 가능합니다")

    ts = datetime.now().strftime("%Y%m%d%H%M%S%f")[:18]
    remote_path = f"/www/honeyerp/{work_order_id}/htmls/instruction_{ts}.html"

    try:
        with Cafe24FTP() as ftp:
            # 기존 파일 정리(최선 노력 — 실패해도 신규 업로드 계속)
            if old_url:
                base_url = "http://jyk980.cafe24.com"
                if old_url.startswith(base_url):
                    old_remote = f"/www{old_url[len(base_url):]}"
                    try:
                        ftp.delete_file(old_remote)
                    except Exception:
                        pass
            url = ftp.upload_bytes(html.encode("utf-8"), remote_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"FTP 업로드 실패: {str(e)}")

    return {"url": url, "size": len(html.encode("utf-8"))}


@router.delete("/work-instruction/delete-html")
async def delete_instruction_html(url: str):
    """작업지시서 HTML 파일 삭제"""
    base_url = "http://jyk980.cafe24.com"
    if not url.startswith(base_url):
        raise HTTPException(status_code=400, detail="유효하지 않은 URL")

    remote_path = f"/www{url[len(base_url):]}"

    try:
        with Cafe24FTP() as ftp:
            ftp.delete_file(remote_path)
    except Exception:
        pass  # 삭제 실패해도 무시 (최선 노력)

    return {"success": True}
