import type { Mark } from './api'

const SYMBOL: Record<Mark, string> = { hit: '■', near: '▣', miss: '□' }

/** The result grid as plain text: never contains the word or any letter. */
export function shareText(title: string, date: string, rows: Mark[][], won: boolean, max: number): string {
  const score = won ? `${rows.length}/${max}` : `X/${max}`
  return [`${title} ${date} ${score}`, ...rows.map((r) => r.map((m) => SYMBOL[m]).join(''))].join('\n')
}
