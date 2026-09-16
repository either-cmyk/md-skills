"""
빅셀 특이사항 섹션 데이터 요약 빌더.

입력: Phase 1이 생성한 bigcell_YYYY-MM-DD/ 폴더의 JSON들
출력: special_context.json — Claude가 해석 문장을 쓰기 위한 컨텍스트 데이터

원칙:
- 숫자 계산은 전부 여기서 처리 (전일 대비 변동, 적자 상품, 최고 수익 등)
- '주요 사유' / bullet 해석은 Claude가 context.json을 읽고 작성
- 3대 PC 모두 같은 입력이면 같은 context.json이 나옴 (결정적)
"""
import json
import re
import argparse
import os
from pathlib import Path


def parse_won(s):
    """₩1,234,567 → 1234567 (정수). 음수/공백/None 안전 처리."""
    if s is None or s == '' or s == '-':
        return 0
    if isinstance(s, (int, float)):
        return int(s)
    # 괄호 음수 (₩-1,234) or -₩1,234
    sign = -1 if '-' in s else 1
    digits = re.sub(r'[^\d]', '', s)
    return sign * (int(digits) if digits else 0)


def pct(curr, prev):
    """전일 대비 변동률(%). prev가 0이면 None."""
    if prev == 0:
        return None
    return round((curr - prev) / prev * 100, 1)


def extract_daily(data_path, target_date, prev_date, last_week_date=None):
    """data_account{N}_{channel}.json의 daily 배열에서 target/prev/last_week 행을 dict 반환."""
    with open(data_path, encoding='utf-8') as f:
        raw = json.load(f)
    rows = {r['date']: r for r in raw.get('daily', [])}
    t = rows.get(target_date, {})
    p = rows.get(prev_date, {})
    lw = rows.get(last_week_date, {}) if last_week_date else {}
    return {
        'target': {
            'sales': parse_won(t.get('sales')),
            'profit': parse_won(t.get('profit')),
            'adCost': parse_won(t.get('adCost')),
            'netProfit': parse_won(t.get('netProfit')),
        },
        'prev': {
            'sales': parse_won(p.get('sales')),
            'profit': parse_won(p.get('profit')),
            'adCost': parse_won(p.get('adCost')),
            'netProfit': parse_won(p.get('netProfit')),
        },
        'last_week': {
            'sales': parse_won(lw.get('sales')),
            'profit': parse_won(lw.get('profit')),
            'adCost': parse_won(lw.get('adCost')),
            'netProfit': parse_won(lw.get('netProfit')),
            'has_data': bool(lw),
        },
    }


def build_account(base_dir, account, target_date, prev_date, last_week_date=None):
    """계정 하나의 집계 데이터 생성."""
    prefix = account['data_prefix']
    name = account['name']
    is_dual = account['dual']

    cp_path = os.path.join(base_dir, f'data_{prefix}_coupang.json')
    cp = extract_daily(cp_path, target_date, prev_date, last_week_date) if os.path.exists(cp_path) else None

    result = {
        'name': name,
        'account_id': account['id'],
        'dual': is_dual,
        'target':    {'sales': 0, 'netProfit': 0, 'adCost': 0},
        'prev':      {'sales': 0, 'netProfit': 0, 'adCost': 0},
        'last_week': {'sales': 0, 'netProfit': 0, 'adCost': 0, 'has_data': False},
        'sub': {},  # dual 계정만 쿠팡/네이버 분리
    }

    if not is_dual:
        # 쿠팡 단일
        if cp:
            result['target'] = {k: cp['target'][k] for k in ('sales', 'netProfit', 'adCost')}
            result['prev']   = {k: cp['prev'][k]   for k in ('sales', 'netProfit', 'adCost')}
            result['last_week'] = {
                'sales': cp['last_week']['sales'],
                'netProfit': cp['last_week']['netProfit'],
                'adCost': cp['last_week']['adCost'],
                'has_data': cp['last_week']['has_data'],
            }
    else:
        # dual: "전체스토어" 대시보드 = 쿠팡+네이버 합산
        nv_path = os.path.join(base_dir, f'data_{prefix}_naver.json')
        nv = extract_daily(nv_path, target_date, prev_date, last_week_date) if os.path.exists(nv_path) else None

        if cp:
            # cp가 전체스토어 값 (이미 네이버 포함)
            result['target'] = {k: cp['target'][k] for k in ('sales', 'netProfit', 'adCost')}
            result['prev']   = {k: cp['prev'][k]   for k in ('sales', 'netProfit', 'adCost')}
            result['last_week'] = {
                'sales': cp['last_week']['sales'],
                'netProfit': cp['last_week']['netProfit'],
                'adCost': cp['last_week']['adCost'],
                'has_data': cp['last_week']['has_data'],
            }

        # 네이버 당일 값 (prev는 보통 없음 — daily 배열 1개만)
        nv_t = nv['target'] if nv else {'sales': 0, 'netProfit': 0, 'adCost': 0}
        nv_p = nv['prev'] if nv else {'sales': 0, 'netProfit': 0, 'adCost': 0}

        # 쿠팡 = 전체 - 네이버 (역산)
        cp_t_sales = result['target']['sales'] - nv_t['sales']
        cp_t_netProfit = result['target']['netProfit'] - nv_t['netProfit']
        cp_p_sales = result['prev']['sales'] - nv_p['sales']
        cp_p_netProfit = result['prev']['netProfit'] - nv_p['netProfit']

        result['sub'] = {
            'coupang': {
                'target': {'sales': cp_t_sales, 'netProfit': cp_t_netProfit},
                'prev':   {'sales': cp_p_sales, 'netProfit': cp_p_netProfit},
            },
            'naver': {
                'target': {'sales': nv_t['sales'], 'netProfit': nv_t['netProfit']},
                'prev':   {'sales': nv_p['sales'], 'netProfit': nv_p['netProfit']},
            },
        }

    # 변동 계산 (전일 대비 + 지난주 동일요일 대비)
    result['change'] = {
        'sales': result['target']['sales'] - result['prev']['sales'],
        'netProfit': result['target']['netProfit'] - result['prev']['netProfit'],
        'sales_pct': pct(result['target']['sales'], result['prev']['sales']),
        'netProfit_pct': pct(result['target']['netProfit'], result['prev']['netProfit']),
    }
    # 지난주 동일요일 대비 변동
    if result['last_week']['has_data']:
        result['change_week'] = {
            'sales': result['target']['sales'] - result['last_week']['sales'],
            'netProfit': result['target']['netProfit'] - result['last_week']['netProfit'],
            'sales_pct': pct(result['target']['sales'], result['last_week']['sales']),
            'netProfit_pct': pct(result['target']['netProfit'], result['last_week']['netProfit']),
        }
    else:
        result['change_week'] = None
    return result


def load_products(base_dir, account):
    """계정의 쿠팡/네이버 상품 데이터를 합친 리스트 반환. 각 항목에 channel, account 추가."""
    out = []
    aid = account['id']
    name = account['name']
    cp_path = os.path.join(base_dir, f'{aid}_keyword_data.json')
    if os.path.exists(cp_path):
        with open(cp_path, encoding='utf-8') as f:
            for p in json.load(f):
                out.append({
                    'account': name,
                    'channel': 'coupang',
                    'name': p.get('name', ''),
                    'productId': p.get('productId', ''),
                    'qty': int(re.sub(r'[^\d]', '', str(p.get('qty', '0'))) or 0),
                    'sales': parse_won(p.get('sales')),
                    'adCost': parse_won(p.get('adCost')),
                    'netProfit': parse_won(p.get('netProfit')),
                })
    nv_path = os.path.join(base_dir, f'{aid}_naver_data.json')
    if os.path.exists(nv_path):
        with open(nv_path, encoding='utf-8') as f:
            for p in json.load(f):
                out.append({
                    'account': name,
                    'channel': 'naver',
                    'name': p.get('name', ''),
                    'productId': p.get('productId', ''),
                    'qty': int(re.sub(r'[^\d]', '', str(p.get('qty', '0'))) or 0),
                    'sales': parse_won(p.get('sales')),
                    'adCost': parse_won(p.get('adCost')),
                    'netProfit': parse_won(p.get('netProfit')),
                })
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', required=True, help='bigcell_YYYY-MM-DD 폴더 경로')
    parser.add_argument('--target-date', required=True)
    parser.add_argument('--prev-date', required=True)
    parser.add_argument('--last-week-date', default=None, help='지난주 동일요일 (YYYY-MM-DD). 미제공 시 target-7일 자동계산')
    parser.add_argument('--output', required=True, help='context JSON 출력 경로')
    args = parser.parse_args()

    # 지난주 동일요일 자동 계산
    if not args.last_week_date:
        from datetime import datetime, timedelta
        td = datetime.strptime(args.target_date, '%Y-%m-%d')
        args.last_week_date = (td - timedelta(days=7)).strftime('%Y-%m-%d')

    ACCOUNTS = [
        {'id': 'nutrijung',       'name': '뉴트리정',       'dual': True,  'data_prefix': 'account1'},
        {'id': 'eithercompany',   'name': '이더컴퍼니',     'dual': True,  'data_prefix': 'account4'},
        {'id': 'cleanintech',     'name': '클린인테크',     'dual': False, 'data_prefix': 'account2'},
        {'id': 'mineflow',        'name': '마인플로',       'dual': False, 'data_prefix': 'account3'},
        {'id': 'edencorporation', 'name': '이든코퍼레이션', 'dual': False, 'data_prefix': 'account5'},
    ]

    # 계정별 집계
    accounts = [build_account(args.data_dir, a, args.target_date, args.prev_date, args.last_week_date) for a in ACCOUNTS]

    # 전체 합산 (각 계정 target/prev/last_week를 단순 합산)
    total = {
        'target':    {'sales': 0, 'netProfit': 0, 'adCost': 0},
        'prev':      {'sales': 0, 'netProfit': 0, 'adCost': 0},
        'last_week': {'sales': 0, 'netProfit': 0, 'adCost': 0, 'has_data': False},
    }
    lw_data_count = 0
    for a in accounts:
        for k in ('sales', 'netProfit', 'adCost'):
            total['target'][k] += a['target'][k]
            total['prev'][k] += a['prev'][k]
            total['last_week'][k] += a['last_week'][k]
        if a['last_week']['has_data']:
            lw_data_count += 1
    total['last_week']['has_data'] = lw_data_count > 0  # 하나라도 있으면 True
    total['last_week']['data_count'] = lw_data_count    # 5개 중 몇 개 계정이 데이터 있는지

    total['change'] = {
        'sales': total['target']['sales'] - total['prev']['sales'],
        'netProfit': total['target']['netProfit'] - total['prev']['netProfit'],
        'sales_pct': pct(total['target']['sales'], total['prev']['sales']),
        'netProfit_pct': pct(total['target']['netProfit'], total['prev']['netProfit']),
    }
    if total['last_week']['has_data']:
        total['change_week'] = {
            'sales': total['target']['sales'] - total['last_week']['sales'],
            'netProfit': total['target']['netProfit'] - total['last_week']['netProfit'],
            'sales_pct': pct(total['target']['sales'], total['last_week']['sales']),
            'netProfit_pct': pct(total['target']['netProfit'], total['last_week']['netProfit']),
        }
    else:
        total['change_week'] = None

    # 모든 상품 합치기
    all_products = []
    for a in ACCOUNTS:
        all_products.extend(load_products(args.data_dir, a))

    # Top netProfit (전체 상위 10)
    top_profit = sorted(all_products, key=lambda p: p['netProfit'], reverse=True)[:10]

    # 적자 상품 (netProfit < 0)
    loss = [p for p in all_products if p['netProfit'] < 0]
    loss_sorted = sorted(loss, key=lambda p: p['netProfit'])  # 큰 적자부터 (더 음수 먼저)

    # 적자 중 매출 큰 상품 (판매는 됐는데 손해 — 광고/마진 점검 대상)
    loss_high_sales = sorted(loss, key=lambda p: p['sales'], reverse=True)[:5]

    # 저마진 상품 (매출 > 100,000인데 netProfit/sales < 5%)
    low_margin = [
        p for p in all_products
        if p['sales'] > 100_000 and p['netProfit'] > 0 and (p['netProfit'] / p['sales']) < 0.05
    ]
    low_margin_sorted = sorted(low_margin, key=lambda p: p['sales'], reverse=True)[:5]

    context = {
        'target_date': args.target_date,
        'prev_date': args.prev_date,
        'last_week_date': args.last_week_date,
        'total': total,
        'accounts': accounts,
        'products': {
            'top_profit': top_profit,
            'loss_making': loss_sorted,
            'loss_high_sales': loss_high_sales,
            'low_margin': low_margin_sorted,
            'total_count': len(all_products),
        },
    }

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(context, f, ensure_ascii=False, indent=2)

    # 콘솔 요약
    print(f"✅ context 저장: {args.output}")
    print(f"   대상일: {args.target_date} / 전일: {args.prev_date} / 지난주 동일요일: {args.last_week_date}")
    print(f"   전체 매출: ₩{total['target']['sales']:,} (전일비 {total['change']['sales']:+,})")
    print(f"   전체 순이익: ₩{total['target']['netProfit']:,} (전일비 {total['change']['netProfit']:+,})")
    if total['change_week']:
        print(f"   지난주 대비 매출: {total['change_week']['sales']:+,} ({total['change_week']['sales_pct']}%)")
        print(f"   지난주 대비 순이익: {total['change_week']['netProfit']:+,} ({total['change_week']['netProfit_pct']}%)")
        print(f"   지난주 데이터: {total['last_week']['data_count']}/5 계정")
    else:
        print(f"   ⚠️ 지난주 동일요일 데이터 없음 — 대시보드/statistics 페이지에서 {args.last_week_date} 수집 실패")
    print(f"   계정 수: {len(accounts)} / 상품 수: {len(all_products)}")
    print(f"   적자 상품: {len(loss)}개 / 저마진 상품: {len(low_margin)}개")


if __name__ == '__main__':
    main()
