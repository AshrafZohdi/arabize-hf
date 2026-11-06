import { afterEach, describe, expect, it, vi } from 'vitest'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.resetModules()
})

describe('speak', () => {
  it('plays the bucket recording for English terms without loading Kokoro', async () => {
    const fetchMock = vi.fn(async () => ({ type: 'opaqueredirect', status: 0 }))
    vi.stubGlobal('fetch', fetchMock)
    const played: string[] = []
    vi.stubGlobal(
      'Audio',
      class {
        src: string
        onended: (() => void) | null = null
        onerror: (() => void) | null = null
        constructor(src: string) {
          this.src = src
        }
        play() {
          played.push(this.src)
          setTimeout(() => this.onended?.(), 0)
          return Promise.resolve()
        }
        pause() {}
      },
    )
    const { speak } = await import('./voice')
    await speak('en', 'Hallucination', 'hallucination')
    expect(fetchMock).toHaveBeenCalledWith('/api/tts/term/hallucination?lang=en', { redirect: 'manual' })
    expect(played).toEqual(['/api/tts/term/hallucination?lang=en'])
  })
})
