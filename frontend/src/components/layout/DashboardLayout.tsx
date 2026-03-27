import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/useAuthStore'
import {
  LayoutDashboard,
  Server,
  FolderTree,
  BookOpen,
  Settings,
  LogOut,
  Shield,
  Menu,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'

export default function DashboardLayout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const navItems = [
    { href: '/', label: '概览', icon: <LayoutDashboard className="h-5 w-5" /> },
    {
      href: '/servers',
      label: '服务器',
      icon: <Server className="h-5 w-5" />,
    },
    {
      href: '/deployments',
      label: '部署历史',
      icon: <FolderTree className="h-5 w-5" />,
    },
    {
      href: '/knowledge',
      label: '知识库',
      icon: <BookOpen className="h-5 w-5" />,
    },
    {
      href: '/settings',
      label: '设置',
      icon: <Settings className="h-5 w-5" />,
    },
  ]

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50 dark:bg-gray-900">
      {/* 移动端遮罩 */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* 侧边栏 */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-30 flex w-64 transform flex-col border-r bg-white transition-transform duration-200 ease-in-out dark:bg-gray-800 lg:static lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Logo */}
        <div className="flex h-16 items-center justify-between border-b px-6">
          <Link to="/" className="text-xl font-bold">
            SerPro
          </Link>
          <button
            className="lg:hidden"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* 导航 */}
        <nav className="flex-1 overflow-y-auto px-4 py-4">
          <div className="space-y-1">
            {navItems.map((item) => (
              <Link
                key={item.href}
                to={item.href}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  location.pathname === item.href
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )}
              >
                {item.icon}
                {item.label}
              </Link>
            ))}
          </div>

          {/* 管理员入口 */}
          {user?.role === 'admin' && (
            <div className="mt-6">
              <p className="px-3 text-xs font-medium text-muted-foreground">
                管理员
              </p>
              <div className="mt-2 space-y-1">
                <Link
                  to="/admin/users"
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    location.pathname.startsWith('/admin')
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                  )}
                >
                  <Shield className="h-5 w-5" />
                  管理后台
                </Link>
              </div>
            </div>
          )}
        </nav>

        {/* 用户信息 */}
        <div className="border-t p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground">
              {user?.email?.[0]?.toUpperCase()}
            </div>
            <div className="flex-1 overflow-hidden">
              <p className="truncate text-sm font-medium">{user?.email}</p>
              <p className="truncate text-xs text-muted-foreground">
                {user?.role === 'admin' ? '管理员' : '用户'}
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="mt-3 flex w-full items-center gap-2 rounded-md border px-3 py-2 text-sm text-muted-foreground hover:bg-accent"
          >
            <LogOut className="h-4 w-4" />
            退出登录
          </button>
        </div>
      </aside>

      {/* 主内容区 */}
      <main className="flex-1 overflow-y-auto">
        {/* 顶部栏 (移动端) */}
        <header className="flex h-16 items-center justify-between border-b bg-white px-4 dark:bg-gray-800 lg:hidden">
          <button
            onClick={() => setSidebarOpen(true)}
            className="rounded-md p-2 hover:bg-accent"
          >
            <Menu className="h-5 w-5" />
          </button>
          <span className="font-medium">SerPro</span>
          <div className="w-9" />
        </header>

        {/* 页面内容 */}
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
