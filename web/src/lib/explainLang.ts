import { useState } from 'react'

export type ExplainLang = 'en' | 'msa' | 'gulf'
const KEY = 'darby.explainLang'

export function useExplainLang(): [ExplainLang, (l: ExplainLang) => void] {
  const [lang, setLang] = useState<ExplainLang>(() => {
    try {
      const v = localStorage.getItem(KEY)
      return v === 'en' || v === 'msa' ? v : 'gulf'
    } catch {
      return 'gulf'
    }
  })
  const set = (l: ExplainLang) => {
    setLang(l)
    try {
      localStorage.setItem(KEY, l)
    } catch {
      // Storage blocked: keep the choice for this visit.
    }
  }
  return [lang, set]
}
