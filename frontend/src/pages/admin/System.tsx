import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminApi } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { Users, Server, FolderTree, CheckCircle, XCircle, Activity, Save, Settings, Database, Zap, Coins } from 'lucide-react'

interface SystemConfig {
  openai_api_key: string
  openai_enabled: boolean
  openai_model: string

  volcengine_api_key: string
  volcengine_enabled: boolean
  volcengine_model: string

  alibaba_api_key: string
  alibaba_enabled: boolean
  alibaba_model: string

  deepseek_api_key: string
  deepseek_enabled: boolean
  deepseek_model: string

  ai_provider: string
  default_model: string

  max_servers_per_user: number
  max_deployments_per_day: number
  enable_registration: boolean
  enable_ai_debug: boolean
  free_tier_ai_budget_cny: number
}

export default function AdminSystem() {
  const [config, setConfig] = useState<SystemConfig | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [activeTab, setActiveTab] = useState<'ai' | 'system'>('ai')
  const queryClient = useQueryClient()

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: async () => {
      return await adminApi.getStats()
    },
  })

  const { data: systemConfig, isLoading: configLoading } = useQuery({
    queryKey: ['admin-config'],
    queryFn: async () => {
      const cfg = await adminApi.getConfig() as SystemConfig
      setConfig(cfg)
      return cfg
    },
  })

  const updateConfigMutation = useMutation({
    mutationFn: (newConfig: Partial<SystemConfig>) =>
      adminApi.updateConfig(newConfig),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-config'] })
      setIsEditing(false)
      alert('配置已保存！')
    },
    onError: (error: any) => {
      alert('保存失败：' + (error.response?.data?.detail || '未知错误'))
    },
  })

  const handleSave = () => {
    if (!config) return
    updateConfigMutation.mutate(config)
  }

  const handleCancel = () => {
    if (systemConfig) {
      setConfig(systemConfig as SystemConfig)
    }
    setIsEditing(false)
  }

  const updateConfig = (key: keyof SystemConfig, value: string | number | boolean) => {
    setConfig((prev) => prev ? { ...prev, [key]: value } : null)
  }

  if (statsLoading || configLoading) {
    return <p className="text-muted-foreground">加载中...</p>
  }

  return (
    <div className="space-y-6">
      {/* 系统统计 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="总用户数"
          value={stats?.total_users || 0}
          icon={Users}
          description="注册用户总数"
        />
        <StatCard
          title="总服务器数"
          value={stats?.total_servers || 0}
          icon={Server}
          description="托管服务器"
        />
        <StatCard
          title="总部署数"
          value={stats?.total_deployments || 0}
          icon={FolderTree}
          description="历史部署次数"
        />
        <StatCard
          title="今日 AI 成本"
          value={`¥${(stats?.ai_cost_total_today || 0).toFixed(2)}`}
          icon={Coins}
          description="AI 调用成本"
        />
      </div>

      {/* 部署统计 */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>部署成功/失败</CardTitle>
            <CardDescription>部署结果统计 (24h)</CardDescription>
          </CardHeader>
          <CardContent className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-8 w-8 text-green-600" />
              <div>
                <p className="text-2xl font-bold text-green-600">
                  {stats?.deployments_success_24h || 0}
                </p>
                <p className="text-sm text-muted-foreground">成功</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <XCircle className="h-8 w-8 text-red-600" />
              <div>
                <p className="text-2xl font-bold text-red-600">
                  {stats?.deployments_failed_24h || 0}
                </p>
                <p className="text-sm text-muted-foreground">失败</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>部署成功率</CardTitle>
            <CardDescription>过去 24 小时</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Activity className="h-8 w-8 text-primary" />
              <div>
                <p className="text-2xl font-bold">
                  {(stats?.success_rate_24h || 0).toFixed(1)}%
                </p>
                <p className="text-sm text-muted-foreground">成功率</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* AI 和系统配置 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              <div>
                <CardTitle>系统配置</CardTitle>
                <CardDescription>管理 AI Provider 和系统参数</CardDescription>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex rounded-md border">
                <button
                  className={`px-3 py-1.5 text-sm font-medium rounded-l-md ${activeTab === 'ai' ? 'bg-primary text-primary-foreground' : 'bg-background hover:bg-muted'}`}
                  onClick={() => setActiveTab('ai')}
                >
                  <Zap className="h-4 w-4 inline mr-1" />
                  AI 配置
                </button>
                <button
                  className={`px-3 py-1.5 text-sm font-medium rounded-r-md border-l ${activeTab === 'system' ? 'bg-primary text-primary-foreground' : 'bg-background hover:bg-muted'}`}
                  onClick={() => setActiveTab('system')}
                >
                  <Database className="h-4 w-4 inline mr-1" />
                  系统设置
                </button>
              </div>
              {!isEditing ? (
                <Button onClick={() => setIsEditing(true)} size="sm">
                  编辑
                </Button>
              ) : (
                <div className="flex gap-2">
                  <Button onClick={handleSave} size="sm" disabled={updateConfigMutation.isPending}>
                    <Save className="h-4 w-4 mr-1" />
                    保存
                  </Button>
                  <Button onClick={handleCancel} variant="outline" size="sm">
                    取消
                  </Button>
                </div>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {config?.openai_api_key && !config.openai_enabled && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>
                OpenAI 已配置但未启用，请检查 API Key 是否有效。
              </AlertDescription>
            </Alert>
          )}

          {/* AI Provider 配置 */}
          {activeTab === 'ai' && (
            <div className="space-y-6">
              {/* Provider 选择 */}
              <div className="p-4 bg-muted rounded-lg">
                <Label htmlFor="ai_provider">当前 Provider</Label>
                <select
                  id="ai_provider"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1"
                  value={config?.ai_provider || 'auto'}
                  onChange={(e) => updateConfig('ai_provider', e.target.value)}
                  disabled={!isEditing}
                >
                  <option value="auto">⚡ 自动负载均衡</option>
                  <option value="openai">🤖 OpenAI</option>
                  <option value="volcengine">🔥 火山引擎豆包</option>
                  <option value="alibaba">☁️ 阿里云通义千问</option>
                  <option value="deepseek">🧠 DeepSeek</option>
                </select>
                <p className="text-xs text-muted-foreground mt-2">
                  当前选择：<Badge variant={config?.ai_provider === 'auto' ? 'default' : 'secondary'}>
                    {config?.ai_provider === 'auto' ? '自动负载均衡' : config?.ai_provider}
                  </Badge>
                </p>
              </div>

              <Separator />

              {/* OpenAI */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="h-8 w-8 rounded bg-green-100 flex items-center justify-center">
                      <span className="text-lg">🤖</span>
                    </div>
                    <div>
                      <Label className="text-base">OpenAI</Label>
                      <p className="text-xs text-muted-foreground">GPT-4, GPT-3.5-Turbo</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Label htmlFor="openai_enabled" className="text-sm">启用</Label>
                    <Switch
                      id="openai_enabled"
                      checked={config?.openai_enabled ?? false}
                      onCheckedChange={(checked) => updateConfig('openai_enabled', checked)}
                      disabled={!isEditing}
                    />
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label htmlFor="openai_api_key">API Key</Label>
                    <Input
                      id="openai_api_key"
                      type="password"
                      value={config?.openai_api_key || ''}
                      onChange={(e) => updateConfig('openai_api_key', e.target.value)}
                      disabled={!isEditing}
                      placeholder="sk-..."
                    />
                  </div>
                  <div>
                    <Label htmlFor="openai_model">默认模型</Label>
                    <Input
                      id="openai_model"
                      value={config?.openai_model || 'gpt-4o-mini'}
                      onChange={(e) => updateConfig('openai_model', e.target.value)}
                      disabled={!isEditing}
                      placeholder="gpt-4o-mini"
                    />
                  </div>
                </div>
              </div>

              <Separator />

              {/* 火山引擎 */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="h-8 w-8 rounded bg-red-100 flex items-center justify-center">
                      <span className="text-lg">🔥</span>
                    </div>
                    <div>
                      <Label className="text-base">火山引擎豆包</Label>
                      <p className="text-xs text-muted-foreground">Doubao-pro, Doubao-lite</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Label htmlFor="volcengine_enabled" className="text-sm">启用</Label>
                    <Switch
                      id="volcengine_enabled"
                      checked={config?.volcengine_enabled ?? false}
                      onCheckedChange={(checked) => updateConfig('volcengine_enabled', checked)}
                      disabled={!isEditing}
                    />
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label htmlFor="volcengine_api_key">API Key</Label>
                    <Input
                      id="volcengine_api_key"
                      type="password"
                      value={config?.volcengine_api_key || ''}
                      onChange={(e) => updateConfig('volcengine_api_key', e.target.value)}
                      disabled={!isEditing}
                      placeholder="..."
                    />
                  </div>
                  <div>
                    <Label htmlFor="volcengine_model">默认模型</Label>
                    <Input
                      id="volcengine_model"
                      value={config?.volcengine_model || 'doubao-pro-32k'}
                      onChange={(e) => updateConfig('volcengine_model', e.target.value)}
                      disabled={!isEditing}
                      placeholder="doubao-pro-32k"
                    />
                  </div>
                </div>
              </div>

              <Separator />

              {/* 阿里云 */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="h-8 w-8 rounded bg-orange-100 flex items-center justify-center">
                      <span className="text-lg">☁️</span>
                    </div>
                    <div>
                      <Label className="text-base">阿里云通义千问</Label>
                      <p className="text-xs text-muted-foreground">Qwen-max, Qwen-plus</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Label htmlFor="alibaba_enabled" className="text-sm">启用</Label>
                    <Switch
                      id="alibaba_enabled"
                      checked={config?.alibaba_enabled ?? false}
                      onCheckedChange={(checked) => updateConfig('alibaba_enabled', checked)}
                      disabled={!isEditing}
                    />
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label htmlFor="alibaba_api_key">API Key</Label>
                    <Input
                      id="alibaba_api_key"
                      type="password"
                      value={config?.alibaba_api_key || ''}
                      onChange={(e) => updateConfig('alibaba_api_key', e.target.value)}
                      disabled={!isEditing}
                      placeholder="..."
                    />
                  </div>
                  <div>
                    <Label htmlFor="alibaba_model">默认模型</Label>
                    <Input
                      id="alibaba_model"
                      value={config?.alibaba_model || 'qwen-plus'}
                      onChange={(e) => updateConfig('alibaba_model', e.target.value)}
                      disabled={!isEditing}
                      placeholder="qwen-plus"
                    />
                  </div>
                </div>
              </div>

              <Separator />

              {/* DeepSeek */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="h-8 w-8 rounded bg-blue-100 flex items-center justify-center">
                      <span className="text-lg">🧠</span>
                    </div>
                    <div>
                      <Label className="text-base">DeepSeek</Label>
                      <p className="text-xs text-muted-foreground">DeepSeek-chat, DeepSeek-coder</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Label htmlFor="deepseek_enabled" className="text-sm">启用</Label>
                    <Switch
                      id="deepseek_enabled"
                      checked={config?.deepseek_enabled ?? false}
                      onCheckedChange={(checked) => updateConfig('deepseek_enabled', checked)}
                      disabled={!isEditing}
                    />
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label htmlFor="deepseek_api_key">API Key</Label>
                    <Input
                      id="deepseek_api_key"
                      type="password"
                      value={config?.deepseek_api_key || ''}
                      onChange={(e) => updateConfig('deepseek_api_key', e.target.value)}
                      disabled={!isEditing}
                      placeholder="..."
                    />
                  </div>
                  <div>
                    <Label htmlFor="deepseek_model">默认模型</Label>
                    <Input
                      id="deepseek_model"
                      value={config?.deepseek_model || 'deepseek-chat'}
                      onChange={(e) => updateConfig('deepseek_model', e.target.value)}
                      disabled={!isEditing}
                      placeholder="deepseek-chat"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 系统设置 */}
          {activeTab === 'system' && (
            <div className="space-y-6">
              {/* 用户限制 */}
              <div className="space-y-4">
                <h3 className="text-lg font-medium flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  用户限制
                </h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label htmlFor="max_servers_per_user">每用户最大服务器数</Label>
                    <Input
                      id="max_servers_per_user"
                      type="number"
                      value={config?.max_servers_per_user || 10}
                      onChange={(e) => updateConfig('max_servers_per_user', parseInt(e.target.value))}
                      disabled={!isEditing}
                    />
                  </div>
                  <div>
                    <Label htmlFor="max_deployments_per_day">每用户每日最大部署数</Label>
                    <Input
                      id="max_deployments_per_day"
                      type="number"
                      value={config?.max_deployments_per_day || 50}
                      onChange={(e) => updateConfig('max_deployments_per_day', parseInt(e.target.value))}
                      disabled={!isEditing}
                    />
                  </div>
                </div>
              </div>

              <Separator />

              {/* 功能开关 */}
              <div className="space-y-4">
                <h3 className="text-lg font-medium flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  功能开关
                </h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label htmlFor="enable_registration">开放注册</Label>
                      <p className="text-sm text-muted-foreground">允许新用户注册</p>
                    </div>
                    <Switch
                      id="enable_registration"
                      checked={config?.enable_registration ?? true}
                      onCheckedChange={(checked) => updateConfig('enable_registration', checked)}
                      disabled={!isEditing}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <Label htmlFor="enable_ai_debug">AI 排错</Label>
                      <p className="text-sm text-muted-foreground">启用 AI 智能排错功能</p>
                    </div>
                    <Switch
                      id="enable_ai_debug"
                      checked={config?.enable_ai_debug ?? true}
                      onCheckedChange={(checked) => updateConfig('enable_ai_debug', checked)}
                      disabled={!isEditing}
                    />
                  </div>
                </div>
              </div>

              <Separator />

              {/* AI 预算 */}
              <div className="space-y-4">
                <h3 className="text-lg font-medium flex items-center gap-2">
                  <Coins className="h-5 w-5" />
                  AI 预算
                </h3>
                <div>
                  <Label htmlFor="free_tier_ai_budget_cny">免费用户每日 AI 预算 (CNY)</Label>
                  <Input
                    id="free_tier_ai_budget_cny"
                    type="number"
                    step="0.1"
                    value={config?.free_tier_ai_budget_cny || 10.0}
                    onChange={(e) => updateConfig('free_tier_ai_budget_cny', parseFloat(e.target.value))}
                    disabled={!isEditing}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    免费用户每天的 AI 调用预算上限，超出后将无法使用 AI 功能
                  </p>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function StatCard({
  title,
  value,
  icon: Icon,
  description,
}: {
  title: string
  value: number | string
  icon: React.ElementType
  description: string
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <p className="text-xs text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  )
}
