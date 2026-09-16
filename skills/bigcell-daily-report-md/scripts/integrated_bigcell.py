"""
빅셀 통합 데이터 수집 + 스크린샷 (단일 Playwright 패스)
- 5개 계정에 한 번만 로그인
- 대시보드 데이터 + RFM 상품 데이터 + AG Grid 스크린샷을 한 번에 수집
- 기존 3단계 (Chrome MCP 수집 → Playwright 스크린샷 → 보고서 생성)를 1단계로 통합
"""

import asyncio
import base64
import gzip
import json
import os
import io
import re
import time
from datetime import datetime, timedelta
from PIL import Image
import numpy as np
from playwright.async_api import async_playwright

# ── 설정 (sed 치환용 플레이스홀더) ──
TARGET_DATE = 'TARGET_DATE_PLACEHOLDER'       # sed로 YYYY-MM-DD 치환
PREV_DATE = 'PREV_DATE_PLACEHOLDER'           # sed로 YYYY-MM-DD 치환
BASE_DIR = '/sessions/SESSION_ID_PLACEHOLDER'  # sed로 현재 세션 ID 치환
OUTPUT_DIR_NAME = 'OUTPUT_DIR_PLACEHOLDER'     # sed로 출력 디렉토리명 치환

# 지난주 동일요일 (7일 전) 날짜 계산 — 특이사항 섹션 '지난주 대비' 비교용
LAST_WEEK_DATE = (datetime.strptime(TARGET_DATE, '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d')

TARGET_DATE_SLASH = TARGET_DATE.replace('-', '/')  # 빅셀 URL용
DATA_DIR = os.path.join(BASE_DIR, f'bigcell_{TARGET_DATE}')
SCREENSHOT_DIR = os.path.join(BASE_DIR, 'screenshots')
OUTPUT_DIR = os.path.join(BASE_DIR, f'mnt/{OUTPUT_DIR_NAME}')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

PASSWORD = 'dlejrhddyd1!'

ACCOUNTS = [
    {'id': 'nutrijung',       'name': '뉴트리정',       'naver': True,  'dual': True,  'data_prefix': 'account1'},
    {'id': 'eithercompany',   'name': '이더컴퍼니',     'naver': True,  'dual': True,  'data_prefix': 'account4'},
    {'id': 'cleanintech',     'name': '클린인테크',     'naver': False, 'dual': False, 'data_prefix': 'account2'},
    {'id': 'mineflow',        'name': '마인플로',       'naver': False, 'dual': False, 'data_prefix': 'account3'},
    {'id': 'edencorporation', 'name': '이든코퍼레이션', 'naver': False, 'dual': False, 'data_prefix': 'account5'},
]

_only = os.environ.get('ONLY_ACCOUNT')
_do = os.environ.get('DO', 'all')
if _only:
    ACCOUNTS = [a for a in ACCOUNTS if a['id'] == _only]

# ── JS 코드 ──
# v5.2.1: Auth 객체를 export name 하드코드(mod.K) 대신 동적으로 찾는다.
# 빅셀이 entry.js 빌드를 새로 하면 minified export name 이 K → 다른 글자로 바뀌어서
# `Auth.signIn is not a function` 에러가 난다. 모든 export 를 순회하며 signIn +
# currentAuthenticatedUser 메서드 둘 다 가진 객체를 자동 탐색.
LOGIN_JS = """
(async () => {{
    const scripts = document.querySelectorAll('script[src*="/_nuxt/entry"]');
    let entryPath = null;
    for (const s of scripts) {{ if (s.src.includes('entry')) {{ entryPath = new URL(s.src).pathname; break; }} }}
    if (!entryPath) entryPath = '/_nuxt/entry.6e177eba.js';
    const mod = await import(entryPath);

    // v5.2.1 동적 Auth 탐색 — 1단계: top-level export 중 signIn+currentAuthenticatedUser 둘 다 있는 객체
    let Auth = null;
    const isAuthLike = (v) => v && typeof v.signIn === 'function' && typeof v.currentAuthenticatedUser === 'function';
    for (const k of Object.keys(mod)) {{
        if (isAuthLike(mod[k])) {{ Auth = mod[k]; break; }}
    }}
    // 2단계: 한 단계 깊이 (객체 안의 객체)
    if (!Auth) {{
        for (const k of Object.keys(mod)) {{
            const v = mod[k];
            if (v && typeof v === 'object') {{
                for (const k2 of Object.keys(v)) {{
                    if (isAuthLike(v[k2])) {{ Auth = v[k2]; break; }}
                }}
                if (Auth) break;
            }}
        }}
    }}
    // 3단계: 최후 fallback — 옛 패턴 mod.K
    if (!Auth && isAuthLike(mod.K)) Auth = mod.K;
    if (!Auth) {{
        const keys = Object.keys(mod).join(',');
        throw new Error('Auth 객체 탐색 실패. mod keys: ' + keys);
    }}

    try {{ await Auth.signOut(); }} catch(e) {{}}
    await Auth.signIn({{ username: '{account_id}', password: '{password}' }});
    const user = await Auth.currentAuthenticatedUser();
    await Auth.updateUserAttributes(user, {{ 'custom:password': '{password}' }});
    return 'login_ok';
}})();
"""

CLEANUP_JS = """
(() => {
    let s = document.getElementById('bc-custom-css');
    if (!s) { s = document.createElement('style'); s.id = 'bc-custom-css'; document.head.appendChild(s); }
    s.textContent = `
        [col-id="adverts-anlytics"], [col-id="product_stage_name"], [col-id="order_request"] { display: none !important; }
        .layout-sidebar { display: none !important; }
        .layout-main-container { margin-left: 0 !important; }
        .p-toast, .p-tooltip, .p-overlaypanel, .p-dialog-mask, .p-dialog,
        .p-confirmpopup, .p-component-overlay { display: none !important; }
    `;
    document.querySelectorAll(
        '.p-dialog-mask, .p-dialog, .p-toast, .p-tooltip, .p-overlaypanel, .p-confirmpopup, .popup, .popup-container'
    ).forEach(el => el.remove());
    document.body.style.overflow = '';
    document.body.classList.remove('p-overflow-hidden');
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

DASHBOARD_EXTRACT_JS = """
(() => {
    // 대시보드 innerText에서 날짜별 데이터 추출
    // 패턴: 2026-04-15 → (수) → ₩매출 → %증감 → ₩이익금 → %증감 → ₩광고비 → %증감 → ₩순이익금 → %증감
    const text = document.body.innerText;
    const lines = text.split('\\n').map(l => l.trim());
    const result = {};

    for (let i = 0; i < lines.length; i++) {
        // YYYY-MM-DD 형식의 날짜 찾기
        if (/^\\d{4}-\\d{2}-\\d{2}$/.test(lines[i])) {
            const dateKey = lines[i];
            // 날짜 이후 줄에서 ₩ 값 4개 수집 (% 줄은 건너뜀)
            const wonValues = [];
            for (let j = i + 1; j < Math.min(i + 20, lines.length); j++) {
                // 다음 날짜가 나오면 중단
                if (/^\\d{4}-\\d{2}-\\d{2}$/.test(lines[j])) break;
                const m = lines[j].match(/^(₩[\\d,]+)$/);
                if (m) wonValues.push(m[1]);
                if (wonValues.length >= 4) break;
            }
            if (wonValues.length >= 4) {
                result[dateKey] = {
                    sales: wonValues[0],
                    profit: wonValues[1],
                    adCost: wonValues[2],
                    netProfit: wonValues[3]
                };
            }
        }
    }
    return result;
})();
"""

# RFM 상품 데이터 추출 (AG Grid 내부 API 사용)
RFM_EXTRACT_JS = """
(() => {
    // AG Grid API로 전체 rowData 접근 시도
    const gridEl = document.querySelector('.ag-root-wrapper');
    if (!gridEl) return null;

    // 방법1: __agComponent를 통한 API 접근
    const agApi = gridEl.__agComponent;
    if (agApi && agApi.gridOptions && agApi.gridOptions.api) {
        const api = agApi.gridOptions.api;
        const rows = [];
        api.forEachNode(node => {
            if (node.data) rows.push(node.data);
        });
        if (rows.length > 0) return JSON.stringify(rows);
    }

    // 방법2: DOM에서 직접 추출 (fallback)
    const products = [];
    document.querySelectorAll('.ag-body-viewport .ag-row').forEach(r => {
        const info = r.querySelector('[col-id="product_info"]') || r.querySelector('[col-id="product_name"]');
        const name = info ? info.innerText.split('\\n')[0].trim() : '';
        const idMatch = info ? info.innerText.match(/(\\d{7,})/) : null;
        const pid = idMatch ? idMatch[1] : '';
        if (!name || !pid) return;
        const gv = (c) => {
            const el = r.querySelector(`[col-id="${c}"]`);
            if(!el) return '';
            const m = el.innerText.match(/-?₩[\\d,]+|^[\\d,]+/);
            return m ? m[0] : '';
        };
        products.push({
            name, productId: pid,
            qty: gv('sale_qty'), sales: gv('sale_amount'),
            adCost: gv('advert_ad_cost_sum'), netProfit: gv('sale_net_amount')
        });
    });
    return JSON.stringify(products);
})();
"""

GET_GRID_HEIGHT_JS = """
(() => {
    const vp = document.querySelector('.ag-body-viewport');
    const hvp = document.querySelector('.ag-header-viewport') || document.querySelector('.ag-center-cols-container');
    const header = document.querySelector('.ag-header');
    const ft = document.querySelector('.ag-floating-top');
    const root = document.querySelector('.ag-root-wrapper');
    const paginator = document.querySelector('.p-paginator');
    if (!vp || !root) return null;
    // v5.0.7: scrollWidth 포함 (우측 잘림 방지용 뷰포트 width 계산 기준)
    const scrollWidth = Math.max(
        vp.scrollWidth || 0,
        hvp ? hvp.scrollWidth : 0,
        root.scrollWidth || 0
    );
    return {
        scrollHeight: vp.scrollHeight,
        scrollWidth: scrollWidth,
        clientHeight: vp.clientHeight,
        headerHeight: header ? header.offsetHeight : 0,
        floatingTopHeight: ft ? ft.offsetHeight : 0,
        totalNeeded: Math.ceil(root.getBoundingClientRect().top) + (header ? header.offsetHeight : 0) + (ft ? ft.offsetHeight : 0) + vp.scrollHeight + (paginator ? paginator.offsetHeight : 0) + 50
    };
})();
"""


def crop_screenshot(img_bytes):
    img = Image.open(io.BytesIO(img_bytes))
    arr = np.array(img)
    h, w, _ = arr.shape

    right_crop = w
    for x in range(w - 1, int(w * 0.5), -1):
        col = arr[:, x, :]
        if np.std(col) > 15:
            right_crop = min(x + 4, w)
            break

    bottom_crop = h
    min_y = int(h * 0.05)
    for y in range(h - 1, min_y, -2):
        row = arr[y, :right_crop, :]
        dark_mask = np.all(row < 80, axis=1)
        dark_pct = np.sum(dark_mask) / right_crop * 100
        if dark_pct > 0.3:
            bottom_crop = min(y + 30, h)
            break

    if right_crop < w * 0.7: right_crop = w
    if bottom_crop < h * 0.15: bottom_crop = h

    cropped = img.crop((0, 0, right_crop, bottom_crop))
    buf = io.BytesIO()
    cropped.save(buf, format='PNG')
    return buf.getvalue(), (w, h), (right_crop, bottom_crop)


async def dismiss_overlays(page):
    for _ in range(3):
        await page.keyboard.press('Escape')
        await page.wait_for_timeout(200)
    await page.evaluate("""
    (() => {
        document.querySelectorAll('.p-dialog-mask, .p-dialog, .p-component-overlay, .popup, .popup-container').forEach(el => el.remove());
        document.body.style.overflow = '';
        document.body.classList.remove('p-overflow-hidden');
    })();
    """)
    await page.wait_for_timeout(300)



async def extract_rfm_and_screenshot(page, account, target_date_slash, is_naver=False):
    """RFM 페이지에서 상품 데이터 + 스크린샷 동시 추출"""

    # v5.0.9: 쿠팡은 12개 컬럼(광고ROAS 포함)이라 기본 viewport(1800)로는 AG Grid가 우측 컬럼을 아예 DOM에 렌더링 안 함.
    # → 쿠팡 탐색 전에 viewport를 2600으로 넓혀서 모든 컬럼이 처음부터 렌더링되도록.
    # 네이버는 1800 명시적으로 유지 (이전 쿠팡 호출이 남긴 2600 viewport 상속 방지 → column stretch 차단).
    if is_naver:
        await page.set_viewport_size({'width': 1800, 'height': 900})
    else:
        await page.set_viewport_size({'width': 2600, 'height': 900})

    if is_naver:
        url = f'https://app.bigcell.co.kr/v2/statistics/naver?q_sale_date_from={target_date_slash}&q_sale_date_to={target_date_slash}&q_show_type=summary'
    else:
        url = f'https://app.bigcell.co.kr/v2/statistics/coupang?q_sale_date_from={target_date_slash}&q_sale_date_to={target_date_slash}&q_product_types=RFM&q_show_type=summary'

    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
    await page.wait_for_timeout(5000)
    # MD버전: 그리드 행 렌더링까지 폴링 대기 (최대 40초, 로딩 느린 계정 대응)
    for _wait_i in range(20):
        _n = await page.evaluate("document.querySelectorAll('.ag-center-cols-container .ag-row').length")
        if _n and _n > 0:
            break
        await page.wait_for_timeout(2000)
    await dismiss_overlays(page)
    await page.evaluate(CLEANUP_JS)
    await page.wait_for_timeout(300)

    # 순이익금 내림차순 정렬
    await page.evaluate("""
    (async () => {
        const header = document.querySelector('[col-id="sale_net_amount"] .ag-header-cell-label');
        if (!header) return;
        header.click(); await new Promise(r => setTimeout(r, 500));
        header.click(); await new Promise(r => setTimeout(r, 500));
    })();
    """)
    await page.wait_for_timeout(500)

    # 페이지 사이즈 100으로
    ps_result = await page.evaluate(CHANGE_PAGE_SIZE_JS)
    if 'changed' in str(ps_result):
        await page.wait_for_timeout(3000)
        await dismiss_overlays(page)
        await page.evaluate(CLEANUP_JS)
        # 정렬 재적용
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

    # ── 1) 상품 데이터 추출 (스크롤 + 누적) ──
    await page.evaluate("window._allProducts = {};")

    # 먼저 현재 보이는 행 수집
    total_count = await page.evaluate("""
    (() => {
        const text = document.body.innerText;
        const m = text.match(/총 (\\d+)개/);
        return m ? parseInt(m[1]) : 0;
    })();
    """)

    # 스크롤하면서 데이터 누적
    for scroll_pass in range(12):  # 최대 12번 스크롤 (큰 상품 목록 커버)
        col_id = 'product_info' if not is_naver else 'product_info'
        # 요약보기에서는 naver도 product_info 사용

        count = await page.evaluate("""
        (() => {
            window._allProducts = window._allProducts || {};
            document.querySelectorAll('.ag-center-cols-container .ag-row').forEach(r => {
                const ri = r.getAttribute('row-index');
                const pr = document.querySelector(`.ag-pinned-left-cols-container .ag-row[row-index="${ri}"]`) || r;
                let pid = '', name = '';
                const idEl = pr.querySelector('[col-id="product_id"]');
                const nameEl = pr.querySelector('[col-id="product_name"]');
                const infoEl = pr.querySelector('[col-id="product_info"]') || r.querySelector('[col-id="product_info"]');
                if (idEl || nameEl) {
                    const m = idEl ? idEl.innerText.match(/(\\d{7,})/) : null;
                    pid = m ? m[1] : '';
                    name = nameEl ? nameEl.innerText.split('\\n')[0].trim() : '';
                } else if (infoEl) {
                    name = infoEl.innerText.split('\\n')[0].trim();
                    const m = infoEl.innerText.match(/(\\d{7,})/);
                    pid = m ? m[1] : '';
                }
                if (!pid || !name) return;
                const gv = (c) => { const el = r.querySelector(`[col-id="${c}"]`); if(!el) return ''; const m = el.innerText.match(/-?\u20a9[\\d,]+|^[\\d,]+/); return m?m[0]:''; };
                const sqEl = r.querySelector('[col-id="sale_qty"]');
                const sqTxt = sqEl ? sqEl.innerText : '';
                const qtyM = sqTxt.match(/^[\\d,]+/);
                const salesM = sqTxt.match(/\u20a9[\\d,]+/);
                const salesVal = gv('sale_amount') || (salesM ? salesM[0] : '');
                // MD버전 확장 필드: 노출순위, 쿠팡재고(수량/금액), 최근7일 일일평균판매량, 광고 ROAS
                const _cell = (c) => { const el = r.querySelector(`[col-id="${c}"]`); return el ? el.innerText.replace(/\\n+/g, ' ').trim() : ''; };
                const _stockTxt = _cell('stock_qty');
                const _stockQtyM = _stockTxt.match(/^[\\d,]+/);
                const _stockValM = _stockTxt.match(/\u20a9[\d,]+/);
                const _avgM = _cell('avg_sale_qty').match(/^[\\d,.]+/);
                const _roasM = _cell('advert_sale_amount_rate').match(/-?[\\d,]+%/);
                window._allProducts[pid] = {name, productId:pid, qty:(qtyM?qtyM[0]:gv('sale_qty')), sales:salesVal, adCost:gv('advert_ad_cost_sum'), netProfit:gv('sale_net_amount'),
                    rank:_cell('keyword_rank'), stockQty:(_stockQtyM?_stockQtyM[0]:''), stockValue:(_stockValM?_stockValM[0]:''), avgQty:(_avgM?_avgM[0]:''), roas:(_roasM?_roasM[0]:'')};
            });
            return Object.keys(window._allProducts).length;
        })();
        """)

        if count >= total_count and total_count > 0:
            break

        # 더 스크롤
        await page.evaluate("document.querySelector('.ag-body-viewport')?.scrollBy(0, 600);")
        await page.wait_for_timeout(500)

    # 최종 데이터 수집
    products_json = await page.evaluate("JSON.stringify(Object.values(window._allProducts));")
    products = json.loads(products_json) if products_json else []

    # ── 2) 스크린샷 캡처 ──
    grid_info = await page.evaluate(GET_GRID_HEIGHT_JS)
    screenshot_bytes = None

    if grid_info:
        current_size = page.viewport_size
        new_height = max(grid_info['scrollHeight'] * 3, 3000)
        # v5.0.8: scrollWidth 기준으로만 확장 (최소 제한 제거).
        # 쿠팡처럼 실제로 scrollWidth가 크면 자연스럽게 확장되고,
        # 네이버처럼 좁은 그리드면 원래 viewport 크기 유지 → 컬럼 stretch로 인한 화질 저하 방지.
        needed_width = grid_info.get('scrollWidth', 0) + 100
        new_width = max(needed_width, current_size['width'])
        await page.set_viewport_size({'width': new_width, 'height': new_height})
        await page.wait_for_timeout(2000)
        await page.evaluate(CLEANUP_JS)
        await page.wait_for_timeout(500)

        # 오버레이 제거
        await page.evaluate("""
        (() => {
            Array.from(document.body.children).forEach(el => {
                if (el.classList.contains('ag-root-wrapper') || el.tagName === 'SCRIPT' || el.tagName === 'STYLE' || el.tagName === 'LINK') return;
                const s = getComputedStyle(el);
                const z = parseInt(s.zIndex) || 0;
                if ((s.position === 'fixed' || s.position === 'absolute') && z > 100) {
                    el.style.setProperty('display', 'none', 'important');
                }
            });
            document.querySelectorAll('.popup, .popup-container, [class*="mask"], [class*="overlay"], [class*="dialog"]').forEach(el => {
                if (!el.closest('.ag-root-wrapper')) {
                    el.style.setProperty('display', 'none', 'important');
                }
            });
            document.body.classList.remove('p-overflow-hidden');
            document.body.style.overflow = '';
        })();
        """)
        await page.wait_for_timeout(300)

        grid = await page.query_selector('.ag-root-wrapper')
        if grid:
            raw_screenshot = await grid.screenshot()
            screenshot_bytes, orig, cropped = crop_screenshot(raw_screenshot)

        await page.set_viewport_size(current_size)

    return products, screenshot_bytes


async def main():
    start_time = time.time()
    print(f"🚀 빅셀 통합 수집 시작 ({TARGET_DATE})")
    print(f"   목표: 데이터 수집 + 스크린샷을 단일 Playwright 패스로 처리\n")

    async with async_playwright() as p:
        # MD버전: 클라우드(Cowork 원격) 샌드박스 자동 감지 — 프록시가 TLS1.3을 리셋하므로 TLS1.2 강제 + 전체 Chromium 사용
        import glob as _glob
        _launch_kw = {}
        _launch_args = ['--no-sandbox', '--disable-setuid-sandbox']
        if os.environ.get('CCR_AGENT_PROXY_ENABLED') == '1':
            _proxy = os.environ.get('https_proxy') or os.environ.get('HTTPS_PROXY') or ''
            _chr = sorted(_glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome'))
            if _chr:
                _launch_kw['executable_path'] = _chr[-1]
            if _proxy:
                _launch_args += [f'--proxy-server={_proxy}']
            _launch_args += ['--ignore-certificate-errors', '--ssl-version-max=tls1.2', '--disable-dev-shm-usage']
        browser = await p.chromium.launch(
            headless=True,
            args=_launch_args,
            **_launch_kw
        )
        context = await browser.new_context(
            viewport={'width': 1800, 'height': 900},
            device_scale_factor=2
        )
        page = await context.new_page()

        # 팝업 차단 init script
        await page.add_init_script("""
        (() => {
            const style = document.createElement('style');
            style.textContent = `
                .popup, .popup-container,
                .p-dialog-mask, .p-component-overlay {
                    display: none !important; visibility: hidden !important;
                    opacity: 0 !important; pointer-events: none !important; z-index: -1 !important;
                }
            `;
            if (document.head) document.head.appendChild(style);
            else document.addEventListener('DOMContentLoaded', () => document.head.appendChild(style));

            const observer = new MutationObserver(() => {
                document.querySelectorAll('.p-dialog-mask, .p-component-overlay').forEach(el => {
                    el.style.setProperty('display', 'none', 'important');
                });
                document.body.classList.remove('p-overflow-hidden');
                document.body.style.overflow = '';
            });
            if (document.body) observer.observe(document.body, { childList: true, subtree: true });
            else document.addEventListener('DOMContentLoaded', () => observer.observe(document.body, { childList: true, subtree: true }));
        })();
        """)

        all_data = {}

        for acc in ACCOUNTS:
            acc_start = time.time()
            account_id = acc['id']
            account_name = acc['name']
            print(f"{'='*50}")
            print(f"📋 {account_name} ({account_id})")
            print(f"{'='*50}")

            # ── 1) 로그인 (한 번만!) ──
            print(f"  🔑 로그인...")
            await page.goto('https://app.bigcell.co.kr/login', wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(2000)
            await page.evaluate(LOGIN_JS.format(account_id=account_id, password=PASSWORD))

            if _do in ('dash','all'):
                # ── 2) 대시보드에서 매출/이익금/광고비/순이익금 추출 ──
                print(f"  📊 대시보드 수집...")
                await page.goto('https://app.bigcell.co.kr/v2/dashboard', wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(9000)
                await dismiss_overlays(page)

                # 대시보드 innerText에서 날짜별 ₩ 값 추출
                dashboard_data = await page.evaluate(DASHBOARD_EXTRACT_JS)

                today_data = dashboard_data.get(TARGET_DATE) if dashboard_data else None
                yest_data = dashboard_data.get(PREV_DATE) if dashboard_data else None

                # 대시보드에 보이는 모든 날짜를 저장 (지난주 동일요일, 주간 추이용)
                if dashboard_data:
                    merged = dict(dashboard_data)  # LAST_WEEK fallback 결과 머지용
                else:
                    print(f"  ⚠️ 대시보드 추출 실패. keys: None")
                    merged = {}

                # ── 2-1) LAST_WEEK_DATE(지난주 동일요일) 보강 ──
                # 대시보드 디폴트 뷰에 7일 전 데이터가 포함되지 않으면,
                # 쿠팡 통계 페이지에 해당 일자만 필터해 요약행에서 역산 추출
                if LAST_WEEK_DATE not in merged:
                    lw_slash = LAST_WEEK_DATE.replace('-', '/')
                    lw_url = (f'https://app.bigcell.co.kr/v2/statistics/coupang'
                              f'?q_sale_date_from={lw_slash}&q_sale_date_to={lw_slash}'
                              f'&q_product_types=RFM&q_show_type=summary')
                    try:
                        print(f"  🔁 {LAST_WEEK_DATE} 보강 수집 → 쿠팡 통계 요약행")
                        await page.goto(lw_url, wait_until='domcontentloaded', timeout=30000)
                        await page.wait_for_timeout(4000)
                        await dismiss_overlays(page)
                        await page.evaluate(CLEANUP_JS)
                        await page.wait_for_timeout(400)
                        lw_summary = await page.evaluate("""
                        (() => {
                            const topRow = document.querySelector('.ag-floating-top-container .ag-row');
                            if (!topRow) return null;
                            const gv = (c) => {
                                const el = topRow.querySelector(`[col-id="${c}"]`);
                                if(!el) return '';
                                const m = el.innerText.match(/-?₩[\\d,]+/);
                                return m ? m[0] : '';
                            };
                            return { sales: gv('sale_amount'), profit: gv('sale_profit_amount'),
                                     adCost: gv('advert_ad_cost_sum'), netProfit: gv('sale_net_amount') };
                        })();
                        """)
                        if lw_summary and lw_summary.get('sales'):
                            merged[LAST_WEEK_DATE] = {
                                'sales': lw_summary['sales'] or '₩0',
                                'profit': lw_summary.get('profit') or lw_summary['netProfit'] or '₩0',
                                'adCost': lw_summary.get('adCost') or '₩0',
                                'netProfit': lw_summary['netProfit'] or '₩0',
                            }
                            print(f"  ✅ 보강 성공: {LAST_WEEK_DATE} 매출={merged[LAST_WEEK_DATE]['sales']}")
                        else:
                            print(f"  ⚠️ 보강 실패: {LAST_WEEK_DATE} 요약행 미발견")
                    except Exception as e:
                        print(f"  ⚠️ {LAST_WEEK_DATE} 보강 중 예외: {e}")

                if merged:
                    all_rows = [{'date': dk, **merged[dk]} for dk in sorted(merged.keys(), reverse=True)]
                    dashboard_json = {'daily': all_rows}
                    dates_found = ', '.join(sorted(merged.keys(), reverse=True)[:10])
                    print(f"  📊 최종 날짜 {len(all_rows)}개 저장: {dates_found}")
                    if today_data:
                        print(f"  📊 {TARGET_DATE} 매출={today_data['sales']}, 순이익={today_data['netProfit']}")
                    if yest_data:
                        print(f"  📊 {PREV_DATE} 매출={yest_data['sales']}, 순이익={yest_data['netProfit']}")
                    lw = merged.get(LAST_WEEK_DATE)
                    if lw:
                        print(f"  📊 {LAST_WEEK_DATE}(지난주 동일요일) 매출={lw['sales']}, 순이익={lw['netProfit']}")
                    else:
                        print(f"  ⚠️ {LAST_WEEK_DATE}(지난주 동일요일) 여전히 없음 — 특이사항 섹션에서 N/A 처리")
                else:
                    dashboard_json = {'daily': []}

                cp_file = f'data_{acc["data_prefix"]}_coupang.json'
                with open(os.path.join(DATA_DIR, cp_file), 'w', encoding='utf-8') as f:
                    json.dump(dashboard_json, f, ensure_ascii=False, indent=2)
                print(f"  ✅ {cp_file} 저장")

            # ── 3) 듀얼 계정: 네이버 대시보드는 네이버 RFM 추출 시 같이 처리 ──

            if _do in ('rfm','all'):
                # ── 4) 쿠팡 RFM 데이터 + 스크린샷 ──
                print(f"  📊 쿠팡 RFM 수집 + 스크린샷...")
                products, screenshot = await extract_rfm_and_screenshot(page, acc, TARGET_DATE_SLASH, is_naver=False)

                rfm_file = f'{account_id}_keyword_data.json'
                with open(os.path.join(DATA_DIR, rfm_file), 'w', encoding='utf-8') as f:
                    json.dump(products, f, ensure_ascii=False, indent=2)
                print(f"  ✅ {rfm_file} 저장 ({len(products)}개 상품)")

                if screenshot:
                    ss_file = f'{account_id}_coupang_rfm.png'
                    with open(os.path.join(SCREENSHOT_DIR, ss_file), 'wb') as f:
                        f.write(screenshot)
                    print(f"  ✅ {ss_file} 저장 ({len(screenshot):,} bytes)")

            # ── 5) 네이버 상품 데이터 + 스크린샷 + 네이버 대시보드 ──
            if acc['naver'] and _do in ('naver','all'):
                print(f"  📊 네이버 상품 수집 + 스크린샷...")
                # ✨ 빅셀 네이버 UI 가 sale_amount 컬럼을 숨겨버리므로
                #    내부 Lambda(ta7e75y...) raw 응답을 가로채 sale_amount 를 직접 합산한다.
                _lambda_bodies = []
                async def _lambda_sniffer(resp):
                    try:
                        if 'lambda-url' in resp.url and 'q_sale_date' in resp.url:
                            b = await resp.body()
                            _lambda_bodies.append(b)
                    except Exception:
                        pass
                page.on('response', _lambda_sniffer)

                nv_products, nv_screenshot = await extract_rfm_and_screenshot(page, acc, TARGET_DATE_SLASH, is_naver=True)

                # 리스너 제거 (다음 계정 오염 방지)
                try:
                    page.remove_listener('response', _lambda_sniffer)
                except Exception:
                    pass

                # Lambda 응답 → 총 sale_amount 계산
                nv_sales_lambda = None
                for raw in _lambda_bodies:
                    try:
                        outer = json.loads(raw.decode('utf-8'))
                        body_b64 = outer.get('body')
                        if not body_b64:
                            continue
                        inner = json.loads(gzip.decompress(base64.b64decode(body_b64)).decode('utf-8'))
                        rows = inner.get('statistics') or []
                        total = sum((r.get('sale_amount') or 0) for r in rows if isinstance(r, dict))
                        if total:
                            nv_sales_lambda = total
                            print(f"  💰 Lambda 네이버 매출 합: ₩{total:,} (rows={len(rows)})")
                            break
                    except Exception as e:
                        print(f"  ⚠️ Lambda decode 실패: {e}")

                nv_prod_file = f'{account_id}_naver_data.json'
                with open(os.path.join(DATA_DIR, nv_prod_file), 'w', encoding='utf-8') as f:
                    json.dump(nv_products, f, ensure_ascii=False, indent=2)
                print(f"  ✅ {nv_prod_file} 저장 ({len(nv_products)}개 상품)")

                if nv_screenshot:
                    nv_ss_file = f'{account_id}_naver.png'
                    with open(os.path.join(SCREENSHOT_DIR, nv_ss_file), 'wb') as f:
                        f.write(nv_screenshot)
                    print(f"  ✅ {nv_ss_file} 저장 ({len(nv_screenshot):,} bytes)")

                # 네이버 대시보드 데이터: 네이버 RFM 페이지 상단 요약행에서 추출
                nv_summary = await page.evaluate("""
                (() => {
                    // AG Grid floating-top (요약행)에서 매출/순이익 추출
                    const topRow = document.querySelector('.ag-floating-top-container .ag-row');
                    if (!topRow) return null;
                    const gv = (c) => {
                        const el = topRow.querySelector(`[col-id="${c}"]`);
                        if(!el) return '';
                        const m = el.innerText.match(/-?₩[\\d,]+/);
                        return m ? m[0] : '';
                    };
                    return { sales: gv('sale_amount'), netProfit: gv('sale_net_amount'), adCost: gv('advert_ad_cost_sum') };
                })();
                """)

                # Lambda raw 매출이 있으면 그것이 진실. UI fallback 보다 우선.
                if nv_summary is None:
                    nv_summary = {}
                if nv_sales_lambda is not None:
                    nv_summary['sales'] = f"₩{nv_sales_lambda:,}"

                if nv_summary.get('sales'):
                    nv_dashboard_json = {'daily': [
                        {'date': TARGET_DATE,
                         'sales': nv_summary['sales'],
                         'profit': nv_summary.get('netProfit', '₩0'),
                         'adCost': nv_summary.get('adCost', '₩0'),
                         'netProfit': nv_summary.get('netProfit', '₩0')}
                    ]}
                    print(f"  📊 네이버 요약: 매출={nv_summary['sales']}, 순이익={nv_summary.get('netProfit','N/A')}")
                else:
                    # fallback: 상품 합산
                    nv_dashboard_json = {'daily': []}
                    print(f"  ⚠️ 네이버 요약행 + Lambda 모두 추출 실패")

                nv_file = f'data_{acc["data_prefix"]}_naver.json'
                with open(os.path.join(DATA_DIR, nv_file), 'w', encoding='utf-8') as f:
                    json.dump(nv_dashboard_json, f, ensure_ascii=False, indent=2)
                print(f"  ✅ {nv_file} 저장")

            acc_time = time.time() - acc_start
            print(f"  ⏱️ {account_name} 완료: {acc_time:.1f}초")

        await browser.close()

    total_time = time.time() - start_time
    print(f"\n{'='*50}")
    print(f"✅ 전체 데이터 수집 완료: {total_time:.1f}초 ({total_time/60:.1f}분)")
    print(f"📁 데이터: {DATA_DIR}")
    print(f"📸 스크린샷: {SCREENSHOT_DIR}")

    # ── 파일 목록 출력 ──
    print(f"\n📋 수집된 파일:")
    for f in sorted(os.listdir(DATA_DIR)):
        size = os.path.getsize(os.path.join(DATA_DIR, f))
        print(f"  {f} ({size:,} bytes)")
    for f in sorted(os.listdir(SCREENSHOT_DIR)):
        size = os.path.getsize(os.path.join(SCREENSHOT_DIR, f))
        print(f"  {f} ({size:,} bytes)")


if __name__ == '__main__':
    asyncio.run(main())
