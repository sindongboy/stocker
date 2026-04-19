'use client'

import useSWR from 'swr'

interface ReasoningEntry {
  event: string
  timestamp: string
  summary: string
  decision: string
  confidence: number
}

const fetcher = (url: string) => fetch(url).then((r) => r.json())

function fmtTime(iso: string) {
  const d = new Date(iso)
  return d.toLocaleString('ko-KR', { hour12: false })
}

export function ReasoningList() {
  const { data = [], isLoading } = useSWR<ReasoningEntry[]>(
    '/api/v1/agent/reasoning?limit=50',
    fetcher,
    { refreshInterval: 5000 }
  )

  if (isLoading) return <p className="text-gray-600 text-sm">불러오는 중…</p>
  if (data.length === 0) {
    return <p className="text-gray-600 text-sm">추론 기록이 없습니다.</p>
  }

  return (
    <div className="flex flex-col gap-2">
      {data.map((e, i) => (
        <div
          key={`${e.timestamp}-${i}`}
          className="rounded-lg border border-gray-800 bg-gray-900 p-3 flex flex-col gap-1.5"
        >
          <div className="flex items-center gap-2 text-xs">
            <span className="text-gray-500 font-mono">{fmtTime(e.timestamp)}</span>
            <span className="ml-auto text-gray-400">
              신뢰도{' '}
              <span className="font-mono text-gray-200">
                {(e.confidence * 100).toFixed(0)}%
              </span>
            </span>
          </div>
          <div className="text-sm text-gray-200">{e.decision}</div>
          <div className="text-xs text-gray-500 leading-relaxed">{e.summary}</div>
        </div>
      ))}
    </div>
  )
}
