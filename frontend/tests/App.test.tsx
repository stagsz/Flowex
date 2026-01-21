import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import App from '../src/App'

describe('App', () => {
  it('renders the app with header', async () => {
    render(<App />)
    // Wait for the app to finish loading and display content
    // With DEV_AUTH_BYPASS=true, the app auto-logs in and shows Dashboard
    await waitFor(() => {
      expect(screen.getByText(/Flowex/i)).toBeInTheDocument()
    }, { timeout: 3000 })
    // Check for header/navigation elements that are present when logged in
    // Dashboard appears multiple times (nav link and page header), so use getAllByText
    expect(screen.getAllByText(/Dashboard/i).length).toBeGreaterThan(0)
  })
})
