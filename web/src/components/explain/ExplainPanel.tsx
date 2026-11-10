import { AlertTriangle, ArrowRight, Check, Info, Loader2, RotateCcw, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useI18n, type MessageKey } from '../../i18n'
import { ApiError, findTerms, streamExplain, type Card, type ExplainResult, type ExplainStyle, type TermMatch } from '../../lib/api'
import { termKey, useDictionary } from '../../lib/dictionary'
import type { ExplainLang } from '../../lib/explainLang'
import { MicButton } from '../MicButton'
import { findPrivate, type PrivateKind } from '../../lib/privacy'
import { HighlightedText } from './HighlightedText'
import { QuickQuestion } from './QuickQuestion'
import { TermCard } from './TermCard'

const MAX = 6000
const STYLES: ExplainStyle[] = ['school', 'life', 'work', 'technical']

type Phase = 'idle' | 'streaming' | 'done'

/** `langControl` sits in the card header (the explanation language toggle on Home). */
export function ExplainPanel({ lang, langControl }: { lang: ExplainLang; langControl?: ReactNode }) {
  const { t, lang: uiLang } = useI18n()
  const dictionary = useDictionary()
  const isKnown = (en: string) => Boolean(dictionary.terms[termKey(en)])

  // A term sent from the glossary arrives as ?text=.
  const [text, setText] = useState(() => new URLSearchParams(window.location.search).get('text')?.slice(0, MAX) ?? '')
  const [style, setStyle] = useState<ExplainStyle>('school')
  const [matches, setMatches] = useState<TermMatch[]>([])
  const [privateKinds, setPrivateKinds] = useState<PrivateKind[]>([])
  const [phase, setPhase] = useState<Phase>('idle')
  const [explanation, setExplanation] = useState('')
  const [cards, setCards] = useState<Card[]>([])
  const [result, setResult] = useState<ExplainResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  // The chosen card by term, not by position, so it stays put as more chips arrive.
  const [picked, setPicked] = useState<string | null>(null)
  const abort = useRef<AbortController | null>(null)
  const resultRef = useRef<HTMLElement>(null)
  const textarea = useRef<HTMLTextAreaElement>(null)

  // Live term highlighting: deterministic, no AI, debounced while typing.
  useEffect(() => {
    if (!text.trim()) {
      setMatches([])
      return
    }
    const ctrl = new AbortController()
    const timer = setTimeout(() => {
      findTerms(text, ctrl.signal).then(setMatches).catch(() => {})
    }, 250)
    return () => {
      clearTimeout(timer)
      ctrl.abort()
    }
  }, [text])

  useEffect(() => () => abort.current?.abort(), [])

  const uniqueTerms = useMemo(() => [...new Map(matches.map((m) => [m.en, m])).values()], [matches])
  const knownCount = uniqueTerms.filter((m) => isKnown(m.en)).length

  const allCards = useMemo(() => {
    const out = [...cards, ...(result?.cards ?? [])]
    // Every highlighted term gets a chip: terms with neither a Darbi card nor a model card show their term bank entry.
    if (result) {
      const covered = new Set(out.map((c) => c.term_en.toLowerCase()))
      for (const m of matches) {
        if (covered.has(m.en.toLowerCase()) || covered.has(m.text.toLowerCase())) continue
        covered.add(m.en.toLowerCase())
        out.push({ id: m.id, term_en: m.en, term_ar: m.ar, explanation: '', analogy: '', related: [], source: 'bank' })
      }
    }
    // New chips only ever join at the end, so the card being read never moves or changes when the model's answer lands.
    return out
  }, [cards, result, matches])


  const send = async (skipPrivacy = false) => {
    if (!text.trim()) return
    if (!skipPrivacy) {
      const kinds = findPrivate(text)
      if (kinds.length) {
        setPrivateKinds(kinds)
        return
      }
    }
    setPrivateKinds([])
    abort.current?.abort()
    const ctrl = new AbortController()
    abort.current = ctrl
    setPhase('streaming')
    // On a phone the answer starts below the input card: bring it into view as soon as it starts.
    if (window.matchMedia?.('(max-width: 1023px)').matches) {
      requestAnimationFrame(() => {
        resultRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
      })
    }
    setExplanation('')
    setCards([])
    setPicked(null)
    setResult(null)
    setError(null)
    try {
      await streamExplain(
        { text, lang, style },
        {
          onTerms: (m, c) => {
            setMatches(m)
            setCards(c)
          },
          onExplanation: (piece) => setExplanation((e) => e + piece),
          onResult: (r) => {
            setResult(r)
            if (r.explanation) setExplanation(r.explanation)
          },
        },
        ctrl.signal,
      )
      setPhase('done')
    } catch (e) {
      if (ctrl.signal.aborted) return
      setPhase('done')
      setError(e instanceof ApiError && e.status === 429 ? t('explain.rateLimited', { n: e.retryAfter ?? 60 }) : t('explain.networkError'))
    }
  }

  const startEditing = () => {
    requestAnimationFrame(() => textarea.current?.focus())
  }

  const fallbackKey: MessageKey | null =
    result?.fallback === 'unavailable'
      ? 'explain.fallback.unavailable'
      : result?.fallback === 'unconfigured'
        ? 'explain.fallback.offline'
        : result?.fallback
          ? 'explain.fallback.failed'
          : null

  const selected = Math.max(0, picked ? allCards.findIndex((c) => c.term_en === picked) : 0)
  const card = allCards[selected]

  // Tapping a highlighted word opens its card below.
  const pickTerm = (m: TermMatch) => {
    const i = allCards.findIndex((c) => [m.en.toLowerCase(), m.text.toLowerCase()].includes(c.term_en.toLowerCase()))
    if (i < 0) return
    setPicked(allCards[i].term_en)
    requestAnimationFrame(() => document.getElementById('term-panel')?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }))
  }
  const showResult = phase !== 'idle'

  return (
    <>
      <section aria-labelledby="explain-h" className="card">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 id="explain-h" className="m-0 font-display text-xl font-semibold">
            <label htmlFor="explain-input">{t('explain.inputLabel')}</label>
          </h2>
          {langControl}
        </div>
        {/* The box stays open: a new text can be pasted any time. After explaining, the answer card repeats the text with
            its terms highlighted and tappable. */}
        <textarea
          id="explain-input"
          ref={textarea}
          dir="ltr"
          lang="en"
          value={text}
          maxLength={MAX}
          rows={5}
          placeholder={t('explain.placeholder')}
          onChange={(e) => setText(e.target.value)}
          className="block min-h-32 w-full resize-y rounded-xl sm:min-h-40 border border-line bg-surface-2 p-4 font-en text-[17px] leading-[1.8] text-ink placeholder:text-muted focus:border-maroon sm:p-5"
        />
        {/* The counter only matters near the limit. */}
        {text.length > MAX * 0.8 && <div className="mt-1 text-end text-[13px] text-muted">{t('explain.counter', { n: text.length, max: MAX })}</div>}

        {privateKinds.length > 0 && (
          <div role="alert" className="mt-4 rounded-xl border border-gold bg-gold-soft p-4 text-gold-text">
            <p className="m-0 flex items-center gap-2 font-bold">
              <AlertTriangle aria-hidden="true" size={20} />
              {t('explain.privateTitle')}
            </p>
            <p className="mt-1 mb-3">{t('explain.privateBody', { kinds: privateKinds.map((k) => t(`explain.privateKind.${k}` as MessageKey)).join(uiLang === 'ar' ? '، ' : ', ') })}</p>
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={startEditing} className="min-h-11 cursor-pointer rounded-lg border-2 border-gold-text bg-transparent px-4 font-bold text-gold-text">
                {t('explain.privateEdit')}
              </button>
              <button type="button" onClick={() => send(true)} className="min-h-11 cursor-pointer rounded-lg border-0 bg-transparent px-4 font-bold text-gold-text underline">
                {t('explain.privateSend')}
              </button>
            </div>
          </div>
        )}

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex min-h-11 items-center gap-2 rounded-lg border border-line bg-surface ps-3 text-sm text-ink-2">
              {t('explain.styleLabel')}
              <select
                value={style}
                onChange={(e) => setStyle(e.target.value as ExplainStyle)}
                className="min-h-11 cursor-pointer rounded-lg border-0 bg-transparent pe-2 font-semibold text-ink"
              >
                {STYLES.map((s) => (
                  <option key={s} value={s}>
                    {t(`style.${s}` as MessageKey)}
                  </option>
                ))}
              </select>
            </label>
            <MicButton onText={(said) => setText((v) => `${v} ${said}`.trim().slice(0, MAX))} />
          </div>
          <div className="flex flex-1 items-center justify-end gap-2">
            {text && phase !== 'streaming' && (
              <button
                type="button"
                onClick={() => {
                  setText('')
                  setPhase('idle')
                  setResult(null)
                  startEditing()
                }}
                className="flex min-h-11 cursor-pointer items-center gap-1 rounded-lg border-0 bg-transparent px-3 font-semibold text-muted hover:text-ink"
              >
                <X aria-hidden="true" size={16} />
                {t('explain.clear')}
              </button>
            )}
            <button type="button" className="btn-primary text-lg" disabled={!text.trim() || phase === 'streaming'} onClick={() => send()}>
              {phase === 'streaming' ? (
                <span className="flex items-center gap-2">
                  <Loader2 aria-hidden="true" size={20} className="animate-spin" />
                  {t('explain.working')}
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  {t('explain.submit')}
                  <ArrowRight aria-hidden="true" size={20} className="rtl:-scale-x-100" />
                </span>
              )}
            </button>
          </div>
        </div>
      </section>

      {showResult && (
        <section ref={resultRef} aria-label={t('explain.resultLabel')} aria-busy={phase === 'streaming'} className="card flex scroll-mt-4 flex-col gap-6">
          {matches.length > 0 && (
            <div>
              <div className="mb-2 flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
                <h3 className="m-0 text-base font-bold text-maroon">{t('explain.yourText')}</h3>
                <p className="m-0 flex flex-wrap gap-x-4 gap-y-1 text-sm text-ink-2">
                  <span>{t('explain.termsSummary', { n: uniqueTerms.length, k: knownCount })}</span>
                  <span className="flex items-center gap-1.5">
                    <span className="size-3 rounded-full bg-maroon" aria-hidden="true" />
                    {t('explain.legendNew')}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="flex size-4 items-center justify-center rounded-full bg-teal text-white" aria-hidden="true">
                      <Check size={10} strokeWidth={3.5} />
                    </span>
                    {t('explain.legendKnown')}
                  </span>
                </p>
              </div>
              <div dir="ltr" lang="en" className="well p-4 text-left font-en text-[17px] leading-[1.9] whitespace-pre-wrap sm:p-5">
                <HighlightedText
                  text={text}
                  matches={matches}
                  isKnown={isKnown}
                  knownLabel={t('explain.legendKnown')}
                  newLabel={t('explain.legendNew')}
                  onPick={result ? pickTerm : undefined}
                />
              </div>
            </div>
          )}
          {error && (
            <p role="alert" className="m-0 flex items-center gap-2 rounded-2xl bg-maroon-soft p-4 font-semibold text-maroon-text">
              <AlertTriangle aria-hidden="true" size={20} />
              {error}
            </p>
          )}
          {fallbackKey && (
            <div role="status" className="flex flex-wrap items-center gap-3 rounded-2xl bg-surface-3 p-4 text-ink-2">
              <Info aria-hidden="true" size={20} />
              <span className="flex-1">{t(fallbackKey)}</span>
              {result?.fallback === 'unavailable' && (
                <button type="button" onClick={() => send(true)} className="flex min-h-11 cursor-pointer items-center gap-1.5 rounded-xl border border-line bg-white px-4 font-bold text-ink">
                  <RotateCcw aria-hidden="true" size={16} />
                  {t('explain.retry')}
                </button>
              )}
            </div>
          )}
          {(explanation || phase === 'streaming') && !fallbackKey && (
            <div>
              <h3 className="m-0 mb-1 text-base font-bold text-maroon">{t('explain.meaning')}</h3>
              <p className="m-0 text-[17px]" dir={lang === 'en' ? 'ltr' : 'rtl'} lang={lang === 'en' ? 'en' : 'ar'}>
                {explanation}
                {phase === 'streaming' && <span aria-hidden="true" className="ms-1 inline-block h-4 w-1.5 animate-pulse bg-maroon align-middle" />}
              </p>
            </div>
          )}

          {allCards.length > 1 && (
            <div role="group" aria-label={t('explain.cardsLabel')} className="flex flex-wrap gap-2" dir="ltr">
              {allCards.map((c, i) => (
                <button
                  key={c.term_en}
                  type="button"
                  aria-pressed={i === selected}
                  onClick={() => setPicked(c.term_en)}
                  lang="en"
                  className={`min-h-11 cursor-pointer rounded-full border px-4 font-en text-sm font-semibold ${
                    i === selected ? 'border-maroon bg-maroon text-white' : 'border-line bg-white text-ink-2 hover:bg-surface-3'
                  }`}
                >
                  {c.term_en}
                </button>
              ))}
            </div>
          )}

          {(card || result?.question) && (
            <div id="term-panel" className="flex flex-wrap gap-7">
              {card && <TermCard key={card.term_en} card={card} lang={lang} showMsa={lang === 'gulf' && Boolean(card.term_gulf)} textDir={lang === 'en' ? 'ltr' : 'rtl'} />}
              {result?.question ? (
                <QuickQuestion key={result.question.question} question={result.question} textDir={lang === 'en' ? 'ltr' : 'rtl'} />
              ) : (
                phase === 'streaming' && (
                  // Holds the question's place while the model finishes, so the card beside it does not jump.
                  <div role="status" className="well flex min-h-64 min-w-0 flex-[1_1_300px] items-center justify-center gap-2 p-5 text-ink-2">
                    <Loader2 aria-hidden="true" size={20} className="animate-spin" />
                    {t('explain.preparingQuestion')}
                  </div>
                )
              )}
            </div>
          )}
          {phase === 'done' && !card && !result?.question && !error && !explanation && <p className="m-0 text-muted">{t('explain.noTerms')}</p>}
        </section>
      )}
    </>
  )
}
