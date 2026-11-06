import { RotateCcw } from 'lucide-react'
import type { CSSProperties } from 'react'
import { useI18n } from '../../i18n'
import { useDictionary } from '../../lib/dictionary'
import { DAILY_GOAL, qatarDate, todayXp, useProgress } from '../../lib/progress'
import { Link } from '../../lib/router'

/** Saved terms from before today are due for a look. Hidden when there are none. */
export function ReviewBanner() {
  const { t } = useI18n()
  const { terms } = useDictionary()
  const today = qatarDate()
  const due = Object.values(terms).filter((s) => qatarDate(new Date(s.savedAt)) < today).length
  if (due === 0) return null
  return (
    <Link
      href="/glossary?mine=1"
      className="lift card-enter flex min-h-11 items-center gap-3 rounded-[20px] border border-gold/40 bg-gold-soft/90 py-2.5 ps-2.5 pe-5 text-gold-text no-underline shadow-[0_4px_0_var(--shadow)] hover:text-gold-text"
    >
      <span className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-gold text-white shadow-[0_3px_0_var(--gold-text)]">
        <RotateCcw aria-hidden="true" size={20} strokeWidth={2.5} />
      </span>
      <span className="flex flex-col leading-snug">
        <span className="font-bold">{t('review.due', { n: due })}</span>
        <span className="text-[13px]">{t('review.sub')}</span>
      </span>
    </Link>
  )
}

/** Today's points against the daily goal, as a ring. */
export function DailyGoal() {
  const { t } = useI18n()
  const progress = useProgress()
  const k = Math.min(todayXp(progress), DAILY_GOAL)
  const r = 17
  const c = 2 * Math.PI * r
  return (
    <div className="glass card-enter flex items-center gap-3 rounded-[20px]! py-2.5 ps-4 pe-2.5" style={{ '--i': 1 } as CSSProperties}>
      <span className="flex flex-col leading-snug">
        <span className="font-bold">{t('home.goalTitle')}</span>
        <span className="text-[13px] text-ink-2">{t('home.goalProgress', { k, n: DAILY_GOAL })}</span>
      </span>
      <svg aria-hidden="true" width="44" height="44" viewBox="0 0 44 44" className="-rotate-90 rtl:scale-y-[-1]">
        <circle cx="22" cy="22" r={r} fill="none" stroke="var(--gold-soft)" strokeWidth="5" />
        <circle cx="22" cy="22" r={r} fill="none" stroke="var(--gold)" strokeWidth="5" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - k / DAILY_GOAL)} />
        <circle cx="22" cy="22" r="5" fill="var(--gold-text)" />
      </svg>
    </div>
  )
}
