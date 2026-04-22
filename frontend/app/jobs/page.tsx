'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Play, Pause, Trash2, RefreshCw, Clock, CheckCircle2, XCircle } from 'lucide-react'

interface Job {
  id: string
  name: string
  status: 'running' | 'completed' | 'failed' | 'queued'
  progress: number
  startTime: string
  duration?: string
  tests: number
  passed: number
  failed: number
}

export default function JobsPage() {
  const [jobs] = useState<Job[]>([
    {
      id: '1',
      name: 'Full Regression Suite',
      status: 'running',
      progress: 65,
      startTime: '2 min ago',
      tests: 150,
      passed: 97,
      failed: 0,
    },
    {
      id: '2',
      name: 'Login Flow Tests',
      status: 'completed',
      progress: 100,
      startTime: '15 min ago',
      duration: '4m 23s',
      tests: 25,
      passed: 24,
      failed: 1,
    },
    {
      id: '3',
      name: 'Payment Integration',
      status: 'queued',
      progress: 0,
      startTime: 'In queue',
      tests: 50,
      passed: 0,
      failed: 0,
    },
    {
      id: '4',
      name: 'API Endpoint Tests',
      status: 'failed',
      progress: 45,
      startTime: '1 hour ago',
      duration: '2m 15s',
      tests: 80,
      passed: 36,
      failed: 44,
    },
  ])

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-primary" />
      case 'failed':
        return <XCircle className="w-5 h-5 text-destructive" />
      case 'running':
        return <RefreshCw className="w-5 h-5 text-accent animate-spin" />
      default:
        return <Clock className="w-5 h-5 text-muted-foreground" />
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold">Job Monitor</h1>
          <p className="text-muted-foreground">Track and manage test execution jobs</p>
        </div>
        <Button className="gap-2">
          <Play className="w-4 h-4" />
          New Job
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Jobs</CardTitle>
            <RefreshCw className="h-4 w-4 text-accent" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">2</div>
            <p className="text-xs text-muted-foreground">1 running, 1 queued</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">48</div>
            <p className="text-xs text-muted-foreground">This week</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed</CardTitle>
            <XCircle className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">3</div>
            <p className="text-xs text-muted-foreground">Success rate: 94.1%</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Duration</CardTitle>
            <Clock className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">3m 12s</div>
            <p className="text-xs text-muted-foreground">Per test suite</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Jobs Queue</CardTitle>
          <CardDescription>Active and queued test execution jobs</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {jobs.map((job) => (
              <div key={job.id} className="border border-border rounded-lg p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3 flex-1">
                    {getStatusIcon(job.status)}
                    <div>
                      <p className="font-medium">{job.name}</p>
                      <p className="text-xs text-muted-foreground">Started {job.startTime}</p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {job.status === 'running' && (
                      <>
                        <Button size="sm" variant="ghost" className="h-8 w-8 p-0">
                          <Pause className="w-4 h-4" />
                        </Button>
                      </>
                    )}
                    {job.status !== 'running' && (
                      <Button size="sm" variant="ghost" className="h-8 w-8 p-0">
                        <Play className="w-4 h-4" />
                      </Button>
                    )}
                    <Button size="sm" variant="ghost" className="h-8 w-8 p-0 text-destructive">
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                <div className="mb-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium">Progress</span>
                    <span className="text-xs text-muted-foreground">{job.progress}%</span>
                  </div>
                  <div className="w-full bg-secondary rounded-full h-2">
                    <div
                      className="bg-primary h-2 rounded-full transition-all"
                      style={{ width: `${job.progress}%` }}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground text-xs">Total</p>
                    <p className="font-medium">{job.tests}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Passed</p>
                    <p className="font-medium text-primary">{job.passed}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Failed</p>
                    <p className="font-medium text-destructive">{job.failed}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Duration</p>
                    <p className="font-medium">{job.duration || '-'}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
