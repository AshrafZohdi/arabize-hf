import { AlertTriangle, Check, Hourglass, Info, Loader2, Pencil, RotateCcw, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useI18n, type MessageKey } from '../../i18n'
import { ApiError, findTerms, streamExplain, type Card, type ExplainResult, type ExplainStyle, type TermMatch } from '../../lib/api'
import { termKey, useDictionary } from '../../lib/dictionary'
import type { ExplainLang } from '../../lib/explainLang'
import { findPrivate, type PrivateKind } from '../../lib/privacy'
import { HighlightedText } from './HighlightedText'
import { QuickQuestion } from './QuickQuestion'
import { TermCard } from './TermCard'

const MAX = 2000
const STYLES: ExplainStyle[] = ['work', 'school', 'life', 'technical', 'one_line', 'code', 'sentences']

type Phase = 'idle' | 'streaming' | 'done'

export function ExplainPanel({ lang }: { lang: ExplainLang }) {
  const { t, lang: uiLang } = useI18n()
  const dictionary = useDictionary()
  const isKnown = (en: string) => Boolean(dictionary.terms[termKey(en)])

  // A term sent from the glossary ("Ask Fanar to explain") arrives as ?text=.
  const [text, setText] = useState(() => new URLSearchParams(window.location.search).get('text')?.slice(0, MAX) ?? '')
  const [editing, setEditing] = useState(true)
  const [style, setStyle] = useState<ExplainStyle>('work')
  const [matches, setMatches] = useState<TermMatch[]>([])
  const [privateKinds, setPrivateKinds] = useState<PrivateKind[]>([])
  const [phase, setPhase] = useState<Phase>('idle')
  const [explanation, setExplanation] = useState('')
  const [cards, setCards] = useState<Card[]>([])
  const [result, setResult] = useState<ExplainResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState(0)
  const abort = useRef<AbortController | null>(null)
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
    // Put the term the question is about first, as in the design.
    const answer = result?.question?.options[result.question.correct_index]?.toLowerCase()
    const i = answer ? out.findIndex((c) => c.term_en.toLowerCase() === answer) : -1
    if (i > 0) out.unshift(...out.splice(i, 1))
    return out
  }, [cards, result])

  useEffect(() => setSelected(0), [allCards.length])

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
    setEditing(false)
    setPhase('streaming')
    setExplanation('')
    setCards([])
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
    setEditing(true)
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

  const card = allCards[selected]
  const showResult = phase !== 'idle'

  return (
    <>
      <section aria-labelledby="explain-h" className="card">
        <div className="mb-3.5 flex flex-wrap items-center justify-between gap-3">
          <h2 id="explain-h" className="m-0 font-display text-[22px] font-semibold text-maroon">
            {t('home.explainTitle')}
          </h2>
          {uniqueTerms.length > 0 && (
            <span className="text-sm text-muted">{t('explain.termsSummary', { n: uniqueTerms.length, k: knownCount })}</span>
          )}
        </div>

        <label htmlFor="explain-input" className={editing ? 'mb-2 block font-semibold text-ink-2' : 'sr-only'}>
          {t('explain.inputLabel')}
        </label>
        {editing ? (
          <>
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
              onPaste={() => setTimeout(() => setEditing(false), 0)}
              onBlur={(e) => {
                // Show the highlighted view when focus leaves for something other than the style chips or buttons below.
                if (text.trim() && !e.relatedTarget) setEditing(false)
              }}
              className="block min-h-36 w-full resize-y rounded-[14px] border border-line bg-surface-2 p-5 font-en text-[17px] leading-[1.9] text-ink placeholder:text-muted focus:border-maroon"
            />
            <div className="mt-1 text-end text-[13px] text-muted">{t('explain.counter', { n: text.length, max: MAX })}</div>
          </>
        ) : (
          <>
            <div dir="ltr" lang="en" className="rounded-[14px] border border-line bg-surface-2 p-5 text-left font-en text-[17px] leading-[1.9] whitespace-pre-wrap">
              <HighlightedText text={text} matches={matches} isKnown={isKnown} knownLabel={t('explain.legendKnown')} newLabel={t('explain.legendNew')} />
            </div>
            <div className="mt-1 flex justify-end">
              <button
                type="button"
                onClick={startEditing}
                className="flex min-h-11 cursor-pointer items-center gap-1.5 rounded-xl border-0 bg-transparent px-2 font-semibold text-ink-2 hover:text-maroon"
              >
                <Pencil aria-hidden="true" size={16} />
                {t('explain.edit')}
              </button>
            </div>
          </>
        )}

        <div role="group" aria-label={t('explain.styleLabel')} className="mt-4 flex flex-wrap gap-2">
          {STYLES.map((s) => (
            <button
              key={s}
              type="button"
              aria-pressed={style === s}
              onClick={() => setStyle(s)}
              className={`min-h-11 cursor-pointer rounded-full border px-4 text-sm font-semibold ${
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
                t('explain.submit')
              )}
            </button>
          </div>
        </div>
      </section>

      {showResult && (
        <section aria-label={t('explain.resultLabel')} aria-busy={phase === 'streaming'} className="card flex flex-col gap-6">
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
              <p className="m-0 text-[17px]" dir={lang === 'en' ? 'ltr' : undefined} lang={lang === 'en' ? 'en' : 'ar'}>
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
                  onClick={() => setSelected(i)}
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
            <div className="flex flex-wrap gap-7">
              {card && <TermCard card={card} showMsa={lang === 'gulf' && Boolean(card.term_gulf)} />}
              {result?.question && <QuickQuestion key={result.question.question} question={result.question} />}
            </div>
          )}
          {phase === 'done' && !card && !result?.question && !error && !result?.off_topic && <p className="m-0 text-muted">{t('explain.noTerms')}</p>}
        </section>
      )}
    </>
  )
}
