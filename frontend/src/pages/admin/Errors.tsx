import { useQuery } from '@tanstack/react-query'
import { adminApi } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { AlertTriangle, TrendingUp, Target } from 'lucide-react'

export default function AdminErrors() {
  const { data: errors = [], isLoading } = useQuery({
    queryKey: ['admin-errors'],
    queryFn: async () => {
      const { data } = await adminApi.getErrorSummary()
      return data
    },
  })

  return (
    <div className="space-y-6">
      {/* 错误摘要 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            错误摘要
          </CardTitle>
          <CardDescription>系统错误概览</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground">加载中...</p>
          ) : errors.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">暂无错误记录</p>
          ) : (
            <div className="space-y-4">
              {errors.map((error) => (
                <div
                  key={error.id}
                  className="flex items-center justify-between border-b pb-4 last:border-0"
                >
                  <div className="flex items-center gap-3">
                    <ErrorIcon level={error.error_level} />
                    <div>
                      <p className="font-medium">{error.message}</p>
                      <p className="text-sm text-muted-foreground">
                        类型：{error.error_type} | 分类：{error.category}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{error.count} 次</Badge>
                    <span className="text-sm text-muted-foreground">
                      {new Date(error.last_occurred).toLocaleString('zh-CN')}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 错误趋势 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            错误趋势
          </CardTitle>
          <CardDescription>最近 7 天错误数量趋势</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">
            图表功能待实现...
          </p>
        </CardContent>
      </Card>

      {/* Top 失败项目 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            Top 失败项目
          </CardTitle>
          <CardDescription>失败次数最多的 GitHub 项目</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">
            数据待实现...
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

function ErrorIcon({ level }: { level: string }) {
  const colors: Record<string, string> = {
    info: 'text-blue-500',
    warning: 'text-yellow-500',
    error: 'text-red-500',
    critical: 'text-destructive',
  }

  return (
    <AlertTriangle className={`h-6 w-6 ${colors[level] || 'text-gray-500'}`} />
  )
}
