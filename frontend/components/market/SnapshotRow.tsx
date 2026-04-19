'use client'

import { PriceData } from '@/hooks/usePriceFeed'

interface Props {
  ticker: string
  name: string
  live?: PriceData
  selected: boolean
  onSelect: (ticker: string) => void
}

function fmt(n: number) {
  return n.toLocaleString('ko-KR')
}

export function SnapshotRow({ ticker, name, live, selected, onSelect }: Props) {
  const price = live?.price
  const changePct = live?.change_pct ?? 0
  const isUp = changePct > 0
  const isDown = changePct < 0

  return (
    <button
      onClick={() => onSelect(ticker)}
      className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-sm transition-colors
        ${selected ? 'bg-blue-950 border border-blue-700' : 'hover:bg-gray-800 border border-transparent'}`}
    >
      <div className="text-left">
        <div className="font-medium text-gray-100">{name}</div>
        <div className="text-xs text-gray-500">{ticker}</div>
      </div>

      <div className="text-right">
        {price != null ? (
          <>
            <div className="font-mono font-semibold text-gray-100">{fmt(price)}</div>
            <div className={`text-xs font-mono ${isUp ? 'text-red-400' : isDown ? 'text-blue-400' : 'text-gray-500'}`}>
              {isUp ? '+' : ''}{changePct.toFixed(2)}%
            </div>
          </>
        ) : (
          <div className="text-xs text-gray-600">--</div>
        )}
      </div>
    </button>
  )
}
