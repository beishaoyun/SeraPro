import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { serversApi } from '@/lib/api'
import type { Server } from '@/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Plus, Trash2, RefreshCw, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'

export default function Servers() {
  const queryClient = useQueryClient()
  const [showAddForm, setShowAddForm] = useState(false)
  const [testResult, setTestResult] = useState<{ [key: number]: { success: boolean; message: string } }>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [newServer, setNewServer] = useState({
    name: '',
    host: '',
    port: 22,
    username: 'root',
    password: '',
    os_type: 'ubuntu',
    os_version: '22.04',
  })

  const { data: servers = [], isLoading } = useQuery({
    queryKey: ['servers'],
    queryFn: async () => {
      const { data } = await serversApi.list()
      return data
    },
  })

  const addMutation = useMutation({
    mutationFn: (data: typeof newServer) => serversApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['servers'] })
      setShowAddForm(false)
      setFormError(null)
      setNewServer({
        name: '',
        host: '',
        port: 22,
        username: 'root',
        password: '',
        os_type: 'ubuntu',
        os_version: '22.04',
      })
      alert('服务器添加成功！')
    },
    onError: (error: any) => {
      setFormError(error.response?.data?.detail || '添加失败，请检查输入')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => serversApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['servers'] })
    },
  })

  const testMutation = useMutation({
    mutationFn: async (id: number) => {
      const result = await serversApi.testConnection(id)
      setTestResult(prev => ({ ...prev, [id]: { success: result.data.success, message: result.data.message } }))
      return result
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    // 验证密码
    if (!newServer.password || newServer.password.length < 1) {
      setFormError('SSH 密码不能为空')
      return
    }

    addMutation.mutate(newServer)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">服务器</h1>
          <p className="text-muted-foreground">管理您的托管服务器</p>
        </div>
        <Button onClick={() => setShowAddForm(!showAddForm)}>
          <Plus className="mr-2 h-4 w-4" />
          添加服务器
        </Button>
      </div>

      {/* 添加服务器表单 */}
      {showAddForm && (
        <Card>
          <CardHeader>
            <CardTitle>添加新服务器</CardTitle>
            <CardDescription>输入服务器的连接信息</CardDescription>
          </CardHeader>
          <CardContent>
            {formError && (
              <Alert variant="destructive" className="mb-4">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            )}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="text-sm font-medium">服务器名称</label>
                  <Input
                    value={newServer.name}
                    onChange={(e) =>
                      setNewServer({ ...newServer, name: e.target.value })
                    }
                    placeholder="生产服务器 1"
                    required
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">主机 IP/域名</label>
                  <Input
                    value={newServer.host}
                    onChange={(e) =>
                      setNewServer({ ...newServer, host: e.target.value })
                    }
                    placeholder="192.168.1.100"
                    required
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">SSH 端口</label>
                  <Input
                    type="number"
                    value={newServer.port}
                    onChange={(e) =>
                      setNewServer({ ...newServer, port: parseInt(e.target.value) })
                    }
                    placeholder="22"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">SSH 用户名</label>
                  <Input
                    value={newServer.username}
                    onChange={(e) =>
                      setNewServer({ ...newServer, username: e.target.value })
                    }
                    placeholder="root"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">SSH 密码</label>
                  <Input
                    type="password"
                    value={newServer.password}
                    onChange={(e) =>
                      setNewServer({ ...newServer, password: e.target.value })
                    }
                    placeholder="••••••••"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">操作系统</label>
                  <Input
                    value={newServer.os_type}
                    onChange={(e) =>
                      setNewServer({ ...newServer, os_type: e.target.value })
                    }
                    placeholder="ubuntu"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">系统版本</label>
                  <Input
                    value={newServer.os_version}
                    onChange={(e) =>
                      setNewServer({ ...newServer, os_version: e.target.value })
                    }
                    placeholder="22.04"
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <Button type="submit" disabled={addMutation.isPending}>
                  {addMutation.isPending ? '添加中...' : '添加'}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setShowAddForm(false)
                    setFormError(null)
                  }}
                >
                  取消
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* 服务器列表 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {isLoading ? (
          <p className="text-muted-foreground">加载中...</p>
        ) : servers.length === 0 ? (
          <p className="text-muted-foreground col-span-full text-center py-8">
            暂无服务器，点击上方按钮添加
          </p>
        ) : (
          servers.map((server) => (
            <ServerCard
              key={server.id}
              server={server}
              onDelete={() => deleteMutation.mutate(server.id)}
              onTest={() => testMutation.mutate(server.id)}
              isTesting={testMutation.variables === server.id}
              testResult={testResult[server.id] || null}
            />
          ))
        )}
      </div>
    </div>
  )
}

function ServerCard({
  server,
  onDelete,
  onTest,
  isTesting,
  testResult,
}: {
  server: Server
  onDelete: () => void
  onTest: () => void
  isTesting: boolean
  testResult?: { success: boolean; message: string } | null
}) {
  const handleTest = () => {
    onTest()
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle>{server.name}</CardTitle>
            <CardDescription className="flex items-center gap-2">
              {server.host}:{server.port}
            </CardDescription>
          </div>
          <Badge variant={server.status === 'active' ? 'success' : 'secondary'}>
            {server.status === 'active' ? '活跃' : '未激活'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="text-sm">
          <p className="text-muted-foreground">操作系统</p>
          <p>
            {server.os_type} {server.os_version}
          </p>
        </div>
        <div className="text-sm">
          <p className="text-muted-foreground">用户名</p>
          <p>{server.username || 'root'}</p>
        </div>
        <div className="space-y-2">
          <div className="flex gap-2">
            <Button onClick={handleTest} size="sm" variant="outline" disabled={isTesting}>
              {isTesting ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : testResult?.success ? (
                <CheckCircle className="h-4 w-4 text-green-600" />
              ) : testResult ? (
                <XCircle className="h-4 w-4 text-red-600" />
              ) : (
                <CheckCircle className="h-4 w-4" />
              )}
              {isTesting ? '测试中...' : '测试连接'}
            </Button>
            <Button onClick={onDelete} size="sm" variant="destructive">
              <Trash2 className="h-4 w-4" />
              删除
            </Button>
          </div>
          {testResult && (
            <div className={`text-sm p-2 rounded ${testResult.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
              {testResult.success ? '✅' : '❌'} {testResult.message}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
