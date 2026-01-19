import { test, expect } from '@playwright/test'
import { mockUser } from './fixtures'

/**
 * Helper to set up authenticated state for tests.
 */
async function setupAuth(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    localStorage.setItem('flowex-auth', JSON.stringify({
      state: { token: 'mock-jwt-token' },
      version: 0,
    }))
  })

  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'test-user-id',
        email: 'test@example.com',
        name: 'Test User',
        role: 'admin',
        organizationId: 'test-org-id',
        organizationName: 'Test Organization',
      }),
    })
  })
}

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page)
  })

  test('should display dashboard with stats cards', async ({ page }) => {
    await page.goto('/dashboard')

    // Check that dashboard header is visible
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
    await expect(page.getByText(/welcome back/i)).toBeVisible()

    // Check that stats cards are displayed
    await expect(page.getByText('Total Projects')).toBeVisible()
    await expect(page.getByText('Total Drawings')).toBeVisible()
    await expect(page.getByText('Success Rate')).toBeVisible()
    await expect(page.getByText('Monthly Usage')).toBeVisible()
  })

  test('should display recent drawings section', async ({ page }) => {
    await page.goto('/dashboard')

    await expect(page.getByText('Recent Drawings')).toBeVisible()
    await expect(page.getByText('Your most recently uploaded drawings')).toBeVisible()
  })

  test('should display quick actions section', async ({ page }) => {
    await page.goto('/dashboard')

    await expect(page.getByText('Quick Actions')).toBeVisible()
    await expect(page.getByRole('link', { name: /upload new p&id/i })).toBeVisible()
    await expect(page.getByRole('link', { name: /create new project/i })).toBeVisible()
  })

  test('should navigate to upload page when clicking upload button', async ({ page }) => {
    await page.goto('/dashboard')

    // Click the main upload button in the header
    await page.getByRole('link', { name: /upload p&id/i }).first().click()

    await expect(page).toHaveURL('/upload')
  })

  test('should navigate to drawings page when clicking view all drawings', async ({ page }) => {
    await page.goto('/dashboard')

    await page.getByRole('link', { name: /view all drawings/i }).click()

    await expect(page).toHaveURL('/drawings')
  })

  test('should show progress bar for monthly usage', async ({ page }) => {
    await page.goto('/dashboard')

    // The Progress component from shadcn/ui renders with role="progressbar"
    const progressBar = page.locator('[role="progressbar"]').first()
    await expect(progressBar).toBeVisible()
  })
})
