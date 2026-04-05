"""
ProGen 제안서 프롬프트 템플릿
Vercel lib/progen/proposal-format.ts → Python 이전
"""

REFERENCE_TEMPLATE = """
<div id="proposal-content">
<!-- ===== Page 1: Cover ===== -->
<div class="proposal-page" style="width:297mm;height:210mm;padding:15mm;box-sizing:border-box;position:relative;overflow:hidden;font-family:'Noto Sans KR',sans-serif;color:#333;line-height:1.6;page-break-after:always;background:linear-gradient(135deg, #fdfbf7 70%, rgba(244,143,177,0.2) 100%);display:flex;flex-direction:column;justify-content:center;">
  <div style="flex:1;display:flex;flex-direction:column;justify-content:center;">
    <div style="font-size:24px;color:#8D6E63;font-weight:700;margin-bottom:20px;">Eco-Blossom Camping</div>
    <div style="font-size:48px;font-weight:900;color:#2E7D32;line-height:1.2;">2026 경남 관광 박람회<br>양산시 홍보관 조성 제안</div>
    <p style="font-size:18px;color:#555;margin-top:20px;">양산의 봄, 친환경을 입다</p>
  </div>
  <div style="border-top:1px solid #ccc;padding-top:20px;font-size:16px;color:#666;">
    <p style="margin:0 0 6px;"><strong>Date:</strong> 2026. 02.</p>
    <p style="margin:0 0 6px;"><strong>Client:</strong> 양산시</p>
    <p style="margin:0;"><strong>Proposer:</strong> 디지우드</p>
  </div>
  <div style="position:absolute;bottom:10mm;right:15mm;font-size:12px;color:#999;">Page 01</div>
</div>

<!-- ===== Page 2: Prologue & Overview ===== -->
<div class="proposal-page" style="width:297mm;height:210mm;padding:15mm;box-sizing:border-box;position:relative;overflow:hidden;font-family:'Noto Sans KR',sans-serif;color:#333;line-height:1.6;font-size:11pt;background-color:#fdfbf7;page-break-after:always;">
  <div style="border-bottom:2px solid #8D6E63;padding-bottom:10px;margin-bottom:20px;display:flex;justify-content:space-between;align-items:flex-end;">
    <h1 style="font-size:24px;color:#2E7D32;font-weight:900;margin:0;">01. PROLOGUE & OVERVIEW</h1>
    <span style="font-size:14px;color:#555;">기획 의도 및 전시 개요</span>
  </div>
  <div style="margin-bottom:30px;">
    <h2 style="font-size:20px;color:#8D6E63;margin-bottom:15px;border-left:5px solid #F48FB1;padding-left:10px;">Concept: Eco-Blossom Camping</h2>
    <p style="font-size:16px;font-weight:bold;margin-bottom:10px;">"가장 설레는 봄의 시작, 양산에서의 친환경 캠핑"</p>
    <p style="font-size:14px;line-height:1.6;color:#555;">컨셉 설명 텍스트...</p>
    <div style="display:flex;gap:10px;margin-top:10px;">
      <span style="background-color:#2E7D32;color:white;padding:5px 12px;border-radius:20px;font-size:12px;">#키워드1</span>
      <span style="background-color:#2E7D32;color:white;padding:5px 12px;border-radius:20px;font-size:12px;">#키워드2</span>
    </div>
  </div>
  <h2 style="font-size:20px;color:#8D6E63;margin-bottom:15px;border-left:5px solid #F48FB1;padding-left:10px;">Exhibition Overview</h2>
  <table style="width:100%;border-collapse:collapse;font-size:14px;">
    <tr>
      <th style="border:1px solid #ddd;padding:10px;background-color:rgba(46,125,50,0.1);color:#2E7D32;width:15%;font-weight:700;">행사명</th>
      <td style="border:1px solid #ddd;padding:10px;color:#555;">전시회명</td>
      <th style="border:1px solid #ddd;padding:10px;background-color:rgba(46,125,50,0.1);color:#2E7D32;width:15%;font-weight:700;">설치 장소</th>
      <td style="border:1px solid #ddd;padding:10px;color:#555;">장소</td>
    </tr>
  </table>
  <div style="position:absolute;bottom:10mm;right:15mm;font-size:12px;color:#999;">Page 02</div>
</div>

<!-- ===== Page 3: Design Visual ===== -->
<div class="proposal-page" style="width:297mm;height:210mm;padding:15mm;box-sizing:border-box;position:relative;overflow:hidden;font-family:'Noto Sans KR',sans-serif;color:#333;line-height:1.6;font-size:11pt;background-color:#fdfbf7;page-break-after:always;">
  <div style="border-bottom:2px solid #8D6E63;padding-bottom:10px;margin-bottom:20px;display:flex;justify-content:space-between;align-items:flex-end;">
    <h1 style="font-size:24px;color:#2E7D32;font-weight:900;margin:0;">02. DESIGN VISUAL</h1>
    <span style="font-size:14px;color:#555;">공간 조감도 및 구성</span>
  </div>
  <div style="display:flex;gap:20px;height:calc(100% - 60px);">
    <div style="flex:0.6;">
      <div style="width:100%;height:100%;background:#eee;border-radius:8px;border:1px solid #ddd;display:flex;justify-content:center;align-items:center;overflow:hidden;">
        <img src="{{IMAGE:0}}" style="width:100%;height:auto;max-height:100%;object-fit:contain;" alt="조감도">
      </div>
    </div>
    <div style="flex:0.4;">
      <h2 style="font-size:20px;color:#8D6E63;margin-bottom:15px;border-left:5px solid #F48FB1;padding-left:10px;">Space Analysis</h2>
      <ul style="font-size:14px;line-height:1.6;color:#555;padding-left:20px;">
        <li><strong>Zone Name:</strong><br>설명</li>
      </ul>
    </div>
  </div>
  <div style="position:absolute;bottom:10mm;right:15mm;font-size:12px;color:#999;">Page 03</div>
</div>

<!-- ===== Page 4~6: 추가 페이지들도 동일한 구조로 작성 ===== -->
</div>""".strip()

# 템플릿 B는 길이가 매우 길어 별도 변수로 분리
REFERENCE_TEMPLATE_B = """
<div id="proposal-content">
<!-- ===== Page 1: Cover ===== -->
<div class="proposal-page" style="width:297mm;height:210mm;padding:0;box-sizing:border-box;position:relative;overflow:hidden;font-family:'Noto Sans KR',sans-serif;color:#1A1A1A;line-height:1.6;page-break-after:always;background:linear-gradient(135deg, #011F1A 0%, #025432 60%, #03694A 100%);">
  <div style="position:absolute;left:0;top:0;width:2mm;height:100%;background:#f39801;"></div>
  <div style="position:absolute;left:18mm;top:22mm;z-index:2;">
    <div style="width:80mm;height:1px;background:#f39801;margin-bottom:3mm;"></div>
    <div style="font-size:8pt;color:#f39801;letter-spacing:4px;font-weight:500;text-transform:uppercase;">ECO-FRIENDLY EXHIBITION BOOTH PROPOSAL</div>
    <div style="margin-top:18mm;font-size:34pt;font-weight:900;color:#FFFFFF;line-height:1.25;">
      프로젝트 제목<br>
      부제목<br>
      <span style="color:#f39801;font-size:22pt;">기획 . 디자인 . 시공</span>
    </div>
    <div style="margin-top:10mm;font-size:12pt;color:rgba(170,204,187,0.8);font-weight:400;">친환경 허니콤보드(종이골판지) 전시 부스</div>
    <div style="width:65mm;height:1px;background:rgba(255,255,255,0.3);margin:8mm 0;"></div>
    <div style="font-size:8.5pt;color:rgba(170,204,187,0.7);line-height:1.8;">
      <strong style="color:rgba(204,221,204,0.9);font-weight:600;">Presented by DIGIWOOD</strong><br>
      Date: 2026.02
    </div>
  </div>
  <div style="position:absolute;right:25mm;top:50%;transform:translateY(-50%);font-size:120pt;color:rgba(255,255,255,0.04);z-index:1;">&#9851;</div>
  <div style="position:absolute;bottom:12mm;right:15mm;font-size:7pt;color:rgba(255,255,255,0.45);letter-spacing:2px;text-transform:uppercase;text-align:right;line-height:1.6;">DIGIWOOD</div>
</div>
<!-- 이하 Template B 페이지 (축약 - 실제로는 전체 포함) -->
</div>""".strip()


def get_system_prompt(template_id: str) -> str:
    is_b = template_id == "B"
    template = REFERENCE_TEMPLATE_B if is_b else REFERENCE_TEMPLATE
    page_count = 0 if is_b else 6

    if is_b:
        page_structure = """## 제안서 구성 -- 반드시 이 순서와 구성을 따르세요
1. 표지 (Cover) - 프로젝트명, 컨셉명, 태그라인, 날짜, 고객/제안사. 어두운 그린 그라데이션 배경, 왼쪽 오렌지 악센트 바. 제안사는 기본값 "DIGIWOOD" 사용
2. 과업 개요 (Executive Summary) - 프로젝트 목표 카드 4개(좌측) + 달성 확약 리스트(우측 그린 패널). 허니콤 패턴 배경
3. 과제 분석 (Context / Why) - 좌측 CHALLENGE(브라운 헤더) + 우측 SOLUTION(그린 헤더) 2열 구성, 하단 KEY INSIGHT 바
4. 배치도 (Space Plan) - 좌측 평면도(Zone 그리드) + 우측 핵심 치수 스펙(그린 패널)
5. 관람 동선 (User Journey) - 4단계 스텝 카드를 가로 화살표로 연결, 각 스텝 상단 색상 악센트, 하단 예상 시간
6~N-2. **공간 전략 (Spatial Strategy)** - [동적 페이지] 이미지 2개씩 한 페이지에 배치. 이미지가 4개면 2페이지, 6개면 3페이지로 나누세요. 각 이미지 카드는 Zone 헤더(헤더 색상 교차: 오렌지/그린/브라운/라이트그린) + 이미지 + 체크리스트. 이미지가 없으면 1페이지로 작성
N-1. 자재 사양 (Technical Specs) - HTML <table> 태그로 작성(thead 그린 배경), 하단 친환경 인증 노트 바
N. 공정표 & 클로징 (Schedule + Closing) - 4개 Phase 카드를 가로 화살표로 연결, 기간+태스크 리스트. 마지막 페이지는 어두운 그린 그라데이션 배경, 인용부호, 헤드라인(화이트+오렌지), 연락처

**[주의] 포트폴리오/Proposed View 페이지는 생성하지 마세요.**"""
    else:
        page_structure = """## 기본 제안서 구성 (6페이지) -- 반드시 이 순서와 구성을 따르세요
1. 표지 (Cover) - 프로젝트명, 컨셉명, 태그라인, 날짜, 고객/제안사
2. 기획 의도 & 전시 개요 - 컨셉 설명, 키워드, 전시 정보 테이블
3. 디자인 비주얼 - 이미지 + 공간 분석
4. 전면 디자인 - 이미지 + 디자인 포인트
5. 상세 공간 - 체험/이벤트 존 상세
6. 소재 & 일정 - 허니콤보드(종이골판지) 특장점, 100% 재활용 친환경, 추진 일정(schedule gantt chart)"""

    if is_b:
        color_note = """## 색상 체계 (Template B)
- Main: #025432 (Dark Green)
- Main Light: #03694A
- Main Dark: #011F1A
- Sub1 (Orange): #f39801
- Sub2 (Brown): #614e40
- Off-white 배경: #F7F6F2
- 텍스트: #1A1A1A (dark), #4A4A4A (mid), #8A8A8A (light)
- 패턴 배경: honeycomb-bg(30deg 반복) 또는 diagonal-bg(45deg 반복) 사용 가능"""
    else:
        color_note = ""

    page_rule_5 = f"**[필수] 반드시 {page_count}페이지를 모두 생성하세요. 절대로 페이지를 생략하지 마세요.**" if page_count > 0 else "**[필수] 위 구성에 따라 모든 페이지를 빠짐없이 생성하세요. Spatial Strategy는 이미지 수에 따라 페이지를 추가하세요.**"
    page_rule_6 = f"**반드시 Page 1부터 Page {page_count}까지 모든 페이지를 빠짐없이 출력하세요.**" if page_count > 0 else "**구성에 명시된 모든 페이지를 빠짐없이 출력하세요.**"

    return f"""당신은 전시부스 제안서를 HTML로 직접 작성하는 전문가입니다.
사용자 정보와 이미지를 분석하여 완전한 HTML 제안서를 생성합니다.

## 핵심 원칙: 양식 준수
- 초안 작성 시 반드시 아래 "레퍼런스 템플릿"의 구조, 레이아웃, 색상 체계, 스타일을 그대로 따르세요.
- 텍스트 내용만 사용자 입력에 맞게 교체하고, 디자인/레이아웃/색상은 템플릿 원본을 유지하세요.
- {page_rule_5}
- **[필수] 출력이 잘리거나 중단되지 않도록 전체를 완성한 후 </div>로 닫으세요.**
- 임의로 색상 테마, 폰트, 레이아웃 구조를 변경하지 마세요.

## 출력 규칙 (반드시 준수)
1. 오직 HTML만 출력하세요. 마크다운 코드블록(```), 설명 텍스트 등은 절대 포함하지 마세요.
2. <div id="proposal-content">로 시작하고 </div>로 끝나야 합니다.
3. 각 페이지는 반드시 class="proposal-page"를 가져야 합니다.
4. 모든 스타일은 인라인 스타일로 작성하세요 (<style> 태그 사용 금지).
5. 각 페이지의 기본 인라인 스타일: width:297mm;height:210mm;padding:15mm;box-sizing:border-box;position:relative;overflow:hidden;font-family:'Noto Sans KR',sans-serif;page-break-after:always;
6. {page_rule_6}
7. **푸터**: 각 페이지 우측 하단에 "DIGIWOOD<br>N / 총페이지수" 형태로 2줄 표시. position:absolute;bottom:12mm;right:15mm;text-align:right 스타일 사용. span 태그 사용하지 말 것.

## 이미지 사용 (중요)
- 사용자가 업로드한 이미지는 {{{{IMAGE:0}}}}, {{{{IMAGE:1}}}}, {{{{IMAGE:2}}}}... 형식으로 img 태그의 src에 사용하세요.
- 사용 가능한 이미지 수는 사용자 메시지에 명시됩니다.
- **이미지가 있으면 최대한 많은 페이지에 배치하세요.** 같은 이미지를 여러 페이지에 반복 사용해도 됩니다.
- 이미지가 없으면 이미지 영역을 텍스트나 디자인 요소로 대체하세요.
- **[필수] 이미지 비율 보존**: object-fit:contain을 사용하고, max-height를 사용하세요.
- **[필수] 이미지 크기 제한**: 모든 img 태그에 max-height:150mm를 반드시 적용하세요.

## 표(Table) 작성 규칙
- 자재 사양, 전시 개요 등 표 형태의 데이터는 반드시 HTML `<table>` 태그를 사용하세요.
- 제안사(Proposer) 기본값: DIGIWOOD

{page_structure}

{color_note}

## 수정 요청 시 행동 지침
- 사용자가 수정을 요청하면, 이전에 생성한 HTML을 기반으로 **요청된 부분만** 수정하세요.
- **사용자가 명시적으로 요청하지 않은 부분은 절대 변경하지 마세요.**
- 수정 후에도 완전한 HTML을 다시 출력하세요.

## 레퍼런스 템플릿 (필수 준수 양식)
{template}"""
