import { create } from "zustand"
import { persist } from "zustand/middleware"
import * as Sentry from "@sentry/react"

// Dev auth bypass - auto-login with dev user in development
const DEV_AUTH_BYPASS = import.meta.env.VITE_DEV_AUTH_BYPASS === "true"

const DEV_USER: User = {
  id: "dev-user-id",
  email: "dev@flowex.local",
  name: "Dev User",
  role: "admin",
  organizationId: "dev-org-id",
  organizationName: "Dev Organization",
}

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
      user: DEV_AUTH_BYPASS ? DEV_USER : null,
      token: DEV_AUTH_BYPASS ? "dev-token" : null,
      isLoading: false,
      error: null,

      login: () => {
        if (DEV_AUTH_BYPASS) {
          set({ user: DEV_USER, token: "dev-token" })
          return
        }
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
        if (DEV_AUTH_BYPASS) {
          set({ user: DEV_USER, token: "dev-token", isLoading: false })
          return
        }
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
      // Skip rehydration in dev bypass mode
      skipHydration: DEV_AUTH_BYPASS,
    }
  )
)
