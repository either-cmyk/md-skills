"""
v3 보고서 생성: 기존 HTML 보고서의 상품별 실적 테이블을 빅셀 AG Grid 스크린샷으로 교체.
- 스크린샷을 base64로 인코딩하여 단일 HTML 파일에 임베딩
- 쿠팡/네이버 상품별 실적을 각각 접이식 서브 토글로 변경
- 이미지 width:100%로 보고서 폭에 맞게 확대

사용법 (스킬 내부에서):
  sed -e "s|SESSION_ID|현재세션ID|g" \
      -e "s|REPORT_DATE|YYYY-MM-DD|g" \
      스킬경로/scripts/build_v3_report.py > /tmp/build.py && python3 /tmp/build.py
"""

import base64
import os
import re

# ── sed로 치환할 변수 ──
BASE_DIR = '/sessions/SESSION_ID'
SCREENSHOT_DIR = os.path.join(BASE_DIR, 'screenshots')
INPUT_HTML = os.path.join(BASE_DIR, 'mnt/빅셀 데일리 분석리포트/빅셀_일일보고서_REPORT_DATE.html')
OUTPUT_HTML = os.path.join(BASE_DIR, 'mnt/빅셀 데일리 분석리포트/빅셀_일일보고서_v3_REPORT_DATE.html')

# 계정별 스크린샷 파일 매핑
ACCOUNTS = [
    {
        'name': '뉴트리정',
        'coupang_img': 'nutrijung_coupang_rfm.png',
        'naver_img': 'nutrijung_naver.png',
    },
    {
        'name': '이더컴퍼니',
        'coupang_img': 'eithercompany_coupang_rfm.png',
        'naver_img': 'eithercompany_naver.png',
    },
    {
        'name': '클린인테크',
        'coupang_img': 'cleanintech_coupang_rfm.png',
        'naver_img': None,
    },
    {
        'name': '마인플로',
        'coupang_img': 'mineflow_coupang_rfm.png',
        'naver_img': None,
    },
    {
        'name': '이든코퍼레이션',
        'coupang_img': 'edencorporation_coupang_rfm.png',
        'naver_img': None,
    },
]


def img_to_base64(filename):
    """이미지 파일을 base64 문자열로 변환"""
    path = os.path.join(SCREENSHOT_DIR, filename)
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def build_screenshot_section(account, section_idx):
    """계정별 상품별 실적 스크린샷 HTML 생성 (서브 토글 포함)"""
    name = account['name']
    html_parts = []

    # 쿠팡 스크린샷 (서브 토글)
    if account['coupang_img']:
        b64 = img_to_base64(account['coupang_img'])
        toggle_id = f'sub_cp_{section_idx}'
        html_parts.append(f'''
            <div class="sub-toggle-header cp-toggle" onclick="toggleSubSection('{toggle_id}')">
                <span class="sub-toggle-icon" id="{toggle_id}_icon">▶</span>
                <h3 class="sub-title" style="margin:0; display:inline;">쿠팡 상품별 실적 (RFM)</h3>
            </div>
            <div class="sub-toggle-body" id="{toggle_id}" style="display:none;">
                <div class="screenshot-wrap">
                    <img src="data:image/png;base64,{b64}" alt="{name} 쿠팡 RFM">
                </div>
            </div>''')

    # 네이버 스크린샷 (서브 토글)
    if account['naver_img']:
        b64 = img_to_base64(account['naver_img'])
        toggle_id = f'sub_nv_{section_idx}'
        html_parts.append(f'''
            <div class="sub-toggle-header nv-toggle" onclick="toggleSubSection('{toggle_id}')">
                <span class="sub-toggle-icon" id="{toggle_id}_icon">▶</span>
                <h3 class="sub-title nv-title" style="margin:0; display:inline;">네이버 상품별 실적</h3>
            </div>
            <div class="sub-toggle-body" id="{toggle_id}" style="display:none;">
                <div class="screenshot-wrap">
                    <img src="data:image/png;base64,{b64}" alt="{name} 네이버">
                </div>
            </div>''')

    return '\n'.join(html_parts)


def replace_product_sections(html_content):
    """기존 HTML에서 상품별 실적 테이블을 스크린샷으로 교체"""

    for account in ACCOUNTS:
        name = account['name']
        screenshot_html = build_screenshot_section(account)

        if account['naver_img']:
            # 듀얼 계정: 쿠팡 상품별 실적 ~ 네이버 상품별 실적 테이블 끝까지 교체
            # 패턴: <h3 class="sub-title">쿠팡 상품별 실적 (RFM)</h3> ... 다음 섹션 시작 전까지
            # 해당 계정의 account-body 안에서 교체
            pass
        else:
            # 단일 계정: 쿠팡 상품별 실적 테이블만 교체
            pass

    # 계정별로 정확한 위치를 찾기 위해 줄 단위로 처리
    lines = html_content.split('\n')
    result_lines = []
    i = 0
    account_idx = 0  # 현재 처리 중인 계정

    # 각 계정 섹션을 찾기 위한 상태 머신
    in_account_body = False
    skip_until_end = False
    current_account = None
    product_section_start = -1

    while i < len(lines):
        line = lines[i]

        # 상품별 실적 섹션 시작 감지
        if '쿠팡 상품별 실적 (RFM)' in line and account_idx < len(ACCOUNTS):
            current_account = ACCOUNTS[account_idx]
            product_section_start = i
            skip_until_end = True

            # 네이버가 있는 계정인지 확인
            has_naver = current_account['naver_img'] is not None

            # 건너뛸 종료 지점 찾기
            j = i + 1
            found_naver = False
            bracket_target = None

            while j < len(lines):
                if has_naver and '네이버 상품별 실적' in lines[j]:
                    found_naver = True

                # 종료 조건: 다음 sub-title(상품별 실적이 아닌) 또는 account-body 끝
                if '</div><!-- end-products -->' in lines[j]:
                    # 명시적 종료 마커 (없을 수 있음)
                    break

                # account-body 닫히는 div 또는 다음 섹션 시작
                # 주간 차트 섹션이나 다음 account-section이 시작되면 종료
                if has_naver and found_naver:
                    # 네이버 테이블 끝 찾기: </table> 후 </div> 패턴
                    if '</table>' in lines[j]:
                        # 테이블 끝 다음의 div 닫기까지
                        k = j + 1
                        while k < len(lines) and lines[k].strip() == '':
                            k += 1
                        if k < len(lines) and '</div>' in lines[k]:
                            j = k
                        else:
                            j = j
                        break
                elif not has_naver:
                    # 쿠팡만: 테이블 끝 찾기
                    if '</table>' in lines[j]:
                        k = j + 1
                        while k < len(lines) and lines[k].strip() in ('', '</div>'):
                            if '</div>' in lines[k].strip():
                                break
                            k += 1
                        j = j
                        break
                j += 1

            # 스크린샷 HTML 삽입
            result_lines.append(build_screenshot_section(current_account, account_idx))
            i = j + 1
            account_idx += 1
            continue

        result_lines.append(line)
        i += 1

    return '\n'.join(result_lines)


def main():
    print("📖 기존 보고서 읽기...")
    with open(INPUT_HTML, 'r', encoding='utf-8') as f:
        html = f.read()

    print("🔄 상품별 실적 섹션을 스크린샷으로 교체...")

    # 더 안정적인 방식: regex로 각 상품별 실적 블록을 찾아서 교체
    # 패턴: <h3 class="sub-title">쿠팡 상품별 실적 (RFM)</h3> ~ 다음 <h3 또는 </div>\s*</div> 전까지

    account_idx = 0

    def replace_coupang_block(match):
        nonlocal account_idx
        if account_idx >= len(ACCOUNTS):
            return match.group(0)

        acc = ACCOUNTS[account_idx]
        replacement = build_screenshot_section(acc)
        account_idx += 1
        return replacement

    # 각 계정의 상품별 실적 블록을 순서대로 찾아서 교체
    # 듀얼 계정: "쿠팡 상품별 실적" ~ "네이버 상품별 실적" + 테이블
    # 단일 계정: "쿠팡 상품별 실적" + 테이블

    # 전략: 수동으로 각 블록의 시작/끝 위치를 찾아서 교체
    positions = []

    # 모든 "쿠팡 상품별 실적 (RFM)" 위치 찾기
    pattern_coupang = re.compile(r'<h3 class="sub-title">쿠팡 상품별 실적 \(RFM\)</h3>')
    pattern_naver = re.compile(r'<h3 class="sub-title nv-title">네이버 상품별 실적</h3>')

    coupang_starts = [m.start() for m in pattern_coupang.finditer(html)]
    naver_starts = [m.start() for m in pattern_naver.finditer(html)]

    print(f"  쿠팡 상품별 실적 블록 {len(coupang_starts)}개 발견")
    print(f"  네이버 상품별 실적 블록 {len(naver_starts)}개 발견")

    # 각 쿠팡 블록의 끝 위치 찾기
    # 블록은 </table> 다음의 </div>까지
    def find_table_end(start_pos):
        """테이블 블록의 끝 위치 찾기 (table-wrap div 끝)"""
        # </table> 찾기
        table_end = html.find('</table>', start_pos)
        if table_end == -1:
            return start_pos + 100
        # </table> 다음 </div> (table-wrap 닫기)
        div_end = html.find('</div>', table_end)
        if div_end == -1:
            return table_end + 8
        return div_end + 6

    # 교체 영역 결정
    replacements = []  # (start, end, new_html)

    for idx, cp_start in enumerate(coupang_starts):
        acc = ACCOUNTS[idx]

        if acc['naver_img']:
            # 듀얼: 쿠팡 시작 ~ 네이버 테이블 끝
            # 이 쿠팡 블록 다음에 오는 네이버 블록 찾기
            nv_start = None
            for ns in naver_starts:
                if ns > cp_start:
                    nv_start = ns
                    break

            if nv_start:
                block_end = find_table_end(nv_start)
            else:
                block_end = find_table_end(cp_start)
        else:
            # 단일: 쿠팡 테이블 끝
            block_end = find_table_end(cp_start)

        replacement_html = build_screenshot_section(acc, idx)
        replacements.append((cp_start, block_end, replacement_html))

    # 역순으로 교체 (위치가 밀리지 않도록)
    new_html = html
    for start, end, repl in reversed(replacements):
        new_html = new_html[:start] + repl + new_html[end:]

    # 추가 CSS: 스크린샷 + 서브 토글 스타일
    extra_css = """
    .screenshot-wrap {
        overflow-x: auto;
        margin: 8px 0 16px;
    }
    .screenshot-wrap img {
        width: 100%;
        height: auto;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
    }
    .nv-toggle .screenshot-wrap img {
        border-color: #c8e6c9;
    }
    .sub-toggle-header {
        display: flex;
        align-items: center;
        gap: 8px;
        cursor: pointer;
        padding: 10px 14px;
        margin: 8px 0 0;
        border-radius: 8px;
        transition: background 0.15s;
        user-select: none;
    }
    .sub-toggle-header:hover {
        background: #f5f5f5;
    }
    .cp-toggle {
        background: #fff8e1;
        border-left: 3px solid #ff9800;
    }
    .cp-toggle:hover { background: #fff3cd; }
    .nv-toggle {
        background: #e8f5e9;
        border-left: 3px solid #4caf50;
    }
    .nv-toggle:hover { background: #dcedc8; }
    .sub-toggle-icon {
        font-size: 12px;
        transition: transform 0.2s;
        color: #666;
        min-width: 16px;
    }
    .sub-toggle-body {
        overflow: hidden;
        transition: max-height 0.3s ease;
    }
    """

    # 서브 토글 JS
    extra_js = """
    <script>
    function toggleSubSection(id) {
        const body = document.getElementById(id);
        const icon = document.getElementById(id + '_icon');
        if (body.style.display === 'none') {
            body.style.display = 'block';
            icon.textContent = '▼';
            icon.style.transform = 'rotate(0deg)';
        } else {
            body.style.display = 'none';
            icon.textContent = '▶';
        }
    }
    </script>
    """

    # CSS 삽입 (</style> 앞에)
    new_html = new_html.replace('</style>', extra_css + '\n</style>')

    # JS 삽입 (</body> 앞에)
    new_html = new_html.replace('</body>', extra_js + '\n</body>')

    # 타이틀에 v3 표시
    new_html = new_html.replace(
        '<title>빅셀 일일 매출 분석 보고서 - 2026-04-15</title>',
        '<title>빅셀 일일 매출 분석 보고서 (v3) - 2026-04-15</title>'
    )

    print(f"📝 v3 보고서 저장: {OUTPUT_HTML}")
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(new_html)

    file_size = os.path.getsize(OUTPUT_HTML)
    print(f"✅ 완료! 파일 크기: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")


if __name__ == '__main__':
    main()
