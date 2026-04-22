import type { Metadata } from 'next'
import { Sidebar } from '@/components/layout/sidebar'
import { TopNav } from '@/components/layout/topnav'
import './globals.css'

export const metadata: Metadata = {
  title: 'AutoQA Pro - Performance Analytics',
  description: 'Advanced SaaS platform for QA performance analysis and insights',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <div className="flex h-screen bg-background">
          <Sidebar />
          <div className="flex-1 flex flex-col">
            <TopNav />
            <main className="flex-1 overflow-auto bg-background">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  )
}
