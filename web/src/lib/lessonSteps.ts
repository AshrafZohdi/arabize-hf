// Pure lesson logic: which text to show, the order of steps, and missed exercises coming back before the recap.

export type Texts = { en?: string; ar?: string; gulf?: string }
export type ExplainLang = 'en' | 'msa' | 'gulf'

/** Gulf falls back to simple Arabic; English falls back to Arabic only when a block has no English. */
export function pick(texts: Texts | undefined, lang: ExplainLang): { text: string; lang: 'en' | 'ar' } {
  if (!texts) return { text: '', lang: 'ar' }
  if (lang === 'en' && texts.en) return { text: texts.en, lang: 'en' }
  const ar = (lang === 'gulf' && texts.gulf) || texts.ar || texts.gulf || ''
  if (ar) return { text: ar, lang: 'ar' }
  return { text: texts.en ?? '', lang: 'en' }
}

export type Segment = { text: string } | { term: string; label: string }

/** Lesson text marks glossary terms as [[Prompt]] or [[Prompt|الأمر]]. */
export function segments(text: string): Segment[] {
  const out: Segment[] = []
  const re = /\[\[([^|\]]+)(?:\|([^\]]+))?\]\]/g
  let at = 0
  for (const m of text.matchAll(re)) {
    if (m.index! > at) out.push({ text: text.slice(at, m.index) })
    out.push({ term: m[1], label: m[2] ?? m[1] })
    at = m.index! + m[0].length
  }
  if (at < text.length) out.push({ text: text.slice(at) })
  return out
}

export type Step = { kind: 'block'; block: number } | { kind: 'exercise'; block: number; index: number; retry: boolean }

/** One step per screen: each exercise is its own step; recap comes last. */
export function buildSteps(blocks: { type: string; exercises?: unknown[] }[]): Step[] {
  const steps: Step[] = []
  blocks.forEach((b, i) => {
    if (b.type === 'exercise') (b.exercises ?? []).forEach((_, j) => steps.push({ kind: 'exercise', block: i, index: j, retry: false }))
    else steps.push({ kind: 'block', block: i })
  })
  return steps
}

/** Put missed exercises back in front of the recap (the last step), once each. `at` is the step about to be shown:
 * call it when the learner reaches the recap. */
export function withRetries(steps: Step[], missed: Step[], at: number): Step[] {
  const recap = steps.length - 1
  if (!missed.length || at > recap) return steps
  const retries = missed.map((s) => ({ ...s, retry: true }) as Step)
  return [...steps.slice(0, recap), ...retries, ...steps.slice(recap)]
}

/** Same shuffle every time for the same seed, so the screen does not jump on re-render. */
export function seededShuffle<T>(items: T[], seed: string): T[] {
  let h = 2166136261
  for (const c of seed) h = Math.imul(h ^ c.charCodeAt(0), 16777619)
  const out = items.slice()
  for (let i = out.length - 1; i > 0; i--) {
    h = Math.imul(h ^ (h >>> 13), 1274126177)
    const j = Math.abs(h) % (i + 1)
    ;[out[i], out[j]] = [out[j], out[i]]
  }
  return out
}

export function termSlug(term: string): string {
  return term
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}
