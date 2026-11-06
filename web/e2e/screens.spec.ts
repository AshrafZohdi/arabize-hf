import { test } from '@playwright/test'
import { todaysWord } from './helpers'

// Pitch screenshots, only when SCREENSHOTS=1: every page, Arabic and English, at the project's viewport.
const EMAIL = 'Before you send the summary to the client, check it for hallucinations. Give the model more context in your prompt and ask it to cite the source paragraph.'
test.skip(!process.env.SCREENSHOTS, 'set SCREENSHOTS=1 to capture')

for (const lang of ['ar', 'en'] as const) {
  test(`screens ${lang}`, async ({ page }, info) => {
    await page.addInitScript((l) => {
      localStorage.clear()
      localStorage.setItem('darby.uiLang', l)
    }, lang)
    const dir = `../docs/screenshots/final/${info.project.name}-${lang}`
    await page.goto('/')
    await page.locator('#explain-input').fill(EMAIL)
    await page.locator('.btn-primary').first().click()
    // Wait for the finished answer: the quick question is the last part to arrive.
    await page.locator('#quiz-h').waitFor({ timeout: 20_000 })
    await page.locator('.btn-primary:not([disabled])').first().waitFor({ timeout: 20_000 })
    await page.screenshot({ path: `${dir}-home.png`, fullPage: true })
    // A viewport capture mid page shows the fixed page light and tab bar as a visitor sees them (kept out of the repo).
    await page.locator('#quiz-h').scrollIntoViewIfNeeded()
    await page.screenshot({ path: info.outputPath('home-scrolled.png') })
    await page.goto('/')
    await page.locator('#code-h').waitFor()
    await page.getByRole('group', { name: lang === 'ar' ? 'لغة الشيفرة' : 'Code language' }).getByRole('button', { name: 'EN' }).click()
    await page.locator('#code-input').fill(todaysWord())
    await page.locator('#code-input').press('Enter')
    await page.locator('#win-title').waitFor()
    await page.waitForTimeout(800)
    await page.screenshot({ path: `${dir}-code-win.png` })
    await page.goto('/this-page-does-not-exist')
    await page.waitForTimeout(500)
    await page.screenshot({ path: `${dir}-404.png` })
    await page.goto('/glossary')
    await page.locator('#full-h + p + ul li').first().waitFor()
    await page.screenshot({ path: `${dir}-glossary.png`, fullPage: false })
    await page.goto('/tutor?lesson=day-2')
    // The recorded demo question (fixtures match exact text), so DEMO_MODE answers it.
    await page.locator('#suggest-h').waitFor()
    await page.locator('#tutor-input').fill('شلون أعرف إن الـ AI قاعد يهلوس في التقرير؟')
    await page.locator('#tutor-input').press('Enter')
    await page.locator('[role="log"][aria-busy="false"] .bg-white\\/85').first().waitFor({ timeout: 20_000 })
    await page.screenshot({ path: `${dir}-tutor.png`, fullPage: false })
    await page.goto('/lesson/day-2')
    await page.locator('h1').first().waitFor()
    await page.screenshot({ path: `${dir}-lesson.png`, fullPage: false })
  })
}
