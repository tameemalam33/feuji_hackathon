'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { BarChart3, Zap, Brain, Activity, Upload, LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function Sidebar() {
  const pathname = usePathname()

  const navItems = [
    { href: '/dashboard', label: 'Dashboard', icon: BarChart3 },
    { href: '/regression', label: 'Regression Analysis', icon: Zap },
    { href: '/insights', label: 'AI Insights', icon: Brain },
    { href: '/jobs', label: 'Job Monitor', icon: Activity },
    { href: '/upload', label: 'Data Upload', icon: Upload },
  ]

  return (
    <div className="w-64 bg-card border-r border-border h-screen flex flex-col">
      <div className="p-6 border-b border-border">
        <h1 className="text-xl font-bold text-primary">AutoQA Pro</h1>
        <p className="text-xs text-muted-foreground mt-1">SaaS Analytics</p>
      </div>

      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = pathname === item.href
          return (
            <Link key={item.href} href={item.href}>
              <div
                className={cn(
                  'flex items-center gap-3 px-4 py-2.5 rounded-md text-sm font-medium transition-colors cursor-pointer',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-foreground hover:bg-accent'
                )}
              >
                <Icon className="w-5 h-5" />
                {item.label}
              </div>
            </Link>
          )
        })}
      </nav>

      <div className="p-4 border-t border-border">
        <Button variant="outline" className="w-full gap-2" size="sm">
          <LogOut className="w-4 h-4" />
          Logout
        </Button>
      </div>
    </div>
  )
}
