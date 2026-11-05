import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import ar from './ar.json'
import en from './en.json'

export type UiLang = 'ar' | 'en'
type PluralForms = Partial<Record<Intl.LDMLPluralRule, string>> & { other: string }
type Messages = Record<string, string | PluralForms>

export const messages: Record<UiLang, Messages> = { ar, en }
export type MessageKey = keyof typeof ar

const STORAGE_KEY = 'darby.uiLang'

function readStoredLang(): UiLang {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    return v === 'en' ? 'en' : 'ar'
  } catch {
    return 'ar'
  }
}

function interpolate(s: string, vars?: Record<string, string | number>): string {
  if (!vars) return s
  return s.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m))
}

export function translate(lang: UiLang, key: MessageKey, vars?: Record<string, string | number>): string {
  const entry = messages[lang][key] ?? messages.ar[key]
  if (entry === undefined) return key
  if (typeof entry === 'string') return interpolate(entry, vars)
  const n = Number(vars?.n ?? 0)
  // Arabic uses "zero" as a category; Intl only reports it for ar, so check 0 first for both.
  const rule: Intl.LDMLPluralRule = n === 0 && entry.zero ? 'zero' : new Intl.PluralRules(lang).select(n)
  return interpolate(entry[rule] ?? entry.other, vars)
}

type I18n = {
  lang: UiLang
  dir: 'rtl' | 'ltr'
  setLang: (l: UiLang) => void
  t: (key: MessageKey, vars?: Record<string, string | number>) => string
}

const I18nContext = createContext<I18n | null>(null)

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<UiLang>(readStoredLang)
  const dir = lang === 'ar' ? 'rtl' : 'ltr'

  useEffect(() => {
    document.documentElement.lang = lang
    document.documentElement.dir = dir
  }, [lang, dir])

  const setLang = useCallback((l: UiLang) => {
    setLangState(l)
    try {
      localStorage.setItem(STORAGE_KEY, l)
    } catch {
      // Storage can be blocked; the choice still holds for this visit.
    }
  }, [])

  const t = useCallback((key: MessageKey, vars?: Record<string, string | number>) => translate(lang, key, vars), [lang])
  const value = useMemo(() => ({ lang, dir, setLang, t }) as I18n, [lang, dir, setLang, t])
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n(): I18n {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used inside I18nProvider')
  return ctx
}
