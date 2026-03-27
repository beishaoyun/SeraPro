import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { serversApi, deploymentsApi } from '@/lib/api'
import type { Deployment, DeploymentCreate, DeploymentStep } from '@/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Plus, Square, RotateCcw, Terminal, CheckCircle, XCircle, Loader2, MessageSquare, AlertCircle } from 'lucide-react'
import { useDeploymentWebSocket, type WebSocketMessage } from '@/hooks/useDeploymentWebSocket'
import { AIChatDialog } from '@/components/AIChatDialog'
import { Alert, AlertDescription } from '@/components/ui/alert'

export default function Deployments() {
  const queryClient = useQueryClient()
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [selectedDeployment, setSelectedDeployment] = useState<Deployment | null>(null)
  const [showChatDialog, setShowChatDialog] = useState(false)
  const [deploymentLogs, setDeploymentLogs] = useState<DeploymentStep[]>([])
  const [formError, setFormError] = useState<string | null>(null)
  const [newDeployment, setNewDeployment] = useState<DeploymentCreate>({
    server_id: 0,
    github_url: '',
    service_type: '',
  })

  const { data: servers = [] } = useQuery({
    queryKey: ['servers'],
    queryFn: async () => {
      const { data } = await serversApi.list()
      return data
    },
  })

  const { data: deployments = [], isLoading, refetch } = useQuery({
    queryKey: ['deployments'],
    queryFn: async () => {
      const { data } = await deploymentsApi.list()
      return data
    },
  })

  // WebSocket for real-time logs
  useDeploymentWebSocket(selectedDeployment?.id || null, {
    onMessage: (message: WebSocketMessage) => {
      if (message.type === 'step_log' && message.log) {
        const log = message.log
        setDeploymentLogs((prev) => {
          const existingIndex = prev.findIndex((s) => s.step_number === log.step_number)
          const newStep: DeploymentStep = {
            id: Date.now(),
            deployment_id: selectedDeployment!.id,
            step_number: log.step_number,
            description: log.description,
            command: log.command,
            status: log.status as 'pending' | 'running' | 'success' | 'failed' | 'skipped',
            output: log.output,
            error_message: log.error_message,
            duration_ms: log.duration_ms,
            created_at: new Date().toISOString(),
          }
          if (existingIndex >= 0) {
            const updated = [...prev]
            updated[existingIndex] = newStep
            return updated
          }
          return [...prev, newStep]
        })
      } else if (message.type === 'deployment_complete') {
        setTimeout(() => refetch(), 1000)
      }
    },
    onDisconnect: () => {
      setTimeout(() => refetch(), 2000)
    },
  })

  const createMutation = useMutation({
    mutationFn: (data: DeploymentCreate) => deploymentsApi.create(data),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['deployments'] })
      setShowCreateForm(false)
      setFormError(null)
      setNewDeployment({ server_id: 0, github_url: '', service_type: '' })
      setSelectedDeployment(response.data)
      setDeploymentLogs([])
      alert('部署任务已创建！正在初始化...')
    },
    onError: (error: any) => {
      setFormError(error.response?.data?.detail || '创建部署失败，请检查输入')
    },
  })

  const retryMutation = useMutation({
    mutationFn: (id: number) => deploymentsApi.retry(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deployments'] })
    },
  })

  const cancelMutation = useMutation({
    mutationFn: (id: number) => deploymentsApi.cancel(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deployments'] })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    if (!newDeployment.server_id || newDeployment.server_id === 0) {
      setFormError('请选择服务器')
      return
    }
    if (!newDeployment.github_url) {
      setFormError('请输入 GitHub 项目地址')
      return
    }

    createMutation.mutate(newDeployment)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">部署历史</h1>
          <p className="text-muted-foreground">查看和管理部署记录</p>
        </div>
        <Button onClick={() => setShowCreateForm(!showCreateForm)}>
          <Plus className="mr-2 h-4 w-4" />
          新建部署
        </Button>
      </div>

      {/* 实时日志视图 */}
      {selectedDeployment && !showChatDialog && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Terminal className="h-5 w-5" />
                  部署实时日志 - {selectedDeployment.github_repo_name || selectedDeployment.github_url}
                </CardTitle>
                <CardDescription>
                  步骤 {selectedDeployment.current_step}/{selectedDeployment.total_steps} | 状态：{selectedDeployment.status}
                </CardDescription>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setSelectedDeployment(null)
                  setDeploymentLogs([])
                }}
              >
                关闭
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-[600px] overflow-y-auto font-mono text-sm">
              {deploymentLogs.length === 0 ? (
                <p className="text-muted-foreground">等待部署开始...</p>
              ) : (
                deploymentLogs.map((log) => (
                  <div key={log.id} className="rounded-md border p-3">
                    <div className="flex items-center gap-2">
                      {log.status === 'success' && (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      )}
                      {log.status === 'failed' && (
                        <XCircle className="h-4 w-4 text-red-600" />
                      )}
                      {log.status === 'running' && (
                        <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                      )}
                      <span className="font-medium">步骤 {log.step_number}: {log.description}</span>
                    </div>
                    {log.command && (
                      <pre className="mt-2 bg-muted p-2 rounded text-xs overflow-x-auto">
                        <code>{log.command}</code>
                      </pre>
                    )}
                    {log.output && (
                      <pre className="mt-2 bg-muted p-2 rounded text-xs overflow-x-auto whitespace-pre-wrap">
                        {log.output}
                      </pre>
                    )}
                    {log.error_message && (
                      <pre className="mt-2 bg-destructive/10 p-2 rounded text-xs overflow-x-auto text-destructive">
                        {log.error_message}
                      </pre>
                    )}
                    {log.duration_ms && (
                      <p className="mt-1 text-xs text-muted-foreground">耗时：{log.duration_ms}ms</p>
                    )}
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* AI 对话排错 */}
      {showChatDialog && selectedDeployment && (
        <AIChatDialog
          deploymentId={selectedDeployment.id}
          deploymentStatus={selectedDeployment.status}
          onClose={() => setShowChatDialog(false)}
        />
      )}

      {/* 创建部署表单 */}
      {showCreateForm && (
        <Card>
          <CardHeader>
            <CardTitle>创建新部署</CardTitle>
            <CardDescription>输入 GitHub 项目地址开始部署</CardDescription>
          </CardHeader>
          <CardContent>
            {formError && (
              <Alert variant="destructive" className="mb-4">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            )}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="text-sm font-medium">选择服务器</label>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={newDeployment.server_id}
                  onChange={(e) =>
                    setNewDeployment({ ...newDeployment, server_id: parseInt(e.target.value) })
                  }
                  required
                >
                  <option value="">请选择服务器</option>
                  {servers.map((s: { id: number; name: string }) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium">GitHub 项目地址</label>
                <Input
                  value={newDeployment.github_url}
                  onChange={(e) =>
                    setNewDeployment({ ...newDeployment, github_url: e.target.value })
                  }
                  placeholder="https://github.com/owner/repo"
                  required
                />
              </div>
              <div>
                <label className="text-sm font-medium">
                  服务类型 <span className="text-muted-foreground">(可选)</span>
                </label>
                <Input
                  value={newDeployment.service_type}
                  onChange={(e) =>
                    setNewDeployment({ ...newDeployment, service_type: e.target.value })
                  }
                  placeholder="web, database, proxy 等"
                />
              </div>
              <div className="flex gap-2">
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? '创建中...' : '创建部署'}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowCreateForm(false)}
                >
                  取消
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* 部署列表 */}
      <Card>
        <CardHeader>
          <CardTitle>部署记录</CardTitle>
          <CardDescription>查看所有部署历史</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground">加载中...</p>
          ) : deployments.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">
              暂无部署记录，点击"新建部署"开始
            </p>
          ) : (
            <div className="space-y-4">
              {deployments.map((deployment) => (
                <DeploymentItem
                  key={deployment.id}
                  deployment={deployment}
                  onRetry={() => retryMutation.mutate(deployment.id)}
                  onCancel={() => cancelMutation.mutate(deployment.id)}
                  onViewLogs={() => {
                    setSelectedDeployment(deployment)
                    setDeploymentLogs([])
                  }}
                  onChat={() => {
                    setSelectedDeployment(deployment)
                    setShowChatDialog(true)
                  }}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function DeploymentItem({
  deployment,
  onRetry,
  onCancel,
  onViewLogs,
  onChat,
}: {
  deployment: Deployment
  onRetry: () => void
  onCancel: () => void
  onViewLogs: () => void
  onChat: () => void
}) {
  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'success' | 'destructive' | 'warning' | 'secondary'> = {
      success: 'success',
      running: 'default',
      pending: 'warning',
      failed: 'destructive',
      cancelled: 'secondary',
    }
    const texts: Record<string, string> = {
      success: '成功',
      running: '进行中',
      pending: '等待中',
      failed: '失败',
      cancelled: '已取消',
    }
    return <Badge variant={variants[status] || 'secondary'}>{texts[status] || status}</Badge>
  }

  return (
    <div className="flex items-center justify-between border-b pb-4 last:border-0">
      <div className="flex-1 cursor-pointer" onClick={onViewLogs}>
        <div className="flex items-center gap-2">
          <p className="font-medium hover:underline">{deployment.github_repo_name || deployment.github_url}</p>
          {getStatusBadge(deployment.status)}
        </div>
        <p className="text-sm text-muted-foreground">
          步骤 {deployment.current_step}/{deployment.total_steps} -{' '}
          {new Date(deployment.created_at).toLocaleString('zh-CN')}
        </p>
      </div>
      <div className="flex gap-2">
        {deployment.status === 'failed' && (
          <Button size="sm" variant="outline" onClick={onRetry}>
            <RotateCcw className="mr-1 h-4 w-4" />
            重试
          </Button>
        )}
        {deployment.status === 'running' && (
          <Button size="sm" variant="destructive" onClick={onCancel}>
            <Square className="mr-1 h-4 w-4" />
            取消
          </Button>
        )}
        {(deployment.status === 'failed' || deployment.status === 'running') && (
          <Button size="sm" variant="outline" onClick={onChat} title="AI 排错">
            <MessageSquare className="h-4 w-4" />
          </Button>
        )}
        {(deployment.status === 'running' || deployment.status === 'failed') && (
          <Button size="sm" variant="outline" onClick={onViewLogs}>
            <Terminal className="mr-1 h-4 w-4" />
            日志
          </Button>
        )}
      </div>
    </div>
  )
}
