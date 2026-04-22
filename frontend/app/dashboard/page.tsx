'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { TrendingUp, AlertCircle, CheckCircle, Clock } from 'lucide-react'

const metricData = [
  { name: 'Mon', tests: 45, passed: 40, failed: 5 },
  { name: 'Tue', tests: 52, passed: 48, failed: 4 },
  { name: 'Wed', tests: 48, passed: 45, failed: 3 },
  { name: 'Thu', tests: 61, passed: 58, failed: 3 },
  { name: 'Fri', tests: 55, passed: 52, failed: 3 },
  { name: 'Sat', tests: 38, passed: 36, failed: 2 },
  { name: 'Sun', tests: 42, passed: 40, failed: 2 },
]

export default function DashboardPage() {
  return (
    <div className="p-6 space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Welcome back. Here&apos;s your performance overview.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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

        <Card>
          <CardHeader>
            <CardTitle>AI Insights</CardTitle>
            <CardDescription>Automated analysis</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="p-3 rounded-lg bg-accent/10 border border-accent/20">
                <p className="text-sm font-medium text-accent">Performance Improved</p>
                <p className="text-xs text-muted-foreground mt-1">Average test time reduced by 12%</p>
              </div>
              <div className="p-3 rounded-lg bg-accent/10 border border-accent/20">
                <p className="text-sm font-medium text-accent">New Pattern Detected</p>
                <p className="text-xs text-muted-foreground mt-1">3 tests show consistent failures</p>
              </div>
            </div>
            <Button className="w-full mt-4" variant="outline">
              View All Insights
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
