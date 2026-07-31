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
    window.localStorage.clear()
    window.history.replaceState({}, '', '/')
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
    expect(screen.queryByText('No matching games found.')).not.toBeInTheDocument()
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

  it('ignores malformed played-game storage', () => {
    window.localStorage.setItem('next-play:played-appids', '{not valid json')

    render(<App />)

    expect(screen.getByRole('combobox', { name: /game you already enjoy/i })).toBeInTheDocument()
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

  it('moves played games behind unplayed recommendations and persists the choice', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.startsWith('/api/games/search')) {
        const isHadesSearch = url.includes('q=Hades')
        return jsonResponse({
          query: isHadesSearch ? 'Hades' : 'Portal',
          results: [
            isHadesSearch
              ? { appid: 1145360, title: 'Hades' }
              : { appid: 400, title: 'Portal' },
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
      if (url.startsWith('/api/games/1145360/recommendations')) {
        return jsonResponse({
          source: { appid: 1145360, title: 'Hades' },
          recommendations: [
            { appid: 620, title: 'Portal 2', rank: 1 },
            { appid: 588650, title: 'Dead Cells', rank: 2 },
          ],
        })
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    let user = userEvent.setup()
    await user.type(screen.getByRole('combobox', { name: /game you already enjoy/i }), 'Portal')
    await user.click(await screen.findByRole('option', { name: 'Portal Steam app 400' }))
    await screen.findByRole('link', { name: 'Open Portal 2 on Steam' })

    await user.click(screen.getByRole('button', { name: 'Mark Portal 2 as played' }))

    expect(screen.getAllByRole('heading', { level: 3 }).map((heading) => heading.textContent)).toEqual([
      'Half-Life 2',
      'Portal 2',
    ])
    expect(screen.getByText('#01')).toBeInTheDocument()
    expect(window.localStorage.getItem('next-play:played-appids')).toBe('[620]')

    cleanup()
    render(<App />)
    user = userEvent.setup()
    await user.type(screen.getByRole('combobox', { name: /game you already enjoy/i }), 'Hades')
    await user.click(await screen.findByRole('option', { name: 'Hades Steam app 1145360' }))

    await waitFor(() => {
      expect(
        screen.getAllByRole('heading', { level: 3 }).map((heading) => heading.textContent),
      ).toEqual(['Dead Cells', 'Portal 2'])
    })

    await user.click(screen.getByRole('button', { name: 'Mark Portal 2 as not played' }))

    expect(screen.getAllByRole('heading', { level: 3 }).map((heading) => heading.textContent)).toEqual([
      'Portal 2',
      'Dead Cells',
    ])
    expect(window.localStorage.getItem('next-play:played-appids')).toBe('[]')
  })

  it('selects the matrix model from the debug URL parameter', async () => {
    window.history.replaceState({}, '', '/?model=matrix')
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.startsWith('/api/games/search')) {
        return jsonResponse({
          query: 'Portal',
          results: [{ appid: 400, title: 'Portal' }],
        })
      }
      if (url.startsWith('/api/games/400/recommendations')) {
        return jsonResponse({
          model: 'matrix',
          source: { appid: 400, title: 'Portal' },
          recommendations: [{ appid: 620, title: 'Portal 2', rank: 1 }],
        })
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    render(<App />)
    await user.type(screen.getByRole('combobox', { name: /game you already enjoy/i }), 'Portal')
    await user.click(await screen.findByRole('option', { name: 'Portal Steam app 400' }))
    await screen.findByRole('link', { name: 'Open Portal 2 on Steam' })

    expect(screen.getByText(/debug model: matrix/i)).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/recommendations\?.*model=matrix/),
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
  })

  it('selects the peabrain model from the debug URL parameter', async () => {
    window.history.replaceState({}, '', '/?model=peabrain')
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.startsWith('/api/games/search')) {
        return jsonResponse({
          query: 'Portal',
          results: [{ appid: 400, title: 'Portal' }],
        })
      }
      if (url.startsWith('/api/games/400/recommendations')) {
        return jsonResponse({
          model: 'peabrain',
          source: { appid: 400, title: 'Portal' },
          recommendations: [{ appid: 620, title: 'Portal 2', rank: 1 }],
        })
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    render(<App />)
    await user.type(screen.getByRole('combobox', { name: /game you already enjoy/i }), 'Portal')
    await user.click(await screen.findByRole('option', { name: 'Portal Steam app 400' }))
    await screen.findByRole('link', { name: 'Open Portal 2 on Steam' })

    expect(screen.getByText(/debug model: peabrain/i)).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/recommendations\?.*model=peabrain/),
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
  })

  it('ignores a stale recommendation response after selecting another game', async () => {
    let resolvePortalRecommendations: ((response: Response) => void) | undefined
    const portalRecommendations = new Promise<Response>((resolve) => {
      resolvePortalRecommendations = resolve
    })
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.startsWith('/api/games/search')) {
        const isHadesSearch = url.includes('q=Hades')
        return jsonResponse({
          query: isHadesSearch ? 'Hades' : 'Portal',
          results: [
            isHadesSearch
              ? { appid: 1145360, title: 'Hades' }
              : { appid: 400, title: 'Portal' },
          ],
        })
      }
      if (url.startsWith('/api/games/400/recommendations')) return portalRecommendations
      if (url.startsWith('/api/games/1145360/recommendations')) {
        return jsonResponse({
          model: 'asymmetric',
          source: { appid: 1145360, title: 'Hades' },
          recommendations: [{ appid: 588650, title: 'Dead Cells', rank: 1 }],
        })
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    render(<App />)
    const searchInput = screen.getByRole('combobox', { name: /game you already enjoy/i })
    await user.type(searchInput, 'Portal')
    await user.click(await screen.findByRole('option', { name: 'Portal Steam app 400' }))
    await waitFor(() => expect(resolvePortalRecommendations).toBeDefined())

    await user.clear(searchInput)
    await user.type(searchInput, 'Hades')
    await user.click(await screen.findByRole('option', { name: 'Hades Steam app 1145360' }))
    await screen.findByRole('link', { name: 'Open Dead Cells on Steam' })

    resolvePortalRecommendations?.(
      jsonResponse({
        model: 'asymmetric',
        source: { appid: 400, title: 'Portal' },
        recommendations: [{ appid: 620, title: 'Portal 2', rank: 1 }],
      }),
    )
    await new Promise((resolve) => window.setTimeout(resolve, 0))

    await waitFor(() => {
      expect(screen.getByRole('link', { name: 'Open Dead Cells on Steam' })).toBeInTheDocument()
      expect(screen.queryByRole('link', { name: 'Open Portal 2 on Steam' })).not.toBeInTheDocument()
    })
  })

  it('ignores a stale recommendation response after clearing the selection', async () => {
    let resolvePortalRecommendations: ((response: Response) => void) | undefined
    const portalRecommendations = new Promise<Response>((resolve) => {
      resolvePortalRecommendations = resolve
    })
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.startsWith('/api/games/search')) {
        return jsonResponse({
          query: 'Portal',
          results: [{ appid: 400, title: 'Portal' }],
        })
      }
      if (url.startsWith('/api/games/400/recommendations')) return portalRecommendations
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    render(<App />)
    await user.type(screen.getByRole('combobox', { name: /game you already enjoy/i }), 'Portal')
    await user.click(await screen.findByRole('option', { name: 'Portal Steam app 400' }))
    await waitFor(() => expect(resolvePortalRecommendations).toBeDefined())

    await user.click(screen.getByRole('button', { name: 'Clear' }))
    resolvePortalRecommendations?.(
      jsonResponse({
        model: 'symmetric',
        source: { appid: 400, title: 'Portal' },
        recommendations: [{ appid: 620, title: 'Portal 2', rank: 1 }],
      }),
    )

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: 'Choose a game above to reveal what comes next.' }),
      ).toBeInTheDocument()
      expect(screen.queryByRole('link', { name: 'Open Portal 2 on Steam' })).not.toBeInTheDocument()
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
