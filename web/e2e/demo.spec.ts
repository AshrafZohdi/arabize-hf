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
  await expect(chips).toHaveText(['Prompt', 'Hallucination', 'Context', 'Summary', 'Source'], { useInnerText: true })
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
  await page.keyboard.press('Escape')
  await page.getByRole('button', { name: 'رجوع' }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'البداية' })).toBeVisible()
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '1')
  await noHorizontalScroll(page)
})

test('lesson: picks up where you left off, and the step list jumps back', async ({ page }) => {
  await page.goto('/lesson/day-2')
  await page.getByRole('button', { name: 'التالي' }).click()
  await page.getByRole('button', { name: 'التالي' }).click()
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '3')
  // Leave and come back inside the app (a full reload would run the storage reset in beforeEach).
  await page.getByRole('link', { name: 'اطلع من الدرس' }).click()
  await expect(page.locator('#explain-h')).toBeVisible()
  await page.evaluate(() => {
    history.pushState(null, '', '/lesson/day-2')
    dispatchEvent(new PopStateEvent('popstate'))
  })
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '3')
  // Narrow screens keep the step list in a collapsed section.
  const steps = page.locator('summary', { hasText: 'خطوات الدرس' })
  if (await steps.isVisible()) await steps.click()
  await page.getByRole('button', { name: /^1البداية|البداية/ }).filter({ visible: true }).first().click()
  await expect(page.getByRole('heading', { level: 1, name: 'البداية' })).toBeVisible()
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '1')
})

test('image features show when switched on and fail gently without their endpoints', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('button', { name: 'صوّر أو ارفع صورة' })).toBeVisible()
  await page.goto('/tutor?tab=image')
  await expect(page.getByRole('heading', { name: 'مختبر أوامر الصور' })).toBeVisible()
  await page.getByLabel('أمرك للصورة').fill('مكتب في الدوحة')
  await page.getByRole('button', { name: 'قيّم أمري' }).click()
  await expect(page.getByRole('alert')).toBeVisible()
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
