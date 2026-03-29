import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '@/types'
import { authApi } from '@/lib/api'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, company?: string) => Promise<void>
  logout: () => void
  fetchUser: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: !!(typeof window !== 'undefined' && localStorage.getItem('access_token')),

      login: async (email: string, password: string) => {
        const { data } = await authApi.login({ email, password })
        localStorage.setItem('access_token', data.access_token)
        localStorage.setItem('refresh_token', data.refresh_token)
        await get().fetchUser()
      },

      register: async (email: string, password: string, company?: string) => {
        await authApi.register({ email, password, company })
        await get().login(email, password)
      },

      logout: () => {
        authApi.logout()
        set({ user: null, isAuthenticated: false, isLoading: false })
      },

      fetchUser: async () => {
        // 如果有存储的用户信息，先恢复加载状态为 false
        if (get().isAuthenticated && get().user) {
          set({ isLoading: false })
          return
        }

        // 没有 token 时，直接设置为未登录状态
        const token = localStorage.getItem('access_token')
        if (!token) {
          set({ user: null, isAuthenticated: false, isLoading: false })
          return
        }

        try {
          const { data } = await authApi.getCurrentUser()
          set({ user: data, isAuthenticated: true, isLoading: false })
        } catch {
          set({ user: null, isAuthenticated: false, isLoading: false })
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
