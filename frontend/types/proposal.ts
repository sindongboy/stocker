export type OrderSide = 'buy' | 'sell'
export type ProposalStatus = 'pending' | 'approved' | 'rejected'

export interface Proposal {
  id: string
  ticker: string
  name: string
  side: OrderSide
  qty: number
  price: number
  strategy: string
  reasoning: string
  status: ProposalStatus
  tier: string
  created_at: string
  fill_price: number | null
  order_no: string | null
  executed_at: string | null
}

export interface Trade {
  id: string
  proposal_id: string
  ticker: string
  name: string
  side: OrderSide
  qty: number
  fill_price: number
  realized_pnl: number
  executed_at: string
}
