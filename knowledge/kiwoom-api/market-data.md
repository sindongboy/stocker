# Kiwoom REST API — Market Data Endpoints

> Verified against live API responses. Official docs: https://openapi.kiwoom.com/

## 공통 요청 형식

- Method: **POST**
- Content-Type: `application/json;charset=UTF-8`
- Headers: `authorization: Bearer <token>`, `api-id: <TR명>`
- Body: JSON

---

## 주식 기본정보 / 현재가 (Snapshot)

```
POST /api/dostk/stkinfo
api-id: ka10001
```

**Request body:**
```json
{ "stk_cd": "005930" }
```

**Response fields:**
- `stk_nm` — 종목명
- `cur_prc` — 현재가 (부호 포함 문자열, e.g. `"-216000"` → abs = 216000)
- `pred_pre` — 전일대비 (부호 포함, e.g. `"-1500"`)
- `base_pric` — 기준가 (전일 종가, e.g. `"217500"`)
- `pre_sig` — 등락구분 (1:상한, 2:상승, 3:보합, 4:하한, 5:하락)
- `return_code` — 0 = 정상

> 거래량은 미포함. 필요 시 `ka10007` (시세표성정보) 사용.

---

## 주식 일봉 차트

```
POST /api/dostk/chart
api-id: ka10081
```

**Request body:**
```json
{
  "stk_cd": "005930",
  "base_dt": "20260419",
  "upd_stkpc_tp": "1"
}
```

- `base_dt`: 기준일 (YYYYMMDD), 해당일 이전 데이터 반환
- `upd_stkpc_tp`: `"0"` 수정주가 / `"1"` 원주가

**Response key:** `stk_dt_pole_chart_qry` (배열)

**Per-row fields:**
- `dt` — 날짜 (YYYYMMDD)
- `open_pric` — 시가
- `high_pric` — 고가
- `low_pric` — 저가
- `cur_prc` — 종가
- `trde_qty` — 거래량

---

## 기타 차트 api-id 및 응답 키

| api-id | 설명 | 응답 배열 키 |
|--------|------|------------|
| ka10079 | 틱차트 | (미확인) |
| ka10080 | 분봉 | (미확인) |
| ka10081 | 일봉 | `stk_dt_pole_chart_qry` |
| ka10082 | 주봉 | `stk_stk_pole_chart_qry` (live API 확인) |
| ka10083 | 월봉 | `stk_mth_pole_chart_qry` |

---

## 연속 조회 (페이지네이션)

응답에 다음 페이지가 있으면:
```
cont-yn: Y
next-key: <값>
```
다음 요청 헤더에 `cont-yn: Y`, `next-key: <값>` 추가.
