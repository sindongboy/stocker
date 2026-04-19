'use client'

import type { Proposal } from '@/types/proposal'

interface Props {
  proposal: Proposal
  onAction?: (id: string, status: 'approved' | 'rejected') => Promise<void>
}

const sideLabel = { buy: '매수', sell: '매도' }
const sideColor = { buy: 'text-red-400 bg-red-950 border-red-900', sell: 'text-blue-400 bg-blue-950 border-blue-900' }
const statusBadge: Record<string, string> = {
  pending:  'bg-yellow-900 text-yellow-300 border-yellow-700',
  approved: 'bg-green-900 text-green-300 border-green-700',
  rejected: 'bg-gray-800 text-gray-500 border-gray-700',
}
const tierBadge: Record<string, string> = {
  T2: 'bg-green-950 text-green-400 border-green-800',
  T3: 'bg-yellow-950 text-yellow-400 border-yellow-800',
  T4: 'bg-red-950 text-red-400 border-red-800',
}

function fmt(n: number) {
  return n.toLocaleString('ko-KR')
}

export function ProposalRow({ proposal: p, onAction }: Props) {
  const isPending = p.status === 'pending'
  const isExecuted = p.status === 'approved' && p.fill_price != null

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-4 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`text-xs font-bold px-2 py-0.5 rounded border ${sideColor[p.side]}`}>
          {sideLabel[p.side]}
        </span>
        <span className="font-semibold text-gray-100">{p.name}</span>
        <span className="text-sm text-gray-500">{p.ticker}</span>
        <span
          className={`ml-auto text-xs px-1.5 py-0.5 rounded border font-mono ${tierBadge[p.tier] ?? 'bg-gray-800 text-gray-500 border-gray-700'}`}
          title="승인 티어"
        >
          {p.tier}
        </span>
        <span className={`text-xs px-2 py-0.5 rounded border ${statusBadge[p.status]}`}>
          {p.status}
        </span>
      </div>

      {/* Order detail */}
      <div className="flex gap-4 text-sm flex-wrap">
        <div>
          <span className="text-gray-500">수량 </span>
          <span className="font-mono text-gray-200">{fmt(p.qty)}주</span>
        </div>
        <div>
          <span className="text-gray-500">지정가 </span>
          <span className="font-mono text-gray-200">₩{fmt(p.price)}</span>
        </div>
        <div>
          <span className="text-gray-500">총액 </span>
          <span className="font-mono text-gray-200">₩{fmt(p.qty * p.price)}</span>
        </div>
        <div>
          <span className="text-gray-500">전략 </span>
          <span className="text-gray-400">{p.strategy}</span>
        </div>
      </div>

      {/* Execution result (after approval) */}
      {isExecuted && (
        <div className="flex items-center gap-3 bg-green-950 border border-green-800 rounded px-3 py-2 text-xs">
          <span className="text-green-400 font-medium">체결 완료</span>
          <span className="text-gray-400">체결가 <span className="font-mono text-green-300">₩{fmt(p.fill_price!)}</span></span>
          {p.order_no && (
            <span className="text-gray-500">주문번호 <span className="font-mono">{p.order_no}</span></span>
          )}
        </div>
      )}

      {/* Reasoning */}
      <p className="text-xs text-gray-500 leading-relaxed">{p.reasoning}</p>

      {/* Actions */}
      {isPending && onAction && (
        <div className="flex gap-2 pt-1">
          <button
            onClick={() => onAction(p.id, 'approved')}
            className="px-4 py-1.5 rounded text-sm font-medium bg-green-700 hover:bg-green-600 text-white transition-colors"
          >
            승인
          </button>
          <button
            onClick={() => onAction(p.id, 'rejected')}
            className="px-4 py-1.5 rounded text-sm font-medium bg-gray-700 hover:bg-gray-600 text-gray-200 transition-colors"
          >
            거부
          </button>
        </div>
      )}
    </div>
  )
}
