import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Stocker KR',
  description: 'Korean Stock Market AI Trading Agent',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="bg-gray-950 text-gray-100 antialiased">{children}</body>
    </html>
  )
}
