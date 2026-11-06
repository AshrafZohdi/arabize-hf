// Photo explain: the browser shrinks the photo, Fanar-2-Oryx-IVU reads its English text, Smart Explain explains it.
import { ApiError } from './api'
import type { ExplainLang } from './explainLang'

type ImageHealth = { read: boolean; generate: boolean }
let health: Promise<ImageHealth> | null = null
export function imageFeatures(): Promise<ImageHealth> {
  health ??= fetch('/api/health')
    .then((r) => r.json())
    .then((h) => ({ read: Boolean(h.image?.read), generate: Boolean(h.image?.generate) }))
    .catch(() => ({ read: false, generate: false }))
  return health
}

/** A JPEG data URL no larger than `max` pixels on its long side, so phone photos upload quickly. */
export async function shrinkImage(file: File, max = 1600): Promise<string> {
  const bitmap = await createImageBitmap(file)
  const scale = Math.min(1, max / Math.max(bitmap.width, bitmap.height))
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(bitmap.width * scale)
  canvas.height = Math.round(bitmap.height * scale)
  canvas.getContext('2d')!.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
  bitmap.close?.()
  return canvas.toDataURL('image/jpeg', 0.85)
}

export async function readImage(image: string, lang: ExplainLang): Promise<{ text: string; description: string }> {
  const r = await fetch('/api/read-image', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ image, lang }) })
  if (!r.ok) throw new ApiError(r.status, Number(r.headers.get('retry-after')) || undefined)
  return r.json()
}
