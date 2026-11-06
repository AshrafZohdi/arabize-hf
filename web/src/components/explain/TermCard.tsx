import { BookOpen, BookmarkCheck, Library, Plus, Sparkles } from 'lucide-react'
import { useI18n } from '../../i18n'
import type { Card } from '../../lib/api'
import { saveTerm, termKey, useDictionary } from '../../lib/dictionary'
import { ListenButtons } from '../ListenButtons'

/** textDir: the direction of the explanation language, which can differ from the interface (Arabic text in the English UI). */
export function TermCard({ card, showMsa, textDir = 'rtl' }: { card: Card; showMsa: boolean; textDir?: 'rtl' | 'ltr' }) {
  const { t } = useI18n()
  const saved = Boolean(useDictionary().terms[termKey(card.term_en)])
  const Icon = card.source === 'glossary' ? BookOpen : card.source === 'bank' ? Library : Sparkles
  return (
    <article className="min-w-0 flex-[1_1_300px]" aria-labelledby={`term-${termKey(card.term_en)}`}>
      <div className="flex items-center gap-3.5">
        <span className="flex size-14 shrink-0 items-center justify-center rounded-[18px] bg-maroon-soft text-maroon">
          <Icon aria-hidden="true" size={28} strokeWidth={2} />
        </span>
        <div className="min-w-0 flex-auto">
          <h3 id={`term-${termKey(card.term_en)}`} className="m-0 font-display text-[26px] leading-[1.3] font-semibold text-maroon" lang="ar">
            {card.term_ar}
          </h3>
          <div className="font-en text-[17px] font-semibold text-ink-2">
            <span dir="ltr" lang="en">
              {card.term_en}
            </span>
          </div>
        </div>
        <ListenButtons en={card.term_en} ar={card.term_ar} termId={card.id} />
      </div>
      {card.source === 'bank' ? (
        <p className="mt-3.5 mb-0 text-[17px] text-ink-2">{t('explain.bankNote')}</p>
      ) : (
        <p className="mt-3.5 mb-0 text-[17px]" dir={textDir}>
          {card.explanation}
        </p>
      )}
      {card.analogy && (
        <div className="mt-3.5 rounded-[14px] bg-surface-3 px-4 py-3 text-ink-2" dir={textDir}>
          <span className="sr-only">{t('explain.analogy')}: </span>
          {card.analogy}
        </div>
      )}
      <div className="mt-3.5 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => saveTerm(card)}
          disabled={saved}
          className={`inline-flex min-h-11 cursor-pointer items-center gap-1.5 rounded-full border px-4 font-bold ${
            saved ? 'cursor-default border-teal-soft bg-teal-soft text-teal-text' : 'border-line bg-white text-ink hover:bg-surface-3'
          }`}
        >
          {saved ? <BookmarkCheck aria-hidden="true" size={18} /> : <Plus aria-hidden="true" size={18} />}
          {saved ? t('explain.saved') : t('explain.save')}
        </button>
        {showMsa && <span className="text-sm text-muted">{t('explain.msaLabel', { t: card.term_ar })}</span>}
      </div>
      <p className="mt-2 mb-0 flex items-center gap-1.5 text-[13px] text-muted">
        <Icon aria-hidden="true" size={14} />
        {card.source === 'glossary' ? t('explain.fromGlossary') : card.source === 'bank' ? t('explain.fromBank') : t('explain.fromFanar')}
      </p>
    </article>
  )
}
