// Pure technical indicator functions — no dependencies

export interface OHLCV {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

// ── Moving Averages ─────────────────────────────────────────

export function sma(values: number[], period: number): Array<number | null> {
  const out: Array<number | null> = []
  let sum = 0
  for (let i = 0; i < values.length; i++) {
    sum += values[i]
    if (i >= period) sum -= values[i - period]
    out.push(i >= period - 1 ? sum / period : null)
  }
  return out
}

export function ema(values: number[], period: number): Array<number | null> {
  const out: Array<number | null> = Array(values.length).fill(null)
  const k = 2 / (period + 1)
  let prev: number | null = null
  for (let i = 0; i < values.length; i++) {
    if (prev == null) {
      if (i === period - 1) {
        prev = values.slice(0, period).reduce((a, b) => a + b, 0) / period
        out[i] = prev
      }
    } else {
      prev = values[i] * k + prev * (1 - k)
      out[i] = prev
    }
  }
  return out
}

// ── Bollinger Bands ─────────────────────────────────────────

export function bollingerBands(closes: number[], period = 20, mult = 2) {
  const mid = sma(closes, period)
  const upper: Array<number | null> = []
  const lower: Array<number | null> = []
  for (let i = 0; i < closes.length; i++) {
    if (mid[i] == null || i < period - 1) {
      upper.push(null); lower.push(null); continue
    }
    const slice = closes.slice(i - period + 1, i + 1)
    const m = mid[i]!
    const sd = Math.sqrt(slice.reduce((s, v) => s + (v - m) ** 2, 0) / period)
    upper.push(m + mult * sd)
    lower.push(m - mult * sd)
  }
  return { upper, mid, lower }
}

// ── RSI ─────────────────────────────────────────────────────

export function rsi(closes: number[], period = 14): Array<number | null> {
  const out: Array<number | null> = Array(closes.length).fill(null)
  if (closes.length < period + 1) return out

  let avgGain = 0, avgLoss = 0
  for (let i = 1; i <= period; i++) {
    const d = closes[i] - closes[i - 1]
    if (d > 0) avgGain += d; else avgLoss -= d
  }
  avgGain /= period; avgLoss /= period

  for (let i = period; i < closes.length; i++) {
    if (i === period) {
      out[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss)
      continue
    }
    const d = closes[i] - closes[i - 1]
    avgGain = (avgGain * (period - 1) + Math.max(d, 0)) / period
    avgLoss = (avgLoss * (period - 1) + Math.max(-d, 0)) / period
    out[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss)
  }
  return out
}

// ── MACD ────────────────────────────────────────────────────

export function macd(
  closes: number[],
  fast = 12,
  slow = 26,
  signal = 9
): { macdLine: Array<number | null>; signalLine: Array<number | null>; hist: Array<number | null> } {
  const fastEma = ema(closes, fast)
  const slowEma = ema(closes, slow)
  const macdLine: Array<number | null> = closes.map((_, i) =>
    fastEma[i] != null && slowEma[i] != null ? fastEma[i]! - slowEma[i]! : null
  )
  const nonNull = macdLine.filter((v): v is number => v != null)
  const signalRaw = ema(nonNull, signal)
  // Re-align signal to original length
  const signalLine: Array<number | null> = Array(closes.length).fill(null)
  let si = 0
  for (let i = 0; i < closes.length; i++) {
    if (macdLine[i] != null) {
      signalLine[i] = signalRaw[si++] ?? null
    }
  }
  const hist: Array<number | null> = closes.map((_, i) =>
    macdLine[i] != null && signalLine[i] != null ? macdLine[i]! - signalLine[i]! : null
  )
  return { macdLine, signalLine, hist }
}

// ── OBV ─────────────────────────────────────────────────────

export function obv(candles: OHLCV[]): number[] {
  const out: number[] = [0]
  for (let i = 1; i < candles.length; i++) {
    const prev = out[i - 1]
    const d = candles[i].close - candles[i - 1].close
    out.push(d > 0 ? prev + candles[i].volume : d < 0 ? prev - candles[i].volume : prev)
  }
  return out
}

// ── Parabolic SAR ────────────────────────────────────────────

export function parabolicSar(
  candles: OHLCV[],
  initAf = 0.02,
  maxAf = 0.2
): Array<{ value: number; bull: boolean }> {
  if (candles.length < 2) return []
  const out: Array<{ value: number; bull: boolean }> = []
  let bull = true
  let af = initAf
  let ep = candles[0].high
  let sar = candles[0].low

  for (let i = 1; i < candles.length; i++) {
    const prev = candles[i - 1]
    const curr = candles[i]

    sar = sar + af * (ep - sar)

    if (bull) {
      if (sar > Math.min(prev.low, curr.low)) {
        bull = false; sar = ep; ep = curr.low; af = initAf
      } else {
        if (curr.high > ep) { ep = curr.high; af = Math.min(af + initAf, maxAf) }
        sar = Math.min(sar, prev.low, i > 1 ? candles[i - 2].low : prev.low)
      }
    } else {
      if (sar < Math.max(prev.high, curr.high)) {
        bull = true; sar = ep; ep = curr.high; af = initAf
      } else {
        if (curr.low < ep) { ep = curr.low; af = Math.min(af + initAf, maxAf) }
        sar = Math.max(sar, prev.high, i > 1 ? candles[i - 2].high : prev.high)
      }
    }
    out.push({ value: sar, bull })
  }
  // pad first element
  out.unshift(out[0] ?? { value: candles[0].low, bull: true })
  return out
}

// ── Ichimoku ─────────────────────────────────────────────────

function midRange(arr: OHLCV[], i: number, period: number): number | null {
  if (i < period - 1) return null
  const slice = arr.slice(i - period + 1, i + 1)
  const hi = Math.max(...slice.map((c) => c.high))
  const lo = Math.min(...slice.map((c) => c.low))
  return (hi + lo) / 2
}

export function ichimoku(candles: OHLCV[], displacement = 26) {
  const tenkan:  Array<number | null> = []
  const kijun:   Array<number | null> = []
  const senkouA: Array<number | null> = []
  const senkouB: Array<number | null> = []
  const chikou:  Array<number | null> = []

  for (let i = 0; i < candles.length; i++) {
    tenkan.push(midRange(candles, i, 9))
    kijun.push(midRange(candles, i, 26))
    // Senkou A/B are projected forward by displacement — align to future candle index
    const sa = tenkan[i] != null && kijun[i] != null
      ? (tenkan[i]! + kijun[i]!) / 2 : null
    const sb = midRange(candles, i, 52)
    senkouA.push(sa)
    senkouB.push(sb)
    // Chikou: current close plotted displacement bars in the past
    chikou.push(i + displacement < candles.length ? candles[i + displacement].close : null)
  }

  return { tenkan, kijun, senkouA, senkouB, chikou }
}

// ── Volume MA ────────────────────────────────────────────────

export function volumeMa(candles: OHLCV[], period: number): Array<number | null> {
  return sma(candles.map((c) => c.volume), period)
}

// ── Price Volume Profile (매물대) ────────────────────────────

export interface PVPBucket {
  price: number   // bucket mid-price
  volume: number  // total volume in bucket
  buyVol: number
  sellVol: number
}

export function priceVolumeProfile(candles: OHLCV[], buckets = 40): PVPBucket[] {
  if (candles.length === 0) return []
  const allHigh = Math.max(...candles.map((c) => c.high))
  const allLow  = Math.min(...candles.map((c) => c.low))
  const range   = allHigh - allLow || 1
  const step    = range / buckets

  const result: PVPBucket[] = Array.from({ length: buckets }, (_, i) => ({
    price: allLow + (i + 0.5) * step,
    volume: 0,
    buyVol: 0,
    sellVol: 0,
  }))

  for (const c of candles) {
    const isBull = c.close >= c.open
    // distribute volume evenly across the candle's price range
    const lo = Math.min(c.open, c.close, c.low)
    const hi = Math.max(c.open, c.close, c.high)
    const startB = Math.max(0, Math.floor((lo - allLow) / step))
    const endB   = Math.min(buckets - 1, Math.floor((hi - allLow) / step))
    const spread  = endB - startB + 1
    const volPer  = c.volume / spread
    for (let b = startB; b <= endB; b++) {
      result[b].volume += volPer
      if (isBull) result[b].buyVol += volPer
      else result[b].sellVol += volPer
    }
  }
  return result
}
