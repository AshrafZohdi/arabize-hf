import { describe, expect, it } from 'vitest'
import { shareText } from './share'

describe('shareText', () => {
  it('shows the grid and score, never letters', () => {
    const t = shareText('Darby', '2026-11-06', [['miss', 'near', 'hit'], ['hit', 'hit', 'hit']], true, 6)
    expect(t).toBe('Darby 2026-11-06 2/6\n□▣■\n■■■')
    expect(t).not.toMatch(/[ء-ي]/)
  })
  it('marks a loss with X', () => {
    expect(shareText('D', 'd', [['miss']], false, 6).split('\n')[0]).toBe('D d X/6')
  })
})
