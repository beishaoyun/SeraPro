import { useQuery } from '@tanstack/react-query'
import { serversApi, deploymentsApi } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Server, FolderTree, CheckCircle, XCircle, TrendingUp, Activity } from 'lucide-react'
import { LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

export default function Dashboard() {
  const { data: servers = [] } = useQuery({
    queryKey: ['servers'],
    queryFn: async () => {
      const { data } = await serversApi.list()
      return data
    },
  })

  const { data: deployments = [] } = useQuery({
    queryKey: ['deployments'],
    queryFn: async () => {
      const { data } = await deploymentsApi.list({ limit: 100 })
      return data
    },
  })

  const stats = {
    totalServers: servers?.length || 0,
    totalDeployments: deployments?.length || 0,
    successfulDeployments: deployments?.filter((d) => d.status === 'success').length || 0,
    failedDeployments: deployments?.filter((d) => d.status === 'failed').length || 0,
  }

  // 部署趋势数据 - 按日期统计
  const deploymentTrendData = (() => {
    const dateMap = new Map<string, { date: string; deployments: number; success: number; failed: number }>()

    // 获取最近 7 天
    for (let i = 6; i >= 0; i--) {
      const date = new Date()
      date.setDate(date.getDate() - i)
      const dateStr = date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
      dateMap.set(dateStr, { date: dateStr, deployments: 0, success: 0, failed: 0 })
    }

    // 统计数据
    deployments.forEach((d) => {
      const date = new Date(d.created_at)
      const dateStr = date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
      const entry = dateMap.get(dateStr)
      if (entry) {
        entry.deployments += 1
        if (d.status === 'success') entry.success += 1
        if (d.status === 'failed') entry.failed += 1
      }
    })

    return Array.from(dateMap.values())
  })()

  // 部署状态分布数据
  const statusDistributionData = [
    { name: '成功', value: stats.successfulDeployments, color: '#22c55e' },
    { name: '失败', value: stats.failedDeployments, color: '#ef4444' },
    { name: '进行中', value: deployments.filter((d) => d.status === 'running').length, color: '#3b82f6' },
    { name: '等待中', value: deployments.filter((d) => d.status === 'pending').length, color: '#eab308' },
    { name: '已取消', value: deployments.filter((d) => d.status === 'cancelled').length, color: '#6b7280' },
  ].filter((item) => item.value > 0)

  // 成功率
  const successRate = stats.totalDeployments > 0
    ? Math.round((stats.successfulDeployments / stats.totalDeployments) * 100)
    : 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">概览</h1>
        <p className="text-muted-foreground">欢迎使用 SerPro 服务器自动化托管平台</p>
      </div>

      {/* 统计卡片 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="服务器"
          value={stats.totalServers}
          icon={Server}
          description="已添加的服务器"
        />
        <StatCard
          title="部署总数"
          value={stats.totalDeployments}
          icon={FolderTree}
          description="历史部署次数"
        />
        <StatCard
          title="成功部署"
          value={stats.successfulDeployments}
          icon={CheckCircle}
          description="成功的部署次数"
          className="text-green-600"
        />
        <StatCard
          title="失败部署"
          value={stats.failedDeployments}
          icon={XCircle}
          description="失败的部署次数"
          className="text-red-600"
        />
      </div>

      {/* 图表区域 */}
      {deployments.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2">
          {/* 部署趋势图 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                部署趋势 (最近 7 天)
              </CardTitle>
              <CardDescription>每日部署次数及成功/失败分布</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={deploymentTrendData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="deployments" name="总部署" stroke="#3b82f6" strokeWidth={2} />
                  <Line type="monotone" dataKey="success" name="成功" stroke="#22c55e" strokeWidth={2} />
                  <Line type="monotone" dataKey="failed" name="失败" stroke="#ef4444" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* 状态分布图 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                部署状态分布
              </CardTitle>
              <CardDescription>成功率：{successRate}%</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={statusDistributionData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {statusDistributionData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex flex-wrap gap-4 justify-center mt-4">
                {statusDistributionData.map((item) => (
                  <div key={item.name} className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-sm text-muted-foreground">
                      {item.name}: {item.value}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 最近部署 */}
      <Card>
        <CardHeader>
          <CardTitle>最近部署</CardTitle>
          <CardDescription>查看最近的部署记录</CardDescription>
        </CardHeader>
        <CardContent>
          {deployments && deployments.length > 0 ? (
            <div className="space-y-4">
              {deployments.slice(0, 5).map((deployment) => (
                <div
                  key={deployment.id}
                  className="flex items-center justify-between border-b pb-4 last:border-0"
                >
                  <div>
                    <p className="font-medium">{deployment.github_repo_name || deployment.github_url}</p>
                    <p className="text-sm text-muted-foreground">
                      {new Date(deployment.created_at).toLocaleString('zh-CN')}
                    </p>
                  </div>
                  <StatusBadge status={deployment.status} />
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-muted-foreground py-8">
              暂无部署记录
            </p>
          )}
        </CardContent>
      </Card>

      {/* 快速操作 */}
      <Card>
        <CardHeader>
          <CardTitle>快速操作</CardTitle>
          <CardDescription>常用功能快捷入口</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <QuickAction
            title="添加服务器"
            description="添加新的托管服务器"
            href="/servers"
          />
          <QuickAction
            title="创建部署"
            description="从 GitHub 项目创建部署"
            href="/deployments"
          />
          <QuickAction
            title="查看知识库"
            description="浏览部署知识库"
            href="/knowledge"
          />
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
  className = '',
}: {
  title: string
  value: number
  icon: React.ElementType
  description: string
  className?: string
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold ${className}`}>{value}</div>
        <p className="text-xs text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  )
}

function QuickAction({
  title,
  description,
  href,
}: {
  title: string
  description: string
  href: string
}) {
  return (
    <a
      href={href}
      className="flex flex-col items-start rounded-lg border p-4 transition-colors hover:bg-accent"
    >
      <h3 className="font-medium">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </a>
  )
}

function StatusBadge({ status }: { status: string }) {
  const statusColors: Record<string, string> = {
    success: 'bg-green-100 text-green-800',
    running: 'bg-blue-100 text-blue-800',
    pending: 'bg-yellow-100 text-yellow-800',
    failed: 'bg-red-100 text-red-800',
    cancelled: 'bg-gray-100 text-gray-800',
  }

  const statusTexts: Record<string, string> = {
    success: '成功',
    running: '进行中',
    pending: '等待中',
    failed: '失败',
    cancelled: '已取消',
  }

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
        statusColors[status] || 'bg-gray-100 text-gray-800'
      }`}
    >
      {statusTexts[status] || status}
    </span>
  )
}
