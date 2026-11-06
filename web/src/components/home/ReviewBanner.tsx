import { MessageSquare } from 'lucide-react'
import { useI18n } from '../../i18n'
import { useDictionary } from '../../lib/dictionary'
import { qatarDate } from '../../lib/progress'
import { Link } from '../../lib/router'

/** Saved terms from before today are due for a look. Hidden when there are none. */
export function ReviewBanner() {
  const { t } = useI18n()
  const { terms } = useDictionary()
  const today = qatarDate()
  const due = Object.values(terms).filter((s) => qatarDate(new Date(s.savedAt)) < today).length
  if (due === 0) return null
  return (
    <section className="flex items-center gap-3.5 rounded-[20px] bg-gold-soft px-5 py-4">
      <MessageSquare aria-hidden="true" size={26} className="shrink-0 text-gold-text" />
      <span className="flex-auto font-semibold text-gold-text">{t('review.due', { n: due })}</span>
      <Link href="/glossary?mine=1" className="flex min-h-11 items-center rounded-xl border-2 border-gold-text px-3.5 font-bold text-gold-text no-underline hover:text-gold-text">
        {t('review.go')}
      </Link>
    </section>
  )
}
