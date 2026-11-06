import { Check } from 'lucide-react'
import type { ReactNode } from 'react'
import type { TermMatch } from '../../lib/api'

/** The pasted English text with dictionary terms marked: teal with a check when the learner knows them, maroon when new. */
export function HighlightedText({
  text,
  matches,
  isKnown,
  knownLabel,
  newLabel,
}: {
  text: string
  matches: TermMatch[]
  isKnown: (en: string) => boolean
  knownLabel: string
  newLabel: string
}) {
  const parts: ReactNode[] = []
  let at = 0
  matches.forEach((m, i) => {
    if (m.start > at) parts.push(text.slice(at, m.start))
    const known = isKnown(m.en)
    parts.push(
      <mark
        key={i}
        className={`inline-flex items-baseline gap-1 rounded-t-md border-b-2 px-1 ${
          known ? 'border-teal bg-teal-soft font-semibold text-teal-text' : 'border-maroon bg-maroon-soft font-bold text-maroon-text'
        }`}
      >
        {known && <Check aria-hidden="true" size={12} strokeWidth={3} className="self-center" />}
        {text.slice(m.start, m.end)}
        <span className="sr-only"> ({known ? knownLabel : newLabel})</span>
      </mark>,
    )
    at = m.end
  })
  if (at < text.length) parts.push(text.slice(at))
  return <>{parts}</>
}
