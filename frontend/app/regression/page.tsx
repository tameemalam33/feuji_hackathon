'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ScatterChart, Scatter } from 'recharts'
import { AlertTriangle, TrendingDown, Bug, ArrowDown, AlertCircle } from 'lucide-react'
import { ComparisonCard } from '@/components/comparison-card'
import { Badge } from '@/components/ui/badge'

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

      <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-red-900">Performance Degraded by 2.1%</h3>
            <p className="text-sm text-red-800 mt-1">
              Pass rate dropped from 95% (baseline) to 93% (current). This regression spans 3 critical test suites.
            </p>
          </div>
        </div>
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
            <CardTitle className="text-sm font-medium">Performance Change</CardTitle>
            <ArrowDown className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">-2.1%</div>
            <p className="text-xs text-muted-foreground">From baseline to current</p>
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

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ComparisonCard
          title="Pass Rate"
          baselineValue="95%"
          currentValue="93%"
          changePercent={-2.1}
          isRegression={true}
          description="Test pass rate comparison"
        />
        <ComparisonCard
          title="Avg Response Time"
          baselineValue="245ms"
          currentValue="312ms"
          changePercent={-27.3}
          isRegression={true}
          unit="ms"
          description="API latency comparison"
        />
        <ComparisonCard
          title="Test Coverage"
          baselineValue="87%"
          currentValue="84%"
          changePercent={-3.4}
          isRegression={true}
          unit="%"
          description="Code coverage comparison"
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Timeline Comparison</CardTitle>
          <CardDescription>Pass rate trend over last 5 weeks with regression markers</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={regressionData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
              <defs>
                <linearGradient id="colorBaseline" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#2563eb" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorCurrent" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#dc2626" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#dc2626" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="week" stroke="#888" />
              <YAxis domain={[85, 100]} stroke="#888" />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                labelStyle={{ color: '#fff' }}
              />
              <Legend />
              <Line type="monotone" dataKey="baseline" stroke="#2563eb" name="Baseline" strokeWidth={2} dot={false} />
              <Line
                type="monotone"
                dataKey="current"
                stroke="#dc2626"
                name="Current"
                strokeWidth={2}
                dot={{ fill: '#dc2626', r: 4 }}
              />
              <ScatterChart>
                <Scatter name="Regression Point" data={[regressionData[2]]} fill="#ff6b6b" shape="diamond" />
              </ScatterChart>
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Regression Tests</CardTitle>
          <CardDescription>Tests showing performance degradation with visual indicators</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-gray-50">
                  <th className="text-left py-3 px-4 font-medium">Test Name</th>
                  <th className="text-left py-3 px-4 font-medium">Severity</th>
                  <th className="text-left py-3 px-4 font-medium">Status</th>
                  <th className="text-left py-3 px-4 font-medium">Change</th>
                  <th className="text-left py-3 px-4 font-medium">Action</th>
                </tr>
              </thead>
              <tbody>
                {failedTests.map((test) => (
                  <tr
                    key={test.id}
                    className={`border-b border-border hover:bg-opacity-50 ${
                      test.regression ? 'bg-red-50 hover:bg-red-100' : 'hover:bg-gray-50'
                    }`}
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        {test.regression && <AlertTriangle className="h-4 w-4 text-red-600 flex-shrink-0" />}
                        <span className="font-medium">{test.name}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <Badge
                        className={`text-xs font-medium ${
                          test.severity === 'critical'
                            ? 'bg-destructive/10 text-destructive'
                            : test.severity === 'high'
                            ? 'bg-orange-100 text-orange-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}
                      >
                        {test.severity}
                      </Badge>
                    </td>
                    <td className="py-3 px-4">
                      <Badge
                        className={`text-xs font-medium ${
                          test.regression ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                        }`}
                      >
                        {test.regression ? '⚠️ Regression' : '✓ Stable'}
                      </Badge>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        {test.trend < 0 ? (
                          <ArrowDown className="h-4 w-4 text-destructive" />
                        ) : (
                          <TrendingDown className="h-4 w-4 text-primary" />
                        )}
                        <span className={`font-semibold ${test.trend < 0 ? 'text-destructive' : 'text-primary'}`}>
                          {test.trend > 0 ? '+' : ''}{test.trend}%
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <Button size="sm" variant="outline" className="text-xs">
                        {test.regression ? 'Investigate' : 'View'}
                      </Button>
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
