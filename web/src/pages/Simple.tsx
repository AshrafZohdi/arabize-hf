import { PageTitle } from '../components/PageTitle'
import { useI18n } from '../i18n'
import { Link } from '../lib/router'

export function GlossaryPage() {
  const { t } = useI18n()
  return (
    <>
      <PageTitle title={t('glossary.title')} />
      <p className="text-muted">{t('placeholder.soon')}</p>
    </>
  )
}

export function TutorPage() {
  const { t } = useI18n()
  return (
    <>
      <PageTitle title={t('tutor.title')} />
      <p className="text-muted">{t('placeholder.soon')}</p>
    </>
  )
}

export function NotFound() {
  const { t } = useI18n()
  return (
    <>
      <PageTitle title={t('notFound.title')} />
      <Link href="/">{t('notFound.back')}</Link>
    </>
  )
}
