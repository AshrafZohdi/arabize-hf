import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { todaysWord } from './helpers'

// WCAG 2.2 AA checks with axe on every page, Arabic interface. Serious and critical issues fail the test.
const PAGES = ['/', '/glossary', '/tutor', '/tutor?tab=lab&lesson=day-2', '/lesson/day-1', '/no-such-page']

async function seriousIssues(page: import('@playwright/test').Page) {
  const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze()
  const bad = result.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
  return bad.map((v) => `${v.id}: ${v.nodes.length} (${v.nodes[0]?.target.join(' ')})`)
}

test('no serious accessibility issues: daily code win dialog', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('group', { name: 'لغة الشيفرة' }).getByRole('button', { name: 'EN' }).click()
  await page.locator('#code-input').fill(todaysWord())
  await page.locator('#code-input').press('Enter')
  await page.locator('#win-title').waitFor()
  await page.waitForTimeout(800)
  expect(await seriousIssues(page)).toEqual([])
})

for (const path of PAGES) {
  test(`no serious accessibility issues: ${path}`, async ({ page }) => {
    await page.goto(path)
    await page.waitForLoadState('networkidle')
    expect(await seriousIssues(page)).toEqual([])
  })
}
