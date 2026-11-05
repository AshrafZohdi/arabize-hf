import { useI18n } from '../i18n'

export function Footer() {
  const { t } = useI18n()
  const [before, middle, after] = t('footer.poweredBy').split(/\{model\}|\{platform\}/)
  return (
    <footer className="mx-auto mt-10 flex max-w-[1240px] flex-wrap items-center gap-3 px-4 pb-14 text-sm text-muted sm:px-10">
      <span className="rounded-full border border-line bg-surface px-3.5 py-1.5">
        {before}
        <bdi lang="en">Fanar 2</bdi>
        {middle}
        <bdi lang="en">Hugging Face</bdi>
        {after}
      </span>
      <span>{t('footer.privacy')}</span>
    </footer>
  )
}
