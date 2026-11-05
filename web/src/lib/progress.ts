import { useSyncExternalStore } from 'react'

// XP and streak live in local storage for the hackathon (no accounts). Rules arrive in step 6.
export type Progress = { xp: number; streak: number }

const KEY = 'darby.progress'
const EMPTY: Progress = { xp: 0, streak: 0 }
let cache: Progress | null = null
const listeners = new Set<() => void>()

function read(): Progress {
  if (cache) return cache
  try {
    const raw = localStorage.getItem(KEY)
    cache = raw ? { ...EMPTY, ...JSON.parse(raw) } : EMPTY
  } catch {
    cache = EMPTY
  }
  return cache!
}

export function setProgress(next: Progress) {
  cache = next
  try {
    localStorage.setItem(KEY, JSON.stringify(next))
  } catch {
    // Storage blocked: keep the in-memory value for this visit.
  }
  listeners.forEach((l) => l())
}

export function useProgress(): Progress {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l)
      return () => listeners.delete(l)
    },
    read,
    () => EMPTY,
  )
}
