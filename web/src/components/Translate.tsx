import { Languages, Loader2 } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { useI18n } from '../i18n'
import { ApiError, translateText } from '../lib/api'
import type { ExplainLang } from '../lib/explainLang'

const ARABIC = /[؀-ۿ]/g

/** Arabic text goes to English; English goes to the learner's Arabic (Gulf or Standard, from the language choice). */
export function translateTarget(text: string, lang: ExplainLang): ExplainLang {
  const arabic = (text.match(ARABIC) ?? []).length
  const latin = (text.match(/[A-Za-z]/g) ?? []).length
  return arabic > latin ? 'en' : lang === 'msa' ? 'msa' : 'gulf'
}

/**
 * Shows `text` (or `children`) with a button that swaps in a Fanar translation and back. The translation is fetched
 * once per text and target.
 */
export function Translatable({ text, lang, children, className }: { text: string; lang: ExplainLang; children?: ReactNode; className?: string }) {
  const { t } = useI18n()
  const target = translateTarget(text, lang)
  const [cache, setCache] = useState<Record<string, string>>({})
  const [showing, setShowing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const key = `${target}:${text}`
  const translated = cache[key]

  const toggle = async () => {
    if (showing) return setShowing(false)
    setError(null)
    if (!translated) {
      setBusy(true)
      try {
        const out = await translateText(text, target)
        setCache((c) => ({ ...c, [key]: out }))
      } catch (e) {
        setError(e instanceof ApiError && e.status === 429 ? t('tutor.limit') : e instanceof ApiError && e.status === 503 ? t('translate.waking') : t('translate.failed'))
        return
      } finally {
        setBusy(false)
      }
    }
    setShowing(true)
  }

  const label = showing ? t('translate.original') : target === 'en' ? t('translate.toEn') : target === 'msa' ? t('translate.toMsa') : t('translate.toGulf')
  return (
    <div className={className}>
      {showing && translated ? (
        <p className="m-0 whitespace-pre-wrap" dir={target === 'en' ? 'ltr' : 'rtl'} lang={target === 'en' ? 'en' : 'ar'}>
          {translated}
        </p>
      ) : (
        (children ?? (
          <p className="m-0 whitespace-pre-wrap" dir="auto">
            {text}
          </p>
        ))
      )}
      <div className="mt-1.5 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={toggle}
          disabled={busy}
          aria-pressed={showing}
          className="inline-flex min-h-11 cursor-pointer items-center gap-1.5 rounded-full border-0 bg-teal-soft px-3 text-sm font-bold text-teal-text disabled:cursor-wait"
        >
          {busy ? <Loader2 aria-hidden="true" size={15} className="animate-spin" /> : <Languages aria-hidden="true" size={15} />}
          {busy ? t('translate.working') : label}
        </button>
        {error && (
          <span role="status" className="text-[13px] text-ink-2">
            {error}
          </span>
        )}
      </div>
    </div>
  )
}
