'use client'

import { AlertTriangle, Bug, Zap } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface Issue {
  id: number
  title: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  type: 'crash' | 'slowdown' | 'error'
  affectedTests: number
  firstSeen: string
}

interface TopIssuesProps {
  issues: Issue[]
}

const severityConfig = {
  critical: { color: 'bg-red-100 text-red-800', icon: AlertTriangle },
  high: { color: 'bg-orange-100 text-orange-800', icon: Bug },
  medium: { color: 'bg-yellow-100 text-yellow-800', icon: AlertTriangle },
  low: { color: 'bg-blue-100 text-blue-800', icon: Zap },
}

const typeConfig = {
  crash: 'Crash',
  slowdown: 'Slowdown',
  error: 'Error',
}

export function TopIssues({ issues }: TopIssuesProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Top Issues</CardTitle>
        <CardDescription>Critical problems requiring attention</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {issues.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">No issues detected</p>
          ) : (
            issues.map((issue) => {
              const config = severityConfig[issue.severity]
              const Icon = config.icon
              return (
                <div key={issue.id} className="flex items-start gap-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50">
                  <div className={`p-2 rounded ${config.color}`}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="font-medium text-sm truncate">{issue.title}</p>
                      <Badge variant="outline" className="text-xs">
                        {typeConfig[issue.type]}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Affects {issue.affectedTests} test{issue.affectedTests !== 1 ? 's' : ''} • {issue.firstSeen}
                    </p>
                  </div>
                  <Badge className={config.color}>{issue.severity}</Badge>
                </div>
              )
            })
          )}
        </div>
      </CardContent>
    </Card>
  )
}
