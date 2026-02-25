"""
Suggestion Images Router
개선제안 이미지 업로드/삭제 API (Railway 경유 - Vercel 4.5MB 제한 우회)
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Header
from typing import Optional, List
from PIL import Image, ImageOps
from datetime import datetime
import io

from services.database import get_supabase
from services.ftp import Cafe24FTP

router = APIRouter(prefix="/api/suggestions", tags=["suggestion-images"])


def optimize_image(content: bytes, max_width: int = 1920, quality: int = 80) -> tuple[bytes, dict]:
    """이미지 최적화 (리사이징 + 품질 조정) - photos.py와 동일 로직"""
    original_size = len(content)
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

    new_width, new_height = img.size
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=quality, optimize=True)
    optimized_content = output.getvalue()
    optimized_size = len(optimized_content)

    info = {
        "original_size": original_size,
        "optimized_size": optimized_size,
        "original_dimensions": f"{original_width}x{original_height}",
        "optimized_dimensions": f"{new_width}x{new_height}",
        "compression_ratio": round(original_size / optimized_size, 1) if optimized_size > 0 else 0,
        "size_reduction_percent": round((1 - optimized_size / original_size) * 100, 1) if original_size > 0 else 0,
        "resized": resized,
    }
    return optimized_content, info


def get_suggestion_image_path(suggestion_id: str, filename: str) -> str:
    """개선제안 이미지 FTP 경로: /www/suggestion/{id}/images/{filename}"""
    return f"/www/suggestion/{suggestion_id}/images/{filename}"


def generate_suggestion_filename(index: int) -> str:
    """타임스탬프 기반 파일명: photo{N}_{timestamp}.jpg"""
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"photo{index}_{ts}.jpg"


def verify_employee(employee_id: str) -> dict:
    """직원 조회 및 권한 확인"""
    if not employee_id:
        raise HTTPException(status_code=401, detail="인증이 필요합니다")
    supabase = get_supabase()
    result = supabase.table("employees").select("id, role").eq("id", employee_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="유효하지 않은 사용자입니다")
    return result.data


@router.post("/{suggestion_id}/images")
async def upload_suggestion_images(
    suggestion_id: str,
    files: List[UploadFile] = File(...),
    image_type: str = Form(...),
    x_employee_id: Optional[str] = Header(None, alias="X-Employee-Id"),
):
    """개선제안 이미지 업로드 (PIL 최적화 + FTP)"""
    try:
        # 인증
        employee = verify_employee(x_employee_id)
        is_admin = employee["role"] == "super_admin"

        # 제안 조회 및 권한 확인
        supabase = get_supabase()
        result = supabase.table("suggestions").select("employee_id, status").eq("id", suggestion_id).single().execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="제안을 찾을 수 없습니다")

        if not is_admin and result.data["employee_id"] != employee["id"]:
            raise HTTPException(status_code=403, detail="본인의 제안에만 이미지를 업로드할 수 있습니다")

        if image_type not in ("problem", "improvement"):
            raise HTTPException(status_code=400, detail="image_type은 problem 또는 improvement이어야 합니다")

        # 기존 이미지 수 조회 (파일명 번호용)
        count_result = supabase.table("suggestion_images").select("id", count="exact").eq("suggestion_id", suggestion_id).eq("image_type", image_type).execute()
        photo_index = (count_result.count or 0) + 1

        uploaded_images = []

        # 단일 FTP 연결로 일괄 처리
        with Cafe24FTP() as ftp:
            for file in files:
                content = await file.read()
                original_name = file.filename or "photo.jpg"

                # 이미지 최적화
                optimized_content, info = optimize_image(content)
                print(f"[Suggestion Image] {original_name}: {info['original_size']:,} → {info['optimized_size']:,} bytes ({info['size_reduction_percent']}% 감소)")

                # 파일명 및 경로 생성
                filename = generate_suggestion_filename(photo_index)
                remote_path = get_suggestion_image_path(suggestion_id, filename)

                # FTP 업로드
                ftp_url = ftp.upload_bytes(optimized_content, remote_path)

                # DB 저장
                insert_result = supabase.table("suggestion_images").insert({
                    "suggestion_id": suggestion_id,
                    "image_type": image_type,
                    "file_name": original_name,
                    "file_path": remote_path,
                    "file_url": ftp_url,
                    "sort_order": photo_index,
                }).execute()

                if insert_result.data:
                    uploaded_images.append(insert_result.data[0])

                photo_index += 1

        return {"images": uploaded_images}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[Suggestion Image Upload Error] {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/images/{image_id}")
async def delete_suggestion_image(
    image_id: str,
    x_employee_id: Optional[str] = Header(None, alias="X-Employee-Id"),
):
    """개선제안 이미지 삭제"""
    try:
        employee = verify_employee(x_employee_id)
        is_admin = employee["role"] == "super_admin"

        supabase = get_supabase()

        # 이미지 조회
        img_result = supabase.table("suggestion_images").select("id, file_path, suggestion_id").eq("id", image_id).single().execute()
        if not img_result.data:
            raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다")
        image = img_result.data

        # 제안 조회 및 권한 확인
        sug_result = supabase.table("suggestions").select("employee_id").eq("id", image["suggestion_id"]).single().execute()
        if not sug_result.data:
            raise HTTPException(status_code=404, detail="제안을 찾을 수 없습니다")

        if not is_admin and sug_result.data["employee_id"] != employee["id"]:
            raise HTTPException(status_code=403, detail="본인의 제안 이미지만 삭제할 수 있습니다")

        # FTP 삭제
        if image.get("file_path"):
            try:
                with Cafe24FTP() as ftp:
                    ftp.delete_file(image["file_path"])
            except Exception as ftp_err:
                print(f"FTP delete warning: {ftp_err}")

        # DB 삭제
        supabase.table("suggestion_images").delete().eq("id", image_id).execute()

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[Suggestion Image Delete Error] {e}")
        raise HTTPException(status_code=500, detail=str(e))
