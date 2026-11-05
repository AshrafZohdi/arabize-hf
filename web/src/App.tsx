import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { useI18n } from './i18n'
import { useRouter } from './lib/router'
import { Home } from './pages/Home'
import { GlossaryPage } from './pages/Glossary'
import { NotFound, TutorPage } from './pages/Simple'

function Page({ path }: { path: string }) {
  if (path === '/') return <Home />
  if (path.startsWith('/glossary')) return <GlossaryPage />
  if (path.startsWith('/tutor')) return <TutorPage />
  return <NotFound />
}

export default function App() {
  const { t } = useI18n()
  const { path } = useRouter()
  return (
    <div className="min-h-screen bg-bg text-ink">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:start-4 focus:top-4 focus:z-10 focus:rounded-xl focus:bg-surface focus:p-3">
        {t('app.skipToContent')}
      </a>
      <Header />
      <main id="main" className="mx-auto max-w-[1240px] px-4 pt-10 sm:px-10">
        <Page path={path} />
      </main>
      <Footer />
    </div>
  )
}
