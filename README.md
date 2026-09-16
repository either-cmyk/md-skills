# md-skills

이더컴퍼니 MD 업무 자동화 스킬 모음 (21종).

> ⚠️ **이 저장소는 반드시 private 이어야 합니다.** 일부 스킬에 빅셀·사방넷 로그인 자격증명이
> 평문으로 들어 있습니다. 자세한 내용은 아래 [자격증명](#자격증명) 참고.

## 설치

```
/plugin marketplace add <owner>/md-skills
/plugin install md-skills@md-skills
```

## 수록 스킬

### 매출·분석

| 스킬 | 하는 일 |
|---|---|
| `bigcell-daily-report-md` | 빅셀 5개 계정 일일 매출 분석 보고서 생성 (수집 → 해석 → HTML) |
| `bigcell-daily-update` | 빅셀 매출 데이터 → 그로스 재고 DB 시트 동기화 (대표님 플러그인 사본) |
| `supply-cost-analyzer` | 수입 상품 SKU별 공급원가 (N값 + FBC·밀크런 배분 + 시트 대조) |
| `n-value-calculator` | 발주번호 기준 1위안당 원화(N값) 산출 후 원가 시트 입력 |
| `fbc-milkrun-calculator` | 입수량 기준 개당 물류비 즉시 계산 |

### 재고·발주

| 스킬 | 하는 일 |
|---|---|
| `nutrijeong-inventory` | 뉴트리정 재고 조회 → 시트 입력 → 한미양행 발주서 → 에이투지 세트포장 |
| `dr-on-inventory` | 닥터온 재고·번들 작업·작업요청 시트 |
| `auto-ordering` | 4개 사업자 재고 DB 분석 → CN인사이더 장바구니 자동 담기 |
| `cn-proforma-invoice-filler` | 발주번호 + PI 엑셀 → 은행 송금용 인보이스 작성 |

### 물류·입출고

| 스킬 | 하는 일 |
|---|---|
| `coupang-jiksong` | 쿠팡 동봉문서 PDF → 사방넷 **직송** 발주등록 엑셀 (v1.5.0) |
| `real-shipping` | 스마트스토어·쿠팡 주문 → 사방넷 발주등록 엑셀 변환 (택배) |
| `sabangnet-waybill` | 빈박스(체험단)·실배송 송장 등록·송신 자동화 (v1.8.0) |
| `cn-incoming-converter` | CN인사이더 출고내역 → 에이투지 간편입고 양식 |
| `loading-list-generator` | 쿠팡 동봉문서 + 출고내역 → 팔레트 적재리스트 PDF |
| `shipment-quantity-summary` | 출고내역 상품·옵션별 수량 집계 + 파레트 수 |
| `empty-box-delivery` | 쿠팡 빈박스 운송장 자동 매칭 |
| `notion-incoming-log` | 쿠팡 거래명세서 PDF → 노션 입고일지 등록 |

### 고객·기타

| 스킬 | 하는 일 |
|---|---|
| `cs-auto-answer` | 사방넷 전 쇼핑몰 문의 수집 → 법적 리스크 없는 답변 생성·송신 |
| `coupang-quality-response` | 쿠팡 품질확인서 답변 생성 (귀책없음 입장) |
| `packaging-design` | 패키징 디자인 요청서·목업·칼선 검수 |
| `daily-work-log` | 퇴근 전 업무 정리 → 노션 업무일지 등록 |

## 자격증명

다음 파일에 로그인 정보가 평문으로 포함되어 있습니다. **저장소를 public 으로 바꾸지 마세요.**

- `skills/bigcell-daily-report-md/SKILL.md` — 빅셀 5개 계정 공용 비밀번호
- `skills/bigcell-daily-report-md/scripts/integrated_bigcell.py` — 동일
- `skills/bigcell-daily-report-md/scripts/capture_screenshots.py` — 동일
- `skills/cs-auto-answer/SKILL.md` — 사방넷 로그인
- `skills/sabangnet-waybill/SKILL.md` — 사방넷 로그인 + 발주조회 엑셀 복호화 비밀번호

노션 PAT 등 토큰류는 **하드코딩하지 않는다**는 기존 원칙을 유지합니다 (노션 페이지에서 조회).

## 주의사항

- `bigcell-daily-report-md` 는 대표님 `bigcell-daily-report-v5` 플러그인에서 파생된 개인 커스텀 버전입니다.
  **원본 플러그인은 수정하지 않습니다.** 클라우드 샌드박스용 패치(프록시 포트 동적 조회, TLS 1.2 상한,
  MD 전용 `build_md_section.py`)가 들어가 있어 원본과 3개 파일이 다릅니다.
- `real-shipping/scripts/product_mapping.json` 은 상품 매핑 DB입니다. 신상품이 늘면 여기에 추가해야 합니다.
- `bigcell-daily-update` 는 대표님 `ether-bigcell` 플러그인의 사본(2026-08-24 기준)입니다.
  대표님 쪽이 갱신되면 여기 사본은 자동으로 따라오지 않습니다. 최신본이 필요하면
  대표님 마켓플레이스를 별도로 추가해서 설치하는 편이 낫습니다.
- `coupang-jiksong` 의 `mapping_rules.json` 은 SKU 마스터입니다. 신상품이 생기면 갱신해야 합니다.
- 각 스킬의 상세 동작은 해당 `SKILL.md` 를 참고하세요.

## 변경 이력

- **1.1.0** (2026-09-16) — `coupang-jiksong`(v1.5.0), `bigcell-daily-update`, `sabangnet-waybill`(v1.8.0) 추가. 총 21종.
- **1.0.0** (2026-09-16) — 최초 패키징. 계정 이관용으로 18개 스킬 통합.
