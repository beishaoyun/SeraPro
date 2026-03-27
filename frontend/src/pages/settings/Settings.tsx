import { useAuthStore } from '@/store/useAuthStore'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { LogOut, User, Mail } from 'lucide-react'

export default function Settings() {
  const { user, logout } = useAuthStore()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">设置</h1>
        <p className="text-muted-foreground">管理您的账户设置</p>
      </div>

      {/* 账户信息 */}
      <Card>
        <CardHeader>
          <CardTitle>账户信息</CardTitle>
          <CardDescription>查看您的账户详情</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <Mail className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium">邮箱</p>
              <p className="text-muted-foreground">{user?.email}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <User className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium">角色</p>
              <p className="text-muted-foreground">
                {user?.role === 'admin' ? '管理员' : '普通用户'}
              </p>
            </div>
          </div>
          <div>
            <p className="text-sm font-medium">注册日期</p>
            <p className="text-muted-foreground">
              {user?.created_at && new Date(user.created_at).toLocaleDateString('zh-CN')}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* 修改密码 */}
      <Card>
        <CardHeader>
          <CardTitle>修改密码</CardTitle>
          <CardDescription>更新您的登录密码</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium">当前密码</label>
            <Input type="password" placeholder="••••••••" />
          </div>
          <div>
            <label className="text-sm font-medium">新密码</label>
            <Input type="password" placeholder="至少 8 位" />
          </div>
          <div>
            <label className="text-sm font-medium">确认新密码</label>
            <Input type="password" placeholder="再次输入新密码" />
          </div>
          <Button>更新密码</Button>
        </CardContent>
      </Card>

      {/* 危险区域 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-destructive">危险区域</CardTitle>
          <CardDescription>这些操作不可逆转，请谨慎操作</CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="destructive" onClick={() => logout()}>
            <LogOut className="mr-2 h-4 w-4" />
            退出登录
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
