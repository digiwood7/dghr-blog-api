"""
honey_orders.instruction_html → FTP 마이그레이션 1회성 스크립트

배경: DB의 instruction_html 컬럼(Fabric.js JSON, 평균 280KB)이 Supabase egress를 폭증시킴.
목표: 모든 기존 데이터를 FTP로 옮기고 DB에는 URL만 남김.

실행:
    cd C:/src/test/dghr-blog-api
    # 필요 환경변수: SUPABASE_ACCESS_TOKEN, FTP_PASS (services/ftp.py가 참조)
    python scripts/migrate_instruction_html.py

안전장치:
    - 이미 instruction_html_url 이 채워진 행은 skip
    - 각 건 업로드 성공 후에만 DB UPDATE
    - 건별 실패해도 계속 진행 (결과 요약 출력)
    - DRY_RUN=1 환경변수로 업로드/업데이트 없이 목록만 확인 가능
"""
import os
import sys
import json
from datetime import datetime

import requests

# 상위 폴더 import 가능하도록
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.ftp import Cafe24FTP  # noqa: E402

PROJECT_REF = "spamcydtxzuelpsjbvkp"
ACCESS_TOKEN = os.getenv("SUPABASE_ACCESS_TOKEN")
DRY_RUN = os.getenv("DRY_RUN") == "1"

if not ACCESS_TOKEN:
    print("ERROR: SUPABASE_ACCESS_TOKEN 환경변수 필요")
    sys.exit(1)


def supabase_sql(query: str):
    """Supabase Management API로 SQL 실행"""
    res = requests.post(
        f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query",
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
        json={"query": query},
        timeout=60,
    )
    res.raise_for_status()
    return res.json()


def fetch_pending_orders():
    """마이그레이션 대상: instruction_html IS NOT NULL AND instruction_html_url IS NULL"""
    # id만 먼저 가져오기 (egress 최소화)
    rows = supabase_sql(
        "SELECT id FROM honey_orders "
        "WHERE instruction_html IS NOT NULL AND instruction_html_url IS NULL "
        "ORDER BY created_at"
    )
    return [r["id"] for r in rows]


def fetch_order_html(order_id: str):
    """단건 instruction_html 조회"""
    # SQL injection 방지용: id 는 UUID 형식만 허용
    import re
    if not re.fullmatch(r"[0-9a-fA-F\-]{36}", order_id):
        raise ValueError(f"Invalid order id: {order_id}")
    rows = supabase_sql(
        f"SELECT id, instruction_html FROM honey_orders WHERE id = '{order_id}'"
    )
    if not rows:
        return None
    return rows[0]["instruction_html"]


def update_order_url(order_id: str, url: str):
    """URL 저장 + instruction_html은 NULL 처리"""
    import re
    if not re.fullmatch(r"[0-9a-fA-F\-]{36}", order_id):
        raise ValueError(f"Invalid order id: {order_id}")
    # URL 내 작은따옴표 이스케이프
    safe_url = url.replace("'", "''")
    supabase_sql(
        f"UPDATE honey_orders "
        f"SET instruction_html_url = '{safe_url}', instruction_html = NULL "
        f"WHERE id = '{order_id}'"
    )


def main():
    print(f"[migrate] DRY_RUN={DRY_RUN}")
    print("[migrate] 대상 행 조회 중...")
    order_ids = fetch_pending_orders()
    print(f"[migrate] 대상: {len(order_ids)}건")

    if not order_ids:
        print("[migrate] 할 일 없음. 종료.")
        return

    if DRY_RUN:
        for oid in order_ids[:5]:
            print(f"  - {oid}")
        if len(order_ids) > 5:
            print(f"  ... 외 {len(order_ids) - 5}건")
        return

    success, failed = 0, []

    with Cafe24FTP() as ftp:
        for idx, oid in enumerate(order_ids, 1):
            try:
                print(f"[{idx}/{len(order_ids)}] {oid} ...", end=" ", flush=True)
                html = fetch_order_html(oid)
                if not html:
                    print("본문 없음 → skip")
                    continue

                ts = datetime.now().strftime("%Y%m%d%H%M%S%f")[:18]
                # 신규 저장 로직과 동일한 규칙 (/www/honeyerp/{order.id}/htmls/...) — 이미지도 order.id 기준
                remote_path = f"/www/honeyerp/{oid}/htmls/instruction_{ts}.html"
                url = ftp.upload_bytes(html.encode("utf-8"), remote_path)

                update_order_url(oid, url)
                success += 1
                print(f"OK ({len(html)} bytes)")
            except Exception as e:
                failed.append((oid, str(e)))
                print(f"FAIL: {e}")

    print(f"\n[migrate] 완료: 성공 {success}건, 실패 {len(failed)}건")
    if failed:
        print("실패 목록:")
        for oid, err in failed:
            print(f"  - {oid}: {err}")


if __name__ == "__main__":
    main()
