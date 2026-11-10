type Option<T extends string> = { value: T; label: string; lang?: string }

export function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string
  options: Option<T>[]
  value: T
  onChange: (v: T) => void
}) {
  return (
    <div role="group" aria-label={label} className="flex gap-1 rounded-xl border border-line bg-surface-2 p-1 text-[15px] font-semibold">
      {options.map((o) => {
        const on = o.value === value
        return (
          <button
            key={o.value}
            type="button"
            lang={o.lang}
            aria-pressed={on}
            onClick={() => onChange(o.value)}
            className={`min-h-10 cursor-pointer rounded-lg border-0 px-4 ${on ? 'bg-maroon text-white' : 'bg-transparent text-ink-2 hover:bg-surface-3'}`}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}
