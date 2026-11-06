// Speech to text: record in the browser, send 16 kHz mono 16-bit WAV to the Space, where Whisper small transcribes it.
import { ApiError } from './api'

let enabled: Promise<boolean> | null = null
export function asrEnabled(): Promise<boolean> {
  enabled ??= fetch('/api/health')
    .then((r) => r.json())
    .then((h) => Boolean(h.asr) && typeof navigator !== 'undefined' && Boolean(navigator.mediaDevices?.getUserMedia))
    .catch(() => false)
  return enabled
}

export const MAX_SECONDS = 30

/** Float samples at `from` Hz to 16 kHz by averaging (enough for speech). */
export function downsample(input: Float32Array, from: number, to = 16000): Float32Array {
  if (from === to) return input
  const ratio = from / to
  const out = new Float32Array(Math.floor(input.length / ratio))
  for (let i = 0; i < out.length; i++) {
    const start = Math.floor(i * ratio)
    const end = Math.min(input.length, Math.floor((i + 1) * ratio))
    let sum = 0
    for (let j = start; j < end; j++) sum += input[j]
    out[i] = sum / Math.max(1, end - start)
  }
  return out
}

/** 16-bit PCM mono WAV. */
export function encodeWav(samples: Float32Array, rate = 16000): Blob {
  const buf = new ArrayBuffer(44 + samples.length * 2)
  const v = new DataView(buf)
  const str = (o: number, s: string) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)))
  str(0, 'RIFF')
  v.setUint32(4, 36 + samples.length * 2, true)
  str(8, 'WAVE')
  str(12, 'fmt ')
  v.setUint32(16, 16, true)
  v.setUint16(20, 1, true)
  v.setUint16(22, 1, true)
  v.setUint32(24, rate, true)
  v.setUint32(28, rate * 2, true)
  v.setUint16(32, 2, true)
  v.setUint16(34, 16, true)
  str(36, 'data')
  v.setUint32(40, samples.length * 2, true)
  samples.forEach((s, i) => v.setInt16(44 + i * 2, Math.max(-1, Math.min(1, s)) * 0x7fff, true))
  return new Blob([buf], { type: 'audio/wav' })
}

export type Recording = { stop: () => Promise<Blob> }

/** Start recording from the microphone; stop() resolves with the WAV. */
export async function startRecording(): Promise<Recording> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } })
  const ctx = new AudioContext()
  const source = ctx.createMediaStreamSource(stream)
  // ScriptProcessor is old but works in every browser we test, including Safari, without a separate worklet file.
  const node = ctx.createScriptProcessor(4096, 1, 1)
  const chunks: Float32Array[] = []
  node.onaudioprocess = (e) => chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)))
  source.connect(node)
  node.connect(ctx.destination)
  return {
    stop: async () => {
      node.disconnect()
      source.disconnect()
      stream.getTracks().forEach((t) => t.stop())
      const rate = ctx.sampleRate
      await ctx.close()
      const all = new Float32Array(chunks.reduce((n, c) => n + c.length, 0))
      let at = 0
      for (const c of chunks) {
        all.set(c, at)
        at += c.length
      }
      return encodeWav(downsample(all, rate).slice(0, MAX_SECONDS * 16000))
    },
  }
}

export async function transcribe(wav: Blob, lang: 'ar' | 'en' | 'auto' = 'auto'): Promise<string> {
  const r = await fetch(`/api/asr?lang=${lang}`, { method: 'POST', headers: { 'content-type': 'audio/wav' }, body: wav })
  if (!r.ok) throw new ApiError(r.status, Number(r.headers.get('retry-after')) || undefined)
  return (await r.json()).text
}
