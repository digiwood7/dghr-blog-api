"""
Generate Router
AI 글 생성 API 엔드포인트
"""
import json
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone, timedelta

# 한국 시간대 (UTC+9)
KST = timezone(timedelta(hours=9))

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


def create_sse_message(event: str, data: dict) -> str:
    """SSE 메시지 포맷 생성"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/{project_id}/generate-stream")
async def generate_blog_content_stream(project_id: str, keywords: str = ""):
    """AI 블로그 글 생성 (SSE 스트리밍)"""

    async def event_generator():
        try:
            # Step 1: 프로젝트 확인
            yield create_sse_message("progress", {
                "step": 1,
                "total": 5,
                "message": "프로젝트 확인 중...",
                "percent": 5
            })
            await asyncio.sleep(0.1)

            project = get_project(project_id)
            if not project:
                yield create_sse_message("error", {"message": "프로젝트를 찾을 수 없습니다"})
                return

            project_name = project.get("name", "")
            ftp_path = project.get("ftp_path", "")
            # 설정은 글로벌 공유이므로 "global" ID 사용
            settings_user_id = "global"

            # Step 2: 사진 목록 조회
            yield create_sse_message("progress", {
                "step": 2,
                "total": 5,
                "message": "이미지 다운로드 중...",
                "percent": 15
            })
            await asyncio.sleep(0.1)

            photos = get_photos(project_id)
            if not photos:
                yield create_sse_message("error", {"message": "업로드된 사진이 없습니다"})
                return

            image_urls = [p.get("ftp_url", "") for p in photos if p.get("ftp_url")]
            if not image_urls:
                yield create_sse_message("error", {"message": "유효한 이미지 URL이 없습니다"})
                return

            yield create_sse_message("progress", {
                "step": 2,
                "total": 5,
                "message": f"이미지 {len(image_urls)}장 준비 완료",
                "percent": 20
            })
            await asyncio.sleep(0.1)

            # 상태 업데이트: 분석 중
            update_project_status(project_id, "analyzing")

            # Step 3: 이미지 분석
            yield create_sse_message("progress", {
                "step": 3,
                "total": 5,
                "message": "AI 이미지 분석 중...",
                "percent": 30
            })

            analysis_result = analyze_images_with_gemini(image_urls, project_name)
            if "error" in analysis_result:
                yield create_sse_message("error", {"message": f"이미지 분석 실패: {analysis_result['error']}"})
                return

            yield create_sse_message("progress", {
                "step": 3,
                "total": 5,
                "message": "이미지 분석 완료",
                "percent": 50
            })
            await asyncio.sleep(0.1)

            # Step 4: 블로그 글 생성
            yield create_sse_message("progress", {
                "step": 4,
                "total": 5,
                "message": "블로그 글 작성 중...",
                "percent": 60
            })

            keyword_list = [k.strip() for k in keywords.split(",")] if keywords else analysis_result.get("main_keywords", [])
            blog_result = generate_blog_with_gemini(analysis_result, keyword_list, project_name, image_urls, settings_user_id)
            if "error" in blog_result:
                yield create_sse_message("error", {"message": f"글 생성 실패: {blog_result['error']}"})
                return

            title = blog_result.get("title", "")
            content_html = blog_result.get("content_html", "")
            tags = blog_result.get("tags", [])

            yield create_sse_message("progress", {
                "step": 4,
                "total": 5,
                "message": "블로그 글 작성 완료",
                "percent": 80
            })
            await asyncio.sleep(0.1)

            # Step 5: 저장
            yield create_sse_message("progress", {
                "step": 5,
                "total": 5,
                "message": "저장 중...",
                "percent": 85
            })

            # DB 저장
            save_content(project_id, title, content_html, tags)

            # FTP에 HTML 파일 저장
            html_url = None
            if ftp_path:
                html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: 'Noto Sans KR', sans-serif; max-width: 740px; margin: 0 auto; padding: 20px; font-size: 16px; line-height: 1.8; color: #333; }}
        h2 {{ font-size: 22px; font-weight: 700; margin-top: 32px; margin-bottom: 14px; color: #111; }}
        h3 {{ font-size: 19px; font-weight: 700; margin-top: 28px; margin-bottom: 12px; color: #222; }}
        p {{ font-size: 16px; margin-bottom: 18px; }}
        img {{ max-width: 100%; width: 100%; height: auto; border-radius: 6px; margin: 20px 0; display: block; }}
        figure {{ text-align: center; margin: 20px 0; }}
        figcaption {{ font-size: 13px; color: #888; margin-top: 8px; }}
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

                kst_now = datetime.now(KST)
                html_filename = f"blog_{kst_now.strftime('%Y%m%d_%H%M%S')}.html"
                remote_path = f"{ftp_path}/drafts/{html_filename}"

                try:
                    with Cafe24FTP() as ftp:
                        html_url = ftp.upload_bytes(html_content.encode("utf-8"), remote_path)
                except Exception as ftp_err:
                    print(f"FTP HTML save warning: {ftp_err}")

            # 상태 업데이트: 생성 완료
            update_project_status(project_id, "generated")

            yield create_sse_message("progress", {
                "step": 5,
                "total": 5,
                "message": "완료!",
                "percent": 100
            })

            # 최종 결과 전송
            debug_info = blog_result.get("debug", {})
            yield create_sse_message("complete", {
                "title": title,
                "content_html": content_html,
                "tags": tags,
                "html_url": html_url,
                "debug": debug_info
            })

        except Exception as e:
            yield create_sse_message("error", {"message": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )


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
        # 설정은 글로벌 공유이므로 "global" ID 사용
        settings_user_id = "global"

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

        # Step 2: 블로그 글 생성 (참고 URL 포함)
        keywords = data.keywords if data and data.keywords else analysis_result.get("main_keywords", [])
        blog_result = generate_blog_with_gemini(analysis_result, keywords, project_name, image_urls, settings_user_id)
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
        body {{ font-family: 'Noto Sans KR', sans-serif; max-width: 740px; margin: 0 auto; padding: 20px; font-size: 16px; line-height: 1.8; color: #333; }}
        h2 {{ font-size: 22px; font-weight: 700; margin-top: 32px; margin-bottom: 14px; color: #111; }}
        h3 {{ font-size: 19px; font-weight: 700; margin-top: 28px; margin-bottom: 12px; color: #222; }}
        p {{ font-size: 16px; margin-bottom: 18px; }}
        img {{ max-width: 100%; width: 100%; height: auto; border-radius: 6px; margin: 20px 0; display: block; }}
        figure {{ text-align: center; margin: 20px 0; }}
        figcaption {{ font-size: 13px; color: #888; margin-top: 8px; }}
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

            # 한국 시간 기준으로 파일명 생성
            kst_now = datetime.now(KST)
            html_filename = f"blog_{kst_now.strftime('%Y%m%d_%H%M%S')}.html"
            remote_path = f"{ftp_path}/drafts/{html_filename}"

            try:
                with Cafe24FTP() as ftp:
                    html_url = ftp.upload_bytes(html_content.encode("utf-8"), remote_path)
            except Exception as ftp_err:
                print(f"FTP HTML save warning: {ftp_err}")

        # 상태 업데이트: 생성 완료
        update_project_status(project_id, "generated")

        # 디버그 정보 추출
        debug_info = blog_result.get("debug", {})

        return GenerateResponse(
            title=title,
            content_html=content_html,
            tags=tags,
            html_url=html_url,
            debug=debug_info,
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
