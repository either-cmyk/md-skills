#!/usr/bin/env python3
"""
MD버전 전용: '오늘 확인할 것' 체크리스트 섹션 생성 + 보고서 상단 주입
- 순위 이슈 (3페이지내 없음 / 노출순위 미등록)
- 판매량 급변 (7일 평균 대비 급증/급감)
- 과재고·판매부진 (재고소진일수 기반)
- 광고 저효율 (저ROAS + 광고비 집행 중)
- 적자 상품 (고매출 적자 우선)

사용법:
  python3 build_md_section.py --data-dir <bigcell_YYYY-MM-DD 경로> --report <v5 html 경로> [--json-out <경로>]

integrated_bigcell.py(MD버전)가 저장한 *_keyword_data.json 의 확장 필드
(rank, stockQty, stockValue, avgQty, roas)를 사용한다.
"""
import argparse, json, os, re, html

ACCOUNTS = [
    ('nutrijung', '뉴트리정'),
    ('eithercompany', '이더컴퍼니'),
    ('cleanintech', '클린인테크'),
    ('mineflow', '마인플로'),
    ('edencorporation', '이든코퍼레이션'),
]

# ── 판정 기준 (MD 조정 가능) ──
SWING_UP_RATIO = 1.5      # 어제 판매량 >= 7일평균 * 1.5 → 급증
SWING_DOWN_RATIO = 0.5    # 어제 판매량 <= 7일평균 * 0.5 → 급감
SWING_MIN_AVG = 3         # 7일평균이 이 값 미만이면 급변 판정 제외 (노이즈)
OVERSTOCK_DAYS = 60       # 재고소진일수 >= 60일 → 과재고 후보
OVERSTOCK_MIN_QTY = 50    # 재고수량 최소 기준
LOW_ROAS_PCT = 200        # ROAS < 200% + 광고비 집행 중 → 저효율
LOW_ROAS_MIN_ADCOST = 10000
LOSS_MIN = -10000         # 순이익 <= -1만원 → 적자 리스트


def parse_num(s):
    if not s:
        return 0
    m = re.search(r'-?[\d,]+', str(s).replace('₩', ''))
    return int(m.group(0).replace(',', '')) if m else 0


def parse_float(s):
    if not s:
        return 0.0
    try:
        return float(str(s).replace(',', ''))
    except ValueError:
        return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data-dir', required=True)
    ap.add_argument('--report', required=True)
    ap.add_argument('--json-out', default=None)
    args = ap.parse_args()

    rank_issues, swings_up, swings_down, overstock, dead_stock, low_roas, losses = [], [], [], [], [], [], []

    for acc_id, acc_name in ACCOUNTS:
        path = os.path.join(args.data_dir, f'{acc_id}_keyword_data.json')
        if not os.path.exists(path):
            continue
        products = json.load(open(path, encoding='utf-8'))
        for pr in products:
            name = pr.get('name', '')
            pid = pr.get('productId', '')
            qty = parse_num(pr.get('qty'))
            net = parse_num(pr.get('netProfit'))
            ad = parse_num(pr.get('adCost'))
            sales = parse_num(pr.get('sales'))
            rank = (pr.get('rank') or '').strip()
            stock = parse_num(pr.get('stockQty'))
            stock_val = pr.get('stockValue') or ''
            avg = parse_float(pr.get('avgQty'))
            roas = parse_num(pr.get('roas'))
            item = {'account': acc_name, 'name': name, 'productId': pid}

            # 1) 순위 이슈 — 실제 판매 중인 상품만 (어제 판매 or 7일평균 1개 이상; 휴면 상품 제외)
            if (qty > 0 or avg >= 1):
                if '3페이지내 없음' in rank:
                    rank_issues.append({**item, 'issue': '3페이지내 없음', 'qty': qty, 'avg': avg})
                elif rank == '' or '등록' in rank:
                    rank_issues.append({**item, 'issue': '노출순위 미등록', 'qty': qty, 'avg': avg})

            # 2) 판매량 급변
            if avg >= SWING_MIN_AVG:
                if qty >= avg * SWING_UP_RATIO and qty - avg >= 3:
                    swings_up.append({**item, 'qty': qty, 'avg': avg, 'pct': round((qty / avg - 1) * 100)})
                elif qty <= avg * SWING_DOWN_RATIO:
                    swings_down.append({**item, 'qty': qty, 'avg': avg, 'pct': round((qty / avg - 1) * 100)})

            # 3) 과재고 / 판매부진
            if stock >= OVERSTOCK_MIN_QTY:
                if avg > 0:
                    days = stock / avg
                    if days >= OVERSTOCK_DAYS:
                        overstock.append({**item, 'stock': stock, 'stockValue': stock_val, 'avg': avg, 'days': int(days)})
                else:
                    dead_stock.append({**item, 'stock': stock, 'stockValue': stock_val})

            # 4) 광고 저효율
            if ad >= LOW_ROAS_MIN_ADCOST and 0 < roas < LOW_ROAS_PCT:
                low_roas.append({**item, 'adCost': ad, 'roas': roas, 'net': net})

            # 5) 적자
            if net <= LOSS_MIN:
                losses.append({**item, 'net': net, 'sales': sales, 'adCost': ad})

    swings_down.sort(key=lambda x: x['pct'])
    swings_up.sort(key=lambda x: -x['pct'])
    overstock.sort(key=lambda x: -x['days'])
    dead_stock.sort(key=lambda x: -x['stock'])
    low_roas.sort(key=lambda x: -x['adCost'])
    losses.sort(key=lambda x: x['net'])

    data = {'rank_issues': rank_issues, 'swings_up': swings_up, 'swings_down': swings_down,
            'overstock': overstock, 'dead_stock': dead_stock, 'low_roas': low_roas, 'losses': losses}
    if args.json_out:
        os.makedirs(os.path.dirname(args.json_out), exist_ok=True)
        json.dump(data, open(args.json_out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    # ── HTML 생성 ──
    def esc(s):
        return html.escape(str(s))

    def won(n):
        return f'-₩{abs(n):,}' if n < 0 else f'₩{n:,}'

    def plink(pid, name):
        return f'<a href="https://www.coupang.com/vp/products/{esc(pid)}" target="_blank" style="color:#1a1a2e;text-decoration:none">{esc(name[:42])}</a>'

    def block(title, color, rows_html, count, empty_msg=None):
        if count == 0:
            if not empty_msg:
                return ''
            body = f'<div style="font-size:13px;color:#888;padding:4px 2px">{empty_msg}</div>'
        else:
            body = rows_html
        return f'''
        <div style="margin-bottom:14px">
          <div style="font-size:14px;font-weight:700;color:{color};margin-bottom:6px">{title} <span style="font-weight:400;color:#999">({count}건)</span></div>
          {body}
        </div>'''

    def table(headers, rows):
        th = ''.join(f'<th style="text-align:left;padding:5px 8px;font-size:12px;color:#666;border-bottom:1px solid #eee;white-space:nowrap">{h}</th>' for h in headers)
        trs = ''
        for cells in rows:
            tds = ''.join(f'<td style="padding:5px 8px;font-size:13px;border-bottom:1px solid #f5f5f5;white-space:nowrap">{c}</td>' for c in cells)
            trs += f'<tr>{tds}</tr>'
        return f'<table style="border-collapse:collapse;width:100%"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>'

    MAX_ROWS = 15

    rank_rows = table(['계정', '상품', '이슈', '어제판매', '7일평균'],
                      [[esc(x['account']), plink(x['productId'], x['name']), f'<span style="color:#e74c3c;font-weight:600">{esc(x["issue"])}</span>', x['qty'], f'{x["avg"]:g}'] for x in rank_issues[:MAX_ROWS]])
    down_rows = table(['계정', '상품', '어제판매', '7일평균', '변동'],
                      [[esc(x['account']), plink(x['productId'], x['name']), x['qty'], f'{x["avg"]:g}', f'<span style="color:#e74c3c">▼ {x["pct"]}%</span>'] for x in swings_down[:MAX_ROWS]])
    up_rows = table(['계정', '상품', '어제판매', '7일평균', '변동'],
                    [[esc(x['account']), plink(x['productId'], x['name']), x['qty'], f'{x["avg"]:g}', f'<span style="color:#27ae60">▲ +{x["pct"]}%</span>'] for x in swings_up[:MAX_ROWS]])
    over_rows = table(['계정', '상품', '재고', '재고금액', '7일평균', '소진일수'],
                      [[esc(x['account']), plink(x['productId'], x['name']), f'{x["stock"]:,}', esc(x['stockValue']), f'{x["avg"]:g}', f'<b>{x["days"]}일</b>'] for x in overstock[:MAX_ROWS]])
    dead_rows = table(['계정', '상품', '재고', '재고금액'],
                      [[esc(x['account']), plink(x['productId'], x['name']), f'{x["stock"]:,}', esc(x['stockValue'])] for x in dead_stock[:MAX_ROWS]])
    roas_rows = table(['계정', '상품', '광고비', 'ROAS', '순이익'],
                      [[esc(x['account']), plink(x['productId'], x['name']), won(x['adCost']), f'<span style="color:#e67e22;font-weight:600">{x["roas"]}%</span>', won(x['net'])] for x in low_roas[:MAX_ROWS]])
    loss_rows = table(['계정', '상품', '순이익', '매출', '광고비'],
                      [[esc(x['account']), plink(x['productId'], x['name']), f'<span style="color:#e74c3c;font-weight:600">{won(x["net"])}</span>', won(x['sales']), won(x['adCost'])] for x in losses[:MAX_ROWS]])

    total_issues = len(rank_issues) + len(swings_down) + len(overstock) + len(dead_stock) + len(low_roas) + len(losses)

    section = f'''
    <!-- MD 오늘 확인할 것 (build_md_section.py 자동 생성) -->
    <div style="background:#fff;border:2px solid #1a1a2e;border-radius:12px;padding:18px 20px;margin-bottom:24px;box-shadow:0 2px 8px rgba(0,0,0,0.06)">
      <div style="font-size:18px;font-weight:800;color:#1a1a2e;margin-bottom:2px">✅ 오늘 확인할 것 <span style="font-size:13px;font-weight:400;color:#999">— MD 액션 아이템 {total_issues}건</span></div>
      <div style="font-size:12px;color:#999;margin-bottom:14px">순위 이슈 · 판매량 급변 · 과재고 · 광고 저효율 · 적자 상품 (각 최대 {MAX_ROWS}건 표시)</div>
      {block('🚨 순위 이슈 — 노출 확인 필요', '#e74c3c', rank_rows, len(rank_issues), '순위 이슈 없음 ✓')}
      {block('📉 판매량 급감 (7일 평균 대비)', '#e74c3c', down_rows, len(swings_down), '급감 상품 없음 ✓')}
      {block('📈 판매량 급증 (재고·광고 대응 검토)', '#27ae60', up_rows, len(swings_up))}
      {block('📦 과재고 후보 (소진 ' + str(OVERSTOCK_DAYS) + '일 이상)', '#8e44ad', over_rows, len(overstock), '과재고 후보 없음 ✓')}
      {block('🛑 판매부진 재고 (7일 판매 0 + 재고 보유)', '#8e44ad', dead_rows, len(dead_stock))}
      {block('💸 광고 저효율 (ROAS ' + str(LOW_ROAS_PCT) + '% 미만)', '#e67e22', roas_rows, len(low_roas))}
      {block('🔻 적자 상품', '#e74c3c', loss_rows, len(losses), '적자 상품 없음 ✓')}
    </div>
'''

    t = open(args.report, encoding='utf-8').read()
    # 기존 MD 섹션 있으면 교체 (재실행 대응)
    t = re.sub(r'\n?\s*<!-- MD 오늘 확인할 것.*?</div>\n?(?=\s*<!-- Summary -->)', '\n', t, flags=re.S)
    anchor = '<!-- Summary -->'
    assert anchor in t, 'Summary anchor not found in report'
    t = t.replace(anchor, section + '\n    ' + anchor, 1)
    open(args.report, 'w', encoding='utf-8').write(t)

    print(f'✅ MD 섹션 주입 완료: 순위이슈 {len(rank_issues)} / 급감 {len(swings_down)} / 급증 {len(swings_up)} / 과재고 {len(overstock)} / 부진 {len(dead_stock)} / 저ROAS {len(low_roas)} / 적자 {len(losses)}')


if __name__ == '__main__':
    main()
