"""
빅셀 특이사항 섹션 HTML 조립 + v3 보고서 삽입.

v5.1.0 (2026-04-23) 포맷 간소화:
  - 한눈 요약의 '전일 → 금일' 블록 제거 → 지난주 동일요일 대비만 메인으로
  - 계정별 변동 표에서 '전일 대비' 2개 컬럼 제거 → 지난주 동일요일 대비만
  - 상품 단위 이슈는 product_bullets가 실제로 있을 때만 ② 섹션 렌더링
    (데이터 수집 실패 안내 문구 같은 fallback bullet 금지 — 빈 리스트면 섹션 자체 숨김)

입력:
  --context       build_special_context.py가 만든 JSON (숫자/상품 데이터)
  --interpretation Claude가 작성한 해석 문장들 JSON (구조는 아래 스키마 참조)
  --report        삽입 대상 v3 HTML 보고서 경로 (in-place 수정)

interpretation JSON 스키마 (v5.1.0):
{
  "weekly_bullets": [                  // 지난주 동일요일 대비 해석 (2~4개 리스트)
    "수치 + 한 줄 결론",
    ...
  ],
  "account_reasons": {                 // 계정별 '주요 사유' (지난주 대비 중심)
    "전체 합산": "...",
    "뉴트리정": "...",
    ...
  },
  "product_bullets": [                 // 상품 단위 이슈 (있을 때만, 아주 간략하게)
    "<b>상품명 — 이슈</b>: 수치",
    ...
  ]
}

레거시 호환: summary_bullets/summary_interpretation 등 전일 관련 필드가 들어와도 무시함.
"""
import json
import argparse
import os
import re


def won(n):
    """정수를 ₩12,345 형식으로."""
    if n < 0:
        return f"-₩{abs(n):,}"
    return f"₩{n:,}"


def change_cell(delta, pct=None, bg=''):
    """변동 셀 HTML. +/-에 따라 색상 + 컬럼 그룹 배경색."""
    color = '#27ae60' if delta > 0 else ('#e74c3c' if delta < 0 else '#7f8c8d')
    sign = '+' if delta > 0 else ('' if delta == 0 else '')
    pct_str = f" ({pct:+.1f}%)" if pct is not None else ''
    bg_style = f'background:{bg};' if bg else ''
    return f'<td style="padding:8px;text-align:center;color:{color};border:1px solid #e0e0e0;{bg_style}"><b>{sign}{won(delta)}</b>{pct_str}</td>'


def value_cell(value, bold=False, bg=''):
    """일반 숫자 셀 (가운데 정렬)."""
    bg_style = f'background:{bg};' if bg else ''
    inner = f'<b>{won(value)}</b>' if bold else won(value)
    return f'<td style="padding:8px;text-align:center;border:1px solid #e0e0e0;{bg_style}">{inner}</td>'


def to_bullets(value):
    """해석 값을 번호 리스트 아이템으로. list면 그대로, string이면 소수점 보호 split."""
    if value is None:
        return []
    if isinstance(value, list):
        return [s for s in (str(x).strip() for x in value) if s]
    text = str(value).strip().replace('。', '.')
    if not text:
        return []
    # 소수점(앞뒤가 숫자인 .)은 보호
    parts = re.split(r'(?<!\d)\.(?!\d)', text)
    return [p.strip() for p in parts if p and p.strip()]


def format_weekday(date_str):
    """2026-04-19 → '04/19 일'"""
    from datetime import datetime
    days = ['월', '화', '수', '목', '금', '토', '일']
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    return f"{dt.month:02d}/{dt.day:02d} {days[dt.weekday()]}"


def build_html(context, interp):
    """특이사항 섹션 HTML 블록 생성 (v5.1.0: 지난주 동일요일 대비 only)."""
    td = context['target_date']
    lw = context.get('last_week_date')
    total = context['total']

    week_change = total.get('change_week')
    has_week = week_change is not None

    # 지난주 대비 해석 bullets
    weekly_bullets = to_bullets(interp.get('weekly_bullets') or interp.get('weekly_interpretation'))

    # 지난주 요약 블록
    week_summary_html = ''
    if has_week:
        wk_s_delta = week_change['sales']
        wk_np_delta = week_change['netProfit']
        wk_s_color = '#27ae60' if wk_s_delta > 0 else '#e74c3c'
        wk_np_color = '#27ae60' if wk_np_delta > 0 else '#e74c3c'
        wk_s_pct = week_change.get('sales_pct')
        wk_np_pct = week_change.get('netProfit_pct')
        wk_s_pct_str = f", {wk_s_pct:+.1f}%" if wk_s_pct is not None else ''
        wk_np_pct_str = f", {wk_np_pct:+.1f}%" if wk_np_pct is not None else ''
        weekly_items_html = f'''
                <li>매출: {won(total['last_week']['sales'])} → <b>{won(total['target']['sales'])}</b> <span style="color:{wk_s_color}">({'+' if wk_s_delta>=0 else ''}{won(wk_s_delta)}{wk_s_pct_str})</span></li>
                <li>순이익: {won(total['last_week']['netProfit'])} → <b>{won(total['target']['netProfit'])}</b> <span style="color:{wk_np_color}">({'+' if wk_np_delta>=0 else ''}{won(wk_np_delta)}{wk_np_pct_str})</span></li>'''
        for b in weekly_bullets:
            weekly_items_html += f'\n                <li>{b}</li>'

        week_summary_html = f'''
            <div style="background:#fff;border-left:4px solid #8e44ad;padding:14px 18px;margin-bottom:18px;border-radius:6px">
                <strong style="font-size:1.05em;color:#8e44ad">📅 지난주 동일요일 대비 ({format_weekday(lw)} → {format_weekday(td)})</strong>
                <ol style="margin:10px 0 0 0;padding-left:24px;color:#444;line-height:1.8">{weekly_items_html}
                </ol>
            </div>'''
    elif lw:
        week_summary_html = f'''
            <div style="background:#f9f9f9;padding:10px 14px;margin-bottom:18px;border-radius:6px">
                <span style="color:#999;font-size:0.9em">📅 지난주 동일요일({lw}) 데이터 미수집 — 다음 실행 시 자동 수집</span>
            </div>'''

    html = f'''<!-- 특이사항 (자동 분석) -->
    <div class="account-section" style="margin-top:30px;border:2px solid #8e44ad;background:#faf5fe">
        <div class="account-header" onclick="toggleSection('section_special')" style="background:linear-gradient(135deg,#8e44ad 0%,#6c3483 100%);color:white">
            <div class="account-title-row">
                <span class="account-name" style="color:white">📌 특이사항 — 지난주 동일요일 대비 분석</span>
                <span class="account-toggle" style="color:white">▼</span>
            </div>
        </div>
        <div class="account-body" id="section_special" style="padding:24px;line-height:1.7">
            {week_summary_html}

            <h3 style="color:#8e44ad;border-bottom:2px solid #8e44ad;padding-bottom:6px;margin-top:18px">① 계정별 변동 (지난주 동일요일 대비)</h3>
            <table style="width:100%;border-collapse:collapse;margin-bottom:8px;font-size:0.93em">
                <thead>
                    <tr style="background:#f8f9fa">
                        <th style="padding:8px;text-align:center;border:1px solid #e0e0e0">계정</th>
                        <th style="padding:8px;text-align:center;border:1px solid #e0e0e0">금일 순이익</th>
                        <th style="padding:8px;text-align:center;border:1px solid #e0e0e0;background:#f3e5f5;color:#5e2a76">지난주 순이익</th>
                        <th style="padding:8px;text-align:center;border:1px solid #e0e0e0;background:#f3e5f5;color:#5e2a76">변동</th>
                        <th style="padding:8px;text-align:center;border:1px solid #e0e0e0">주요 사유</th>
                    </tr>
                </thead>
                <tbody>
'''

    reasons = interp.get('account_reasons', {})

    BG_WEEK = '#f3e5f5'   # 지난주 대비 열

    # 전체 합산 행
    total_reason = reasons.get('전체 합산', '')
    if has_week:
        cw = total['change_week']
        total_lw_cells = value_cell(total['last_week']['netProfit'], bg=BG_WEEK) + '\n                    ' + change_cell(cw['netProfit'], cw['netProfit_pct'], bg=BG_WEEK)
    else:
        total_lw_cells = f'<td colspan="2" style="padding:8px;text-align:center;border:1px solid #e0e0e0;color:#999;background:{BG_WEEK}">N/A</td>'

    html += f'''                <tr style="background:#f8f0ff">
                    <td style="padding:8px;text-align:center;border:1px solid #e0e0e0"><b>전체 합산</b></td>
                    {value_cell(total['target']['netProfit'], bold=True)}
                    {total_lw_cells}
                    <td style="padding:8px;text-align:left;border:1px solid #e0e0e0">{total_reason}</td>
                </tr>
'''

    # 계정별 행
    for a in context['accounts']:
        name = a['name']
        label = name + ("(전체)" if a['dual'] else "")
        reason = reasons.get(name, '')
        if a.get('change_week'):
            cw = a['change_week']
            lw_cells = value_cell(a['last_week']['netProfit'], bg=BG_WEEK) + '\n                    ' + change_cell(cw['netProfit'], cw['netProfit_pct'], bg=BG_WEEK)
        else:
            lw_cells = f'<td colspan="2" style="padding:8px;text-align:center;border:1px solid #e0e0e0;color:#999;background:{BG_WEEK}">N/A</td>'
        html += f'''                <tr>
                    <td style="padding:8px;text-align:center;border:1px solid #e0e0e0"><b>{label}</b></td>
                    {value_cell(a['target']['netProfit'], bold=True)}
                    {lw_cells}
                    <td style="padding:8px;text-align:left;border:1px solid #e0e0e0">{reason}</td>
                </tr>
'''

    html += '''                </tbody>
            </table>
'''

    # ② 상품 단위 이슈 — product_bullets가 실제로 있을 때만 렌더링
    product_bullets = interp.get('product_bullets') or []
    # 빈 문자열/공백만 있는 항목 필터링
    product_bullets = [b for b in product_bullets if str(b).strip()]

    if product_bullets:
        html += '''
            <h3 style="color:#8e44ad;border-bottom:2px solid #8e44ad;padding-bottom:6px;margin-top:18px">② 주목할 상품 단위 이슈</h3>
            <ul>
'''
        for bullet in product_bullets:
            html += f'                <li>{bullet}</li>\n'
        html += '            </ul>\n'

    html += '''
        </div>
    </div>'''

    return html


def inject(report_path, html_block):
    """보고서의 </body> 직전에 HTML 블록 삽입."""
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 기존 특이사항 섹션이 있으면 제거하고 새로 삽입
    old_start = content.find('<!-- 특이사항 (자동 분석) -->')
    if old_start != -1:
        body_end = content.find('</body>', old_start)
        content = content[:old_start].rstrip() + '\n' + content[body_end:]

    body_close = content.rfind('</body>')
    if body_close == -1:
        raise RuntimeError("</body> 태그를 찾을 수 없음")

    new_content = content[:body_close] + '\n    ' + html_block + '\n\n' + content[body_close:]

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return len(html_block)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--context', required=True, help='special_context JSON 경로')
    parser.add_argument('--interpretation', required=True, help='Claude 해석 JSON 경로')
    parser.add_argument('--report', required=True, help='v3 HTML 보고서 경로 (in-place 수정)')
    args = parser.parse_args()

    with open(args.context, encoding='utf-8') as f:
        context = json.load(f)
    with open(args.interpretation, encoding='utf-8') as f:
        interp = json.load(f)

    html = build_html(context, interp)
    size = inject(args.report, html)

    print(f"✅ 특이사항 섹션 삽입 완료")
    print(f"   HTML 블록 크기: {size:,} bytes")
    print(f"   보고서: {args.report}")


if __name__ == '__main__':
    main()
