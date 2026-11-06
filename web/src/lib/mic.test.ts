import { describe, expect, it } from 'vitest'
import { downsample, encodeWav } from './mic'

describe('microphone audio', () => {
  it('downsamples 48 kHz to 16 kHz', () => {
    const out = downsample(new Float32Array(48000).fill(0.5), 48000)
    expect(out.length).toBe(16000)
    expect(out[100]).toBeCloseTo(0.5)
  })

  it('writes 16 kHz mono 16-bit WAV that the server accepts', async () => {
    const wav = encodeWav(new Float32Array([0, 0.5, -0.5, 1, -1]))
    const v = new DataView(await wav.arrayBuffer())
    const text = (o: number) => String.fromCharCode(...new Uint8Array(v.buffer, o, 4))
    expect([text(0), text(8), text(36)]).toEqual(['RIFF', 'WAVE', 'data'])
    expect([v.getUint16(22, true), v.getUint32(24, true), v.getUint16(34, true)]).toEqual([1, 16000, 16])
    expect(v.getUint32(40, true)).toBe(10)
    expect(v.getInt16(44 + 6, true)).toBe(0x7fff)
  })
})
