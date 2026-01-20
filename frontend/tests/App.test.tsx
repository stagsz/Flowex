import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import App from '../src/App'

describe('App', () => {
  it('renders the home page', async () => {
    render(<App />)
    // Wait for the app to finish loading and display content
    await waitFor(() => {
      expect(screen.getByText(/Flowex/i)).toBeInTheDocument()
    }, { timeout: 3000 })
    expect(screen.getByText(/P&ID Digitization/i)).toBeInTheDocument()
  })
})
