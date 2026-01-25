"""
Generate Router
AI 글 생성 API 엔드포인트
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime

from schemas.blog import (
    GenerateRequest,
    GenerateResponse,
    ContentResponse,
)
from services.database import (
    get_project,
    get_photos,
    get_content,
    save_content,
    update_project_status,
)
from services.gemini import analyze_images_with_gemini, generate_blog_with_gemini
from services.ftp import Cafe24FTP

router = APIRouter(prefix="/api/blog/projects", tags=["generate"])


@router.post("/{project_id}/generate", response_model=GenerateResponse)
async def generate_blog_content(project_id: str, data: GenerateRequest = None):
    """AI 블로그 글 생성"""
    try:
        # 프로젝트 확인
        project = get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        project_name = project.get("name", "")
        ftp_path = project.get("ftp_path", "")

        # 사진 목록 조회
        photos = get_photos(project_id)
        if not photos:
            raise HTTPException(status_code=400, detail="업로드된 사진이 없습니다")

        image_urls = [p.get("ftp_url", "") for p in photos if p.get("ftp_url")]
        if not image_urls:
            raise HTTPException(status_code=400, detail="유효한 이미지 URL이 없습니다")

        # 상태 업데이트: 분석 중
        update_project_status(project_id, "analyzing")

        # Step 1: 이미지 분석
        analysis_result = analyze_images_with_gemini(image_urls, project_name)
        if "error" in analysis_result:
            raise HTTPException(status_code=500, detail=f"이미지 분석 실패: {analysis_result['error']}")

        # Step 2: 블로그 글 생성
        keywords = data.keywords if data and data.keywords else analysis_result.get("main_keywords", [])
        blog_result = generate_blog_with_gemini(analysis_result, keywords, project_name, image_urls)
        if "error" in blog_result:
            raise HTTPException(status_code=500, detail=f"글 생성 실패: {blog_result['error']}")

        title = blog_result.get("title", "")
        content_html = blog_result.get("content_html", "")
        tags = blog_result.get("tags", [])

        # Step 3: DB 저장
        save_content(project_id, title, content_html, tags)

        # Step 4: FTP에 HTML 파일 저장
        html_url = None
        if ftp_path:
            html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: 'Noto Sans KR', sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        img {{ max-width: 100%; height: auto; }}
        .tags {{ margin-top: 20px; }}
        .tag {{ display: inline-block; background: #e0e0e0; padding: 5px 10px; margin: 5px; border-radius: 15px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    {content_html}
    <div class="tags">
        {''.join([f'<span class="tag">#{tag}</span>' for tag in tags])}
    </div>
</body>
</html>"""

            html_filename = f"blog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            remote_path = f"{ftp_path}/drafts/{html_filename}"

            try:
                with Cafe24FTP() as ftp:
                    html_url = ftp.upload_bytes(html_content.encode("utf-8"), remote_path)
            except Exception as ftp_err:
                print(f"FTP HTML save warning: {ftp_err}")

        # 상태 업데이트: 생성 완료
        update_project_status(project_id, "generated")

        return GenerateResponse(
            title=title,
            content_html=content_html,
            tags=tags,
            html_url=html_url,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/content", response_model=ContentResponse)
async def get_project_content(project_id: str):
    """생성된 글 조회"""
    try:
        # 프로젝트 확인
        project = get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        content = get_content(project_id)
        if not content:
            return ContentResponse()

        return ContentResponse(
            id=content.get("id"),
            project_id=content.get("project_id"),
            title=content.get("title", ""),
            content_html=content.get("content_html", ""),
            tags=content.get("tags", []),
            created_at=content.get("created_at"),
            updated_at=content.get("updated_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
