'use client'

import { useState } from 'react'

interface ScanResult {
  ticker: string
  strategy: string
  side?: string
  qty?: number
  price?: number
  blocked?: boolean
  reason?: string
  proposal_id?: string
}

interface ScanResponse {
  scanned_tickers: number
  strategies: number
  signals: number
  blocked: number
  results: ScanResult[]
}

interface Props {
  onScanComplete?: () => void
}

export function StrategyControls({ onScanComplete }: Props) {
  const [scanning, setScanning] = useState(false)
  const [last, setLast] = useState<ScanResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleScan = async () => {
    setScanning(true)
    setError(null)
    try {
      const res = await fetch('/api/v1/strategies/scan', { method: 'POST' })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        setError(body.detail ?? `오류 ${res.status}`)
        return
      }
      const data: ScanResponse = await res.json()
      setLast(data)
      onScanComplete?.()
    } catch (e) {
      setError(String(e))
    } finally {
      setScanning(false)
    }
  }

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={handleScan}
        disabled={scanning}
        className="px-3 py-1.5 rounded text-sm font-medium bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {scanning ? '스캔 중…' : '전략 스캔'}
      </button>

      {error && (
        <span className="text-xs text-red-400">{error}</span>
      )}

      {last && !error && (
        <span className="text-xs text-gray-500">
          {last.scanned_tickers}종목 × {last.strategies}전략
          {last.signals > 0 && (
            <span className="ml-1 text-yellow-400 font-medium">
              → {last.signals}개 제안
            </span>
          )}
          {last.signals === 0 && (
            <span className="ml-1 text-gray-600"> 시그널 없음</span>
          )}
        </span>
      )}
    </div>
  )
}
