'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Upload, File, Trash2, CheckCircle2 } from 'lucide-react'

interface UploadedFile {
  id: string
  name: string
  size: string
  uploadedAt: string
  status: 'processing' | 'completed' | 'failed'
}

export default function UploadPage() {
  const [files, setFiles] = useState<UploadedFile[]>([
    {
      id: '1',
      name: 'regression_data_2024_01.csv',
      size: '2.4 MB',
      uploadedAt: '2 hours ago',
      status: 'completed',
    },
    {
      id: '2',
      name: 'test_results_week_4.json',
      size: '1.8 MB',
      uploadedAt: '4 hours ago',
      status: 'completed',
    },
    {
      id: '3',
      name: 'performance_metrics.xlsx',
      size: '3.1 MB',
      uploadedAt: '6 hours ago',
      status: 'processing',
    },
  ])

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const uploadedFiles = e.target.files
    if (!uploadedFiles) return

    Array.from(uploadedFiles).forEach((file) => {
      const newFile: UploadedFile = {
        id: Date.now().toString(),
        name: file.name,
        size: `${(file.size / (1024 * 1024)).toFixed(2)} MB`,
        uploadedAt: 'Just now',
        status: 'processing',
      }
      setFiles((prev) => [newFile, ...prev])
    })
  }

  const deleteFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id))
  }

  return (
    <div className="p-6 space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">Data Upload</h1>
        <p className="text-muted-foreground">Upload test results and performance data for analysis</p>
      </div>

      <Card className="border-2 border-dashed border-border">
        <CardContent className="pt-6">
          <label className="flex flex-col items-center justify-center gap-4 py-8 cursor-pointer">
            <div className="p-4 rounded-lg bg-accent/10">
              <Upload className="w-8 h-8 text-accent" />
            </div>
            <div className="text-center">
              <p className="font-medium">Drop files here or click to upload</p>
              <p className="text-sm text-muted-foreground">CSV, JSON, or Excel files up to 10 MB</p>
            </div>
            <input
              type="file"
              multiple
              className="hidden"
              onChange={handleFileUpload}
              accept=".csv,.json,.xlsx,.xls"
            />
          </label>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Upload History</CardTitle>
          <CardDescription>Recently uploaded files and their processing status</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {files.map((file) => (
              <div key={file.id} className="flex items-center justify-between p-3 rounded-lg border border-border">
                <div className="flex items-center gap-3 flex-1">
                  <File className="w-5 h-5 text-muted-foreground" />
                  <div className="flex-1">
                    <p className="font-medium text-sm">{file.name}</p>
                    <p className="text-xs text-muted-foreground">{file.size} • Uploaded {file.uploadedAt}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {file.status === 'completed' && (
                    <span className="px-2 py-1 rounded text-xs font-medium bg-primary/10 text-primary flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" />
                      Completed
                    </span>
                  )}
                  {file.status === 'processing' && (
                    <span className="px-2 py-1 rounded text-xs font-medium bg-accent/10 text-accent">
                      Processing...
                    </span>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                    onClick={() => deleteFile(file.id)}
                  >
                    <Trash2 className="w-4 h-4 text-destructive" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Supported Formats</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-sm">
              <p className="font-medium mb-2">CSV Files</p>
              <p className="text-muted-foreground text-xs">Test results with columns: test_name, status, duration, timestamp</p>
            </div>
            <div className="text-sm">
              <p className="font-medium mb-2">JSON Files</p>
              <p className="text-muted-foreground text-xs">Structured test data with results and metrics</p>
            </div>
            <div className="text-sm">
              <p className="font-medium mb-2">Excel Files</p>
              <p className="text-muted-foreground text-xs">Spreadsheets with test metrics and performance data</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Processing Info</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-sm">
              <p className="font-medium mb-1">Time Required</p>
              <p className="text-muted-foreground text-xs">Usually 5-10 minutes per file</p>
            </div>
            <div className="text-sm">
              <p className="font-medium mb-1">File Size Limit</p>
              <p className="text-muted-foreground text-xs">Maximum 10 MB per upload</p>
            </div>
            <div className="text-sm">
              <p className="font-medium mb-1">Notifications</p>
              <p className="text-muted-foreground text-xs">You&apos;ll be notified when processing completes</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
