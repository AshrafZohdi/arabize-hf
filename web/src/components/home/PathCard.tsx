import { Check, Lock, Star } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useI18n } from '../../i18n'
import { listLessons, type LessonSummary } from '../../lib/api'
import { useExplainLang } from '../../lib/explainLang'
import { pathStates, useLessonProgress, type PathState } from '../../lib/lessonProgress'
import { Link } from '../../lib/router'

/** دربك: the 7 lessons in order, done, current and locked. */
export function PathCard() {
  const { t, lang: uiLang } = useI18n()
  const [lang] = useExplainLang()
  const { done } = useLessonProgress()
  const [lessons, setLessons] = useState<LessonSummary[]>([])
  const [all, setAll] = useState(false)

  useEffect(() => {
    listLessons().then(setLessons).catch(() => {})
  }, [])

  const states = pathStates(lessons.map((l) => l.slug), done)
  const current = states.indexOf('current')
  // Collapsed: the lesson before the current one, the current one and the next.
  const focus = current === -1 ? lessons.length - 1 : current
  const shown = lessons.map((l, i) => ({ l, s: states[i], i })).filter(({ i }) => all || (i >= focus - 1 && i <= focus + 1))
  const title = (l: LessonSummary) => (uiLang === 'en' ? l.title.en : lang === 'gulf' ? l.title.gulf || l.title.ar : l.title.ar)

  return (
    <section aria-labelledby="path-h" className="card">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 id="path-h" className="m-0 font-display text-[22px] font-semibold text-maroon">
          {t('home.pathTitle')}
        </h2>
        {lessons.length > 0 && <span className="text-sm font-semibold text-muted">{t('path.progress', { k: done.length, n: lessons.length })}</span>}
      </div>
      <ol className="m-0 flex list-none flex-col gap-2.5 p-0">
        {shown.map(({ l, s }) => (
          <PathRow key={l.slug} slug={l.slug} title={title(l)} state={s} minutes={l.est_minutes ?? 10} />
        ))}
      </ol>
      {lessons.length > 3 && (
        <button type="button" onClick={() => setAll((v) => !v)} className="mt-3 block min-h-11 w-full cursor-pointer border-0 bg-transparent text-center text-[15px] font-semibold text-maroon">
          {all ? t('path.showLess') : t('path.showAll')}
        </button>
      )}
    </section>
  )
}

function PathRow({ slug, title, state, minutes }: { slug: string; title: string; state: PathState; minutes: number }) {
  const { t } = useI18n()
  const node =
    state === 'done' ? (
      <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-success text-white shadow-[0_3px_0_var(--success-text)]">
        <Check aria-hidden="true" size={18} strokeWidth={3} />
      </span>
    ) : state === 'current' ? (
      <span className="path-glow flex size-10 shrink-0 items-center justify-center rounded-full bg-maroon text-white shadow-[0_3px_0_var(--maroon-deep)]">
        <Star aria-hidden="true" size={18} fill="currentColor" />
      </span>
    ) : (
      <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-locked text-muted">
        <Lock aria-hidden="true" size={18} />
      </span>
    )
  return (
    <li className={`flex items-center gap-3 rounded-[14px] px-3 py-2.5 ${state === 'done' ? 'bg-surface-3' : state === 'current' ? 'border-2 border-maroon bg-maroon-soft' : ''}`}>
      {node}
      <span className="min-w-0 flex-auto">
        <span className={`block text-[15px] ${state === 'current' ? 'font-bold' : 'font-semibold'} ${state === 'locked' ? 'text-ink-2' : ''}`}>{title}</span>
        <span className={`text-[13px] ${state === 'current' ? 'text-maroon-deep' : 'text-muted'}`}>
          {state === 'done' ? t('path.done') : state === 'current' ? t('path.current', { m: minutes }) : t('path.locked')}
        </span>
      </span>
      {state !== 'locked' && (
        <Link
          href={`/lesson/${slug}`}
          className={`flex min-h-11 shrink-0 items-center rounded-xl px-4 font-bold no-underline ${
            state === 'current' ? 'bg-maroon text-white shadow-[0_3px_0_var(--maroon-deep)] hover:text-white' : 'text-maroon'
          }`}
        >
          {state === 'current' ? t('path.continue') : t('path.review')}
        </Link>
      )}
    </li>
  )
}
