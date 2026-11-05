// Text that looks private gets a warning before it is sent. Nothing is stored either way.
const PATTERNS: { kind: 'email' | 'phone' | 'id'; re: RegExp }[] = [
  { kind: 'email', re: /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/ },
  // Qatar ID: 11 digits starting with 2 or 3.
  { kind: 'id', re: /(?<!\d)[23]\d{10}(?!\d)/ },
  // Phone numbers: +974 or 00974 prefixes, or 8 digit local numbers, with optional spaces or dashes.
  { kind: 'phone', re: /(?:\+|00)\d{1,3}[\s-]?\d{3,4}[\s-]?\d{3,4}|(?<!\d)[3-7]\d{3}[\s-]?\d{4}(?!\d)/ },
]

export type PrivateKind = (typeof PATTERNS)[number]['kind']

export function findPrivate(text: string): PrivateKind[] {
  return PATTERNS.filter((p) => p.re.test(text)).map((p) => p.kind)
}
