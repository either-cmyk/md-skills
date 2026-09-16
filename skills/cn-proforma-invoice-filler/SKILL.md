---
name: cn-proforma-invoice-filler
description: "CN인사이더 발주번호 + 프로포마 인보이스 엑셀을 받아 은행 송금용 인보이스(품목·수량·단가)를 채운다. '인보이스 채워줘', 'PI 작성', '송금 인보이스', '프로포마 인보이스' 요청 시 사용."
---

# CN인사이더 프로포마 인보이스 채우기

## 목적
CN인사이더(CNINSIDER INTERNATIONAL TRADING LIMITED)가 보내준 PROFORMA INVOICE 엑셀은
`1 PCS × 총액` 한 줄로만 되어 있어 은행(T/T 송금 심사)에서 반려된다.
은행은 **개수 · 품목 · 단가 · 총금액**이 모두 적혀 있고 `수량 × 단가 = 금액`이 정확히 맞는지 본다.
이 스킬은 발주번호로 CN인사이더에서 품목/수량을 수집해 인보이스를 은행 제출 가능한 형태로 채운다.

## 절대 원칙
1. **USD 총액은 인보이스에 이미 적힌 값을 그대로 고정**한다 (예: $16,900.00). CN인사이더의 CNY→USD 환산에는 오차가 있을 수 있으므로 절대 재계산하지 않는다. 사용자 명시 지시.
2. 모든 라인에서 `Quantity × Unit Price = Total Amount`가 **소수점(센트)까지 정확히** 일치해야 하고, 라인 합계 = 인보이스 총액이어야 한다.
3. 수량은 CN인사이더 발주 상세의 수량(상품 총수량)을 그대로 쓴다. 양말은 20켤레 묶음으로 판매하지만 CN인사이더 수량은 낱개(켤레) 기준이다. 혼합세트 SKU는 CN인사이더가 세트 단위로 집계하므로 그대로 따른다. 20을 곱하거나 나누지 않는다.
4. 양식(헤더, 주소, PI NO, Date, 은행정보, 도장 이미지 '캡처' 시트)은 절대 건드리지 않는다. 품목 표(row 13~19)와 TOTAL(row 20)만 수정.

## 입력
- 인보이스 엑셀 (시트명 `PROFORMA     INVOICE`, 공백 5개 주의). 채워야 할 셀:
  - A13:E19 품목 행 (A=ITEM NO., B=Quantity PCS, C=DESCRIPTION, D=Unit Price/US$, E=Total Amount USD)
  - B20 = 총 PCS, C20 = 'PCS', E20 = 총액 (E20에 이미 적힌 USD 총액이 기준값)
- 발주번호 1개 이상 (형식 `S-QDE######`, 뒤에 2/3 붙는 경우도 있음: S-QDE2608282)

## 절차

### Step 1. 엑셀 구조 확인
```python
import openpyxl; wb=openpyxl.load_workbook(path); ws=wb['PROFORMA     INVOICE']
# E20(또는 E13)의 '$16900.000' 형태 문자열에서 USD 총액 파싱
```

### Step 2. CN인사이더 발주 상세 수집 (Claude in Chrome)
- 크롬이 여러 대 연결되어 있으면 AskUserQuestion으로 어느 브라우저인지 묻고 `select_browser`. (2026-09 기준 CN인사이더 로그인된 크롬 = "Browser 3", 하지만 매번 확인)
- 로그인 페이지로 리다이렉트되면 사용자에게 직접 로그인 요청 (비밀번호 입력 금지).
- `https://www.cninsider.co.kr/mall/#/orderList` 진입 → `get_page_text`로 목록에서 발주번호·결제금액 확인.
- 각 발주의 `상세보기` 클릭 (`find`로 "상세보기 link for 발주번호 X" 검색 후 ref 클릭) → `get_page_text`.
- 상세에서 추출:
  - 라인별: 상품명(한글), 바코드, 수량, 단가(¥), 금액(¥)
  - 하단: `상품 총수량 : N건`, `상품총금액`, `수수료`, `부가서비스`, `결제금액`
- 검증: 라인 수량 합 = 상품 총수량. 발주 결제금액 합 ÷ USD 총액 ≈ 6.0~6.3 CNY/USD 이면 정상.
- 끝나면 탭 닫기.

### Step 3. 품목 그룹핑
- 한 줄로 쓰면 단가가 나누어떨어지지 않으므로 **품목 카테고리별로 여러 줄**로 나눈다.
- 상품명 → 영문 DESCRIPTION 예시: 양말→`Socks`, 드로즈/팬티→`Men's underwear`, 베개→`Pillow`, 변기시트 커버→`Toilet seat cover`, 보호대→`Knee support`/`Wrist support`, 자켓→`Fleece jacket`, 볼캡→`Cap`. C열 폭이 좁으니 20자 이내로.
- ITEM NO.는 `S-QDE-1`, `S-QDE-2`… 순번.
- 그룹별 수량 = 해당 SKU 수량 합, 그룹별 CNY = 해당 SKU 금액(¥) 합.

### Step 4. USD 배분 (총액 고정, 단가 깔끔하게)
1. 그룹별 목표 USD = 그룹 CNY × (USD 총액 ÷ 전체 상품 CNY 합).
2. 각 그룹 단가 = 목표 USD ÷ 수량 → **소수점 3자리**로 반올림, 금액 = 수량 × 단가.
3. 마지막(가장 수량이 적은) 그룹으로 잔차를 흡수: 잔차 ÷ 수량이 3자리로 떨어지도록 다른 그룹 단가를 ±0.001~0.005 조정하며 탐색. 4자리까지는 허용, 그 이상은 그룹 구성 재조정.
4. 최종 검산: 모든 라인 `round(q*u,2) == amount`, `sum(amount) == USD 총액` (부동소수점 주의, round 사용).

### Step 5. 엑셀 작성
- row 13 스타일(font/alignment/border)을 `copy()`로 14~ 행에 복사.
- 숫자 셀은 실제 숫자로 쓰고 number_format: B=`#,##0`, D=`"$"#,##0.000`, E=`"$"#,##0.00`.
- 빈 품목 행(17~19 등)은 None.
- B20=총 PCS, E20=총액(숫자, `"$"#,##0.00`).
- 인쇄 한 페이지 맞춤: `ws.sheet_properties.pageSetUpPr=PageSetupProperties(fitToPage=True); ws.page_setup.fitToWidth=1; fitToHeight=1`.
- 파일명: `SQDE_<사업자>_<날짜>_인보이스_작성본.xlsx`.

### Step 6. 검증 및 전달
- `soffice --headless --convert-to pdf` → `pdftoppm -png` 1페이지 렌더해서 표가 잘리지 않는지, DESCRIPTION 넘침 없는지 눈으로 확인.
- SendUserFile로 xlsx 전달. 답변에 라인 표(수량/품목/단가/금액)와 CN인사이더 발주별 수량·¥ 합계, 그리고 "USD 총액은 인보이스 값에 맞춰 역산했다"는 점을 짧게 명시.

## 참고
- 통관용 정식 인보이스는 별도이며, 이 스킬은 은행 송금 제출용 PI만 다룬다.
- 사업자 예: 주식회사 클린인테크 (마인플로 상품이 클린인테크로 이관 중).