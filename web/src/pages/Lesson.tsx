import { ArrowDown, ArrowUp, Check, PartyPopper, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Segmented } from '../components/Segmented'
import { useI18n, type MessageKey } from '../i18n'
import { ApiError, type Card } from '../lib/api'
import { useExplainLang, type ExplainLang } from '../lib/explainLang'
import { completeLesson, LESSON_XP } from '../lib/lessonProgress'
import { buildSteps, pick, seededShuffle, segments, termSlug, withRetries, type Step, type Texts } from '../lib/lessonSteps'
import { award } from '../lib/progress'
import { Link, useRouter } from '../lib/router'
import { PromptLab } from './Tutor'

type Exercise = Record<string, unknown> & { type: 'mcq' | 'match' | 'fill' | 'order'; explanation?: Texts }
type Block = { type: string; en?: string; ar?: string; gulf?: string; terms?: string[]; exercises?: Exercise[] }
type Lesson = { slug: string; order: number; title: Texts; blocks: Block[] }

const BLOCK_TITLE: Record<string, MessageKey> = {
  hook: 'lesson.hook',
  concept: 'lesson.concept',
  example: 'lesson.example',
  key_terms: 'lesson.keyTerms',
  prompt_lab: 'lesson.promptLab',
  recap: 'lesson.recap',
}
const EXERCISE_XP = 5 // first-try exercise (old app's rule)

export function LessonPage({ slug }: { slug: string }) {
  const { t } = useI18n()
  const { navigate } = useRouter()
  const [lang, setLang] = useExplainLang()
  const [lesson, setLesson] = useState<Lesson | null>(null)
  const [missing, setMissing] = useState(false)
  const [steps, setSteps] = useState<Step[]>([])
  const [at, setAt] = useState(0)
  const [missed, setMissed] = useState<Step[]>([])
  const [answered, setAnswered] = useState(false)
  const [finished, setFinished] = useState<number | null>(null)
  const [termOpen, setTermOpen] = useState<string | null>(null)
  const top = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    fetch(`/api/lessons/${slug}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new ApiError(r.status))))
      .then((d: Lesson) => {
        setLesson(d)
        setSteps(buildSteps(d.blocks))
      })
      .catch(() => setMissing(true))
  }, [slug])

  useEffect(() => {
    // Move focus to the step heading so keyboard and screen reader users start at the top of each screen.
    top.current?.focus()
  }, [at, finished])

  if (missing) {
    return (
      <div className="card">
        <p className="mt-0">{t('lesson.notFound')}</p>
        <Link href="/">{t('lesson.backHome')}</Link>
      </div>
    )
  }
  if (!lesson || steps.length === 0) return null

  const step = steps[at]
  const isExercise = step.kind === 'exercise'
  const canNext = !isExercise || answered
  const title = pick(lesson.title, lang)

  const next = () => {
    const target = at + 1
    if (target >= steps.length) {
      setFinished(completeLesson(lesson.slug))
      return
    }
    // Reaching the recap: missed exercises come back first, once.
    const recapIndex = steps.length - 1
    if (target === recapIndex && missed.length) {
      setSteps(withRetries(steps, missed, target))
      setMissed([])
    }
    setAt(target)
    setAnswered(false)
  }

  const onResult = (firstTry: boolean, correct: boolean) => {
    setAnswered(true)
    if (step.kind !== 'exercise') return
    if (correct && firstTry && !step.retry) award(`ex:${lesson.slug}:${step.block}:${step.index}`, EXERCISE_XP)
    if (!correct && !step.retry) setMissed((m) => [...m, step])
  }

  const langOptions: { value: ExplainLang; label: string; lang: string }[] = [
    { value: 'en', label: t('lang.en'), lang: 'en' },
    { value: 'msa', label: t('lang.msa'), lang: 'ar' },
    { value: 'gulf', label: t('lang.gulf'), lang: 'ar' },
  ]

  return (
    <div className="mx-auto flex max-w-[760px] flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link href="/" className="flex min-h-11 items-center gap-1.5 font-semibold no-underline">
          <X aria-hidden="true" size={18} />
          {t('lesson.exit')}
        </Link>
        <Segmented label={t('home.explainLanguage')} options={langOptions} value={lang} onChange={setLang} />
      </div>
      <div>
        <p className="m-0 font-display text-lg font-semibold text-ink-2" lang={title.lang} dir={title.lang === 'en' ? 'ltr' : 'rtl'}>
          {lesson.order}. {title.text}
        </p>
        <div className="mt-2 flex items-center gap-3">
          <div
            role="progressbar"
            aria-valuemin={1}
            aria-valuemax={steps.length}
            aria-valuenow={Math.min(at + 1, steps.length)}
            aria-label={t('lesson.progress', { k: Math.min(at + 1, steps.length), n: steps.length })}
            className="h-3 flex-1 overflow-hidden rounded-full bg-line"
          >
            <div className="h-full rounded-full bg-maroon transition-[width]" style={{ width: `${((finished !== null ? steps.length : at + 1) / steps.length) * 100}%` }} />
          </div>
          <span className="text-sm text-muted">{t('lesson.progress', { k: Math.min(at + 1, steps.length), n: steps.length })}</span>
        </div>
      </div>

      {finished !== null ? (
        <section className="card flex flex-col items-center gap-3 text-center">
          <PartyPopper aria-hidden="true" size={44} className="text-gold" />
          <h1 ref={top} tabIndex={-1} className="m-0 font-display text-[28px] font-semibold text-maroon">
            {t('lesson.done')}
          </h1>
          <p className="m-0 rounded-full bg-gold-soft px-4 py-1 text-lg font-bold text-gold-text">{t('lesson.doneXp', { n: finished || LESSON_XP })}</p>
          <button type="button" className="btn-primary" onClick={() => navigate('/')}>
            {t('lesson.backHome')}
          </button>
        </section>
      ) : (
        <section className="card flex flex-col gap-4" aria-live="polite">
          <h1 ref={top} tabIndex={-1} className="m-0 font-display text-[22px] font-semibold text-maroon outline-none">
            {isExercise ? `${t('lesson.exercise')}${step.retry ? ` · ${t('lesson.again')}` : ''}` : t(BLOCK_TITLE[lesson.blocks[step.block].type] ?? 'lesson.concept')}
          </h1>
          {step.kind === 'block' ? (
            <BlockView block={lesson.blocks[step.block]} lang={lang} slug={lesson.slug} onTerm={setTermOpen} />
          ) : (
            <ExerciseView
              key={`${at}-${step.block}-${step.index}`}
              ex={lesson.blocks[step.block].exercises![step.index]}
              lang={lang}
              seed={`${lesson.slug}:${step.block}:${step.index}`}
              onResult={onResult}
            />
          )}
          <div className="flex justify-end">
            <button type="button" className="btn-primary" disabled={!canNext} onClick={next}>
              {at === steps.length - 1 ? t('lesson.finish') : t('lesson.next')}
            </button>
          </div>
        </section>
      )}
      <TermDialog id={termOpen} lang={lang} onClose={() => setTermOpen(null)} />
    </div>
  )
}

function RichText({ texts, lang, onTerm }: { texts: Texts; lang: ExplainLang; onTerm: (id: string) => void }) {
  const shown = pick(texts, lang)
  return (
    <div lang={shown.lang} dir={shown.lang === 'en' ? 'ltr' : 'rtl'} className={`text-[17px] whitespace-pre-line ${shown.lang === 'en' ? 'font-en text-left' : ''}`}>
      {segments(shown.text).map((s, i) =>
        'term' in s ? (
          <button
            key={i}
            type="button"
            onClick={() => onTerm(termSlug(s.term))}
            className="inline cursor-pointer rounded-md border-0 bg-maroon-soft px-1 font-[inherit] text-[inherit] font-bold text-maroon-text underline decoration-dotted underline-offset-4"
          >
            {s.label}
          </button>
        ) : (
          <span key={i}>{s.text}</span>
        ),
      )}
    </div>
  )
}

function BlockView({ block, lang, slug, onTerm }: { block: Block; lang: ExplainLang; slug: string; onTerm: (id: string) => void }) {
  if (block.type === 'key_terms') {
    return (
      <ul className="m-0 flex list-none flex-wrap gap-2 p-0" dir="ltr">
        {(block.terms ?? []).map((term) => (
          <li key={term}>
            <button type="button" onClick={() => onTerm(termSlug(term))} lang="en" className="min-h-11 cursor-pointer rounded-full border border-line bg-white px-4 font-en font-bold text-maroon hover:bg-maroon-soft">
              {term}
            </button>
          </li>
        ))}
      </ul>
    )
  }
  if (block.type === 'prompt_lab') return <PromptLab lang={lang} lesson={slug} />
  return <RichText texts={block} lang={lang} onTerm={onTerm} />
}

function ExerciseView({ ex, lang, seed, onResult }: { ex: Exercise; lang: ExplainLang; seed: string; onResult: (firstTry: boolean, correct: boolean) => void }) {
  const { t } = useI18n()
  const [tries, setTries] = useState(0)
  const [state, setState] = useState<'open' | 'right' | 'wrong'>('open')
  const optionLang = lang === 'en' ? 'en' : 'ar'
  const explanation = pick(ex.explanation, lang)

  const result = (ok: boolean) => {
    const first = tries === 0
    setTries((n) => n + 1)
    setState(ok ? 'right' : 'wrong')
    onResult(first, ok)
  }

  let body: React.ReactNode = null
  if (ex.type === 'mcq') {
    const q = pick(ex.question as Texts, lang)
    const options = ex.options as Texts[]
    body = (
      <>
        <p className="m-0 text-lg font-bold" lang={q.lang} dir={q.lang === 'en' ? 'ltr' : 'rtl'}>
          {q.text}
        </p>
        <div className="grid grid-cols-1 gap-2.5">
          {options.map((o, i) => {
            const label = (optionLang === 'en' ? o.en : o.ar) ?? o.en ?? ''
            const chosenRight = state === 'right' && i === (ex.correct as number)
            return (
              <button
                key={i}
                type="button"
                disabled={state === 'right'}
                onClick={() => result(i === (ex.correct as number))}
                className={`flex min-h-[52px] cursor-pointer items-center justify-between gap-2 rounded-[14px] border-2 px-4 text-start font-semibold ${
                  chosenRight ? 'border-success bg-success-soft text-success-text' : 'border-line bg-white text-ink shadow-answer hover:border-maroon'
                }`}
              >
                <span dir="auto">{label}</span>
                {chosenRight && <Check aria-hidden="true" size={18} strokeWidth={3} />}
              </button>
            )
          })}
        </div>
      </>
    )
  } else if (ex.type === 'fill') {
    body = <FillView ex={ex} lang={lang} done={state === 'right'} onPick={(ok) => result(ok)} />
  } else if (ex.type === 'match') {
    body = <MatchView ex={ex} lang={lang} seed={seed} done={state === 'right'} onDone={(ok) => result(ok)} />
  } else if (ex.type === 'order') {
    body = <OrderView ex={ex} lang={lang} seed={seed} done={state === 'right'} onCheck={(ok) => result(ok)} />
  }

  return (
    <div className="flex flex-col gap-4">
      {body}
      <p role="status" className="m-0 min-h-6 font-semibold">
        {state === 'right' && (
          <span className="flex items-start gap-2 text-success-text">
            <Check aria-hidden="true" size={18} className="mt-1 shrink-0" />
            <span>
              {t('lesson.correct')} <span lang={explanation.lang}>{explanation.text}</span>
            </span>
          </span>
        )}
        {state === 'wrong' && (
          <span className="flex items-start gap-2 text-ink-2">
            <X aria-hidden="true" size={18} className="mt-1 shrink-0" />
            <span>
              {t('lesson.wrong')} <span lang={explanation.lang}>{explanation.text}</span>
            </span>
          </span>
        )}
      </p>
    </div>
  )
}

function FillView({ ex, lang, done, onPick }: { ex: Exercise; lang: ExplainLang; done: boolean; onPick: (ok: boolean) => void }) {
  const prompt = pick(ex.prompt as Texts, lang)
  const sentence = (ex.sentence as Texts).en ?? ''
  const bank = ex.bank as Texts[]
  const [chosen, setChosen] = useState<number | null>(null)
  const [before, after] = sentence.split('___')
  return (
    <>
      <p className="m-0 font-bold" lang={prompt.lang}>
        {prompt.text}
      </p>
      <p dir="ltr" lang="en" className="m-0 rounded-2xl bg-surface-2 p-4 text-left font-en text-lg">
        {before}
        <span className="mx-1 inline-block min-w-16 border-b-2 border-maroon text-center font-bold text-maroon">{chosen !== null ? bank[chosen].en : ' '}</span>
        {after}
      </p>
      <div className="flex flex-wrap gap-2" dir="ltr">
        {bank.map((b, i) => (
          <button
            key={i}
            type="button"
            disabled={done}
            onClick={() => {
              setChosen(i)
              onPick(i === (ex.answer as number))
            }}
            lang="en"
            className="min-h-11 cursor-pointer rounded-full border-2 border-line bg-white px-4 font-en font-bold text-ink hover:border-maroon"
          >
            {b.en}
          </button>
        ))}
      </div>
    </>
  )
}

function MatchView({ ex, lang, seed, done, onDone }: { ex: Exercise; lang: ExplainLang; seed: string; done: boolean; onDone: (ok: boolean) => void }) {
  const { t } = useI18n()
  const prompt = pick(ex.prompt as Texts, lang)
  const pairs = ex.pairs as { left: string; right: Texts }[]
  const rights = useMemo(() => seededShuffle(pairs.map((_, i) => i), seed), [pairs, seed])
  const [left, setLeft] = useState<number | null>(null)
  const [matched, setMatched] = useState<number[]>([])
  const [mistake, setMistake] = useState(false)
  const pickRight = (i: number) => {
    if (left === null || done) return
    if (left === i) {
      const m = [...matched, i]
      setMatched(m)
      setLeft(null)
      if (m.length === pairs.length) onDone(!mistake)
    } else {
      setMistake(true)
      setLeft(null)
    }
  }
  return (
    <>
      <p className="m-0 font-bold" lang={prompt.lang}>
        {prompt.text}
      </p>
      <p className="m-0 text-sm text-muted">{t('lesson.match.pick')}</p>
      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-2" dir="ltr">
          {pairs.map((p, i) => (
            <button
              key={i}
              type="button"
              aria-pressed={left === i}
              disabled={matched.includes(i) || done}
              onClick={() => setLeft(i)}
              lang="en"
              className={`min-h-12 cursor-pointer rounded-xl border-2 px-3 font-en font-bold ${
                matched.includes(i) ? 'border-success bg-success-soft text-success-text' : left === i ? 'border-maroon bg-maroon-soft text-maroon-text' : 'border-line bg-white text-ink'
              }`}
            >
              {p.left}
            </button>
          ))}
        </div>
        <div className="flex flex-col gap-2">
          {rights.map((i) => {
            const r = pick(pairs[i].right, lang === 'en' ? 'msa' : lang)
            return (
              <button
                key={i}
                type="button"
                disabled={matched.includes(i) || done}
                onClick={() => pickRight(i)}
                lang={r.lang}
                className={`min-h-12 cursor-pointer rounded-xl border-2 px-3 font-bold ${matched.includes(i) ? 'border-success bg-success-soft text-success-text' : 'border-line bg-white text-ink'}`}
              >
                {r.text}
              </button>
            )
          })}
        </div>
      </div>
    </>
  )
}

function OrderView({ ex, lang, seed, done, onCheck }: { ex: Exercise; lang: ExplainLang; seed: string; done: boolean; onCheck: (ok: boolean) => void }) {
  const { t } = useI18n()
  const prompt = pick(ex.prompt as Texts, lang)
  const items = ex.items as Texts[]
  const [order, setOrder] = useState(() => {
    const s = seededShuffle(items.map((_, i) => i), seed)
    return s.every((v, i) => v === i) ? [...s].reverse() : s
  })
  const move = (pos: number, by: number) => {
    const o = order.slice()
    ;[o[pos], o[pos + by]] = [o[pos + by], o[pos]]
    setOrder(o)
  }
  return (
    <>
      <p className="m-0 font-bold" lang={prompt.lang}>
        {prompt.text}
      </p>
      <ol className="m-0 flex list-none flex-col gap-2 p-0">
        {order.map((i, pos) => {
          const text = pick(items[i], lang)
          return (
            <li key={i} className="flex items-center gap-2 rounded-xl border-2 border-line bg-white p-2">
              <span className="w-6 text-center font-bold text-muted">{pos + 1}</span>
              <span className="flex-1" lang={text.lang} dir={text.lang === 'en' ? 'ltr' : undefined}>
                {text.text}
              </span>
              <button type="button" disabled={done || pos === 0} onClick={() => move(pos, -1)} aria-label={`${t('lesson.order.up')}: ${text.text}`} className="flex size-11 cursor-pointer items-center justify-center rounded-lg border border-line bg-surface-2 text-ink-2 disabled:opacity-40">
                <ArrowUp aria-hidden="true" size={18} />
              </button>
              <button type="button" disabled={done || pos === order.length - 1} onClick={() => move(pos, 1)} aria-label={`${t('lesson.order.down')}: ${text.text}`} className="flex size-11 cursor-pointer items-center justify-center rounded-lg border border-line bg-surface-2 text-ink-2 disabled:opacity-40">
                <ArrowDown aria-hidden="true" size={18} />
              </button>
            </li>
          )
        })}
      </ol>
      {!done && (
        <div>
          <button type="button" onClick={() => onCheck(order.every((v, i) => v === i))} className="min-h-11 cursor-pointer rounded-xl border-2 border-maroon bg-white px-5 font-bold text-maroon">
            {t('lesson.check')}
          </button>
        </div>
      )}
    </>
  )
}

function TermDialog({ id, lang, onClose }: { id: string | null; lang: ExplainLang; onClose: () => void }) {
  const { t } = useI18n()
  const ref = useRef<HTMLDialogElement>(null)
  const [card, setCard] = useState<Card | null>(null)
  const [quick, setQuick] = useState<{ en: string; ar: string } | null>(null)

  useEffect(() => {
    const d = ref.current
    if (!d) return
    if (id) {
      setCard(null)
      setQuick(null)
      if (!d.open) d.showModal?.()
      fetch(`/api/glossary/term/${id}?lang=${lang}`)
        .then((r) => r.json())
        .then((j) => {
          setCard(j.full)
          setQuick(j.quick ? { en: j.quick.en, ar: j.quick.ar } : null)
        })
        .catch(() => {})
    } else if (d.open) {
      d.close()
    }
  }, [id, lang])

  return (
    <dialog ref={ref} onClose={onClose} onClick={(e) => e.target === ref.current && onClose()} aria-label={card?.term_en ?? quick?.en ?? t('lesson.termLoading')} className="m-auto w-[min(520px,calc(100vw-32px))] rounded-3xl border border-line bg-surface p-0 text-ink shadow-card backdrop:bg-ink/40">
      <div className="flex flex-col gap-3 p-5 sm:p-6">
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <p className="m-0 font-display text-2xl font-semibold text-maroon">{card?.term_ar ?? quick?.ar ?? t('lesson.termLoading')}</p>
            <span dir="ltr" lang="en" className="font-en font-semibold text-ink-2">
              {card?.term_en ?? quick?.en}
            </span>
          </div>
          <button type="button" onClick={onClose} aria-label={t('glossary.close')} className="flex size-11 cursor-pointer items-center justify-center rounded-xl border border-line bg-white text-ink-2">
            <X aria-hidden="true" size={20} />
          </button>
        </div>
        {card && <p className="m-0 text-[17px]">{card.explanation}</p>}
        {card?.analogy && <div className="rounded-[14px] bg-surface-3 px-4 py-3 text-ink-2">{card.analogy}</div>}
      </div>
    </dialog>
  )
}
