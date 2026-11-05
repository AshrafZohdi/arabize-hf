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
        aside={<Segmented label={t('home.explainLanguage')} options={options} value={explainLang} onChange={setExplainLang} />}
      />
      <div className="flex flex-wrap items-start gap-5 sm:gap-7">
        <div className="flex min-w-0 flex-[999_1_600px] flex-col gap-5 sm:gap-7">
          <section aria-labelledby="explain-h" className="card">
            <h2 id="explain-h" className="m-0 font-display text-[22px] font-semibold text-maroon">{t('home.explainTitle')}</h2>
            <p className="mb-0 text-muted">{t('placeholder.soon')}</p>
          </section>
        </div>
        <aside className="flex min-w-0 flex-[1_1_340px] flex-col gap-5 sm:gap-7">
          <section aria-labelledby="code-h" className="card">
            <h2 id="code-h" className="m-0 font-display text-[22px] font-semibold text-maroon">{t('home.codeTitle')}</h2>
            <p className="mb-0 text-muted">{t('placeholder.soon')}</p>
          </section>
          <section aria-labelledby="path-h" className="card">
            <h2 id="path-h" className="m-0 font-display text-[22px] font-semibold text-maroon">{t('home.pathTitle')}</h2>
            <p className="mb-0 text-muted">{t('placeholder.soon')}</p>
          </section>
        </aside>
      </div>
    </>
  )
}
