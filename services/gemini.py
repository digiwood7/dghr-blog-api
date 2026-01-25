"""
Gemini AI Service
이미지 분석 및 블로그 글 생성
"""
import os
import json
import google.generativeai as genai
import httpx


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


def generate_blog_with_gemini(analysis: dict, keywords: list, project_name: str, image_urls: list) -> dict:
    """
    분석 결과를 바탕으로 블로그 글 생성

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

    prompt = f"""
블로그 글을 작성해주세요.

프로젝트: {project_name}
테마: {analysis.get('overall_theme', '')}
메인 키워드: {main_keyword} (5회 이상 자연스럽게 반복)
이미지 URL: {json.dumps(image_urls)}

작성 규칙:
1. 인트로 (100-150자)
2. 본문 (500-1500자, 소제목 포함)
3. 이미지마다 <img src="URL"> 와 설명 포함
4. 마무리 (50-100자)
5. 태그 5-10개

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
