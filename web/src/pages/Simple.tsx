import { ArrowRight, BookOpen, Compass, MessageCircle } from 'lucide-react'
import { useI18n } from '../i18n'
import { Link } from '../lib/router'

export function NotFound() {
  const { t } = useI18n()
  return (
    <section className="card card-enter flex flex-wrap-reverse items-center gap-8">
      <svg aria-hidden="true" viewBox="0 0 440 300" className="w-full max-w-[440px] flex-[1_1_280px] rounded-3xl">
        <rect width="440" height="300" fill="var(--gold-soft)" />
        <circle cx="330" cy="80" r="46" fill="var(--gold)" opacity="0.6" />
        <path d="M0 190 C90 150 170 210 260 175 S390 150 440 170 V300 H0Z" fill="var(--surface-3)" />
        <path d="M0 230 C110 205 220 250 320 225 S410 215 440 225 V300 H0Z" fill="var(--bg)" />
        <path d="M180 232 C230 250 260 220 320 238 S400 262 420 270" fill="none" stroke="var(--white)" strokeWidth="16" strokeLinecap="round" />
        <path d="M180 232 C230 250 260 220 320 238 S400 262 420 270" fill="none" stroke="var(--maroon)" strokeWidth="3" strokeLinecap="round" strokeDasharray="2 9" />
        <rect x="146" y="184" width="6" height="40" fill="var(--ink-2)" />
        <rect x="108" y="170" width="82" height="28" rx="6" fill="var(--maroon)" />
        <text x="149" y="190" textAnchor="middle" fontSize="16" fontWeight="700" fill="var(--white)" fontFamily="var(--font-en)">
          404
        </text>
      </svg>
      <div className="flex min-w-0 flex-[1_1_320px] flex-col items-start gap-4">
        <span className="flex items-center gap-1.5 rounded-full bg-gold-soft px-3 py-1 text-sm font-bold text-gold-text">
          <Compass aria-hidden="true" size={15} />
          {t('notFound.tag')}
        </span>
        <h1 className="m-0 font-display text-[32px] leading-tight font-semibold sm:text-[44px]">{t('notFound.title')}</h1>
        <p className="m-0 text-lg text-ink-2">{t('notFound.body')}</p>
        <Link href="/" className="btn-primary flex items-center gap-2 text-lg no-underline hover:text-white">
          {t('notFound.back')}
          <ArrowRight aria-hidden="true" size={20} className="rtl:-scale-x-100" />
        </Link>
        <div className="flex flex-wrap gap-2">
          <Link href="/glossary" className="lift flex min-h-11 items-center gap-2 rounded-full border border-white/80 bg-white/70 px-4 font-bold text-ink no-underline hover:text-ink">
            <BookOpen aria-hidden="true" size={18} className="text-maroon" />
            {t('nav.glossary')}
          </Link>
          <Link href="/tutor" className="lift flex min-h-11 items-center gap-2 rounded-full border border-white/80 bg-white/70 px-4 font-bold text-ink no-underline hover:text-ink">
            <MessageCircle aria-hidden="true" size={18} className="text-maroon" />
            {t('nav.tutor')}
          </Link>
        </div>
      </div>
    </section>
  )
}
