'use client'

import { useState } from 'react'
import useSWR from 'swr'
import { ProposalRow } from './ProposalRow'
import { ReasoningList } from './ReasoningList'
import type { Proposal, Trade } from '@/types/proposal'

const fetcher = (url: string) => fetch(url).then((r) => r.json())

type Tab = 'pending' | 'history' | 'trades' | 'reasoning'

function fmt(n: number) {
  return n.toLocaleString('ko-KR')
}

function TradeList() {
  const { data: trades = [], isLoading } = useSWR<Trade[]>(
    '/api/v1/agent/trades',
    fetcher,
    { refreshInterval: 5000 }
  )
  if (isLoading) return <p className="text-gray-600 text-sm">불러오는 중…</p>
  if (trades.length === 0) return <p className="text-gray-600 text-sm">체결 이력이 없습니다.</p>
  return (
    <div className="flex flex-col gap-2">
      {trades.map((t) => (
        <div key={t.id} className="rounded-lg border border-gray-800 bg-gray-900 px-4 py-3 flex flex-col gap-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-xs font-bold px-2 py-0.5 rounded border ${
              t.side === 'buy'
                ? 'text-red-400 bg-red-950 border-red-900'
                : 'text-blue-400 bg-blue-950 border-blue-900'
            }`}>
              {t.side === 'buy' ? '매수' : '매도'}
            </span>
            <span className="font-semibold text-gray-100">{t.name}</span>
            <span className="text-sm text-gray-500">{t.ticker}</span>
            <span className="ml-auto text-xs text-gray-500">
              {new Date(t.executed_at).toLocaleString('ko-KR')}
            </span>
          </div>
          <div className="flex gap-4 text-sm flex-wrap">
            <div>
              <span className="text-gray-500">수량 </span>
              <span className="font-mono text-gray-200">{fmt(t.qty)}주</span>
            </div>
            <div>
              <span className="text-gray-500">체결가 </span>
              <span className="font-mono text-gray-200">₩{fmt(t.fill_price)}</span>
            </div>
            {t.realized_pnl !== 0 && (
              <div>
                <span className="text-gray-500">실현손익 </span>
                <span className={`font-mono ${t.realized_pnl > 0 ? 'text-red-400' : 'text-blue-400'}`}>
                  {t.realized_pnl > 0 ? '+' : ''}{fmt(t.realized_pnl)}원
                </span>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

export function ProposalQueue() {
  const [tab, setTab] = useState<Tab>('pending')

  const { data: all = [], mutate, isLoading } = useSWR<Proposal[]>(
    '/api/v1/agent/proposals',
    fetcher,
    { refreshInterval: 3000 }
  )

  const pending  = all.filter((p) => p.status === 'pending')
  const history  = all.filter((p) => p.status !== 'pending')

  async function handleAction(id: string, status: 'approved' | 'rejected') {
    mutate(
      (current = []) => current.map((p) => (p.id === id ? { ...p, status } : p)),
      { revalidate: false }
    )
    await fetch(`/api/v1/agent/proposals/${id}?status=${status}`, { method: 'PATCH' })
    mutate()
  }

  const tabs: Array<{ key: Tab; label: string; count?: number }> = [
    { key: 'pending',   label: '대기 중',   count: pending.length },
    { key: 'history',   label: '처리 완료', count: history.length },
    { key: 'trades',    label: '체결 이력' },
    { key: 'reasoning', label: '추론 이력' },
  ]

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar */}
      <div className="flex items-center gap-1 border-b border-gray-800 px-4 py-2 shrink-0">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider mr-3">
          주문 제안
        </span>
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              tab === t.key
                ? 'bg-gray-800 text-gray-100'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {t.label}
            {t.count != null && t.count > 0 && (
              <span className={`ml-1.5 px-1.5 py-0.5 rounded-full text-xs ${
                t.key === 'pending' ? 'bg-yellow-700 text-yellow-200' : 'bg-gray-700 text-gray-400'
              }`}>
                {t.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
        {tab === 'reasoning' ? (
          <ReasoningList />
        ) : tab === 'trades' ? (
          <TradeList />
        ) : (
          <>
            {isLoading && <p className="text-gray-600 text-sm">불러오는 중…</p>}
            {!isLoading && (tab === 'pending' ? pending : history).length === 0 && (
              <p className="text-gray-600 text-sm">
                {tab === 'pending' ? '대기 중인 제안이 없습니다.' : '처리된 제안이 없습니다.'}
              </p>
            )}
            {(tab === 'pending' ? pending : history).map((p) => (
              <ProposalRow
                key={p.id}
                proposal={p}
                onAction={tab === 'pending' ? handleAction : undefined}
              />
            ))}
          </>
        )}
      </div>
    </div>
  )
}
