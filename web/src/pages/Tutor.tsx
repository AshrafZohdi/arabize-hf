import { AlertTriangle, ArrowRight, BookOpen, Image as ImageIcon, Check, Copy, Hourglass, Layers, Lightbulb, Loader2, MessageCircle, Pencil, Send, Target, Trophy } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { PageTitle } from '../components/PageTitle'
import { Segmented } from '../components/Segmented'
import { useI18n, type MessageKey } from '../i18n'
import { LogoMark } from '../components/Logo'
import { MicButton } from '../components/MicButton'
import { PhotoButton } from '../components/PhotoButton'
import { Translatable } from '../components/Translate'
import { HighlightedText } from '../components/explain/HighlightedText'
import { ApiError, findTerms, glossaryCards, listLessons, promptLabTask, scorePrompt, streamTutor, type ChatTurn, type LessonSummary, type PromptScores, type TermMatch } from '../lib/api'
import { useExplainLang, type ExplainLang } from '../lib/explainLang'
import { Link } from '../lib/router'
import { imageFeatures } from '../lib/image'
import { tutorSession } from '../lib/session'

type Tab = 'chat' | 'lab' | 'image'

export function TutorPage() {
  const { t, lang: uiLang } = useI18n()
  const [lang, setLang] = useExplainLang()
  const params = new URLSearchParams(window.location.search)
  const asked = params.get('tab')
  const [tab, setTab] = useState<Tab>(asked === 'lab' || asked === 'image' ? asked : 'chat')
  // The image tab appears only when the Space has image generation switched on.
  const [drawOn, setDrawOn] = useState(false)
  useEffect(() => {
    imageFeatures().then((f) => setDrawOn(f.generate))
  }, [])
  const [lessons, setLessons] = useState<LessonSummary[]>([])
  const [lesson, setLesson] = useState<string>(params.get('lesson') ?? 'day-2')

  useEffect(() => {
    listLessons().then(setLessons).catch(() => {})
  }, [])

  const title = (l: LessonSummary) => (uiLang === 'en' ? l.title.en : lang === 'gulf' ? l.title.gulf || l.title.ar : l.title.ar)
  const langOptions: { value: ExplainLang; label: string; lang: string }[] = [
    { value: 'en', label: t('lang.en'), lang: 'en' },
    { value: 'msa', label: t('lang.msa'), lang: 'ar' },
    { value: 'gulf', label: t('lang.gulf'), lang: 'ar' },
  ]

  return (
    <>
      <PageTitle title={t('tutor.title')} subtitle={t('tutor.subtitle')} aside={<Segmented label={t('home.explainLanguage')} options={langOptions} value={lang} onChange={setLang} />} />
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <Segmented
          label={t('tutor.tabsLabel')}
          options={[
            { value: 'chat' as Tab, label: t('tutor.tabChat') },
            { value: 'lab' as Tab, label: t('tutor.tabLab') },
            ...(drawOn ? [{ value: 'image' as Tab, label: t('tutor.tabImage') }] : []),
          ]}
          value={tab}
          onChange={setTab}
        />
        <label className={`w-full max-w-[420px] min-w-0 flex-col gap-1 font-semibold text-ink-2 sm:w-auto ${tab === 'image' ? 'hidden' : 'flex'}`}>
          {t('tutor.lessonLabel')}
          <select
            value={lesson}
            onChange={(e) => setLesson(e.target.value)}
            className="min-h-11 w-full min-w-0 rounded-full border border-white/80 bg-white/80 px-4 font-semibold text-ink shadow-[0_3px_0_var(--shadow)]"
          >
            {tab === 'chat' && <option value="">{t('tutor.noLesson')}</option>}
            {lessons.map((l) => (
              <option key={l.slug} value={l.slug}>
                {l.order}. {title(l)}
              </option>
            ))}
          </select>
        </label>
      </div>
      {tab === 'chat' ? (
        <Chat lang={lang} lesson={lesson || null} />
      ) : tab === 'image' && drawOn ? (
        <ImageLab lang={lang} />
      ) : (
        <PromptLab lang={lang} lesson={lesson || 'day-2'} />
      )}
    </>
  )
}

type LessonTerm = { en: string; ar: string }

/** The lesson's key terms with their Arabic from the Darby cards. */
function useLessonTerms(lesson: string | null, lang: ExplainLang): LessonTerm[] {
  const [terms, setTerms] = useState<LessonTerm[]>([])
  useEffect(() => {
    if (!lesson) {
      setTerms([])
      return
    }
    let live = true
    Promise.all([fetch(`/api/lessons/${lesson}`).then((r) => (r.ok ? r.json() : null)), glossaryCards(lang).catch(() => [])])
      .then(([l, cards]) => {
        if (!live || !l) return
        const ar = new Map(cards.map((c) => [c.term_en.toLowerCase(), c.term_ar]))
        const en: string[] = (l.blocks as { type: string; terms?: string[] }[]).find((b) => b.type === 'key_terms')?.terms ?? []
        setTerms(en.map((e) => ({ en: e, ar: ar.get(e.toLowerCase()) ?? '' })))
      })
      .catch(() => {})
    return () => {
      live = false
    }
  }, [lesson, lang])
  return terms
}

function Chat({ lang, lesson }: { lang: ExplainLang; lesson: string | null }) {
  const { t } = useI18n()
  const terms = useLessonTerms(lesson, lang)
  const name = (x: LessonTerm) => (lang === 'en' || !x.ar ? x.en : x.ar)
  const suggestions =
    terms.length >= 2
      ? [t('tutor.suggestWhat', { a: name(terms[0]) }), t('tutor.suggestDiff', { a: name(terms[0]), b: name(terms[1]) }), t('tutor.suggestExample', { a: name(terms[terms.length - 1]) })]
      : []
  const [turns, setTurns] = useState<ChatTurn[]>([])
  // A question handed over from another page ("Ask the tutor" on a term card) arrives as ?q= and waits for Send.
  const [input, setInput] = useState(() => new URLSearchParams(window.location.search).get('q')?.slice(0, 500) ?? '')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<MessageKey | null>(null)
  const [left, setLeft] = useState<number | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Braces matter: Chrome 155 returns a Promise from scrollIntoView, and React would call it as a cleanup.
    endRef.current?.scrollIntoView?.({ block: 'nearest' })
  }, [turns])

  const send = async (asked?: string) => {
    const text = (asked ?? input).trim()
    if (!text || busy) return
    const history: ChatTurn[] = [...turns, { role: 'user', content: text }]
    setTurns([...history, { role: 'assistant', content: '' }])
    setInput('')
    setBusy(true)
    setNotice(null)
    try {
      const end = await streamTutor({ messages: history, lang, lesson, session: tutorSession() }, (piece) =>
        setTurns((ts) => {
          const copy = ts.slice()
          copy[copy.length - 1] = { role: 'assistant', content: copy[copy.length - 1].content + piece }
          return copy
        }),
      )
      if (end.messagesLeft !== undefined) setLeft(end.messagesLeft)
      if (!end.done) {
        setNotice(end.state === 'waking' ? 'tutor.waking' : 'tutor.offline')
        setTurns(history.slice(0, -1))
        setInput(text)
      }
    } catch (e) {
      setNotice(e instanceof ApiError && e.status === 429 ? 'tutor.limit' : 'tutor.offline')
      setTurns(history.slice(0, -1))
      setInput(text)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-wrap items-start gap-5 sm:gap-7">
      <section aria-label={t('tutor.tabChat')} className="card flex min-w-0 flex-[999_1_560px] flex-col gap-4">
        <div role="log" aria-live="polite" aria-busy={busy} className="flex min-h-48 flex-col gap-4">
          {turns.length === 0 && <p className="m-0 text-ink-2">{t('tutor.empty')}</p>}
          {turns.map((m, i) =>
            m.role === 'user' ? (
              <div key={i} className="flex max-w-[88%] items-start gap-2.5 self-start">
                <span aria-hidden="true" className="hidden size-10 shrink-0 items-center justify-center rounded-xl bg-ink text-sm font-bold text-white sm:flex">
                  {t('tutor.you')}
                </span>
                <div className="rounded-2xl rounded-ss-md bg-maroon px-4 py-3 text-white shadow-[0_4px_0_var(--maroon-deep)]">
                  <span className="mb-0.5 block text-xs font-bold opacity-80">{t('tutor.you')}</span>
                  <p dir="auto" className="m-0 text-[17px] whitespace-pre-wrap">
                    {m.content}
                  </p>
                </div>
              </div>
            ) : (
              <div key={i} className="flex max-w-[92%] items-start gap-2.5 self-end">
                <div className="order-1 rounded-2xl rounded-se-md border border-white/80 bg-white/85 px-4 py-3 text-ink shadow-[0_4px_0_var(--shadow)]">
                  <span className="mb-0.5 block text-xs font-bold text-muted">{t('tutor.darby')}</span>
                  {busy && i === turns.length - 1 ? (
                    <p dir="auto" className="m-0 text-[17px] whitespace-pre-wrap">
                      {m.content}
                      <span aria-hidden="true" className="ms-1 inline-block h-4 w-1.5 animate-pulse bg-maroon align-middle" />
                    </p>
                  ) : (
                    <Translatable text={m.content} lang={lang} className="text-[17px]" />
                  )}
                </div>
                {/* Avatars only from 640 px: on a phone they took a third of the bubble width. */}
                <span aria-hidden="true" className="order-2 hidden shrink-0 sm:block">
                  <LogoMark />
                </span>
              </div>
            ),
          )}
          <div ref={endRef} />
        </div>
        {notice && (
          <p role="status" className="m-0 flex items-center gap-2 rounded-2xl bg-surface-3 p-3 text-ink-2">
            {notice === 'tutor.waking' ? <Hourglass aria-hidden="true" size={18} /> : <AlertTriangle aria-hidden="true" size={18} />}
            {t(notice)}
          </p>
        )}
        <form
          className="flex items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault()
            send()
          }}
        >
          <label htmlFor="tutor-input" className="sr-only">
            {t('tutor.placeholder')}
          </label>
          <textarea
            id="tutor-input"
            dir="auto"
            rows={1}
            value={input}
            maxLength={2000}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                send()
              }
            }}
            placeholder={t('tutor.placeholder')}
            className="min-h-14 min-w-0 flex-1 resize-y rounded-[20px] border-2 border-line bg-white/80 px-4 py-3.5 text-[17px] text-ink placeholder:text-muted focus:border-maroon"
          />
          <button type="submit" aria-label={t('tutor.send')} className="btn-primary flex size-14 items-center justify-center p-0!" disabled={busy || !input.trim() || left === 0}>
            {busy ? <Loader2 aria-hidden="true" size={22} className="animate-spin" /> : <Send aria-hidden="true" size={22} className="rtl:-scale-x-100" />}
          </button>
        </form>
        <div className="flex flex-wrap items-center gap-2">
          <MicButton onText={(said) => setInput((v) => `${v} ${said}`.trim())} />
          <PhotoButton lang={lang} onText={(text) => setInput(`${t('tutor.photoAsk')}\n"${text}"`.slice(0, 2000))} />
        </div>
        <p className="m-0 flex flex-wrap justify-between gap-2 text-[13px] text-ink-2">
          <span>{t('tutor.privacy')}</span>
          {left !== null && <span>{t('tutor.messagesLeft', { n: left })}</span>}
        </p>
      </section>

      {terms.length > 0 && (
        <aside className="flex min-w-0 flex-[1_1_300px] flex-col gap-5 sm:gap-7">
          {suggestions.length > 0 && (
            <section aria-labelledby="suggest-h" className="card">
              <h2 id="suggest-h" className="m-0 mb-3 flex items-center gap-2 font-display text-[22px] font-semibold">
                <Lightbulb aria-hidden="true" size={20} className="text-maroon" />
                {t('tutor.suggestTitle')}
              </h2>
              <ul className="m-0 flex list-none flex-col gap-2 p-0">
                {suggestions.map((q) => (
                  <li key={q}>
                    <button
                      type="button"
                      onClick={() => send(q)}
                      disabled={busy || left === 0}
                      className="lift flex min-h-11 w-full cursor-pointer items-center gap-2 rounded-2xl border-0 bg-teal-soft px-4 py-2.5 text-start font-semibold text-teal-text disabled:cursor-default disabled:opacity-60"
                    >
                      <MessageCircle aria-hidden="true" size={16} className="shrink-0" />
                      <span dir="auto">{q}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}
          <section aria-labelledby="lterms-h" className="card">
            <h2 id="lterms-h" className="m-0 mb-3 flex items-center gap-2 font-display text-[22px] font-semibold">
              <BookOpen aria-hidden="true" size={20} className="text-maroon" />
              {t('tutor.lessonTerms')}
            </h2>
            <ul className="m-0 flex list-none flex-col gap-2 p-0">
              {terms.map((x) => (
                <li key={x.en}>
                  <Link
                    href={`/glossary?q=${encodeURIComponent(x.en)}`}
                    className="well lift flex min-h-11 items-center justify-between gap-3 px-4 py-2 text-ink no-underline hover:text-ink"
                  >
                    <bdi lang="en" className="font-en font-bold">
                      {x.en}
                    </bdi>
                    {x.ar && <span lang="ar">{x.ar}</span>}
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        </aside>
      )}
    </div>
  )
}

const CRITERIA = ['goal', 'context', 'format', 'constraints'] as const

export function PromptLab({ lang, lesson }: { lang: ExplainLang; lesson: string }) {
  const { t } = useI18n()
  const [task, setTask] = useState('')
  const [taskEn, setTaskEn] = useState('')
  const [taskTerms, setTaskTerms] = useState<TermMatch[]>([])
  const [prompt, setPrompt] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<PromptScores | null>(null)
  const [error, setError] = useState<MessageKey | null>(null)

  // A new lesson is a new task, so the old score goes; switching the language only re-labels the task.
  useEffect(() => {
    setResult(null)
  }, [lesson])

  useEffect(() => {
    promptLabTask(lesson, lang)
      .then((r) => setTask(r.task))
      .catch(() => setTask(''))
  }, [lesson, lang])

  // The English task sits under the Arabic one, with its key terms highlighted, so the learner can link the two.
  useEffect(() => {
    const ctrl = new AbortController()
    promptLabTask(lesson, 'en')
      .then((r) => {
        setTaskEn(r.task)
        return findTerms(r.task, ctrl.signal)
      })
      .then(setTaskTerms)
      .catch(() => {})
    return () => ctrl.abort()
  }, [lesson])

  const score = async () => {
    if (!prompt.trim()) return
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      setResult(await scorePrompt(lesson, prompt, lang))
    } catch (e) {
      setError(e instanceof ApiError && e.status === 503 ? 'lab.unavailable' : e instanceof ApiError && e.status === 429 ? 'tutor.limit' : 'lab.failed')
    } finally {
      setBusy(false)
    }
  }


  return (
    <section aria-labelledby="lab-h" className="card flex flex-col gap-4">
      <h2 id="lab-h" className="m-0 flex items-center gap-2 font-display text-[22px] font-semibold text-maroon">
        <Pencil aria-hidden="true" size={20} />
        {t('lab.title')}
      </h2>
      <div className="well p-4">
        <h3 className="m-0 mb-1 flex items-center gap-1.5 text-sm font-bold text-maroon">
          <Target aria-hidden="true" size={16} />
          {t('lab.task')}
        </h3>
        <p className="m-0 text-[17px]" dir="auto">
          {task}
        </p>
        {taskEn && (
          <p dir="ltr" lang="en" className={`m-0 font-en text-[15px] leading-[1.9] text-ink-2 ${lang === 'en' ? 'hidden' : 'mt-2 border-t border-line pt-2'}`}>
            <HighlightedText text={taskEn} matches={taskTerms} isKnown={() => false} knownLabel="" newLabel={t('explain.legendNew')} />
          </p>
        )}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label htmlFor="lab-input" className="font-semibold text-ink-2">
          {t('lab.yourPrompt')}
        </label>
        <MicButton onText={(said) => setPrompt((v) => `${v} ${said}`.trim())} />
      </div>
      <textarea
        id="lab-input"
        dir="auto"
        rows={5}
        maxLength={2000}
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder={t('lab.placeholder')}
        className="min-h-32 w-full resize-y rounded-[20px] border-2 border-line bg-white/80 p-4 text-[17px] text-ink placeholder:text-muted focus:border-maroon"
      />
      <div>
        <button type="button" className="btn-primary" onClick={score} disabled={busy || !prompt.trim()}>
          {busy ? (
            <span className="flex items-center gap-2">
              <Loader2 aria-hidden="true" size={20} className="animate-spin" />
              {t('lab.working')}
            </span>
          ) : (
            <span className="flex items-center gap-2">
              {t('lab.submit')}
              <ArrowRight aria-hidden="true" size={20} className="rtl:-scale-x-100" />
            </span>
          )}
        </button>
      </div>
      {error && (
        <p role="alert" className="m-0 flex items-center gap-2 rounded-2xl bg-maroon-soft p-3 font-semibold text-maroon-text">
          <AlertTriangle aria-hidden="true" size={18} />
          {t(error)}
        </p>
      )}
      {result && <ScoreView result={result} lang={lang} criterion="lab.criterion" />}
    </section>
  )
}

/** A prompt's score: the ring out of 20, five segments per criterion, the summary and the improved prompt. */
export function ScoreView({ result, lang, criterion, footer }: { result: PromptScores; lang: ExplainLang; criterion: 'lab.criterion' | 'image.criterion'; footer?: React.ReactNode }) {
  const { t } = useI18n()
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(result.improved_prompt)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard can be blocked; the text stays selectable.
    }
  }
  return (
    <div className="flex flex-col gap-4" aria-live="polite">
      <div className="flex flex-wrap items-center gap-5">
        <ScoreRing total={result.total} label={t('lab.total', { n: result.total })} outOf={t('lab.outOf')} />
        <div className="min-w-0 flex-1">
          <h3 className="m-0 flex items-center gap-2 font-display text-xl font-semibold">
            <Trophy aria-hidden="true" size={19} className="text-maroon" />
            {t('lab.scoreTitle')}
          </h3>
          <p className="m-0 mt-1 text-[17px] text-ink-2" dir="auto">
            {result.summary}
          </p>
        </div>
      </div>
      <ul className="m-0 grid list-none grid-cols-1 gap-4 p-0 sm:grid-cols-2">
        {CRITERIA.map((c) => {
          const s = result.scores[c]
          const tone = s.score >= 4 ? 'bg-success' : s.score >= 3 ? 'bg-gold' : 'bg-maroon'
          return (
            <li key={c} className="well p-4">
              <div className="flex items-center justify-between gap-2">
                <span className="font-bold">{t(`${criterion}.${c}` as MessageKey)}</span>
                <span className="font-en font-bold">{t('lab.scoreOf', { n: s.score })}</span>
              </div>
              <div className="mt-2 grid grid-cols-5 gap-1.5" aria-hidden="true">
                {[1, 2, 3, 4, 5].map((n) => (
                  <span key={n} className={`h-2.5 rounded-full ${n <= s.score ? tone : 'bg-surface-3'}`} />
                ))}
              </div>
              <p className="mt-2 mb-0 text-[15px] text-ink-2" dir="auto">
                {s.feedback}
              </p>
            </li>
          )
        })}
      </ul>
      <div className="rounded-2xl border border-success bg-success-soft p-4">
        <div className="mb-2 flex items-center justify-between gap-2">
          <h3 className="m-0 flex items-center gap-1.5 text-base font-bold text-success-text">
            <Layers aria-hidden="true" size={17} />
            {t('lab.improved')}
          </h3>
          <button type="button" onClick={copy} className="flex min-h-11 cursor-pointer items-center gap-1.5 rounded-xl border border-success bg-white px-3 font-bold text-success-text">
            {copied ? <Check aria-hidden="true" size={16} /> : <Copy aria-hidden="true" size={16} />}
            {copied ? t('lab.copied') : t('lab.copy')}
          </button>
        </div>
        <Translatable text={result.improved_prompt} lang={lang} className="text-[17px]" />
        {footer}
      </div>
    </div>
  )
}

/** The prompt score out of 20 as a ring; the number is the label. */
function ScoreRing({ total, label, outOf }: { total: number; label: string; outOf: string }) {
  const r = 40
  const c = 2 * Math.PI * r
  return (
    <div role="img" aria-label={label} className="relative size-28 shrink-0">
      <svg viewBox="0 0 100 100" className="size-full -rotate-90 rtl:scale-y-[-1]" aria-hidden="true">
        <circle cx="50" cy="50" r={r} fill="var(--white)" stroke="var(--surface-3)" strokeWidth="10" />
        <circle cx="50" cy="50" r={r} fill="none" stroke="var(--maroon)" strokeWidth="10" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - total / 20)} />
      </svg>
      <span aria-hidden="true" className="absolute inset-0 flex flex-col items-center justify-center leading-none">
        <span className="font-en text-3xl font-bold">{total}</span>
        <span className="mt-1 text-xs text-ink-2">{outOf}</span>
      </span>
    </div>
  )
}

/** Image prompts: Fanar scores the learner's image prompt and writes a better one in English; Fanar-2-Oryx-IG draws it. */
function ImageLab({ lang }: { lang: ExplainLang }) {
  const { t } = useI18n()
  const [task, setTask] = useState<{ task: string; task_en: string } | null>(null)
  const [prompt, setPrompt] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<PromptScores | null>(null)
  const [error, setError] = useState<MessageKey | null>(null)
  const [drawing, setDrawing] = useState(false)
  const [image, setImage] = useState<string | null>(null)
  const [drawNote, setDrawNote] = useState<string | null>(null)

  useEffect(() => {
    fetch(`/api/image-lab/task?lang=${lang}`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setTask)
      .catch(() => {})
  }, [lang])

  const score = async () => {
    if (!prompt.trim()) return
    setBusy(true)
    setError(null)
    setResult(null)
    setImage(null)
    try {
      const r = await fetch('/api/image-lab', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ prompt, lang }) })
      if (!r.ok) throw new ApiError(r.status)
      setResult(await r.json())
    } catch (e) {
      setError(e instanceof ApiError && e.status === 503 ? 'lab.unavailable' : e instanceof ApiError && e.status === 429 ? 'tutor.limit' : 'lab.failed')
    } finally {
      setBusy(false)
    }
  }

  const draw = async () => {
    if (!result) return
    setDrawing(true)
    setDrawNote(null)
    try {
      const r = await fetch('/api/generate-image', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ prompt: result.improved_prompt, lang }) })
      const body = await r.json().catch(() => ({}))
      if (r.ok) setImage(body.image)
      else if (r.status === 422 && body.reason) setDrawNote(body.reason)
      else if (r.status === 503) setDrawNote(t('image.waking'))
      else if (r.status === 429) setDrawNote(t('tutor.limit'))
      else setDrawNote(t('image.failed'))
    } catch {
      setDrawNote(t('image.failed'))
    } finally {
      setDrawing(false)
    }
  }

  return (
    <section aria-labelledby="image-h" className="card flex flex-col gap-4">
      <h2 id="image-h" className="m-0 flex items-center gap-2 font-display text-[22px] font-semibold text-maroon">
        <ImageIcon aria-hidden="true" size={20} />
        {t('image.title')}
      </h2>
      {task && (
        <div className="well p-4">
          <h3 className="m-0 mb-1 flex items-center gap-1.5 text-sm font-bold text-maroon">
            <Target aria-hidden="true" size={16} />
            {t('lab.task')}
          </h3>
          <p className="m-0 text-[17px]" dir="auto">
            {task.task}
          </p>
          {lang !== 'en' && (
            <p dir="ltr" lang="en" className="m-0 mt-2 border-t border-line pt-2 font-en text-[15px] text-ink-2">
              {task.task_en}
            </p>
          )}
        </div>
      )}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label htmlFor="image-input" className="font-semibold text-ink-2">
          {t('image.yourPrompt')}
        </label>
        <MicButton onText={(said) => setPrompt((v) => `${v} ${said}`.trim())} />
      </div>
      <textarea
        id="image-input"
        dir="auto"
        rows={4}
        maxLength={2000}
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder={t('image.placeholder')}
        className="min-h-28 w-full resize-y rounded-[20px] border-2 border-line bg-white/80 p-4 text-[17px] text-ink placeholder:text-muted focus:border-maroon"
      />
      <div>
        <button type="button" className="btn-primary" onClick={score} disabled={busy || !prompt.trim()}>
          <span className="flex items-center gap-2">
            {busy && <Loader2 aria-hidden="true" size={20} className="animate-spin" />}
            {busy ? t('lab.working') : t('lab.submit')}
          </span>
        </button>
      </div>
      {error && (
        <p role="alert" className="m-0 flex items-center gap-2 rounded-2xl bg-maroon-soft p-3 font-semibold text-maroon-text">
          <AlertTriangle aria-hidden="true" size={18} />
          {t(error)}
        </p>
      )}
      {result && (
        <ScoreView
          result={result}
          lang={lang}
          criterion="image.criterion"
          footer={
            <div className="mt-3 flex flex-col gap-3">
              <div>
                <button type="button" className="btn-primary" onClick={draw} disabled={drawing}>
                  <span className="flex items-center gap-2">
                    {drawing ? <Loader2 aria-hidden="true" size={20} className="animate-spin" /> : <ImageIcon aria-hidden="true" size={20} />}
                    {drawing ? t('image.drawing') : t('image.draw')}
                  </span>
                </button>
              </div>
              {drawNote && (
                <p role="status" className="m-0 text-ink-2">
                  {drawNote}
                </p>
              )}
              {image && (
                <figure className="m-0">
                  <img src={image} alt={t('image.alt', { p: result.improved_prompt })} className="w-full max-w-[560px] rounded-2xl" width={768} height={768} />
                  <figcaption className="mt-1 text-[13px] text-ink-2">{t('image.caption')}</figcaption>
                </figure>
              )}
            </div>
          }
        />
      )}
    </section>
  )
}
