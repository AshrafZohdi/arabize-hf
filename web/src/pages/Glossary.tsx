import { BookOpen, Search, Sparkles, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { PageTitle } from '../components/PageTitle'
import { Segmented } from '../components/Segmented'
import { useI18n, type MessageKey } from '../i18n'
import { glossaryBrowse, glossaryCards, glossarySearch, type GlossaryCard, type QuickCard } from '../lib/api'
import { removeTerm, saveTerm, termKey, useDictionary } from '../lib/dictionary'
import { useExplainLang } from '../lib/explainLang'
import { Link } from '../lib/router'
import { ListenButtons } from '../components/ListenButtons'

type Domain = 'all' | 'ai' | 'software'

const CARDS_FIRST = 12

export function GlossaryPage() {
  const { t } = useI18n()
  const [lang] = useExplainLang()
  const params = new URLSearchParams(window.location.search)
  const [q, setQ] = useState(() => params.get('q') ?? '')
  const [domain, setDomain] = useState<Domain>('all')
  const [cards, setCards] = useState<GlossaryCard[]>([])
  const [results, setResults] = useState<QuickCard[] | null>(null)
  const [suggestion, setSuggestion] = useState<QuickCard | null>(null)
  const [bankSize, setBankSize] = useState(0)
  const [error, setError] = useState(false)
  const [open, setOpen] = useState<GlossaryCard | null>(null)

  useEffect(() => {
    glossaryCards(lang).then(setCards).catch(() => setError(true))
  }, [lang])

  useEffect(() => {
    if (!q.trim()) {
      setResults(null)
      return
    }
    const ctrl = new AbortController()
    const timer = setTimeout(() => {
      glossarySearch(q, domain, ctrl.signal)
        .then((r) => {
          setResults(r.results)
          setSuggestion(r.suggestion)
          setBankSize(r.terms)
          setError(false)
        })
        .catch((e) => {
          if (!ctrl.signal.aborted) setError(Boolean(e))
        })
    }, 250)
    return () => {
      clearTimeout(timer)
      ctrl.abort()
    }
  }, [q, domain])

  const shownCards = cards.filter((c) => domain === 'all' || c.domain === domain)
  // 12 cards first: all of them pushed search results and A to Z many screens down on a phone.
  const [allCards, setAllCards] = useState(false)
  const visibleCards = allCards ? shownCards : shownCards.slice(0, CARDS_FIRST)
  const cardById = new Map(cards.map((c) => [c.id, c]))
  const domains: { value: Domain; label: string }[] = [
    { value: 'all', label: t('glossary.domain.all') },
    { value: 'ai', label: t('glossary.domain.ai') },
    { value: 'software', label: t('glossary.domain.software') },
  ]

  return (
    <>
      <PageTitle title={t('glossary.title')} subtitle={t('glossary.subtitle')} />
      <div className="card mb-7 flex flex-col gap-4">
        <label htmlFor="glossary-q" className="font-semibold text-ink-2">
          {t('glossary.searchLabel')}
        </label>
        <div className="relative">
          <Search aria-hidden="true" size={20} className="pointer-events-none absolute start-4 top-1/2 -translate-y-1/2 text-muted" />
          <input
            id="glossary-q"
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t('glossary.searchPlaceholder')}
            autoComplete="off"
            dir="auto"
            className="block min-h-14 w-full rounded-2xl border border-line bg-surface-2 ps-12 pe-4 text-lg text-ink placeholder:text-muted focus:border-maroon"
          />
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Segmented label={t('glossary.filterLabel')} options={domains} value={domain} onChange={setDomain} />
          {results && bankSize > 0 && <span className="text-sm text-muted">{t('glossary.bankSize', { n: bankSize.toLocaleString('en-US') })}</span>}
        </div>
      </div>

      {error && (
        <p role="alert" className="rounded-2xl bg-maroon-soft p-4 font-semibold text-maroon-text">
          {t('glossary.error')}
        </p>
      )}

      <MyDictionary open={params.get('mine') === '1'} />

      {results ? (
        <section aria-live="polite" aria-label={t('glossary.results', { n: results.length })}>
          {suggestion && (
            <p className="glass mt-0 mb-3 flex flex-wrap items-center gap-2 rounded-2xl! px-4 py-2 text-ink-2">
              {t('glossary.didYouMean')}
              <button
                type="button"
                onClick={() => setQ(suggestion.en)}
                className="min-h-11 cursor-pointer rounded-full border-0 bg-maroon-soft px-4 font-en font-bold text-maroon-text"
                lang="en"
              >
                {suggestion.en}
              </button>
              <span lang="ar">{suggestion.ar}</span>
            </p>
          )}
          <p className="mt-0 mb-3 font-semibold text-ink-2">{t('glossary.results', { n: results.length })}</p>
          {results.length === 0 && <p className="text-muted">{t('glossary.empty')}</p>}
          <ul className="m-0 grid list-none grid-cols-1 gap-3 p-0 md:grid-cols-2">
            {results.map((r) => (
              <QuickCardItem key={r.id} r={r} full={cardById.get(r.id)} onOpen={setOpen} />
            ))}
          </ul>
          {shownCards.length > CARDS_FIRST && (
            <button
              type="button"
              onClick={() => setAllCards((v) => !v)}
              aria-expanded={allCards}
              className="mx-auto mt-4 flex min-h-11 cursor-pointer items-center rounded-full border border-white/80 bg-white/80 px-5 font-bold text-maroon shadow-[0_3px_0_var(--shadow)]"
            >
              {allCards ? t('glossary.fewerCards') : t('glossary.allCards', { n: shownCards.length })}
            </button>
          )}
        </section>
      ) : (
        <section aria-labelledby="full-h">
          <h2 id="full-h" className="m-0 font-display text-[22px] font-semibold text-maroon">
            {t('glossary.fullCards')}
          </h2>
          <p className="mt-1 mb-4 text-muted">{t('glossary.fullCardsNote')}</p>
          <ul className="m-0 grid list-none grid-cols-1 gap-3 p-0 min-[480px]:grid-cols-2 lg:grid-cols-3">
            {visibleCards.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => setOpen(c)}
                  className="glass lift flex min-h-[88px] w-full cursor-pointer items-center gap-3 rounded-[20px]! p-4 text-start text-ink"
                >
                  <span className="flex size-11 shrink-0 items-center justify-center rounded-[14px] bg-maroon-soft text-maroon">
                    {c.source === 'fanar' ? <Sparkles aria-hidden="true" size={22} /> : <BookOpen aria-hidden="true" size={22} />}
                    <span className="sr-only">{c.source === 'fanar' ? t('explain.fromFanar') : t('explain.fromGlossary')}</span>
                  </span>
                  <span className="min-w-0">
                    <span className="block font-display text-lg font-semibold text-maroon">{c.term_ar}</span>
                    <span dir="ltr" lang="en" className="block font-en font-semibold text-ink-2">
                      {c.term_en}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
      {!results && <BrowseAll domain={domain} cardById={cardById} onOpen={setOpen} />}
      <FullCardDialog card={open} onClose={() => setOpen(null)} />
    </>
  )
}

/** Terms the learner saved, kept in this browser. Shown when there are any. */
function MyDictionary({ open }: { open: boolean }) {
  const { t } = useI18n()
  const { terms } = useDictionary()
  const list = Object.values(terms).sort((a, b) => b.savedAt.localeCompare(a.savedAt))
  if (list.length === 0) return null
  return (
    <details open={open} className="card mb-7">
      <summary className="min-h-11 cursor-pointer font-display text-[22px] font-semibold text-maroon">
        {t('glossary.mine')} ({list.length})
      </summary>
      <p className="mt-1 mb-3 text-muted">{t('glossary.mineNote')}</p>
      <ul className="m-0 grid list-none grid-cols-1 gap-2 p-0 md:grid-cols-2">
        {list.map((s) => (
          <li key={s.term_en} className="flex items-center justify-between gap-2 rounded-2xl border border-line bg-surface-2 p-3">
            <span className="min-w-0">
              <span className="block font-display font-semibold text-maroon">{s.term_ar}</span>
              <span dir="ltr" lang="en" className="block font-en text-sm font-semibold text-ink-2">
                {s.term_en}
              </span>
            </span>
            <button type="button" onClick={() => removeTerm(s.term_en)} aria-label={`${t('glossary.remove')}: ${s.term_en}`} className="flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-xl border border-line bg-white text-ink-2">
              <X aria-hidden="true" size={18} />
            </button>
          </li>
        ))}
      </ul>
    </details>
  )
}

const LETTERS = ['#', ...'abcdefghijklmnopqrstuvwxyz']

/** Every term in the bank, A to Z, 50 at a time: nothing is only reachable by searching. */
function BrowseAll({ domain, cardById, onOpen }: { domain: Domain; cardById: Map<string, GlossaryCard>; onOpen: (c: GlossaryCard) => void }) {
  const { t } = useI18n()
  const [letter, setLetter] = useState('')
  const [items, setItems] = useState<QuickCard[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const ctrl = new AbortController()
    setLoading(true)
    glossaryBrowse(domain, letter, 0, ctrl.signal)
      .then((r) => {
        setItems(r.results)
        setTotal(r.total)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
    return () => ctrl.abort()
  }, [domain, letter])

  const more = () => {
    setLoading(true)
    glossaryBrowse(domain, letter, items.length)
      .then((r) => setItems((prev) => [...prev, ...r.results]))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  return (
    <section aria-labelledby="all-h" className="card mt-10">
      <h2 id="all-h" className="m-0 font-display text-[22px] font-semibold text-maroon">
        {t('glossary.allTerms')}
      </h2>
      <p className="mt-1 mb-4 text-muted">{t('glossary.allTermsNote', { n: total.toLocaleString('en-US') })}</p>
      {/* One sideways-scrolling row on phones (27 letters wrapped into six rows), wrapping from 640 px. */}
      <div role="group" aria-label={t('glossary.letterLabel')} dir="ltr" className="-mx-5 mb-4 flex gap-1.5 overflow-x-auto px-5 pb-1 sm:mx-0 sm:flex-wrap sm:overflow-visible sm:px-0">
        {['', ...LETTERS].map((l) => (
          <button
            key={l || 'all'}
            type="button"
            aria-pressed={letter === l}
            onClick={() => setLetter(l)}
            className={`min-h-11 min-w-11 shrink-0 cursor-pointer rounded-full border-0 px-2 font-en font-bold uppercase ${
              letter === l ? 'bg-ink text-white' : 'bg-transparent text-ink-2 hover:bg-white/70'
            }`}
          >
            {l || t('glossary.allLetters')}
          </button>
        ))}
      </div>
      <ul className="m-0 grid list-none grid-cols-1 gap-3 p-0 md:grid-cols-2">
        {items.map((r) => (
          <QuickCardItem key={r.id} r={r} full={cardById.get(r.id)} onOpen={onOpen} />
        ))}
      </ul>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <span className="text-sm text-muted" aria-live="polite">
          {t('glossary.shown', { k: items.length.toLocaleString('en-US'), n: total.toLocaleString('en-US') })}
        </span>
        {items.length < total && (
          <button type="button" onClick={more} disabled={loading} className="btn-primary min-h-12 px-6 text-base">
            {t('glossary.showMore')}
          </button>
        )}
      </div>
    </section>
  )
}

function QuickCardItem({ r, full, onOpen }: { r: QuickCard; full?: GlossaryCard; onOpen: (c: GlossaryCard) => void }) {
  const { t } = useI18n()
  // Compact: names on top, then source and actions on one line (an entry used to take most of a phone screen).
  return (
    <li className="well flex flex-col gap-1.5 px-4 py-3">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <span className="font-display text-lg font-semibold text-maroon" lang="ar">
          {r.ar}
        </span>
        <span dir="ltr" lang="en" className="font-en font-semibold text-ink-2">
          {r.en}
        </span>
      </div>
      {r.en_expanded && (
        <p className="m-0 text-sm text-ink-2">
          {t('glossary.expanded', { t: '' })}
          <bdi lang="en">{r.en_expanded}</bdi>
        </p>
      )}
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-muted">
        <span>{t(`glossary.source.${r.source}` as MessageKey)}</span>
        {r.needs_review && <span className="rounded-full bg-gold-soft px-2 py-0.5 font-semibold text-gold-text">{t('glossary.needsReview')}</span>}
        {r.match === 'meaning' && (
          <span className="flex items-center gap-1 rounded-full bg-teal-soft px-2 py-0.5 font-bold text-teal-text">
            <Sparkles aria-hidden="true" size={12} />
            {t('glossary.byMeaning')}
          </span>
        )}
        <span className="ms-auto flex flex-wrap gap-1">
          {full && (
            <button type="button" onClick={() => onOpen(full)} className="min-h-11 cursor-pointer rounded-xl border border-line bg-white px-3 text-sm font-bold text-ink hover:bg-surface-3">
              {t('glossary.open')}
            </button>
          )}
          <Link href={`/?text=${encodeURIComponent(r.en)}`} className="flex min-h-11 items-center rounded-xl px-2 text-sm font-bold no-underline">
            {t('glossary.askFanar')}
          </Link>
        </span>
      </div>
    </li>
  )
}

function FullCardDialog({ card, onClose }: { card: GlossaryCard | null; onClose: () => void }) {
  const { t } = useI18n()
  const [explainLang] = useExplainLang()
  const textDir = explainLang === 'en' ? 'ltr' : 'rtl' // card text follows the explanation language, not the interface
  const ref = useRef<HTMLDialogElement>(null)
  const opener = useRef<Element | null>(null)
  const saved = useDictionary().terms[termKey(card?.term_en ?? '')]

  useEffect(() => {
    const d = ref.current
    if (!d) return
    if (card && !d.open) {
      opener.current = document.activeElement
      d.showModal?.()
    } else if (!card && d.open) {
      d.close()
    }
  }, [card])

  const close = () => {
    onClose()
    // Safari does not focus buttons on click, so fall back to the element that was active when the dialog opened.
    requestAnimationFrame(() => (opener.current as HTMLElement | null)?.focus?.())
  }

  return (
    <dialog
      ref={ref}
      onClose={close}
      onClick={(e) => e.target === ref.current && close()}
      aria-labelledby="card-title"
      className="glass m-auto w-[min(640px,calc(100vw-32px))] max-h-[calc(100dvh-32px)] rounded-[28px]! bg-surface/90! p-0 text-ink"
    >
      {card && (
        <div className="flex flex-col gap-4 p-5 sm:p-7">
          <div className="flex items-start gap-3">
            <div className="min-w-0 flex-1">
              <h2 id="card-title" className="m-0 font-display text-[26px] font-semibold text-maroon">
                {card.term_ar}
              </h2>
              <span dir="ltr" lang="en" className="font-en text-lg font-semibold text-ink-2">
                {card.term_en}
              </span>
            </div>
            <button type="button" onClick={close} aria-label={t('glossary.close')} className="flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-xl border border-line bg-white text-ink-2">
              <X aria-hidden="true" size={20} />
            </button>
          </div>
          <p className="m-0 flex items-center gap-1.5 text-[13px] text-muted">
            {card.source === 'fanar' ? <Sparkles aria-hidden="true" size={14} /> : <BookOpen aria-hidden="true" size={14} />}
            {card.source === 'fanar' ? t('explain.fromFanar') : t('explain.fromGlossary')}
          </p>
          <ListenButtons en={card.term_en} ar={card.term_ar} termId={card.id} />
          {card.term_gulf && <p className="m-0 text-ink-2">{t('glossary.gulfUsage', { t: card.term_gulf })}</p>}
          <Field label={t('glossary.definition')} dir={textDir}>
            {card.explanation}
          </Field>
          {card.analogy && (
            <div className="rounded-[14px] bg-surface-3 px-4 py-3 text-ink-2" dir={textDir}>
              {card.analogy}
            </div>
          )}
          {card.example && (
            <Field label={t('glossary.example')} dir={textDir}>
              {card.example}
            </Field>
          )}
          {card.mistake && (
            <Field label={t('glossary.mistake')} dir={textDir}>
              {card.mistake}
            </Field>
          )}
          {card.related.length > 0 && (
            <Field label={t('glossary.related')}>
              <span dir="ltr" lang="en" className="font-en">
                {card.related.join(', ')}
              </span>
            </Field>
          )}
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={Boolean(saved)}
              onClick={() => saveTerm(card)}
              className="min-h-11 cursor-pointer rounded-full border border-line bg-white px-4 font-bold text-ink disabled:cursor-default disabled:bg-teal-soft disabled:text-teal-text"
            >
              {saved ? t('explain.saved') : t('explain.save')}
            </button>
            <Link href={`/?text=${encodeURIComponent(card.term_en)}`} className="flex min-h-11 items-center rounded-full px-4 font-bold no-underline">
              {t('glossary.askFanar')}
            </Link>
          </div>
        </div>
      )}
    </dialog>
  )
}

function Field({ label, children, dir }: { label: string; children: React.ReactNode; dir?: 'rtl' | 'ltr' }) {
  return (
    <div>
      <h3 className="m-0 mb-1 text-sm font-bold text-maroon">{label}</h3>
      <p className="m-0 text-[17px]" dir={dir}>
        {children}
      </p>
    </div>
  )
}
