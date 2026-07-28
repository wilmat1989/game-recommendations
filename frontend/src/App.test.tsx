import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('App', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('searches, selects a game, and displays ranked recommendations', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.startsWith('/api/games/search')) {
        return jsonResponse({
          query: 'Portal',
          results: [
            { appid: 400, title: 'Portal' },
            { appid: 620, title: 'Portal 2' },
          ],
        })
      }
      if (url.startsWith('/api/games/400/recommendations')) {
        return jsonResponse({
          source: { appid: 400, title: 'Portal' },
          recommendations: [
            { appid: 620, title: 'Portal 2', rank: 1 },
            { appid: 220, title: 'Half-Life 2', rank: 2 },
          ],
        })
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    render(<App />)
    await user.type(screen.getByRole('combobox', { name: /game you already enjoy/i }), 'Portal')

    const portalOption = await screen.findByRole('option', {
      name: 'Portal Steam app 400',
    })
    await user.click(portalOption)

    expect(await screen.findByText(/if you liked/i)).toHaveTextContent('Portal')
    expect(screen.getByRole('link', { name: 'Open Portal 2 on Steam' })).toHaveAttribute(
      'href',
      'https://store.steampowered.com/app/620',
    )
    expect(screen.getByText('#01')).toBeInTheDocument()
    expect(screen.getByText('#02')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/games/400/recommendations?'),
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
  })

  it('shows a useful message when the backend search is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse({ detail: 'Unavailable' }, 503)))
    const user = userEvent.setup()

    render(<App />)
    await user.type(screen.getByRole('combobox', { name: /game you already enjoy/i }), 'Hades')

    expect(await screen.findByRole('alert')).toHaveTextContent(
      /make sure the API is running and try again/i,
    )
  })

  it('renders the empty recommendation state for a known game', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.startsWith('/api/games/search')) {
        return jsonResponse({
          query: 'Lonely',
          results: [{ appid: 999, title: 'Lonely Game' }],
        })
      }
      return jsonResponse({
        source: { appid: 999, title: 'Lonely Game' },
        recommendations: [],
      })
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    render(<App />)
    await user.type(screen.getByRole('combobox', { name: /game you already enjoy/i }), 'Lonely')
    await user.click(await screen.findByRole('option', { name: 'Lonely Game Steam app 999' }))

    await waitFor(() => {
      expect(screen.getByText(/no ranked recommendations are available/i)).toBeInTheDocument()
    })
  })

  it('ignores a stale search response after the query changes', async () => {
    let resolvePortalSearch: ((response: Response) => void) | undefined
    const portalSearch = new Promise<Response>((resolve) => {
      resolvePortalSearch = resolve
    })
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('q=Portal')) return portalSearch
      if (url.includes('q=Hades')) {
        return jsonResponse({
          query: 'Hades',
          results: [{ appid: 1145360, title: 'Hades' }],
        })
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    render(<App />)
    const input = screen.getByRole('combobox', { name: /game you already enjoy/i })
    expect(input).toHaveAttribute('maxlength', '100')

    await user.type(input, 'Portal')
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    await user.clear(input)
    await user.type(input, 'Hades')

    resolvePortalSearch?.(
      jsonResponse({
        query: 'Portal',
        results: [{ appid: 400, title: 'Portal' }],
      }),
    )

    await waitFor(() => expect(input).toHaveValue('Hades'))
    expect(screen.queryByRole('option', { name: 'Portal Steam app 400' })).not.toBeInTheDocument()
    expect(await screen.findByRole('option', { name: 'Hades Steam app 1145360' })).toBeInTheDocument()
  })
})
