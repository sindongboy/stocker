'use client'

import useSWR from 'swr'

interface Holding {
  ticker: string
  name: string
  qty: number
  avg_price: number
  current_price: number
  market_value: number
  unrealized_pnl: number
}

interface PortfolioData {
  cash: number
  total_value: number
  total_market_value: number
  daily_realized_pnl: number
  holdings: Holding[]
  mode: string
}

const fetcher = (url: string) => fetch(url).then((r) => r.json())

function fmt(n: number) {
  return n.toLocaleString('ko-KR')
}

function PnlSpan({ value }: { value: number }) {
  if (value === 0) return <span className="text-gray-500">—</span>
  return (
    <span className={value > 0 ? 'text-red-400' : 'text-blue-400'}>
      {value > 0 ? '+' : ''}{fmt(value)}
    </span>
  )
}

export function PortfolioWidget() {
  const { data, error } = useSWR<PortfolioData>(
    '/api/v1/strategies/portfolio',
    fetcher,
    { refreshInterval: 5000, revalidateOnFocus: false },
  )

  if (error || !data) return null

  return (
    <div className="px-2 py-3 border-t border-gray-800">
      <div className="text-xs text-gray-500 font-medium mb-2 flex items-center justify-between">
        <span>포트폴리오</span>
        <span className="text-gray-700 text-[10px]">{data.mode}</span>
      </div>

      <div className="space-y-1 text-xs">
        <div className="flex justify-between text-gray-400">
          <span>현금</span>
          <span className="font-mono text-gray-200">{fmt(data.cash)}원</span>
        </div>
        <div className="flex justify-between text-gray-400">
          <span>평가금액</span>
          <span className="font-mono text-gray-200">{fmt(data.total_value)}원</span>
        </div>
        {data.daily_realized_pnl !== 0 && (
          <div className="flex justify-between text-gray-400">
            <span>당일손익</span>
            <span className="font-mono"><PnlSpan value={data.daily_realized_pnl} /></span>
          </div>
        )}
      </div>

      {data.holdings.length > 0 && (
        <div className="mt-2 space-y-1">
          {data.holdings.map((h) => (
            <div key={h.ticker} className="bg-gray-900 rounded px-2 py-1">
              <div className="flex justify-between text-xs">
                <span className="text-gray-300">{h.name}</span>
                <PnlSpan value={h.unrealized_pnl} />
              </div>
              <div className="flex justify-between text-[10px] text-gray-600 mt-0.5">
                <span>{h.qty}주 @ {fmt(h.avg_price)}</span>
                <span>{fmt(h.market_value)}원</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
