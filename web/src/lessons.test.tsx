import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { I18nProvider } from './i18n'
import { buildSteps } from './lib/lessonSteps'
import { ExerciseView } from './pages/Lesson'

// Every exercise in every lesson renders with visible words on every button and line (a word order exercise once
// rendered empty because its items were plain strings).
const lessons = import.meta.glob('../../content/day-*.json', { eager: true, import: 'default' }) as Record<
  string,
  { slug: string; blocks: { type: string; exercises?: Record<string, unknown>[] }[] }
>

afterEach(cleanup)

describe('lesson exercises', () => {
  const all = Object.values(lessons).flatMap((l) =>
    l.blocks.flatMap((b, bi) => (b.exercises ?? []).map((ex, ei) => ({ name: `${l.slug} block ${bi} exercise ${ei} (${ex.type})`, ex }))),
  )

  it('found all 7 lessons and their exercises', () => {
    expect(Object.keys(lessons)).toHaveLength(7)
    expect(all.length).toBe(21)
    for (const l of Object.values(lessons)) expect(buildSteps(l.blocks).length).toBeGreaterThan(5)
  })

  for (const lang of ['gulf', 'msa', 'en'] as const) {
    for (const { name, ex } of all) {
      it(`${name} in ${lang} has text on every control`, () => {
        render(
          <I18nProvider>
            <ExerciseView ex={ex as never} lang={lang} seed="t" onResult={() => {}} />
          </I18nProvider>,
        )
        const buttons = screen.getAllByRole('button')
        expect(buttons.length).toBeGreaterThan(1)
        for (const b of buttons) expect((b.textContent ?? '').trim() || b.getAttribute('aria-label')?.replace(/^[^:]*:\s*/, '').trim()).toBeTruthy()
        for (const li of document.querySelectorAll('li')) expect(li.textContent?.replace(/^\d+/, '').trim()).toBeTruthy()
      })
    }
  }
})
