import { useI18n } from '../i18n'
import { SaduBand } from './Motifs'

export function Footer() {
  const { t } = useI18n()
  const [before, after] = t('footer.poweredBy').split('{model}')
  return (
    // The bottom padding keeps the last line clear of the phone tab bar.
    <footer className="mt-14 border-t border-line bg-surface pb-20 sm:pb-0">
      <SaduBand />
      <div className="mx-auto flex max-w-[1120px] flex-col gap-3 px-4 py-7 text-sm text-ink-2 sm:px-8">
        <p className="m-0 max-w-[70ch] text-[15px] text-ink">{t('app.about')}</p>
        <p className="m-0 flex flex-wrap gap-x-5 gap-y-1 text-muted">
          <span>{t('footer.made')}</span>
          <span>
            {before}
            <bdi lang="en">Jais 3</bdi>
            {after}
          </span>
          <span>{t('footer.privacy')}</span>
        </p>
      </div>
    </footer>
  )
}
