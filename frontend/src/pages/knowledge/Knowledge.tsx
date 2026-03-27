import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { knowledgeApi } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Search } from 'lucide-react'

export default function Knowledge() {
  const [query, setQuery] = useState('')
  const [osFilter, setOsFilter] = useState('')

  const { data: results = [], isLoading } = useQuery({
    queryKey: ['knowledge', query, osFilter],
    queryFn: async () => {
      const { data } = await knowledgeApi.search({
        query: query || 'web',
        os_filter: osFilter || undefined,
        limit: 20,
      })
      return data
    },
    enabled: false,
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">知识库</h1>
        <p className="text-muted-foreground">浏览和搜索部署知识库</p>
      </div>

      {/* 搜索框 */}
      <Card>
        <CardHeader>
          <CardTitle>搜索知识库</CardTitle>
          <CardDescription>搜索部署教程和常见错误</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              // 触发查询
            }}
            className="space-y-4"
          >
            <div className="flex gap-2">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="搜索关键词..."
                className="flex-1"
              />
              <Input
                value={osFilter}
                onChange={(e) => setOsFilter(e.target.value)}
                placeholder="操作系统 (可选)"
                className="w-48"
              />
              <Button type="submit">
                <Search className="mr-2 h-4 w-4" />
                搜索
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* 搜索结果 */}
      {isLoading && <p className="text-muted-foreground">搜索中...</p>}

      {results && results.length > 0 && (
        <div className="grid gap-4">
          {results.map((item) => (
            <KnowledgeCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  )
}

function KnowledgeCard({ item }: { item: {
  id: number
  github_url: string
  os_type: string
  os_version: string
  service_type: string
  deploy_steps: Array<{ step: number; description: string; command: string }>
  common_errors: Array<{ step: number; error: string }>
  success_count: number
  failure_count: number
  created_at: string
} }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-lg">
              <a
                href={item.github_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
              >
                {item.github_url}
              </a>
            </CardTitle>
            <CardDescription className="flex items-center gap-2">
              {item.os_type} {item.os_version} - {item.service_type}
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Badge variant="success">成功 {item.success_count}</Badge>
            <Badge variant="destructive">失败 {item.failure_count}</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {item.deploy_steps && item.deploy_steps.length > 0 && (
          <div className="space-y-2">
            <p className="font-medium">部署步骤:</p>
            <ol className="list-decimal list-inside space-y-1 text-sm">
              {item.deploy_steps.slice(0, 5).map((step: { step: number; description: string; command: string }, i: number) => (
                <li key={i} className="text-muted-foreground">
                  {step.description || step.command}
                </li>
              ))}
              {item.deploy_steps.length > 5 && (
                <li className="text-muted-foreground">
                  ... 还有 {item.deploy_steps.length - 5} 个步骤
                </li>
              )}
            </ol>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
