'use client'

import { Bell, Settings, User } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function TopNav() {
  return (
    <div className="h-16 bg-card border-b border-border flex items-center justify-between px-6">
      <div>
        <h2 className="text-sm text-muted-foreground">Welcome back</h2>
      </div>

      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon">
          <Bell className="w-5 h-5" />
        </Button>
        <Button variant="ghost" size="icon">
          <Settings className="w-5 h-5" />
        </Button>
        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground">
          <User className="w-4 h-4" />
        </div>
      </div>
    </div>
  )
}
