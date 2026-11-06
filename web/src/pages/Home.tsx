import type { CSSProperties } from 'react'
import { ExplainPanel } from '../components/explain/ExplainPanel'
import { DailyCode } from '../components/home/DailyCode'
import { PathCard } from '../components/home/PathCard'
import { DailyGoal, ReviewBanner } from '../components/home/ReviewBanner'
import { PageTitle } from '../components/PageTitle'
import { Segmented } from '../components/Segmented'
import { useI18n } from '../i18n'
import { useExplainLang, type ExplainLang } from '../lib/explainLang'
import { qatarHour } from '../lib/qatarTime'

export function Home() {
  const { t } = useI18n()
  const [explainLang, setExplainLang] = useExplainLang()
  const hour = qatarHour()
  const greeting = hour >= 4 && hour < 12 ? t('home.greetingMorning') : t('home.greetingEvening')

  const options: { value: ExplainLang; label: string; lang: string }[] = [
    { value: 'en', label: t('lang.en'), lang: 'en' },
    { value: 'msa', label: t('lang.msa'), lang: 'ar' },
    { value: 'gulf', label: t('lang.gulf'), lang: 'ar' },
  ]

  return (
    <>
      <PageTitle
        title={greeting}
        subtitle={t('home.subtitle')}
        aside={
          <div className="flex flex-wrap gap-3">
            <ReviewBanner />
            <DailyGoal />
          </div>
        }
      />
      <div className="flex flex-wrap items-start gap-5 sm:gap-7">
        <div className="card-enter flex min-w-0 flex-[999_1_600px] flex-col gap-5 sm:gap-7">
          <ExplainPanel
            lang={explainLang}
            langControl={<Segmented label={t('home.explainLanguage')} options={options} value={explainLang} onChange={setExplainLang} />}
          />
        </div>
        <aside className="flex min-w-0 flex-[1_1_340px] flex-col gap-5 sm:gap-7">
          <div className="card-enter" style={{ '--i': 1 } as CSSProperties}>
            <DailyCode />
          </div>
          <div className="card-enter" style={{ '--i': 2 } as CSSProperties}>
            <PathCard />
          </div>
        </aside>
      </div>
    </>
  )
}
