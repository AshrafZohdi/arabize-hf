import { expect, test, type Page } from '@playwright/test'

const EMAIL = 'Before you send the summary to the client, check it for hallucinations. Give the model more context in your prompt and ask it to cite the source paragraph.'

async function noHorizontalScroll(page: Page) {
  const [client, scroll] = await page.evaluate(() => [document.documentElement.clientWidth, document.documentElement.scrollWidth])
  expect(scroll, 'page must not scroll sideways').toBeLessThanOrEqual(client)
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.clear())
})

test('home: Smart Explain end to end in Gulf Arabic', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
  await page.getByLabel('النص اللي وصلك').fill(EMAIL)
  await expect(page.getByText(/مصطلحات، 0 منها في قاموسك/)).toBeVisible()
  await page.getByRole('button', { name: 'فهّمني' }).click()
  await expect(page.getByRole('heading', { name: 'شنو يعني النص' })).toBeVisible({ timeout: 20_000 })
  await expect(page.getByRole('heading', { name: 'سؤال سريع' })).toBeVisible({ timeout: 20_000 })
  await page.getByRole('button', { name: 'Hallucination', exact: true }).last().click()
  await expect(page.getByText('صح!')).toBeVisible()
  await expect(page.getByText(/20 نقطة|15 نقطة/).first()).toBeVisible()
  await noHorizontalScroll(page)
})

test('home: every highlighted term has a chip, and tapping one opens it', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('النص اللي وصلك').fill(EMAIL)
  await page.getByRole('button', { name: 'فهّمني' }).click()
  await expect(page.getByRole('heading', { name: 'سؤال سريع' })).toBeVisible({ timeout: 20_000 })
  const chips = page.getByRole('group', { name: 'المصطلحات' }).getByRole('button')
  await expect(chips).toHaveText(['Hallucination', 'Prompt', 'Context', 'Summary', 'Source'], { useInnerText: true })
  await page.getByRole('button', { name: /^context/ }).click()
  await expect(chips.filter({ hasText: 'Context' })).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByRole('heading', { name: 'السياق' })).toBeVisible()
})

test('glossary: Arabic search and the full card', async ({ page }) => {
  await page.goto('/glossary')
  await page.getByLabel('دوّر على مصطلح').fill('الهلوسة')
  // Search waits 250 ms after typing; until then the browse list (A to Z) is on screen.
  const results = page.getByRole('region', { name: /نتيجة/ })
  await expect(results.getByText('Hallucination').first()).toBeVisible()
  await results.getByRole('button', { name: 'افتح البطاقة' }).first().click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByRole('heading', { name: 'الهلوسة' })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(dialog).toBeHidden()
  await noHorizontalScroll(page)
})

test('tutor answers in Gulf Arabic and the prompt lab scores a prompt', async ({ page }) => {
  await page.goto('/tutor?lesson=day-1')
  await page.getByLabel('اكتب سؤالك هنا').fill('شلون أعرف إن الـ AI قاعد يهلوس في التقرير؟')
  await page.getByRole('button', { name: 'أرسل' }).click()
  await expect(page.getByRole('log')).toContainText('هلوس', { timeout: 20_000 })
  await page.goto('/tutor?tab=lab&lesson=day-2')
  await page.getByLabel('أمرك (برومبت)').fill('اكتب إيميل عن سياسة الإجازات الجديدة')
  await page.getByRole('button', { name: 'قيّم أمري' }).click()
  await expect(page.getByRole('img', { name: /المجموع: \d+ من 20/ })).toBeVisible({ timeout: 30_000 })
  await noHorizontalScroll(page)
})

test('daily code: a real word is marked, the answer is not revealed', async ({ page }) => {
  await page.goto('/')
  const start = await (await page.request.get('/api/daily-code?lang=en')).json()
  await page.getByLabel('خمّن الكلمة').fill('a'.repeat(start.length))
  await page.getByRole('button', { name: 'جرّب' }).click()
  await expect(page.getByText('مو كلمة معروفة. ما انحسبت عليك.')).toBeVisible()
  await expect(page.getByText(/باقي 6 محاولات|باقي 6 محاولة/)).toBeHidden()
})

test('lesson: steps, a tappable term, the progress bar', async ({ page }) => {
  await page.goto('/lesson/day-1')
  await expect(page.getByRole('progressbar')).toBeVisible()
  await page.getByRole('button', { name: 'التالي' }).click()
  await page.getByRole('button', { name: 'هلوسة' }).click()
  await expect(page.getByRole('dialog')).toContainText('Hallucination')
  await noHorizontalScroll(page)
})

test('English interface switches to LTR', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: /English/ }).click()
  await expect(page.locator('html')).toHaveAttribute('dir', 'ltr')
  await expect(page.getByRole('navigation', { name: 'Sections' })).toBeVisible()
  await noHorizontalScroll(page)
})

for (const lang of ['ar', 'en'] as const) {
  test(`no page scrolls sideways (${lang})`, async ({ page }) => {
    await page.addInitScript((l) => localStorage.setItem('darby.uiLang', l), lang)
    for (const path of ['/', '/glossary', '/tutor?lesson=day-2', '/tutor?tab=lab&lesson=day-2', '/lesson/day-2', '/no-such-page']) {
      await page.goto(path)
      await page.waitForLoadState('networkidle')
      await noHorizontalScroll(page)
    }
  })
}
