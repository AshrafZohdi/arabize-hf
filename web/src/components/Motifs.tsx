import { useId } from 'react'

/**
 * The serrated line of Qatar's flag, where the white meets the maroon, as the strip at the very top of the page.
 * Decorative only.
 */
export function FlagEdge() {
  const id = useId()
  return (
    <svg aria-hidden="true" className="block h-2.5 w-full" preserveAspectRatio="none">
      <defs>
        <pattern id={id} width="20" height="10" patternUnits="userSpaceOnUse">
          <path d="M0 0H20V3L10 10 0 3Z" fill="var(--maroon)" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#${id})`} />
    </svg>
  )
}

/**
 * A band in the manner of Al Sadu, the Bedouin weaving of the Gulf: interlocking triangles in maroon, black and
 * white with a small gold diamond. Used as a divider. Decorative only.
 */
export function SaduBand({ className = '' }: { className?: string }) {
  const id = useId()
  return (
    <svg aria-hidden="true" className={`block h-3.5 w-full ${className}`} preserveAspectRatio="none">
      <defs>
        <pattern id={id} width="24" height="14" patternUnits="userSpaceOnUse">
          <rect width="24" height="14" fill="var(--maroon)" />
          <path d="M0 14 6 3 12 14Z" fill="var(--surface)" />
          <path d="M12 0 18 11 24 0Z" fill="var(--ink)" />
          <path d="M6 8 8 10.5 6 13 4 10.5Z" fill="var(--gold)" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#${id})`} />
    </svg>
  )
}
