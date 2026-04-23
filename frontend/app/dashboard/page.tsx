'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { TrendingUp, AlertCircle, CheckCircle, Clock } from 'lucide-react'
import { Gauge } from '@/components/gauge'
import { LatencyChart } from '@/components/latency-chart'
import { TopIssues } from '@/components/top-issues'

const metricData = [
  { name: 'Mon', tests: 45, passed: 40, failed: 5 },
  { name: 'Tue', tests: 52, passed: 48, failed: 4 },
  { name: 'Wed', tests: 48, passed: 45, failed: 3 },
  { name: 'Thu', tests: 61, passed: 58, failed: 3 },
  { name: 'Fri', tests: 55, passed: 52, failed: 3 },
  { name: 'Sat', tests: 38, passed: 36, failed: 2 },
  { name: 'Sun', tests: 42, passed: 40, failed: 2 },
]

const latencyData = [
  { time: '00:00', p95: 120, p99: 180 },
  { time: '04:00', p95: 135, p99: 195 },
  { time: '08:00', p95: 145, p99: 220 },
  { time: '12:00', p95: 165, p99: 280 },
  { time: '16:00', p95: 155, p99: 240 },
  { time: '20:00', p95: 140, p99: 210 },
  { time: '23:59', p95: 125, p99: 185 },
]

const topIssues = [
  { id: 1, title: 'Slow API Endpoint', severity: 'critical' as const, type: 'slowdown' as const, affectedTests: 12, firstSeen: '2 hours ago' },
  { id: 2, title: 'Database Connection Timeout', severity: 'high' as const, type: 'error' as const, affectedTests: 8, firstSeen: '30 min ago' },
  { id: 3, title: 'Memory Leak in Cache', severity: 'high' as const, type: 'crash' as const, affectedTests: 5, firstSeen: '1 hour ago' },
]

export default function DashboardPage() {
  return (
    <div className="p-6 space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Welcome back. Here&apos;s your performance overview.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Tests</CardTitle>
            <CheckCircle className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">341</div>
            <p className="text-xs text-muted-foreground">+12.5% from last week</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pass Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">94.3%</div>
            <p className="text-xs text-muted-foreground">+2.1% improvement</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed Tests</CardTitle>
            <AlertCircle className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">19</div>
            <p className="text-xs text-muted-foreground">-5 from yesterday</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Duration</CardTitle>
            <Clock className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">2.4s</div>
            <p className="text-xs text-muted-foreground">Per test</p>
          </CardContent>
        </Card>

        <Card className="flex items-center justify-center">
          <CardContent className="pt-6">
            <Gauge value={87} max={100} label="Performance Score" />
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>P95 Latency</CardTitle>
            <CardDescription>95th percentile response time with anomaly detection</CardDescription>
          </CardHeader>
          <CardContent>
            <LatencyChart data={latencyData} title="P95 Latency" p95Key="p95" p99Key="p99" anomalies={[3]} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>P99 Latency</CardTitle>
            <CardDescription>99th percentile response time over 24 hours</CardDescription>
          </CardHeader>
          <CardContent>
            <LatencyChart data={latencyData} title="P99 Latency" p95Key="p95" p99Key="p99" anomalies={[3, 5]} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Weekly Performance</CardTitle>
          <CardDescription>Tests executed and pass/fail breakdown</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={metricData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="passed" fill="#2563eb" />
              <Bar dataKey="failed" fill="#dc2626" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <TopIssues issues={topIssues} />
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Recent Jobs</CardTitle>
            <CardDescription>Latest test executions</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center justify-between py-2 border-b last:border-0">
                  <div>
                    <p className="font-sm font-medium">Test Run #{i}</p>
                    <p className="text-xs text-muted-foreground">2 hours ago</p>
                  </div>
                  <span className="px-2 py-1 rounded bg-primary/10 text-primary text-xs font-medium">
                    Completed
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
