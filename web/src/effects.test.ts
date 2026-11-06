import { describe, expect, it } from 'vitest'

// Vite reads the sources as text, so this needs no Node types in the app's TypeScript settings.
const sources = import.meta.glob(['./**/*.{ts,tsx}', '!./**/*.test.*'], { query: '?raw', import: 'default', eager: true }) as Record<string, string>

describe('effects', () => {
  it('never return the value of an expression (Chrome 155 scroll methods return Promises)', () => {
    const bad = Object.entries(sources).flatMap(([path, text]) =>
      text
        .split('\n')
        .map((line, i) => ({ path, i, line }))
        .filter(({ line }) => /useEffect\(\(\) => (?![{(]|\(\) =>)/.test(line))
        .map(({ path, i }) => `${path}:${i + 1}`),
    )
    expect(Object.keys(sources).length).toBeGreaterThan(10)
    expect(bad).toEqual([])
  })
})
