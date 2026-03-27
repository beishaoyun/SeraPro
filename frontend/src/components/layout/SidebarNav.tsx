import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'

interface SidebarNavProps {
  items: {
    href: string
    label: string
    icon: React.ReactNode
  }[]
}

export function SidebarNav({ items }: SidebarNavProps) {
  const location = useLocation()

  return (
    <nav className="flex flex-col gap-1">
      {items.map((item) => (
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
    </nav>
  )
}
