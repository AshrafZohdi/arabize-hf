import { Flame, Share2, Star, Trophy, X } from 'lucide-react'
import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { useI18n } from '../../i18n'
import type { Mark } from '../../lib/api'
import { useProgress } from '../../lib/progress'

const SQUARE: Record<Mark, string> = { hit: 'bg-success', near: 'bg-present', miss: 'bg-absent' }

/** Time to the next Qatar midnight (UTC+3 all year) as HH:MM:SS. */
function untilNextCode(now = Date.now()): string {
  const day = 86_400_000
  const offset = 3 * 3_600_000
  const left = Math.ceil((now + offset) / day) * day - offset - now
  const s = Math.floor(left / 1000)
  return [Math.floor(s / 3600), Math.floor(s / 60) % 60, s % 60].map((n) => String(n).padStart(2, '0')).join(':')
}

type Props = {
  open: boolean
  onClose: () => void
  onShare: () => void
  copied: boolean
  word: string
  lang: 'en' | 'ar'
  clue: { term: string; meaning: string }
  rows: Mark[][]
  maxTries: number
  xp: number
}

/** The daily code win, as a modal over Home. The share grid never contains the word. */
export function CodeWinDialog({ open, onClose, onShare, copied, word, lang, clue, rows, maxTries, xp }: Props) {
  const { t, lang: uiLang } = useI18n()
  const { streak } = useProgress()
  const ref = useRef<HTMLDialogElement>(null)
  const [left, setLeft] = useState(untilNextCode)

  useEffect(() => {
    const d = ref.current
    if (!d) return
    if (open && !d.open) d.showModal?.()
    else if (!open && d.open) d.close()
  }, [open])

  useEffect(() => {
    if (!open) return
    const id = setInterval(() => setLeft(untilNextCode()), 1000)
    return () => clearInterval(id)
  }, [open])

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={(e) => e.target === ref.current && onClose()}
      aria-labelledby="win-title"
      className="glass m-auto w-[min(560px,calc(100vw-32px))] max-h-[calc(100dvh-32px)] rounded-[28px]! bg-surface/92! p-0 text-ink"
    >
      {open && (
        <div className="flex flex-col items-center gap-4 p-5 text-center sm:p-8">
          <button
            type="button"
            onClick={onClose}
            aria-label={t('glossary.close')}
            className="flex size-11 cursor-pointer items-center justify-center self-end rounded-full border border-line bg-white/80 text-ink-2"
          >
            <X aria-hidden="true" size={18} />
          </button>
          <span className="-mt-8 flex size-20 items-center justify-center rounded-3xl bg-success text-white shadow-[0_5px_0_var(--success-text)]">
            <Trophy aria-hidden="true" size={38} />
          </span>
          <div>
            <h2 id="win-title" className="m-0 font-display text-[30px] font-semibold">
              {t('code.winTitle')}
            </h2>
            <p className="m-0 text-ink-2">{t('code.winSub', { k: rows.length, n: maxTries })}</p>
          </div>
          <div dir={lang === 'ar' ? 'rtl' : 'ltr'} lang={lang} className="flex gap-2 font-en text-2xl font-bold">
            {[...word].map((ch, i) => (
              <span
                key={i}
                className="tile-flip flex size-12 items-center justify-center rounded-xl bg-success text-white uppercase shadow-[0_4px_0_var(--success-text)] sm:size-14"
                style={{ '--i': i } as CSSProperties}
              >
                {ch}
              </span>
            ))}
          </div>
          <div className="well w-full p-4 text-start">
            <p className="m-0 font-bold">
              <bdi>{word}</bdi>
              {uiLang === 'ar' ? '، ' : ', '}
              <bdi>{clue.term}</bdi>
            </p>
            {clue.meaning && (
              <p dir="auto" className="m-0 mt-1 text-[15px] text-ink-2">
                {clue.meaning}
              </p>
            )}
          </div>
          <div className="flex flex-wrap justify-center gap-2 text-sm font-bold">
            <span className="flex items-center gap-1.5 rounded-full bg-gold-soft px-3 py-1.5 text-gold-text">
              <Star aria-hidden="true" size={15} className="fill-gold text-gold" />
              {t('code.winPoints', { n: xp })}
            </span>
            <span className="flex items-center gap-1.5 rounded-full bg-maroon-soft px-3 py-1.5 text-maroon-text">
              <Flame aria-hidden="true" size={15} className="fill-flame text-flame" />
              {t('header.streak', { n: streak })}
            </span>
          </div>
          <div className="flex w-full flex-wrap items-center gap-4 rounded-[20px] border border-white/80 bg-white/70 p-4">
            <div aria-hidden="true" className="flex flex-col gap-1">
              {rows.map((r, i) => (
                <div key={i} className="flex gap-1">
                  {r.map((m, j) => (
                    <span key={j} className={`size-3.5 rounded-[3px] ${SQUARE[m]}`} />
                  ))}
                </div>
              ))}
            </div>
            <div className="min-w-0 flex-1 text-start">
              <p className="m-0 font-bold">{t('code.share')}</p>
              <p className="m-0 text-[13px] text-ink-2">{t('code.shareSub')}</p>
            </div>
            <button type="button" onClick={onShare} className="btn-primary flex min-h-11 items-center gap-2 px-5 text-base">
              <Share2 aria-hidden="true" size={18} />
              {copied ? t('code.copied') : t('code.shareShort')}
            </button>
          </div>
          <p className="m-0 text-[13px] text-ink-2">
            {t('code.nextIn')} <strong className="font-en tabular-nums">{left}</strong>
            {t('code.nextZone')}
          </p>
        </div>
      )}
    </dialog>
  )
}
