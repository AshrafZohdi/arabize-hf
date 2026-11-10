import { BookOpen, GraduationCap, Home, MessageCircle } from 'lucide-react'
import { useI18n, type UiLang } from '../i18n'
import { Link, useRouter } from '../lib/router'
import { LogoMark } from './Logo'
import { FlagEdge } from './Motifs'

const NAV = [
  { href: '/', key: 'nav.home', Icon: Home },
  { href: '/learn', key: 'nav.learn', Icon: GraduationCap },
  { href: '/glossary', key: 'nav.glossary', Icon: BookOpen },
  { href: '/tutor', key: 'nav.tutor', Icon: MessageCircle },
] as const

function useCurrent() {
  const { path } = useRouter()
  return (href: string) => {
    if (href === '/') return path === '/'
    // A lesson is part of the Learn section.
    if (href === '/learn') return path.startsWith('/learn') || path.startsWith('/lesson')
    return path.startsWith(href)
  }
}

/**
 * The header: the flag's serrated edge, the wordmark, the four sections and the language switch. The section nav
 * is one landmark: links in the header from 640px, a bar fixed to the bottom of the screen on phones. The header
 * has no filter or transform, which would pin that fixed bar to the header instead of the screen.
 */
export function Header() {
  const { t, lang, setLang } = useI18n()
  const current = useCurrent()

  return (
    <header className="border-b border-line bg-surface">
      <FlagEdge />
      <div className="mx-auto flex h-16 max-w-[1120px] items-center gap-4 px-4 sm:gap-8 sm:px-8">
        <Link href="/" className="flex items-center gap-2.5 no-underline" aria-label={`${t('app.name')} ${t('app.nameLatin')}`}>
          <LogoMark />
          {/* Side by side on one baseline: stacked, the dots under ي and ب ran into the Latin name. */}
          <span className="flex items-baseline gap-2">
            <span lang="ar" className="font-display text-[22px] leading-normal font-bold text-maroon">
              دربي
            </span>
            <span lang="en" className="font-en text-sm font-semibold tracking-wide text-muted">
              Darbi
            </span>
          </span>
        </Link>

        <nav aria-label={t('nav.label')} className="fixed inset-x-0 bottom-0 z-30 sm:static sm:z-auto sm:flex-1">
          <div className="tabbar flex sm:gap-1" style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
            {NAV.map(({ href, key, Icon }) => {
              const on = current(href)
              return (
                <Link
                  key={href}
                  href={href}
                  aria-current={on ? 'page' : undefined}
                  className={`relative flex min-h-14 flex-1 flex-col items-center justify-center gap-0.5 text-xs font-semibold no-underline sm:min-h-16 sm:flex-none sm:flex-row sm:gap-2 sm:px-3.5 sm:text-[15px] ${
                    on ? 'text-maroon hover:text-maroon' : 'text-ink-2 hover:text-ink'
                  }`}
                >
                  <Icon aria-hidden="true" size={19} strokeWidth={on ? 2.4 : 2} />
                  {t(key)}
                  {/* The current section: a maroon rule on the edge that touches the page. */}
                  {on && <span aria-hidden="true" className="absolute inset-x-3 top-0 h-[3px] rounded-b bg-maroon sm:top-auto sm:bottom-0 sm:rounded-t sm:rounded-b-none" />}
                </Link>
              )
            })}
          </div>
        </nav>

        <div className="ms-auto">
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
      aria-label={`${other === 'en' ? 'English' : 'العربية'}, ${label}`}
      lang={other}
      className="flex min-h-11 cursor-pointer items-center justify-center rounded-lg border border-line bg-surface px-3.5 text-sm font-semibold text-ink-2 hover:border-maroon hover:text-maroon"
    >
      {other === 'en' ? 'English' : 'العربية'}
    </button>
  )
}
