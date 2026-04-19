'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
  CandlestickData,
  LineData,
  HistogramData,
  ColorType,
  Time,
  CrosshairMode,
  IPrimitivePaneRenderer,
  IPrimitivePaneView,
  ISeriesPrimitive,
  SeriesAttachedParameter,
} from 'lightweight-charts'
import useSWR from 'swr'
import {
  sma, ema, bollingerBands, rsi as calcRsi, macd as calcMacd,
  obv as calcObv, parabolicSar, ichimoku as calcIchimoku,
  volumeMa, priceVolumeProfile, type OHLCV, type PVPBucket,
} from '@/lib/indicators'
import { usePriceFeed } from '@/hooks/usePriceFeed'

// ── types ──────────────────────────────────────────────────────────────────────

interface Candle {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface Props {
  ticker: string
  name: string
}

interface LegendBar {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

type Period = 'D' | 'W' | 'M'
type Count  = 60 | 120 | 250

interface OverlayInds {
  ma5: boolean; ma20: boolean; ma60: boolean; ma120: boolean
  bb: boolean; sar: boolean; ichimoku: boolean; pvp: boolean
}

interface PanelInds {
  volume: boolean; volMa: boolean; obv: boolean
  rsi: boolean; macd: boolean
}

// ── constants ──────────────────────────────────────────────────────────────────

const fetcher = (url: string) => fetch(url).then((r) => r.json())

const PERIOD_LABELS: Record<Period, string> = { D: '일봉', W: '주봉', M: '월봉' }
const COUNT_OPTIONS: Count[] = [60, 120, 250]

const OVERLAY_CONFIG = [
  { key: 'ma5'     as const, label: 'MA5',    color: '#fbbf24' },
  { key: 'ma20'    as const, label: 'MA20',   color: '#a78bfa' },
  { key: 'ma60'    as const, label: 'MA60',   color: '#34d399' },
  { key: 'ma120'   as const, label: 'MA120',  color: '#f472b6' },
  { key: 'bb'      as const, label: '볼린저',  color: '#64748b' },
  { key: 'sar'     as const, label: 'SAR',    color: '#fb923c' },
  { key: 'ichimoku'as const, label: '일목',   color: '#38bdf8' },
  { key: 'pvp'     as const, label: '매물대', color: '#6366f1' },
]

const PANEL_CONFIG = [
  { key: 'volume'  as const, label: '거래량' },
  { key: 'volMa'   as const, label: '거래량MA' },
  { key: 'obv'     as const, label: 'OBV' },
  { key: 'rsi'     as const, label: 'RSI' },
  { key: 'macd'    as const, label: 'MACD' },
]

// ── Price Volume Profile primitive ────────────────────────────────────────────

type DrawTarget = Parameters<IPrimitivePaneRenderer['draw']>[0]

class PVPRenderer implements IPrimitivePaneRenderer {
  constructor(
    private _buckets: PVPBucket[],
    private _series: ISeriesApi<'Candlestick'>,
    private _step: number,
    private _visible: boolean,
  ) {}

  draw(target: DrawTarget) {
    if (!this._visible || this._buckets.length === 0) return
    target.useBitmapCoordinateSpace(({ context, bitmapSize, verticalPixelRatio }) => {
      const maxVol = Math.max(...this._buckets.map((b) => b.volume))
      if (maxVol === 0) return
      const maxBarW = bitmapSize.width * 0.2  // 20% of pane width for POC

      for (const bucket of this._buckets) {
        const yTop = this._series.priceToCoordinate(bucket.price + this._step / 2)
        const yBot = this._series.priceToCoordinate(bucket.price - this._step / 2)
        if (yTop == null || yBot == null) continue

        const barW = (bucket.volume / maxVol) * maxBarW
        const y = Math.round(yTop * verticalPixelRatio)
        const h = Math.max(1, Math.round((yBot - yTop) * verticalPixelRatio))
        const x = bitmapSize.width - Math.round(barW)

        // bull/bear split colour
        const bullW = (bucket.buyVol / (bucket.volume || 1)) * barW
        context.fillStyle = 'rgba(248,113,113,0.3)'
        context.fillRect(x, y, Math.round(bullW), h)
        context.fillStyle = 'rgba(96,165,250,0.3)'
        context.fillRect(x + Math.round(bullW), y, Math.round(barW - bullW), h)
      }
    })
  }
}

class PVPView implements IPrimitivePaneView {
  constructor(private _renderer: PVPRenderer) {}
  renderer() { return this._renderer }
  zOrder(): 'bottom' { return 'bottom' }
}

class PVPPrimitive implements ISeriesPrimitive {
  private _series: ISeriesApi<'Candlestick'> | null = null
  private _requestUpdate: (() => void) | null = null
  private _view: PVPView | null = null

  update(buckets: PVPBucket[], step: number, visible: boolean) {
    if (!this._series) return
    const renderer = new PVPRenderer(buckets, this._series, step, visible)
    this._view = new PVPView(renderer)
    this._requestUpdate?.()
  }

  attached(param: SeriesAttachedParameter) {
    this._series = param.series as ISeriesApi<'Candlestick'>
    this._requestUpdate = param.requestUpdate
  }

  detached() {
    this._series = null
    this._requestUpdate = null
    this._view = null
  }

  paneViews(): readonly IPrimitivePaneView[] {
    return this._view ? [this._view] : []
  }
}

// ── helpers ────────────────────────────────────────────────────────────────────

function toLineData(times: string[], values: Array<number | null>): LineData[] {
  return values
    .map((v, i) => (v == null ? null : { time: times[i] as Time, value: v }))
    .filter((x): x is LineData => x !== null)
}

function fmt(n: number | undefined) {
  return n == null ? '--' : n.toLocaleString('ko-KR')
}

// ── component ──────────────────────────────────────────────────────────────────

export function CandleChart({ ticker, name }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef     = useRef<IChartApi | null>(null)

  // Series refs
  const SR = useRef<{
    candle:    ISeriesApi<'Candlestick'> | null
    ma5:       ISeriesApi<'Line'> | null
    ma20:      ISeriesApi<'Line'> | null
    ma60:      ISeriesApi<'Line'> | null
    ma120:     ISeriesApi<'Line'> | null
    bbUp:      ISeriesApi<'Line'> | null
    bbMid:     ISeriesApi<'Line'> | null
    bbLow:     ISeriesApi<'Line'> | null
    sar:       ISeriesApi<'Line'> | null
    ichTenkan: ISeriesApi<'Line'> | null
    ichKijun:  ISeriesApi<'Line'> | null
    ichSenkouA:ISeriesApi<'Line'> | null
    ichSenkouB:ISeriesApi<'Line'> | null
    ichChikou: ISeriesApi<'Line'> | null
    volume:    ISeriesApi<'Histogram'> | null
    volMa5:    ISeriesApi<'Line'> | null
    volMa20:   ISeriesApi<'Line'> | null
    obv:       ISeriesApi<'Line'> | null
    rsi:       ISeriesApi<'Line'> | null
    rsiOB:     ISeriesApi<'Line'> | null
    rsiOS:     ISeriesApi<'Line'> | null
    macdLine:  ISeriesApi<'Line'> | null
    macdSig:   ISeriesApi<'Line'> | null
    macdHist:  ISeriesApi<'Histogram'> | null
  }>({
    candle: null, ma5: null, ma20: null, ma60: null, ma120: null,
    bbUp: null, bbMid: null, bbLow: null, sar: null,
    ichTenkan: null, ichKijun: null, ichSenkouA: null, ichSenkouB: null, ichChikou: null,
    volume: null, volMa5: null, volMa20: null, obv: null,
    rsi: null, rsiOB: null, rsiOS: null,
    macdLine: null, macdSig: null, macdHist: null,
  })

  // Pane indices (assigned when pane created)
  const paneIdx = useRef<{ vol: number; obv: number; rsi: number; macd: number }>({
    vol: 1, obv: 2, rsi: 3, macd: 4,
  })

  const [period,  setPeriod]  = useState<Period>('D')
  const [count,   setCount]   = useState<Count>(60)
  const [legend,  setLegend]  = useState<LegendBar | null>(null)
  const [overlay, setOverlay] = useState<OverlayInds>({
    ma5: true, ma20: true, ma60: false, ma120: false,
    bb: false, sar: false, ichimoku: false, pvp: false,
  })
  const [panels, setPanels] = useState<PanelInds>({
    volume: true, volMa: false, obv: false, rsi: false, macd: false,
  })

  const candlesRef   = useRef<Candle[]>([])
  const pvpPrimitive = useRef(new PVPPrimitive())

  const { data: candles, isLoading } = useSWR<Candle[]>(
    `/api/v1/market/candles/${ticker}?period=${period}&count=${count}`,
    fetcher,
    { revalidateOnFocus: false }
  )

  // Real-time price feed
  const { feed } = usePriceFeed([ticker])
  const live = feed[ticker]

  // ── Init chart ─────────────────────────────────────────────────────────────

  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: '#0f172a' },
        textColor: '#94a3b8',
      },
      grid: { vertLines: { color: '#1e293b' }, horzLines: { color: '#1e293b' } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: '#334155', scaleMargins: { top: 0.05, bottom: 0.02 } },
      timeScale: { borderColor: '#334155', timeVisible: true },
    })

    const s = SR.current

    // Pane 0 — main candle chart
    s.candle = chart.addSeries(CandlestickSeries, {
      upColor: '#f87171', downColor: '#60a5fa',
      borderUpColor: '#f87171', borderDownColor: '#60a5fa',
      wickUpColor: '#f87171', wickDownColor: '#60a5fa',
    }, 0)

    const line = (color: string, title: string, visible: boolean, pane = 0) =>
      chart.addSeries(LineSeries, {
        color, lineWidth: 1, priceLineVisible: false,
        lastValueVisible: false, title, visible,
      }, pane)

    s.ma5    = line('#fbbf24', 'MA5',   true)
    s.ma20   = line('#a78bfa', 'MA20',  true)
    s.ma60   = line('#34d399', 'MA60',  false)
    s.ma120  = line('#f472b6', 'MA120', false)
    s.bbUp   = line('#475569', 'BB+', false)
    s.bbMid  = line('#64748b', 'BB Mid', false)
    s.bbLow  = line('#475569', 'BB-', false)
    s.sar    = chart.addSeries(LineSeries, {
      color: '#fb923c', lineWidth: 1, lineStyle: 0,
      pointMarkersVisible: true, priceLineVisible: false, lastValueVisible: false,
      title: 'SAR', visible: false,
    }, 0)
    s.ichTenkan  = line('#ef4444', '転換',  false)
    s.ichKijun   = line('#3b82f6', '基準',  false)
    s.ichSenkouA = line('#86efac', '先A',   false)
    s.ichSenkouB = line('#fca5a5', '先B',   false)
    s.ichChikou  = line('#a78bfa', '遅行',  false)

    // Pane 1 — volume
    chart.addPane()
    paneIdx.current.vol = 1
    s.volume = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' }, priceScaleId: 'right', visible: true,
    }, 1)
    chart.panes()[1]?.setHeight(80)
    s.volMa5  = line('#fbbf24', 'VolMA5',  false, 1)
    s.volMa20 = line('#a78bfa', 'VolMA20', false, 1)

    // Pane 2 — OBV
    chart.addPane()
    paneIdx.current.obv = 2
    s.obv = line('#38bdf8', 'OBV', false, 2)
    chart.panes()[2]?.setHeight(60)

    // Pane 3 — RSI
    chart.addPane()
    paneIdx.current.rsi = 3
    s.rsi   = line('#f59e0b', 'RSI', false, 3)
    s.rsiOB = line('#ef444488', '', false, 3)
    s.rsiOS = line('#60a5fa88', '', false, 3)
    chart.panes()[3]?.setHeight(80)

    // Pane 4 — MACD
    chart.addPane()
    paneIdx.current.macd = 4
    s.macdLine = line('#f59e0b', 'MACD',   false, 4)
    s.macdSig  = line('#f87171', 'Signal', false, 4)
    s.macdHist = chart.addSeries(HistogramSeries, {
      priceScaleId: 'right', visible: false,
    }, 4)
    chart.panes()[4]?.setHeight(80)

    // Price Volume Profile primitive
    s.candle.attachPrimitive(pvpPrimitive.current)

    // Crosshair legend
    chart.subscribeCrosshairMove((param) => {
      if (!param.time || !s.candle) { setLegend(null); return }
      const bar = param.seriesData.get(s.candle) as CandlestickData | undefined
      const volBar = param.seriesData.get(s.volume!) as HistogramData | undefined
      if (bar) {
        setLegend({
          date: String(param.time),
          open: bar.open, high: bar.high, low: bar.low, close: bar.close,
          volume: Number(volBar?.value ?? 0),
        })
      }
    })

    chartRef.current = chart
    return () => { chart.remove() }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Sync visibility ───────────────────────────────────────────────────────

  useEffect(() => {
    const s = SR.current
    s.ma5?.applyOptions({ visible: overlay.ma5 })
    s.ma20?.applyOptions({ visible: overlay.ma20 })
    s.ma60?.applyOptions({ visible: overlay.ma60 })
    s.ma120?.applyOptions({ visible: overlay.ma120 })
    s.bbUp?.applyOptions({ visible: overlay.bb })
    s.bbMid?.applyOptions({ visible: overlay.bb })
    s.bbLow?.applyOptions({ visible: overlay.bb })
    s.sar?.applyOptions({ visible: overlay.sar })
    const ichVis = overlay.ichimoku
    s.ichTenkan?.applyOptions({ visible: ichVis })
    s.ichKijun?.applyOptions({ visible: ichVis })
    s.ichSenkouA?.applyOptions({ visible: ichVis })
    s.ichSenkouB?.applyOptions({ visible: ichVis })
    s.ichChikou?.applyOptions({ visible: ichVis })

    // PVP — re-render with current visibility (preserves existing buckets)
    if (candlesRef.current.length > 0) {
      const ohlcv: OHLCV[] = candlesRef.current.map((c) => ({ ...c }))
      const pvpBuckets = priceVolumeProfile(ohlcv, 40)
      const allHigh = Math.max(...ohlcv.map((c) => c.high))
      const allLow  = Math.min(...ohlcv.map((c) => c.low))
      pvpPrimitive.current.update(pvpBuckets, (allHigh - allLow) / 40, overlay.pvp)
    }
  }, [overlay])

  useEffect(() => {
    const s = SR.current
    s.volume?.applyOptions({ visible: panels.volume })
    s.volMa5?.applyOptions({ visible: panels.volMa })
    s.volMa20?.applyOptions({ visible: panels.volMa })
    s.obv?.applyOptions({ visible: panels.obv })
    s.rsi?.applyOptions({ visible: panels.rsi })
    s.rsiOB?.applyOptions({ visible: panels.rsi })
    s.rsiOS?.applyOptions({ visible: panels.rsi })
    s.macdLine?.applyOptions({ visible: panels.macd })
    s.macdSig?.applyOptions({ visible: panels.macd })
    s.macdHist?.applyOptions({ visible: panels.macd })

    // Resize sub-panes based on visibility
    const panes = chartRef.current?.panes()
    if (!panes) return
    panes[1]?.setHeight(panels.volume ? 80 : 0)
    panes[2]?.setHeight(panels.obv    ? 70 : 0)
    panes[3]?.setHeight(panels.rsi    ? 80 : 0)
    panes[4]?.setHeight(panels.macd   ? 80 : 0)
  }, [panels])

  // ── Update data ───────────────────────────────────────────────────────────

  useEffect(() => {
    const s = SR.current
    if (!s.candle) return

    if (!candles || candles.length === 0) {
      Object.values(s).forEach((sr) => (sr as ISeriesApi<never> | null)?.setData([]))
      return
    }

    candlesRef.current = candles
    const ohlcv: OHLCV[] = candles.map((c) => ({ ...c }))
    const times  = candles.map((c) => c.date)
    const closes = candles.map((c) => c.close)
    const vols   = candles.map((c) => c.volume)

    // Candle
    const candleData: CandlestickData[] = candles.map((c) => ({
      time: c.date as Time, open: c.open, high: c.high, low: c.low, close: c.close,
    }))
    s.candle.setData(candleData)

    // MA
    s.ma5?.setData(toLineData(times, sma(closes, 5)))
    s.ma20?.setData(toLineData(times, sma(closes, 20)))
    s.ma60?.setData(toLineData(times, sma(closes, 60)))
    s.ma120?.setData(toLineData(times, sma(closes, 120)))

    // BB
    const { upper, mid, lower } = bollingerBands(closes)
    s.bbUp?.setData(toLineData(times, upper))
    s.bbMid?.setData(toLineData(times, mid))
    s.bbLow?.setData(toLineData(times, lower))

    // SAR
    const sarData = parabolicSar(ohlcv)
    s.sar?.setData(sarData.map((v, i) => ({ time: times[i] as Time, value: v.value })))

    // Ichimoku
    const ich = calcIchimoku(ohlcv)
    s.ichTenkan?.setData(toLineData(times, ich.tenkan))
    s.ichKijun?.setData(toLineData(times, ich.kijun))
    s.ichSenkouA?.setData(toLineData(times, ich.senkouA))
    s.ichSenkouB?.setData(toLineData(times, ich.senkouB))
    s.ichChikou?.setData(toLineData(times, ich.chikou))

    // Volume
    s.volume?.setData(candles.map((c) => ({
      time: c.date as Time,
      value: c.volume,
      color: c.close >= c.open ? 'rgba(248,113,113,0.5)' : 'rgba(96,165,250,0.5)',
    })))
    s.volMa5?.setData(toLineData(times, volumeMa(ohlcv, 5)))
    s.volMa20?.setData(toLineData(times, volumeMa(ohlcv, 20)))

    // OBV
    const obvData = calcObv(ohlcv)
    s.obv?.setData(times.map((t, i) => ({ time: t as Time, value: obvData[i] })))

    // RSI
    const rsiData = calcRsi(closes, 14)
    s.rsi?.setData(toLineData(times, rsiData))
    s.rsiOB?.setData(times.map((t) => ({ time: t as Time, value: 70 })))
    s.rsiOS?.setData(times.map((t) => ({ time: t as Time, value: 30 })))

    // MACD
    const { macdLine, signalLine, hist } = calcMacd(closes)
    s.macdLine?.setData(toLineData(times, macdLine))
    s.macdSig?.setData(toLineData(times, signalLine))
    s.macdHist?.setData(
      hist.flatMap((v, i) => v == null ? [] : [{
        time: times[i] as Time,
        value: v,
        color: v >= 0 ? 'rgba(248,113,113,0.6)' : 'rgba(96,165,250,0.6)',
      } satisfies HistogramData<Time>])
    )

    // PVP
    const pvpBuckets = priceVolumeProfile(ohlcv, 40)
    const allHigh = Math.max(...ohlcv.map((c) => c.high))
    const allLow  = Math.min(...ohlcv.map((c) => c.low))
    const pvpStep = (allHigh - allLow) / 40
    pvpPrimitive.current.update(pvpBuckets, pvpStep, overlay.pvp)

    chartRef.current?.timeScale().fitContent()
  }, [candles, ticker])  // overlay.pvp intentionally omitted — handled by visibility effect

  // ── Real-time last candle update ──────────────────────────────────────────

  useEffect(() => {
    if (!live || !SR.current.candle || candlesRef.current.length === 0) return
    const last = candlesRef.current[candlesRef.current.length - 1]
    SR.current.candle.update({
      time: last.date as Time,
      open: last.open,
      high: Math.max(last.high, live.price),
      low:  Math.min(last.low,  live.price),
      close: live.price,
    })
  }, [live])

  // ── Toggles ───────────────────────────────────────────────────────────────

  const toggleOverlay = useCallback((key: keyof OverlayInds) => {
    setOverlay((p) => ({ ...p, [key]: !p[key] }))
  }, [])

  const togglePanel = useCallback((key: keyof PanelInds) => {
    setPanels((p) => ({ ...p, [key]: !p[key] }))
  }, [])

  // ── render ────────────────────────────────────────────────────────────────

  const isUp = legend ? legend.close >= legend.open : true

  return (
    <div className="flex flex-col gap-2 h-full">
      {/* ── Header: name + legend ── */}
      <div className="flex items-start gap-3 flex-wrap shrink-0">
        <div>
          <span className="text-base font-semibold text-gray-100">{name}</span>
          <span className="ml-2 text-xs text-gray-500">{ticker}</span>
        </div>

        {legend ? (
          <div className="flex items-center gap-3 text-xs font-mono flex-wrap">
            <span className="text-gray-500">{legend.date}</span>
            <span className="text-gray-400">시 <span className={isUp ? 'text-red-400' : 'text-blue-400'}>{fmt(legend.open)}</span></span>
            <span className="text-gray-400">고 <span className="text-red-400">{fmt(legend.high)}</span></span>
            <span className="text-gray-400">저 <span className="text-blue-400">{fmt(legend.low)}</span></span>
            <span className="text-gray-400">종 <span className={isUp ? 'text-red-400' : 'text-blue-400'}>{fmt(legend.close)}</span></span>
            <span className="text-gray-400">량 <span className="text-gray-300">{fmt(legend.volume)}</span></span>
          </div>
        ) : live ? (
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className={live.change_pct >= 0 ? 'text-red-400 font-semibold' : 'text-blue-400 font-semibold'}>
              {fmt(live.price)}
            </span>
            <span className={live.change_pct >= 0 ? 'text-red-400' : 'text-blue-400'}>
              {live.change_pct >= 0 ? '+' : ''}{live.change_pct.toFixed(2)}%
            </span>
          </div>
        ) : null}
      </div>

      {/* ── Period + Count switcher ── */}
      <div className="flex items-center gap-2 shrink-0 flex-wrap">
        <div className="flex gap-1">
          {(['D', 'W', 'M'] as Period[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
                period === p
                  ? 'bg-blue-700 text-white'
                  : 'text-gray-500 hover:text-gray-300 border border-gray-700'
              }`}
            >
              {PERIOD_LABELS[p]}
            </button>
          ))}
        </div>
        <div className="flex gap-1">
          {COUNT_OPTIONS.map((n) => (
            <button
              key={n}
              onClick={() => setCount(n)}
              className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
                count === n
                  ? 'bg-gray-700 text-gray-100'
                  : 'text-gray-500 hover:text-gray-300 border border-gray-700'
              }`}
            >
              {n}
            </button>
          ))}
        </div>

        {/* Overlay indicators */}
        <div className="flex gap-1 flex-wrap ml-2 border-l border-gray-800 pl-2">
          {OVERLAY_CONFIG.map(({ key, label, color }) => (
            <button
              key={key}
              onClick={() => toggleOverlay(key)}
              className={`px-2 py-0.5 rounded text-xs font-medium border transition-colors ${
                overlay[key]
                  ? 'border-transparent text-gray-900'
                  : 'border-gray-700 text-gray-500 hover:text-gray-300'
              }`}
              style={overlay[key] ? { backgroundColor: color } : undefined}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Sub-panel indicators */}
        <div className="flex gap-1 flex-wrap border-l border-gray-800 pl-2">
          {PANEL_CONFIG.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => togglePanel(key)}
              className={`px-2 py-0.5 rounded text-xs font-medium border transition-colors ${
                panels[key]
                  ? 'bg-gray-700 border-gray-600 text-gray-100'
                  : 'border-gray-700 text-gray-500 hover:text-gray-300'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Chart ── */}
      <div className="relative flex-1 min-h-0">
        <div ref={containerRef} className="absolute inset-0" />
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center text-gray-600 text-sm bg-[#0f172a] z-10">
            불러오는 중…
          </div>
        )}
      </div>
    </div>
  )
}
