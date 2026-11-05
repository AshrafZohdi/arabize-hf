import { describe, expect, it } from 'vitest'
import { parseSseBlock } from './api'

describe('parseSseBlock', () => {
  it('reads event and JSON data', () => {
    expect(parseSseBlock('event: explanation\ndata: {"text":"يعني"}')).toEqual({ event: 'explanation', data: { text: 'يعني' } })
  })
  it('ignores blocks without data', () => {
    expect(parseSseBlock(': keep-alive')).toBeNull()
  })
})
