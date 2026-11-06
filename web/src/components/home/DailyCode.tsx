import { Check, Copy, Grid3x3 } from 'lucide-react'
import { useEffect, useState, type CSSProperties } from 'react'
import { useI18n, type MessageKey } from '../../i18n'
import { guessCode, startCode, type CodeStart, type Mark } from '../../lib/api'
import { award } from '../../lib/progress'
import { Link } from '../../lib/router'
import { shareText } from '../../lib/share'

type Row = { guess: string; marks: Mark[] }
type Saved = { token: string; rows: Row[]; finished: boolean; won: boolean; answer: { id: string; word: string } | null }
const TILE: Record<Mark, string> = { hit: 'bg-success text-white', near: 'bg-present text-white', miss: 'bg-absent text-ink' }
const SWATCH: Record<Mark, string> = { hit: 'bg-success', near: 'bg-present', miss: 'bg-absent' }
const MARK_KEY: Record<Mark, MessageKey> = { hit: 'code.hit', near: 'code.near', miss: 'code.miss' }

function load(key: string): Saved | null {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as Saved) : null
  } catch {
    return null
  }
}

function store(key: string, s: Saved) {
  try {
    localStorage.setItem(key, JSON.stringify(s))
  } catch {
    // Storage blocked: the game still works for this visit.
  }
}

/** شيفرة اليوم: the server picks the word and marks guesses; the word only arrives when the game ends. */
export function DailyCode() {
  const { t, lang: uiLang } = useI18n()
  const [lang, setLang] = useState<'en' | 'ar'>(uiLang === 'ar' ? 'en' : 'ar')
  const [start, setStart] = useState<CodeStart | null>(null)
  const [state, setState] = useState<Saved | null>(null)
  const [input, setInput] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState(false)
  // Only the row just played flips; rows restored from storage show their colours at once.
  const [flipRow, setFlipRow] = useState(-1)

  useEffect(() => {
    setStart(null)
    setError(false)
    setMessage(null)
    startCode(lang)
      .then((s) => {
        setStart(s)
        const saved = load(`darby.code.${s.date}.${lang}`)
        setState(saved ?? { token: s.token, rows: [], finished: false, won: false, answer: null })
      })
      .catch(() => setError(true))
  }, [lang])

  const submit = async () => {
    if (!start || !state || state.finished || busy) return
    const g = input.trim()
    if (!g) return
    setBusy(true)
    setMessage(null)
    try {
      const r = await guessCode(lang, state.token, g)
      if ('error' in r) {
        setMessage(r.reason === 'not_a_word' ? t('code.notAWord') : r.reason === 'length' ? t('code.wrongLength', { n: start.length }) : t('code.error'))
        return
      }
      const next: Saved = {
        token: r.token,
        rows: [...state.rows, { guess: r.guess, marks: r.marks }],
        finished: r.finished,
        won: r.won,
        answer: r.answer ? { id: r.answer.id, word: r.answer.word } : null,
      }
      setState(next)
      setFlipRow(next.rows.length - 1)
      store(`darby.code.${start.date}.${lang}`, next)
      setInput('')
      if (r.answer) award(`code:${start.date}:${lang}`, r.answer.xp)
    } catch {
      setMessage(t('code.error'))
    } finally {
      setBusy(false)
    }
  }

  const share = async () => {
    if (!start || !state) return
    try {
      await navigator.clipboard.writeText(shareText(t('code.shareTitle'), start.date, state.rows.map((r) => r.marks), state.won, start.max_tries))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard blocked: nothing to do.
    }
  }

  const tries = start?.max_tries ?? 6
  const len = start?.length ?? 5
  const emptyRows = state && !state.finished ? tries - state.rows.length : 0
  const dir = lang === 'ar' ? 'rtl' : 'ltr'
  const cols = { gridTemplateColumns: `repeat(${len}, minmax(0, 1fr))` }

  return (
    <section aria-labelledby="code-h" className="card">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 id="code-h" className="m-0 flex items-center gap-2 font-display text-[22px] font-semibold whitespace-nowrap text-maroon">
          <Grid3x3 aria-hidden="true" size={20} />
          {t('home.codeTitle')}
        </h2>
        {start && state && !state.finished && (
          <span className="rounded-full bg-surface-3/80 px-3 py-1 text-sm font-semibold text-ink-2">
            {t('code.attempt', { k: Math.min(state.rows.length + 1, start.max_tries), n: start.max_tries })}
          </span>
        )}
      </div>
      <div className="mb-3 flex items-center gap-2">
          <div role="group" aria-label={t('code.langLabel')} className="flex gap-1 rounded-full border border-line p-0.5">
            {(['en', 'ar'] as const).map((l) => (
              <button
                key={l}
                type="button"
                aria-pressed={lang === l}
                lang={l}
                onClick={() => setLang(l)}
                className={`min-h-11 min-w-11 cursor-pointer rounded-full border-0 px-2 font-bold ${lang === l ? 'bg-maroon text-white' : 'bg-transparent text-ink-2'}`}
              >
                {l === 'en' ? t('code.langEn') : t('code.langAr')}
              </button>
            ))}
          </div>
          <span className="rounded-full bg-gold-soft px-3 py-1 text-sm font-bold text-gold-text">{t('code.points', { n: 30 })}</span>
      </div>
      {error && <p className="m-0 text-muted">{t('code.error')}</p>}
      {start && state && (
        <>
          <p className="mt-0 mb-4 text-[15px] text-ink-2">
            {t('code.clue')} <strong dir="auto">{start.clue.term}</strong>
            {start.clue.meaning && (
              <>
                {uiLang === 'ar' ? '، ' : ', '}
                <span dir="auto">{start.clue.meaning}</span>
              </>
            )}
          </p>
          <div dir={dir} lang={lang} className="mx-auto flex w-full max-w-[300px] flex-col gap-1.5 font-en text-xl font-bold">
            {state.rows.map((row, i) => (
              <div key={i} className="grid gap-1.5" style={cols}>
                {[...row.guess].map((ch, j) => (
                  <div
                    key={j}
                    role="img"
                    className={`flex h-11 items-center justify-center rounded-[10px] uppercase shadow-[0_3px_0_var(--shadow)] ${TILE[row.marks[j]]} ${i === flipRow ? 'tile-flip' : ''}`}
                    style={{ '--i': j } as CSSProperties}
                    aria-label={`${ch}: ${t(MARK_KEY[row.marks[j]])}`}
                  >
                    <span aria-hidden="true">{ch}</span>
                  </div>
                ))}
              </div>
            ))}
            {Array.from({ length: emptyRows }, (_, i) => {
              // The current row shows what is being typed; the next empty tile is outlined in maroon.
              const typed = i === 0 ? [...input.trim()].slice(0, len) : []
              return (
                <div key={`e${i}`} aria-hidden="true" className="grid gap-1.5" style={cols}>
                  {Array.from({ length: len }, (_, j) => (
                    <div
                      key={j}
                      className={`flex h-11 items-center justify-center rounded-[10px] border-2 bg-white/70 uppercase text-ink ${
                        i === 0 && (j < typed.length || j === typed.length) ? 'border-maroon' : 'border-line'
                      }`}
                    >
                      {typed[j] ?? ''}
                    </div>
                  ))}
                </div>
              )
            })}
          </div>
          <div className="mt-3 flex flex-wrap justify-center gap-3 text-[13px] text-ink-2">
            {(['hit', 'near', 'miss'] as Mark[]).map((m) => (
              <span key={m} className="flex items-center gap-1.5">
                <span aria-hidden="true" className={`size-3 rounded-[3px] ${SWATCH[m]}`} />
                {t(MARK_KEY[m])}
              </span>
            ))}
          </div>
          {!state.finished ? (
            <form
              className="mt-4 flex gap-2"
              onSubmit={(e) => {
                e.preventDefault()
                submit()
              }}
            >
              <label htmlFor="code-input" className="sr-only">
                {t('code.inputLabel')}
              </label>
              <input
                id="code-input"
                dir={dir}
                lang={lang}
                value={input}
                maxLength={len + 3}
                autoComplete="off"
                autoCapitalize="none"
                spellCheck={false}
                onChange={(e) => setInput(e.target.value)}
                placeholder={t('code.placeholder', { n: len })}
                className="min-h-11 min-w-0 flex-1 rounded-xl border border-line bg-surface-2 px-3 text-lg font-bold text-ink placeholder:font-normal placeholder:text-muted focus:border-maroon"
              />
              <button type="submit" disabled={busy || !input.trim()} className="btn-primary min-h-11 px-5 text-base">
                {t('code.submit')}
              </button>
            </form>
          ) : (
            <div className="mt-4 flex flex-col items-center gap-2 text-center">
              <p role="status" className={`m-0 font-bold ${state.won ? 'text-success-text' : 'text-ink-2'}`}>
                {state.won ? t('code.won', { w: state.answer?.word ?? '' }) : t('code.lost', { w: state.answer?.word ?? '' })}
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                <button type="button" onClick={share} className="flex min-h-11 cursor-pointer items-center gap-1.5 rounded-xl border border-line bg-white px-3 font-bold text-ink">
                  {copied ? <Check aria-hidden="true" size={16} /> : <Copy aria-hidden="true" size={16} />}
                  {copied ? t('code.copied') : t('code.share')}
                </button>
                {state.answer && (
                  <Link href={`/glossary?q=${encodeURIComponent(state.answer.word)}`} className="flex min-h-11 items-center rounded-xl px-3 font-bold no-underline">
                    {t('code.openCard')}
                  </Link>
                )}
              </div>
            </div>
          )}
          <p role="status" aria-live="polite" className="mt-2 mb-0 min-h-5 text-center text-[13px] text-muted">
            {message ?? (state.finished ? '' : t('code.triesLeft', { n: tries - state.rows.length }))}
          </p>
        </>
      )}
    </section>
  )
}
