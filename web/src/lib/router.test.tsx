import { act, cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { RouterProvider, useRouter } from './router'

let go: (to: string) => void = () => {}
function Probe() {
  const { path, navigate } = useRouter()
  go = navigate
  return <p data-testid="path">{path}</p>
}

afterEach(() => {
  cleanup()
  window.history.pushState(null, '', '/')
})

describe('router', () => {
  it('keeps the query string out of the route', () => {
    window.history.pushState(null, '', '/glossary')
    render(
      <RouterProvider>
        <Probe />
      </RouterProvider>,
    )
    act(() => go('/?text=Hallucination'))
    expect(screen.getByTestId('path').textContent).toBe('/')
    expect(window.location.search).toBe('?text=Hallucination')
    act(() => go('/tutor?q=What%20is%20RAG'))
    expect(screen.getByTestId('path').textContent).toBe('/tutor')
  })
})
