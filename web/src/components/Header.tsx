import { Flame, Star } from 'lucide-react'
import { useI18n, type UiLang } from '../i18n'
import { Link, useRouter } from '../lib/router'
import { useProgress } from '../lib/progress'
import { LogoMark } from './Logo'

const NAV = [
  { href: '/', key: 'nav.home' },
  { href: '/glossary', key: 'nav.glossary' },
  { href: '/tutor', key: 'nav.tutor' },
] as const

export function Header() {
  const { t, lang, setLang } = useI18n()
  const { path } = useRouter()
  const { xp, streak } = useProgress()

  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex max-w-[1240px] flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3.5 sm:px-10">
        <Link href="/" className="flex items-center gap-2.5 no-underline" aria-label={`${t('app.name')} ${t('app.nameLatin')}`}>
          <LogoMark />
          <span className="flex items-baseline gap-2">
            <span lang="ar" className="font-display text-[26px] leading-none font-semibold text-maroon">دربي</span>
            <span lang="en" className="font-en text-[15px] font-semibold text-muted">Darby</span>
          </span>
        </Link>

        <div className="ms-auto flex items-center gap-2 text-[15px] font-bold sm:order-last">
          <span className="flex min-h-11 items-center gap-1.5 rounded-full border border-line bg-white px-3.5" title={t('header.streakLabel')}>
            <Flame aria-hidden="true" size={18} className="fill-flame text-flame" />
            <span className="sr-only">{t('header.streakLabel')}: </span>
            {t('header.streak', { n: streak })}
          </span>
          <span className="flex min-h-11 items-center gap-1.5 rounded-full border border-line bg-white px-3.5" title={t('header.pointsLabel')}>
            <Star aria-hidden="true" size={18} className="fill-gold text-gold" />
            <span className="sr-only">{t('header.pointsLabel')}: </span>
            {t('header.points', { n: xp })}
          </span>
          <LangToggle lang={lang} setLang={setLang} label={t('header.uiLanguage')} />
        </div>

        <nav aria-label={t('nav.label')} className="flex w-full flex-wrap gap-1.5 font-semibold sm:w-auto sm:flex-1">
          {NAV.map((item) => {
            const current = item.href === '/' ? path === '/' : path.startsWith(item.href)
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={current ? 'page' : undefined}
                className={`flex min-h-11 items-center rounded-full px-4 no-underline ${
                  current ? 'bg-maroon text-white hover:text-white' : 'text-ink-2 hover:bg-surface-3 hover:text-ink'
                }`}
              >
                {t(item.key)}
              </Link>
            )
          })}
        </nav>
      </div>
    </header>
  )
}

function LangToggle({ lang, setLang, label }: { lang: UiLang; setLang: (l: UiLang) => void; label: string }) {
  const other: UiLang = lang === 'ar' ? 'en' : 'ar'
  return (
    <button
      type="button"
      onClick={() => setLang(other)}
      // The name starts with the visible text (WCAG 2.5.3, so voice control users can say what they see).
      aria-label={`${other === 'en' ? 'EN' : 'ع'}, ${label}: ${other === 'en' ? 'English' : 'العربية'}`}
      lang={other}
      className="flex min-h-11 min-w-11 cursor-pointer items-center justify-center rounded-full border border-line bg-white px-3 font-bold text-ink-2 hover:bg-surface-3"
    >
      {other === 'en' ? 'EN' : 'ع'}
    </button>
  )
}
