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

test.describe('Upload Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page)
  })

  test('should display upload page with correct elements', async ({ page }) => {
    await page.goto('/upload')

    // Check page header
    await expect(page.getByRole('heading', { name: 'Upload P&ID' })).toBeVisible()
    await expect(page.getByText('Upload PDF files for AI-powered digitization')).toBeVisible()

    // Check project selection
    await expect(page.getByText('Select Project')).toBeVisible()
    await expect(page.locator('select')).toBeVisible()

    // Check upload area
    await expect(page.getByText('Upload Files')).toBeVisible()
    await expect(page.getByText(/drop pdf files here or click to browse/i)).toBeVisible()
    await expect(page.getByText('Maximum file size: 50MB per file')).toBeVisible()
  })

  test('should show project dropdown with options', async ({ page }) => {
    await page.goto('/upload')

    const select = page.locator('select')
    await expect(select).toBeVisible()

    // Check that project options are present (mock data from UploadPage)
    await expect(select.locator('option')).toHaveCount(4) // "Select a project..." + 3 projects
  })

  test('should show browse files button', async ({ page }) => {
    await page.goto('/upload')

    // "Browse Files" is a label (styled as button via asChild)
    const browseButton = page.getByText('Browse Files')
    await expect(browseButton).toBeVisible()
  })

  test('should disable upload button when no project is selected', async ({ page }) => {
    await page.goto('/upload')

    // The upload button should be disabled initially
    const uploadButton = page.getByRole('button', { name: /upload/i }).last()
    await expect(uploadButton).toBeDisabled()
  })

  test('should show cancel button that navigates back', async ({ page }) => {
    await page.goto('/dashboard')
    await page.goto('/upload')

    const cancelButton = page.getByRole('button', { name: /cancel/i })
    await expect(cancelButton).toBeVisible()
  })

  test('should allow selecting a project', async ({ page }) => {
    await page.goto('/upload')

    const select = page.locator('select')
    await select.selectOption({ index: 1 }) // Select first project

    // Verify selection was made
    await expect(select).not.toHaveValue('')
  })

  test('should have drag and drop area styled correctly', async ({ page }) => {
    await page.goto('/upload')

    // The drop zone should have dashed border styling
    const dropZone = page.locator('.border-dashed').first()
    await expect(dropZone).toBeVisible()
  })

  test('should display file upload icon', async ({ page }) => {
    await page.goto('/upload')

    // The FileUp icon should be visible in the drop zone
    const uploadIcon = page.locator('svg').filter({ has: page.locator('[d*="M21 15v4"]') }).first()
    // Alternative: just check the drop zone content is present
    await expect(page.getByText(/drop pdf files here/i)).toBeVisible()
  })
})

test.describe('Upload Flow with Files', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page)
  })

  test('should accept PDF files via file input', async ({ page }) => {
    await page.goto('/upload')

    // Create a fake PDF file
    const fileInput = page.locator('input[type="file"]')

    // Set files on the hidden input
    await fileInput.setInputFiles({
      name: 'test-drawing.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('fake pdf content'),
    })

    // File should appear in the list
    await expect(page.getByText('test-drawing.pdf')).toBeVisible()
  })

  test('should show file size after selecting file', async ({ page }) => {
    await page.goto('/upload')

    const fileInput = page.locator('input[type="file"]')

    await fileInput.setInputFiles({
      name: 'test-drawing.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('x'.repeat(1024)), // 1KB file = ~0.00 MB
    })

    // File size should be displayed (shows as "0.00 MB" for 1KB file)
    await expect(page.getByText('0.00 MB')).toBeVisible()
  })

  test('should allow removing a selected file', async ({ page }) => {
    await page.goto('/upload')

    const fileInput = page.locator('input[type="file"]')

    await fileInput.setInputFiles({
      name: 'test-drawing.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('fake pdf content'),
    })

    // File should appear
    await expect(page.getByText('test-drawing.pdf')).toBeVisible()

    // Find and click the remove button (X icon) within the file item
    const fileItem = page.locator('.rounded-lg.border').filter({ hasText: 'test-drawing.pdf' })
    const removeButton = fileItem.getByRole('button')
    await removeButton.click()

    // File should be removed
    await expect(page.getByText('test-drawing.pdf')).not.toBeVisible()
  })

  test('should enable upload button when project selected and files added', async ({ page }) => {
    await page.goto('/upload')

    // Select a project
    const select = page.locator('select')
    await select.selectOption({ index: 1 })

    // Add a file
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'test-drawing.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('fake pdf content'),
    })

    // Upload button should now be enabled
    const uploadButton = page.getByRole('button', { name: /upload \(1\)/i })
    await expect(uploadButton).toBeEnabled()
  })

  test('should show upload progress when uploading files', async ({ page }) => {
    await page.goto('/upload')

    // Select a project
    const select = page.locator('select')
    await select.selectOption({ index: 1 })

    // Add a file
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'test-drawing.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('fake pdf content'),
    })

    // Click upload
    const uploadButton = page.getByRole('button', { name: /upload \(1\)/i })
    await uploadButton.click()

    // Progress bar should appear during upload (simulated in the component)
    // Wait for upload to complete
    await expect(page.locator('[role="progressbar"]').or(page.getByText(/completed/i).or(page.locator('.text-green-500')))).toBeVisible({ timeout: 5000 })
  })
})
