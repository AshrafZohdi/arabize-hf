import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((f) => {
    const p = join(dir, f)
    return statSync(p).isDirectory() ? files(p) : /\.tsx?$/.test(f) && !f.includes('.test.') ? [p] : []
  })
}

describe('effects', () => {
  it('never return the value of an expression (Chrome 155 scroll methods return Promises)', () => {
    const bad = files(join(__dirname))
      .flatMap((p) => readFileSync(p, 'utf8').split('\n').map((line, i) => ({ p, i, line })))
      .filter(({ line }) => /useEffect\(\(\) => (?![{(]|\(\) =>)/.test(line))
    expect(bad.map(({ p, i }) => `${p}:${i + 1}`)).toEqual([])
  })
})
