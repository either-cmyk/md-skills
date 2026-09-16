---
name: n-value-calculator
description: >
  CN인사이더 발주번호로부터 1위안당 원화(N값)를 계산하여 수입원가 구글시트의 지정된 행에 자동 입력하는 스킬.
  CN인사이더 발주 상세에서 위안화 비용을 수집하고, Gmail 전자세금계산서에서 팝빌 청구서/정산서 PDF를 추출하여
  관세·부가세·해상운임·DOC 등 통관 비용을 산출, N = M/C 공식으로 1위안당 통관 완료 원화를 계산한다.
  공식: M = (C+D)×P(환율) + SUM(E:L), N = M ÷ C.
  C = 상품금액 + 중중배송비 + 부가서비스(위안), D = 수수료(위안). 환율 P는 청구서의 '구매대행수수료 1%' 행 환율 사용.
  K(1% 수수료) = C × 0.01 × P 공식. 다중품목 발주는 상품금액 비율로 C/D 분배. 정산서가 한 줄로 합쳐진 경우 출고 PC 비율로 I/J 분배.
  CBM 비율로 F(해상운임)/G(DOC+원산지+통관) 분배. 1+1 번들은 세트 기준 Q 입력.
  반드시 이 스킬을 사용해야 하는 경우 "1위안당금액 계산해줘", "1위안당 금액 구해줘", "N값 계산", "원가 시트 입력",
  "수입원가 행 입력", "발주번호 N값", "청구서 정산서 계산", "원가 행 입력", "1위안당 시트 입력",
  "이 발주 원가", "S-QEC 원가 계산해줘 X행에 넣어줘", "발주번호 줄게 N값 구해줘",
  "1위안당원화 계산" 등 발주번호로 1위안당 금액을 산출하고 원가 시트 특정 행에 입력하는 모든 요청.
  사용자가 발주번호(S-Q로 시작)를 언급하면서 "X번줄에 넣어줘", "1위안당 구해줘", "N값" 등을 언급하면 이 스킬을 반드시 사용할 것.
---

# n-value-calculator 스킬

## 개요
CN인사이더 발주의 **1위안당 원화(N값)** 를 계산하여 수입원가 구글시트의 지정 행에 자동 입력하는 스킬.

**주 트리거 명령어: `1위안당금액 계산해줘`**

---

## 🔴 Step 0: 사용자 정보 확인 (세션당 1회 필수)

이 스킬을 호출하면 **가장 먼저** 현재 대화 세션에서 사용자 정보가 이미 확인되었는지 확인한다.

### Case A: 세션에서 처음 호출되는 경우
`AskUserQuestion` 도구로 다음 3가지를 한번에 물어본다:

**질문 1: 어떤 사업자의 시트에 입력할까요?**
- 이든코퍼레이션
- 이더컴퍼니
- 클린인테크
- 마인플로

**질문 2: Gmail 계정은 어떤걸 사용할까요?**
- kimhh0522@gmail.com (이든코퍼레이션)
- njcommerce2@gmail.com (이더컴퍼니)
- Other (직접 입력)

**질문 3: 팝빌 인증용 사업자번호는?**
- 578-85-02944 (이든코퍼레이션)
- Other (직접 입력)

받은 정보를 **세션 메모리(작업 노트)에 기록**하고 모든 후속 작업에 사용한다:
```
✅ 사업자: [받은값]
✅ Gmail: [받은값]
✅ 사업자번호: [받은값]
✅ 시트 ID: [매핑 또는 사용자 입력]
```

### Case B: 이미 받은 정보가 있는 경우
재질문 없이 그대로 사용. 한 줄로 확인만:
> "📌 [사업자명] 시트에 [Gmail]로 진행합니다."

사용자가 "다른 사업자", "이번엔 ○○사로" 등 명시적으로 변경 요청 시에만 다시 묻는다.

### 사업자별 매핑 (참고)

| 사업자 | Gmail | 사업자번호 | 시트 ID |
|--------|-------|----------|---------|
| 이든코퍼레이션 | kimhh0522@gmail.com | 578-85-02944 | 1X7UsQ5WFZmT1XiuVJwFVjZlb_mxb9AqNBaQIUkz9n44 |
| 이더컴퍼니 | njcommerce2@gmail.com | (사용자에게 받기) | (사용자에게 받기) |
| 클린인테크 | (사용자에게 받기) | (사용자에게 받기) | (사용자에게 받기) |
| 마인플로 | (사용자에게 받기) | (사용자에게 받기) | (사용자에게 받기) |

⚠️ 매핑되지 않은 항목은 Other 옵션으로 사용자에게 직접 받는다. 한번 받으면 세션 동안 재사용.

---

## 🎯 핵심 공식

```
M (총비용 KRW)   = (C + D) × P + SUM(E:L)
N (1위안당 원화) = M ÷ C
K (1% 수수료)    = C × 0.01 × P
```

- **C** = 상품 위안화 + 중중배송비 + 부가서비스 합 (CNY)
- **D** = 수수료 (CNY)
- **P** = 환율 (CNY → KRW, 청구서의 '구매대행수수료 1%' 행 환율)
- **E~L** = 모든 KRW 비용 합

⚠️ **P(환율) 누락 시 N값이 1/3 수준으로 잘못 계산됨. 반드시 입력 확인!**

---

## 📋 시트 컬럼 구조 (⚠️ G:H 셀 병합)

| 셀 | 항목 | 통화 | 출처 / 공식 |
|---|---|---|---|
| A | 발주번호 | - | S-QEC... 코드 |
| B | 품목 | - | 상품명 (한글: `="이름"` 수식 트릭) |
| C | 상품 위안화 + 중중배송비 + 부가서비스 합 | CNY | CN인사이더 발주 상세 |
| D | 수수료 | CNY | CN인사이더 발주 상세 |
| E | 현지반품관련비용 | KRW | 보통 빈칸 |
| F | 중한배송비 (해상운임) | KRW | 청구서 PDF (CBM × 단가) |
| **G:H (병합)** | DOF + 원산지 + 통관수수료 | KRW | 청구서 PDF (VAT 포함, CBM 비율) |
| I | 관세 | KRW | 정산서 PDF |
| J | 부가세 | KRW | 정산서 PDF |
| **K** | **1% 수수료** | KRW | **`=C*0.01*P`** ← 수식 입력 |
| L | 한한배송비 | KRW | 보통 빈칸 |
| M | 총비용 | KRW | `=(C+D)*P+SUM(E:L)` |
| N | **1위안당 금액 ★** | KRW/CNY | `=M/C` |
| O | CBM | - | 발주별 CBM |
| P | **환율** ⚠️ | - | 청구서 환율 (필수 입력) |
| Q | 박스당 입수량 | PC/세트 | CN인사이더 출고내역 |

⚠️ **G:H는 셀 병합**이라 Tab 시 H를 건너뜀. G에만 값 입력.

---

## 🔄 작업 흐름 (Step 0 완료 후)

### Step 1: CN인사이더 발주 상세 조회 (C, D, 품목명)
1. https://www.cninsider.co.kr/mall/#/orderList 진입
2. 발주번호 검색 → "상세보기" 클릭
3. 결제정보 섹션에서 추출:
   - 상품총금액 (¥)
   - 물류비 (¥) (중중배송비)
   - 부가서비스 (¥)
   - 수수료 (¥)
4. **C = 상품총금액 + 물류비 + 부가서비스**
5. **D = 수수료**

검증: C + D ≈ CN인사이더 총금액 (위안)

### Step 2: CN인사이더 CN출고 → BL번호, CBM 확인
1. https://www.cninsider.co.kr/mall/#/invoiceList 진입
2. 발주번호로 검색 → 출고송장번호와 박스 패킹 정보 확인
3. **해당 발주의 CBM** 기록 (다중 SKU면 SKU별 CBM 합)
4. **BL 총 CBM** 기록 (비율 계산용)

### Step 3: Gmail에서 팝빌 청구서/정산서 진입
1. Gmail (Step 0에서 받은 계정)에서 "전자세금계산서" 검색
2. 해당 BL과 일치하는 메일 (출고일 기준 4~5일 후 발행) 선택
3. 본문 팝빌 링크 클릭 → 팝빌 페이지 진입
4. 사업자번호 입력란에 **Step 0에서 받은 사업자번호** 입력 → 확인
5. 첨부파일 PDF 확인:
   - INVOICE PDF (보통 미사용)
   - 청구서 PDF (F, G, P 추출)
   - 정산서(수입신고필증) PDF (I, J 추출)

### Step 4: 청구서 PDF에서 F, G, P 추출
청구서 운임내역 표에서:
- **P (환율)** = '구매대행수수료 1%' 행의 환율 (예: 216.84)
- **F (중한배송비)** = 해상운임 단가 × 해당 발주 CBM
  - 예: 96,000 KRW/CBM × 0.90 CBM = ₩86,400
- **G (DOF+원산지+통관)** = (DOC 25,000 + VAT) + 원산지 35,000 + (통관 30,000 + VAT) 합산 후 × (발주 CBM / BL 총 CBM)
  - 예: 130,500 × (0.90/21.90) = ₩5,363

### Step 5: 정산서 PDF에서 I, J 추출
해당 상품의 거래품명 라인(란번호/총란수)에서:
- **I (관세)** = 세액(관) 값. 면세품(FCN1중가 0%)은 0
- **J (부가세)** = 세액(부) 값 (보통 10% × CIF)

### Step 6: K, M, N, P 수식 입력
- **K (1% 수수료)**: `=C{행}*0.01*P{행}` ← 수식으로 입력 (자동 계산)
- **M (총비용)**: `=(C{행}+D{행})*P{행}+SUM(E{행}:L{행})`
- **N (1위안당)**: `=M{행}/C{행}`
- **P (환율)**: 청구서에서 받은 환율 직접 입력

### Step 7: 시트 입력 순서
Step 0에서 확정된 시트 ID로 진입.
1. A, B, C, D 입력 (CNY 부분)
2. E 건너뛰기 (빈칸)
3. F, G (G:H 병합) 입력 (Tab으로 이동 시 H 자동 건너뜀)
4. I, J 입력 (관세/부가세)
5. K, M, N 수식 입력
6. P 환율 입력 (⚠️ 필수)
7. O (CBM) 입력

### Step 8: 결과 보고
```
📦 [품목명] (발주번호 [S-QEC...]) → [시트] [N]행 입력 완료

C: ¥[금액]   D: ¥[금액]   P: [환율]
F: ₩[금액] (해상운임)
G: ₩[금액] (DOC+원산지+통관)
I: ₩[금액] (관세)
J: ₩[금액] (부가세)
K: ₩[금액] (1% 수수료) ← C × 0.01 × P
M (총비용): ₩[금액]
N (1위안당 금액): ₩[N값] ★
```

---

## ⚠️ 특수 케이스 처리

| 케이스 | 처리 방법 |
|---|---|
| **다중품목 발주** (12개입+20개입 등) | C, D를 상품금액 CNY 비율로 분배. K는 C × 0.01 × P 자동 계산 |
| **정산서 한 줄 합산** (같은 세번부호로 묶임) | I, J를 출고 PC 비율로 분배 |
| **혼적 BL** (여러 발주가 같은 BL) | 각 발주 CBM 비율로 F, G 분배 / I, J는 정산서 라인 값 사용 |
| **다중 컨테이너 분할 출고** | 각 컨테이너 KRW 합산 |
| **1+1 번들 상품** | N 동일, 원가위안만 ×2, Q는 세트 단위 |
| **발주 ≠ 출고 수량** | C/D: 발주 기준, I/J: 출고 PC 비율 |
| **면세 상품** (FCN1중가 0%) | I = 0 |

---

## ✅ 검증 체크리스트

1. C + D ≈ CN인사이더 총금액 (위안)
2. **P (환율) 입력 확인** ← 가장 중요
3. K 수식이 `=C*0.01*P` 인가
4. M 수식이 `=(C+D)*P+SUM(E:L)` 인가
5. N 수식이 `=M/C` 인가 (절대참조 함정 X)
6. **N 값 정상 범위 검증**:
   - 단가 ¥0.32 저단가 (수세미 등) → N=320~360 정상
   - 단가 ¥5+ (캐리어 등) → N=260~290 정상
   - **N < 250 또는 N > 400** → 입력값 재검증 (P 확인 1순위)

---

## 🛠️ 기술 환경 설정

### 팝빌 인증 (React Controlled Input)
팝빌 사업자번호 입력은 React onChange 핸들러를 통해 트리거해야 함:

```javascript
const inp = document.querySelectorAll('input')[0];
const propsKey = Object.keys(inp).find(k => k.startsWith('__reactProps'));
const props = inp[propsKey];
const setValue = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
setValue.call(inp, '사업자번호');
props.onChange({target: inp, currentTarget: inp});

// 확인 버튼 클릭 (onClickCapture로)
const spans = document.querySelectorAll('span');
let confirmBtn = null;
spans.forEach(s => { if (s.textContent.trim() === '확인' && s.children.length === 0) confirmBtn = s.parentElement; });
confirmBtn[Object.keys(confirmBtn).find(k => k.startsWith('__reactProps'))]
  .onClickCapture({preventDefault: () => {}, stopPropagation: () => {}, target: confirmBtn});
```

JS 자동 인증 실패 시 사용자에게 직접 사업자번호 입력 + 확인 클릭을 요청.

### 팝빌 PDF 추출 (auth token 캡처)
```javascript
// 1. fetch 인터셉터 설치
window.__authToken = null;
const origFetch = window.fetch;
window.fetch = function(...args) {
  const opts = args[1] || {};
  if (opts.headers?.Authorization) window.__authToken = opts.headers.Authorization;
  return origFetch.apply(this, args);
};

// 2. PDF 버튼 클릭하여 토큰 캡처 (보통 인덱스 2 클릭)
const pdfBtns = [...document.querySelectorAll('button')].filter(b => b.textContent.trim().endsWith('.pdf'));
pdfBtns[2].click();
// 토큰 확인: window.__authToken.length (보통 ~640자)

// 3. 모든 인덱스 시도 (0~5)
// 실제 PDF는 보통 인덱스 2~4에 있음 (0, 1, 5는 JSON 에러)
const url = `https://www.popbill.com/__API_V1__/Taxinvoice/AttachedFile/${docId}/${idx}?`;
const r = await fetch(url, {method:'GET', headers:{
  'Authorization': window.__authToken,
  'Accept-Language': 'ko',
  'X-LH-Referrer': `Taxinvoice/${docId}.E`
}});
const ab = await r.arrayBuffer();
```

⚠️ Auth token이 JSON serialize 시 잘릴 수 있음. 전체 길이 확인 후 사용.

### pdf.js로 PDF 텍스트 추출
```javascript
if (!window.pdfjsLib) {
  const script = document.createElement('script');
  script.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
  document.head.appendChild(script);
  await new Promise(r => script.onload = r);
  window.pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
}

const pdf = await pdfjsLib.getDocument({data: arrayBuffer}).promise;
let text = '';
for (let p = 1; p <= pdf.numPages; p++) {
  const page = await pdf.getPage(p);
  const content = await page.getTextContent();
  text += content.items.map(it => it.str).join(' ') + '\n';
}
```

### 시트 입력 (Name Box 네비게이션)
```javascript
const nb = document.querySelector('input.waffle-name-box');
nb.focus();
const setValue = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
setValue.call(nb, 'A80'); // 목표 셀
nb.dispatchEvent(new Event('input', {bubbles: true}));
nb.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true, keyCode: 13, which: 13}));
```

⚠️ Name Box 네비게이션 후 셀 포커스가 안 옮겨가는 경우, 사용자에게 클립보드 paste 방식으로 데이터 입력 요청:
- 한 줄 탭 구분 데이터를 clipboard.writeText()로 복사
- 사용자가 A행 클릭 후 Ctrl+V로 한번에 입력

### 한글 IME 회피
B열 품목명 한글 입력 시 첫 글자 누락 방지: `="품목명"` 수식 트릭 사용.

### G:H 병합 컬럼 처리
- G:H는 시트에서 셀 병합 상태
- 값 입력 시 G에만 입력 (Tab으로 G에서 다음 입력 시 H를 건너뛰고 I로 이동)
- Tab 순서: F → G(:H 자동 건너뜀) → I → J → K

---

## 📚 작업 예시 (실측)

**입력**: 발주번호 `S-QEC260414` (캐리어 커버), 시트 행

### Step 0: 사용자 정보 (세션 첫 호출)
AskUserQuestion으로 받은 응답:
- 사업자: 이든코퍼레이션
- Gmail: kimhh0522@gmail.com
- 사업자번호: 578-85-02944
- 시트 ID: 1X7UsQ5WFZmT1XiuVJwFVjZlb_mxb9AqNBaQIUkz9n44

### Step 1: CN인사이더 발주 상세
- 상품총금액: ¥8,052.20
- 물류비: ¥0
- 부가서비스: ¥552.00
- 수수료: ¥563.66
- **C = 8,604.20 / D = 563.66**

### Step 2: CN출고 → BL/CBM
- BL: CNIS260419C04, 발주 CBM 0.90 / BL 총 CBM 21.90 (15박스)

### Step 3-4: 청구서 PDF
- 환율 **P = 216.84**
- 해상운임 단가 96,000 KRW/CBM
- DOC 25,000 + VAT + 원산지 70,000 + 통관 30,000 + VAT = 130,500
- **F = 0.90 × 96,000 = ₩86,400**
- **G = 130,500 × (0.90/21.90) = ₩5,363**

### Step 5: 정산서 PDF (TRUNK COVER 란 002/004)
- CIF: ₩2,229,927, 관세율 1.30%, 부가세율 10%
- **I = ₩28,989 / J = ₩225,891**

### Step 6: K, M, N 수식
- **K = `=C*0.01*P`** = 8,604.20 × 0.01 × 216.84 = ₩18,657
- M = `=(C+D)*P+SUM(E:L)` = ₩2,353,259
- **N = `=M/C`** = ₩273.50 ★

---

## 📝 호출 명령어

**주 트리거**: `1위안당금액 계산해줘`

기타 트리거:
- "발주번호 [S-QEC...] 1위안당 계산해줘 [N]번에 입력해줘"
- "N값 계산해줘"
- "[S-QEC...] 원가 계산"
- "1위안당 원화 구해줘"
- "이 발주 N값 구해줘"
