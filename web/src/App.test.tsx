import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import App from './App'
import { I18nProvider } from './i18n'
import { RouterProvider } from './lib/router'

const renderApp = () =>
  render(
    <I18nProvider>
      <RouterProvider>
        <App />
      </RouterProvider>
    </I18nProvider>,
  )

afterEach(() => {
  cleanup()
  localStorage.clear()
  window.history.pushState(null, '', '/')
})

describe('App shell', () => {
  it('renders Arabic RTL by default with the three nav items', () => {
    renderApp()
    expect(document.documentElement.dir).toBe('rtl')
    expect(document.documentElement.lang).toBe('ar')
    const nav = screen.getByRole('navigation', { name: 'الأقسام' })
    expect(nav.textContent).toContain('الرئيسية')
    expect(nav.textContent).toContain('القاموس')
    expect(nav.textContent).toContain('المعلّم')
  })

  it('switches to English LTR', () => {
    renderApp()
    fireEvent.click(screen.getByRole('button', { name: /English/ }))
    expect(document.documentElement.dir).toBe('ltr')
    expect(screen.getByRole('navigation', { name: 'Sections' })).toBeTruthy()
  })

  it('navigates to the glossary without a reload', () => {
    renderApp()
    fireEvent.click(screen.getByRole('link', { name: 'القاموس' }))
    expect(window.location.pathname).toBe('/glossary')
    expect(screen.getByRole('heading', { level: 1, name: 'القاموس' })).toBeTruthy()
  })
})
