import { render, screen, waitFor, fireEvent, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { CookieConsentBanner } from '@/components/consent/CookieConsentBanner'
import {
  hasConsentDecision,
  getConsent,
  clearConsent,
  COOKIE_CONSENT_KEY,
} from '@/lib/cookieConsent'

describe('CookieConsentBanner', () => {
  beforeEach(() => {
    // Clear localStorage and timers before each test
    localStorage.clear()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  describe('Banner Display', () => {
    it('should show banner after delay when no consent decision exists', async () => {
      render(<CookieConsentBanner />)

      // Banner should not be visible immediately
      expect(screen.queryByTestId('cookie-consent-banner')).not.toBeInTheDocument()

      // Advance timer past the 500ms delay
      await act(async () => {
        vi.advanceTimersByTime(600)
      })

      // Now banner should be visible
      expect(screen.getByTestId('cookie-consent-banner')).toBeInTheDocument()
      expect(screen.getByText('Cookie Settings')).toBeInTheDocument()
    })

    it('should not show banner when consent already exists', async () => {
      // Set consent before rendering
      localStorage.setItem(COOKIE_CONSENT_KEY, JSON.stringify({
        necessary: true,
        analytics: false,
        functional: false,
        marketing: false,
        timestamp: new Date().toISOString(),
        version: '1.0',
      }))

      render(<CookieConsentBanner />)

      // Advance timer
      await act(async () => {
        vi.advanceTimersByTime(600)
      })

      // Banner should not appear
      expect(screen.queryByTestId('cookie-consent-banner')).not.toBeInTheDocument()
    })

    it('should display privacy policy link', async () => {
      render(<CookieConsentBanner />)

      await act(async () => {
        vi.advanceTimersByTime(600)
      })

      const privacyLink = screen.getByRole('link', { name: /privacy policy/i })
      expect(privacyLink).toHaveAttribute('href', '/privacy')
    })
  })

  describe('Accept All', () => {
    it('should save all cookies as accepted and hide banner', async () => {
      render(<CookieConsentBanner />)

      await act(async () => {
        vi.advanceTimersByTime(600)
      })

      const acceptButton = screen.getByTestId('cookie-accept-button')
      fireEvent.click(acceptButton)

      // Banner should be hidden
      expect(screen.queryByTestId('cookie-consent-banner')).not.toBeInTheDocument()

      // All cookies should be accepted
      expect(hasConsentDecision()).toBe(true)
      const consent = getConsent()
      expect(consent.analytics).toBe(true)
      expect(consent.functional).toBe(true)
      expect(consent.marketing).toBe(true)
    })
  })

  describe('Necessary Only', () => {
    it('should save only necessary cookies and hide banner', async () => {
      render(<CookieConsentBanner />)

      await act(async () => {
        vi.advanceTimersByTime(600)
      })

      const rejectButton = screen.getByTestId('cookie-reject-button')
      fireEvent.click(rejectButton)

      // Banner should be hidden
      expect(screen.queryByTestId('cookie-consent-banner')).not.toBeInTheDocument()

      // Only necessary cookies should be enabled
      expect(hasConsentDecision()).toBe(true)
      const consent = getConsent()
      expect(consent.necessary).toBe(true)
      expect(consent.analytics).toBe(false)
      expect(consent.functional).toBe(false)
      expect(consent.marketing).toBe(false)
    })
  })

  describe('Customize Preferences', () => {
    it('should open preferences dialog when Customize is clicked', async () => {
      render(<CookieConsentBanner />)

      await act(async () => {
        vi.advanceTimersByTime(600)
      })

      const customizeButton = screen.getByTestId('cookie-customize-button')
      fireEvent.click(customizeButton)

      // Preferences dialog should appear
      expect(screen.getByText('Cookie Preferences')).toBeInTheDocument()
      expect(screen.getByTestId('cookie-category-necessary')).toBeInTheDocument()
      expect(screen.getByTestId('cookie-category-analytics')).toBeInTheDocument()
      expect(screen.getByTestId('cookie-category-functional')).toBeInTheDocument()
      expect(screen.getByTestId('cookie-category-marketing')).toBeInTheDocument()
    })

    it('should show necessary category as required and always enabled', async () => {
      render(<CookieConsentBanner />)

      await act(async () => {
        vi.advanceTimersByTime(600)
      })

      fireEvent.click(screen.getByTestId('cookie-customize-button'))

      // Necessary toggle should be disabled
      const necessaryToggle = screen.getByTestId('cookie-toggle-necessary')
      expect(necessaryToggle).toBeDisabled()
      expect(necessaryToggle).toHaveAttribute('aria-checked', 'true')

      // Required badge should be visible
      expect(screen.getByText('Required')).toBeInTheDocument()
    })

    it('should allow toggling optional cookie categories', async () => {
      render(<CookieConsentBanner />)

      await act(async () => {
        vi.advanceTimersByTime(600)
      })

      fireEvent.click(screen.getByTestId('cookie-customize-button'))

      // Toggle analytics on
      const analyticsToggle = screen.getByTestId('cookie-toggle-analytics')
      expect(analyticsToggle).toHaveAttribute('aria-checked', 'false')
      fireEvent.click(analyticsToggle)
      expect(analyticsToggle).toHaveAttribute('aria-checked', 'true')

      // Toggle analytics off
      fireEvent.click(analyticsToggle)
      expect(analyticsToggle).toHaveAttribute('aria-checked', 'false')
    })

    it('should save custom preferences when Save Preferences is clicked', async () => {
      render(<CookieConsentBanner />)

      await act(async () => {
        vi.advanceTimersByTime(600)
      })

      fireEvent.click(screen.getByTestId('cookie-customize-button'))

      // Enable analytics and functional, leave marketing off
      fireEvent.click(screen.getByTestId('cookie-toggle-analytics'))
      fireEvent.click(screen.getByTestId('cookie-toggle-functional'))

      // Save preferences
      fireEvent.click(screen.getByTestId('cookie-save-preferences'))

      // Dialog should close
      expect(screen.queryByText('Cookie Preferences')).not.toBeInTheDocument()

      // Check saved preferences
      const consent = getConsent()
      expect(consent.necessary).toBe(true)
      expect(consent.analytics).toBe(true)
      expect(consent.functional).toBe(true)
      expect(consent.marketing).toBe(false)
    })

    it('should close dialog without saving when Cancel is clicked', async () => {
      render(<CookieConsentBanner />)

      await act(async () => {
        vi.advanceTimersByTime(600)
      })

      fireEvent.click(screen.getByTestId('cookie-customize-button'))

      // Toggle some preferences
      fireEvent.click(screen.getByTestId('cookie-toggle-analytics'))

      // Cancel
      fireEvent.click(screen.getByRole('button', { name: /cancel/i }))

      // Dialog should close but banner should still be visible
      expect(screen.queryByText('Cookie Preferences')).not.toBeInTheDocument()

      // No consent should be saved
      expect(hasConsentDecision()).toBe(false)
    })

    it('should handle Necessary Only button in preferences dialog', async () => {
      render(<CookieConsentBanner />)

      await act(async () => {
        vi.advanceTimersByTime(600)
      })

      fireEvent.click(screen.getByTestId('cookie-customize-button'))

      // Toggle some preferences first
      fireEvent.click(screen.getByTestId('cookie-toggle-analytics'))
      fireEvent.click(screen.getByTestId('cookie-toggle-functional'))

      // Click Necessary Only in dialog
      // There may be multiple buttons with this text (one in banner, one in dialog)
      const buttons = screen.getAllByRole('button', { name: /necessary only/i })
      fireEvent.click(buttons[buttons.length - 1]) // Click the one in dialog

      // Should save with only necessary
      const consent = getConsent()
      expect(consent.analytics).toBe(false)
      expect(consent.functional).toBe(false)
      expect(consent.marketing).toBe(false)
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA attributes on banner', async () => {
      render(<CookieConsentBanner />)

      await act(async () => {
        vi.advanceTimersByTime(600)
      })

      const banner = screen.getByTestId('cookie-consent-banner')
      expect(banner).toHaveAttribute('role', 'dialog')
      expect(banner).toHaveAttribute('aria-labelledby', 'cookie-banner-title')
      expect(banner).toHaveAttribute('aria-describedby', 'cookie-banner-description')
    })

    it('should have proper ARIA attributes on toggle switches', async () => {
      render(<CookieConsentBanner />)

      await act(async () => {
        vi.advanceTimersByTime(600)
      })

      fireEvent.click(screen.getByTestId('cookie-customize-button'))

      const analyticsToggle = screen.getByTestId('cookie-toggle-analytics')
      expect(analyticsToggle).toHaveAttribute('role', 'switch')
      expect(analyticsToggle).toHaveAttribute('aria-label', 'Toggle Analytics cookies')
    })
  })
})
