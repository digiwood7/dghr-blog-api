"""
Gemini AI Service
이미지 분석 및 블로그 글 생성
"""
import os
import json
import google.generativeai as genai
import httpx

from .database import get_reference_urls, get_project


def fetch_url_content(url: str, max_length: int = 5000) -> str:
    """URL에서 텍스트 콘텐츠 추출"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = httpx.get(url, timeout=15.0, headers=headers, follow_redirects=True)
        if resp.status_code != 200:
            return ""

        content = resp.text

        # 간단한 HTML 태그 제거
        import re
        # script, style 태그 제거
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
        # HTML 태그 제거
        content = re.sub(r'<[^>]+>', ' ', content)
        # 여러 공백을 하나로
        content = re.sub(r'\s+', ' ', content).strip()

        return content[:max_length] if len(content) > max_length else content
    except Exception as e:
        print(f"URL fetch failed ({url}): {e}")
        return ""


def get_reference_content(user_id: str) -> str:
    """사용자의 참고 URL들에서 콘텐츠 수집"""
    urls = get_reference_urls(user_id)
    if not urls:
        return ""

    reference_texts = []
    for url_data in urls[:5]:  # 최대 5개 URL만 사용
        url = url_data.get("url", "")
        title = url_data.get("title", "")
        content = fetch_url_content(url, max_length=3000)

        if content:
            reference_texts.append(f"[참고글: {title or url}]\n{content[:2000]}")

    if reference_texts:
        return "\n\n---\n\n".join(reference_texts)
    return ""


def analyze_images_with_gemini(image_urls: list[str], project_name: str) -> dict:
    """
    이미지들을 분석하여 블로그 글 작성에 필요한 정보 추출

    Returns:
        {
            "suggested_title": "추천 블로그 제목",
            "overall_theme": "전체 테마 설명",
            "main_keywords": ["키워드1", "키워드2", ...],
            "images": [
                {"description": "이미지 설명", "category": "전시부스|인테리어|사인물|기타", "caption": "추천 캡션"}
            ]
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

        return json.loads(text.strip())
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
    분석 결과를 바탕으로 블로그 글 생성
    참고 URL이 있으면 해당 글의 스타일과 형식을 참고하여 작성

    Returns:
        {
            "title": "블로그 제목",
            "content_html": "<article>HTML 내용</article>",
            "tags": ["태그1", "태그2"]
        }
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_API_KEY not set"}

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash-exp")

    main_keyword = keywords[0] if keywords else project_name

    # 참고 URL 콘텐츠 가져오기
    reference_content = ""
    if user_id:
        reference_content = get_reference_content(user_id)

    # 참고 콘텐츠가 있으면 프롬프트에 추가
    reference_section = ""
    if reference_content:
        reference_section = f"""
=== 참고 블로그 글 (스타일, 톤, 형식 참고) ===
{reference_content}
=== 참고 블로그 끝 ===

위 참고 글들의 스타일, 톤, 문장 구조를 분석하고 비슷한 느낌으로 작성해주세요.
"""

    prompt = f"""
블로그 글을 작성해주세요.

프로젝트: {project_name}
테마: {analysis.get('overall_theme', '')}
메인 키워드: {main_keyword} (5회 이상 자연스럽게 반복)
이미지 URL: {json.dumps(image_urls)}
{reference_section}
작성 규칙:
1. 인트로 (100-150자) - 독자의 관심을 끄는 문장으로 시작
2. 본문 (500-1500자, 소제목 포함) - 전문적이면서도 친근한 톤
3. 이미지마다 <img src="URL"> 와 설명 포함 - 이미지 설명은 자연스럽게
4. 마무리 (50-100자) - 행동을 유도하는 문장
5. 태그 5-10개

HTML 형식 규칙:
- <article> 태그로 전체 감싸기
- 소제목은 <h3> 태그 사용
- 문단은 <p> 태그 사용
- 이미지는 <figure><img src="URL" alt="설명"><figcaption>캡션</figcaption></figure> 형식

JSON 응답:
{{
    "title": "블로그 제목",
    "content_html": "<article>HTML 내용</article>",
    "tags": ["태그1", "태그2"]
}}
"""

    try:
        response = model.generate_content(prompt)
        text = response.text

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        return json.loads(text.strip())
    except Exception as e:
        return {"error": str(e)}
