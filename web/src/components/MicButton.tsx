import { Loader2, Mic, Square } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useI18n } from '../i18n'
import { ApiError } from '../lib/api'
import { asrEnabled, MAX_SECONDS, startRecording, transcribe, type Recording } from '../lib/mic'

/** Talk instead of typing: tap to record, tap again to stop; the words are added to the box. Hidden when speech to
 * text is off or the browser has no microphone access. */
export function MicButton({ onText, lang = 'auto' }: { onText: (text: string) => void; lang?: 'ar' | 'en' | 'auto' }) {
  const { t } = useI18n()
  const [on, setOn] = useState(false)
  const [state, setState] = useState<'idle' | 'recording' | 'working'>('idle')
  const [note, setNote] = useState<string | null>(null)
  const rec = useRef<Recording | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    asrEnabled().then(setOn)
    return () => {
      if (timer.current) clearTimeout(timer.current)
      rec.current?.stop().catch(() => {})
    }
  }, [])
  if (!on) return null

  const stop = async () => {
    if (timer.current) clearTimeout(timer.current)
    const r = rec.current
    rec.current = null
    if (!r) return
    setState('working')
    try {
      const text = await transcribe(await r.stop(), lang)
      if (text) onText(text)
      else setNote(t('mic.nothing'))
    } catch (e) {
      setNote(e instanceof ApiError && e.status === 429 ? t('tutor.limit') : e instanceof ApiError && e.status === 422 ? t('mic.short') : t('mic.failed'))
    } finally {
      setState('idle')
    }
  }

  const start = async () => {
    setNote(null)
    try {
      rec.current = await startRecording()
      setState('recording')
      timer.current = setTimeout(stop, MAX_SECONDS * 1000)
    } catch {
      setNote(t('mic.denied'))
    }
  }

  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <button
        type="button"
        onClick={state === 'recording' ? stop : start}
        disabled={state === 'working'}
        aria-pressed={state === 'recording'}
        className={`inline-flex min-h-11 cursor-pointer items-center gap-1.5 rounded-full border-0 px-4 text-sm font-bold disabled:cursor-wait ${
          state === 'recording' ? 'bg-maroon text-white' : 'bg-teal-soft text-teal-text'
        }`}
      >
        {state === 'working' ? <Loader2 aria-hidden="true" size={16} className="animate-spin" /> : state === 'recording' ? <Square aria-hidden="true" size={14} fill="currentColor" /> : <Mic aria-hidden="true" size={16} />}
        {state === 'working' ? t('mic.working') : state === 'recording' ? t('mic.stop') : t('mic.start')}
      </button>
      {note && (
        <span role="status" className="text-[13px] text-ink-2">
          {note}
        </span>
      )}
    </span>
  )
}
