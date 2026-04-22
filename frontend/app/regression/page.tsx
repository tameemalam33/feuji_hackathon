'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ScatterChart, Scatter } from 'recharts'
import { AlertTriangle, TrendingDown, Bug } from 'lucide-react'

const regressionData = [
  { week: 'W1', baseline: 95, current: 95, delta: 0 },
  { week: 'W2', baseline: 95, current: 94, delta: -1 },
  { week: 'W3', baseline: 95, current: 92, delta: -3 },
  { week: 'W4', baseline: 95, current: 94, delta: -1 },
  { week: 'W5', baseline: 95, current: 93, delta: -2 },
]

const failedTests = [
  { id: 1, name: 'Login Flow', severity: 'high', regression: true, trend: -15 },
  { id: 2, name: 'Payment Processing', severity: 'critical', regression: true, trend: -22 },
  { id: 3, name: 'Search Functionality', severity: 'medium', regression: false, trend: 5 },
  { id: 4, name: 'User Profile Update', severity: 'low', regression: false, trend: 2 },
  { id: 5, name: 'Export to CSV', severity: 'medium', regression: true, trend: -8 },
]

export default function RegressionPage() {
  return (
    <div className="p-6 space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">Regression Analysis</h1>
        <p className="text-muted-foreground">Track performance changes and identify regressions</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Regressions</CardTitle>
            <AlertTriangle className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">3</div>
            <p className="text-xs text-muted-foreground">Compared to baseline</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Improvement</CardTitle>
            <TrendingDown className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">-2.1%</div>
            <p className="text-xs text-muted-foreground">From W4 to W5</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Critical Issues</CardTitle>
            <Bug className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1</div>
            <p className="text-xs text-muted-foreground">Requires immediate attention</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Trend Analysis</CardTitle>
          <CardDescription>Pass rate trend over last 5 weeks</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={regressionData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="week" />
              <YAxis domain={[85, 100]} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="baseline" stroke="#2563eb" name="Baseline" />
              <Line type="monotone" dataKey="current" stroke="#dc2626" name="Current" />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Failed Tests</CardTitle>
          <CardDescription>Tests with regression detected</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 font-medium">Test Name</th>
                  <th className="text-left py-3 px-4 font-medium">Severity</th>
                  <th className="text-left py-3 px-4 font-medium">Status</th>
                  <th className="text-left py-3 px-4 font-medium">Trend</th>
                </tr>
              </thead>
              <tbody>
                {failedTests.map((test) => (
                  <tr key={test.id} className="border-b border-border hover:bg-accent/50">
                    <td className="py-3 px-4">{test.name}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          test.severity === 'critical'
                            ? 'bg-destructive/10 text-destructive'
                            : test.severity === 'high'
                            ? 'bg-orange-100 text-orange-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}
                      >
                        {test.severity}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          test.regression ? 'bg-destructive/10 text-destructive' : 'bg-green-100 text-green-800'
                        }`}
                      >
                        {test.regression ? 'Regression' : 'Stable'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className={test.trend < 0 ? 'text-destructive' : 'text-primary'}>
                        {test.trend > 0 ? '+' : ''}{test.trend}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
