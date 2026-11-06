import { award } from './progress'
import { createStore } from './store'

// Which lessons are done, in local storage (no accounts). 100 XP per completed lesson (map node, old app's rule).
// `place` remembers where the learner left each unfinished lesson: the step on screen and the furthest step reached.
type Place = { at: number; reached: number }
type LessonProgress = { done: string[]; place?: Record<string, Place> }
const store = createStore<LessonProgress>('darby.lessons', { done: [] })
export const useLessonProgress = store.use
export const resetLessonProgressCache = store.reset
export const LESSON_XP = 100

export function savePlace(slug: string, place: Place): void {
  const p = store.get()
  store.set({ ...p, place: { ...p.place, [slug]: place } })
}

export function getPlace(slug: string): Place | null {
  return store.get().place?.[slug] ?? null
}

export function completeLesson(slug: string): number {
  const p = store.get()
  const { [slug]: _, ...place } = p.place ?? {}
  store.set({ done: p.done.includes(slug) ? p.done : [...p.done, slug], place })
  return award(`lesson:${slug}`, LESSON_XP)
}

export type PathState = 'done' | 'current' | 'locked'

/** Lessons open in order: every done lesson, then the first one not done; the rest stay locked. */
export function pathStates(slugs: string[], done: string[]): PathState[] {
  let currentGiven = false
  return slugs.map((s) => {
    if (done.includes(s)) return 'done'
    if (!currentGiven) {
      currentGiven = true
      return 'current'
    }
    return 'locked'
  })
}
