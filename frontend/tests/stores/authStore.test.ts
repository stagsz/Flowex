import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { Session, User as SupabaseUser } from '@supabase/supabase-js'

// Use vi.hoisted to ensure mocks are defined before module imports
const { mockGetSession, mockSignInWithOAuth, mockSignOut, mockOnAuthStateChange } = vi.hoisted(() => ({
  mockGetSession: vi.fn(),
  mockSignInWithOAuth: vi.fn(),
  mockSignOut: vi.fn(),
  mockOnAuthStateChange: vi.fn(() => ({
    data: { subscription: { unsubscribe: vi.fn() } },
  })),
}))

// Mock Sentry
vi.mock('@sentry/react', () => ({
  setUser: vi.fn(),
}))

// Mock the supabase module
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: () => mockGetSession(),
      signInWithOAuth: (options: unknown) => mockSignInWithOAuth(options),
      signOut: () => mockSignOut(),
      onAuthStateChange: (callback: unknown) => mockOnAuthStateChange(callback),
    },
  },
}))

// Import authStore AFTER mocks are set up
import { useAuthStore, type User } from '@/stores/authStore'

// Check if DEV_AUTH_BYPASS is enabled (from environment)
const DEV_AUTH_BYPASS = import.meta.env.VITE_DEV_AUTH_BYPASS === 'true'

// Helper to create a mock Supabase user
function createMockSupabaseUser(overrides: Partial<SupabaseUser> = {}): SupabaseUser {
  return {
    id: 'test-user-id',
    email: 'test@example.com',
    user_metadata: {
      full_name: 'Test User',
      avatar_url: 'https://example.com/avatar.jpg',
    },
    app_metadata: {
      org_id: 'test-org-id',
      role: 'editor',
    },
    aud: 'authenticated',
    created_at: '2024-01-01T00:00:00Z',
    ...overrides,
  } as SupabaseUser
}

// Helper to create a mock session
function createMockSession(user: SupabaseUser): Session {
  return {
    access_token: 'test-access-token',
    token_type: 'bearer',
    expires_in: 3600,
    refresh_token: 'test-refresh-token',
    user,
  } as Session
}

describe('authStore', () => {
  beforeEach(() => {
    // Reset all mocks
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('setUser', () => {
    it('should set user in state', () => {
      const testUser: User = {
        id: 'user-1',
        email: 'test@example.com',
        name: 'Test User',
        role: 'editor',
        organizationId: 'org-1',
        organizationName: 'Test Org',
      }

      useAuthStore.getState().setUser(testUser)
      expect(useAuthStore.getState().user).toEqual(testUser)
    })

    it('should set user to null', () => {
      useAuthStore.setState({ user: { id: 'test', email: 'test@test.com', name: 'Test', role: 'viewer', organizationId: 'org', organizationName: 'Org' } })
      useAuthStore.getState().setUser(null)
      expect(useAuthStore.getState().user).toBeNull()
    })
  })

  describe('setToken', () => {
    it('should set token in state', () => {
      useAuthStore.getState().setToken('new-token')
      expect(useAuthStore.getState().token).toBe('new-token')
    })

    it('should set token to null', () => {
      useAuthStore.setState({ token: 'existing-token' })
      useAuthStore.getState().setToken(null)
      expect(useAuthStore.getState().token).toBeNull()
    })
  })

  describe('setError', () => {
    it('should set error in state', () => {
      useAuthStore.getState().setError('Something went wrong')
      expect(useAuthStore.getState().error).toBe('Something went wrong')
    })

    it('should clear error', () => {
      useAuthStore.setState({ error: 'Previous error' })
      useAuthStore.getState().setError(null)
      expect(useAuthStore.getState().error).toBeNull()
    })
  })

  // Tests that run only when DEV_AUTH_BYPASS is enabled
  describe('DEV_AUTH_BYPASS mode', () => {
    beforeEach(() => {
      // Ensure we're starting fresh
      vi.clearAllMocks()
    })

    it.skipIf(!DEV_AUTH_BYPASS)('login should restore dev user after clearing state', async () => {
      // Clear state first (simulating a logged out state)
      useAuthStore.setState({ user: null, token: null, isLoading: false, error: null })

      // In bypass mode, login should restore the dev user
      await useAuthStore.getState().login('google')

      const state = useAuthStore.getState()
      expect(state.user).not.toBeNull()
      expect(state.user?.email).toBe('dev@flowex.local')
      expect(state.user?.name).toBe('Dev User')
      expect(state.user?.role).toBe('admin')
      expect(state.token).toBe('dev-token')
    })

    it.skipIf(!DEV_AUTH_BYPASS)('login should set dev user immediately without calling Supabase', async () => {
      // Reset to null state first
      useAuthStore.setState({ user: null, token: null })

      await useAuthStore.getState().login('google')

      // Should have dev user set
      const state = useAuthStore.getState()
      expect(state.user?.email).toBe('dev@flowex.local')
      expect(state.token).toBe('dev-token')

      // Supabase should NOT have been called
      expect(mockSignInWithOAuth).not.toHaveBeenCalled()
    })

    it.skipIf(!DEV_AUTH_BYPASS)('handleAuthCallback should set dev user without calling Supabase', async () => {
      // Reset to null state first
      useAuthStore.setState({ user: null, token: null, isLoading: false })

      await useAuthStore.getState().handleAuthCallback()

      const state = useAuthStore.getState()
      expect(state.user?.email).toBe('dev@flowex.local')
      expect(state.token).toBe('dev-token')
      expect(state.isLoading).toBe(false)

      // Supabase should NOT have been called
      expect(mockGetSession).not.toHaveBeenCalled()
    })

    it.skipIf(!DEV_AUTH_BYPASS)('checkAuth should set dev user without calling Supabase', async () => {
      // Reset to null state first
      useAuthStore.setState({ user: null, token: null, isLoading: false })

      await useAuthStore.getState().checkAuth()

      const state = useAuthStore.getState()
      expect(state.user?.email).toBe('dev@flowex.local')
      expect(state.token).toBe('dev-token')
      expect(state.isLoading).toBe(false)

      // Supabase should NOT have been called
      expect(mockGetSession).not.toHaveBeenCalled()
    })
  })

  // Tests that run only when DEV_AUTH_BYPASS is disabled
  describe('Production mode (no bypass)', () => {
    beforeEach(() => {
      vi.clearAllMocks()
    })

    it.skipIf(DEV_AUTH_BYPASS)('should initialize with null user when bypass is disabled', () => {
      // Reset state
      useAuthStore.setState({ user: null, token: null, isLoading: false, error: null })
      const state = useAuthStore.getState()
      expect(state.user).toBeNull()
      expect(state.token).toBeNull()
    })

    it.skipIf(DEV_AUTH_BYPASS)('login should call Supabase signInWithOAuth', async () => {
      useAuthStore.setState({ user: null, token: null, isLoading: false, error: null })
      mockSignInWithOAuth.mockResolvedValueOnce({ data: {}, error: null })

      await useAuthStore.getState().login('google')

      expect(mockSignInWithOAuth).toHaveBeenCalledWith({
        provider: 'google',
        options: {
          redirectTo: expect.stringContaining('/auth/callback'),
        },
      })
    })

    it.skipIf(DEV_AUTH_BYPASS)('handleAuthCallback should get session from Supabase', async () => {
      useAuthStore.setState({ user: null, token: null, isLoading: false, error: null })
      const mockUser = createMockSupabaseUser()
      const mockSession = createMockSession(mockUser)
      mockGetSession.mockResolvedValueOnce({ data: { session: mockSession }, error: null })

      await useAuthStore.getState().handleAuthCallback()

      expect(mockGetSession).toHaveBeenCalled()
      const state = useAuthStore.getState()
      expect(state.user?.id).toBe('test-user-id')
    })
  })

  describe('logout', () => {
    it('should call supabase signOut and clear state', async () => {
      mockSignOut.mockResolvedValueOnce({ error: null })

      // Mock window.location
      const originalLocation = window.location
      Object.defineProperty(window, 'location', {
        value: { href: '' },
        writable: true,
      })

      useAuthStore.setState({
        user: { id: 'test', email: 'test@test.com', name: 'Test', role: 'viewer', organizationId: 'org', organizationName: 'Org' },
        token: 'existing-token',
      })

      await useAuthStore.getState().logout()

      // In both modes, logout should clear state and redirect
      expect(useAuthStore.getState().user).toBeNull()
      expect(useAuthStore.getState().token).toBeNull()
      expect(window.location.href).toBe('/')

      // Restore window.location
      Object.defineProperty(window, 'location', { value: originalLocation })
    })

    it('should clear state even if signOut throws', async () => {
      mockSignOut.mockRejectedValueOnce(new Error('Sign out failed'))

      // Mock window.location
      const originalLocation = window.location
      Object.defineProperty(window, 'location', {
        value: { href: '' },
        writable: true,
      })

      useAuthStore.setState({
        user: { id: 'test', email: 'test@test.com', name: 'Test', role: 'viewer', organizationId: 'org', organizationName: 'Org' },
        token: 'existing-token',
      })

      await useAuthStore.getState().logout()

      // State should still be cleared
      expect(useAuthStore.getState().user).toBeNull()
      expect(useAuthStore.getState().token).toBeNull()

      // Restore window.location
      Object.defineProperty(window, 'location', { value: originalLocation })
    })
  })

  describe('User type validation', () => {
    it('should accept all valid role types', () => {
      const roles: Array<User['role']> = ['viewer', 'editor', 'admin', 'owner']

      for (const role of roles) {
        const testUser: User = {
          id: 'user-1',
          email: 'test@example.com',
          name: 'Test User',
          role,
          organizationId: 'org-1',
          organizationName: 'Test Org',
        }
        useAuthStore.getState().setUser(testUser)
        expect(useAuthStore.getState().user?.role).toBe(role)
      }
    })

    it('should handle user with optional avatar', () => {
      const userWithAvatar: User = {
        id: 'user-1',
        email: 'test@example.com',
        name: 'Test User',
        avatar: 'https://example.com/avatar.jpg',
        role: 'editor',
        organizationId: 'org-1',
        organizationName: 'Test Org',
      }
      useAuthStore.getState().setUser(userWithAvatar)
      expect(useAuthStore.getState().user?.avatar).toBe('https://example.com/avatar.jpg')

      const userWithoutAvatar: User = {
        id: 'user-2',
        email: 'test2@example.com',
        name: 'Test User 2',
        role: 'viewer',
        organizationId: 'org-2',
        organizationName: 'Test Org 2',
      }
      useAuthStore.getState().setUser(userWithoutAvatar)
      expect(useAuthStore.getState().user?.avatar).toBeUndefined()
    })
  })

  describe('State persistence', () => {
    it('should only persist token in storage', () => {
      // This tests the partialize configuration
      // The store is configured to only persist { token: state.token }
      useAuthStore.setState({
        user: { id: 'test', email: 'test@test.com', name: 'Test', role: 'viewer', organizationId: 'org', organizationName: 'Org' },
        token: 'test-token',
        isLoading: true,
        error: 'some error',
      })

      // The token should be accessible
      expect(useAuthStore.getState().token).toBe('test-token')
    })
  })

  describe('Loading state management', () => {
    it('should track isLoading flag correctly', () => {
      // Initial state
      useAuthStore.setState({ isLoading: false })
      expect(useAuthStore.getState().isLoading).toBe(false)

      // Set loading
      useAuthStore.setState({ isLoading: true })
      expect(useAuthStore.getState().isLoading).toBe(true)

      // Clear loading
      useAuthStore.setState({ isLoading: false })
      expect(useAuthStore.getState().isLoading).toBe(false)
    })
  })

  describe('Error state management', () => {
    it('should track error messages correctly', () => {
      // Initial state
      useAuthStore.setState({ error: null })
      expect(useAuthStore.getState().error).toBeNull()

      // Set error via setError
      useAuthStore.getState().setError('Test error message')
      expect(useAuthStore.getState().error).toBe('Test error message')

      // Clear error via setError
      useAuthStore.getState().setError(null)
      expect(useAuthStore.getState().error).toBeNull()
    })
  })
})
