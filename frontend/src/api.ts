import type { RecommendationResponse, SearchResponse } from './types'

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function requestJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, {
    headers: { Accept: 'application/json' },
    signal,
  })

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) message = body.detail
    } catch {
      // The status code still gives callers a useful failure when a response is not JSON.
    }
    throw new ApiError(message, response.status)
  }

  return (await response.json()) as T
}

export function searchGames(
  query: string,
  limit = 8,
  signal?: AbortSignal,
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query, limit: String(limit) })
  return requestJson<SearchResponse>(`/api/games/search?${params}`, signal)
}

export function getRecommendations(
  appid: number,
  limit = 12,
  signal?: AbortSignal,
): Promise<RecommendationResponse> {
  const params = new URLSearchParams({ limit: String(limit) })
  return requestJson<RecommendationResponse>(
    `/api/games/${appid}/recommendations?${params}`,
    signal,
  )
}
