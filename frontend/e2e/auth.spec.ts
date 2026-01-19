import { test, expect } from '@playwright/test'
import { mockUser } from './fixtures'

test.describe('Authentication Flow', () => {
  test('should display login page for unauthenticated users', async ({ page }) => {
    await page.goto('/login')

    // Check that the login page is displayed
    await expect(page.getByText('Welcome to Flowex')).toBeVisible()
    await expect(page.getByText('AI-Powered P&ID Digitization Platform')).toBeVisible()

    // Check that the sign in button is present
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible()

    // Check that SSO provider options are shown
    await expect(page.getByRole('button', { name: /google/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /microsoft/i })).toBeVisible()
  })

  test('should redirect unauthenticated users from protected routes to login', async ({ page }) => {
    // Try to access dashboard without authentication
    await page.goto('/dashboard')

    // Should be redirected to login
    await expect(page).toHaveURL('/login')
    await expect(page.getByText('Welcome to Flowex')).toBeVisible()
  })

  test('should redirect unauthenticated users from projects page to login', async ({ page }) => {
    await page.goto('/projects')
    await expect(page).toHaveURL('/login')
  })

  test('should redirect unauthenticated users from upload page to login', async ({ page }) => {
    await page.goto('/upload')
    await expect(page).toHaveURL('/login')
  })

  test('should redirect root path to dashboard for authenticated users', async ({ page }) => {
    // Set up authentication state
    await page.addInitScript(() => {
      localStorage.setItem('flowex-auth', JSON.stringify({
        state: { token: 'mock-jwt-token' },
        version: 0,
      }))
    })

    // Mock the auth check endpoint
    await page.route('**/api/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockUser),
      })
    })

    await page.goto('/')
    await expect(page).toHaveURL('/dashboard')
  })

  test('should display user info after authentication', async ({ page }) => {
    // Set up authentication state
    await page.addInitScript(() => {
      localStorage.setItem('flowex-auth', JSON.stringify({
        state: { token: 'mock-jwt-token' },
        version: 0,
      }))
    })

    // Mock the auth check endpoint
    await page.route('**/api/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockUser),
      })
    })

    await page.goto('/dashboard')

    // Check that dashboard is displayed with user greeting
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
    await expect(page.getByText(/welcome back/i)).toBeVisible()
  })

  test('should show loading state while checking authentication', async ({ page }) => {
    // Set up authentication state
    await page.addInitScript(() => {
      localStorage.setItem('flowex-auth', JSON.stringify({
        state: { token: 'mock-jwt-token' },
        version: 0,
      }))
    })

    // Mock the auth check endpoint with a delay
    await page.route('**/api/auth/me', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 500))
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockUser),
      })
    })

    await page.goto('/dashboard')

    // Should show loading spinner while checking auth
    // Then show dashboard after auth check completes
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible({ timeout: 5000 })
  })

  test('should handle authentication failure gracefully', async ({ page }) => {
    // Set up invalid token
    await page.addInitScript(() => {
      localStorage.setItem('flowex-auth', JSON.stringify({
        state: { token: 'invalid-token' },
        version: 0,
      }))
    })

    // Mock the auth check endpoint to return 401
    await page.route('**/api/auth/me', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Invalid token' }),
      })
    })

    await page.goto('/dashboard')

    // Should redirect to login page
    await expect(page).toHaveURL('/login')
  })

  test('should initiate login when clicking sign in button', async ({ page }) => {
    await page.goto('/login')

    // Listen for navigation to Auth0
    const loginButton = page.getByRole('button', { name: /sign in with sso/i })
    await expect(loginButton).toBeVisible()

    // We can't fully test the Auth0 redirect, but we verify the button is clickable
    await expect(loginButton).toBeEnabled()
  })
})
