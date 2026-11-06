import { BookOpen, Flame, Home, MessageCircle, Star } from 'lucide-react'
import { useI18n, type UiLang } from '../i18n'
import { useProgress } from '../lib/progress'
import { Link, useRouter } from '../lib/router'
import { LogoMark } from './Logo'

const NAV = [
  { href: '/', key: 'nav.home', Icon: Home },
  { href: '/glossary', key: 'nav.glossary', Icon: BookOpen },
  { href: '/tutor', key: 'nav.tutor', Icon: MessageCircle },
] as const

function useCurrent() {
  const { path } = useRouter()
  return (href: string) => (href === '/' ? path === '/' : path.startsWith(href))
}

/**
 * Floating glass header. The section nav is one landmark: inside the pill from 640px, a fixed tab bar at the
 * bottom on phones. The glass sits on a background layer because backdrop-filter on an ancestor would pin the
 * fixed tab bar to the header instead of the screen.
 */
export function Header() {
  const { t, lang, setLang } = useI18n()
  const { xp, streak } = useProgress()
  const current = useCurrent()

  return (
    <header className="px-4 pt-4 sm:px-10 sm:pt-6">
      <div className="relative z-30 mx-auto flex max-w-[1240px] items-center gap-3 px-3 py-2.5 sm:gap-6 sm:px-4">
        <div aria-hidden="true" className="glass absolute inset-0 -z-10 rounded-full!" />
        <Link href="/" className="flex items-center gap-2.5 no-underline" aria-label={`${t('app.name')} ${t('app.nameLatin')}`}>
          <LogoMark />
          <span className="hidden flex-col gap-1.5 min-[400px]:flex">
            {/* Arabic needs its own line height: at 1 the dots under ي and ب sat on top of the Latin name. */}
            <span lang="ar" className="font-display text-[22px] leading-[1.45] font-semibold text-maroon">
              دربي
            </span>
            <span lang="en" className="font-en text-xs leading-none font-semibold text-muted">
              Darby
            </span>
          </span>
        </Link>

        <nav
          aria-label={t('nav.label')}
          className="fixed inset-x-3 bottom-3 sm:static sm:flex-1"
          style={{ marginBottom: 'env(safe-area-inset-bottom)' }}
        >
          <div className="tabbar flex gap-1 rounded-full! p-1.5 sm:inline-flex sm:p-1">
            {NAV.map(({ href, key, Icon }) => {
              const on = current(href)
              return (
                <Link
                  key={href}
                  href={href}
                  aria-current={on ? 'page' : undefined}
                  className={`flex min-h-12 flex-1 flex-col items-center justify-center gap-0.5 rounded-full text-xs font-bold no-underline lift sm:min-h-11 sm:flex-none sm:flex-row sm:gap-2 sm:px-4 sm:text-base sm:font-semibold ${
                    on ? 'bg-white text-maroon shadow-[0_2px_0_var(--shadow)]' : 'text-ink-2 hover:text-ink'
                  }`}
                >
                  <Icon aria-hidden="true" size={19} />
                  {t(key)}
                </Link>
              )
            })}
          </div>
        </nav>

        <div className="ms-auto flex items-center gap-1.5 text-sm font-bold sm:gap-2 sm:text-[15px]">
          <span className="flex min-h-11 items-center gap-1 whitespace-nowrap rounded-full bg-white/80 px-2.5 sm:gap-1.5 sm:px-3" title={t('header.streakLabel')}>
            <Flame aria-hidden="true" size={18} className="fill-flame text-flame" />
            <span className="sr-only">{t('header.streakLabel')}: </span>
            {t('header.streak', { n: streak })}
          </span>
          <span className="flex min-h-11 items-center gap-1 whitespace-nowrap rounded-full bg-white/80 px-2.5 sm:gap-1.5 sm:px-3" title={t('header.pointsLabel')}>
            <Star aria-hidden="true" size={18} className="fill-gold text-gold" />
            <span className="sr-only">{t('header.pointsLabel')}: </span>
            {t('header.points', { n: xp })}
          </span>
          <LangToggle lang={lang} setLang={setLang} label={t('header.uiLanguage')} />
        </div>
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
      className="flex min-h-11 min-w-11 cursor-pointer items-center justify-center rounded-full border-0 bg-white/80 px-3 font-bold text-ink-2 hover:bg-white"
    >
      {other === 'en' ? 'EN' : 'ع'}
    </button>
  )
}
