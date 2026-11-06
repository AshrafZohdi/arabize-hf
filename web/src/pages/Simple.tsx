import { PageTitle } from '../components/PageTitle'
import { useI18n } from '../i18n'
import { Link } from '../lib/router'

export function NotFound() {
  const { t } = useI18n()
  return (
    <>
      <PageTitle title={t('notFound.title')} />
      <Link href="/">{t('notFound.back')}</Link>
    </>
  )
}
