import { Outlet, Link, useLocation } from 'react-router-dom'
import { Users, Settings, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'

export default function AdminLayout() {
  const location = useLocation()

  const navItems = [
    { href: '/admin/users', label: '用户管理', icon: <Users className="h-4 w-4" /> },
    { href: '/admin/system', label: '系统配置', icon: <Settings className="h-4 w-4" /> },
    { href: '/admin/errors', label: '错误报表', icon: <AlertTriangle className="h-4 w-4" /> },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">管理后台</h1>
        <p className="text-muted-foreground">管理系统用户和配置</p>
      </div>

      {/* 管理员导航 */}
      <div className="flex gap-2 border-b pb-4">
        {navItems.map((item) => (
          <Link
            key={item.href}
            to={item.href}
            className={cn(
              'flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors',
              location.pathname === item.href
                ? 'bg-primary text-primary-foreground'
                : 'hover:bg-accent hover:text-accent-foreground'
            )}
          >
            {item.icon}
            {item.label}
          </Link>
        ))}
      </div>

      {/* 子页面内容 */}
      <Outlet />
    </div>
  )
}
