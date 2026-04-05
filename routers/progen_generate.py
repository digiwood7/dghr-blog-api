"""
ProGen 제안서 AI 생성 라우터
Vercel /api/generate → Railway 이전
"""
import os
import re
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import google.generativeai as genai

from services.progen_prompts import get_system_prompt

router = APIRouter(prefix="/api/progen", tags=["progen-generate"])

GEMINI_MODEL = "gemini-3.1-pro-preview"


def get_client():
    api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="GOOGLE_AI_API_KEY 환경변수가 설정되지 않았습니다")
    return genai.GenerativeModel(model_name=GEMINI_MODEL)


# === 요청/응답 스키마 ===

class ImageData(BaseModel):
    base64: str
    mimeType: str


class ConversationMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class GenerateRequest(BaseModel):
    projectName: str | None = None
    clientName: str | None = None
    exhibitionName: str | None = None
    boothSize: str | None = None
    requirements: str | None = None
    images: list[ImageData] | None = None
    imageUrls: list[str] | None = None
    conversationHistory: list[ConversationMessage] | None = None
    templateId: str | None = "A"


# === 유틸리티 함수 ===

def build_user_message(body: GenerateRequest) -> str:
    parts = []
    if body.projectName:
        parts.append(f"프로젝트명: {body.projectName}")
    if body.clientName:
        parts.append(f"고객명: {body.clientName}")
    if body.exhibitionName:
        parts.append(f"전시회: {body.exhibitionName}")
    if body.boothSize:
        parts.append(f"부스규모: {body.boothSize}")
    if body.requirements:
        parts.append(f"요청사항: {body.requirements}")

    image_count = len(body.imageUrls or []) or len(body.images or [])
    if image_count > 0:
        parts.append(f"첨부 이미지: {image_count}장 ({{{{IMAGE:0}}}} ~ {{{{IMAGE:{image_count - 1}}}}} 사용 가능)")
    else:
        parts.append("첨부 이미지: 없음 (이미지 영역은 디자인 요소로 대체)")

    return "\n".join(parts)


def extract_html_from_response(text: str) -> str:
    html = text.strip()
    # 마크다운 코드 블록 제거
    match = re.search(r"```(?:html)?\s*\n?([\s\S]*?)\n?```", html)
    if match:
        html = match.group(1).strip()

    # proposal-content div 찾기
    start_idx = html.find('<div id="proposal-content"')
    if start_idx != -1:
        html = html[start_idx:]
    else:
        alt_idx = html.find("<div id='proposal-content'")
        if alt_idx != -1:
            html = html[alt_idx:]
        elif not html.startswith("<"):
            raise ValueError("응답에서 HTML을 추출할 수 없습니다")

    return html


def replace_image_placeholders(html: str, images: list[ImageData] | None, image_urls: list[str] | None) -> str:
    def replacer(match):
        idx = int(match.group(1))
        if image_urls and idx < len(image_urls):
            return image_urls[idx]
        if images and idx < len(images):
            return f"data:{images[idx].mimeType};base64,{images[idx].base64}"
        return ""
    return re.sub(r"\{\{IMAGE:(\d+)\}\}", replacer, html)


def sanitize_html(html: str) -> str:
    html = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    html = re.sub(r'\son\w+="[^"]*"', "", html, flags=re.IGNORECASE)
    html = re.sub(r"\son\w+='[^']*'", "", html, flags=re.IGNORECASE)
    return html


def constrain_images(html: str) -> str:
    def replacer(match):
        before, style, after = match.group(1), match.group(2), match.group(3)
        max_h = re.search(r"max-height\s*:\s*(\d+)mm", style, re.IGNORECASE)
        if max_h and int(max_h.group(1)) <= 150:
            return f'<img{before}style="{style}"{after}>'
        cleaned = re.sub(r"max-height\s*:[^;]+;?", "", style, flags=re.IGNORECASE).strip()
        sep = "" if cleaned.endswith(";") or not cleaned else ";"
        return f'<img{before}style="{cleaned}{sep}max-height:150mm;object-fit:contain;"{after}>'
    return re.sub(r'<img\b([^>]*?)style="([^"]*?)"([^>]*?)>', replacer, html, flags=re.IGNORECASE)


async def fetch_image_from_url(url: str) -> ImageData:
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.get(url)
        res.raise_for_status()
        import base64
        b64 = base64.b64encode(res.content).decode()
        mime = res.headers.get("content-type", "image/jpeg")
        return ImageData(base64=b64, mimeType=mime)


# === API 엔드포인트 ===

@router.post("/generate-proposal")
async def generate_proposal(body: GenerateRequest):
    """ProGen 제안서 AI 생성"""
    if not body.projectName and not body.requirements:
        raise HTTPException(status_code=400, detail="프로젝트명 또는 요청사항을 입력해주세요")

    api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="API 키가 설정되지 않았습니다")

    genai.configure(api_key=api_key)

    # 대화 기록 구성
    contents = []
    if body.conversationHistory:
        for msg in body.conversationHistory:
            role = "model" if msg.role == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": msg.content}]})

    # 이미지 resolve: FTP URL 우선, fallback으로 base64
    resolved_images: list[ImageData] = []
    if body.imageUrls:
        for url in body.imageUrls:
            try:
                img = await fetch_image_from_url(url)
                resolved_images.append(img)
            except Exception:
                pass
    elif body.images:
        resolved_images = body.images

    # 사용자 메시지 parts 구성
    user_parts = []
    for img in resolved_images:
        user_parts.append({
            "inline_data": {"data": img.base64, "mime_type": img.mimeType}
        })
    user_parts.append({"text": build_user_message(body)})
    contents.append({"role": "user", "parts": user_parts})

    # Gemini API 호출
    template_id = body.templateId or "A"
    max_tokens = 65536 if template_id == "B" else 32768

    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=get_system_prompt(template_id),
        generation_config=genai.GenerationConfig(
            temperature=0.7,
            max_output_tokens=max_tokens,
        ),
    )

    try:
        response = model.generate_content(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API 오류: {str(e)}")

    response_text = response.text
    if not response_text:
        raise HTTPException(status_code=500, detail="Gemini로부터 빈 응답을 받았습니다")

    # HTML 추출 및 처리
    try:
        raw_html = extract_html_from_response(response_text)
    except ValueError:
        raise HTTPException(status_code=500, detail="응답 형식 오류: HTML을 추출할 수 없습니다")

    raw_html = sanitize_html(raw_html)
    raw_html = constrain_images(raw_html)

    # 이미지 플레이스홀더 교체
    if body.imageUrls:
        html = replace_image_placeholders(raw_html, None, body.imageUrls)
    elif body.images:
        html = replace_image_placeholders(raw_html, body.images, None)
    else:
        html = raw_html

    return {
        "success": True,
        "content": {"html": html, "rawHtml": raw_html},
    }
