import { Loader2, Volume2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useI18n } from '../i18n'
import { preloadTerm, speak, voiceEnabled } from '../lib/voice'

/** Two listen buttons: the English term and the Arabic term. Hidden when voice is off. */
export function ListenButtons({ en, ar, termId }: { en: string; ar: string; termId?: string | null }) {
  const { t } = useI18n()
  const [on, setOn] = useState(false)
  const [busy, setBusy] = useState<'en' | 'ar' | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    voiceEnabled().then(setOn)
  }, [])
  useEffect(() => {
    if (termId) preloadTerm(termId)
  }, [termId])
  if (!on) return null

  const play = async (lang: 'en' | 'ar') => {
    setBusy(lang)
    setFailed(false)
    try {
      await speak(lang, lang === 'en' ? en : ar, termId)
    } catch {
      setFailed(true)
    } finally {
      setBusy(null)
    }
  }

  return (
    <span className="flex items-center gap-1.5">
      {(['en', 'ar'] as const).map((lang) => (
        <button
          key={lang}
          type="button"
          onClick={() => play(lang)}
          disabled={busy !== null}
          aria-label={`${lang === 'en' ? t('voice.listenEn') : t('voice.listenAr')}${busy === lang ? `, ${t('voice.loading')}` : ''}`}
          title={lang === 'en' ? t('voice.listenEn') : t('voice.listenAr')}
          className="flex h-12 min-w-12 cursor-pointer items-center justify-center gap-1 rounded-2xl border-0 bg-teal-soft px-2.5 font-bold text-teal-text shadow-[0_4px_0_var(--line)] disabled:cursor-wait"
        >
          {busy === lang ? <Loader2 aria-hidden="true" size={20} className="animate-spin" /> : <Volume2 aria-hidden="true" size={20} />}
          <span aria-hidden="true" className="text-xs" lang={lang}>
            {lang === 'en' ? 'EN' : 'ع'}
          </span>
        </button>
      ))}
      {failed && (
        <span role="status" className="text-xs text-muted">
          {t('voice.failed')}
        </span>
      )}
    </span>
  )
}
