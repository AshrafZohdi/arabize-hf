import { ArrowRight, BookOpen, GraduationCap, MessageCircle, type LucideIcon } from 'lucide-react'
import { ExplainPanel } from '../components/explain/ExplainPanel'
import { Segmented } from '../components/Segmented'
import { useI18n, type MessageKey } from '../i18n'
import { useExplainLang, type ExplainLang } from '../lib/explainLang'
import { qatarHour } from '../lib/qatarTime'
import { Link } from '../lib/router'

const QUICK: { href: string; title: MessageKey; sub: MessageKey; Icon: LucideIcon }[] = [
  { href: '/learn', title: 'home.quick.learn', sub: 'home.quick.learnSub', Icon: GraduationCap },
  { href: '/glossary', title: 'home.quick.glossary', sub: 'home.quick.glossarySub', Icon: BookOpen },
  { href: '/tutor', title: 'home.quick.tutor', sub: 'home.quick.tutorSub', Icon: MessageCircle },
]

/** Home does one thing: paste an English text and have it explained. Everything else is one tap away below. */
export function Home() {
  const { t } = useI18n()
  const [explainLang, setExplainLang] = useExplainLang()
  const hour = qatarHour()
  const greeting = hour >= 4 && hour < 12 ? t('home.greetingMorning') : t('home.greetingEvening')

  const options: { value: ExplainLang; label: string; lang: string }[] = [
    { value: 'gulf', label: t('lang.gulf'), lang: 'ar' },
    { value: 'msa', label: t('lang.msa'), lang: 'ar' },
    { value: 'en', label: t('lang.en'), lang: 'en' },
  ]

  return (
    <>
      <div className="mb-6 max-w-[46rem] sm:mb-8">
        <p className="m-0 mb-1 text-[15px] font-semibold text-maroon">{greeting}</p>
        <h1 className="m-0 font-display text-[28px] font-bold sm:text-[40px]">{t('home.heroTitle')}</h1>
        <p className="mt-2 mb-0 text-lg text-ink-2">{t('home.heroSub')}</p>
      </div>

      <div className="card-enter flex flex-col gap-5 sm:gap-6">
        <ExplainPanel
          lang={explainLang}
          langControl={<Segmented label={t('home.explainLanguage')} options={options} value={explainLang} onChange={setExplainLang} />}
        />
      </div>

      <section aria-labelledby="more-h" className="mt-10 sm:mt-12">
        <h2 id="more-h" className="m-0 mb-3 font-display text-xl font-semibold">
          {t('home.moreTitle')}
        </h2>
        <ul className="m-0 grid list-none gap-3 p-0 sm:grid-cols-3">
          {QUICK.map(({ href, title, sub, Icon }) => (
            <li key={href}>
              <Link href={href} className="card lift group flex h-full items-center gap-3.5 p-4! text-ink no-underline hover:border-maroon hover:text-ink">
                <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-maroon-soft text-maroon">
                  <Icon aria-hidden="true" size={21} />
                </span>
                <span className="flex min-w-0 flex-1 flex-col leading-snug">
                  <span className="font-bold">{t(title)}</span>
                  <span className="text-sm text-muted">{t(sub)}</span>
                </span>
                <ArrowRight aria-hidden="true" size={18} className="shrink-0 text-muted group-hover:text-maroon rtl:-scale-x-100" />
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </>
  )
}
