import json, re
from datetime import datetime, timedelta

# ── sed 치환용 플레이스홀더 ──
BASE = '/sessions/SESSION_ID/bigcell_TARGET_DATE'
OUTPUT_DIR = '/sessions/SESSION_ID/mnt/OUTPUT_DIR_NAME'
TARGET_DATE = 'TARGET_DATE_PLACEHOLDER'
PREV_DATE = 'PREV_DATE_PLACEHOLDER'

# ========== Helpers ==========
def parse_won(s):
    if not s: return 0
    s = str(s).replace('₩','').replace(',','').replace(' ','').split('\n')[0].split('(')[0]
    try: return int(s or '0')
    except: return 0

def parse_qty(s):
    if not s: return 0
    try: return int(str(s).replace(',','').split('\n')[0].split('(')[0].strip() or '0')
    except: return 0

def fmt(n):
    if n < 0: return f'-₩{abs(n):,}'
    return f'₩{n:,}'

def chg_html(diff, pct):
    if diff >= 0:
        return f'<span style="color:#27ae60">▲ {fmt(diff)}</span>'
    else:
        return f'<span style="color:#e74c3c">▼ {fmt(abs(diff))}</span>'

# ========== Data Loading ==========
with open(f'{BASE}/data_account1_coupang.json') as f: nutri_total = json.load(f)
with open(f'{BASE}/data_account1_naver.json') as f: nutri_nv = json.load(f)
with open(f'{BASE}/data_account2_coupang.json') as f: clean_cp = json.load(f)
with open(f'{BASE}/data_account3_coupang.json') as f: mine_cp = json.load(f)
with open(f'{BASE}/data_account4_coupang.json') as f: either_total = json.load(f)
with open(f'{BASE}/data_account4_naver.json') as f: either_nv = json.load(f)
with open(f'{BASE}/data_account5_coupang.json') as f: eden_cp = json.load(f)

with open(f'{BASE}/nutrijung_keyword_data.json') as f: nutri_rfm = json.load(f)
with open(f'{BASE}/cleanintech_keyword_data.json') as f: clean_rfm = json.load(f)
with open(f'{BASE}/mineflow_keyword_data.json') as f: mine_rfm = json.load(f)
with open(f'{BASE}/eithercompany_keyword_data.json') as f: either_rfm = json.load(f)
with open(f'{BASE}/edencorporation_keyword_data.json') as f: eden_rfm = json.load(f)
with open(f'{BASE}/nutrijung_naver_data.json') as f: nutri_nv_products = json.load(f)
with open(f'{BASE}/eithercompany_naver_data.json') as f: either_nv_products = json.load(f)

# ========== Product Name Maps ==========
PRODUCT_SHORT_NAMES = {
    # 뉴트리정 쿠팡
    '9161001505': '멜라토닌 5mg', '9221467723': '맥주효모', '9179488881': '이노시톨4000',
    '8943399049': '글루타치온', '8943192294': '브로멜라인', '8769633250': '콘드로이친',
    '9400311452': '루테인', '9165399920': '알파cd', '9288847656': 'ps70',
    '9400616139': '마그네슘', '8773958461': '멜라토닌2mg',
    # 이더컴퍼니 쿠팡
    '8325292270': '운동화', '7972887783': '아치깔창', '8003382441': '아쿠아슈즈',
    '8783930281': '신발', '8768985501': '런닝화(여)', '8783878699': '선글라스',
    '8810673811': '단화', '8422989181': '가습기', '8298273840': 'AB슬라이드',
    '7970095413': '빗자루', '8513569146': '내전근운동기구', '8549527628': '클린인가습기필터',
    '7582188500': '1+1 푹신한', '7770410464': '무중력슬리퍼', '7430539442': '타투팔토시',
    # 클린인테크 쿠팡
    '8522680027': '양말', '8409658552': '발목보호대', '8527077875': '볼캡',
    '8359551789': '무릎보호대', '8554950210': '드로즈', '8417214116': '손목보호대',
    '8564373976': '쿨팬티', '8603767969': '손목보호대', '8308572578': '고탄력허리보호대',
    '8615861399': '수면베개', '8124017542': '아치깔창', '9061613312': '남녀공용허리보호대',
    '8308519744': '슬개골보호대',
    # 마인플로 쿠팡
    '8412883857': '반원형 옷걸이', '8959736368': '정리대 블랙', '8887935359': '가방',
    '9018675705': '여자브라', '8887916796': '구두(비즈니스)', '9016436834': '페이크삭스',
    '9025582867': '남자팬티', '9116084651': '털부착변기시트', '9032105194': '호텔베개',
    '9016675188': '단목양말', '9452603308': '슬개골 무릎보호대', '8887893674': '구두',
    '8973372728': '정리대 블랙', '9047377097': '리빙 논슬립',
    # 이든코퍼레이션 쿠팡
    '9349793036': '캐리어방수커버', '9471983670': '샤워기헤드',
}

NAVER_SHORT_NAMES = {
    # 뉴트리정 네이버
    '13370924697': '활력 비타민B', '13371229974': '대용량300정 비타민D',
    '13371063214': '간건강 케어', '13370685315': '루테인 눈건강',
    '13371161022': '마그네슘 600mg', '13376260425': '올인원 멀티비타민',
    '12972561981': 'PS70', '12232817902': '브로멜라인',
    '12684610364': '멜라토닌 테아닌', '12232405745': '글루타치온',
    '12684689067': '알파CD', '12781378578': '비오틴', '12684630043': '미오이노시톨',
    '12931362266': '오메가3',
    # 이더컴퍼니 네이버
    '10250626818': '쿠션깔창', '10529422983': '기능성깔창',
    '13376374206': '목디스크 경추베개', '13376433854': '무릎보호대 슬개골',
    '13376628182': '아쿠아슈즈 논슬립', '13376451904': '심리스브라 스포츠',
}

NAVER_STORE_SLUGS = {'nutrijung': 'nutrijung', 'eithercompany': 'bodyinsole'}

BRAND_PREFIXES = {'뉴트리정','덴코','슬루나','바디인솔','이더커머스','클린인','가드웰',
                  '맨인핏','디아핏','아치온','아지온','푸에버','풋에버','풋토피아','글램루아','푸토피아'}

GHOST_IDS = {'9353395557'}

def extract_brand(name):
    words = name.split()
    if not words: return ''
    i = 0
    while i < len(words) and (words[i][0].isdigit() or words[i] in {'1+1','2+2','3Set','2Set'}):
        i += 1
    if i < len(words):
        for bp in BRAND_PREFIXES:
            if words[i].startswith(bp) or bp.startswith(words[i]):
                return bp
        return words[i]
    return words[0]

def extract_keyword(name, product_id):
    if product_id in PRODUCT_SHORT_NAMES:
        return PRODUCT_SHORT_NAMES[product_id]
    brand = extract_brand(name)
    rest = name
    for bp in BRAND_PREFIXES:
        rest = rest.replace(bp, '', 1).strip()
    FILLERS = {'가득채운','리얼','초임계','식물성','대용량','프리미엄','남녀공용','편한','쫀쫀',
               '구름','쿠션','무봉제','패드일체형','고함량','플러스','식약처','HACCP','인증',
               '함유','300정','180정','90정','60정','포함','비건','유기농','발편한','푹신한'}
    words = rest.split()
    meaningful = [w for w in words if w not in FILLERS and not re.match(r'^\d+$', w)
                  and len(w) > 1 and w not in {'및','의','에','을','를','로','은','는','이','가'}]
    if meaningful:
        return ' '.join(meaningful[:2])
    return name.split()[1] if len(name.split()) > 1 else name

def extract_naver_keyword(name, product_id):
    if product_id in NAVER_SHORT_NAMES:
        return NAVER_SHORT_NAMES[product_id]
    return extract_keyword(name, product_id)

# ========== Daily Data ==========
def parse_daily(data):
    result = []
    for d in data.get('daily', []):
        result.append({
            'date': d['date'],
            'sales': parse_won(d.get('sales', '0')),
            'profit': parse_won(d.get('profit', '0')),
            'adCost': parse_won(d.get('adCost', '0')),
            'netProfit': parse_won(d.get('netProfit', '0')),
        })
    return result

nutri_total_d = parse_daily(nutri_total)
nutri_nv_d = parse_daily(nutri_nv)
clean_cp_d = parse_daily(clean_cp)
mine_cp_d = parse_daily(mine_cp)
either_total_d = parse_daily(either_total)
either_nv_d = parse_daily(either_nv)
eden_cp_d = parse_daily(eden_cp)

def find_day(daily, date):
    for d in daily:
        if d['date'] == date: return d
    return {'sales': 0, 'profit': 0, 'adCost': 0, 'netProfit': 0, 'date': date}

# ========== Account Metrics ==========
def dual_account_metrics(total_daily, nv_daily):
    today_all = find_day(total_daily, TARGET_DATE)
    yest_all = find_day(total_daily, PREV_DATE)
    today_nv = find_day(nv_daily, TARGET_DATE)
    total_sales = today_all['sales']
    total_profit = today_all['netProfit']
    total_profit_y = yest_all['netProfit']
    total_adcost = today_all['adCost']
    cp_sales = today_all['sales'] - today_nv['sales']
    cp_profit = today_all['netProfit'] - today_nv['netProfit']
    cp_adcost = today_all['adCost'] - today_nv['adCost']
    diff = total_profit - total_profit_y
    pct = diff / total_profit_y * 100 if total_profit_y else 0
    return {
        'sales': total_sales, 'profit': total_profit, 'profit_y': total_profit_y,
        'adcost': total_adcost, 'diff': diff, 'pct': pct,
        'cp_sales': cp_sales, 'cp_profit': cp_profit, 'cp_adcost': cp_adcost,
        'nv_sales': today_nv['sales'], 'nv_profit': today_nv['netProfit'], 'nv_adcost': today_nv.get('adCost',0),
    }

def single_account_metrics(cp_daily):
    today = find_day(cp_daily, TARGET_DATE)
    yest = find_day(cp_daily, PREV_DATE)
    diff = today['netProfit'] - yest['netProfit']
    pct = diff / yest['netProfit'] * 100 if yest['netProfit'] else 0
    return {
        'sales': today['sales'], 'profit': today['netProfit'], 'profit_y': yest['netProfit'],
        'adcost': today['adCost'], 'diff': diff, 'pct': pct,
        'cp_sales': today['sales'], 'cp_profit': today['netProfit'], 'cp_adcost': today['adCost'],
        'nv_sales': 0, 'nv_profit': 0, 'nv_adcost': 0,
    }

n = dual_account_metrics(nutri_total_d, nutri_nv_d)
e = dual_account_metrics(either_total_d, either_nv_d)
c = single_account_metrics(clean_cp_d)
m = single_account_metrics(mine_cp_d)
d = single_account_metrics(eden_cp_d)

# Account order: 뉴트리정 → 이더컴퍼니 → 클린인테크 → 마인플로 → 이든코퍼레이션
accounts = [
    {'key': 'nutrijung', 'name': '뉴트리정', 'metrics': n, 'color': '#E8EAF6', 'bar_color': '#667eea',
     'title': '뉴트리정 (쿠팡+네이버)', 'rfm': nutri_rfm, 'nv_products': nutri_nv_products, 'has_naver': True},
    {'key': 'eithercompany', 'name': '이더컴퍼니', 'metrics': e, 'color': '#FFF3E0', 'bar_color': '#ffa726',
     'title': '이더컴퍼니 (쿠팡+네이버)', 'rfm': either_rfm, 'nv_products': either_nv_products, 'has_naver': True},
    {'key': 'cleanintech', 'name': '클린인테크', 'metrics': c, 'color': '#E3F2FD', 'bar_color': '#42a5f5',
     'title': '클린인테크 (쿠팡)', 'rfm': clean_rfm, 'nv_products': None, 'has_naver': False},
    {'key': 'mineflow', 'name': '마인플로', 'metrics': m, 'color': '#E8F5E9', 'bar_color': '#66bb6a',
     'title': '마인플로 (쿠팡)', 'rfm': mine_rfm, 'nv_products': None, 'has_naver': False},
    {'key': 'edencorporation', 'name': '이든코퍼레이션', 'metrics': d, 'color': '#FCE4EC', 'bar_color': '#ef5350',
     'title': '이든코퍼레이션 (쿠팡)', 'rfm': eden_rfm, 'nv_products': None, 'has_naver': False},
]

tp = sum(a['metrics']['profit'] for a in accounts)
tpy = sum(a['metrics']['profit_y'] for a in accounts)
ts = sum(a['metrics']['sales'] for a in accounts)
ta = sum(a['metrics']['adcost'] for a in accounts)
td = tp - tpy
tpct = td / tpy * 100 if tpy else 0
troas = ts / ta * 100 if ta else 0

# ========== Weekly Data ==========
target_dt = datetime.strptime(TARGET_DATE, '%Y-%m-%d')
WEEK_DATES = [(target_dt - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7, -1, -1)]
WEEKDAY_KOR = ['월', '화', '수', '목', '금', '토', '일']
weekly_sales, weekly_profits, labels = [], [], []
for date in WEEK_DATES:
    s = sum(find_day(dd, date)['sales'] for dd in [nutri_total_d, clean_cp_d, mine_cp_d, either_total_d, eden_cp_d])
    pr = sum(find_day(dd, date)['netProfit'] for dd in [nutri_total_d, clean_cp_d, mine_cp_d, either_total_d, eden_cp_d])
    dt = datetime.strptime(date, '%Y-%m-%d')
    labels.append(f"{date[5:].replace('-','/')}({WEEKDAY_KOR[dt.weekday()]})")
    weekly_sales.append(s)
    weekly_profits.append(pr)

# ========== Product Table Generation ==========
def build_rank_display(product_id, product_name, keyword_rank_raw):
    kw = extract_keyword(product_name, product_id)
    try:
        rank = int(str(keyword_rank_raw).strip())
    except:
        return '-'
    if rank < 1 or rank > 40:
        return '-'
    if rank == 1:
        return f'<b style="color:#e74c3c">{kw} 1위</b>'
    elif rank <= 20:
        return f'{kw} {rank}위'
    else:
        page = (rank - 1) // 20 + 1
        pos = rank - (page - 1) * 20
        return f'{kw} ({page}p){pos}위'

def coupang_product_table(products, table_id):
    valid = [p for p in products if p.get('product_id') and p['product_id'] not in GHOST_IDS]
    valid = sorted(valid, key=lambda p: parse_won(p.get('sale_net_amount','0')), reverse=True)
    filtered = []
    for p in valid:
        qty = parse_qty(p.get('sale_qty','0'))
        net = parse_won(p.get('sale_net_amount','0'))
        if qty > 0 or net > 0:
            filtered.append(p)

    TOP_N = 5
    top = filtered[:TOP_N]
    rest = filtered[TOP_N:]

    rows_html = ''
    for p in top:
        rows_html += _coupang_row(p)

    if rest:
        rows_html += f'''<tr id="cp_{table_id}_toggle_row"><td colspan="8" style="text-align:center;padding:8px;cursor:pointer;color:#667eea;font-size:13px;font-weight:600" onclick="toggleProducts('cp_{table_id}')">
            <span id="cp_{table_id}_toggle_text">▼ 나머지 {len(rest)}개 상품 더보기</span>
        </td></tr></tbody>
    <tbody id="cp_{table_id}_more" style="display:none">'''
        for p in rest:
            rows_html += _coupang_row(p)
        rows_html += '</tbody>'

    return f'''<div class="table-wrap">
    <table>
    <thead><tr>
        <th style="text-align:left">상품</th>
        <th class="r">주판매</th><th class="r">재고</th>
        <th class="r">판매</th>
        <th class="r">순이익</th>
        <th class="r">광고비</th>
        <th class="r">ROAS</th><th style="text-align:left">노출순위</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
    </table></div>'''

def _coupang_row(p):
    pid = p.get('product_id','')
    name_full = p.get('product_name','')
    brand = extract_brand(name_full)
    kw = extract_keyword(name_full, pid)
    display_name = f'{brand} · {kw}'
    url = f'https://www.coupang.com/vp/products/{pid}'
    link = f'<a href="{url}" style="color:#1a1a2e;text-decoration:none;border-bottom:1px dotted #999">{display_name}</a>'

    avg_qty = parse_qty(p.get('avg_sale_qty','0'))
    stock = parse_qty(p.get('stock_qty','0'))
    qty = parse_qty(p.get('sale_qty','0'))
    net = parse_won(p.get('sale_net_amount','0'))
    ad = parse_won(p.get('advert_ad_cost_sum','0'))
    roas_val = f'{net/ad*100:.0f}%' if ad > 0 else '-'
    rank_html = build_rank_display(pid, name_full, p.get('keyword_rank','-'))

    return f'<tr><td>{link}</td><td class="r">{avg_qty:,}개</td><td class="r">{stock:,}</td><td class="r">{qty:,}개</td><td class="r">{fmt(net)}</td><td class="r">{fmt(ad)}</td><td class="r">{roas_val}</td><td>{rank_html}</td></tr>\n'

def naver_product_table(products, table_id, store_slug):
    valid = [p for p in products if p.get('product_id')]
    valid = sorted(valid, key=lambda p: parse_won(p.get('sale_net_amount','0')), reverse=True)
    filtered = [p for p in valid if parse_qty(p.get('sale_qty','0')) > 0 or parse_won(p.get('sale_net_amount','0')) > 0]

    TOP_N = 5
    top = filtered[:TOP_N]
    rest = filtered[TOP_N:]

    rows_html = ''
    for p in top:
        rows_html += _naver_row(p, store_slug)

    if rest:
        rows_html += f'''<tr id="nv_{table_id}_toggle_row"><td colspan="4" style="text-align:center;padding:8px;cursor:pointer;color:#667eea;font-size:13px;font-weight:600" onclick="toggleProducts('nv_{table_id}')">
            <span id="nv_{table_id}_toggle_text">▼ 나머지 {len(rest)}개 상품 더보기</span>
        </td></tr></tbody>
    <tbody id="nv_{table_id}_more" style="display:none">'''
        for p in rest:
            rows_html += _naver_row(p, store_slug)
        rows_html += '</tbody>'

    return f'''<div class="table-wrap">
    <table>
    <thead><tr class="nv-header">
        <th style="text-align:left">상품</th>

        <th class="r">판매</th>
        <th class="r">순이익</th>
        <th class="r">광고비</th>

    </tr></thead>
    <tbody>{rows_html}</tbody>
    </table></div>'''

def _naver_row(p, store_slug):
    pid = p.get('product_id','')
    name_full = p.get('product_name','')
    brand = extract_brand(name_full)
    kw = extract_naver_keyword(name_full, pid)
    display_name = f'{brand} · {kw}'
    url = f'https://smartstore.naver.com/{store_slug}/products/{pid}'
    link = f'<a href="{url}" style="color:#1a1a2e;text-decoration:none;border-bottom:1px dotted #999">{display_name}</a>'

    qty = parse_qty(p.get('sale_qty','0'))
    net = parse_won(p.get('sale_net_amount','0'))
    ad = parse_won(p.get('advert_ad_cost_sum','0'))

    return f'<tr><td>{link}</td><td class="r">{qty}개</td><td class="r">{fmt(net)}</td><td class="r">{fmt(ad)}</td></tr>\n'

# ========== Build Account Sections ==========
def account_section(idx, acc):
    mt = acc['metrics']
    section_id = f'section_{idx}'

    nv_metrics = ''
    if acc['has_naver']:
        nv_metrics = f'''
            <div class="metric-card nv">
                <div class="metric-label">네이버 매출</div>
                <div class="metric-value">{fmt(mt['nv_sales'])}</div>
            </div>
            <div class="metric-card nv">
                <div class="metric-label">네이버 순이익</div>
                <div class="metric-value">{fmt(mt['nv_profit'])}</div>
            </div>'''

    cp_table = coupang_product_table(acc['rfm'], idx)

    nv_table = ''
    if acc['has_naver'] and acc['nv_products']:
        slug = NAVER_STORE_SLUGS.get(acc['key'], acc['key'])
        nv_table = f'''
        <h3 class="sub-title nv-title">네이버 상품별 실적</h3>
        {naver_product_table(acc['nv_products'], idx, slug)}'''

    return f'''
    <div class="account-section">
        <div class="account-header" onclick="toggleSection('{section_id}')">
            <div class="account-title-row">
                <span class="toggle-icon collapsed" id="icon_{section_id}">▼</span>
                <h2 class="account-name">{acc['title']}</h2>
            </div>
            <div class="header-metrics">
                <span class="header-profit">순이익 {fmt(mt['profit'])}</span>
                <span class="header-change">{chg_html(mt['diff'], mt['pct'])}</span>
                <span class="header-sales">매출 {fmt(mt['sales'])}</span>
            </div>
        </div>
        <div class="account-body collapsed" id="{section_id}">
            <div class="metrics-grid">
                <div class="metric-card cp">
                    <div class="metric-label">쿠팡 매출</div>
                    <div class="metric-value">{fmt(mt['cp_sales'])}</div>
                </div>
                <div class="metric-card cp">
                    <div class="metric-label">쿠팡 순이익</div>
                    <div class="metric-value">{fmt(mt['cp_profit'])}</div>
                </div>
                <div class="metric-card cp">
                    <div class="metric-label">쿠팡 광고비</div>
                    <div class="metric-value">{fmt(mt['cp_adcost'])}</div>
                </div>
                {nv_metrics}
            </div>
            <h3 class="sub-title">쿠팡 상품별 실적 (RFM)</h3>
            {cp_table}
            {nv_table}
        </div>
    </div>'''

# ========== Build Account Cards ==========
def account_card(idx, acc):
    mt = acc['metrics']
    sales_pct = mt['sales'] / ts * 100 if ts else 0
    profit_pct = mt['profit'] / tp * 100 if tp else 0
    # 순이익 비중 (음수 순이익 계정은 비중 음수로 표기)
    profit_pct_color = '#27ae60' if mt['profit'] >= 0 else '#e74c3c'
    return f'''
        <div class="acc-card" style="background:{acc['color']}" onclick="toggleSection('section_{idx}');scrollToSection('section_{idx}')">
            <div class="card-name">{acc['name']}</div>
            <div class="card-profit">{fmt(mt['profit'])}</div>
            <div class="card-change">{chg_html(mt['diff'], mt['pct'])}</div>
            <div class="card-sub">매출 {fmt(mt['sales'])} · 광고 {fmt(mt['adcost'])}</div>
            <div style="font-size:11px;color:#555;margin-top:4px">
                전일 순이익 {fmt(mt['profit_y'])}
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;font-size:11px;font-weight:600">
                <span style="color:#555">매출 비중</span>
                <span style="color:#1a1a2e">{sales_pct:.1f}%</span>
            </div>
            <div style="display:flex;gap:4px;margin-top:2px">
                <div style="flex:1;height:5px;background:#e0e0e0;border-radius:3px;overflow:hidden">
                    <div style="width:{max(0, sales_pct):.1f}%;height:100%;background:{acc['bar_color']};opacity:0.55;border-radius:3px"></div>
                </div>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px;font-size:11px;font-weight:600">
                <span style="color:#555">순이익 비중</span>
                <span style="color:{profit_pct_color}">{profit_pct:.1f}%</span>
            </div>
            <div style="display:flex;gap:4px;margin-top:2px">
                <div style="flex:1;height:5px;background:#e0e0e0;border-radius:3px;overflow:hidden">
                    <div style="width:{max(0, min(100, profit_pct)):.1f}%;height:100%;background:{acc['bar_color']};border-radius:3px"></div>
                </div>
            </div>
        </div>
'''

# ========== Generate HTML ==========
DAY_NAMES = ['월','화','수','목','금','토','일']
day_name = DAY_NAMES[target_dt.weekday()]

cards_html = '\n'.join(account_card(i, a) for i, a in enumerate(accounts))
sections_html = '\n'.join(account_section(i, a) for i, a in enumerate(accounts))
chart_labels = json.dumps(labels)
chart_sales = json.dumps([round(s/10000) for s in weekly_sales])
chart_profits = json.dumps([round(p/10000) for p in weekly_profits])

html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>빅셀 일일 매출 분석 보고서 - {TARGET_DATE}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background:#f5f6fa; color:#333; line-height:1.5; }}
.container {{ max-width:1200px; margin:0 auto; padding:20px; }}
.r {{ text-align:right !important; }}

/* Summary */
.summary-card {{
    background:linear-gradient(135deg,#667eea,#764ba2);
    border-radius:14px; padding:28px; color:#fff; margin-bottom:20px;
}}
.summary-card .label {{ font-size:14px; opacity:0.85; }}
.summary-card .big {{ font-size:38px; font-weight:800; margin:6px 0; }}
.summary-card .sub {{ font-size:13px; opacity:0.8; margin-top:6px; }}

/* Account cards row */
.cards-row {{ display:flex; gap:10px; flex-wrap:wrap; margin-bottom:20px; }}
.acc-card {{
    flex:1; min-width:180px; border-radius:12px; padding:16px;
    cursor:pointer; transition:transform .15s;
}}
.acc-card:hover {{ transform:translateY(-2px); }}
.acc-card .card-name {{ font-size:13px; color:#555; margin-bottom:2px; }}
.acc-card .card-profit {{ font-size:22px; font-weight:700; color:#1a1a2e; }}
.acc-card .card-change {{ font-size:11px; margin-top:3px; }}
.acc-card .card-sub {{ font-size:11px; color:#888; margin-top:3px; }}

/* Account sections */
.account-section {{ background:#fff; border:1px solid #e0e0e0; border-radius:12px; margin-bottom:12px; overflow:hidden; }}
.account-header {{
    padding:16px 20px; cursor:pointer; display:flex; justify-content:space-between;
    align-items:center; flex-wrap:wrap; gap:8px;
    background:#fafbfc; border-bottom:1px solid #eee; user-select:none;
    transition:background .15s;
}}
.account-header:hover {{ background:#f0f1f3; }}
.account-title-row {{ display:flex; align-items:center; gap:8px; }}
.toggle-icon {{ font-size:12px; color:#999; transition:transform .2s; display:inline-block; }}
.toggle-icon.collapsed {{ transform:rotate(-90deg); }}
.account-name {{ font-size:17px; font-weight:700; color:#1a1a2e; }}
.header-metrics {{ display:flex; gap:16px; align-items:center; flex-wrap:wrap; }}
.header-profit {{ font-size:16px; font-weight:700; color:#2c3e50; }}
.header-change {{ font-size:12px; }}
.header-sales {{ font-size:13px; color:#666; }}

.account-body {{ padding:20px; transition:max-height .3s ease; overflow:hidden; }}
.account-body.collapsed {{ display:none; }}

.metrics-grid {{ display:flex; gap:10px; flex-wrap:wrap; margin-bottom:16px; }}
.metric-card {{ flex:1; min-width:140px; border-radius:8px; padding:12px; }}
.metric-card.cp {{ background:#f8f9fa; }}
.metric-card.nv {{ background:#e8f5e9; }}
.metric-label {{ font-size:12px; color:#666; }}
.metric-card.nv .metric-label {{ color:#2e7d32; }}
.metric-value {{ font-size:18px; font-weight:700; margin-top:2px; }}

.sub-title {{ font-size:14px; color:#444; margin:14px 0 8px; font-weight:600; }}
.nv-title {{ color:#2e7d32; }}

/* Tables */
.table-wrap {{ overflow-x:auto; margin-bottom:12px; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th {{ padding:8px; border-bottom:2px solid #dee2e6; background:#f1f3f5; font-weight:600; white-space:nowrap; }}
.nv-header {{ background:#e8f5e9 !important; border-bottom-color:#c8e6c9 !important; }}
td {{ padding:6px 8px; border-bottom:1px solid #eee; }}
tr:hover td {{ background:#f8f9fa; }}

/* Option sub-rows */
.opt-toggle {{ cursor:pointer; font-size:10px; color:#667eea; display:inline-block; transition:transform .2s; vertical-align:middle; margin-right:2px; }}
.opt-toggle.open {{ transform:rotate(90deg); }}
.opt-row td {{ background:#f8f9ff !important; font-size:12px; color:#555; padding:4px 8px; border-bottom:1px solid #eef; }}

/* Chart */
.chart-section {{ background:#fff; border:1px solid #e0e0e0; border-radius:12px; padding:20px; margin-bottom:20px; }}
.chart-title {{ font-size:17px; font-weight:700; margin-bottom:12px; color:#1a1a2e; }}

.footer {{ text-align:center; padding:20px; color:#999; font-size:12px; }}
</style>
</head>
<body>
<div class="container">
    <div style="text-align:center;margin-bottom:24px">
        <h1 style="font-size:26px;color:#1a1a2e;margin-bottom:2px">빅셀 일일 매출 분석 보고서</h1>
        <div style="font-size:15px;color:#666">{TARGET_DATE} ({day_name}) 기준</div>
    </div>

    <!-- Summary -->
    <div class="summary-card">
        <div class="label">전체 순이익</div>
        <div class="big">{fmt(tp)}</div>
        <div style="font-size:14px;margin-top:2px">{chg_html(td, tpct)}</div>
        <div class="sub">전체 매출 {fmt(ts)} · 전체 광고비 {fmt(ta)} · 전일 순이익 {fmt(tpy)}</div>
    </div>

    <!-- Account Cards (비중 통합) -->
    <div class="cards-row">
        {cards_html}
    </div>

    <!-- Weekly Chart -->
    <div class="chart-section">
        <div class="chart-title">주간 매출/순이익 추이</div>
        <canvas id="weeklyChart" height="90"></canvas>
    </div>

    <!-- Account Sections (collapsible) -->
    {sections_html}

    <div class="footer">
        Generated by BigCell Daily Report · {datetime.now().strftime('%Y-%m-%d %H:%M')}
    </div>
</div>

<script>
function toggleSection(id) {{
    const body = document.getElementById(id);
    const icon = document.getElementById('icon_' + id);
    if (body.classList.contains('collapsed')) {{
        body.classList.remove('collapsed');
        icon.classList.remove('collapsed');
    }} else {{
        body.classList.add('collapsed');
        icon.classList.add('collapsed');
    }}
}}
function toggleProducts(tableId) {{
    const more = document.getElementById(tableId + '_more');
    const txt = document.getElementById(tableId + '_toggle_text');
    const row = document.getElementById(tableId + '_toggle_row');
    if (more.style.display === 'none') {{
        more.style.display = '';
        txt.textContent = '▲ 접기';
    }} else {{
        more.style.display = 'none';
        const cnt = more.querySelectorAll('tr').length;
        txt.textContent = '▼ 나머지 ' + cnt + '개 상품 더보기';
    }}
}}
function toggleOpt(id) {{
    const body = document.getElementById(id);
    const icon = document.getElementById('icon_' + id);
    if (body.style.display === 'none') {{
        body.style.display = '';
        icon.classList.add('open');
        icon.textContent = '▶';
    }} else {{
        body.style.display = 'none';
        icon.classList.remove('open');
        icon.textContent = '▶';
    }}
}}
function scrollToSection(id) {{
    setTimeout(() => {{
        const el = document.getElementById(id);
        if (el && !el.classList.contains('collapsed')) {{
            el.parentElement.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
        }}
    }}, 50);
}}

// Chart - Dual Y axis
new Chart(document.getElementById('weeklyChart'), {{
    type: 'bar',
    data: {{
        labels: {chart_labels},
        datasets: [
            {{ label: '매출 (만원)', data: {chart_sales}, backgroundColor: 'rgba(102,126,234,0.55)', borderRadius: 4, order: 2, yAxisID: 'y' }},
            {{ label: '순이익 (만원)', data: {chart_profits}, type: 'line', borderColor: '#e74c3c', borderWidth: 3.5, backgroundColor: 'rgba(231,76,60,0.05)', fill: true, tension: 0.35, pointRadius: 7, pointBackgroundColor: '#e74c3c', pointBorderColor: '#fff', pointBorderWidth: 2.5, pointHoverRadius: 10, order: 1, yAxisID: 'y1' }}
        ]
    }},
    options: {{
        responsive: true,
        interaction: {{ intersect: false, mode: 'index' }},
        plugins: {{ legend: {{ position: 'top' }} }},
        scales: {{
            y: {{ beginAtZero: true, position: 'left', title: {{ display: true, text: '매출 (만원)', color: '#667eea' }}, ticks: {{ callback: v => v.toLocaleString() + '만', color: '#667eea' }}, grid: {{ color: 'rgba(0,0,0,0.06)' }} }},
            y1: {{ beginAtZero: true, position: 'right', title: {{ display: true, text: '순이익 (만원)', color: '#e74c3c' }}, ticks: {{ callback: v => v.toLocaleString() + '만', color: '#e74c3c' }}, grid: {{ drawOnChartArea: false }} }}
        }}
    }}
}});
</script>
</body>
</html>'''

output_path = f'{OUTPUT_DIR}/빅셀_일일보고서_{TARGET_DATE}.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✅ Report generated: {output_path}")
print(f"")
print(f"=== 순이익 요약 (전체스토어 기준, 이중계산 제거) ===")
print(f"전체 순이익: {fmt(tp)}")
for a in accounts:
    mt = a['metrics']
    if a['has_naver']:
        print(f"  {a['name']}: 순이익 {fmt(mt['profit'])} (쿠팡 {fmt(mt['cp_profit'])} + 네이버 {fmt(mt['nv_profit'])})")
    else:
        print(f"  {a['name']}: 순이익 {fmt(mt['profit'])}")
