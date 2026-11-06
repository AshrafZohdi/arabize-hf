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
  onPick,
}: {
  text: string
  matches: TermMatch[]
  isKnown: (en: string) => boolean
  knownLabel: string
  newLabel: string
  /** When set, each highlighted term is a button that opens its card. */
  onPick?: (m: TermMatch) => void
}) {
  const parts: ReactNode[] = []
  let at = 0
  matches.forEach((m, i) => {
    if (m.start > at) parts.push(text.slice(at, m.start))
    const known = isKnown(m.en)
    const body = (
      <>
        {known && <Check aria-hidden="true" size={12} strokeWidth={3} className="self-center" />}
        {text.slice(m.start, m.end)}
        <span className="sr-only"> ({known ? knownLabel : newLabel})</span>
      </>
    )
    const look = `inline-flex items-baseline gap-1 rounded-t-md border-b-2 px-1 ${
      known ? 'border-teal bg-teal-soft font-semibold text-teal-text' : 'border-maroon bg-maroon-soft font-bold text-maroon-text'
    }`
    parts.push(
      onPick ? (
        <button key={i} type="button" onClick={() => onPick(m)} className={`${look} cursor-pointer border-x-0 border-t-0 border-solid font-[inherit] text-[length:inherit] leading-[inherit]`}>
          {body}
        </button>
      ) : (
        <mark key={i} className={look}>
          {body}
        </mark>
      ),
    )
    at = m.end
  })
  if (at < text.length) parts.push(text.slice(at))
  return <>{parts}</>
}
