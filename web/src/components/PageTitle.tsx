import type { ReactNode } from 'react'

export function PageTitle({ title, subtitle, aside }: { title: string; subtitle?: string; aside?: ReactNode }) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-5">
      <div>
        <h1 className="m-0 font-display text-[28px] leading-[1.35] font-semibold sm:text-4xl">{title}</h1>
        {subtitle && <p className="mt-1 mb-0 text-lg text-muted">{subtitle}</p>}
      </div>
      {aside}
    </div>
  )
}
