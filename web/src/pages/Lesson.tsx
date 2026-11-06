import type React from 'react'
import { ArrowDown, ArrowLeft, ArrowRight, ArrowUp, BookOpen, Check, Clock, Dumbbell, Flame, Layers, Lightbulb, MessageSquare, Pencil, Star, Target, Trophy, X, type LucideIcon } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Segmented } from '../components/Segmented'
import { useI18n, type MessageKey } from '../i18n'
import { ApiError, listLessons, type Card, type LessonSummary } from '../lib/api'
import { useExplainLang, type ExplainLang } from '../lib/explainLang'
import { completeLesson, getPlace, LESSON_XP, savePlace } from '../lib/lessonProgress'
import { buildSteps, pick, seededShuffle, segments, termSlug, withRetries, type Step, type Texts } from '../lib/lessonSteps'
import { award, useProgress } from '../lib/progress'
import { Link, useRouter } from '../lib/router'
import { PromptLab } from './Tutor'

type Exercise = Record<string, unknown> & { type: 'mcq' | 'match' | 'fill' | 'order'; explanation?: Texts }
type Block = { type: string; en?: string; ar?: string; gulf?: string; terms?: string[]; exercises?: Exercise[] }
type Lesson = { slug: string; order: number; est_minutes?: number; title: Texts; blocks: Block[] }

const BLOCK_TITLE: Record<string, MessageKey> = {
  hook: 'lesson.hook',
  concept: 'lesson.concept',
  example: 'lesson.example',
  key_terms: 'lesson.keyTerms',
  prompt_lab: 'lesson.promptLab',
  recap: 'lesson.recap',
}
const BLOCK_ICON: Record<string, LucideIcon> = {
  hook: Target,
  concept: Lightbulb,
  example: MessageSquare,
  key_terms: BookOpen,
  exercise: Dumbbell,
  prompt_lab: Pencil,
  recap: Layers,
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
  // The furthest step reached: going back never locks a step the learner already passed.
  const [reached, setReached] = useState(0)
  const [finished, setFinished] = useState<number | null>(null)
  const [termOpen, setTermOpen] = useState<string | null>(null)
  const top = useRef<HTMLHeadingElement>(null)
  const [all, setAll] = useState<LessonSummary[]>([])
  const { streak } = useProgress()

  useEffect(() => {
    listLessons().then(setAll).catch(() => {})
  }, [])

  useEffect(() => {
    fetch(`/api/lessons/${slug}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new ApiError(r.status))))
      .then((d: Lesson) => {
        const built = buildSteps(d.blocks)
        setLesson(d)
        setSteps(built)
        // Pick up where the learner left off.
        const place = getPlace(d.slug)
        if (place) {
          setAt(Math.min(place.at, built.length - 1))
          setReached(Math.min(place.reached, built.length - 1))
        }
      })
      .catch(() => setMissing(true))
  }, [slug])

  useEffect(() => {
    if (lesson && finished === null) savePlace(lesson.slug, { at, reached })
  }, [lesson, at, reached, finished])

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
  const canNext = !isExercise || answered || at < reached
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
    setReached((r) => Math.max(r, target))
    setAnswered(false)
  }

  const jumpTo = (target: number) => {
    if (target > reached || target === at) return
    setAt(target)
    setAnswered(false)
  }

  const back = () => {
    if (at === 0) return
    setAt(at - 1)
    setAnswered(false)
  }

  const onResult = (firstTry: boolean, correct: boolean) => {
    setAnswered(true)
    if (step.kind !== 'exercise') return
    if (correct && firstTry && !step.retry) award(`ex:${lesson.slug}:${step.block}:${step.index}`, EXERCISE_XP)
    if (!correct && !step.retry) setMissed((m) => (m.some((x) => x.kind === 'exercise' && x.block === step.block && x.index === step.index) ? m : [...m, step]))
  }

  const langOptions: { value: ExplainLang; label: string; lang: string }[] = [
    { value: 'en', label: t('lang.en'), lang: 'en' },
    { value: 'msa', label: t('lang.msa'), lang: 'ar' },
    { value: 'gulf', label: t('lang.gulf'), lang: 'ar' },
  ]

  const nextLesson = all.find((l) => l.order === lesson.order + 1)
  const termCount = lesson.blocks.find((b) => b.type === 'key_terms')?.terms?.length ?? 0
  const shownStep = Math.min(at + 1, steps.length)
  const blockType = isExercise ? 'exercise' : lesson.blocks[step.block].type
  const Icon = BLOCK_ICON[blockType] ?? Lightbulb
  // The rail lists the lesson's blocks; all exercises in a block are one row.
  const rail = lesson.blocks.map((b, i) => ({ i, type: b.type, first: steps.findIndex((s) => s.block === i) }))
  const currentBlock = finished !== null ? lesson.blocks.length : step.block
  const railList = (
    <ol className="m-0 flex list-none flex-col gap-1.5 p-0">
      {rail.map(({ i, type, first }, n) => {
        const state = i === currentBlock ? 'current' : first <= reached || finished !== null ? 'done' : 'next'
        const name = t(type === 'exercise' ? 'lesson.exercises' : (BLOCK_TITLE[type] ?? 'lesson.concept'))
        const look = `flex min-h-11 w-full items-center gap-3 rounded-2xl border-0 px-2.5 text-start font-[inherit] text-[length:inherit] ${
          state === 'current' ? 'bg-maroon-soft font-bold text-maroon-text' : 'bg-transparent text-ink-2'
        }`
        const body = (
          <>
            <span
              className={`flex size-8 shrink-0 items-center justify-center rounded-lg font-en text-sm font-bold ${
                state === 'done' ? 'bg-success text-white' : state === 'current' ? 'bg-maroon text-white' : 'bg-surface-3 text-ink-2'
              }`}
            >
              {state === 'done' ? <Check aria-hidden="true" size={16} strokeWidth={3} /> : n + 1}
            </span>
            {name}
            {state === 'done' && <span className="sr-only">({t('path.done')})</span>}
          </>
        )
        return (
          <li key={i} aria-current={state === 'current' ? 'step' : undefined}>
            {state === 'done' && finished === null ? (
              <button type="button" onClick={() => jumpTo(first)} className={`${look} cursor-pointer hover:bg-white/60`}>
                {body}
              </button>
            ) : (
              <span className={look}>{body}</span>
            )}
          </li>
        )
      })}
    </ol>
  )

  return (
    <div className="mx-auto flex max-w-[1100px] flex-col gap-5">
      <div className="glass flex flex-wrap items-center gap-x-5 gap-y-3 px-4 py-3">
        <Link
          href="/"
          aria-label={t('lesson.exit')}
          className="flex size-11 shrink-0 items-center justify-center rounded-full border border-white/80 bg-white/80 text-ink-2 no-underline hover:text-ink"
        >
          <X aria-hidden="true" size={20} />
        </Link>
        <div className="min-w-0 flex-[1_1_200px]">
          {all.length > 0 && <p className="m-0 text-[13px] font-bold text-maroon">{t('lesson.of', { k: lesson.order, n: all.length })}</p>}
          <p className="m-0 font-display text-lg leading-snug font-semibold" lang={title.lang} dir={title.lang === 'en' ? 'ltr' : 'rtl'}>
            {title.text}
          </p>
        </div>
        <div className="flex min-w-0 flex-[2_1_220px] items-center gap-3">
          <div
            role="progressbar"
            aria-valuemin={1}
            aria-valuemax={steps.length}
            aria-valuenow={shownStep}
            aria-label={t('lesson.progress', { k: shownStep, n: steps.length })}
            className="h-3 flex-1 overflow-hidden rounded-full bg-surface-3"
          >
            <div className="h-full rounded-full bg-maroon transition-[width] duration-300" style={{ width: `${((finished !== null ? steps.length : at + 1) / steps.length) * 100}%` }} />
          </div>
          <span className="text-sm whitespace-nowrap text-ink-2">{t('lesson.progress', { k: shownStep, n: steps.length })}</span>
        </div>
        {lesson.est_minutes && (
          <span className="hidden items-center gap-1.5 rounded-full bg-white/80 px-3 py-1.5 text-sm font-bold sm:flex">
            <Clock aria-hidden="true" size={15} />
            {t('lesson.minutes', { m: lesson.est_minutes })}
          </span>
        )}
        <Segmented label={t('home.explainLanguage')} options={langOptions} value={lang} onChange={setLang} />
      </div>

      <div className="flex flex-wrap items-start gap-5 sm:gap-7">
        <nav aria-labelledby="rail-h" className="card hidden min-w-0 flex-[1_1_240px] lg:block">
          <h2 id="rail-h" className="m-0 mb-3 flex items-center gap-2 font-display text-xl font-semibold">
            <Layers aria-hidden="true" size={19} className="text-maroon" />
            {t('lesson.stepsTitle')}
          </h2>
          {railList}
        </nav>

        <div className="flex min-w-0 flex-[999_1_480px] flex-col gap-5">
          <details className="glass px-4 py-2 lg:hidden">
            <summary className="flex min-h-11 cursor-pointer items-center gap-2 font-bold">
              <Layers aria-hidden="true" size={18} className="text-maroon" />
              {t('lesson.stepsTitle')}
            </summary>
            <div className="pb-2">{railList}</div>
          </details>
          {finished !== null ? (
            <section className="card card-enter flex flex-col items-center gap-5 text-center">
              <span className="flex size-24 items-center justify-center rounded-[28px] bg-gold text-white shadow-[0_6px_0_var(--gold-text)]">
                <Trophy aria-hidden="true" size={46} />
              </span>
              <div>
                <h1 ref={top} tabIndex={-1} className="m-0 font-display text-[30px] leading-tight font-semibold outline-none sm:text-[38px]">
                  {t('lesson.doneTitle')}
                </h1>
                <p className="m-0 mt-1 text-ink-2" lang={title.lang}>
                  {title.text}
                </p>
              </div>
              <ul className="m-0 grid w-full list-none grid-cols-1 gap-3 p-0 min-[420px]:grid-cols-3">
                {[
                  { Icon: Star, tone: 'bg-gold', value: `+${finished || LESSON_XP}`, label: t('lesson.statPoints') },
                  { Icon: Flame, tone: 'bg-flame', value: String(streak), label: t('lesson.statStreak') },
                  { Icon: BookOpen, tone: 'bg-teal', value: String(termCount), label: t('lesson.statTerms') },
                ].map(({ Icon: I, tone, value, label }, n) => (
                  <li key={label} className="well card-enter flex flex-col items-center gap-1.5 p-4" style={{ '--i': n + 1 } as React.CSSProperties}>
                    <span className={`flex size-11 items-center justify-center rounded-xl text-white ${tone}`}>
                      <I aria-hidden="true" size={20} />
                    </span>
                    <span className="font-en text-2xl font-bold">{value}</span>
                    <span className="text-sm text-ink-2">{label}</span>
                  </li>
                ))}
              </ul>
              <div className="flex flex-wrap justify-center gap-3">
                {nextLesson && (
                  <button type="button" className="btn-primary flex items-center gap-2" onClick={() => navigate(`/lesson/${nextLesson.slug}`)}>
                    {t('lesson.nextLesson')}
                    <ArrowRight aria-hidden="true" size={20} className="rtl:-scale-x-100" />
                  </button>
                )}
                <button
                  type="button"
                  className="min-h-12 cursor-pointer rounded-2xl border border-white/80 bg-white/80 px-5 font-bold text-ink shadow-[0_4px_0_var(--shadow)]"
                  onClick={() => navigate('/')}
                >
                  {t('lesson.backHome')}
                </button>
              </div>
            </section>
          ) : (
            <section key={at} className="card card-enter flex flex-col gap-4" aria-live="polite">
              <p className="m-0 flex items-center gap-1.5 text-sm font-bold text-maroon">
                <Icon aria-hidden="true" size={16} />
                {t('lesson.progress', { k: shownStep, n: steps.length })}
              </p>
              <h1 ref={top} tabIndex={-1} className="m-0 -mt-2 font-display text-[24px] font-semibold outline-none">
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
              <div className="flex flex-wrap items-center justify-between gap-3">
                {at > 0 ? (
                  <button
                    type="button"
                    onClick={back}
                    className="flex min-h-12 cursor-pointer items-center gap-2 rounded-2xl border border-white/80 bg-white/80 px-5 font-bold text-ink shadow-[0_4px_0_var(--shadow)]"
                  >
                    <ArrowLeft aria-hidden="true" size={20} className="rtl:-scale-x-100" />
                    {t('lesson.back')}
                  </button>
                ) : (
                  <span />
                )}
                <button type="button" className="btn-primary flex items-center gap-2" disabled={!canNext} onClick={next}>
                  {at === steps.length - 1 ? t('lesson.finish') : t('lesson.next')}
                  <ArrowRight aria-hidden="true" size={20} className="rtl:-scale-x-100" />
                </button>
              </div>
            </section>
          )}
        </div>
      </div>
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
            className="inline cursor-pointer rounded-t-md border-0 border-b-2 border-solid border-maroon bg-maroon-soft px-1 font-[inherit] text-[inherit] font-bold text-maroon-text"
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

export function ExerciseView({ ex, lang, seed, onResult }: { ex: Exercise; lang: ExplainLang; seed: string; onResult: (firstTry: boolean, correct: boolean) => void }) {
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
  // Word order items are plain words in the exercise's language; sentence order items are {en, ar, gulf}.
  const items = ex.items as (string | Texts)[]
  const label = (it: string | Texts) => (typeof it === 'string' ? { text: it, lang: (ex.lang as 'en' | 'ar') ?? 'en' } : pick(it, lang))
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
          const text = label(items[i])
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
