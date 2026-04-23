'use client'

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ScatterChart, Scatter } from 'recharts'

interface LatencyChartProps {
  data: any[]
  title: string
  p95Key: string
  p99Key: string
  anomalies?: number[]
}

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload
    return (
      <div className="bg-slate-900 text-white p-3 rounded-lg shadow-lg border border-slate-700">
        <p className="font-semibold text-sm">{data.time}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} style={{ color: entry.color }} className="text-xs">
            {entry.name}: {entry.value.toFixed(2)}ms
          </p>
        ))}
      </div>
    )
  }
  return null
}

export function LatencyChart({ data, title, p95Key, p99Key, anomalies = [] }: LatencyChartProps) {
  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
          <defs>
            <linearGradient id="colorP95" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorP99" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="time" stroke="#888" />
          <YAxis stroke="#888" label={{ value: 'Latency (ms)', angle: -90, position: 'insideLeft' }} />
          <Tooltip content={<CustomTooltip />} />
          <Line type="monotone" dataKey={p95Key} stroke="#3b82f6" dot={false} name="P95" isAnimationActive={false} />
          <Line type="monotone" dataKey={p99Key} stroke="#ef4444" dot={false} name="P99" isAnimationActive={false} />
          {anomalies.length > 0 && (
            <Scatter name="Anomalies" data={anomalies.map((idx) => data[idx])} fill="#ff6b6b" shape="circle" />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
