import { useQuery } from '@tanstack/react-query'
import { adminApi } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Users, Server, FolderTree, CheckCircle, XCircle, Activity, DollarSign } from 'lucide-react'

export default function AdminSystem() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: async () => {
      const { data } = await adminApi.getStats()
      return data
    },
  })

  if (isLoading) {
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
          title="今日 AI 调用"
          value={stats?.ai_calls_today || 0}
          icon={Activity}
          description="AI 请求次数"
        />
      </div>

      {/* 部署统计 */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>部署成功/失败</CardTitle>
            <CardDescription>部署结果统计</CardDescription>
          </CardHeader>
          <CardContent className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-8 w-8 text-green-600" />
              <div>
                <p className="text-2xl font-bold text-green-600">
                  {stats?.successful_deployments || 0}
                </p>
                <p className="text-sm text-muted-foreground">成功</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <XCircle className="h-8 w-8 text-red-600" />
              <div>
                <p className="text-2xl font-bold text-red-600">
                  {stats?.failed_deployments || 0}
                </p>
                <p className="text-sm text-muted-foreground">失败</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>AI 成本</CardTitle>
            <CardDescription>今日 AI 调用成本</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <DollarSign className="h-8 w-8 text-primary" />
              <div>
                <p className="text-2xl font-bold">
                  ¥{(stats?.ai_cost_today || 0).toFixed(2)}
                </p>
                <p className="text-sm text-muted-foreground">人民币</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 系统配置 */}
      <Card>
        <CardHeader>
          <CardTitle>系统配置</CardTitle>
          <CardDescription>管理系统配置信息</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex justify-between border-b pb-2">
            <span className="text-muted-foreground">AI Provider</span>
            <span className="font-medium">Auto (自动负载均衡)</span>
          </div>
          <div className="flex justify-between border-b pb-2">
            <span className="text-muted-foreground">数据库连接池</span>
            <span className="font-medium">10 连接</span>
          </div>
          <div className="flex justify-between border-b pb-2">
            <span className="text-muted-foreground">限流配置</span>
            <span className="font-medium">100 请求/分钟</span>
          </div>
          <div className="flex justify-between border-b pb-2">
            <span className="text-muted-foreground">Token 过期时间</span>
            <span className="font-medium">15 分钟</span>
          </div>
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
  value: number
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
