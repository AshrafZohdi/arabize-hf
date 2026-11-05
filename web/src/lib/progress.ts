import { createStore } from './store'

// XP, streaks and saved terms live in local storage for the hackathon (no accounts).
// XP rules from the old Arabize app: 15 for explaining and practising a term, plus 5 on the first attempt.
export type Progress = { xp: number; streak: number; lastActive: string | null; paid: string[] }

export const XP = { practice: 15, firstTry: 5 } as const

const store = createStore<Progress>('darby.progress', { xp: 0, streak: 0, lastActive: null, paid: [] })
export const useProgress = store.use
export const resetProgressCache = store.reset

/** Qatar date as YYYY-MM-DD. */
export function qatarDate(now = new Date()): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Qatar' }).format(now)
}

function nextStreak(p: Progress, today: string): number {
  if (p.lastActive === today) return p.streak
  const yesterday = qatarDate(new Date(new Date(`${today}T12:00:00+03:00`).getTime() - 86_400_000))
  return p.lastActive === yesterday ? p.streak + 1 : 1
}

/** Pay XP once per key (for example a question id). Returns the XP actually paid. */
export function award(key: string, amount: number, now = new Date()): number {
  const p = store.get()
  if (p.paid.includes(key)) return 0
  const today = qatarDate(now)
  store.set({ xp: p.xp + amount, streak: nextStreak(p, today), lastActive: today, paid: [...p.paid.slice(-499), key] })
  return amount
}
