import { AlertTriangle, ArrowRight, Camera, Check, Hourglass, Info, Loader2, Pencil, RotateCcw, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useI18n, type MessageKey } from '../../i18n'
import { ApiError, findTerms, streamExplain, type Card, type ExplainResult, type ExplainStyle, type TermMatch } from '../../lib/api'
import { termKey, useDictionary } from '../../lib/dictionary'
import type { ExplainLang } from '../../lib/explainLang'
import { imageFeatures, readImage, shrinkImage } from '../../lib/image'
import { MicButton } from '../MicButton'
import { findPrivate, type PrivateKind } from '../../lib/privacy'
import { HighlightedText } from './HighlightedText'
import { QuickQuestion } from './QuickQuestion'
import { TermCard } from './TermCard'

const MAX = 2000
const STYLES: ExplainStyle[] = ['work', 'school', 'life', 'technical', 'one_line', 'code', 'sentences']

type Phase = 'idle' | 'streaming' | 'done'

/** `langControl` sits in the card header (the explanation language toggle on Home). */
export function ExplainPanel({ lang, langControl }: { lang: ExplainLang; langControl?: ReactNode }) {
  const { t, lang: uiLang } = useI18n()
  const dictionary = useDictionary()
  const isKnown = (en: string) => Boolean(dictionary.terms[termKey(en)])

  // A term sent from the glossary ("Ask Fanar to explain") arrives as ?text=.
  const [text, setText] = useState(() => new URLSearchParams(window.location.search).get('text')?.slice(0, MAX) ?? '')
  const [style, setStyle] = useState<ExplainStyle>('work')
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
  // Photo explain (Fanar-2-Oryx-IVU): shown only when the server has it switched on.
  const [photoOn, setPhotoOn] = useState(false)
  const [reading, setReading] = useState(false)
  const [photoNote, setPhotoNote] = useState<string | null>(null)
  const photoInput = useRef<HTMLInputElement>(null)
  useEffect(() => {
    imageFeatures().then((f) => setPhotoOn(f.read))
  }, [])

  const onPhoto = async (file: File | undefined) => {
    if (!file) return
    setReading(true)
    setPhotoNote(null)
    try {
      const r = await readImage(await shrinkImage(file), lang)
      if (r.text) setText(r.text.slice(0, MAX))
      setPhotoNote(r.text ? r.description || t('photo.read') : t('photo.noText', { d: r.description }))
    } catch (e) {
      setPhotoNote(e instanceof ApiError && e.status === 503 ? t('photo.waking') : e instanceof ApiError && e.status === 429 ? t('tutor.limit') : t('photo.failed'))
    } finally {
      setReading(false)
      if (photoInput.current) photoInput.current.value = ''
    }
  }
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
    // Every highlighted term gets a chip: terms with neither a Darby nor a Fanar card show their term bank entry.
    if (result) {
      const covered = new Set(out.map((c) => c.term_en.toLowerCase()))
      for (const m of matches) {
        if (covered.has(m.en.toLowerCase()) || covered.has(m.text.toLowerCase())) continue
        covered.add(m.en.toLowerCase())
        out.push({ id: m.id, term_en: m.en, term_ar: m.ar, explanation: '', analogy: '', related: [], source: 'bank' })
      }
    }
    // New chips only ever join at the end, so the card being read never moves or changes when Fanar's answer lands.
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
    result?.fallback === 'waking'
      ? 'explain.fallback.waking'
      : result?.fallback === 'demo' || result?.fallback === 'unconfigured'
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
        <div className="mb-3.5 flex flex-wrap items-center justify-between gap-3">
          <h2 id="explain-h" className="m-0 flex items-center gap-2 font-display text-[22px] font-semibold text-maroon">
            <Pencil aria-hidden="true" size={20} />
            {t('home.explainTitle')}
          </h2>
          {langControl}
        </div>
        {uniqueTerms.length > 0 && (
          <p className="mt-0 mb-2 text-sm text-ink-2">{t('explain.termsSummary', { n: uniqueTerms.length, k: knownCount })}</p>
        )}

        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <label htmlFor="explain-input" className="font-semibold text-ink-2">
            {t('explain.inputLabel')}
          </label>
          <span className="flex flex-wrap items-center gap-2">
          <MicButton onText={(said) => setText((v) => `${v} ${said}`.trim().slice(0, MAX))} />
          {photoOn && (
            <>
              <input ref={photoInput} type="file" accept="image/*" capture="environment" className="sr-only" tabIndex={-1} aria-hidden="true" onChange={(e) => onPhoto(e.target.files?.[0])} />
              <button
                type="button"
                onClick={() => photoInput.current?.click()}
                disabled={reading}
                className="inline-flex min-h-11 cursor-pointer items-center gap-1.5 rounded-full border-0 bg-teal-soft px-4 text-sm font-bold text-teal-text disabled:cursor-wait"
              >
                {reading ? <Loader2 aria-hidden="true" size={16} className="animate-spin" /> : <Camera aria-hidden="true" size={16} />}
                {reading ? t('photo.reading') : t('photo.button')}
              </button>
            </>
          )}
          </span>
        </div>
        {photoNote && (
          <p role="status" className="mt-0 mb-2 text-sm text-ink-2">
            {photoNote}
          </p>
        )}
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
          className="block min-h-36 w-full resize-y rounded-[14px] border border-line bg-surface-2 p-5 font-en text-[17px] leading-[1.9] text-ink placeholder:text-muted focus:border-maroon"
        />
        <div className="mt-1 text-end text-[13px] text-muted">{t('explain.counter', { n: text.length, max: MAX })}</div>
        <p id="style-label" className="mt-4 mb-2 text-sm font-semibold text-ink-2">
          {t('explain.styleLabel')}
        </p>
        {/* One row that scrolls sideways on phones (seven chips took three rows), wrapping from 640 px. */}
        <div role="group" aria-labelledby="style-label" className="-mx-5 flex snap-x gap-2 overflow-x-auto px-5 pb-1 sm:mx-0 sm:flex-wrap sm:overflow-visible sm:px-0">
          {STYLES.map((s) => (
            <button
              key={s}
              type="button"
              aria-pressed={style === s}
              onClick={() => setStyle(s)}
              className={`min-h-11 shrink-0 cursor-pointer snap-start rounded-full border px-4 text-sm font-semibold whitespace-nowrap ${
                style === s ? 'border-maroon bg-maroon-soft text-maroon-text' : 'border-line bg-white text-ink-2 hover:bg-surface-3'
              }`}
            >
              {t(`style.${s}` as MessageKey)}
            </button>
          ))}
        </div>

        {privateKinds.length > 0 && (
          <div role="alert" className="mt-4 rounded-2xl border border-gold bg-gold-soft p-4 text-gold-text">
            <p className="m-0 flex items-center gap-2 font-bold">
              <AlertTriangle aria-hidden="true" size={20} />
              {t('explain.privateTitle')}
            </p>
            <p className="mt-1 mb-3">{t('explain.privateBody', { kinds: privateKinds.map((k) => t(`explain.privateKind.${k}` as MessageKey)).join(uiLang === 'ar' ? '، ' : ', ') })}</p>
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={startEditing} className="min-h-11 cursor-pointer rounded-xl border-2 border-gold-text bg-transparent px-4 font-bold text-gold-text">
                {t('explain.privateEdit')}
              </button>
              <button type="button" onClick={() => send(true)} className="min-h-11 cursor-pointer rounded-xl border-0 bg-transparent px-4 font-bold text-gold-text underline">
                {t('explain.privateSend')}
              </button>
            </div>
          </div>
        )}

        <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap gap-4 text-sm text-ink-2">
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
          </div>
          <div className="flex items-center gap-2">
            {text && phase !== 'streaming' && (
              <button
                type="button"
                onClick={() => {
                  setText('')
                  setPhase('idle')
                  setResult(null)
                  startEditing()
                }}
                className="flex min-h-11 cursor-pointer items-center gap-1 rounded-xl border-0 bg-transparent px-3 font-semibold text-muted hover:text-ink"
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
              <h3 className="m-0 mb-2 text-base font-bold text-maroon">{t('explain.yourText')}</h3>
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
              {result?.fallback === 'waking' ? <Hourglass aria-hidden="true" size={20} /> : <Info aria-hidden="true" size={20} />}
              <span className="flex-1">{t(fallbackKey)}</span>
              {result?.fallback === 'waking' && (
                <button type="button" onClick={() => send(true)} className="flex min-h-11 cursor-pointer items-center gap-1.5 rounded-xl border border-line bg-white px-4 font-bold text-ink">
                  <RotateCcw aria-hidden="true" size={16} />
                  {t('explain.retry')}
                </button>
              )}
            </div>
          )}
          {result?.off_topic && <p className="m-0 text-lg">{t('explain.offTopic')}</p>}

          {(explanation || phase === 'streaming') && !result?.off_topic && !fallbackKey && (
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
                  // Holds the question's place while Fanar finishes, so the card beside it does not jump.
                  <div role="status" className="well flex min-h-64 min-w-0 flex-[1_1_300px] items-center justify-center gap-2 p-5 text-ink-2">
                    <Loader2 aria-hidden="true" size={20} className="animate-spin" />
                    {t('explain.preparingQuestion')}
                  </div>
                )
              )}
            </div>
          )}
          {phase === 'done' && !card && !result?.question && !error && !result?.off_topic && <p className="m-0 text-muted">{t('explain.noTerms')}</p>}
        </section>
      )}
    </>
  )
}
