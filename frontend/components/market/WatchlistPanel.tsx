'use client'

import { useState } from 'react'
import { usePriceFeed } from '@/hooks/usePriceFeed'
import { SnapshotRow } from './SnapshotRow'

interface WatchlistItem {
  ticker: string
  name: string
  market: string
}

interface Props {
  items: WatchlistItem[]
  selected: string | null
  onSelect: (ticker: string) => void
  onWatchlistChange?: () => void
}

const statusDot: Record<string, string> = {
  connecting: 'bg-yellow-500 animate-pulse',
  open: 'bg-green-500',
  closed: 'bg-red-500',
}

const statusLabel: Record<string, string> = {
  connecting: '연결 중',
  open: '실시간',
  closed: '연결 끊김',
}

export function WatchlistPanel({ items, selected, onSelect, onWatchlistChange }: Props) {
  const tickers = items.map((i) => i.ticker)
  const { feed, status } = usePriceFeed(tickers)
  const [addInput, setAddInput] = useState('')
  const [addError, setAddError] = useState<string | null>(null)
  const [removing, setRemoving] = useState<string | null>(null)

  async function handleAdd() {
    const ticker = addInput.trim().replace(/\s/g, '')
    if (!ticker) return
    setAddError(null)
    const res = await fetch(`/api/v1/market/watchlist/${ticker}`, { method: 'POST' })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      setAddError(body.detail ?? '추가 실패')
      return
    }
    setAddInput('')
    onWatchlistChange?.()
  }

  async function handleRemove(ticker: string) {
    setRemoving(ticker)
    await fetch(`/api/v1/market/watchlist/${ticker}`, { method: 'DELETE' })
    setRemoving(null)
    onWatchlistChange?.()
  }

  return (
    <aside className="flex flex-col gap-1 h-full overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 shrink-0">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
          관심종목
        </span>
        <span
          className="flex items-center gap-1.5 text-[10px] text-gray-500"
          title={statusLabel[status]}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${statusDot[status]}`} />
          {statusLabel[status]}
        </span>
      </div>

      {/* Ticker list */}
      {items.map((item) => (
        <div key={item.ticker} className="relative group">
          <SnapshotRow
            ticker={item.ticker}
            name={item.name}
            live={feed[item.ticker]}
            selected={selected === item.ticker}
            onSelect={onSelect}
          />
          <button
            onClick={() => handleRemove(item.ticker)}
            disabled={removing === item.ticker}
            className="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 text-gray-600 hover:text-red-400 text-xs px-1 transition-opacity"
            title="관심종목 삭제"
          >
            ×
          </button>
        </div>
      ))}

      {/* Add ticker input */}
      <div className="px-2 pt-2 pb-1 shrink-0">
        <div className="flex gap-1">
          <input
            type="text"
            value={addInput}
            onChange={(e) => setAddInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
            placeholder="종목코드 (예: 005930)"
            maxLength={6}
            className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-gray-500"
          />
          <button
            onClick={handleAdd}
            className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs text-gray-200 transition-colors shrink-0"
          >
            추가
          </button>
        </div>
        {addError && <p className="text-[10px] text-red-400 mt-1">{addError}</p>}
      </div>
    </aside>
  )
}
