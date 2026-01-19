import { test as base, expect } from '@playwright/test'

/**
 * Mock user data for authenticated tests.
 */
export const mockUser = {
  id: 'test-user-id',
  email: 'test@example.com',
  name: 'Test User',
  role: 'admin' as const,
  organizationId: 'test-org-id',
  organizationName: 'Test Organization',
}

/**
 * Extended test fixture that handles authentication mocking.
 */
export const test = base.extend<{
  authenticatedPage: typeof base
}>({
  authenticatedPage: async ({ page }, use) => {
    // Set up authentication state in localStorage before navigating
    await page.addInitScript(() => {
      const authState = {
        state: {
          token: 'mock-jwt-token',
        },
        version: 0,
      }
      localStorage.setItem('flowex-auth', JSON.stringify(authState))
    })

    // Mock the /api/auth/me endpoint to return the mock user
    await page.route('**/api/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockUser),
      })
    })

    await use(base)
  },
})

export { expect }
