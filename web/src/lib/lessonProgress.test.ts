import { describe, expect, it } from 'vitest'
import { pathStates } from './lessonProgress'

describe('pathStates', () => {
  it('opens lessons in order', () => {
    expect(pathStates(['d1', 'd2', 'd3'], [])).toEqual(['current', 'locked', 'locked'])
    expect(pathStates(['d1', 'd2', 'd3'], ['d1'])).toEqual(['done', 'current', 'locked'])
    expect(pathStates(['d1', 'd2'], ['d1', 'd2'])).toEqual(['done', 'done'])
  })
})
