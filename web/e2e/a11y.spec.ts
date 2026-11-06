import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

// WCAG 2.2 AA checks with axe on every page, Arabic interface. Serious and critical issues fail the test.
const PAGES = ['/', '/glossary', '/tutor', '/tutor?tab=lab&lesson=day-2', '/lesson/day-1']

for (const path of PAGES) {
  test(`no serious accessibility issues: ${path}`, async ({ page }) => {
    await page.goto(path)
    await page.waitForLoadState('networkidle')
    const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze()
    const bad = result.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
    expect(bad.map((v) => `${v.id}: ${v.nodes.length} (${v.nodes[0]?.target.join(' ')})`)).toEqual([])
  })
}
