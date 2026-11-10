import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { PageBackdrop } from './components/PageBackdrop'
import { useI18n } from './i18n'
import { useRouter } from './lib/router'
import { Home } from './pages/Home'
import { LearnPage } from './pages/Learn'
import { LessonPage } from './pages/Lesson'
import { GlossaryPage } from './pages/Glossary'
import { NotFound } from './pages/Simple'
import { TutorPage } from './pages/Tutor'

function Page({ path }: { path: string }) {
  if (path === '/') return <Home />
  if (path.startsWith('/learn')) return <LearnPage />
  if (path.startsWith('/glossary')) return <GlossaryPage />
  if (path.startsWith('/tutor')) return <TutorPage />
  const lesson = path.match(/^\/lesson\/([a-z0-9-]+)\/?$/)
  if (lesson) return <LessonPage key={lesson[1]} slug={lesson[1]} />
  return <NotFound />
}

export default function App() {
  const { t } = useI18n()
  const { path } = useRouter()
  return (
    <div className="relative flex min-h-screen flex-col text-ink">
      <PageBackdrop />
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:start-4 focus:top-4 focus:z-40 focus:rounded-xl focus:bg-surface focus:p-3">
        {t('app.skipToContent')}
      </a>
      <Header />
      <main id="main" className="mx-auto w-full max-w-[1120px] flex-1 px-4 pt-7 sm:px-8 sm:pt-10">
        <Page path={path} />
      </main>
      <Footer />
    </div>
  )
}
