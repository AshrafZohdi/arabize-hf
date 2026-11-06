import { describe, expect, it } from 'vitest'
import { buildSteps, pick, seededShuffle, segments, termSlug, withRetries } from './lessonSteps'

describe('lesson steps', () => {
  it('picks text with Gulf falling back to Arabic', () => {
    expect(pick({ en: 'E', ar: 'ع' }, 'gulf')).toEqual({ text: 'ع', lang: 'ar' })
    expect(pick({ en: 'E', ar: 'ع', gulf: 'خ' }, 'gulf')).toEqual({ text: 'خ', lang: 'ar' })
    expect(pick({ ar: 'ع' }, 'en')).toEqual({ text: 'ع', lang: 'ar' })
  })

  it('splits glossary markup', () => {
    expect(segments('Use a [[Prompt]] and [[Context|السياق]].')).toEqual([
      { text: 'Use a ' },
      { term: 'Prompt', label: 'Prompt' },
      { text: ' and ' },
      { term: 'Context', label: 'السياق' },
      { text: '.' },
    ])
  })

  it('one step per exercise, missed ones before the recap', () => {
    const steps = buildSteps([{ type: 'hook' }, { type: 'exercise', exercises: [1, 2] }, { type: 'recap' }])
    expect(steps.map((s) => s.kind)).toEqual(['block', 'exercise', 'exercise', 'block'])
    const again = withRetries(steps, [steps[1]], 3)
    expect(again.length).toBe(5)
    expect(again[3]).toMatchObject({ kind: 'exercise', index: 0, retry: true })
    expect(again[4]).toEqual(steps[3])
  })

  it('shuffles the same way for the same seed', () => {
    const a = seededShuffle([1, 2, 3, 4, 5], 'day-2:0')
    expect(seededShuffle([1, 2, 3, 4, 5], 'day-2:0')).toEqual(a)
    expect([...a].sort()).toEqual([1, 2, 3, 4, 5])
  })

  it('makes glossary ids', () => {
    expect(termSlug('Output format')).toBe('output-format')
    expect(termSlug('Fact-check')).toBe('fact-check')
  })
})
