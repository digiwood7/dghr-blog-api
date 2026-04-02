"""
Webhook Service
d-onworks 포트폴리오 자동 연동을 위한 webhook 발송
"""
import os
import httpx
from datetime import datetime, timezone


def send_publish_webhook(project: dict, content: dict, photos: list[dict]) -> dict:
    """발행 완료 시 d-onworks에 webhook POST 전송

    Args:
        project: blog_projects 레코드
        content: blog_contents 레코드
        photos: blog_photos 레코드 목록 (display_order 순)

    Returns:
        webhook 응답 dict (success, action, project 등)

    Raises:
        환경변수 미설정이나 전송 실패 시 예외 발생
    """
    webhook_url = os.getenv("DONWORKS_WEBHOOK_URL")
    webhook_secret = os.getenv("DONWORKS_WEBHOOK_SECRET")

    if not webhook_url:
        raise ValueError("DONWORKS_WEBHOOK_URL 환경변수가 설정되지 않았습니다")
    if not webhook_secret:
        raise ValueError("DONWORKS_WEBHOOK_SECRET 환경변수가 설정되지 않았습니다")

    # 사진 목록 구성 (display_order 순)
    photo_list = [
        {"url": p["ftp_url"], "order": p.get("display_order", 0)}
        for p in photos
        if p.get("ftp_url")
    ]

    payload = {
        "event": "blog.published",
        "project_id": project["id"],
        "title": content.get("title", project.get("name", "")),
        "content_html": content.get("content_html", ""),
        "description": content.get("title", ""),
        "tags": content.get("tags", []),
        "thumbnail_url": photo_list[0]["url"] if photo_list else None,
        "photos": photo_list,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "secret": webhook_secret,
    }

    response = httpx.post(webhook_url, json=payload, timeout=30.0)
    response.raise_for_status()
    return response.json()
