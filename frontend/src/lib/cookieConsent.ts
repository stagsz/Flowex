/**
 * Cookie consent management utility for GDPR compliance.
 * Handles storage and retrieval of user cookie preferences.
 *
 * Cookie Categories (per GDPR requirements):
 * - necessary: Always enabled, required for basic functionality
 * - analytics: Performance and usage tracking
 * - functional: Enhanced features like preferences and personalization
 * - marketing: Advertising and marketing cookies (currently not used)
 */

export interface CookieConsent {
  necessary: boolean // Always true, cannot be disabled
  analytics: boolean
  functional: boolean
  marketing: boolean
  timestamp: string // ISO date string of when consent was given
  version: string // Consent version for re-prompting on policy changes
}

export const COOKIE_CONSENT_KEY = "flowex-cookie-consent"
export const COOKIE_CONSENT_VERSION = "1.0"

/**
 * Default consent state - only necessary cookies enabled
 */
export const DEFAULT_CONSENT: CookieConsent = {
  necessary: true,
  analytics: false,
  functional: false,
  marketing: false,
  timestamp: "",
  version: COOKIE_CONSENT_VERSION,
}

/**
 * Check if consent has been given (any decision made)
 */
export function hasConsentDecision(): boolean {
  try {
    const stored = localStorage.getItem(COOKIE_CONSENT_KEY)
    if (!stored) return false

    const consent = JSON.parse(stored) as CookieConsent
    // Re-prompt if consent version has changed
    return consent.version === COOKIE_CONSENT_VERSION && !!consent.timestamp
  } catch {
    return false
  }
}

/**
 * Get the current consent preferences
 */
export function getConsent(): CookieConsent {
  try {
    const stored = localStorage.getItem(COOKIE_CONSENT_KEY)
    if (!stored) return DEFAULT_CONSENT

    const consent = JSON.parse(stored) as CookieConsent
    // If version mismatch, return defaults
    if (consent.version !== COOKIE_CONSENT_VERSION) {
      return DEFAULT_CONSENT
    }
    return consent
  } catch {
    return DEFAULT_CONSENT
  }
}

/**
 * Save consent preferences
 */
export function saveConsent(consent: Partial<CookieConsent>): void {
  const fullConsent: CookieConsent = {
    ...DEFAULT_CONSENT,
    ...consent,
    necessary: true, // Always required
    timestamp: new Date().toISOString(),
    version: COOKIE_CONSENT_VERSION,
  }
  localStorage.setItem(COOKIE_CONSENT_KEY, JSON.stringify(fullConsent))
}

/**
 * Accept all cookies
 */
export function acceptAllCookies(): void {
  saveConsent({
    necessary: true,
    analytics: true,
    functional: true,
    marketing: true,
  })
}

/**
 * Accept only necessary cookies (reject optional)
 */
export function acceptNecessaryOnly(): void {
  saveConsent({
    necessary: true,
    analytics: false,
    functional: false,
    marketing: false,
  })
}

/**
 * Clear consent (useful for testing or user-requested reset)
 */
export function clearConsent(): void {
  localStorage.removeItem(COOKIE_CONSENT_KEY)
}

/**
 * Check if a specific cookie category is allowed
 */
export function isCategoryAllowed(category: keyof Omit<CookieConsent, "timestamp" | "version">): boolean {
  const consent = getConsent()
  return consent[category]
}

/**
 * Cookie category descriptions for UI display
 */
export const COOKIE_CATEGORIES = {
  necessary: {
    name: "Strictly Necessary",
    description:
      "These cookies are essential for the website to function properly. They enable core functionality such as security, authentication, and session management. You cannot disable these cookies.",
    canDisable: false,
  },
  analytics: {
    name: "Analytics",
    description:
      "These cookies help us understand how visitors interact with our website by collecting and reporting information anonymously. This helps us improve our service.",
    canDisable: true,
  },
  functional: {
    name: "Functional",
    description:
      "These cookies enable enhanced functionality and personalization, such as remembering your preferences and settings. If you disable these, some features may not work properly.",
    canDisable: true,
  },
  marketing: {
    name: "Marketing",
    description:
      "These cookies are used to track visitors across websites to display relevant advertisements. We currently do not use marketing cookies, but this option is available for future use.",
    canDisable: true,
  },
} as const
