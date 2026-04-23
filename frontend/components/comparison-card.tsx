'use client'

import { ArrowDown, ArrowUp, AlertTriangle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

interface ComparisonCardProps {
  title: string
  baselineValue: string | number
  currentValue: string | number
  changePercent: number
  isRegression: boolean
  unit?: string
  description?: string
}

export function ComparisonCard({
  title,
  baselineValue,
  currentValue,
  changePercent,
  isRegression,
  unit = '',
  description = 'vs baseline',
}: ComparisonCardProps) {
  return (
    <Card className={isRegression ? 'border-red-200 bg-red-50' : 'border-green-200 bg-green-50'}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-lg">{title}</CardTitle>
            <CardDescription>{description}</CardDescription>
          </div>
          {isRegression && <AlertTriangle className="h-5 w-5 text-red-600" />}
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-muted-foreground mb-1">Baseline</p>
            <p className="text-2xl font-bold text-blue-600">
              {baselineValue}
              {unit}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">Current</p>
            <p className={`text-2xl font-bold ${isRegression ? 'text-red-600' : 'text-green-600'}`}>
              {currentValue}
              {unit}
            </p>
          </div>
        </div>
        <div className="mt-4 pt-4 border-t flex items-center gap-2">
          {isRegression ? (
            <ArrowDown className="h-4 w-4 text-red-600" />
          ) : (
            <ArrowUp className="h-4 w-4 text-green-600" />
          )}
          <span className={`font-semibold ${isRegression ? 'text-red-600' : 'text-green-600'}`}>
            {isRegression ? '-' : '+'}
            {Math.abs(changePercent).toFixed(1)}%
          </span>
          <span className="text-xs text-muted-foreground">Change</span>
        </div>
      </CardContent>
    </Card>
  )
}
