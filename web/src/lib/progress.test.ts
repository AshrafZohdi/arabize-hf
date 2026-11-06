import { afterEach, describe, expect, it } from 'vitest'
import { award, qatarDate, resetProgressCache, todayXp } from './progress'

afterEach(() => {
  localStorage.clear()
  resetProgressCache()
})

const read = () => JSON.parse(localStorage.getItem('darby.progress')!)

describe('award', () => {
  it('pays once per key and starts a streak', () => {
    const now = new Date('2026-11-05T10:00:00+03:00')
    expect(award('q1', 20, now)).toBe(20)
    expect(award('q1', 20, now)).toBe(0)
    expect(read()).toMatchObject({ xp: 20, streak: 1, lastActive: '2026-11-05' })
  })
  it('grows the streak on consecutive Qatar days and restarts after a gap', () => {
    award('a', 15, new Date('2026-11-05T23:30:00+03:00'))
    award('b', 15, new Date('2026-11-06T00:10:00+03:00'))
    expect(read().streak).toBe(2)
    award('c', 15, new Date('2026-11-08T09:00:00+03:00'))
    expect(read().streak).toBe(1)
  })
  it('uses Qatar time for the date', () => {
    expect(qatarDate(new Date('2026-11-05T22:30:00Z'))).toBe('2026-11-06')
  })
  it('counts points per Qatar day for the daily goal', () => {
    award('a', 15, new Date('2026-11-05T10:00:00+03:00'))
    award('b', 20, new Date('2026-11-05T11:00:00+03:00'))
    expect(todayXp(read(), new Date('2026-11-05T12:00:00+03:00'))).toBe(35)
    expect(todayXp(read(), new Date('2026-11-06T09:00:00+03:00'))).toBe(0)
    award('c', 15, new Date('2026-11-06T09:00:00+03:00'))
    expect(read().dayXp).toBe(15)
  })
})
