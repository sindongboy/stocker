'use client'

import { useEffect, useRef, useState } from 'react'

export interface PriceData {
  ticker: string
  price: number
  change: number
  change_pct: number
  volume: number
  timestamp: string
}

export type ConnectionStatus = 'connecting' | 'open' | 'closed'

type PriceFeed = Record<string, PriceData>

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:7878/api/v1/market/ws'

export function usePriceFeed(tickers: string[]): {
  feed: PriceFeed
  status: ConnectionStatus
} {
  const [feed, setFeed] = useState<PriceFeed>({})
  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<number | null>(null)
  const tickerKey = tickers.join(',')

  useEffect(() => {
    if (tickers.length === 0) {
      setStatus('closed')
      return
    }

    let cancelled = false

    function connect() {
      if (cancelled) return
      setStatus('connecting')

      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        setStatus('open')
        ws.send(JSON.stringify({ tickers }))
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data as string)
          if (data.ping) return
          setFeed((prev) => ({ ...prev, ...data }))
        } catch {
          // ignore malformed frames
        }
      }

      ws.onerror = () => ws.close()

      ws.onclose = () => {
        setStatus('closed')
        if (cancelled) return
        reconnectTimerRef.current = window.setTimeout(connect, 3000)
      }
    }

    connect()

    return () => {
      cancelled = true
      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current)
        reconnectTimerRef.current = null
      }
      wsRef.current?.close()
      wsRef.current = null
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tickerKey])

  return { feed, status }
}
