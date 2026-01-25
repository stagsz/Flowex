import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  hasConsentDecision,
  getConsent,
  saveConsent,
  acceptAllCookies,
  acceptNecessaryOnly,
  clearConsent,
  isCategoryAllowed,
  COOKIE_CONSENT_KEY,
  COOKIE_CONSENT_VERSION,
  DEFAULT_CONSENT,
} from '@/lib/cookieConsent'

describe('cookieConsent', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear()
    vi.clearAllMocks()
  })

  describe('hasConsentDecision', () => {
    it('should return false when no consent is stored', () => {
      expect(hasConsentDecision()).toBe(false)
    })

    it('should return false when stored consent has no timestamp', () => {
      localStorage.setItem(COOKIE_CONSENT_KEY, JSON.stringify({
        ...DEFAULT_CONSENT,
        timestamp: '',
      }))
      expect(hasConsentDecision()).toBe(false)
    })

    it('should return false when consent version mismatches', () => {
      localStorage.setItem(COOKIE_CONSENT_KEY, JSON.stringify({
        ...DEFAULT_CONSENT,
        timestamp: new Date().toISOString(),
        version: '0.9',
      }))
      expect(hasConsentDecision()).toBe(false)
    })

    it('should return true when valid consent is stored', () => {
      localStorage.setItem(COOKIE_CONSENT_KEY, JSON.stringify({
        ...DEFAULT_CONSENT,
        timestamp: new Date().toISOString(),
        version: COOKIE_CONSENT_VERSION,
      }))
      expect(hasConsentDecision()).toBe(true)
    })

    it('should return false when localStorage has invalid JSON', () => {
      localStorage.setItem(COOKIE_CONSENT_KEY, 'invalid-json')
      expect(hasConsentDecision()).toBe(false)
    })
  })

  describe('getConsent', () => {
    it('should return default consent when nothing is stored', () => {
      expect(getConsent()).toEqual(DEFAULT_CONSENT)
    })

    it('should return stored consent when valid', () => {
      const storedConsent = {
        necessary: true,
        analytics: true,
        functional: false,
        marketing: false,
        timestamp: '2026-01-20T12:00:00Z',
        version: COOKIE_CONSENT_VERSION,
      }
      localStorage.setItem(COOKIE_CONSENT_KEY, JSON.stringify(storedConsent))
      expect(getConsent()).toEqual(storedConsent)
    })

    it('should return default consent when version mismatches', () => {
      localStorage.setItem(COOKIE_CONSENT_KEY, JSON.stringify({
        necessary: true,
        analytics: true,
        functional: true,
        marketing: true,
        timestamp: '2026-01-20T12:00:00Z',
        version: '0.9',
      }))
      expect(getConsent()).toEqual(DEFAULT_CONSENT)
    })

    it('should return default consent on parse error', () => {
      localStorage.setItem(COOKIE_CONSENT_KEY, 'not-json')
      expect(getConsent()).toEqual(DEFAULT_CONSENT)
    })
  })

  describe('saveConsent', () => {
    it('should save consent with timestamp and version', () => {
      const now = new Date()
      vi.setSystemTime(now)

      saveConsent({ analytics: true, functional: true })

      const stored = JSON.parse(localStorage.getItem(COOKIE_CONSENT_KEY) || '{}')
      expect(stored.analytics).toBe(true)
      expect(stored.functional).toBe(true)
      expect(stored.marketing).toBe(false)
      expect(stored.necessary).toBe(true)
      expect(stored.version).toBe(COOKIE_CONSENT_VERSION)
      expect(stored.timestamp).toBe(now.toISOString())

      vi.useRealTimers()
    })

    it('should always set necessary to true even if passed false', () => {
      saveConsent({ necessary: false } as any)

      const stored = JSON.parse(localStorage.getItem(COOKIE_CONSENT_KEY) || '{}')
      expect(stored.necessary).toBe(true)
    })
  })

  describe('acceptAllCookies', () => {
    it('should save consent with all categories enabled', () => {
      acceptAllCookies()

      const stored = JSON.parse(localStorage.getItem(COOKIE_CONSENT_KEY) || '{}')
      expect(stored.necessary).toBe(true)
      expect(stored.analytics).toBe(true)
      expect(stored.functional).toBe(true)
      expect(stored.marketing).toBe(true)
      expect(stored.timestamp).toBeTruthy()
    })
  })

  describe('acceptNecessaryOnly', () => {
    it('should save consent with only necessary cookies enabled', () => {
      acceptNecessaryOnly()

      const stored = JSON.parse(localStorage.getItem(COOKIE_CONSENT_KEY) || '{}')
      expect(stored.necessary).toBe(true)
      expect(stored.analytics).toBe(false)
      expect(stored.functional).toBe(false)
      expect(stored.marketing).toBe(false)
      expect(stored.timestamp).toBeTruthy()
    })
  })

  describe('clearConsent', () => {
    it('should remove consent from localStorage', () => {
      acceptAllCookies()
      expect(localStorage.getItem(COOKIE_CONSENT_KEY)).not.toBeNull()

      clearConsent()
      expect(localStorage.getItem(COOKIE_CONSENT_KEY)).toBeNull()
    })
  })

  describe('isCategoryAllowed', () => {
    it('should return true for necessary cookies always', () => {
      expect(isCategoryAllowed('necessary')).toBe(true)
    })

    it('should return false for analytics when not consented', () => {
      acceptNecessaryOnly()
      expect(isCategoryAllowed('analytics')).toBe(false)
    })

    it('should return true for analytics when consented', () => {
      acceptAllCookies()
      expect(isCategoryAllowed('analytics')).toBe(true)
    })

    it('should return correct values for all categories', () => {
      saveConsent({ analytics: true, functional: false, marketing: true })

      expect(isCategoryAllowed('necessary')).toBe(true)
      expect(isCategoryAllowed('analytics')).toBe(true)
      expect(isCategoryAllowed('functional')).toBe(false)
      expect(isCategoryAllowed('marketing')).toBe(true)
    })
  })

  describe('COOKIE_CATEGORIES', () => {
    it('should have necessary category as non-disableable', () => {
      const { COOKIE_CATEGORIES } = require('@/lib/cookieConsent')
      expect(COOKIE_CATEGORIES.necessary.canDisable).toBe(false)
    })

    it('should have other categories as disableable', () => {
      const { COOKIE_CATEGORIES } = require('@/lib/cookieConsent')
      expect(COOKIE_CATEGORIES.analytics.canDisable).toBe(true)
      expect(COOKIE_CATEGORIES.functional.canDisable).toBe(true)
      expect(COOKIE_CATEGORIES.marketing.canDisable).toBe(true)
    })
  })
})
