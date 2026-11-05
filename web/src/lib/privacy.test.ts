import { describe, expect, it } from 'vitest'
import { findPrivate } from './privacy'

describe('findPrivate', () => {
  it('flags emails, Qatar IDs and phone numbers', () => {
    expect(findPrivate('mail noura.k@ministry.gov.qa today')).toEqual(['email'])
    expect(findPrivate('QID 28463400123')).toEqual(['id'])
    expect(findPrivate('call +974 5512 3456')).toEqual(['phone'])
    expect(findPrivate('call 5512 3456')).toEqual(['phone'])
  })
  it('leaves ordinary work text alone', () => {
    expect(findPrivate('Q3 revenue grew 12% to 4,500,000 in 2026. Check it for hallucinations.')).toEqual([])
  })
})
