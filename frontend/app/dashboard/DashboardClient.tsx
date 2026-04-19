'use client'

import { useState, useCallback } from 'react'
import useSWR from 'swr'
import { WatchlistPanel } from '@/components/market/WatchlistPanel'
import { CandleChart } from '@/components/market/CandleChart'
import { AgentControls } from '@/components/agent/AgentControls'
import { ProposalQueue } from '@/components/agent/ProposalQueue'
import { PortfolioWidget } from '@/components/strategies/PortfolioWidget'
import { StrategyControls } from '@/components/strategies/StrategyControls'

interface WatchlistItem {
  ticker: string
  name: string
  market: string
}

const fetcher = (url: string) => fetch(url).then((r) => r.json())

export function DashboardClient() {
  const [selected, setSelected] = useState<string | null>(null)
  const [queueKey, setQueueKey] = useState(0)

  const { data: watchlist = [], mutate: mutateWatchlist } = useSWR<WatchlistItem[]>(
    '/api/v1/market/watchlist',
    fetcher,
    {
      revalidateOnFocus: false,
      onSuccess: (data) => {
        if (selected === null && data.length > 0) {
          setSelected(data[0].ticker)
        }
      },
    }
  )

  const tickers = watchlist.map((i) => i.ticker)
  const selectedItem = watchlist.find((i) => i.ticker === selected)

  const handleRunComplete = useCallback(() => {
    setQueueKey((k) => k + 1)
  }, [])

  const handleWatchlistChange = useCallback(() => {
    mutateWatchlist()
  }, [mutateWatchlist])

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-gray-100">
      {/* Top bar */}
      <div className="flex items-center gap-4 px-4 py-2 border-b border-gray-800 shrink-0">
        <AgentControls tickers={tickers} onRunComplete={handleRunComplete} />
        <div className="h-5 w-px bg-gray-800" />
        <StrategyControls onScanComplete={handleRunComplete} />
      </div>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <div className="w-56 shrink-0 border-r border-gray-800 overflow-y-auto flex flex-col">
          <div className="p-2 flex-1">
            <WatchlistPanel
              items={watchlist}
              selected={selected}
              onSelect={setSelected}
              onWatchlistChange={handleWatchlistChange}
            />
          </div>
          <PortfolioWidget />
        </div>

        {/* Main column */}
        <div className="flex flex-col flex-1 overflow-hidden">
          {/* Chart */}
          <div className="flex-[55] overflow-auto p-6 border-b border-gray-800">
            {selectedItem ? (
              <CandleChart ticker={selectedItem.ticker} name={selectedItem.name} />
            ) : (
              <div className="h-full flex items-center justify-center text-gray-600 text-sm">
                관심종목을 선택하세요
              </div>
            )}
          </div>

          {/* Proposal queue */}
          <div className="flex-[45] overflow-hidden">
            <ProposalQueue key={queueKey} />
          </div>
        </div>
      </div>
    </div>
  )
}
