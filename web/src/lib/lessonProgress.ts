import { award } from './progress'
import { createStore } from './store'

// Which lessons are done, in local storage (no accounts). 100 XP per completed lesson (map node, old app's rule).
type LessonProgress = { done: string[] }
const store = createStore<LessonProgress>('darby.lessons', { done: [] })
export const useLessonProgress = store.use
export const resetLessonProgressCache = store.reset
export const LESSON_XP = 100

export function completeLesson(slug: string): number {
  const p = store.get()
  if (!p.done.includes(slug)) store.set({ done: [...p.done, slug] })
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
