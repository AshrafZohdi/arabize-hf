import { describe, expect, it } from 'vitest'
import ar from './ar.json'
import en from './en.json'
import { translate } from './index'

const shape = (o: Record<string, unknown>) =>
  Object.entries(o)
    .map(([k, v]) => (typeof v === 'string' ? k : `${k}{${Object.keys(v as object).sort().join(',')}}`))
    .sort()

describe('i18n files', () => {
  it('ar and en have the same keys and plural shapes', () => {
    expect(shape(en)).toEqual(shape(ar))
  })

  it('contain no em or en dashes', () => {
    for (const file of [ar, en]) {
      expect(JSON.stringify(file)).not.toMatch(/[–—]/)
    }
  })

  it('use Western digits only', () => {
    for (const file of [ar, en]) {
      expect(JSON.stringify(file)).not.toMatch(/[٠-٩۰-۹]/)
    }
  })
})

describe('translate', () => {
  it('picks Arabic plural forms', () => {
    expect(translate('ar', 'header.streak', { n: 0 })).toBe('0 أيام')
    expect(translate('ar', 'header.streak', { n: 1 })).toBe('يوم واحد')
    expect(translate('ar', 'header.streak', { n: 2 })).toBe('يومان')
    expect(translate('ar', 'header.streak', { n: 7 })).toBe('7 أيام')
    expect(translate('ar', 'header.points', { n: 340 })).toBe('340 نقطة')
  })

  it('interpolates variables', () => {
    expect(translate('en', 'footer.poweredBy', { model: 'Fanar 2', platform: 'Hugging Face' })).toBe(
      "Runs on Qatar's Fanar 2 model on Hugging Face",
    )
  })
})
