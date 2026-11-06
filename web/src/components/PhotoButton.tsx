import { Camera, Loader2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useI18n } from '../i18n'
import { ApiError } from '../lib/api'
import type { ExplainLang } from '../lib/explainLang'
import { imageFeatures, readImage, shrinkImage } from '../lib/image'

/** Take or pick a photo; Fanar-2-Oryx-IVU reads its English text and hands it over. Hidden when photo explain is off. */
export function PhotoButton({ lang, onText }: { lang: ExplainLang; onText: (text: string, description: string) => void }) {
  const { t } = useI18n()
  const [on, setOn] = useState(false)
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState<string | null>(null)
  const input = useRef<HTMLInputElement>(null)

  useEffect(() => {
    imageFeatures().then((f) => setOn(f.read))
  }, [])
  if (!on) return null

  const pick = async (file: File | undefined) => {
    if (!file) return
    setBusy(true)
    setNote(null)
    try {
      const r = await readImage(await shrinkImage(file), lang)
      if (r.text) onText(r.text, r.description)
      else setNote(t('photo.noText', { d: r.description }))
    } catch (e) {
      setNote(e instanceof ApiError && e.status === 503 ? t('photo.waking') : e instanceof ApiError && e.status === 429 ? t('tutor.limit') : t('photo.failed'))
    } finally {
      setBusy(false)
      if (input.current) input.current.value = ''
    }
  }

  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <input ref={input} type="file" accept="image/*" capture="environment" className="sr-only" tabIndex={-1} aria-hidden="true" onChange={(e) => pick(e.target.files?.[0])} />
      <button
        type="button"
        onClick={() => input.current?.click()}
        disabled={busy}
        className="inline-flex min-h-11 cursor-pointer items-center gap-1.5 rounded-full border-0 bg-teal-soft px-4 text-sm font-bold text-teal-text disabled:cursor-wait"
      >
        {busy ? <Loader2 aria-hidden="true" size={16} className="animate-spin" /> : <Camera aria-hidden="true" size={16} />}
        {busy ? t('photo.reading') : t('photo.button')}
      </button>
      {note && (
        <span role="status" className="text-[13px] text-ink-2">
          {note}
        </span>
      )}
    </span>
  )
}
