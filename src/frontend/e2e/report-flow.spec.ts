import { Buffer } from 'node:buffer'

import { expect, test, type Page } from '@playwright/test'

const REQUIRED_FIELDS: ReadonlyArray<{ label: string; value: string }> = [
  { label: 'Testing Date', value: '2026-02' },
  { label: 'Building Name', value: 'Acacia Residences' },
  { label: 'Building Location', value: 'Makati City' },
  { label: 'Number of Storey', value: '12' },
  { label: 'Rebar Scan Locations', value: '3' },
  { label: 'Rebound Hammer Test Locations', value: '4' },
  { label: 'Coring Locations', value: '2' },
  { label: 'Rebar Samples Extracted', value: '2' },
  { label: 'Non-shrink Grout Product', value: 'SikaGrout 214' },
  { label: 'Epoxy A&B Product', value: 'Sikadur-31' },
  { label: 'Foundation Locations', value: '3' },
  { label: 'Extracted Foundation Cores', value: '3' },
  { label: 'Prepared By', value: 'Jane Dela Cruz' },
  { label: 'Role', value: 'Structural Engineer' },
]

const sampleImageBase64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO8BfYcAAAAASUVORK5CYII='

async function fillRequiredFormFields(page: Page): Promise<void> {
  for (const field of REQUIRED_FIELDS) {
    await page.getByLabel(field.label).fill(field.value)
  }
}

async function uploadRequiredPhotoGroups(page: Page): Promise<void> {
  const uploadInputs = page.locator('.upload-dropzone__input')
  const groupCount = await uploadInputs.count()

  expect(groupCount).toBeGreaterThan(0)

  const imagePayload = {
    name: 'sample.png',
    mimeType: 'image/png',
    buffer: Buffer.from(sampleImageBase64, 'base64'),
  }

  for (let index = 0; index < groupCount; index += 1) {
    await uploadInputs.nth(index).setInputFiles(imagePayload)
  }
}

test('completes intake and generates report download url', async ({ page }) => {
  test.slow()

  await page.goto('/')
  await fillRequiredFormFields(page)
  await uploadRequiredPhotoGroups(page)

  const continueToConfirmationButton = page.getByRole('button', {
    name: 'Continue to Confirmation',
  })

  await expect(continueToConfirmationButton).toBeEnabled()
  await continueToConfirmationButton.click()

  await expect(page).toHaveURL(/\/confirm$/)

  const continueToGenerateButton = page.getByRole('button', {
    name: 'Continue and Generate PDF',
  })

  await expect(continueToGenerateButton).toBeEnabled()
  await continueToGenerateButton.click()

  await expect(page.getByText('Report generated. A new tab was opened for download.')).toBeVisible({
    timeout: 60_000,
  })
  await expect(page.getByText(/Download URL: \/reports\/[0-9a-f-]+\/download/)).toBeVisible({
    timeout: 60_000,
  })
})
