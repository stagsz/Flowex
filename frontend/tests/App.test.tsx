import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import App from '../src/App'

describe('App', () => {
  it('renders the home page', () => {
    render(<App />)
    expect(screen.getByText(/Flowex/i)).toBeInTheDocument()
    expect(screen.getByText(/P&ID Digitization/i)).toBeInTheDocument()
  })
})
