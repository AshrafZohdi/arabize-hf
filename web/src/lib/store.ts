import { useSyncExternalStore } from 'react'

/** A small JSON value in local storage that components can subscribe to. Storage can be blocked: then it lives in memory. */
export function createStore<T>(key: string, empty: T) {
  let cache: T | undefined
  const listeners = new Set<() => void>()

  const get = (): T => {
    if (cache !== undefined) return cache
    try {
      const raw = localStorage.getItem(key)
      cache = raw ? { ...empty, ...JSON.parse(raw) } : empty
    } catch {
      cache = empty
    }
    return cache as T
  }

  const set = (next: T) => {
    cache = next
    try {
      localStorage.setItem(key, JSON.stringify(next))
    } catch {
      // Storage blocked: keep the value for this visit.
    }
    listeners.forEach((l) => l())
  }

  const subscribe = (l: () => void) => {
    listeners.add(l)
    return () => {
      listeners.delete(l)
    }
  }

  const use = (): T => useSyncExternalStore(subscribe, get, () => empty)
  const reset = () => {
    cache = undefined
  }
  return { get, set, use, reset }
}
