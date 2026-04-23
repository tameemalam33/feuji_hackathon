'use client'

import { useState, useRef, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Send, Loader2, Zap, AlertCircle, CheckCircle2, Clock } from 'lucide-react'
import { ExpandableSection } from '@/components/expandable-section'

interface RootCauseAnalysis {
  explanation: string
  cause: string
  fix: string
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  analysis?: RootCauseAnalysis
}

export default function InsightsPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hello! I&apos;m your AI assistant. Ask me about test failures, performance issues, or error analysis. I&apos;ll provide detailed root cause analysis and actionable solutions.',
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/ai/explain-error`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ errorMessage: input }),
      })

      if (response.ok) {
        const data = await response.json()
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.explanation || 'Analysis complete',
          analysis: {
            explanation: data.explanation || '',
            cause: data.cause || '',
            fix: data.fix || '',
          },
        }
        setMessages((prev) => [...prev, assistantMessage])
      }
    } catch (error) {
      console.error('Error:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">AI Insights</h1>
        <p className="text-muted-foreground">Get intelligent analysis and recommendations for your tests</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card className="h-[600px] flex flex-col">
            <CardHeader>
              <CardTitle>AI Assistant</CardTitle>
              <CardDescription>Ask about errors, performance, or test failures</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col overflow-hidden bg-gradient-to-b from-background to-accent/5">
              <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-4">
                {messages.map((message) => (
                  <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    {message.role === 'user' ? (
                      <div className="max-w-xs lg:max-w-md rounded-2xl px-4 py-3 bg-blue-600 text-white shadow-md">
                        <p className="text-sm">{message.content}</p>
                      </div>
                    ) : (
                      <div className="max-w-2xl space-y-3">
                        <div className="rounded-2xl px-4 py-3 bg-white border border-gray-200 shadow-sm">
                          <p className="text-sm text-gray-700">{message.content}</p>
                        </div>

                        {message.analysis && (
                          <div className="space-y-2 pl-4">
                            <ExpandableSection title="Root Cause Analysis" defaultOpen={true}>
                              <div className="space-y-3">
                                <div className="space-y-2">
                                  <div className="flex items-start gap-3">
                                    <AlertCircle className="h-5 w-5 text-orange-500 flex-shrink-0 mt-0.5" />
                                    <div className="flex-1">
                                      <p className="font-semibold text-sm text-gray-900">Cause</p>
                                      <p className="text-sm text-gray-700 mt-1">{message.analysis.cause}</p>
                                    </div>
                                  </div>
                                </div>

                                <div className="space-y-2">
                                  <div className="flex items-start gap-3">
                                    <Zap className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
                                    <div className="flex-1">
                                      <p className="font-semibold text-sm text-gray-900">Solution</p>
                                      <p className="text-sm text-gray-700 mt-1">{message.analysis.fix}</p>
                                    </div>
                                  </div>
                                </div>

                                <div className="space-y-2">
                                  <div className="flex items-start gap-3">
                                    <CheckCircle2 className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
                                    <div className="flex-1">
                                      <p className="font-semibold text-sm text-gray-900">Details</p>
                                      <p className="text-sm text-gray-700 mt-1">{message.analysis.explanation}</p>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </ExpandableSection>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
                {loading && (
                  <div className="flex justify-start">
                    <div className="rounded-2xl px-4 py-3 bg-white border border-gray-200">
                      <div className="flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                        <span className="text-sm text-gray-600">Analyzing...</span>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={scrollRef} />
              </div>

              <form onSubmit={handleSubmit} className="flex gap-2 border-t border-border pt-4">
                <Input
                  placeholder="Ask about errors, performance, or failures..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  disabled={loading}
                  className="rounded-full bg-gray-100 border-gray-300 focus:bg-white"
                />
                <Button
                  type="submit"
                  size="icon"
                  disabled={loading}
                  className="rounded-full bg-blue-600 hover:bg-blue-700 text-white flex-shrink-0"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
            <CardHeader>
              <CardTitle className="text-lg text-blue-900">Quick Prompts</CardTitle>
              <CardDescription className="text-blue-700">Ask me about common issues</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {[
                { icon: '🔌', text: 'Network timeout issue' },
                { icon: '🗄️', text: 'Database connection error' },
                { icon: '🔐', text: 'Auth failure debugging' },
                { icon: '⚡', text: 'Performance degradation' },
              ].map((issue, i) => (
                <Button
                  key={i}
                  variant="outline"
                  className="w-full justify-start text-left bg-white hover:bg-blue-50 border-blue-200 text-gray-700 h-auto py-2"
                  onClick={() => setInput(issue.text)}
                >
                  <span className="text-lg mr-2">{issue.icon}</span>
                  <span className="text-xs">{issue.text}</span>
                </Button>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Analysis History</CardTitle>
              <CardDescription>Recent error analyses</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                { title: 'Database Pool Exhaustion', time: '2 hours ago' },
                { title: 'Memory Leak Detection', time: '4 hours ago' },
                { title: 'API Rate Limiting Issue', time: '1 day ago' },
              ].map((item, i) => (
                <button
                  key={i}
                  onClick={() => setInput(item.title)}
                  className="w-full text-left p-3 rounded-lg bg-gray-50 hover:bg-blue-50 border border-gray-200 transition-colors"
                >
                  <p className="font-medium text-sm text-gray-900">{item.title}</p>
                  <div className="flex items-center gap-1 mt-1">
                    <Clock className="h-3 w-3 text-gray-400" />
                    <p className="text-xs text-gray-500">{item.time}</p>
                  </div>
                </button>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
