export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 dark:bg-gray-900">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold">SerPro</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            服务器自动化托管平台
          </p>
        </div>
        {children}
      </div>
    </div>
  )
}
