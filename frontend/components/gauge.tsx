'use client'

interface GaugeProps {
  value: number
  max?: number
  label?: string
  color?: string
}

export function Gauge({ value, max = 100, label = 'Performance', color = 'text-blue-600' }: GaugeProps) {
  const percentage = (value / max) * 100
  const getColor = () => {
    if (percentage >= 80) return 'text-green-600'
    if (percentage >= 60) return 'text-yellow-600'
    return 'text-red-600'
  }

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative w-32 h-32">
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r="54" fill="none" stroke="currentColor" strokeWidth="8" className="text-gray-200" />
          <circle
            cx="60"
            cy="60"
            r="54"
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            strokeDasharray={`${(percentage / 100) * 2 * Math.PI * 54} ${2 * Math.PI * 54}`}
            className={getColor()}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className={`text-3xl font-bold ${getColor()}`}>{value}</div>
          <div className="text-xs text-muted-foreground">{label}</div>
        </div>
      </div>
    </div>
  )
}
