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
      body: JSON.stringify(mockUser),
    })
  })
}

test.describe('Main Layout', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page)
  })

  test('should display header with Flowex logo', async ({ page }) => {
    await page.goto('/dashboard')

    // Header should have Flowex branding
    await expect(page.getByText('Flowex')).toBeVisible()
  })

  test('should display sidebar navigation', async ({ page }) => {
    await page.goto('/dashboard')

    // Sidebar navigation items (scoped to aside element)
    const sidebar = page.locator('aside')
    await expect(sidebar.getByRole('link', { name: 'Dashboard' })).toBeVisible()
    await expect(sidebar.getByRole('link', { name: 'Projects' })).toBeVisible()
    await expect(sidebar.getByRole('link', { name: 'Drawings' })).toBeVisible()
    await expect(sidebar.getByRole('link', { name: 'Upload' })).toBeVisible()
  })

  test('should display secondary navigation in sidebar', async ({ page }) => {
    await page.goto('/dashboard')

    await expect(page.getByRole('link', { name: /settings/i })).toBeVisible()
    await expect(page.getByRole('link', { name: /help/i })).toBeVisible()
  })

  test('should show user avatar in header when authenticated', async ({ page }) => {
    await page.goto('/dashboard')

    // Avatar button should be visible
    const avatarButton = page.locator('button').filter({ has: page.locator('[role="img"]') }).or(
      page.locator('.rounded-full').first()
    )
    await expect(avatarButton).toBeVisible()
  })

  test('should highlight active navigation item', async ({ page }) => {
    await page.goto('/dashboard')

    // Dashboard link should have active styling (bg-primary) - scoped to sidebar
    const sidebar = page.locator('aside')
    const dashboardLink = sidebar.getByRole('link', { name: 'Dashboard' })
    await expect(dashboardLink).toHaveClass(/bg-primary/)
  })
})

test.describe('Sidebar Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page)
  })

  test('should navigate to Dashboard', async ({ page }) => {
    await page.goto('/projects')

    const sidebar = page.locator('aside')
    await sidebar.getByRole('link', { name: 'Dashboard' }).click()

    await expect(page).toHaveURL('/dashboard')
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  })

  test('should navigate to Projects', async ({ page }) => {
    await page.goto('/dashboard')

    const sidebar = page.locator('aside')
    await sidebar.getByRole('link', { name: 'Projects' }).click()

    await expect(page).toHaveURL('/projects')
  })

  test('should navigate to Drawings', async ({ page }) => {
    await page.goto('/dashboard')

    const sidebar = page.locator('aside')
    await sidebar.getByRole('link', { name: 'Drawings' }).click()

    await expect(page).toHaveURL('/drawings')
  })

  test('should navigate to Upload', async ({ page }) => {
    await page.goto('/dashboard')

    const sidebar = page.locator('aside')
    await sidebar.getByRole('link', { name: 'Upload' }).click()

    await expect(page).toHaveURL('/upload')
  })

  test('should navigate to Settings', async ({ page }) => {
    await page.goto('/dashboard')

    const sidebar = page.locator('aside')
    await sidebar.getByRole('link', { name: 'Settings' }).click()

    // Settings links to /settings/integrations
    await expect(page).toHaveURL('/settings/integrations')
  })
})

test.describe('Header User Menu', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page)
  })

  test('should open dropdown menu when clicking avatar', async ({ page }) => {
    await page.goto('/dashboard')

    // Click on avatar/user button in header (button with rounded-full class)
    const avatarButton = page.locator('header button.rounded-full')
    await avatarButton.click()

    // Dropdown should show user info and menu items - use exact matching
    await expect(page.getByText(mockUser.name, { exact: true })).toBeVisible()
    await expect(page.getByText(mockUser.email, { exact: true })).toBeVisible()
  })

  test('should show profile, settings, help, and logout in dropdown', async ({ page }) => {
    await page.goto('/dashboard')

    // Open dropdown
    const avatarButton = page.locator('header button.rounded-full')
    await avatarButton.click()

    // Check menu items
    await expect(page.getByRole('menuitem', { name: /profile/i })).toBeVisible()
    await expect(page.getByRole('menuitem', { name: /settings/i })).toBeVisible()
    await expect(page.getByRole('menuitem', { name: /help/i })).toBeVisible()
    await expect(page.getByRole('menuitem', { name: /log out/i })).toBeVisible()
  })

  test('should navigate home when clicking Flowex logo', async ({ page }) => {
    await page.goto('/projects')

    // Click on Flowex logo/brand in header
    await page.getByRole('link', { name: /flowex/i }).click()

    await expect(page).toHaveURL('/dashboard')
  })
})

test.describe('Responsive Layout', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page)
  })

  test('should show sidebar on desktop viewport', async ({ page }) => {
    // Set desktop viewport
    await page.setViewportSize({ width: 1280, height: 720 })
    await page.goto('/dashboard')

    // Sidebar should be visible (has md:flex class, visible from md breakpoint)
    const sidebar = page.locator('aside')
    await expect(sidebar).toBeVisible()
  })

  test('should hide sidebar on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/dashboard')

    // Sidebar should be hidden on mobile (has hidden class)
    const sidebar = page.locator('aside')
    await expect(sidebar).toBeHidden()
  })
})
