import { Flame, Star } from 'lucide-react'
import type { CSSProperties } from 'react'
import { DailyCode } from '../components/home/DailyCode'
import { PathCard } from '../components/home/PathCard'
import { DailyGoal, ReviewBanner } from '../components/home/ReviewBanner'
import { PageTitle } from '../components/PageTitle'
import { useI18n } from '../i18n'
import { useProgress } from '../lib/progress'

/** Lessons, today's word game and the learner's progress, together in one place. */
export function LearnPage() {
  const { t } = useI18n()
  const { xp, streak } = useProgress()

  return (
    <>
      <PageTitle
        title={t('learn.title')}
        subtitle={t('learn.subtitle')}
        aside={
          <ul aria-label={t('learn.progress')} className="m-0 flex list-none flex-wrap items-center gap-2.5 p-0 font-semibold">
            <li className="flex min-h-11 items-center gap-1.5 rounded-xl border border-line bg-surface px-3.5">
              <Flame aria-hidden="true" size={18} className="fill-flame text-flame" />
              <span className="sr-only">{t('header.streakLabel')}: </span>
              {t('header.streak', { n: streak })}
            </li>
            <li className="flex min-h-11 items-center gap-1.5 rounded-xl border border-line bg-surface px-3.5">
              <Star aria-hidden="true" size={18} className="fill-gold text-gold" />
              <span className="sr-only">{t('header.pointsLabel')}: </span>
              {t('header.points', { n: xp })}
            </li>
            <li>
              <DailyGoal />
            </li>
          </ul>
        }
      />
      <div className="mb-5 empty:hidden">
        <ReviewBanner />
      </div>
      <div className="flex flex-wrap items-start gap-5 sm:gap-6">
        <div className="card-enter min-w-0 flex-[999_1_520px]">
          <PathCard />
        </div>
        <aside className="card-enter min-w-0 flex-[1_1_340px]" style={{ '--i': 1 } as CSSProperties}>
          <DailyCode />
        </aside>
      </div>
    </>
  )
}
