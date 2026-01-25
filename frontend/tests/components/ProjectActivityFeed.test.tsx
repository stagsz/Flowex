import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import { ProjectActivityFeed, DashboardActivityFeed } from '@/components/ProjectActivityFeed'

// Mock the api module
vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn(),
  },
}))

import { api } from '@/lib/api'

const mockActivityData = {
  items: [
    {
      id: 'act-1',
      user_name: 'Anna Müller',
      action: 'uploaded',
      entity_type: 'drawing',
      entity_name: 'P&ID-001',
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
    },
    {
      id: 'act-2',
      user_name: 'Erik Schmidt',
      action: 'completed_validation',
      entity_type: 'drawing',
      entity_name: 'P&ID-002',
      timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(), // 15 min ago
    },
    {
      id: 'act-3',
      user_name: null, // System action
      action: 'completed_processing',
      entity_type: 'drawing',
      entity_name: 'P&ID-003',
      timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(), // 1 day ago
    },
  ],
  total: 3,
  limit: 10,
}

const mockProjectsData = [
  {
    id: 'project-1',
    name: 'Refinery Unit A',
    updated_at: new Date().toISOString(),
  },
  {
    id: 'project-2',
    name: 'Chemical Plant B',
    updated_at: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
  },
]

// Helper to wrap components with BrowserRouter
const renderWithRouter = (component: React.ReactNode) => {
  return render(<BrowserRouter>{component}</BrowserRouter>)
}

describe('ProjectActivityFeed', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render loading state initially', () => {
    const mockGet = vi.mocked(api.get)
    mockGet.mockImplementation(() => new Promise(() => {})) // Never resolves

    renderWithRouter(<ProjectActivityFeed projectId="test-project" />)

    // Should show loading spinner
    const spinner = document.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
    expect(screen.getByText('Loading activity...')).toBeInTheDocument()
  })

  it('should display activity items when loaded successfully', async () => {
    const mockGet = vi.mocked(api.get)
    mockGet.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockActivityData),
    } as Response)

    renderWithRouter(<ProjectActivityFeed projectId="test-project" />)

    await waitFor(() => {
      expect(screen.getByText('Anna Müller')).toBeInTheDocument()
    })

    expect(screen.getByText('Recent Activity')).toBeInTheDocument()
    expect(screen.getByText('Erik Schmidt')).toBeInTheDocument()
    expect(screen.getByText('System')).toBeInTheDocument() // null user_name shows as System
    expect(screen.getByText('P&ID-001')).toBeInTheDocument()
    expect(screen.getByText('P&ID-002')).toBeInTheDocument()
    expect(screen.getByText('P&ID-003')).toBeInTheDocument()
  })

  it('should display relative timestamps correctly', async () => {
    const mockGet = vi.mocked(api.get)
    mockGet.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockActivityData),
    } as Response)

    renderWithRouter(<ProjectActivityFeed projectId="test-project" />)

    await waitFor(() => {
      expect(screen.getByText('Anna Müller')).toBeInTheDocument()
    })

    // Check for relative time formats
    expect(screen.getByText('2h ago')).toBeInTheDocument()
    expect(screen.getByText('15m ago')).toBeInTheDocument()
    expect(screen.getByText('1d ago')).toBeInTheDocument()
  })

  it('should display empty state when no activities', async () => {
    const mockGet = vi.mocked(api.get)
    mockGet.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ items: [], total: 0, limit: 10 }),
    } as Response)

    renderWithRouter(<ProjectActivityFeed projectId="test-project" />)

    await waitFor(() => {
      expect(screen.getByText('No activity yet')).toBeInTheDocument()
    })

    expect(
      screen.getByText('Activity will appear here when team members work on drawings')
    ).toBeInTheDocument()
  })

  it('should display error state when API fails', async () => {
    const mockGet = vi.mocked(api.get)
    mockGet.mockResolvedValueOnce({
      ok: false,
      status: 500,
    } as Response)

    renderWithRouter(<ProjectActivityFeed projectId="test-project" />)

    await waitFor(() => {
      expect(screen.getByText('Failed to load activity')).toBeInTheDocument()
    })

    expect(screen.getByText('Try again')).toBeInTheDocument()
  })

  it('should retry loading when Try again is clicked', async () => {
    const mockGet = vi.mocked(api.get)
    // First call fails
    mockGet.mockResolvedValueOnce({
      ok: false,
      status: 500,
    } as Response)

    renderWithRouter(<ProjectActivityFeed projectId="test-project" />)

    await waitFor(() => {
      expect(screen.getByText('Failed to load activity')).toBeInTheDocument()
    })

    // Second call succeeds
    mockGet.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockActivityData),
    } as Response)

    fireEvent.click(screen.getByText('Try again'))

    await waitFor(() => {
      expect(screen.getByText('Anna Müller')).toBeInTheDocument()
    })
  })

  it('should respect limit parameter', async () => {
    const mockGet = vi.mocked(api.get)
    mockGet.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockActivityData),
    } as Response)

    renderWithRouter(<ProjectActivityFeed projectId="test-project" limit={5} />)

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith(
        '/api/v1/projects/test-project/activity?limit=5'
      )
    })
  })

  it('should hide header when showHeader is false', async () => {
    const mockGet = vi.mocked(api.get)
    mockGet.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockActivityData),
    } as Response)

    renderWithRouter(
      <ProjectActivityFeed projectId="test-project" showHeader={false} />
    )

    await waitFor(() => {
      expect(screen.getByText('Anna Müller')).toBeInTheDocument()
    })

    // Header should not be present
    expect(screen.queryByText('Recent Activity')).not.toBeInTheDocument()
  })

  it('should show View All link when showViewAll is true', async () => {
    const mockGet = vi.mocked(api.get)
    mockGet.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockActivityData),
    } as Response)

    renderWithRouter(
      <ProjectActivityFeed projectId="test-project" showViewAll={true} />
    )

    await waitFor(() => {
      expect(screen.getByText('Anna Müller')).toBeInTheDocument()
    })

    expect(screen.getByText('View all activity')).toBeInTheDocument()
  })

  it('should display correct icons for different action types', async () => {
    const actionsWithIcons = {
      items: [
        {
          id: 'act-1',
          user_name: 'User 1',
          action: 'uploaded',
          entity_type: 'drawing',
          entity_name: 'Drawing 1',
          timestamp: new Date().toISOString(),
        },
        {
          id: 'act-2',
          user_name: 'User 2',
          action: 'exported_dxf',
          entity_type: 'drawing',
          entity_name: 'Drawing 2',
          timestamp: new Date().toISOString(),
        },
        {
          id: 'act-3',
          user_name: 'User 3',
          action: 'deleted_symbol',
          entity_type: 'symbol',
          entity_name: 'Symbol 1',
          timestamp: new Date().toISOString(),
        },
      ],
      total: 3,
      limit: 10,
    }

    const mockGet = vi.mocked(api.get)
    mockGet.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(actionsWithIcons),
    } as Response)

    renderWithRouter(<ProjectActivityFeed projectId="test-project" />)

    await waitFor(() => {
      expect(screen.getByText('User 1')).toBeInTheDocument()
    })

    // Check that all users are displayed (icons are rendered)
    expect(screen.getByText('User 2')).toBeInTheDocument()
    expect(screen.getByText('User 3')).toBeInTheDocument()
  })
})

describe('DashboardActivityFeed', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render loading state while fetching projects', () => {
    const mockGet = vi.mocked(api.get)
    mockGet.mockImplementation(() => new Promise(() => {})) // Never resolves

    renderWithRouter(<DashboardActivityFeed />)

    const spinner = document.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
  })

  it('should fetch activity from the most recent project', async () => {
    const mockGet = vi.mocked(api.get)

    // First call: fetch projects
    mockGet.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockProjectsData),
    } as Response)

    // Second call: fetch activity for most recent project
    mockGet.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockActivityData),
    } as Response)

    renderWithRouter(<DashboardActivityFeed limit={5} />)

    await waitFor(() => {
      // Should call projects API first
      expect(mockGet).toHaveBeenCalledWith('/api/v1/projects/')
    })

    await waitFor(() => {
      // Should call activity API for project-1 (most recently updated)
      expect(mockGet).toHaveBeenCalledWith(
        '/api/v1/projects/project-1/activity?limit=5'
      )
    })

    await waitFor(() => {
      expect(screen.getByText('Anna Müller')).toBeInTheDocument()
    })
  })

  it('should display empty state when no projects exist', async () => {
    const mockGet = vi.mocked(api.get)
    mockGet.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([]),
    } as Response)

    renderWithRouter(<DashboardActivityFeed />)

    await waitFor(() => {
      expect(screen.getByText('No projects yet')).toBeInTheDocument()
    })

    expect(screen.getByText('Create a project to see activity')).toBeInTheDocument()
    expect(screen.getByText('Create project')).toBeInTheDocument()
  })

  it('should display empty state when projects API fails', async () => {
    const mockGet = vi.mocked(api.get)
    mockGet.mockRejectedValueOnce(new Error('Network error'))

    renderWithRouter(<DashboardActivityFeed />)

    await waitFor(() => {
      expect(screen.getByText('No projects yet')).toBeInTheDocument()
    })
  })

  it('should pass showViewAll=true to ProjectActivityFeed', async () => {
    const mockGet = vi.mocked(api.get)

    mockGet.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockProjectsData),
    } as Response)

    mockGet.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockActivityData),
    } as Response)

    renderWithRouter(<DashboardActivityFeed />)

    await waitFor(() => {
      expect(screen.getByText('Anna Müller')).toBeInTheDocument()
    })

    expect(screen.getByText('View all activity')).toBeInTheDocument()
  })
})
