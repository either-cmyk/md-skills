---
name: bigcell-daily-update
description: 빅셀(BigCell) 로켓그로스 매출분석 엑셀 다운로드 → 반품 제거 → 시트 헤더 이름기준 컬럼 매핑 → 구글시트 판매 Data append → 그로스 재고 DB 날짜 컬럼 삽입(Standalone API)까지의 일일 데이터 업데이트 완전 자동화 스킬. 반드시 이 스킬을 사용해야 하는 경우 "빅셀 업데이트", "빅셀 일일", "매출분석 업데이트", "그로스 시트 업데이트", "빅셀 데이터 넣어줘", "이더컴퍼니 업데이트", "뉴트리정 업데이트", "클린인 업데이트", "마인플로 업데이트", "이든코퍼레이션 업데이트" 등 빅셀 매출 데이터를 구글시트에 반영하는 모든 요청. 사용자가 "빅셀"이나 회사명 + "업데이트/시트/데이터" 키워드를 언급하면 이 스킬을 사용할 것.
---

# 빅셀 일일 업데이트 스킬 (v2.4.2 - 2026-08-24 검증 기준 보정 + 재기록 경계 확인 규칙)

빅셀(app.bigcell.co.kr) 로켓그로스 매출분석 데이터를 다운로드하여 가공 후 구글시트에 입력하는 일일 업무를 완전 자동화한다.

## 핵심 방법론

1. 빅셀에서 Blob intercept + SheetJS로 엑셀 파싱 + 반품 필터링 + **시트 헤더 이름기준 컬럼 매핑(45필드)**
2. gviz로 **D열과 F열 모두** 조회하여 안전한 startRow 확인 (max + 1)
3. doPost로 판매 Data 탭에 데이터 전송 (회사별 Apps Script URL, YYYY. M. D 날짜 포맷)
4. **Standalone Apps Script API**로 그로스 재고 DB 자동 업데이트 (컬럼 삽입 + 수식 채우기 + 값 변환 + 검증)

5. **(이더컴퍼니 전용) 갱신 완료 후 일일 판매 비교 보고서(HTML) 자동 생성** — 전일 대비 + 전략 코멘트 포함 (5단계)

1~3단계는 브라우저 메모리에서, 4단계는 서버사이드 Apps Script에서 처리. 5단계는 gviz 집계 후 로컬 HTML 생성.

**목표 소요 시간: 사업자당 15분 이내** (누적 피로 관리 목적)

## startRow 필수 규칙 (절대 변경 금지)

**D열과 F열을 모두 조회하여 max(D행수, F행수) + 1을 startRow로 사용한다.**

사업자에 따라 D열(날짜)에 빈 행이 많을 수 있다 (예: 뉴트리정 D=196행 vs F=291행).
반대로 F열이 더 적을 수도 있다. 어느 한쪽만 보면 기존 데이터를 덮어쓴다.

**실제 사고 사례:**
- D열 10,534행 vs F열 2,083행: F열 기준 시 4/2 데이터가 덮어써져 버전 히스토리 복원
- 뉴트리정 D열 196행 vs F열 291행: D열 기준 시 startRow=197로 계산돼 기존 데이터 영역에 덮어쓰기 발생

## 날짜 범위 규칙 (KST 전날 하루치만)

기본 대상 날짜는 **서울(KST) 기준 현재일 - 1일** 하루치만 처리한다. 예: KST 4/24 실행 → 4/23만 갱신.

- 시트 중간에 빠진 날짜가 보여도 사용자 명시 요청 없으면 건드리지 않는다
- 과거 누락일을 임의로 채우면 발주/재고 계산과 어긋남
- 범위 다운로드(여러 날 합쳐서)는 사용자가 명시 요청할 때만

## 회사별 설정 (5개 사업자, 2026-04-15 전체 통일 완료)

회사명을 지정하지 않으면 반드시 물어볼 것.

| 회사 | 빅셀 계정 | 시트 ID |
|------|-----------|---------|
| 이더컴퍼니 | 이더컴퍼니 | `1pfikkAKbYOtgxIjFZYtwa1G4CIQLnMcbw2OaZTiWUuU` |
| 뉴트리정 | 뉴트리정 | `1Fai97aHOhzY5lPBpQBo8d1ji32oaaX5q6_3TgQKHWzE` |
| 마인플로 | 마인플로 | `12eHkB_6cGvEM5EYfDontmxEM1WgIsBSDPVHNRTsWeII` |
| 클린인테크 | 클린인테크 | `1AVPuPo7rkT-K923BOl2vFe5aKAHJE7bUNZM0kQ0w_PE` |
| 이든코퍼레이션 | 이든코퍼레이션 | `1ow9OBUrjJYjtuANyGBRCCEqkktfUwwKVk8oyv6oypbY` |

### 판매 Data doPost (5개 사업자 공용, hg.kim 배포)

- **URL**: `https://script.google.com/macros/s/AKfycbxZ6SCV0k98aVdqfg5t11KlTAt2JPSM-PDqKp94x0oEIXQllumH3OEqAjDEG5x7FQLs/exec`
- 이 URL 하나로 5개 사업자 모두 처리. payload에 **`sheetId` 파라미터로 대상 구분** (그로스 API와 동일 방식).
- 실행 계정 = hg.kim@either.co.kr (워크스페이스, 익명 액세스 허용됨). openById(sheetId)로 각 시트의 '판매 Data' 탭 F열부터 기록 + D열 날짜.

- 판매 Data gid (모든 사업자): `1453058054`
- Apps Script URL 형식: `https://script.google.com/macros/s/<ID>/exec`
- 모든 사업자 공통 날짜 포맷: `YYYY. M. D` (공백 있음, 월/일 앞자리 0 없음)

### 그로스 재고 DB Standalone Apps Script (5개 사업자 공용)

- **URL**: `https://script.google.com/macros/s/AKfycby2JKRW6hBypZve_E8O6HbmXP5o8crRfwGvGGeNNVmuJqoE8vtDYyRrmQCzjYEcwBOM/exec`
- **프로젝트**: `https://script.google.com/home/projects/1k16QVe1DpF-GU1t9UwcXDHalRs5Xdzbu5Imf1PUNpLzwTnGvQCZC36zJ/edit`
- 이 URL 하나로 5개 사업자 모두의 그로스 재고 DB 업데이트. `sheetId` 파라미터로 대상 구분
- 타 PC에서 재배포 시 이 스킬의 `bigcell-apps-script.gs` 파일을 Standalone 프로젝트로 deploy 하면 동일 동작

### ARRAYFORMULA 구조 (모든 사업자 공통, 고정)

수식은 모든 사업자에서 동일한 고정 템플릿을 사용한다. 직전 컬럼 수식을 복사하지 않고, 아래 템플릿에서 컬럼 레터와 행번호만 자동 생성한다.

```
=ARRAYFORMULA(INDEX('판매 Data'!$AE$1:$AE$63111, MATCH(1, ('판매 Data'!$J$1:$J$63111=$E{row})*('판매 Data'!$D$1:$D$63111={colLetter}$2), 0)))
```

- `{row}`: 데이터행 번호 (3부터 시작, copyTo로 자동 조정)
- `{colLetter}`: 새로 삽입된 컬럼의 레터 (예: AN, AP 등)
- `판매 Data J열` = `그로스 재고 DB E열` (옵션 ID로 상품 매칭)
- `판매 Data D열` = `그로스 재고 DB 날짜 헤더 {colLetter}$2` (날짜 매칭)
- `판매 Data AE열` = 반환값 (판매 수량)
- 유한범위 `$AE$1:$AE$63111` 사용 (무한범위 `$AE:$AE` 금지 — 2026-04-15 통일 완료)

### 한글 시트명 유니코드 이스케이프 필수 (Apps Script)

Apps Script V8 런타임은 소스 파일 한글을 UTF-8 → Latin-1로 잘못 재해석하는 버그가 있다. `.gs` 소스에 `"판매 Data"` 리터럴을 넣으면 배포 후 `"íë§¤ Data"` 같은 깨진 문자열로 실행된다.

**해결**: 시트명을 반드시 유니코드 이스케이프로 작성.

```javascript
var SHEET_NAME = "\uD310\uB9E4 Data";  // = "판매 Data"
```

본 스킬의 `bigcell-apps-script.gs` 파일은 이미 이스케이프 처리되어 있다.

## 실전 운용 노하우 (2026-05 통합)

수십 일 운용하면서 굳어진 패턴. 이걸 따르면 사업자당 5~15분 안에 끝낸다.

### 0-A. 빅셀 사업자 계정 전환 트릭

빅셀 우측 상단 드롭다운으로 일일이 전환하지 말고 — **`https://app.bigcell.co.kr/mypage/members` 로 navigate 하면 해당 사업자가 멤버로 등록돼 있을 경우 자동 전환된다.** 그 후 다시 매출분석 URL로 navigate.

```
1. navigate(빅셀탭, https://app.bigcell.co.kr/mypage/members)
2. screenshot으로 우측 상단 사업자명 확인 (예: "eithercompany님" / "nutrijung님")
3. navigate(빅셀탭, https://app.bigcell.co.kr/v2/statistics/coupang?q_sale_date_from=YYYY/MM/DD&...)
```

### 0-B. 다운로드 클릭 재시도 패턴

빅셀 페이지 로딩 직후 첫 다운로드 클릭은 종종 실패한다 (blob 미캡처). 원인은 보통:
1. "Claude is active in this tab group" 알림이 다운로드 버튼을 가림 — 좌표 `(905, 671)` 또는 `(905, 719)` 클릭으로 닫기
2. SheetJS 로드 타이밍

**표준 시퀀스 (browser_batch 한 번에)**:
```
1. rehook (window.__downloadBlob = null + URL.createObjectURL 오버라이드)
2. left_click(905, 671)         # 알림 닫기
3. wait(1)
4. left_click(다운로드 ref)      # 첫 시도
5. wait(5)
6. left_click(다운로드 ref)      # 두 번째 시도 (보험)
7. wait(8)
8. javascript: blob 상태 확인
```

blob 없으면 → 알림 다시 닫고 한 번 더 클릭. 보통 3회 안에 캡처됨. 캡처 사이즈가 `~40KB` (뉴트리정) / `~700KB` (이더컴퍼니/마인플로) 정도면 정상.

### 0-C. gviz 캐시 우회

`docs.google.com/spreadsheets/.../gviz/tq?...` 는 강력한 응답 캐시가 있다. doPost 직후 행수 변화 확인 시 캐시된 옛값이 반환될 수 있음.

**해결**: URL에 `&_t=Date.now()` 같은 dummy 파라미터를 붙여 캐시 우회.

```javascript
var t = Date.now();
var url = 'https://docs.google.com/spreadsheets/d/'+sid+'/gviz/tq?tqx=out:csv&gid='+gid+'&tq=SELECT+F+WHERE+F+is+not+null&range=F1:F70000&_t='+t;
```

### 0-D. Chrome 탭 freeze + 새 탭 우회

Apps Script 호출(45초 타임아웃) 후에는 해당 탭의 V8 컨텍스트가 한동안 unresponsive 상태가 된다. CDP `Runtime.evaluate timed out` 반복 발생.

**해결**: 그 시점에 새 탭을 만들고 `https://docs.google.com/` 같은 가벼운 페이지로 navigate해서 gviz 검증을 이어간다. freeze된 탭은 1~2분 후 자연 회복.

```
1. tabs_create_mcp()       # 새 탭 생성
2. navigate(새탭, https://docs.google.com/)
3. wait(3~5)
4. 새 탭에서 gviz fetch 또는 Standalone API 재호출
```

### 0-E. Standalone API 타임아웃 대응 (핵심)

이더컴퍼니/마인플로처럼 시트 행 수가 1만 행 넘는 사업자는 그로스 재고 DB Standalone API가 30~60초 걸린다 → 클라이언트는 항상 45초 타임아웃.

**그러나 서버는 계속 실행 중**. 30~45초 대기 후 동일 payload로 재호출하면:
- `{"status":"skip", "message":"이미 동일 날짜 컬럼 존재", "latestStr":"2026. 5. 19", ...}` → 첫 호출이 정상 완료된 것
- gviz로 F열 행 수가 목표치(`기존 F + filtered.length`)에 도달했는지로도 확인 가능

**doPost도 동일 패턴이 적용된다.** 이더컴퍼니 1279행 doPost는 60~90초 걸리고, 서버에서 단계적으로 행을 채워나간다 (예: F열이 +400씩 증가하는 게 보임).

### 0-F. 사업자별 그로스 재고 DB 신규 컬럼 위치

Standalone API 응답의 `newLetter` 는 사업자/시점마다 다르다. 응답을 그대로 보고하면 됨.

| 사업자 | 2026-05 시점 newLetter |
|--------|------------------------|
| 이더컴퍼니 | `AQ` |
| 뉴트리정 | `AO` |
| 마인플로 | `AQ` (추정) |
| 클린인테크 | `AQ` (추정) |
| 이든코퍼레이션 | `AQ` (추정) |

이 값들은 단순 참고용. 실제로는 API 응답 그대로 사용.

### 0-G. 시트 사용자 임의 정리 대응

사용자가 그로스 DB 또는 판매 Data를 임의로 정리(데이터 삭제)했을 수 있다. **항상 gviz로 D/F 현재 행수를 다시 확인하고 startRow를 재계산**한다. 메모리/이전 응답에 박힌 startRow를 재사용하면 데이터 어긋남.

```
판매 Data가 갑자기 줄었다 = 사용자가 정리한 것. 그대로 새 startRow에 이어붙이면 됨.
```

### 0-H. 이더컴퍼니 그로스 DB 1055행 경계

이더컴퍼니 그로스 재고 DB의 **1055행 아래는 스마트스토어 영역**. 빅셀 자동화 수식이 들어가면 안 됨 (스마트스토어는 별도 매핑 체계). Standalone API가 lastRow까지 채우는 상황이면 나중에 1055행 이하 수식을 별도로 클리어할 필요.

### 0-I. 뉴트리정 클린인테크 빅셀 D열 포맷 변형

기본 포맷은 `YYYY. M. D` (공백 있음, 예: `2026. 5. 19`). 사용자가 시트 정리하면서 `2026.5.19` (공백 없음)로 바꿔 놓는 경우 있음. 그로스 재고 DB 헤더와 매칭되려면 둘 다 같은 포맷이어야 하므로, 둘이 어긋나 있으면 새 데이터는 그로스 DB가 사용하는 헤더 포맷에 맞춰서 보낸다.


### 0-J. 재고 필드 전부 0이면 전송 전 재다운로드 (2026-07-03 실증)

다운로드본의 재고 관련 필드(쿠팡재고, 재고금액, 재고합계, 최근7일평균, 쿠팡보관비)가 **전부 0/빈값**이면 빅셀 쿠팡재고 동기화 지연이다. 판매수량은 정상이라 AE_filled 검증만으로는 못 잡는다.

- **파싱 직후 판매수량뿐 아니라 쿠팡재고(r[19]) 비영 개수도 검증**하고, 전부 0이면 전송하지 말고 빅셀 새로고침 후 재다운로드
- 이미 전송했으면: 재다운로드 후 **동일 startRow에 동일 청크로 덮어쓰기** (행수 같은지 먼저 확인). 그로스 재고 DB는 판매수량/옵션ID/날짜만 쓰므로 영향 없고 자동 재계산됨
- 시트에 0이 박히면 재고금액/재고합계가 날짜서식으로 "99/12/30"처럼 보일 수 있음 — 값은 정상, 서식만 숫자(자동)로 복구하면 됨

### 0-K. 판매 Data 행 부족 대응 (사용자 정리 후, 2026-07-15)

사용자가 판매 Data의 과거 데이터를 **행 삭제**로 정리하면 시트 총 행 수가 줄어든다. 기존 수식은 범위가 자동 축소돼 무사하지만:

- **총 행 수 < 63,111이면** 다음 갱신에서 (1) doPost가 범위 밖 행에 쓰기 실패 가능, (2) 새로 삽입되는 그로스 수식이 고정 범위 템플릿이라 #REF
- **갱신 전 gviz range probe로 총 행 수 확인** (예: `range=A63111:A63111` 이 invalid_range면 부족): 부족하면 행 범위 선택 → "아래에 N개 행 삽입" 반복으로 63,111행 이상 확보 (구조 변경이라 사용자 확인 필요할 수 있음)
- 데이터는 3행부터 연속 유지, 최신 날짜(살아있는 수식이 참조)는 남겨두고 지우도록 안내


### 0-M. 빅셀 엑셀 컬럼 2026-08 재변경 + 파싱 무결성 검증 필수 (2026-08-24)

빅셀 다운로드 엑셀 헤더가 또 변경됨 (2026-08 확인). 고정 인덱스 방식은 즉시 깨진다:

- `운영상태`, `자체상품코드` 신규 (옵션명 뒤), `본사발주검토금액`·`본사입고예정금액` 신규
- 헤더 공백 제거: `본사 발주검토`→`본사발주검토` 등 (norm 함수의 공백 제거로 흡수됨)
- 이름 변경: `품절예상일`→`쿠팡품절예상일` (부분매칭 폴백으로 흡수됨)
- 순서 변경: 쿠팡품절예상일이 재고금액 뒤로 이동

**사고 사례 (뉴트리정 2026-08-18~20)**: 구식 매핑으로 3일치가 컬럼 밀림 — 상품명 자리에 옵션ID, 판매수량 자리에 매출값(행당 수만~수십만), 매출·재고 공란. 그로스 재고 DB 해당 날짜 컬럼까지 0으로 값 고정됨 → 판매 Data 재기록 + 그로스 컬럼 삭제·재삽입으로 복구.

**의무 검증 (파싱 직후, 전송 전):**
1. `AE_sum`(판매수량 합)이 평소 범위인지 — 행당 평균이 수백 이상이면 컬럼 밀림
2. **상품명 필드가 정상 텍스트인 행 수 = 전체 행 수** (숫자만 있으면 옵션ID가 밀려 들어온 것. 브랜드명 포함 여부로 확인해도 좋음)
3. SKU ID 채움 행 수 — 단, **사업자별 정상 기준이 다름**: 클린인테크는 SKU 빈 옵션이 원래 140개(343행 중 203만 채움)라 "채움수=행수" 기준은 오탐. 이 검증은 **기존 정상 날짜의 채움수와 대조**하거나 상품명 검증으로 대체
4. 쿠팡재고 비영 개수 (0-J)

**사업자별 일일 행수 (2026-08 기준, 반품 제외):** 이더컴퍼니 1,020 / 클린인테크 343 / 마인플로 268 / 뉴트리정 166 / 이든코퍼레이션 153. 파싱 count가 이 값과 크게 다르면 상품 추가/삭제 여부 확인.

하나라도 실패하면 전송 금지, 헤더 구조 확인 후 이름기준 매핑 재점검.

### 0-N. 과거 날짜 재기록 시 경계는 range probe로 실측 (2026-08-24 이든 사고)

밀린 날짜를 덮어쓸 때 시작 행을 `COUNT(F) WHERE D <= 직전날짜` 계산으로 잡으면 **1행 어긋날 수 있다** (이든 실사례: 계산상 8/19 시작=20628인데 실제는 20627 → 옛 밀린 행 1개가 잔존해 8/19가 154행/합 2,168로 부풀려짐).

- 재기록 전 반드시 `range=D{계산행-3}:D{계산행+3}` 으로 **날짜 경계를 눈으로 확인**하고 실제 첫 행에 맞춰 덮어쓸 것
- 재기록 후 `COUNT(F) WHERE D = 대상날짜` 가 정확히 일일 행수와 일치하는지 검증. 초과하면 잔존 행 존재 → 위치 특정 후 사용자에게 행 삭제 요청 (구조 변경이라 자동 삭제 금지)

### 0-L. 그로스 API 타임아웃 후 재호출 전 gviz 헤더 확인 (중복 컬럼 방지, 2026-07-14 사고)

0-E의 "타임아웃 → 동일 payload 재호출" 패턴에서, **첫 호출이 날짜 헤더를 쓰기 전에 재호출이 도착하면 중복 방지가 작동하지 않아 빈 컬럼이 여분으로 삽입**될 수 있다 (이더 7/13 실사례: 빈 컬럼 + 정상 컬럼 동시 존재).

- 타임아웃 발생 시 **재호출 대신 60~90초 대기 후 gviz로 그로스 DB 헤더(row 2)와 비영값부터 확인**: 새 날짜가 이미 있으면 완료된 것 — 재호출 금지
- 헤더가 아직 없을 때만 재호출
- 이미 빈 중복 컬럼이 생겼으면: 값·헤더 전무한지 확인 후 deleteCol 롤백 (구조 변경이므로 사용자 확인 필수)

---

## 1단계: 빅셀 Blob intercept + 엑셀 파싱 + 자체상품코드 제거

### 1-1. 빅셀 접속 + 로그인

1. `app.bigcell.co.kr` 접속, 해당 회사 계정으로 로그인 (또는 0-A 트릭으로 계정 자동 전환)
2. 좌측 메뉴 **로켓그로스 > 매출 분석** 이동
3. 날짜를 대상 날짜로 설정 (기본: KST 어제)

또는 URL 직접 이동:
```
https://app.bigcell.co.kr/v2/statistics/coupang?q_sale_date_from=YYYY/MM/DD&q_sale_date_to=YYYY/MM/DD&q_product_types=RFM&q_show_type=detail
```

### 1-2. Blob intercept 주입

빅셀 엑셀은 서버 다운로드가 아니라 클라이언트 Blob 생성이다. URL.createObjectURL을 오버라이드한다:

```javascript
var origCreateObjectURL = URL.createObjectURL;
window.__downloadBlob = null;
URL.createObjectURL = function(blob) {
  window.__downloadBlob = blob;
  window.__downloadBlobSize = blob.size;
  window.__downloadBlobType = blob.type;
  return origCreateObjectURL.call(URL, blob);
};
```

### 1-3. SheetJS 로드

```javascript
var s = document.createElement('script');
s.src = 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js';
s.onload = function(){ window.__xlsxLoaded = true; };
document.head.appendChild(s);
```

### 1-4. "엑셀 다운로드" 버튼 클릭

우측 상단의 다운로드 버튼을 클릭하면 `window.__downloadBlob`에 Blob이 캡처된다.

### 1-5. Blob 파싱 + 반품 필터링 + **이름기준 컬럼 매핑(45필드)**

**2026-04-22부터 BigCell export에 col 6=자체상품코드가 추가됨.** 판매 Data로 보내기 전 반드시 제거해야 기존 시트 구조(L=판매가)와 일치한다.

BigCell 엑셀 컬럼 구조 (2026-04-22~):
| col | 내용 | 시트 매핑 |
|-----|------|----------|
| 0 | 스토어명 | F |
| 1 | 노출상품ID | G |
| 2 | 상품명 | H |
| 3 | SKU ID | I |
| 4 | 옵션ID | J |
| 5 | 옵션명 | K |
| **6** | **자체상품코드** | **❌ 제거 필수** |
| 7 | 판매가 | L |
| 8 | 원가 | M |
| ... | ... | ... |

```javascript
(async function(){
  // ★ 이름기준 매핑: 빅셀 엑셀이 컬럼을 추가/재배치해도 시트 헤더 필드명 순서로 재정렬.
  //   slice 고정제거(옛 방식)는 빅셀 컬럼 변동 시 판매수량/재고가 밀려 들어가므로 금지.
  //   판매 Data 시트 헤더 F~AX = 45필드(아래 순서). N번째 동일이름 매칭 + 품절예상일 부분매칭.
  var sheetFields = ["스토어명","노출상품ID","상품명","SKU ID","옵션ID","옵션명","판매가","원가","수입단가","이익금","고객반품(최근30일)","반품률","최근7일 일일 평균판매량","본사 발주검토","본사 입고예정","본사 입고예정일","본사재고","쿠팡 입고예정","쿠팡 입고예정 원가","쿠팡재고","재고금액","재고합계","쿠팡입고필요수량","품절예상일","쿠팡보관비(이번달)","판매수량","판매수량 원가","광고 판매수량","광고 판매수량 비율","자연 판매수량","자연 판매수량 비율","할인전매출","매출","이익금","순이익금","순이익금 비율","광고집행비","광고집행비 비율","광고매출","광고매출 비율","광고판매전환율","광고 ROAS","광고집행 이익금","광고집행 순이익금","광고집행 순이익율"];
  function norm(x){ return String(x||'').replace(/\s+/g,'').replace(/[()]/g,'').trim(); }
  var blob = window.__downloadBlob;
  var buf = await blob.arrayBuffer();
  var wb = XLSX.read(buf, {type:'array'});
  var ws = wb.Sheets[wb.SheetNames[0]];
  var allRows = XLSX.utils.sheet_to_json(ws, {header:1, defval:''});
  var bh = allRows[0].map(norm);
  var usedCount = {};
  function findIdx(sfRaw){
    var sf = norm(sfRaw), occ = usedCount[sf]||0, seen = 0;
    for(var i=0;i<bh.length;i++){ if(bh[i]===sf){ if(seen===occ){ usedCount[sf]=occ+1; return i; } seen++; } }
    for(var i=0;i<bh.length;i++){ if(bh[i] && (bh[i].indexOf(sf)>=0 || sf.indexOf(bh[i])>=0)) return i; } // 품절예상일↔쿠팡품절예상일
    return -1;
  }
  var mapping = sheetFields.map(findIdx);
  if(mapping.indexOf(-1) >= 0) return JSON.stringify({error:'unmapped', which: mapping.map(function(m,k){return m<0?sheetFields[k]:null;}).filter(Boolean)});
  var filtered = [], skippedReturn = 0;
  for(var i=2; i<allRows.length; i++){
    var row = allRows[i];
    if(!String(row[0]||'').trim()) continue;
    if(String(row[5]||'').indexOf('반품') >= 0){ skippedReturn++; continue; }
    filtered.push(mapping.map(function(idx){ return row[idx]; }));  // 45필드 F열순 정렬
  }
  window.__filtered = filtered;
  // 검증: 판매수량(idx25=AE)이 전 행 채워지는지 (이전엔 30/1279처럼 적게 채워지면 정렬 깨진 것)
  var aeFilled=0; filtered.forEach(function(r){ var v=r[25]; if(v!==''&&v!=null&&!isNaN(Number(v))) aeFilled++; });
  return JSON.stringify({count: filtered.length, cols: filtered[0]?filtered[0].length:0, skippedReturn: skippedReturn, AE_filled: aeFilled});
})()
```

## 2단계: startRow 확인 (D열 + F열 모두 조회)

**CORS 주의**: gviz는 반드시 **구글 도메인 탭**에서 실행한다. 빅셀 탭(app.bigcell.co.kr)에서 실행하면 CORS 에러 발생.

```javascript
(async function(){
  var sid = '시트ID여기';
  var gid = '1453058054';
  var urlD = 'https://docs.google.com/spreadsheets/d/'+sid+'/gviz/tq?tqx=out:csv&gid='+gid+'&tq=SELECT+D+WHERE+D+is+not+null&range=D1:D70000';
  var rD = await fetch(urlD);
  var tD = await rD.text();
  var linesD = tD.trim().split('\n').length;
  var urlF = 'https://docs.google.com/spreadsheets/d/'+sid+'/gviz/tq?tqx=out:csv&gid='+gid+'&tq=SELECT+F+WHERE+F+is+not+null&range=F1:F70000';
  var rF = await fetch(urlF);
  var tF = await rF.text();
  var linesF = tF.trim().split('\n').length;
  var safeStart = Math.max(linesD, linesF) + 1;
  return JSON.stringify({dCount: linesD, fCount: linesF, startRow: safeStart});
})()
```

## 3단계: 판매 Data 탭에 데이터 전송 + 검증

payload 키는 `sheetId`, `startRow`, `rows`, `date` 4개 사용. (단일 doPost URL이라 sheetId로 대상 시트 지정)

### 3-1. 날짜 포맷 생성

```javascript
// 모든 사업자 공통 (YYYY. M. D 공백 있음)
var target = new Date(Date.now() - 86400000);  // 어제 (KST 환경 가정)
var date = target.getFullYear() + '. ' + (target.getMonth()+1) + '. ' + target.getDate();
// 결과: "2026. 4. 23"
```

### 3-2. doPost 전송

```javascript
(async function(){
  var allRows = window.__filtered;
  var url = "https://script.google.com/macros/s/AKfycbxZ6SCV0k98aVdqfg5t11KlTAt2JPSM-PDqKp94x0oEIXQllumH3OEqAjDEG5x7FQLs/exec"; // hg.kim 공용 doPost
  var startRow = 2단계결과값;
  var date = "YYYY. M. D";
  var payload = { sheetId: '해당회사 시트ID', startRow: startRow, rows: allRows, date: date };
  var r = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'text/plain'},
    body: JSON.stringify(payload),
    redirect: 'follow'
  });
  var txt = await r.text();
  return JSON.stringify({status: r.status, response: txt.substring(0,500)});
})()
```

- `Content-Type: text/plain` + `redirect: 'follow'` 사용
- `mode: 'no-cors'`는 응답이 opaque라 성공 확인 불가 — 금지
- **빅셀 탭에서 실행**: fetch는 script.google.com 도메인 허용. gviz와 달리 CORS 문제 없음

### 3-3. 클린인테크 D열 날짜타입 정규화 (⚠️ 필수 — 2026-05-22 확정)

**클린인테크 doPost는 D열을 텍스트("2026. 5. 21")로 기록한다.** 반면 이더/뉴트리정은 doPost가 D열을 진짜 날짜값(Date)으로 기록하고, 그로스 재고 DB 날짜 헤더도 날짜값이라 ARRAYFORMULA가 매칭된다. 클린인테크는 텍스트 D ≠ 날짜 헤더라 매칭이 전부 실패(newNonZero=0)하여 그로스 DB가 안 채워진다. (SKU ID(I열)·옵션ID(J열)는 정상 기록되므로 row[3] 관련 과거 우려는 해소됨.)

**해결: doPost 직후, 4단계(updateGrowthDB) 호출 전에 반드시 `normalizeDColumn`을 호출한다.** 그러면 D열 텍스트가 날짜값으로 변환되어 이더/뉴트리정과 완전히 동일한 구조가 된다.

- 효율을 위해 **그날 startRow만** 정규화 (전체 컬럼 스캔 불필요, 타임아웃 방지)
- 이더/뉴트리정/마인플로/이든에 호출해도 무해(이미 날짜값이면 그대로 유지) → **5개 사업자 공통 단계로 둘 것**

```javascript
(async function(){
  var url = "https://script.google.com/macros/s/AKfycby2JKRW6hBypZve_E8O6HbmXP5o8crRfwGvGGeNNVmuJqoE8vtDYyRrmQCzjYEcwBOM/exec";
  var payload = { sheetId: '해당회사시트ID', action: 'normalizeDColumn', startRow: doPost한_startRow };
  var r = await fetch(url, {method:'POST', headers:{'Content-Type':'text/plain'}, body: JSON.stringify(payload), redirect:'follow'});
  return await r.text();  // {status:'ok', normalized:N, skipped:0, empty:0}
})()
```

검증: 정규화 후 gviz `SELECT D ... GROUP BY D`가 `2026-5-21`(대시 = 날짜타입)로 나오면 OK. 텍스트로 남으면 `2026. 5. 21`(점)으로 나온다.

### 3-4. doPost 결과 검증

전송 후 반드시 gviz로 데이터가 정상 입력되었는지 확인:

```javascript
(async function(){
  var sid = '시트ID여기';
  var gid = '1453058054';
  var urlF = 'https://docs.google.com/spreadsheets/d/'+sid+'/gviz/tq?tqx=out:csv&gid='+gid+'&tq=SELECT+F+WHERE+F+is+not+null&range=F1:F70000';
  var rF = await fetch(urlF);
  var tF = await rF.text();
  var newFCount = tF.trim().split('\n').length;
  return newFCount;
})()
```

- 기준: `newFCount`가 전송 전보다 증가 → 성공
- 증가하지 않았으면 Apps Script URL, payload 형식, startRow 재확인

## 4단계: 그로스 재고 DB 자동 업데이트 (Standalone Apps Script API)

> ⚠️ **4단계 전에 3-3의 `normalizeDColumn`을 먼저 실행한다 (특히 클린인테크).** D열이 텍스트로 남아 있으면 매칭이 전부 0이 된다.

UI 조작 완전 제거. 한 번의 API 호출로 다음을 모두 처리한다:

1. 최신 날짜 컬럼 왼쪽에 새 컬럼 삽입
2. 날짜 헤더 입력 (YYYY. M. D)
3. 고정 수식을 첫 데이터행에 설정
4. 수식을 전체 데이터행에 copyTo
5. 직전 컬럼 수식→값 변환
6. 비영값 개수 검증

**날짜 컬럼 탐지 방식**: 오른쪽→왼쪽 스캔으로 연속 날짜 블록(그로스 재고 DB 섹션)을 정확히 식별. 시트 내 다른 영역에 날짜 형태 값이 있어도 혼동하지 않는다.

### 4-1. API 호출 (구글 도메인 탭에서 실행)

```javascript
(async function(){
  var url = "https://script.google.com/macros/s/AKfycby2JKRW6hBypZve_E8O6HbmXP5o8crRfwGvGGeNNVmuJqoE8vtDYyRrmQCzjYEcwBOM/exec";
  var payload = {
    sheetId: '해당회사시트ID',
    date: '2026. 4. 23'
  };
  var r = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'text/plain'},
    body: JSON.stringify(payload),
    redirect: 'follow'
  });
  return await r.text();
})()
```

### 4-2. 응답 해석

**정상 응답 (새 컬럼 삽입됨):**
```json
{
  "status": "ok",
  "newCol": 43, "newLetter": "AQ",
  "oldCol": 44, "oldLetter": "AR",
  "date": "2026. 4. 23",
  "formulaRow": 3, "lastRow": 55,
  "newNonZero": 72, "oldNonZero": 71,
  "formula": "=ARRAYFORMULA(INDEX(...))"
}
```

**중복 방지 (이미 같은 날짜 존재):**
```json
{
  "status": "skip",
  "message": "이미 동일 날짜 컬럼 존재",
  "date": "2026. 4. 23",
  "latestStr": "2026. 4. 23",
  "latestCol": 42,
  "latestLetter": "AP"
}
```

**에러:**
```json
{
  "status": "error",
  "message": "에러 메시지"
}
```

### 4-3. 검증 기준

- `newNonZero`와 `oldNonZero`가 비슷한 수준 → **정상** (일별 판매 변동으로 약간의 차이 정상)
- `newNonZero`가 **0** → 수식 오류 또는 날짜 포맷 불일치. 판매 Data에 해당 날짜 데이터 확인
- 상단 행만 보고 ₩0이라서 타입 오류라고 성급히 판단 금지 — 판매량 0 상품은 정상적으로 0 표시

### 4-4. 타임아웃 대응 (매우 중요)

Apps Script 실행이 45초를 넘으면 클라이언트 측 CDP 타임아웃 발생. **서버에서는 계속 실행된다.**

**대응 패턴**:
1. 타임아웃 발생
2. 30~45초 대기
3. **같은 payload로 재호출** → `status: 'skip'` 응답이면 첫 호출이 성공적으로 완료된 것
4. 또는 gviz로 AP/AN 등 신규 컬럼 비영값 개수 확인

```javascript
// 타임아웃 후 재확인 (동일 payload 재전송)
// 결과가 "skip"이면 첫 호출 완료됨
```

### 4-5. 컬럼 삭제 (롤백용)

잘못 삽입된 컬럼을 삭제해야 할 경우:

```javascript
(async function(){
  var url = "https://script.google.com/macros/s/AKfycby2JKRW6hBypZve_E8O6HbmXP5o8crRfwGvGGeNNVmuJqoE8vtDYyRrmQCzjYEcwBOM/exec";
  var payload = {
    sheetId: '해당회사시트ID',
    action: 'deleteCol',
    col: 43
  };
  var r = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'text/plain'},
    body: JSON.stringify(payload),
    redirect: 'follow'
  });
  return await r.text();
})()
```

### 4-6. D열 날짜 정규화 (클린인테크 전용)

클린인테크 등 D열에 Date 객체/텍스트 혼재 시 강제 정규화:

```javascript
var payload = {
  sheetId: '1AVPuPo7rkT-K923BOl2vFe5aKAHJE7bUNZM0kQ0w_PE',
  action: 'normalizeDColumn',
  startRow: 2  // 생략 시 2
};
```

결과는 `{normalized, skipped, empty}` 카운트 반환.

## 5단계: 이더컴퍼니 일일 판매 비교 보고서 자동 생성 (2026-07-15 요청)

이더컴퍼니 갱신(1~4단계)이 끝나면 **묻지 말고 이어서** 판매 비교 보고서를 생성한다. 뉴트리정도 같은 날 갱신했으면 한 파일에 양사 포함.

### 5-1. 데이터 수집 (gviz, 구글 도메인 탭)

- 상품별 비교: `SELECT H, SUM(AE), SUM(AL) WHERE D = date 'YYYY-MM-DD' GROUP BY H` — 당일/전일 2회
- 재고·광고: `SELECT H, SUM(Y), MIN(AC), SUM(AT) WHERE D = date '당일' GROUP BY H` (쿠팡재고/품절예상일/광고집행비. ROAS는 헤더명으로 컬럼 확인)
- 추이: 판매 Data는 사용자가 과거를 지울 수 있으므로 **그로스 재고 DB 일별 컬럼에서 최근 5~7일** 합계를 뽑아 사용

### 5-2. 보고서 구성 (HTML, 작업 폴더에 `판매비교보고서_YYYY-MM-DD.html`)

1. 요약 카드: 합산/사업자별 판매수량·매출 전일비
2. 상품별 비교표: 수량/매출 + 증감 (증가=녹색, 감소=적색)
3. 증감 TOP 3 하이라이트
4. **전략 코멘트 (필수)**:
   - **집중 추천 상품**: 판매 상승 추이 + 쿠팡재고 여유 + 광고 효율 양호 조합으로 2~3개 선정, 선정 이유 명시
   - **발주/입고 경고**: 판매 상위인데 재고 얇은 상품 (품절예상일 임박, 쿠팡입고필요수량 참고)
   - **점검 대상**: 재고 많은데 판매 하락 중인 상품, 광고비 대비 매출 낮은 상품
5. 각주: 데이터 출처(빅셀 로켓그로스, 반품 제외 순판매), 생성일

생성 후 파일을 사용자에게 전달(present_files).

## 금지 사항 (Ctrl+H 사고 이후)

1. **Ctrl+H 찾기/바꾸기로 전체 시트 수식 일괄 변경 금지** — 30,034셀 터치 전례로 불신
2. **Claude 판단으로 수식을 임의로 고치거나 덮어쓰기 금지** (예: #REF! 발견 시 임의 복구)
3. **판매 Data append + 그로스 재고 DB Standalone API 이외의 구조 변경 금지** (행 삽입/삭제, 서식 변경)
4. **Ctrl+Z 금지** — UI 실수 시 되돌리기로 완료 작업 날아가는 사고 반복. 잘못 눌렀으면 Escape + 상태 재확인

**허용**: 판매 Data append + Standalone API(열 추가/수식 입력)까지의 자동화는 **반드시 유지**한다 (2026-04-23 대표님 재확인). Apps Script 인코딩 버그는 `.gs` 소스에 유니코드 이스케이프(`"\uD310\uB9E4 Data"`)로 원천 차단된 버전을 배포해서 해결.

## 주의사항 총정리

1. **startRow는 D열+F열 max + 1**: 한쪽만 보면 덮어쓰기 사고
2. **날짜 포맷은 YYYY. M. D**: 공백 있음, 모든 사업자 동일 (텍스트 그대로, Date 변환 금지)
3. **컬럼 이름기준 매핑 필수**: 빅셀이 컬럼 추가/재배치해도 시트 헤더(F~AX 45필드)명으로 재정렬. slice 고정제거 금지. 판매수량(AE)이 전 행 채워지는지로 검증 (2026-06-10 개정)
4. **수식은 고정 템플릿**: 컬럼 레터와 행번호만 자동 생성, 구조 변경 금지
5. **그로스 재고 DB는 API로 처리**: UI 조작 사용 금지
6. **CORS**: gviz와 Standalone API 호출은 구글 도메인 탭에서만 실행
7. **검증은 비영값 개수로**: newNonZero/oldNonZero 비교 또는 gviz COUNT
8. **중복 방지 내장**: 같은 날짜로 다시 호출하면 자동 skip
9. **타임아웃 = 서버 실행 중**: 45초 타임아웃 시 30초 후 재호출 or gviz 확인
10. **클린인테크 row[3] 금지**: I열 SKU ID 파괴 — 분기 처리 필수
11. **시트명 유니코드 이스케이프**: V8 UTF-8 재해석 버그 원천 차단
12. **Ctrl+H / Ctrl+Z 절대 금지**: 과거 사고 전례
13. **gviz는 캐시 우회 필수** (`&_t=Date.now()`): doPost 직후 행수 확인 시 옛값 반환됨
14. **45초 타임아웃은 정상 동작**: 서버는 계속 실행 중 → 30~45초 대기 후 동일 payload 재호출 시 `skip` 응답이면 완료
15. **빅셀 계정 전환은 `/mypage/members` navigate**: 드롭다운으로 일일이 전환하지 않음
16. **다운로드 첫 클릭은 종종 실패**: "Claude is active" 알림 닫기 + 재클릭 2~3회까지 정상
17. **탭 freeze 시 새 탭으로 우회**: Apps Script 호출 후 V8 컨텍스트 unresponsive 자주 발생, 새 탭에서 docs.google.com 열고 작업 이어감
18. **재고 필드 0 검증**: 파싱 시 쿠팡재고 비영 개수 확인, 전부 0이면 재다운로드 (0-J)
19. **그로스 API 재호출 전 gviz 헤더 확인**: 중복 빈 컬럼 방지 (0-L)
20. **이더는 갱신 후 보고서 자동 생성** (5단계) — 전략 코멘트 포함

## 첨부 파일

- `bigcell-apps-script.gs`: Standalone Apps Script 소스 (v5, 유니코드 이스케이프 적용)
  - 배포 URL: `https://script.google.com/macros/s/AKfycby2JKRW6hBypZve_E8O6HbmXP5o8crRfwGvGGeNNVmuJqoE8vtDYyRrmQCzjYEcwBOM/exec`
  - 타 PC에서 자체 배포 시: Apps Script > 새 프로젝트 > 내용 붙여넣기 > 배포 > 웹 앱 (실행: 나, 액세스: 모든 사용자) > URL 저장
