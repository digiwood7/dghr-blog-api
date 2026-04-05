"""
메일 템플릿 AI 생성 라우터
Vercel /api/mailing/templates/generate → Railway 이전
"""
import os
import re
import json
import base64
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
import google.generativeai as genai

router = APIRouter(prefix="/api/mailing", tags=["mailing-generate"])

GEMINI_MODEL = "gemini-3.1-pro-preview"

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

TARGET_LABELS = {
    "construction": "건설사/시공사 담당자",
    "interior": "인테리어 업체 관계자",
    "general": "일반 고객",
}

CATEGORY_LABELS = {
    "product": "제품 소개",
    "event": "이벤트/프로모션 안내",
    "newsletter": "정기 뉴스레터",
    "notice": "공지사항",
}

SYSTEM_PROMPT_CREATE = """당신은 한국 B2B 제조업체(디지우드/Digiwood - 허니콤보드, 인테리어 자재 전문)의 이메일 마케팅 전문가입니다.

아래 규칙을 반드시 지켜 뉴스레터 이메일 HTML을 작성해주세요:

## HTML 규칙 (이메일 호환성 필수)
1. 테이블 기반 레이아웃 (max-width: 600px)
2. 모든 CSS는 인라인 스타일로만 작성 (외부/내부 스타일시트 금지)
3. 모든 <img> 태그에 alt 속성 필수
4. 모든 <img>에 width, height 속성 명시, display:block 필수
5. 모든 URL은 반드시 http:// 또는 https://로 시작. ftp:// 절대 사용 금지
6. FTP 경로가 주어지면 반드시 HTTP URL로 변환: ftp://jyk980.cafe24.com/www/... → http://jyk980.cafe24.com/...
7. 모든 링크에 target="_blank" rel="noopener noreferrer" 필수
8. JavaScript, <form>, position:absolute/fixed 사용 금지
9. 반응형: 모바일에서 단일 컬럼으로 자연스럽게 변환
10. 한국어 폰트: '맑은 고딕','Malgun Gothic',sans-serif

## 콘텐츠 규칙
1. 제목은 자연스럽고 전문적인 톤
2. 수신자 개인화: {{name}}님 형태로 인사
3. CTA 버튼 1~2개 포함
4. 하단에 회사 정보와 수신거부 링크 필수:
   - (주)디지우드 | 대표: 정연권
   - 수신거부: <a href="{{unsubscribe_url}}">수신거부</a>

## 사용 가능한 변수
- {{name}} - 수신자 이름
- {{company}} - 수신자 회사명
- {{unsubscribe_url}} - 수신거부 URL

## 출력 형식
반드시 아래 JSON 형식으로만 응답해주세요:
```json
{
  "subject": "이메일 제목 (한국어, 50자 이내)",
  "html_content": "<!DOCTYPE html><html>...(완전한 HTML)...</html>",
  "text_content": "텍스트 전용 버전 (HTML 태그 없이)"
}
```
"""

SYSTEM_PROMPT_EDIT = """당신은 한국 B2B 제조업체(디지우드/Digiwood)의 이메일 마케팅 전문가입니다.

사용자가 기존 이메일 HTML 템플릿과 수정 요청을 보내면, **요청한 부분만 정확히 수정**하고 나머지는 그대로 유지합니다.

## 핵심 규칙
1. 사용자가 수정을 요청한 부분만 변경하세요
2. 수정 요청에 언급되지 않은 부분은 절대 변경하지 마세요
3. 기존 인라인 스타일, 테이블 구조, 변수를 그대로 유지하세요

## 출력 형식
```json
{
  "subject": "수정된 이메일 제목 (변경 요청 없으면 기존 그대로)",
  "html_content": "<!DOCTYPE html><html>...(수정된 완전한 HTML)...</html>",
  "text_content": "텍스트 전용 버전"
}
```
"""


def sanitize_ftp_urls(html: str) -> str:
    """FTP URL을 HTTP URL로 변환"""
    return re.sub(
        r"ftp://(?:[^@]+@)?jyk980\.cafe24\.com/www/",
        "http://jyk980.cafe24.com/",
        html,
    )


# === JSON 요청용 스키마 ===

class MailingGenerateJsonRequest(BaseModel):
    prompt: str
    product_name: Optional[str] = None
    target_audience: Optional[str] = None
    category: Optional[str] = None
    additional_notes: Optional[str] = None
    existing_html: Optional[str] = None
    existing_subject: Optional[str] = None


# === API 엔드포인트 ===

@router.post("/templates/generate")
async def generate_email_template(
    prompt: str = Form(None),
    product_name: str = Form(None),
    target_audience: str = Form(None),
    category: str = Form(None),
    additional_notes: str = Form(None),
    existing_html: str = Form(None),
    existing_subject: str = Form(None),
    files: list[UploadFile] = File(None),
):
    """메일 템플릿 AI 생성 (FormData + JSON 모두 지원)"""

    # prompt가 없으면 JSON body 시도
    if not prompt:
        raise HTTPException(status_code=400, detail="프롬프트를 입력해주세요.")

    api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_AI_API_KEY 환경변수가 설정되지 않았습니다")

    genai.configure(api_key=api_key)

    is_edit_mode = bool(existing_html)

    # 로고 URL 조회
    logo_url = None
    try:
        supabase = get_supabase()
        res = supabase.table("mail_settings") \
            .select("setting_value") \
            .eq("setting_key", "header_logo") \
            .single() \
            .execute()
        if res.data:
            logo_url = (res.data.get("setting_value") or {}).get("url")
    except Exception:
        pass

    # parts 구성
    parts = []

    if is_edit_mode:
        edit_prompt = f'## 기존 이메일 제목\n{existing_subject or "(없음)"}\n\n## 기존 이메일 HTML\n```html\n{existing_html}\n```\n\n## 수정 요청\n{prompt}'
        if additional_notes:
            edit_prompt += f"\n추가 참고: {additional_notes}"
        parts.append(edit_prompt)
    else:
        # 사용자 프롬프트 구성
        user_prompt = f"## 사용자 요청\n{prompt}\n"
        if product_name:
            user_prompt += f"\n제품/서비스: {product_name}"
        if target_audience:
            target = TARGET_LABELS.get(target_audience, "일반 고객")
            user_prompt += f"\n대상 고객: {target}"
        if category:
            cat = CATEGORY_LABELS.get(category, "뉴스레터")
            user_prompt += f"\n메일 유형: {cat}"
        if logo_url:
            user_prompt += f'\n\n## 헤더 로고\n이메일 최상단 헤더에 아래 로고 이미지를 사용해주세요:\n<img src="{logo_url}" alt="디지우드 로고" width="180" style="display:block;margin:0 auto;max-width:180px;height:auto;">'
        if additional_notes:
            user_prompt += f"\n추가 요청: {additional_notes}"
        parts.append(user_prompt)

    # 파일 첨부 → Gemini inlineData
    if files:
        for f in files:
            if f.content_type and f.content_type.startswith("image/"):
                content = await f.read()
                b64 = base64.b64encode(content).decode()
                parts.append(f"[첨부 이미지: {f.filename}] 이 이미지를 이메일 본문에 적절히 활용해주세요:")
                parts.append({"inline_data": {"data": b64, "mime_type": f.content_type}})
            else:
                parts.append(f"[첨부 문서: {f.filename}] 이 문서가 첨부되어 있습니다. 이메일 본문에서 이 문서를 언급해주세요.")

    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=SYSTEM_PROMPT_EDIT if is_edit_mode else SYSTEM_PROMPT_CREATE,
        generation_config=genai.GenerationConfig(
            temperature=0.3 if is_edit_mode else 0.7,
            max_output_tokens=16384,
        ),
    )

    try:
        response = model.generate_content(parts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API 오류: {str(e)}")

    response_text = response.text
    if not response_text:
        raise HTTPException(status_code=500, detail="Gemini로부터 빈 응답을 받았습니다")

    # JSON 추출
    json_match = re.search(r"```json\s*\n?([\s\S]*?)\n?```", response_text)
    parsed = None

    if json_match:
        parsed = json.loads(json_match.group(1))
    else:
        trimmed = response_text.strip()
        if trimmed.startswith("{"):
            parsed = json.loads(trimmed)
        else:
            raise HTTPException(status_code=500, detail="응답에서 JSON을 추출할 수 없습니다")

    if not parsed.get("subject") or not parsed.get("html_content"):
        raise HTTPException(status_code=500, detail="응답에 subject 또는 html_content가 없습니다")

    # FTP URL → HTTP URL 변환
    parsed["html_content"] = sanitize_ftp_urls(parsed["html_content"])

    return {
        "success": True,
        "subject": parsed["subject"],
        "html_content": parsed["html_content"],
        "text_content": parsed.get("text_content", ""),
    }


@router.post("/templates/generate-json")
async def generate_email_template_json(body: MailingGenerateJsonRequest):
    """메일 템플릿 AI 생성 (JSON 전용)"""
    # Form 엔드포인트 재활용
    return await generate_email_template(
        prompt=body.prompt,
        product_name=body.product_name,
        target_audience=body.target_audience,
        category=body.category,
        additional_notes=body.additional_notes,
        existing_html=body.existing_html,
        existing_subject=body.existing_subject,
        files=None,
    )
