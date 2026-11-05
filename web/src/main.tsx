import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'
import { I18nProvider } from './i18n'
import { RouterProvider } from './lib/router'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <I18nProvider>
      <RouterProvider>
        <App />
      </RouterProvider>
    </I18nProvider>
  </StrictMode>,
)
