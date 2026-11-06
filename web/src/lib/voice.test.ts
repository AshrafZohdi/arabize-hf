import { afterEach, describe, expect, it, vi } from 'vitest'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.resetModules()
})

const BUCKET = 'https://huggingface.co/buckets/x/y/resolve/audio/en/hallucination.wav'

function stubAudio(played: string[], created: string[]) {
  vi.stubGlobal(
    'Audio',
    class {
      src: string
      preload = ''
      currentTime = 0
      onended: (() => void) | null = null
      onerror: (() => void) | null = null
      constructor(src: string) {
        this.src = src
        created.push(src)
      }
      play() {
        played.push(this.src)
        setTimeout(() => this.onended?.(), 0)
        return Promise.resolve()
      }
      pause() {}
    },
  )
}

function stubFetch() {
  const fetchMock = vi.fn(async (url: string) => ({
    ok: true,
    json: async () => (url === '/api/health' ? { voice_enabled: true } : { 'en/hallucination': BUCKET }),
  }))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('speak', () => {
  it('plays the bucket recording straight away, without a redirect or Kokoro', async () => {
    const fetchMock = stubFetch()
    const played: string[] = []
    stubAudio(played, [])
    const { speak } = await import('./voice')
    await speak('en', 'Hallucination', 'hallucination')
    expect(fetchMock).toHaveBeenCalledWith('/api/tts/recordings')
    expect(played).toEqual([BUCKET])
  })

  it('Arabic without a recording is spoken by the Space', async () => {
    stubFetch()
    const played: string[] = []
    stubAudio(played, [])
    const { speak } = await import('./voice')
    await speak('ar', 'نموذج', 'model')
    expect(played).toEqual(['/api/tts/term/model?lang=ar'])
  })

  it('preloads a card once and reuses the element on tap', async () => {
    stubFetch()
    const played: string[] = []
    const created: string[] = []
    stubAudio(played, created)
    const { preloadTerm, speak } = await import('./voice')
    await preloadTerm('hallucination')
    await speak('en', 'Hallucination', 'hallucination')
    expect(created).toEqual(['/api/tts/term/hallucination?lang=ar', BUCKET])
    expect(played).toEqual([BUCKET])
  })
})
