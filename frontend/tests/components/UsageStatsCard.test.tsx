import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { UsageStatsCard } from '@/components/UsageStatsCard'

// Mock the api module
vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn(),
  },
}))

// Mock the auth store
vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn(() => ({
    user: {
      id: 'test-user',
      organizationId: 'test-org-id',
      name: 'Test User',
      email: 'test@example.com',
      role: 'admin',
      organizationName: 'Test Org',
    },
  })),
}))

import { api } from '@/lib/api'

const mockUsageData = {
  organization_id: 'test-org-id',
  organization_name: 'Test Organization',
  period_start: '2026-01-01T00:00:00Z',
  period_end: '2026-02-01T00:00:00Z',
  plan: 'professional',
  plan_limit: 50,
  used_count: 32,
  remaining_count: 18,
  member_count: 5,
}

describe('UsageStatsCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render loading state initially', () => {
    const mockGet = vi.mocked(api.get)
    mockGet.mockImplementation(() => new Promise(() => {})) // Never resolves

    render(<UsageStatsCard />)

    // Should show loading spinner (Loader2 icon has animate-spin class)
    const spinner = document.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
  })

  it('should display usage stats when loaded successfully', async () => {
    const mockGet = vi.mocked(api.get)
    mockGet.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockUsageData),
    } as Response)

    render(<UsageStatsCard />)

    await waitFor(() => {
      expect(screen.getByText('32/50')).toBeInTheDocument()
    })

    expect(screen.getByText('Usage This Month')).toBeInTheDocument()
    expect(screen.getByText('Professional Plan')).toBeInTheDocument()
    expect(screen.getByText(/Resets:/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /upgrade plan/i })).toBeInTheDocument()
  })

  it('should display warning when near limit (80%+)', async () => {
    const mockGet = vi.mocked(api.get)
    mockGet.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        ...mockUsageData,
        used_count: 42,
        remaining_count: 8,
      }),
    } as Response)

    render(<UsageStatsCard />)

    await waitFor(() => {
      expect(screen.getByText('42/50')).toBeInTheDocument()
    })

    expect(screen.getByText(/Approaching limit/)).toBeInTheDocument()
    expect(screen.getByText(/8 remaining/)).toBeInTheDocument()
  })

  it('should display error message when at limit (100%)', async () => {
    const mockGet = vi.mocked(api.get)
    mockGet.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        ...mockUsageData,
        used_count: 50,
        remaining_count: 0,
      }),
    } as Response)

    render(<UsageStatsCard />)

    await waitFor(() => {
      expect(screen.getByText('50/50')).toBeInTheDocument()
    })

    expect(screen.getByText(/Limit reached/)).toBeInTheDocument()
    expect(screen.getByText(/Upgrade to continue/)).toBeInTheDocument()
  })

  it('should display error state when API fails', async () => {
    const mockGet = vi.mocked(api.get)
    mockGet.mockResolvedValueOnce({
      ok: false,
      status: 500,
    } as Response)

    render(<UsageStatsCard />)

    await waitFor(() => {
      expect(screen.getByText('Unable to load usage stats')).toBeInTheDocument()
    })
  })

  it('should display error state when API throws', async () => {
    const mockGet = vi.mocked(api.get)
    mockGet.mockRejectedValueOnce(new Error('Network error'))

    render(<UsageStatsCard />)

    await waitFor(() => {
      expect(screen.getByText('Unable to load usage stats')).toBeInTheDocument()
    })
  })

  it('should call onUpgrade when Upgrade Plan button is clicked', async () => {
    const mockGet = vi.mocked(api.get)
    mockGet.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockUsageData),
    } as Response)

    const onUpgrade = vi.fn()
    render(<UsageStatsCard onUpgrade={onUpgrade} />)

    await waitFor(() => {
      expect(screen.getByText('32/50')).toBeInTheDocument()
    })

    const upgradeButton = screen.getByRole('button', { name: /upgrade plan/i })
    fireEvent.click(upgradeButton)

    expect(onUpgrade).toHaveBeenCalledTimes(1)
  })

  it('should format plan names correctly', async () => {
    const testCases = [
      { plan: 'free', expected: 'Free Plan' },
      { plan: 'starter', expected: 'Starter Plan' },
      { plan: 'professional', expected: 'Professional Plan' },
      { plan: 'enterprise', expected: 'Enterprise Plan' },
    ]

    for (const { plan, expected } of testCases) {
      const mockGet = vi.mocked(api.get)
      mockGet.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ ...mockUsageData, plan }),
      } as Response)

      const { unmount } = render(<UsageStatsCard />)

      await waitFor(() => {
        expect(screen.getByText(expected)).toBeInTheDocument()
      })

      unmount()
    }
  })

  it('should apply custom className when provided', async () => {
    const mockGet = vi.mocked(api.get)
    mockGet.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockUsageData),
    } as Response)

    const { container } = render(<UsageStatsCard className="custom-class" />)

    await waitFor(() => {
      expect(screen.getByText('32/50')).toBeInTheDocument()
    })

    // The Card component should have the custom class
    const card = container.querySelector('.custom-class')
    expect(card).toBeInTheDocument()
  })
})
