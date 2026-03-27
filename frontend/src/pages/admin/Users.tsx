import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminApi } from '@/lib/api'
import type { User } from '@/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Shield, UserMinus, UserCheck, KeyRound } from 'lucide-react'

export default function AdminUsers() {
  const queryClient = useQueryClient()

  const { data: users = [], isLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: async () => {
      const { data } = await adminApi.listUsers()
      return data
    },
  })

  const disableMutation = useMutation({
    mutationFn: (userId: number) => adminApi.disableUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
  })

  const enableMutation = useMutation({
    mutationFn: (userId: number) => adminApi.enableUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
  })

  const setRoleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: number; role: 'user' | 'admin' }) =>
      adminApi.setUserRole(userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
  })

  const handleResetPassword = async (user: User) => {
    const newPassword = prompt('请输入新密码:')
    if (!newPassword) return

    try {
      await adminApi.resetUserPassword(user.id, newPassword)
      alert('密码已重置')
    } catch {
      alert('重置失败')
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>用户管理</CardTitle>
        <CardDescription>管理系统所有用户</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="text-muted-foreground">加载中...</p>
        ) : users.length === 0 ? (
          <p className="text-muted-foreground text-center py-8">暂无用户</p>
        ) : (
          <div className="space-y-4">
            {users.map((user) => (
              <div
                key={user.id}
                className="flex items-center justify-between border-b pb-4 last:border-0"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground">
                    {user.email[0].toUpperCase()}
                  </div>
                  <div>
                    <p className="font-medium">{user.email}</p>
                    <p className="text-sm text-muted-foreground">
                      注册于 {new Date(user.created_at).toLocaleDateString('zh-CN')}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={user.role === 'admin' ? 'default' : 'secondary'}>
                    <Shield className="mr-1 h-3 w-3" />
                    {user.role === 'admin' ? '管理员' : '用户'}
                  </Badge>
                  <Badge variant={user.is_disabled ? 'destructive' : 'success'}>
                    {user.is_disabled ? '禁用' : '正常'}
                  </Badge>

                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleResetPassword(user)}
                  >
                    <KeyRound className="h-4 w-4" />
                  </Button>

                  {user.is_disabled ? (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => enableMutation.mutate(user.id)}
                    >
                      <UserCheck className="h-4 w-4" />
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => disableMutation.mutate(user.id)}
                    >
                      <UserMinus className="h-4 w-4" />
                    </Button>
                  )}

                  {user.role !== 'admin' && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setRoleMutation.mutate({ userId: user.id, role: 'admin' })}
                    >
                      设为管理员
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
