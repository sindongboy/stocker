'use client'

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

export function WatchlistPanel({ items, selected, onSelect }: Props) {
  const tickers = items.map((i) => i.ticker)
  const { feed, status } = usePriceFeed(tickers)

  return (
    <aside className="flex flex-col gap-1 h-full overflow-y-auto">
      <div className="flex items-center justify-between px-3 py-2">
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
      {items.map((item) => (
        <SnapshotRow
          key={item.ticker}
          ticker={item.ticker}
          name={item.name}
          live={feed[item.ticker]}
          selected={selected === item.ticker}
          onSelect={onSelect}
        />
      ))}
    </aside>
  )
}
