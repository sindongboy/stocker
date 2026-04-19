# 지표: 이동평균 (Moving Average)

## SMA (단순 이동평균)

```
SMA(n) = 최근 n일 종가의 합 / n
```

- MA5: 단기 추세 (5 영업일 ≈ 1주)
- MA20: 중기 추세 (20 영업일 ≈ 1달)
- MA60: 장기 추세 (60 영업일 ≈ 분기)

## EMA (지수 이동평균)

```
k = 2 / (n + 1)
EMA(t) = 현재가 × k + EMA(t-1) × (1 - k)
```

MACD 계산에 EMA12, EMA26 사용.

## MACD

```
MACD선 = EMA12 - EMA26
시그널 = MACD선의 EMA9
히스토그램 = MACD선 - 시그널
```

## get_indicators 사용 예시

```
get_indicators("005930", ["MA5", "MA20", "RSI14", "MACD"])
```

반환 필드: `MA5`, `MA20`, `RSI14`, `MACD`, `MACD_signal`, `MACD_hist`
