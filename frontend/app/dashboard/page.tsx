import { DashboardClient } from './DashboardClient'

interface WatchlistItem {
  ticker: string
  name: string
  market: string
}

async function fetchWatchlist(): Promise<WatchlistItem[]> {
  try {
    const res = await fetch('http://localhost:7878/api/v1/market/watchlist', {
      cache: 'no-store',
    })
    if (!res.ok) return []
    return res.json()
  } catch {
    return []
  }
}

export default async function DashboardPage() {
  const watchlist = await fetchWatchlist()
  return <DashboardClient watchlist={watchlist} />
}
