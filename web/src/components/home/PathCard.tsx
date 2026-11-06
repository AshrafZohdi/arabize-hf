import { Check, Clock, Lock, Trophy } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useI18n } from '../../i18n'
import { listLessons, type LessonSummary } from '../../lib/api'
import { useExplainLang } from '../../lib/explainLang'
import { pathStates, useLessonProgress, type PathState } from '../../lib/lessonProgress'
import { Link } from '../../lib/router'

/** دربك: the 7 lessons in order on a rail, done, current and locked. */
export function PathCard() {
  const { t, lang: uiLang } = useI18n()
  const [lang] = useExplainLang()
  const { done } = useLessonProgress()
  const [lessons, setLessons] = useState<LessonSummary[]>([])

  useEffect(() => {
    listLessons().then(setLessons).catch(() => {})
  }, [])

  const states = pathStates(lessons.map((l) => l.slug), done)
  const title = (l: LessonSummary) => (uiLang === 'en' ? l.title.en : lang === 'gulf' ? l.title.gulf || l.title.ar : l.title.ar)

  return (
    <section aria-labelledby="path-h" className="card">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 id="path-h" className="m-0 flex items-center gap-2 font-display text-[22px] font-semibold text-maroon">
          <Trophy aria-hidden="true" size={20} />
          {t('home.pathTitle')}
        </h2>
        {lessons.length > 0 && (
          <span className="rounded-full bg-surface-3/80 px-3 py-1 text-sm font-semibold text-ink-2">{t('path.progress', { k: done.length, n: lessons.length })}</span>
        )}
      </div>
      <ol className="relative m-0 flex list-none flex-col gap-3 p-0">
        {/* The rail behind the nodes. */}
        <span aria-hidden="true" className="absolute inset-y-5 start-5 w-0.5 -translate-x-1/2 bg-line rtl:translate-x-1/2" />
        {lessons.map((l, i) => (
          <PathRow key={l.slug} n={i + 1} slug={l.slug} title={title(l)} state={states[i]} minutes={l.est_minutes ?? 10} />
        ))}
      </ol>
    </section>
  )
}

function PathRow({ n, slug, title, state, minutes }: { n: number; slug: string; title: string; state: PathState; minutes: number }) {
  const { t } = useI18n()
  const node =
    state === 'done' ? (
      <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-success text-white shadow-[0_3px_0_var(--success-text)]">
        <Check aria-hidden="true" size={18} strokeWidth={3} />
      </span>
    ) : state === 'current' ? (
      <span className="path-glow flex size-10 shrink-0 items-center justify-center rounded-full bg-maroon font-en font-bold text-white shadow-[0_3px_0_var(--maroon-deep)]">
        {n}
      </span>
    ) : (
      <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-locked text-muted">
        <Lock aria-hidden="true" size={18} />
      </span>
    )
  const status = state === 'done' ? t('path.done') : state === 'current' ? t('path.current', { m: minutes }) : t('path.locked')
  const text = (
    <span className="min-w-0 flex-auto">
      <span className={`block text-[15px] leading-snug ${state === 'current' ? 'font-bold' : 'font-semibold'} ${state === 'locked' ? 'text-ink-2' : ''}`}>{title}</span>
      <span className={`flex items-center gap-1 text-[13px] ${state === 'current' ? 'text-maroon-deep' : 'text-muted'}`}>
        {state === 'current' && <Clock aria-hidden="true" size={13} />}
        {status}
      </span>
    </span>
  )
  return (
    <li className="relative flex items-center gap-3">
      {node}
      {state === 'locked' ? (
        <span className="flex min-h-11 flex-auto items-center px-1">{text}</span>
      ) : (
        <Link
          href={`/lesson/${slug}`}
          className={`lift flex min-h-11 flex-auto items-center gap-2 rounded-2xl px-3 py-2 text-ink no-underline hover:text-ink ${
            state === 'current' ? 'border border-white/80 bg-white/85 shadow-[0_4px_0_var(--shadow)]' : 'hover:bg-white/50'
          }`}
        >
          {text}
          <span className={`shrink-0 text-sm font-bold ${state === 'current' ? 'rounded-xl bg-maroon px-3 py-2 text-white shadow-[0_3px_0_var(--maroon-deep)]' : 'text-maroon'}`}>
            {state === 'current' ? t('path.continue') : t('path.review')}
          </span>
        </Link>
      )}
    </li>
  )
}
