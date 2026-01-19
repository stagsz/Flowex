import { create } from "zustand"
import { persist } from "zustand/middleware"
import * as Sentry from "@sentry/react"

export interface User {
  id: string
  email: string
  name: string
  avatar?: string
  role: "viewer" | "editor" | "admin" | "owner"
  organizationId: string
  organizationName: string
}

interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  error: string | null
  login: () => void
  logout: () => void
  setUser: (user: User | null) => void
  setToken: (token: string | null) => void
  setError: (error: string | null) => void
  checkAuth: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isLoading: false,
      error: null,

      login: () => {
        // Redirect to Auth0 login
        window.location.href = "/api/auth/login"
      },

      logout: async () => {
        try {
          await fetch("/api/auth/logout", { method: "POST" })
        } catch {
          // Ignore errors on logout
        }
        // Clear Sentry user context on logout
        Sentry.setUser(null)
        set({ user: null, token: null })
        window.location.href = "/"
      },

      setUser: (user) => set({ user }),
      setToken: (token) => set({ token }),
      setError: (error) => set({ error }),

      checkAuth: async () => {
        set({ isLoading: true, error: null })
        try {
          const response = await fetch("/api/auth/me", {
            headers: {
              Authorization: `Bearer ${get().token}`,
            },
          })
          if (response.ok) {
            const user = await response.json()
            // Set Sentry user context for error tracking
            Sentry.setUser({
              id: user.id,
              email: user.email,
              username: user.name,
            })
            set({ user, isLoading: false })
          } else {
            set({ user: null, token: null, isLoading: false })
          }
        } catch {
          set({ user: null, token: null, isLoading: false, error: "Failed to check auth" })
        }
      },
    }),
    {
      name: "flowex-auth",
      partialize: (state) => ({ token: state.token }),
    }
  )
)
