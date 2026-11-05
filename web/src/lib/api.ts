import type { ExplainLang } from './explainLang'

export type TermMatch = { start: number; end: number; text: string; id: string; en: string; ar: string; has_card: boolean }
export type Card = {
  id: string | null
  term_en: string
  term_ar: string
  term_gulf?: string | null
  explanation: string
  analogy: string
  mistake?: string
  related: string[]
  source: 'glossary' | 'fanar'
}
export type Question = { question: string; options: string[]; correct_index: number; why: string }
export type Fallback = 'waking' | 'demo' | 'unconfigured' | 'bad_output' | 'error' | null
export type ExplainResult = {
  off_topic?: boolean
  explanation: string | null
  question: Question | null
  cards: Card[]
  source: 'fanar' | 'fixture' | 'glossary'
  fallback: Fallback
}
export type ExplainStyle = 'school' | 'life' | 'technical' | 'one_line' | 'code' | 'sentences' | 'work'

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly retryAfter?: number,
  ) {
    super(`HTTP ${status}`)
  }
}

export async function findTerms(text: string, signal?: AbortSignal): Promise<TermMatch[]> {
  const r = await fetch('/api/terms', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ text }),
    signal,
  })
  if (!r.ok) throw new ApiError(r.status)
  return (await r.json()).matches
}

type ExplainHandlers = {
  onTerms: (matches: TermMatch[], cards: Card[]) => void
  onExplanation: (piece: string) => void
  onResult: (result: ExplainResult) => void
}

/** Parse one Server-Sent Events block ("event: x\ndata: {...}"). */
export function parseSseBlock(block: string): { event: string; data: unknown } | null {
  let event = 'message'
  const data: string[] = []
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) data.push(line.slice(5).trimStart())
  }
  if (!data.length) return null
  return { event, data: JSON.parse(data.join('\n')) }
}

export async function streamExplain(
  body: { text: string; lang: ExplainLang; style: ExplainStyle },
  handlers: ExplainHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const r = await fetch('/api/explain', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!r.ok || !r.body) throw new ApiError(r.status, Number(r.headers.get('retry-after')) || undefined)
  const reader = r.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let cut: number
    while ((cut = buffer.indexOf('\n\n')) !== -1) {
      const parsed = parseSseBlock(buffer.slice(0, cut))
      buffer = buffer.slice(cut + 2)
      if (!parsed) continue
      const d = parsed.data as Record<string, unknown>
      if (parsed.event === 'terms') handlers.onTerms(d.matches as TermMatch[], d.cards as Card[])
      else if (parsed.event === 'explanation') handlers.onExplanation(d.text as string)
      else if (parsed.event === 'result') handlers.onResult(d as unknown as ExplainResult)
    }
  }
}
