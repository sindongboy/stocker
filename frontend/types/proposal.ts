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
}
