"""
Gemini AI Service
이미지 분석 및 블로그 글 생성

Flow: 이미지 분석 → 페르소나 참조 → URL 참고 → 블로그 글 작성
"""
import os
import json
import re
from datetime import datetime
import google.generativeai as genai
import httpx

from .database import get_reference_urls, get_settings


def fetch_url_content(url: str, max_length: int = 5000) -> dict:
    """
    URL에서 텍스트 콘텐츠 추출
    Returns: {"url": url, "content": str, "success": bool, "error": str}
    """
    result = {"url": url, "content": "", "success": False, "error": ""}

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        resp = httpx.get(url, timeout=30.0, headers=headers, follow_redirects=True)

        if resp.status_code != 200:
            result["error"] = f"HTTP {resp.status_code}"
            return result

        content = resp.text

        # HTML 태그 제거
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<noscript[^>]*>.*?</noscript>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        content = re.sub(r'<[^>]+>', ' ', content)
        content = re.sub(r'\s+', ' ', content).strip()

        # 길이 제한 없이 콘텐츠 반환 (빈 문자열도 허용)
        result["content"] = content[:max_length] if content else ""
        result["success"] = True  # 콘텐츠 추출 성공
        return result

    except Exception as e:
        result["error"] = str(e)
        return result


def get_reference_content_with_debug(user_id: str) -> dict:
    """
    사용자의 참고 URL들에서 콘텐츠 수집 (디버그 정보 포함)

    Returns: {
        "urls_found": int,
        "urls_fetched": int,
        "url_details": [{"url": str, "title": str, "success": bool, "content_length": int, "error": str}],
        "combined_content": str
    }
    """
    debug_info = {
        "urls_found": 0,
        "urls_fetched": 0,
        "url_details": [],
        "combined_content": ""
    }

    urls = get_reference_urls(user_id)
    debug_info["urls_found"] = len(urls) if urls else 0

    if not urls:
        return debug_info

    reference_texts = []

    for url_data in urls[:5]:  # 최대 5개
        url = url_data.get("url", "")
        title = url_data.get("title", "")

        fetch_result = fetch_url_content(url, max_length=3000)

        url_detail = {
            "url": url,
            "title": title,
            "success": fetch_result["success"],
            "content_length": len(fetch_result["content"]),
            "error": fetch_result["error"],
            "preview": fetch_result["content"][:200] + "..." if fetch_result["content"] else ""
        }
        debug_info["url_details"].append(url_detail)

        if fetch_result["success"]:
            debug_info["urls_fetched"] += 1
            reference_texts.append(f"[참고글: {title or url}]\n{fetch_result['content'][:2000]}")

    if reference_texts:
        debug_info["combined_content"] = "\n\n---\n\n".join(reference_texts)

    return debug_info


def get_persona_with_debug(user_id: str) -> dict:
    """
    사용자 페르소나 설정 가져오기 (디버그 정보 포함)

    Returns: {
        "has_persona": bool,
        "persona_text": str,
        "persona_length": int
    }
    """
    debug_info = {
        "has_persona": False,
        "persona_text": "",
        "persona_length": 0
    }

    persona = get_settings(user_id, "blog_persona", None)

    if persona and isinstance(persona, str) and len(persona.strip()) > 0:
        debug_info["has_persona"] = True
        debug_info["persona_text"] = persona.strip()
        debug_info["persona_length"] = len(persona.strip())

    return debug_info


def analyze_images_with_gemini(image_urls: list[str], project_name: str) -> dict:
    """
    Step 1: 이미지 분석

    Returns:
        {
            "suggested_title": "추천 블로그 제목",
            "overall_theme": "전체 테마 설명",
            "main_keywords": ["키워드1", "키워드2", ...],
            "images": [
                {"description": "이미지 설명", "category": "전시부스|인테리어|사인물|기타", "caption": "추천 캡션"}
            ],
            "debug": {"images_processed": int, "model": str}
        }
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_API_KEY not set"}

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash-exp")

    # Download images
    image_parts = []
    for url in image_urls:
        try:
            resp = httpx.get(url, timeout=30.0)
            if resp.status_code == 200:
                image_parts.append({
                    "mime_type": resp.headers.get("content-type", "image/jpeg"),
                    "data": resp.content
                })
        except Exception as e:
            print(f"Image download failed: {e}")

    if not image_parts:
        return {"error": "이미지를 다운로드할 수 없습니다"}

    prompt = f"""
이미지들을 분석해서 블로그 글 작성에 필요한 정보를 추출해주세요.
프로젝트: {project_name}

JSON 형식으로 응답:
{{
    "suggested_title": "추천 블로그 제목",
    "overall_theme": "전체 테마 설명",
    "main_keywords": ["키워드1", "키워드2", ...],
    "images": [
        {{"description": "이미지 설명", "category": "전시부스|인테리어|사인물|기타", "caption": "추천 캡션"}}
    ]
}}
"""

    try:
        contents = [prompt] + image_parts
        response = model.generate_content(contents)
        text = response.text

        # Parse JSON
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        result = json.loads(text.strip())
        result["debug"] = {
            "images_processed": len(image_parts),
            "model": "gemini-2.0-flash-exp"
        }
        return result
    except Exception as e:
        return {"error": str(e)}


def generate_blog_with_gemini(
    analysis: dict,
    keywords: list,
    project_name: str,
    image_urls: list,
    user_id: str = None
) -> dict:
    """
    블로그 글 생성 (전체 플로우)

    Flow:
    1. 이미지 분석 결과 수신 (analysis)
    2. 페르소나 로드
    3. 참고 URL 콘텐츠 로드
    4. 통합 프롬프트로 블로그 글 생성

    Returns:
        {
            "title": str,
            "content_html": str,
            "tags": list,
            "debug": {
                "timestamp": str,
                "persona": {...},
                "reference_urls": {...},
                "prompt_sections": {...},
                "full_prompt_length": int
            }
        }
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_API_KEY not set"}

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash-exp")

    # 디버그 정보 초기화
    debug_info = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "persona": {},
        "reference_urls": {},
        "prompt_sections": {
            "has_persona": False,
            "has_reference": False,
            "persona_preview": "",
            "reference_preview": ""
        },
        "full_prompt_length": 0,
        "model": "gemini-2.0-flash-exp"
    }

    main_keyword = keywords[0] if keywords else project_name

    # ============================================================
    # Step 2: 페르소나 로드
    # ============================================================
    persona_section = ""
    if user_id:
        persona_debug = get_persona_with_debug(user_id)
        debug_info["persona"] = persona_debug

        if persona_debug["has_persona"]:
            debug_info["prompt_sections"]["has_persona"] = True
            debug_info["prompt_sections"]["persona_preview"] = persona_debug["persona_text"][:200] + "..."

            persona_section = f"""
╔══════════════════════════════════════════════════════════════╗
║                    작성자 페르소나 (필수 준수)                    ║
╚══════════════════════════════════════════════════════════════╝

{persona_debug["persona_text"]}

위 페르소나의 말투, 어조, 글쓰기 스타일을 반드시 따라주세요.
페르소나가 설정한 특징들을 글 전체에 일관되게 적용해야 합니다.

"""

    # ============================================================
    # Step 3: 참고 URL 콘텐츠 로드
    # ============================================================
    reference_section = ""
    if user_id:
        ref_debug = get_reference_content_with_debug(user_id)
        debug_info["reference_urls"] = ref_debug

        if ref_debug["urls_fetched"] > 0:
            debug_info["prompt_sections"]["has_reference"] = True
            debug_info["prompt_sections"]["reference_preview"] = ref_debug["combined_content"][:300] + "..."

            reference_section = f"""
╔══════════════════════════════════════════════════════════════╗
║              참고 블로그 글 ({ref_debug["urls_fetched"]}개)                  ║
╚══════════════════════════════════════════════════════════════╝

아래 블로그 글들의 문체, 구성, 톤앤매너를 분석하고 유사하게 작성하세요:

{ref_debug["combined_content"]}

참고 글에서 배울 점:
- 문장 길이와 리듬
- 단락 구성 방식
- 독자에게 말하는 어조
- 전문 용어 사용 수준
- 이미지 설명 방식

"""

    # ============================================================
    # Step 4: 블로그 글 생성
    # ============================================================
    prompt = f"""당신은 블로그 글 작성 전문가입니다.

{persona_section}
{reference_section}
╔══════════════════════════════════════════════════════════════╗
║                      블로그 글 작성 요청                       ║
╚══════════════════════════════════════════════════════════════╝

프로젝트명: {project_name}
분석된 테마: {analysis.get('overall_theme', '')}
메인 키워드: {main_keyword}
이미지 URL 목록: {json.dumps(image_urls, ensure_ascii=False)}

【작성 지침】
1. 인트로 (100-150자)
   - 독자의 호기심을 자극하는 문장으로 시작
   - 메인 키워드를 자연스럽게 포함

2. 본문 (800-1500자)
   - 소제목을 활용한 구조적 글쓰기
   - 메인 키워드 "{main_keyword}"를 5회 이상 자연스럽게 반복
   - 각 이미지에 대한 설명 포함
   - 전문적이면서도 친근한 톤 유지

3. 이미지 배치
   - 각 이미지마다 <figure> 태그 사용
   - 이미지 설명은 자연스럽게 본문에 녹여내기

4. 마무리 (50-100자)
   - 독자의 행동을 유도하는 CTA(Call-to-Action)

5. 태그
   - 관련 태그 5-10개 생성

【HTML 형식】
- 전체를 <article> 태그로 감싸기
- 소제목: <h3>
- 문단: <p>
- 이미지: <figure><img src="URL" alt="설명"><figcaption>캡션</figcaption></figure>

【중요】
- 페르소나가 설정되어 있다면 그 말투와 스타일을 우선 적용
- 참고 글이 있다면 그 구성과 톤을 참고하여 작성
- 키워드를 억지로 넣지 말고 자연스럽게 녹여내기

JSON 형식으로만 응답하세요:
{{
    "title": "블로그 제목 (키워드 포함, 50자 이내)",
    "content_html": "<article>완성된 HTML</article>",
    "tags": ["태그1", "태그2", "태그3", ...]
}}
"""

    debug_info["full_prompt_length"] = len(prompt)

    try:
        response = model.generate_content(prompt)
        text = response.text

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        result = json.loads(text.strip())
        result["debug"] = debug_info

        return result

    except Exception as e:
        return {"error": str(e), "debug": debug_info}
