"""
빅셀 AG Grid 스크린샷 캡처 (최종)
Playwright headless Chromium으로 5개 계정의 쿠팡 RFM + 네이버 AG Grid를 캡처.

사용법 (스킬 내부에서):
  sed -e "s|SESSION_ID|현재세션ID|g" \
      -e "s|TARGET_DATE = '2026/04/15'|TARGET_DATE = 'YYYY/MM/DD'|" \
      스킬경로/scripts/capture_screenshots.py > /tmp/cap.py && python3 /tmp/cap.py

특징:
  - 순이익금(sale_net_amount) 내림차순 정렬
  - 100개 페이지네이션 (전체 상품 한 번에)
  - device_scale_factor=2 고화질
  - 광고분석/운영상태/1688구매요청 열 CSS 숨김
  - PIL 크롭: 하단 빈 행 + 우측 빈 공간 자동 제거
  - PrimeVue 팝업 + 빅셀 공지(.popup-container) 완전 차단
"""

import asyncio
import os
import io
from PIL import Image
import numpy as np
from playwright.async_api import async_playwright

# ── sed로 치환할 변수 (스킬에서 실행 시 세션ID와 날짜를 치환) ──
BASE_DIR = '/sessions/SESSION_ID'
OUTPUT_DIR = os.path.join(BASE_DIR, 'screenshots')
os.makedirs(OUTPUT_DIR, exist_ok=True)

PASSWORD = 'dlejrhddyd1!'
TARGET_DATE = '2026/04/15'

ACCOUNTS = [
    {'id': 'nutrijung', 'name': '뉴트리정', 'naver': True},
    {'id': 'eithercompany', 'name': '이더컴퍼니', 'naver': True},
    {'id': 'cleanintech', 'name': '클린인테크', 'naver': False},
    {'id': 'mineflow', 'name': '마인플로', 'naver': False},
    {'id': 'edencorporation', 'name': '이든코퍼레이션', 'naver': False},
]

LOGIN_JS = """
(async () => {{
    const mod = await import('/_nuxt/entry.6e177eba.js');
    const Auth = mod.K;
    try {{ await Auth.signOut(); }} catch(e) {{}}
    await Auth.signIn({{ username: '{account_id}', password: '{password}' }});
    const user = await Auth.currentAuthenticatedUser();
    await Auth.updateUserAttributes(user, {{ 'custom:password': '{password}' }});
    return 'login_ok';
}})();
"""

CLEANUP_JS = """
(() => {
    // 열 숨기기 + 사이드바 + 팝업 CSS
    let s = document.getElementById('bc-custom-css');
    if (!s) { s = document.createElement('style'); s.id = 'bc-custom-css'; document.head.appendChild(s); }
    s.textContent = `
        [col-id="adverts-anlytics"], [col-id="product_stage_name"], [col-id="order_request"] { display: none !important; }
        .layout-sidebar { display: none !important; }
        .layout-main-container { margin-left: 0 !important; }
        .p-toast, .p-tooltip, .p-overlaypanel, .p-dialog-mask, .p-dialog,
        .p-confirmpopup, .p-component-overlay { display: none !important; }
    `;
    // DOM에서 팝업 제거
    document.querySelectorAll(
        '.p-dialog-mask, .p-dialog, .p-toast, .p-tooltip, .p-overlaypanel, .p-confirmpopup'
    ).forEach(el => el.remove());
})();
"""

CHANGE_PAGE_SIZE_JS = """
(async () => {
    const rpp = document.querySelector('.p-paginator-rpp-options');
    if (!rpp) return 'no_paginator';
    rpp.click();
    await new Promise(r => setTimeout(r, 600));
    const items = document.querySelectorAll('.p-dropdown-item, .p-dropdown-items li');
    for (const item of items) {
        if (item.textContent.trim() === '100') { item.click(); return 'changed_to_100'; }
    }
    return 'option_not_found';
})();
"""

GET_GRID_HEIGHT_JS = """
(() => {
    const vp = document.querySelector('.ag-body-viewport');
    const header = document.querySelector('.ag-header');
    const ft = document.querySelector('.ag-floating-top');
    const root = document.querySelector('.ag-root-wrapper');
    const paginator = document.querySelector('.p-paginator');
    if (!vp || !root) return null;
    return {
        scrollHeight: vp.scrollHeight,
        clientHeight: vp.clientHeight,
        headerHeight: header ? header.offsetHeight : 0,
        floatingTopHeight: ft ? ft.offsetHeight : 0,
        rootTop: root.getBoundingClientRect().top,
        rootHeight: root.offsetHeight,
        paginatorHeight: paginator ? paginator.offsetHeight : 0,
        // 전체 필요 높이: rootTop + header + floatingTop + scrollHeight + paginator + 여유
        totalNeeded: Math.ceil(root.getBoundingClientRect().top) + (header ? header.offsetHeight : 0) + (ft ? ft.offsetHeight : 0) + vp.scrollHeight + (paginator ? paginator.offsetHeight : 0) + 50
    };
})();
"""


async def dismiss_all_dialogs(page):
    """모든 PrimeVue 다이얼로그를 닫기 (공지 팝업 등)"""
    # ESC 여러 번
    for _ in range(3):
        await page.keyboard.press('Escape')
        await page.wait_for_timeout(200)

    # 닫기/확인 버튼 클릭 + DOM 제거
    await page.evaluate("""
    (async () => {
        // 1) 모든 닫기/확인/Close 버튼 클릭
        const closeSelectors = [
            '.p-dialog-header-close',
            '.p-dialog-header-icon',
            '[aria-label="Close"]',
            '.p-dialog-footer button',
        ];
        for (const sel of closeSelectors) {
            document.querySelectorAll(sel).forEach(btn => {
                try { btn.click(); } catch(e) {}
            });
        }
        await new Promise(r => setTimeout(r, 300));

        // 2) DOM에서 다이얼로그/마스크 완전 제거
        document.querySelectorAll(
            '.p-dialog-mask, .p-dialog, .p-component-overlay, .p-toast, .p-tooltip'
        ).forEach(el => el.remove());

        // 3) body 스크롤 복원
        document.body.style.overflow = '';
        document.body.classList.remove('p-overflow-hidden');

        // 4) Vue teleport 컨테이너 내 다이얼로그도 제거
        document.querySelectorAll('[class*="dialog"], [class*="modal"]').forEach(el => {
            if (el.querySelector('.p-dialog-content') || el.classList.contains('p-dialog-mask')) {
                el.remove();
            }
        });
    })();
    """)
    await page.wait_for_timeout(300)


def crop_screenshot(img_bytes):
    """스크린샷에서 하단 여백 + 우측 빈 공간 제거
    - 하단: 텍스트(어두운 픽셀)가 없는 빈 AG Grid 행 제거
    - 우측: 마지막 데이터 열 이후 빈 공간 제거
    """
    img = Image.open(io.BytesIO(img_bytes))
    arr = np.array(img)
    h, w, _ = arr.shape

    # === 우측 빈 공간 제거 ===
    right_crop = w
    for x in range(w - 1, int(w * 0.5), -1):
        col = arr[:, x, :]
        if np.std(col) > 15:
            right_crop = min(x + 4, w)
            break

    # === 하단 여백 제거 ===
    # 핵심: 텍스트가 있는 행 = RGB < 80인 "어두운 픽셀"이 0.5% 이상 존재
    # 빈 AG Grid 행 = 줄무늬 배경만 (unique_colors ≤ 3, dark_pct ≈ 0)
    # 아래에서 위로 스캔하여 마지막 텍스트가 있는 행 찾기
    bottom_crop = h
    # 헤더 영역(상단 5%) 이후부터 스캔 가능
    min_y = int(h * 0.05)

    for y in range(h - 1, min_y, -2):  # 2px 간격 스캔 (속도 최적화)
        row = arr[y, :right_crop, :]
        dark_mask = np.all(row < 80, axis=1)
        dark_pct = np.sum(dark_mask) / right_crop * 100
        if dark_pct > 0.3:  # 텍스트가 있는 행
            # 마지막 콘텐츠 행 아래로 약간 여유 (행 하단 border 등)
            bottom_crop = min(y + 30, h)
            break

    # 안전 장치: 너무 많이 자르면 원본 유지
    if right_crop < w * 0.7:
        right_crop = w
    if bottom_crop < h * 0.15:
        bottom_crop = h

    cropped = img.crop((0, 0, right_crop, bottom_crop))

    buf = io.BytesIO()
    cropped.save(buf, format='PNG')
    return buf.getvalue(), (w, h), (right_crop, bottom_crop)


async def capture_view(page, context, output_path, account_name, view_type):
    """AG Grid 뷰를 캡처"""

    # 빅셀 공지 팝업 닫기 (popup-container 클래스)
    try:
        # "다시 보지 않기" 버튼 클릭 (영구 닫기)
        dismiss_btn = page.locator('button:has-text("다시 보지 않기")')
        await dismiss_btn.wait_for(state='visible', timeout=3000)
        await dismiss_btn.click()
        print(f"  🔒 공지 팝업 '다시 보지 않기' 클릭")
        await page.wait_for_timeout(500)
    except Exception:
        pass

    # 혹시 남은 popup 컨테이너 숨기기
    await page.evaluate("""
    (() => {
        document.querySelectorAll('.popup, .popup-container, .p-dialog-mask, .p-component-overlay').forEach(el => {
            el.style.setProperty('display', 'none', 'important');
        });
        document.body.style.overflow = '';
    })();
    """)
    await page.wait_for_timeout(300)
    await page.evaluate(CLEANUP_JS)
    await page.wait_for_timeout(300)

    # 순이익금 내림차순 정렬
    sort_result = await page.evaluate("""
    (async () => {
        const header = document.querySelector('[col-id="sale_net_amount"] .ag-header-cell-label');
        if (!header) return 'no_header';
        // 두 번 클릭 → descending
        header.click();
        await new Promise(r => setTimeout(r, 500));
        header.click();
        await new Promise(r => setTimeout(r, 500));
        const cell = document.querySelector('[col-id="sale_net_amount"]');
        return 'sort: ' + (cell ? cell.getAttribute('aria-sort') : 'unknown');
    })();
    """)
    print(f"  📊 순이익금 정렬: {sort_result}")
    await page.wait_for_timeout(500)

    # 페이지 사이즈 100으로 변경
    ps_result = await page.evaluate(CHANGE_PAGE_SIZE_JS)
    print(f"  📄 페이지사이즈: {ps_result}")
    if 'changed' in str(ps_result):
        await page.wait_for_timeout(3000)
        await dismiss_all_dialogs(page)
        await page.evaluate(CLEANUP_JS)
        # 페이지사이즈 변경 후 순이익금 정렬 재적용
        await page.evaluate("""
        (async () => {
            const header = document.querySelector('[col-id="sale_net_amount"] .ag-header-cell-label');
            if (!header) return;
            const cell = document.querySelector('[col-id="sale_net_amount"]');
            const current = cell ? cell.getAttribute('aria-sort') : '';
            if (current !== 'descending') {
                header.click(); await new Promise(r => setTimeout(r, 400));
                header.click(); await new Promise(r => setTimeout(r, 400));
            }
        })();
        """)
        await page.wait_for_timeout(1000)

    # 그리드 높이 확인
    grid_info = await page.evaluate(GET_GRID_HEIGHT_JS)
    if not grid_info:
        print(f"  ⚠️ AG Grid 없음")
        return False

    total_needed = grid_info['totalNeeded']
    print(f"  📊 Grid: scrollH={grid_info['scrollHeight']}, 필요높이={total_needed}")

    # 뷰포트를 충분히 크게 리사이즈 (scrollHeight*3)
    # AG Grid는 뷰포트가 충분히 크면 clientHeight >= scrollHeight가 되어 모든 행 렌더링
    current_size = page.viewport_size
    new_height = max(grid_info['scrollHeight'] * 3, 3000)
    await page.set_viewport_size({'width': current_size['width'], 'height': new_height})
    await page.wait_for_timeout(2000)  # 가상 스크롤 렌더링 대기

    # 리사이즈 후 팝업 다시 제거
    await page.evaluate(CLEANUP_JS)
    await page.wait_for_timeout(500)

    # 스크린샷 직전: 모든 오버레이 요소 제거 (position:fixed/absolute 고z-index)
    overlay_info = await page.evaluate("""
    (() => {
        const removed = [];
        // body 직계 자식 중 fixed/absolute + 높은 z-index 요소 제거
        Array.from(document.body.children).forEach(el => {
            if (el.classList.contains('ag-root-wrapper') || el.tagName === 'SCRIPT' || el.tagName === 'STYLE' || el.tagName === 'LINK') return;
            const s = getComputedStyle(el);
            const z = parseInt(s.zIndex) || 0;
            if ((s.position === 'fixed' || s.position === 'absolute') && z > 100) {
                removed.push({ tag: el.tagName, class: el.className?.toString().substring(0,60), z: z });
                el.style.setProperty('display', 'none', 'important');
            }
        });
        // 모든 overlay/mask/dialog 클래스 요소
        document.querySelectorAll('.popup, .popup-container, [class*="mask"], [class*="overlay"], [class*="dialog"], [class*="modal"], [class*="Dialog"], [class*="Modal"]').forEach(el => {
            if (!el.closest('.ag-root-wrapper')) {
                removed.push({ tag: el.tagName, class: el.className?.toString().substring(0,60) });
                el.style.setProperty('display', 'none', 'important');
                el.style.setProperty('visibility', 'hidden', 'important');
            }
        });
        document.body.classList.remove('p-overflow-hidden');
        document.body.style.overflow = '';
        return removed;
    })();
    """)
    if overlay_info:
        print(f"  🗑️ 오버레이 {len(overlay_info)}개 숨김: {overlay_info[:3]}")
    await page.wait_for_timeout(300)

    # AG Grid 요소만 캡처
    grid = await page.query_selector('.ag-root-wrapper')
    if not grid:
        print(f"  ⚠️ AG Grid 없음")
        await page.set_viewport_size(current_size)
        return False

    screenshot = await grid.screenshot()

    # PIL로 하단 여백 + 우측 빈 공간 크롭
    cropped_bytes, orig_size, crop_size = crop_screenshot(screenshot)
    with open(output_path, 'wb') as f:
        f.write(cropped_bytes)

    # 뷰포트 원래 크기로 복원
    await page.set_viewport_size(current_size)

    size = os.path.getsize(output_path)
    print(f"  ✅ 저장: {output_path} ({size:,} bytes)")
    print(f"     크롭: {orig_size[0]}x{orig_size[1]} → {crop_size[0]}x{crop_size[1]}")
    return True


async def main():
    print("🚀 빅셀 스크린샷 캡처 v4 시작")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await browser.new_context(
            viewport={'width': 1800, 'height': 900},
            device_scale_factor=2
        )
        page = await context.new_page()

        # 모든 페이지 로드 시 자동으로 다이얼로그를 숨기는 스크립트 주입
        await page.add_init_script("""
        (() => {
            // 다이얼로그 차단 CSS 즉시 주입
            const style = document.createElement('style');
            style.textContent = `
                .popup, .popup-container,
                .p-dialog-mask, .p-component-overlay,
                .p-dialog-mask.p-component-overlay {
                    display: none !important;
                    visibility: hidden !important;
                    opacity: 0 !important;
                    pointer-events: none !important;
                    z-index: -1 !important;
                }
            `;
            if (document.head) {
                document.head.appendChild(style);
            } else {
                document.addEventListener('DOMContentLoaded', () => document.head.appendChild(style));
            }

            // MutationObserver: DOM에 추가되는 다이얼로그 마스크 즉시 숨김
            const observer = new MutationObserver(() => {
                document.querySelectorAll('.p-dialog-mask, .p-component-overlay').forEach(el => {
                    el.style.setProperty('display', 'none', 'important');
                });
                document.body.classList.remove('p-overflow-hidden');
                document.body.style.overflow = '';
            });

            if (document.body) {
                observer.observe(document.body, { childList: true, subtree: true });
            } else {
                document.addEventListener('DOMContentLoaded', () => {
                    observer.observe(document.body, { childList: true, subtree: true });
                });
            }
        })();
        """)

        for acc in ACCOUNTS:
            account_id = acc['id']
            account_name = acc['name']
            print(f"\n{'='*60}")
            print(f"📋 {account_name} ({account_id})")
            print(f"{'='*60}")

            # 로그인
            print(f"  🔑 로그인...")
            await page.goto('https://app.bigcell.co.kr/login', wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(2000)
            await page.evaluate(LOGIN_JS.format(account_id=account_id, password=PASSWORD))
            # 공지 팝업 무시 플래그 설정 시도
            await page.evaluate("""
            (() => {
                // 빅셀 공지 팝업 관련 localStorage 키를 설정하여 팝업 억제
                try {
                    // 일반적인 공지 플래그 패턴들
                    localStorage.setItem('notice_read', 'true');
                    localStorage.setItem('popup_dismissed', 'true');
                    localStorage.setItem('announcement_closed', 'true');
                    // 날짜 기반 팝업 방지
                    const today = new Date().toISOString().split('T')[0];
                    localStorage.setItem('notice_closed_date', today);
                    localStorage.setItem('popup_closed_date', today);
                } catch(e) {}
            })();
            """)

            # 쿠팡 RFM
            rfm_url = f'https://app.bigcell.co.kr/v2/statistics/coupang?q_sale_date_from={TARGET_DATE}&q_sale_date_to={TARGET_DATE}&q_product_types=RFM&q_show_type=detail'
            print(f"  📊 쿠팡 RFM...")
            await page.goto(rfm_url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(5000)
            await capture_view(page, context, os.path.join(OUTPUT_DIR, f'{account_id}_coupang_rfm.png'), account_name, '쿠팡')

            # 네이버
            if acc['naver']:
                naver_url = f'https://app.bigcell.co.kr/v2/statistics/naver?q_sale_date_from={TARGET_DATE}&q_sale_date_to={TARGET_DATE}'
                print(f"  📊 네이버...")
                await page.goto(naver_url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(5000)
                await capture_view(page, context, os.path.join(OUTPUT_DIR, f'{account_id}_naver.png'), account_name, '네이버')

        await browser.close()

    print(f"\n{'='*60}")
    print("📁 결과:")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        if f.endswith('.png') and not f.startswith('v3'):
            size = os.path.getsize(os.path.join(OUTPUT_DIR, f))
            print(f"  {f} ({size:,} bytes)")
    print("✅ 완료!")


if __name__ == '__main__':
    asyncio.run(main())
