import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n'
import { RouterProvider } from '../lib/router'
import { TutorPage } from './Tutor'

function sseBody(blocks: string[]) {
  const enc = new TextEncoder()
  return new ReadableStream({
    start(c) {
      for (const b of blocks) c.enqueue(enc.encode(b))
      c.close()
    },
  })
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('TutorPage', () => {
  it('streams an answer into the chat without crashing', async () => {
    // Chrome 155 returns a Promise from scrollIntoView; an effect must not hand that to React as its cleanup.
    Element.prototype.scrollIntoView = function () {
      return Promise.resolve() as unknown as void
    }
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (url.startsWith('/api/lessons')) return new Response(JSON.stringify({ lessons: [{ slug: 'day-1', order: 1, title: { en: 'L1', ar: 'د1' } }] }))
        return new Response(sseBody(['event: token\ndata: {"text":"السياق "}\n\n', 'event: token\ndata: {"text":"يعني"}\n\n', 'event: done\ndata: {"messages_left":19}\n\n']), {
          headers: { 'content-type': 'text/event-stream' },
        })
      }),
    )
    render(
      <I18nProvider>
        <RouterProvider>
          <TutorPage />
        </RouterProvider>
      </I18nProvider>,
    )
    const box = screen.getByRole('textbox')
    fireEvent.change(box, { target: { value: 'شنو السياق؟' } })
    await act(async () => {
      fireEvent.keyDown(box, { key: 'Enter' })
    })
    await waitFor(() => expect(screen.getByRole('log').textContent).toContain('السياق يعني'))
  })
})
