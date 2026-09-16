---
name: bigcell-daily-report-md
description: |
  [내 전용 복사본 — 원본: 대표님 bigcell-daily-report-v5 플러그인, 원본 플러그인은 절대 수정하지 않는다]
  빅셀(BigCell) 일일 매출 분석 보고서 생성 스킬 (MD 개인 커스텀 버전). 5개 이커머스 계정의 쿠팡/네이버 매출 데이터를 빅셀 웹사이트(app.bigcell.co.kr)에서 추출하고 종합 HTML 보고서를 생성한다. 반드시 이 스킬을 사용해야 하는 경우: "내 빅셀 보고서", "MD 빅셀 보고서", "내 버전 빅셀", "빅셀 보고서 내걸로" 등 사용자가 자신의 개인 버전을 명시적으로 요청할 때. 일반 "빅셀 보고서" 요청 시에도 이 개인 버전이 설치되어 있으면 우선 사용.
---

# 빅셀 일일 매출 분석 보고서 생성 (v5 포맷)

빅셀(https://app.bigcell.co.kr)에서 5개 계정의 쿠팡/네이버 매출 데이터를 추출하여 종합 HTML 보고서를 생성하는 워크플로우다.

## ⚡ 기본 동작 (v5.2.0 고정)

**날짜 기본값 = 어제 (YESTERDAY) — 절대 불변 규칙**

### 핵심 규칙 1 — "어제" 계산 시점

- 어제 = **스킬 호출 시점의 시스템 `date` 명령 기준**. 이전 세션 메모리·이전 보고서 파일 타임스탬프·이전 대화 컨텍스트로 추정 금지.
- 매번 셸에서 `$(date)` / `$(date -d 'yesterday' +%Y-%m-%d)` 를 실제로 실행해 현재 날짜를 확정한 뒤 진행.
- 예: 호출 시점 날짜가 2026-04-27 (월) → 어제 = 2026-04-26 (일).

### 핵심 규칙 2 — 사용자 명시 날짜 우선

사용자가 "오늘", "2026-04-20", "어제", "3일 전" 등 **명시적으로 날짜를 언급한 경우에만** 해당 날짜 사용. 그 외엔 항상 어제 자동 적용.

### 핵심 규칙 3 — **월요일 catch-up 규칙 (v5.2.0 신규)**

호출 시점 요일이 **월요일**이고, **금/토/일 보고서 중 누락된 것이 있으면 자동으로 함께 생성**한다.

흐름:
1. 호출 시점에 시스템 `date +%u` 로 요일 확인 (1=월, ..., 7=일)
2. 월요일(1)이면 지난 금/토/일 3일치 보고서 파일 존재 확인:
   ```bash
   for offset in 3 2 1; do  # 3=금, 2=토, 1=일 (오늘이 월일 때)
       D=$(date -d "${offset} days ago" +%Y-%m-%d)
       [ -f "/sessions/${SESSION_ID}/mnt/${OUT_DIR}/빅셀_일일보고서_v5_${D}.html" ] || MISSING+=("$D")
   done
   ```
3. 누락된 날짜 + 어제(=일요일) 합쳐 일괄 생성. 이미 있는 보고서는 건너뜀.
4. 월요일이 아니면 어제 1건만 생성 (기존 로직).

### 기타 규칙

- **확인 질문 금지**: "어느 날짜로 생성할까요?" 같은 되묻기 절대 하지 않는다. 바로 실행.
- `PREV_DATE` = TARGET - 1일, `LAST_WEEK_DATE` = TARGET - 7일 (모두 자동 계산)

Phase 1 스크립트 실행 셸 블록 맨 앞에서 반드시 다음 패턴으로 처리:
```bash
# 단일 날짜 (기본)
TARGET_DATE=${TARGET_DATE:-$(date -d 'yesterday' +%Y-%m-%d)}
PREV_DATE=$(date -d "${TARGET_DATE} -1 day" +%Y-%m-%d)

# 월요일 catch-up — 다중 날짜 큐
DOW=$(date +%u)
DATES_TO_RUN=()
if [ "$DOW" = "1" ]; then
    for offset in 3 2 1; do
        D=$(date -d "${offset} days ago" +%Y-%m-%d)
        [ -f "${OUT}/빅셀_일일보고서_v5_${D}.html" ] || DATES_TO_RUN+=("$D")
    done
else
    DATES_TO_RUN=("$TARGET_DATE")
fi
# 각 날짜에 대해 Phase 1~7 반복 실행
```

---

**보고서 최종 형태 (v5.2.0, 2026-04-27 고정):**
1. 5개 사업자 카드 — **매출 비중(%) + 순이익 비중(%)** 프로그레스바 포함
2. 주간 매출/순이익 추이 차트 — **8일 범위** (오늘 + 지난주 동일요일 포함) + **레이블 `MM/DD(한글요일)` 형식** (예: `04/13(월)`)
3. 계정별 상세 섹션 (RFM 스크린샷 포함, 접이식) — 쿠팡은 뷰포트 2600px로 로딩되어 광고ROAS까지 모든 컬럼 포함
4. 최하단 **특이사항 섹션** — **지난주 동일요일 대비 only** (전일 블록/컬럼 v5.1.0에서 제거). 📅 지난주 동일요일 블록 + 계정별 변동 표(지난주 순이익 · 변동 · 사유) + 상품 단위 이슈(실제 이슈 있을 때만 조건부 렌더)

v5.1.0 핵심 포맷 요구사항(**비중 카드 + 8일 차트(요일 레이블) + 지난주 동일요일 대비만 + 조건부 상품 섹션**)은 **반드시 포함**된다. 빠뜨리면 포맷 퇴행이다. 전일 대비 블록/컬럼 재도입 금지.


## ☁️ 클라우드(Cowork 원격) 세션 지원 — 패치 내장됨

이 MD버전의 `integrated_bigcell.py`에는 클라우드 샌드박스 대응 패치가 **이미 내장**되어 있다 (별도 수정 불필요):

- `CCR_AGENT_PROXY_ENABLED=1` 환경변수 감지 시 자동으로: 전체 Chromium 바이너리(`/opt/pw-browsers/chromium-*`) 사용 + `--proxy-server`(env `https_proxy`에서 읽음 — **포트가 세션마다 바뀌므로 절대 하드코딩 금지**) + `--ssl-version-max=tls1.2` 적용
- 대시보드 로딩 대기 9초, RFM 그리드 행 폴링(최대 40초) 내장
- 로컬 PC 실행 시에는 기존 동작과 동일

클라우드 실행 시 추가 주의사항:
- `/sessions/{ID}` 없음 → `mkdir -p /sessions/cloud/mnt/빅셀 /sessions/cloud/dev_bigcell/output` 후 SESSION_ID=`cloud`
- 스킬 캐시 .py 파일에 trailing null bytes 있을 수 있음 → `.rstrip(b'\x00')` 후 실행
- 백그라운드 실행 금지, `ONLY_ACCOUNT`/`DO` 분할 실행 사용 (계정당 dash ~24초, rfm ~50초)
- 완료 후: SendUserFile(attach) + `device_commit_files`로 PC `C:\Users\이더컴퍼니\Desktop\Claude-작업\빅셀 보고서\`에 저장
- 월요일 catch-up 판단 시 로컬 파일 대신 프로젝트 `보고서요약/` 문서로 기존 생성 여부 확인

## 🧑‍💼 Phase 6.5: MD '오늘 확인할 것' 섹션 (MD버전 전용 — 필수)

Phase 6(특이사항 주입) 완료 후, 보고서 **최상단**(Summary 카드 위)에 MD 액션 아이템 섹션을 주입한다:

```bash
python3 "스킬경로/scripts/build_md_section.py" \
  --data-dir /sessions/SESSION_ID/bigcell_YYYY-MM-DD \
  --report "보고서경로/빅셀_일일보고서_MD_YYYY-MM-DD.html" \
  --json-out /sessions/SESSION_ID/dev_bigcell/output/md_section_YYYY-MM-DD.json
```

포함 내용 (integrated_bigcell.py MD버전이 추출하는 확장 필드 rank/stockQty/stockValue/avgQty/roas 사용):
1. 🚨 **순위 이슈** — 판매 중 상품(어제 판매>0 또는 7일평균≥1) 중 "3페이지내 없음"/"노출순위 미등록"
2. 📉/📈 **판매량 급변** — 7일평균 대비 어제 판매량 ±50% 이상 (평균 3개 미만 제외)
3. 📦 **과재고 후보** — 재고소진일수(재고÷7일평균) 60일 이상 & 재고 50개 이상 / 🛑 **판매부진 재고** — 7일평균 0 + 재고 보유
4. 💸 **광고 저효율** — ROAS 200% 미만 + 광고비 1만원 이상 집행
5. 🔻 **적자 상품** — 순이익 -1만원 이하

판정 기준은 build_md_section.py 상단 상수로 조정 가능. 재실행 시 기존 MD 섹션은 자동 교체됨.
**최종 파일명: `빅셀_일일보고서_MD_YYYY-MM-DD.html`** (v5 완성본을 MD 이름으로 복사 후 주입).

## 전체 파이프라인

```
Phase 1: integrated_bigcell.py (Playwright) → 데이터 수집 + 스크린샷 + 지난주 동일요일 보강 (~4분)
Phase 2: rebuild_report.py → v2 HTML 보고서 생성 (카드에 비중(%) 포함)
Phase 3: build_v3_report.py → 스크린샷 교체 → v3 보고서
Phase 4: build_special_context.py → 특이사항 수치 데이터 집계 (지난주 비교 포함)
Phase 5: Claude 해석 문장 작성 → interpretation_YYYY-MM-DD.json 저장
Phase 6: inject_special_section.py → v3 보고서 최하단에 특이사항 섹션 주입 → v5 최종본
Phase 7: 중간 산출물 정리 → 공유 폴더에는 v5만 남기고 v2·v3 HTML 삭제
결과:   빅셀_일일보고서_v5_YYYY-MM-DD.html (최종, ~10MB, 공유 폴더 유일)
```

**총 소요시간: ~5분** (Phase 4~7은 Phase 1~3 완료 후 수치 기반으로 1분 내 처리)

---

## 계정 정보

| # | 계정 ID | 계정명 | 스토어 | data_prefix |
|---|---------|--------|--------|-------------|
| 1 | nutrijung | 뉴트리정 | 쿠팡+네이버 (dual) | account1 |
| 2 | eithercompany | 이더컴퍼니 | 쿠팡+네이버 (dual) | account4 |
| 3 | cleanintech | 클린인테크 | 쿠팡 | account2 |
| 4 | mineflow | 마인플로 | 쿠팡 | account3 |
| 5 | edencorporation | 이든코퍼레이션 | 쿠팡 | account5 |

**계정 순서 고정:** 뉴트리정 → 이더컴퍼니 → 클린인테크 → 마인플로 → 이든코퍼레이션. 카드, 상세섹션, 스크린샷, 특이사항 테이블 모두 이 순서.

모든 계정의 비밀번호: `dlejrhddyd1!`

---

## Phase 1: 통합 데이터 수집 (integrated_bigcell.py)

`scripts/integrated_bigcell.py`에 데이터 수집 + 스크린샷 캡처 + **지난주 동일요일 데이터 보강**이 통합되어 있다. **절대 스크립트를 처음부터 새로 작성하지 않는다.**

### 실행 방법

```bash
pip install playwright numpy Pillow --break-system-packages -q
playwright install chromium

# 날짜 계산 — 상단 "⚡ 기본 동작" 규칙 따라감
# 기본값: 어제. 사용자가 특정 날짜 명시했으면 TARGET_DATE=YYYY-MM-DD 로 환경변수 주입
TARGET_DATE=${TARGET_DATE:-$(date -d 'yesterday' +%Y-%m-%d)}
PREV_DATE=$(date -d "${TARGET_DATE} -1 day" +%Y-%m-%d)
# LAST_WEEK_DATE는 스크립트 내부에서 TARGET_DATE - 7일로 자동 계산

sed -e "s|SESSION_ID_PLACEHOLDER|현재세션ID|g" \
    -e "s|TARGET_DATE_PLACEHOLDER|${TARGET_DATE}|g" \
    -e "s|PREV_DATE_PLACEHOLDER|${PREV_DATE}|g" \
    -e "s|OUTPUT_DIR_PLACEHOLDER|출력디렉토리명|g" \
    "스킬경로/scripts/integrated_bigcell.py" | python3
```

### 분할 실행 (v5.3.0 — 샌드박스 셸 타임아웃 대응)

셸 호출당 실행 시간이 제한된 환경(Cowork 샌드박스 45초 등)에서는 전체 실행(~4분)이 불가능하다. v5.3.0부터 환경변수로 **계정×단계 분할 실행**을 지원한다 (환경변수 미지정 시 기존 전체 실행과 100% 동일):

```bash
# 계정 1개 × 단계 1개씩 실행 (호출당 12~35초)
ONLY_ACCOUNT=nutrijung DO=dash  python3 /tmp/staged.py   # 로그인+대시보드+지난주 보강
ONLY_ACCOUNT=nutrijung DO=rfm   python3 /tmp/staged.py   # 로그인+쿠팡 RFM+스크린샷
ONLY_ACCOUNT=nutrijung DO=naver python3 /tmp/staged.py   # 로그인+네이버 (듀얼 계정만)
```

- `ONLY_ACCOUNT`: 계정 id 1개로 필터 (`nutrijung`/`eithercompany`/`cleanintech`/`mineflow`/`edencorporation`)
- `DO`: `dash` | `rfm` | `naver` | `all`(기본)
- 실행 순서: 계정 순서 고정 규칙대로, 계정마다 dash → rfm → (듀얼이면) naver
- 각 단계는 독립 프로세스로 재로그인하며 결과 JSON/스크린샷은 동일 경로에 저장되므로 이후 Phase 2~7은 변경 없음
- **백그라운드(nohup/tmux) 실행은 샌드박스에서 호출 종료 시 강제 종료되므로 사용 금지** — 반드시 포그라운드 분할 실행

### 수집 프로세스 (계정당 자동 처리)

1. **로그인**: Auth.signIn()으로 Cognito 인증 (entry 모듈 동적 탐색)
2. **대시보드**: `/v2/dashboard`에서 innerText 파싱 → **보이는 모든 날짜를** 날짜별 ₩ 값 4개(매출, 이익금, 광고비, 순이익금)로 추출 저장
3. **지난주 동일요일 보강**: `LAST_WEEK_DATE`(7일 전)이 대시보드에 없으면 `/v2/statistics/coupang?q_sale_date_from=...&q_sale_date_to=...&q_show_type=summary`에서 요약행 역산 추출
4. **쿠팡 RFM**: AG Grid 스크롤+누적 방식으로 전체 상품 데이터 추출 + 스크린샷 캡처
5. **네이버** (듀얼 계정만): 네이버 RFM 페이지에서 상품 데이터 + 스크린샷 + floating-top 요약행에서 매출/순이익 추출

### 출력 파일

```
bigcell_YYYY-MM-DD/
  data_account{N}_coupang.json   # 대시보드 매출 데이터 (여러 날짜 포함)
  data_account{N}_naver.json     # 네이버 매출 데이터 (듀얼 계정만)
  {account_id}_keyword_data.json # 쿠팡 RFM 상품별 데이터
  {account_id}_naver_data.json   # 네이버 상품별 데이터 (듀얼 계정만)

screenshots/
  {account_id}_coupang_rfm.png
  {account_id}_naver.png         # 듀얼 계정만
```

`data_account{N}_coupang.json`의 `daily` 배열은 최소 TARGET/PREV/LAST_WEEK 3개 날짜를 포함해야 한다. Phase 4에서 지난주 비교에 사용.

### ⚠️ 듀얼 플랫폼 이중계산 주의 (nutrijung, eithercompany)

"전체스토어" 대시보드는 **이미 쿠팡+네이버 합산 데이터**다.
- **전체 순이익** = 전체스토어 순이익 (그대로)
- **쿠팡 순이익** = 전체스토어 순이익 − 네이버 순이익 (역산)
- 절대: 전체스토어 + 네이버 = 이중계산!

---

## Phase 2: 보고서 생성 (rebuild_report.py)

`scripts/rebuild_report.py`에 보고서 생성 스크립트가 번들되어 있다. **절대 스크립트를 처음부터 새로 작성하지 않는다.**

```bash
# 순서 중요: PLACEHOLDER 먼저, bare 토큰 나중 (bigcell_TARGET_DATE처럼 BASE 경로에 남은 bare TARGET_DATE 처리)
sed -e "s|TARGET_DATE_PLACEHOLDER|YYYY-MM-DD|g" \
    -e "s|PREV_DATE_PLACEHOLDER|YYYY-MM-DD-prev|g" \
    -e "s|SESSION_ID|현재세션ID|g" \
    -e "s|bigcell_TARGET_DATE|bigcell_YYYY-MM-DD|g" \
    -e "s|OUTPUT_DIR_NAME|출력디렉토리명|g" \
    "스킬경로/scripts/rebuild_report.py" | python3
```

출력: `빅셀_일일보고서_YYYY-MM-DD.html` (v2 기본 보고서)

### 보고서 규칙 (반드시 준수)

- **계정 순서 고정**: 뉴트리정→이더컴퍼니→클린인테크→마인플로→이든코퍼레이션
- **사업자 카드 비중(%) 필수**: 각 카드에 `매출 비중` + `순이익 비중` 두 개 프로그레스바. 음수 순이익은 빨간색(#e74c3c).
- **상품명**: `{브랜드} · {메인키워드 1~2개}` 형식만. 순위 텍스트 포함 금지.
- **상품 링크**: 쿠팡 `coupang.com/vp/products/{id}`, 네이버 `smartstore.naver.com/{slug}/products/{id}`
- **초기 토글**: 모든 account-body에 `collapsed` 클래스 (접힘 상태)
- **날짜**: 별도 지정 없으면 **무조건 어제** (상단 "⚡ 기본 동작" 참조). 확인 질문 금지.

---

## Phase 3: 스크린샷 교체 (build_v3_report.py)

Phase 2에서 생성된 기본 보고서(v2)의 상품별 실적 테이블을 AG Grid 스크린샷으로 교체한다.

```bash
# 출력 폴더명은 구 레거시 경로('빅셀 데일리 분석리포트')가 하드코딩되어 있으므로
# 현재 사용 중인 폴더명(예: '빅셀')으로도 반드시 치환해야 한다
sed -e "s|SESSION_ID|현재세션ID|g" \
    -e "s|REPORT_DATE|YYYY-MM-DD|g" \
    -e "s|빅셀 데일리 분석리포트|출력디렉토리명|g" \
    "스킬경로/scripts/build_v3_report.py" | python3
```

**교체 후 변경 사항:**
- 쿠팡/네이버 상품별 실적이 각각 **접이식 서브 토글**로 감싸짐 (쿠팡: 주황, 네이버: 초록)
- 이미지 `width:100%`로 보고서 폭에 맞게 확대
- 기본 상태: 접힘 (클릭해서 펼치기)

출력: `빅셀_일일보고서_v3_YYYY-MM-DD.html` (~10MB, Phase 4~6 입력)

---

## Phase 4: 특이사항 수치 컨텍스트 (build_special_context.py)

`scripts/build_special_context.py`가 Phase 1 JSON을 읽어 특이사항 섹션 해석에 필요한 수치를 전부 계산한다.

```bash
python3 "스킬경로/scripts/build_special_context.py" \
  --data-dir /sessions/SESSION_ID/bigcell_YYYY-MM-DD \
  --target-date YYYY-MM-DD \
  --prev-date YYYY-MM-DD-prev \
  --output /sessions/SESSION_ID/dev_bigcell/output/special_context_YYYY-MM-DD.json
```

`--last-week-date`는 생략 시 target − 7일로 자동 계산.

### 출력 context JSON 구조

```json
{
  "target_date": "YYYY-MM-DD",
  "prev_date": "YYYY-MM-DD",
  "last_week_date": "YYYY-MM-DD",
  "total": {
    "target": {...}, "prev": {...}, "last_week": {"has_data": true, ...},
    "change": {...},        // 전일 대비
    "change_week": {...}    // 지난주 동일요일 대비 (null 가능)
  },
  "accounts": [ { "name": "뉴트리정", "target":..., "prev":..., "last_week":..., "change":..., "change_week":... }, ... ],
  "products": { "top_profit":[], "loss_making":[], "loss_high_sales":[], "low_margin":[] }
}
```

**LAST_WEEK 데이터가 없으면** `change_week = null`, inject 단계에서 "N/A"로 렌더링된다.

---

## Phase 5: 해석 문장 작성 (Claude 직접)

Phase 4 context JSON을 읽고 다음 JSON을 작성해 `interpretation_YYYY-MM-DD.json`로 저장:

```json
{
  "weekly_bullets": [
    "지난주 동일요일 대비 해석 문장 1 (간결 1줄, 수치 + 결론)",
    "지난주 동일요일 대비 해석 문장 2",
    "... (2~4개, change_week가 있을 때만)"
  ],
  "account_reasons": {
    "전체 합산": "한 줄 요약 (지난주 대비 중심, 장황한 서술 금지)",
    "뉴트리정": "...",
    "이더컴퍼니": "...",
    "클린인테크": "...",
    "마인플로": "...",
    "이든코퍼레이션": "..."
  },
  "product_bullets": [
    "<b>상품명 — 이슈</b>: 수치 한 줄",
    "... (있는 경우에만, 아주 간략하게)"
  ]
}
```

**v5.1.0 포맷 원칙 (절대 준수):**
- **전일 대비 필드 작성 금지** — `summary_bullets` / `summary_interpretation` 등은 이번 포맷에서 렌더링되지 않음 (inject 스크립트가 무시). 해석은 **지난주 동일요일 대비로만** 작성.
- `weekly_bullets`는 **반드시 list**, 각 아이템 "수치 + 한 줄 결론" 스타일
- `account_reasons`는 **지난주 대비 주요 사유 중심**으로 서술 (전일 비교 금지)
- 수치는 context에서 **그대로 인용** (새로 계산 금지)
- **`product_bullets`는 실제 이슈 상품이 있을 때만 작성**. 데이터 부재 안내("데이터 수집 실패" 등)나 fallback 문구 절대 금지 — 상품 이슈 없으면 빈 리스트 `[]` 또는 키 생략. 그러면 inject가 ② 섹션 자체를 숨김.
- 아이템은 최대 3~5개, "상품명 — 핵심 이슈 한 줄" 형식으로 아주 간략하게.

**레거시 호환:** `weekly_interpretation` (단일 문자열) 키도 fallback으로 지원되지만, 신규 작성 시에는 `weekly_bullets` list 버전을 쓴다.

---

## Phase 6: 특이사항 섹션 주입 (inject_special_section.py)

`scripts/inject_special_section.py`가 Phase 3 v3 보고서의 `</body>` 직전에 특이사항 섹션 HTML 블록을 주입한다.

```bash
# v3 보고서를 v5 이름으로 복사 후 in-place 주입 권장
cp /sessions/SESSION_ID/mnt/OUTPUT_DIR/빅셀_일일보고서_v3_YYYY-MM-DD.html \
   /sessions/SESSION_ID/mnt/OUTPUT_DIR/빅셀_일일보고서_v5_YYYY-MM-DD.html

python3 "스킬경로/scripts/inject_special_section.py" \
  --context /sessions/SESSION_ID/dev_bigcell/output/special_context_YYYY-MM-DD.json \
  --interpretation /sessions/SESSION_ID/dev_bigcell/output/interpretation_YYYY-MM-DD.json \
  --report /sessions/SESSION_ID/mnt/OUTPUT_DIR/빅셀_일일보고서_v5_YYYY-MM-DD.html
```

### 주입되는 HTML 블록 구조 (v5.1.0)

```
📌 특이사항 — 지난주 동일요일 대비 분석
├─ 📅 지난주 동일요일 대비 (lw → 금일)   ← change_week 있을 때만
│   매출/순이익 변동 + weekly_bullets 리스트
├─ ① 계정별 변동 (지난주 동일요일 대비)
│   계정 | 금일 순이익 | 지난주 순이익 | 변동 | 주요 사유
└─ ② 주목할 상품 단위 이슈 (product_bullets 있을 때만 렌더링)
```

전일 대비 블록/컬럼은 v5.1.0에서 제거됨. 상품 단위 이슈 섹션은 product_bullets가 비어있으면 통째로 생략.

---

## Phase 7: 중간 산출물 정리 (v2·v3 HTML 삭제)

Phase 6 후 공유 폴더(`/mnt/OUTPUT_DIR`)에는 같은 날짜에 3개 HTML이 쌓여있다. 최종본(v5)만 남기고 중간물은 제거한다.

```bash
TARGET_DATE=YYYY-MM-DD
OUT=/sessions/SESSION_ID/mnt/OUTPUT_DIR

# v5 존재 여부 먼저 확인 — v5가 없으면 절대 v2/v3 삭제하지 말 것
if [ -f "${OUT}/빅셀_일일보고서_v5_${TARGET_DATE}.html" ]; then
    rm -f "${OUT}/빅셀_일일보고서_${TARGET_DATE}.html"      # v2 (~27KB)
    rm -f "${OUT}/빅셀_일일보고서_v3_${TARGET_DATE}.html"   # v3 (~10MB)
    echo "✅ 중간 산출물 정리 완료 — v5만 유지"
else
    echo "⚠️ v5 최종본이 없음 — 중간물 삭제 중단"
fi
```

**주의 사항:**
- **반드시 v5 존재 확인 후 삭제**: v5 생성이 실패했으면 중간물이 유일한 산출물이 됨
- **세션 내부(`/sessions/SESSION_ID/bigcell_YYYY-MM-DD/`)는 건드리지 않음**: JSON 원본 데이터는 재검증/재실행용으로 보존
- **옛 날짜 파일은 자동 정리 대상 아님**: 이번 실행 날짜(`TARGET_DATE`)분만 정리. 과거 보고서는 수동 관리.

---

## 생성 후 자가검증 (통과 못하면 공유 금지)

```bash
F="보고서경로/빅셀_일일보고서_v5_YYYY-MM-DD.html"
echo "Size:"; wc -c "$F"                                     # 5MB+ (스크린샷 포함)
echo "Base64 이미지:"; grep -c 'data:image/png;base64' "$F"   # == 7
echo "Collapsed:"; grep -c "account-body collapsed" "$F"      # == 5
echo "매출 비중 카드:"; grep -c '매출 비중</span>' "$F"         # == 5 (사업자 5개)
echo "순이익 비중 카드:"; grep -c '순이익 비중</span>' "$F"     # == 5
echo "MD 오늘 확인할 것:"; grep -c '오늘 확인할 것' "$F"   # >= 1 (MD버전 전용)
echo "특이사항 섹션:"; grep -c '특이사항 (자동 분석)' "$F"       # == 1
echo "지난주 동일요일 대비 컬럼:"; grep -c '지난주 동일요일 대비' "$F"  # >= 1

# v5.0.2~v5.0.3 — 주간 차트
echo "8일 차트 라벨:"; python3 -c "import re; t=open('$F',encoding='utf-8').read(); m=re.search(r'labels:\s*(\[[^\]]+\])', t); print(len(re.findall(r'[0-9]{2}/[0-9]{2}\\\\u[0-9a-f]{4}', m.group(1))) if m else 0)"  # == 8
echo "요일 레이블:"; python3 -c "import re; t=open('$F',encoding='utf-8').read(); m=re.search(r'labels:\s*(\[[^\]]+\])', t); print('OK' if m and re.search(r'[0-9]{2}/[0-9]{2}\([\\\\u]', m.group(1)) else 'MISSING')"  # OK

# v5.1.0 — 전일 관련 요소 제거 확인
echo "전일 컬럼 배경색 (제거됨):"; grep -c 'background:#fff3e0' "$F"  # == 0 (v5.1.0: 전일 배경색 제거)
echo "지난주 컬럼 배경색:"; grep -c 'background:#f3e5f5' "$F"   # >= 10 (표 전체 행)
echo "번호 리스트 ol (지난주만):"; grep -c 'padding-left:24px' "$F"   # >= 1 (지난주 블록)

echo "Account order:"; grep -oE 'class="account-name">[^<]+' "$F"
# 뉴트리정 → 이더컴퍼니 → 클린인테크 → 마인플로 → 이든코퍼레이션
```

**포맷 퇴행 방지 (v5.1.0)**:
- 매출/순이익 비중 카드가 5개씩 렌더링 안 되면 실패
- 특이사항 섹션이 빠지면 실패
- 특이사항 테이블에 "지난주 동일요일 대비" 컬럼이 없으면 실패
- 주간 차트 라벨이 8개가 아니면 실패 (7일 퇴행 금지)
- 주간 차트 라벨이 `MM/DD(요일)` 형식이 아니면 실패 (예: `04/13(월)`)
- 지난주 컬럼 배경색 `#f3e5f5`이 10회 이상 없으면 실패
- **전일 배경색 `#fff3e0`이 남아있으면 포맷 퇴행** (v5.1.0에서 제거된 요소)
- **"특이사항 — 지난주 동일요일 대비 분석" 제목이 없으면 실패** (v5.0.x 제목 "전일/지난주 대비 분석 요약" 사용 금지)

---

## 노션 업로드

생성 완료 후 📈 일일 보고서 (33cd9e75036781a789edfe10810ced4c) 하위에 페이지 생성:
- 제목: `일일 보고서 YYYY-MM-DD (요일)`
- 아이콘: 📈
- 내용: 전체 요약 + 계정별 순이익 테이블 + **지난주 동일요일 대비 한 줄 요약**

---

## 번들 스크립트

| 파일 | 용도 |
|------|------|
| `scripts/integrated_bigcell.py` | Phase 1: Playwright 통합 데이터 수집 + 스크린샷 + 지난주 보강 (**메인**) |
| `scripts/rebuild_report.py` | Phase 2: 데이터→HTML 보고서 생성 (비중 카드 포함) |
| `scripts/build_v3_report.py` | Phase 3: v2 보고서에 스크린샷 삽입 → v3 |
| `scripts/build_special_context.py` | Phase 4: 특이사항 수치 집계 (전일/지난주 비교 포함) |
| `scripts/inject_special_section.py` | Phase 6: 해석 문장 + 2단 테이블 HTML → v5 보고서 |
| `scripts/capture_screenshots.py` | (레거시) integrated_bigcell.py에 통합됨 |

**5개 핵심 스크립트 모두 sed 치환 또는 CLI argparse로 사용.** 절대 처음부터 새로 작성하지 않는다.

## 기술 메모

### 빅셀 앱 구조
- **Nuxt 3 (Vue 3) + PrimeVue** 기반 (React 아님)
- AWS Cognito 인증, Amplify Auth 모듈이 entry.*.js 의 minified export 로 노출됨
- entry 모듈 **해시뿐 아니라 export name 도** 빅셀 빌드마다 변경됨 → v5.2.1부터 `signIn`+`currentAuthenticatedUser` 메서드 보유 export 를 동적 탐색

### 로그인 JS (Playwright용, `{{` 이중 중괄호 필수, v5.2.1 동적 탐색 버전)
```javascript
(async () => {{
    const scripts = document.querySelectorAll('script[src*="/_nuxt/entry"]');
    let entryPath = null;
    for (const s of scripts) {{ if (s.src.includes('entry')) {{ entryPath = new URL(s.src).pathname; break; }} }}
    if (!entryPath) entryPath = '/_nuxt/entry.6e177eba.js';
    const mod = await import(entryPath);
    // 동적 Auth 탐색: signIn+currentAuthenticatedUser 둘 다 가진 export
    let Auth = null;
    const isAuthLike = (v) => v && typeof v.signIn === 'function' && typeof v.currentAuthenticatedUser === 'function';
    for (const k of Object.keys(mod)) if (isAuthLike(mod[k])) {{ Auth = mod[k]; break; }}
    if (!Auth) for (const k of Object.keys(mod)) {{
        const v = mod[k];
        if (v && typeof v === 'object') for (const k2 of Object.keys(v)) if (isAuthLike(v[k2])) {{ Auth = v[k2]; break; }}
        if (Auth) break;
    }}
    if (!Auth && isAuthLike(mod.K)) Auth = mod.K;  // 옛 fallback
    if (!Auth) throw new Error('Auth 객체 탐색 실패. mod keys: ' + Object.keys(mod).join(','));
    try {{ await Auth.signOut(); }} catch(e) {{}}
    await Auth.signIn({{ username: '{account_id}', password: '{password}' }});
    const user = await Auth.currentAuthenticatedUser();
    await Auth.updateUserAttributes(user, {{ 'custom:password': '{password}' }});
    return 'login_ok';
}})();
```

### AG Grid 관련
- AG Grid는 수평+수직 가상 렌더링 사용 — 뷰포트 밖의 열/행은 DOM에 없음
- Playwright에서는 뷰포트 높이를 scrollHeight×3으로 키워서 전체 행 렌더링 강제
- 스크롤+누적 방식으로 데이터 수집: `window._allProducts` 객체에 pid 기준 중복 제거
- pinned 셀은 img+text 복합 구조 → `textContent` 빈 문자열, 반드시 `innerText` 사용
- PIL+numpy로 하단 빈행/우측 빈공간 자동 크롭

### 대시보드 데이터 구조
대시보드 innerText에서 날짜별 데이터를 파싱한다. `q_show_type=daily` URL은 사용하지 않는다 (빈 페이지).
```
innerText 패턴 (날짜당):
2026-04-15
(수)
₩26,693,979    ← 매출 (sales)
5.5%
₩8,072,632     ← 이익금 (profit)
9.7%
₩401,953       ← 광고비 (adCost)
0.3%
₩7,670,679     ← 순이익금 (netProfit)
10.1%
```

### 지난주 동일요일 보강 (v5에서 추가)
대시보드 디폴트 뷰에 7일 전 데이터가 없으면 `/v2/statistics/coupang` 페이지의 `.ag-floating-top-container .ag-row`에서 요약 매출/순이익/광고비/순이익금 역산 추출. 듀얼 계정도 전체스토어 기준이므로 쿠팡 URL 하나로 충분.

### 팝업 제거 (필수)
빅셀에는 2종류 팝업이 존재:
1. **PrimeVue 다이얼로그** (`.p-dialog-mask`, `.p-component-overlay`)
2. **빅셀 커스텀 공지** (`.popup`, `.popup-container`)

팝업 + body overflow 둘 다 제거해야 함. integrated_bigcell.py의 `dismiss_overlays()` + `CLEANUP_JS` + `add_init_script`로 자동 처리.

### 절대 하지 말 것
- 스크립트를 처음부터 새로 작성하지 않는다 — sed 치환/argparse로 사용
- `q_show_type=daily` URL 사용 금지 — 해당 페이지 비어있음
- Chrome MCP로 물리적 입력(triple_click, form_input 등) 금지 — Vue v-model 바인딩 우회 못함
- **v5 포맷 요구사항(비중 카드 + 특이사항 섹션 + 지난주 비교) 누락 금지** — 하나라도 빠지면 포맷 퇴행

## 개선 이력

- **v5.3.0 (2026-07-10)** — 빅셀 신규 UI 컬럼 구조 대응 + 계정×단계 분할 실행 지원
  - 증상 1: 6월 초 빅셀 배포로 RFM 그리드 컬럼 구조 변경 — `product_info` 단일 컬럼이 `product_id` + `product_name` (pinned-left)으로 분리되고, `sale_amount` 컬럼이 사라지며 매출이 `sale_qty` 셀 안에 `163\n(₩1,276,884)` 형태로 통합됨. 기존 추출 JS가 상품 0개 반환.
  - 해결 1: RFM 추출 JS 전면 교체 — `.ag-center-cols-container .ag-row` 순회 + `row-index`로 pinned-left 행 매칭 → `product_id`/`product_name`에서 pid·상품명 추출 (구 `product_info` 구조 fallback 유지), 매출은 `gv('sale_amount')` 우선 + 없으면 `sale_qty` 셀 내 `₩...` 정규식 추출. 2026-06-12~07-10 6회 일일 실행으로 검증 완료.
  - 증상 2: Cowork 샌드박스 셸이 호출당 45초 제한 + 백그라운드 프로세스(nohup/setsid/tmux 모두)를 호출 종료 시 강제 종료 → 전체 실행(~4분) 불가능.
  - 해결 2: `ONLY_ACCOUNT`(계정 id 필터) + `DO`(dash|rfm|naver|all) 환경변수 추가. 미지정 시 기존 전체 실행과 동일(하위 호환 100%). 분할 시 호출당 12~35초로 13회 호출이면 5계정 전체 수집 완료. 상세는 "분할 실행" 섹션.
  - 구현 위치: `integrated_bigcell.py` — ACCOUNTS 정의 직후 env 필터, 대시보드/쿠팡RFM/네이버 3개 구간 조건 분기, RFM 스크롤 수집 JS 교체.

- **v5.2.1 (2026-05-06)** — 빅셀 entry.js 빌드 변경 대응 (동적 Auth 탐색)
  - 증상: 빅셀이 5/5경 entry.js 새로 빌드 → minified export name 변경(이전 `K` → 다른 글자) → `Auth.signIn is not a function` 에러로 모든 계정 로그인 실패.
  - 원인: 기존 `LOGIN_JS` 가 `const Auth = mod.K;` 로 export name 을 하드코딩. 빅셀 빌드마다 minify 결과 달라져서 깨질 수 있음.
  - 해결: `signIn` + `currentAuthenticatedUser` 메서드 둘 다 가진 export 를 자동 탐색. 1단계 top-level 순회 → 2단계 한 단계 깊이 → 3단계 옛 `mod.K` fallback. 모든 단계 실패 시 명시적 에러 메시지 throw (디버깅용 mod keys 동봉).
  - 구현 위치: `integrated_bigcell.py` 의 `LOGIN_JS` 상수 블록.
  - 후속 효과: 빅셀이 또 빌드 변경해도 export name 만 바뀌고 메서드 시그니처 동일하면 자동 대응.

- **v5.2.0 (2026-04-27)** — 날짜 규칙 강화 + 월요일 catch-up
  - 변경: (1) "어제" 계산이 항상 스킬 호출 시점의 시스템 `date` 명령 기준임을 명시 (이전 세션 메모리/타임스탬프 추정 금지). (2) 월요일에 호출되면 지난 금/토/일 보고서 누락분을 어제(일요일)와 함께 자동 일괄 생성하는 catch-up 규칙 추가.
  - 이유: 주말은 보고서 생성 안 되는 경우 많음. 월요일 출근 후 "보고서 생성해줘" 한 번으로 주말 3일치 + 어제까지 한 번에 처리되어야 워크플로우 효율적.
  - 구현 위치: `SKILL.md` 의 "⚡ 기본 동작" 섹션. 실제 스크립트는 SKILL.md 가이드대로 호출 시점에 셸에서 날짜·요일 판정 후 누락 날짜만 큐잉해 Phase 1~7 반복. 별도 스크립트 신규 작성 불요.

- **v5.1.0 (2026-04-23)** — 특이사항 섹션 포맷 간소화 (지난주 동일요일 대비 only)
  - 변경: (1) 한눈 요약 "전일 → 금일" 블록 완전 제거, (2) 계정별 변동 표에서 전일 대비 2개 컬럼(전일 순이익 + 변동) 제거 → 지난주 컬럼(지난주 순이익 + 변동)만 유지, (3) 상품 단위 이슈 섹션은 `product_bullets`가 실제로 있을 때만 렌더링 (빈 리스트/키 없음 → ② 섹션 통째로 생략), (4) 섹션 제목 "전일/지난주 대비 분석 요약" → "지난주 동일요일 대비 분석", 색상 테마 주황→보라(#8e44ad) 통일.
  - 이유: 전일 대비는 빅셀 대시보드 자체에서 바로 확인 가능하고 정산 사이클 때문에 수치 변동이 잦음. 지난주 동일요일 대비가 실제 인사이트의 핵심. 상품 단위는 데이터 없을 때 "데이터 수집 실패" 같은 fallback 문구가 노이즈만 추가해서 조건부 숨김으로 전환.
  - 구현 위치: `inject_special_section.py` 의 `build_html` 전면 간소화. Phase 5 가이드의 interpretation JSON 스키마에서 `summary_bullets`/`summary_interpretation` 삭제 (레거시 호환만 유지, 렌더링은 안 함). 자가검증 grep도 v5.1.0 포맷 반영.

- **v5.0.9 (2026-04-23)** — RFM 페이지 진입 전 viewport 분기 설정 (쿠팡 ROAS DOM 렌더링 강제)
  - 증상: v5.0.8에서도 쿠팡 광고ROAS 컬럼이 스크린샷에 안 잡힘. 이유: context 기본 viewport가 1800이라 AG Grid가 처음 렌더링 시 12개 컬럼 중 11개만 DOM에 배치하고 ROAS는 가상 렌더링으로 제외. 이 상태에서 scrollWidth 측정해도 ROAS 미포함 값이라 이후 뷰포트 확장 로직이 발동 안 함 (catch-22).
  - 해결: `extract_rfm_and_screenshot` 진입 직후, goto 호출 **전에** `set_viewport_size`로 분기 설정. 쿠팡=2600 / 네이버=1800. 초기부터 넓은 뷰포트에 진입하므로 AG Grid가 처음부터 모든 컬럼을 DOM에 렌더링. 네이버는 1800 명시 유지해 이전 쿠팡 호출이 남긴 2600 상속 방지 (column stretch 차단).
  - 구현 위치: `integrated_bigcell.py` 의 `extract_rfm_and_screenshot` 함수 시작부. v5.0.8의 screenshot-time scrollWidth 확장 로직은 그대로 보존 (fallback 역할).

- **v5.0.8 (2026-04-23)** — RFM 스크린샷 width 계산 개선 (네이버 화질 저하 수정)
  - 증상: v5.0.7에서 뷰포트 width 최소 2400 강제 확장 → 쿠팡 광고ROAS 가시성은 확보했지만, 네이버처럼 컬럼 적은 그리드는 AG Grid가 남는 공간을 컬럼 폭 확장으로 채워서 내용이 sparse해지고, 2x DPR + HTML `width:100%` 축소 시 픽셀 밀도 저하 → 흐릿한 스크린샷 발생.
  - 해결: `scrollWidth + 100` 만큼만 확장하되 현재 viewport보다 작으면 그대로 유지. 최소 2400 제한 제거. 쿠팡은 scrollWidth가 크니 자연스럽게 확장되어 ROAS 포함, 네이버는 기본 viewport 유지되어 화질 원상복구.
  - 구현 위치: `integrated_bigcell.py` 의 `extract_rfm_and_screenshot` viewport 재설정 구간만 수정 (`GET_GRID_HEIGHT_JS`는 v5.0.7 그대로 유지).

- **v5.0.7 (2026-04-23)** — RFM 스크린샷 뷰포트 width 확장 (우측 컬럼 잘림 해결)
  - 증상: 쿠팡/네이버 RFM 스크린샷 우측 `광고ROAS` 컬럼이 잘려서 안 보임. 기존 3개 컬럼(광고분석/운영상태/1688구매요청)은 CSS `display:none`으로 이미 잘 숨겨지고 있는데도 우측 잘림 발생.
  - 원인: AG Grid가 **수평으로도 가상 렌더링**을 하기 때문에, 뷰포트 너비 밖의 컬럼은 DOM에 아예 존재하지 않음 → `.ag-root-wrapper` 스크린샷에도 안 잡힘. 기존 코드는 스크린샷 직전 viewport **height만** 키우고 width는 그대로 둬서 문제.
  - 해결: `GET_GRID_HEIGHT_JS`에 `scrollWidth` 추가(body/header viewport 중 큰 값). 스크린샷 직전 `set_viewport_size`로 width도 `scrollWidth + 200` (최소 2400)으로 확장. 확장 후 AG Grid가 전체 컬럼을 DOM에 렌더링 → 스크린샷에 전부 포함.
  - 구현 위치: `integrated_bigcell.py` 의 `GET_GRID_HEIGHT_JS`(scrollWidth 필드 추가) + `extract_rfm_and_screenshot`의 viewport 재설정 구간.
  - v5.0.6 롤백: 잘못된 방향(7일 평균판매량 + 노출순위 동적 숨김)이었음. 사용자 원래 의도는 "우측 잘림 해결"이지 "유용한 지표 컬럼 숨기기"가 아니었음. CLEANUP_JS는 5.0.5 원상복구.

- **v5.0.5 (2026-04-22)** — 네이버 매출 Lambda raw API 가로채기
  - 증상: `.ag-floating-top-container` 요약행에서 `col-id="sale_amount"` 셀이 빈 문자열을 반환 → 네이버 매출이 항상 ₩0 으로 저장 → 매출 비중 % 왜곡
  - 원인: 빅셀이 네이버 통계 페이지 요약행에서 `sale_amount` 컬럼을 UI 에서 숨길 수 있음 (사용자 컬럼 설정 혹은 일시 비공개). 순이익 `sale_net_amount` 만 노출되는 케이스 발생.
  - 해결: Playwright `page.on('response')` 로 `ta7e75y...lambda-url.ap-northeast-2.on.aws` 응답을 가로챔. 응답 `body` 필드가 `gzip+base64` 인코딩된 `{statistics:[상품 row, …]}` 구조 → 디코드 후 각 row 의 `sale_amount` 합산. UI 에 안 보이는 상황에도 raw API 에는 그대로 내려옴.
  - 구현 위치: `integrated_bigcell.py` 의 `# ── 5) 네이버 상품 데이터` 블록 직전 리스너 등록, `nv_sales_lambda` 에 합계 저장, nv_summary 구성 시 Lambda 값이 있으면 UI 요약행보다 우선 사용
  - 검증 (2026-04-21): 뉴트리정 = ₩824,575, 이더컴퍼니 = ₩718,579 (두 값 UI 재집계치와 일치)
