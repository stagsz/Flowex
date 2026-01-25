import { create } from "zustand"
import { persist } from "zustand/middleware"
import * as Sentry from "@sentry/react"
import { supabase } from "@/lib/supabase"
import type { User as SupabaseUser, Session } from "@supabase/supabase-js"

// Dev auth bypass - auto-login with dev user in development
const DEV_AUTH_BYPASS = import.meta.env.VITE_DEV_AUTH_BYPASS === "true"

const DEV_USER: User = {
  id: "dev-user-id",
  email: "dev@flowex.local",
  name: "Dev User",
  role: "admin",
  organizationId: "263d7cd1-7e5c-45fa-a604-98145e996211",
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
  login: (provider: "google" | "azure") => Promise<void>
  logout: () => Promise<void>
  setUser: (user: User | null) => void
  setToken: (token: string | null) => void
  setError: (error: string | null) => void
  checkAuth: () => Promise<void>
  handleAuthCallback: () => Promise<void>
}

// Convert Supabase user to our User format
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function mapSupabaseUser(supabaseUser: SupabaseUser, _session: Session | null): User {
  const metadata = supabaseUser.user_metadata || {}
  const appMetadata = supabaseUser.app_metadata || {}

  // Extract org info from email domain if not set
  const emailDomain = supabaseUser.email?.split("@")[1] || "unknown"
  const orgName = emailDomain.split(".")[0]
  const orgId = appMetadata.org_id || `org-${orgName}`

  return {
    id: supabaseUser.id,
    email: supabaseUser.email || "",
    name: metadata.full_name || metadata.name || supabaseUser.email?.split("@")[0] || "User",
    avatar: metadata.avatar_url || metadata.picture,
    role: appMetadata.role || "member",
    organizationId: orgId,
    organizationName: metadata.organization_name || orgName.charAt(0).toUpperCase() + orgName.slice(1),
  }
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: DEV_AUTH_BYPASS ? DEV_USER : null,
      token: DEV_AUTH_BYPASS ? "dev-token" : null,
      isLoading: false,
      error: null,

      login: async (provider: "google" | "azure") => {
        if (DEV_AUTH_BYPASS) {
          set({ user: DEV_USER, token: "dev-token" })
          return
        }

        set({ isLoading: true, error: null })

        try {
          const { error } = await supabase.auth.signInWithOAuth({
            provider: provider === "azure" ? "azure" : "google",
            options: {
              redirectTo: `${window.location.origin}/auth/callback`,
            },
          })

          if (error) {
            set({ error: error.message, isLoading: false })
          }
          // OAuth will redirect, so we don't need to do anything else here
        } catch (err) {
          set({ error: "Failed to initiate login", isLoading: false })
        }
      },

      logout: async () => {
        try {
          await supabase.auth.signOut()
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

      // Handle OAuth callback
      handleAuthCallback: async () => {
        if (DEV_AUTH_BYPASS) {
          set({ user: DEV_USER, token: "dev-token", isLoading: false })
          return
        }

        set({ isLoading: true, error: null })

        try {
          // Supabase will automatically handle the OAuth callback
          // and set the session from URL params
          const { data: { session }, error } = await supabase.auth.getSession()

          if (error) {
            set({ error: error.message, isLoading: false })
            return
          }

          if (session?.user) {
            const user = mapSupabaseUser(session.user, session)

            // Set Sentry user context
            Sentry.setUser({
              id: user.id,
              email: user.email,
              username: user.name,
            })

            set({
              user,
              token: session.access_token,
              isLoading: false,
            })
          } else {
            set({ user: null, token: null, isLoading: false })
          }
        } catch {
          set({ error: "Failed to complete authentication", isLoading: false })
        }
      },

      checkAuth: async () => {
        if (DEV_AUTH_BYPASS) {
          set({ user: DEV_USER, token: "dev-token", isLoading: false })
          return
        }

        set({ isLoading: true, error: null })

        try {
          const { data: { session }, error } = await supabase.auth.getSession()

          if (error) {
            set({ user: null, token: null, isLoading: false })
            return
          }

          if (session?.user) {
            const user = mapSupabaseUser(session.user, session)

            // Set Sentry user context
            Sentry.setUser({
              id: user.id,
              email: user.email,
              username: user.name,
            })

            set({
              user,
              token: session.access_token,
              isLoading: false,
            })
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

// Listen for auth state changes
supabase.auth.onAuthStateChange((event, session) => {
  if (DEV_AUTH_BYPASS) return

  const store = useAuthStore.getState()

  if (event === "SIGNED_IN" && session?.user) {
    const user = mapSupabaseUser(session.user, session)
    store.setUser(user)
    store.setToken(session.access_token)

    Sentry.setUser({
      id: user.id,
      email: user.email,
      username: user.name,
    })
  } else if (event === "SIGNED_OUT") {
    store.setUser(null)
    store.setToken(null)
    Sentry.setUser(null)
  } else if (event === "TOKEN_REFRESHED" && session) {
    store.setToken(session.access_token)
  }
})
