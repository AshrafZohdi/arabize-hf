import { Check, X } from 'lucide-react'
import { useState } from 'react'
import { useI18n } from '../../i18n'
import type { Question } from '../../lib/api'
import { award, XP } from '../../lib/progress'

function questionKey(q: Question): string {
  let h = 0
  for (const c of q.question + q.options.join('|')) h = (h * 31 + c.charCodeAt(0)) | 0
  return `explain:${h >>> 0}`
}

export function QuickQuestion({ question }: { question: Question }) {
  const { t } = useI18n()
  const [wrong, setWrong] = useState<number[]>([])
  const [solved, setSolved] = useState(false)
  const [earned, setEarned] = useState(0)

  const choose = (i: number) => {
    if (solved || wrong.includes(i)) return
    if (i === question.correct_index) {
      setSolved(true)
      setEarned(award(questionKey(question), XP.practice + (wrong.length === 0 ? XP.firstTry : 0)))
    } else {
      setWrong((w) => [...w, i])
    }
  }

  return (
    <article className="relative min-w-0 flex-[1_1_300px] rounded-2xl border border-line bg-surface-2 p-5" aria-labelledby="quiz-h">
      <div className="flex items-center justify-between gap-3">
        <h3 id="quiz-h" className="m-0 text-base font-bold text-maroon">
          {t('quiz.title')}
        </h3>
        <span className="rounded-full bg-gold-soft px-3 py-1 text-sm font-bold text-gold-text">{t('quiz.points', { n: XP.practice })}</span>
      </div>
      <p className="mt-2 mb-4 text-lg font-bold">{question.question}</p>
      <div dir="ltr" lang="en" className="grid grid-cols-1 gap-2.5 font-en min-[400px]:grid-cols-2">
        {question.options.map((o, i) => {
          const isRight = solved && i === question.correct_index
          const isWrong = wrong.includes(i)
          return (
            <button
              key={i}
              type="button"
              onClick={() => choose(i)}
              aria-disabled={solved || isWrong}
              aria-label={isRight ? `${o}, ${t('quiz.correctMark')}` : isWrong ? `${o}, ${t('quiz.wrongMark')}` : undefined}
              className={`flex min-h-[52px] cursor-pointer items-center justify-center gap-2 rounded-[14px] border-2 px-3 font-semibold transition-transform active:translate-y-0.5 ${
                isRight
                  ? 'border-success bg-success-soft font-bold text-success-text shadow-[0_4px_0_var(--success)]'
                  : isWrong
                    ? 'cursor-default border-line bg-surface-3 text-muted line-through shadow-none'
                    : 'border-line bg-white text-ink shadow-answer hover:border-maroon'
              }`}
            >
              {o}
              {isRight && <Check aria-hidden="true" size={18} strokeWidth={3} />}
              {isWrong && <X aria-hidden="true" size={18} strokeWidth={3} />}
            </button>
          )
        })}
      </div>
      <p role="status" aria-live="polite" className="mt-3.5 mb-0 min-h-6 text-sm font-semibold">
        {solved ? (
          <span className="text-success-text">
            {t('quiz.correct')} {question.why}
          </span>
        ) : wrong.length > 0 ? (
          <span className="text-ink-2">{t('quiz.wrong')}</span>
        ) : null}
      </p>
      {earned > 0 && (
        <span aria-hidden="true" className="points-fly pointer-events-none absolute end-6 top-4 rounded-full bg-gold px-3 py-1 font-bold text-gold-text">
          {t('quiz.earned', { n: earned })}
        </span>
      )}
    </article>
  )
}
