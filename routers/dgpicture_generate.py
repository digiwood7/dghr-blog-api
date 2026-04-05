"""
DGPicture 연출샷 AI 생성 라우터
Vercel /api/dgpicture/generate → Railway 이전
"""
import os
import base64
from datetime import datetime
import httpx
import google.generativeai as genai
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.ftp import Cafe24FTP

router = APIRouter(prefix="/api/dgpicture", tags=["dgpicture-generate"])

GEMINI_MODEL = "gemini-3.1-flash-image-preview"

# Supabase 클라이언트
_supabase = None


def get_supabase():
    global _supabase
    if _supabase is None:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise HTTPException(status_code=500, detail="Supabase 환경변수가 설정되지 않았습니다")
        _supabase = create_client(url, key)
    return _supabase


# === 프롬프트 ===

SYSTEM_PROMPT = """You are a professional product photographer. Create a styled product shot.

MOST IMPORTANT RULE:
- The product in the input image is already photographed from the correct angle.
- You MUST preserve the EXACT same angle, orientation, and direction of the product as shown in the input.
- Do NOT rotate, mirror, flip, or change the viewing angle of the product in any way.
- Simply extract the product and place it into a new scene while keeping its appearance IDENTICAL.

Other rules:
- Extract ONLY the product/object from the input image, completely ignore its original background
- The product must maintain its exact shape, color, texture, proportions, and details
- Compose the product naturally into the provided background scene
- Add appropriate lighting, shadows, and reflections for realism
- Props and scene decoration are allowed for a natural styled look
- Output a single high-quality photograph"""

VIEW_PROMPTS = {
    "upside": "The input image shows the product from above (top-down). Keep this exact top-down perspective in the output.",
    "frontside": "The input image shows the product from the front. Keep this exact front-facing perspective in the output.",
    "leftside": "The input image shows the product from one specific side. Keep the product facing the EXACT same direction as the input. Do NOT rotate or mirror it.",
    "rightside": "The input image shows the product from one specific side. Keep the product facing the EXACT same direction as the input. Do NOT rotate or mirror it.",
}

ORIENTATION_PROMPTS = {
    "horizontal": "CRITICAL: The output image MUST be in LANDSCAPE/HORIZONTAL orientation (wider than tall, e.g. 16:9 or 4:3 aspect ratio).",
    "vertical": "CRITICAL: The output image MUST be in PORTRAIT/VERTICAL orientation (taller than wide, e.g. 9:16 or 3:4 aspect ratio).",
}

VARIATION_PROMPTS = {
    1: "Minimal scene decoration. Clean, simple composition. Only essential shadows and lighting.",
    2: "Subtle scene decoration. A few small complementary props allowed.",
    3: "Moderate scene decoration. Natural props and accessories that complement the product.",
    4: "Rich scene decoration. Multiple props, textures, and atmospheric lighting effects.",
    5: "Full creative styling. Elaborate scene with props, dramatic lighting, textures, and artistic composition.",
}


def build_prompt(view_type: str, variation_level: int, orientation: str, custom_prompt: str | None, has_background: bool) -> str:
    parts = [SYSTEM_PROMPT]
    parts.append(ORIENTATION_PROMPTS.get(orientation, ORIENTATION_PROMPTS["horizontal"]))
    parts.append(VIEW_PROMPTS.get(view_type, VIEW_PROMPTS["frontside"]))
    level = min(5, max(1, variation_level))
    parts.append(VARIATION_PROMPTS[level])

    if has_background:
        parts.append("Use the provided background image as the scene reference. Adapt and transform the background to fit the required orientation. Blend the product naturally into this scene.")
    else:
        parts.append("Generate an appropriate professional studio background for the product.")

    if custom_prompt and custom_prompt.strip():
        parts.append(f"Additional instructions: {custom_prompt.strip()}")

    parts.append("FINAL REMINDER: The product's angle/orientation in the output MUST be IDENTICAL to the input image. Do NOT rotate, flip, or mirror the product under any circumstances.")

    return "\n\n".join(parts)


# === 스키마 ===

class InputImage(BaseModel):
    view_type: str
    base64: str | None = None
    mime_type: str | None = None
    image_url: str | None = None
    orientation: str | None = None
    custom_prompt: str | None = None


class BackgroundImage(BaseModel):
    base64: str | None = None
    mime_type: str | None = None
    image_url: str | None = None


class DgpictureGenerateRequest(BaseModel):
    project_id: str | None = None
    input_images: list[InputImage]
    background_image: BackgroundImage | None = None
    variation_level: int = 3
    orientation: str = "horizontal"
    custom_prompt: str | None = None


# === 유틸 ===

async def resolve_image(img_url: str | None, img_b64: str | None, img_mime: str | None) -> tuple[str, str]:
    """base64 또는 image_url에서 이미지 데이터 resolve"""
    if img_b64 and img_mime:
        return img_b64, img_mime
    if img_url:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(img_url)
            res.raise_for_status()
            b64 = base64.b64encode(res.content).decode()
            mime = res.headers.get("content-type", "image/jpeg")
            return b64, mime
    raise ValueError("base64 또는 image_url이 필요합니다")


def get_output_image_path(project_id: str, view_type: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"/www/dgpicture/output/{project_id}/{view_type}_{ts}.png"


async def generate_styled_shot(
    view_type: str,
    input_b64: str, input_mime: str,
    bg_b64: str | None, bg_mime: str | None,
    orientation: str, variation_level: int, custom_prompt: str | None,
) -> dict:
    """Gemini로 연출샷 생성"""
    api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GOOGLE_GENERATIVE_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_AI_API_KEY 환경변수가 설정되지 않았습니다")

    genai.configure(api_key=api_key)
    prompt = build_prompt(view_type, variation_level, orientation, custom_prompt, bg_b64 is not None)

    # parts 구성
    parts = []
    parts.append("[Product Image] This is the product. You MUST keep the product facing the EXACT same direction as shown here. Do NOT rotate, mirror, or flip it:")
    parts.append({"inline_data": {"data": input_b64, "mime_type": input_mime}})

    if bg_b64 and bg_mime:
        parts.append("[Background Image] Use this as the background scene:")
        parts.append({"inline_data": {"data": bg_b64, "mime_type": bg_mime}})

    parts.append(prompt)

    model = genai.GenerativeModel(model_name=GEMINI_MODEL)
    response = model.generate_content(
        parts,
        generation_config=genai.GenerationConfig(temperature=0.8),
    )

    candidate = response.candidates[0] if response.candidates else None
    if not candidate or not candidate.content or not candidate.content.parts:
        raise ValueError("Gemini 응답에 콘텐츠가 없습니다")

    for part in candidate.content.parts:
        if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
            return {
                "view_type": view_type,
                "image_base64": base64.b64encode(part.inline_data.data).decode() if isinstance(part.inline_data.data, bytes) else part.inline_data.data,
                "mime_type": part.inline_data.mime_type or "image/png",
                "prompt_used": prompt,
                "success": True,
            }

    text_parts = " ".join(p.text for p in candidate.content.parts if hasattr(p, "text") and p.text)
    raise ValueError(f"이미지 생성 실패. Gemini 텍스트 응답: {text_parts[:200]}")


def save_to_ftp(image_b64: str, remote_path: str) -> str:
    """FTP에 이미지 업로드, URL 반환"""
    img_bytes = base64.b64decode(image_b64)
    with Cafe24FTP() as ftp:
        return ftp.upload_bytes(img_bytes, remote_path)


# === API 엔드포인트 ===

@router.post("/generate")
async def dgpicture_generate(body: DgpictureGenerateRequest):
    """연출샷 AI 생성"""
    if not body.input_images:
        raise HTTPException(status_code=400, detail="입력 이미지가 필요합니다")

    # 배경 이미지 resolve
    bg_b64, bg_mime = None, None
    if body.background_image:
        bg_b64, bg_mime = await resolve_image(
            body.background_image.image_url,
            body.background_image.base64,
            body.background_image.mime_type,
        )

    # 입력 이미지 resolve (병렬)
    resolved_inputs = []
    for inp in body.input_images:
        b64, mime = await resolve_image(inp.image_url, inp.base64, inp.mime_type)
        resolved_inputs.append({
            "view_type": inp.view_type,
            "base64": b64,
            "mime_type": mime,
            "orientation": inp.orientation or body.orientation,
            "custom_prompt": inp.custom_prompt or body.custom_prompt,
        })

    # 각 view별 순차 생성 + FTP 저장
    final_results = []
    for inp in resolved_inputs:
        try:
            result = await generate_styled_shot(
                view_type=inp["view_type"],
                input_b64=inp["base64"], input_mime=inp["mime_type"],
                bg_b64=bg_b64, bg_mime=bg_mime,
                orientation=inp["orientation"],
                variation_level=body.variation_level,
                custom_prompt=inp["custom_prompt"],
            )

            # project_id가 있으면 FTP 저장 + DB 기록
            if body.project_id and result["success"] and result.get("image_base64"):
                supabase = get_supabase()

                # 다음 버전 번호 조회
                ver_res = supabase.table("dgpicture_output_images") \
                    .select("version") \
                    .eq("project_id", body.project_id) \
                    .eq("view_type", result["view_type"]) \
                    .order("version", desc=True) \
                    .limit(1) \
                    .execute()
                next_version = (ver_res.data[0]["version"] + 1) if ver_res.data else 1

                # FTP 업로드
                remote_path = get_output_image_path(body.project_id, result["view_type"])
                image_url = save_to_ftp(result["image_base64"], remote_path)

                # DB 저장
                supabase.table("dgpicture_output_images").insert({
                    "project_id": body.project_id,
                    "view_type": result["view_type"],
                    "image_url": image_url,
                    "generation_prompt": result.get("prompt_used", ""),
                    "is_selected": True,
                    "version": next_version,
                }).execute()

                final_results.append({
                    "view_type": result["view_type"],
                    "image_url": image_url,
                    "success": True,
                })
            else:
                final_results.append(result)

        except Exception as err:
            final_results.append({
                "view_type": inp["view_type"],
                "image_base64": "",
                "mime_type": "",
                "prompt_used": "",
                "success": False,
                "error": str(err),
            })

    # 프로젝트 상태 업데이트
    if body.project_id and any(r.get("success") for r in final_results):
        supabase = get_supabase()
        supabase.table("dgpicture_projects").update({
            "status": "completed",
            "updated_at": datetime.now().isoformat(),
        }).eq("id", body.project_id).execute()

    return {"results": final_results}
