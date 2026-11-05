import { createStore } from './store'
import type { Card } from './api'

// "My dictionary": terms the learner saved. Known terms (teal) are the ones in here.
export type SavedTerm = Pick<Card, 'term_en' | 'term_ar' | 'explanation' | 'source'> & { savedAt: string }
type Dictionary = { terms: Record<string, SavedTerm> }

const store = createStore<Dictionary>('darby.dictionary', { terms: {} })
export const useDictionary = store.use
export const resetDictionaryCache = store.reset

export const termKey = (en: string) => en.trim().toLowerCase()

export function saveTerm(card: Card) {
  const d = store.get()
  store.set({
    terms: {
      ...d.terms,
      [termKey(card.term_en)]: { term_en: card.term_en, term_ar: card.term_ar, explanation: card.explanation, source: card.source, savedAt: new Date().toISOString() },
    },
  })
}

export function removeTerm(en: string) {
  const { [termKey(en)]: _, ...rest } = store.get().terms
  store.set({ terms: rest })
}
