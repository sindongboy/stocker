'use client'

import { useState, useEffect } from 'react'

interface Props {
  tickers: string[]
  onRunComplete: () => void
}

type RunState = 'idle' | 'running' | 'done' | 'error'

export function AgentControls({ tickers, onRunComplete }: Props) {
  const [state, setState] = useState<RunState>('idle')
  const [lastResult, setLastResult] = useState<{ proposed_count: number; turns: number } | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [strategyNames, setStrategyNames] = useState<string>('로딩 중…')

  useEffect(() => {
    fetch('/api/v1/strategies/list')
      .then((r) => r.json())
      .then((data: Array<{ name: string }>) => {
        if (data.length > 0) setStrategyNames(data.map((s) => s.name).join(', '))
      })
      .catch(() => setStrategyNames('전략 조회 실패'))
  }, [])

  async function handleRun() {
    setState('running')
    setLastResult(null)
    setErrorMsg(null)
    try {
      const res = await fetch('/api/v1/agent/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tickers }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail ?? `HTTP ${res.status}`)
      }
      const data = await res.json()
      setLastResult(data)
      setState('done')
      onRunComplete()
    } catch (e) {
      console.error(e)
      setErrorMsg(e instanceof Error ? e.message : '알 수 없는 오류')
      setState('error')
    }
  }

  const isRunning = state === 'running'

  return (
    <div className="flex items-center gap-3 px-4 py-2 border-b border-gray-800 bg-gray-950 shrink-0">
      <button
        onClick={handleRun}
        disabled={isRunning}
        className={`flex items-center gap-2 px-4 py-1.5 rounded text-sm font-medium transition-colors ${
          isRunning
            ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
            : 'bg-blue-700 hover:bg-blue-600 text-white'
        }`}
      >
        {isRunning ? (
          <>
            <span className="inline-block h-3 w-3 rounded-full border-2 border-gray-500 border-t-blue-400 animate-spin" />
            분석 중…
          </>
        ) : (
          '▶ 분석 실행'
        )}
      </button>

      <span className="text-xs text-gray-500">전략: {strategyNames}</span>
      <span className="text-xs text-gray-600">종목 {tickers.length}개</span>

      {state === 'done' && lastResult && (
        <span className="text-xs text-green-400 ml-2">
          완료 — 제안 {lastResult.proposed_count}건 ({lastResult.turns}턴)
        </span>
      )}
      {state === 'error' && errorMsg && (
        <span className="text-xs text-red-400 ml-2" title={errorMsg}>
          오류: {errorMsg}
        </span>
      )}
    </div>
  )
}
