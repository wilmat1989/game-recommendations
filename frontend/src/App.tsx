import { useEffect, useRef, useState } from 'react'
import { getRecommendations, searchGames } from './api'
import type { GameSummary, RecommendationItem, RecommendationResponse } from './types'
import { useDebouncedValue } from './useDebouncedValue'
import './App.css'

type RequestState = 'idle' | 'loading' | 'success' | 'error'

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4.25 4.25" />
    </svg>
  )
}

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 12h14M14 7l5 5-5 5" />
    </svg>
  )
}

function initials(title: string) {
  return title
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase())
    .join('')
}

function RecommendationCard({ game }: { game: RecommendationItem }) {
  const [imageFailed, setImageFailed] = useState(false)
  const [imageLoaded, setImageLoaded] = useState(false)
  const rank = String(game.rank).padStart(2, '0')
  const steamUrl = `https://store.steampowered.com/app/${game.appid}`
  const imageUrl = `https://cdn.akamai.steamstatic.com/steam/apps/${game.appid}/header.jpg`

  return (
    <article className="game-card">
      <a
        className="game-card__link"
        href={steamUrl}
        target="_blank"
        rel="noreferrer"
        aria-label={`Open ${game.title} on Steam`}
      >
        <div className="game-card__art">
          <span className="game-card__initials" aria-hidden="true">
            {initials(game.title)}
          </span>
          {!imageFailed && (
            <img
              className={imageLoaded ? 'is-loaded' : ''}
              src={imageUrl}
              alt=""
              loading="lazy"
              onLoad={() => setImageLoaded(true)}
              onError={() => setImageFailed(true)}
            />
          )}
          <span className="game-card__rank">#{rank}</span>
          <span className="game-card__open">
            Steam <ArrowIcon />
          </span>
        </div>
        <div className="game-card__body">
          <h3>{game.title}</h3>
          <p>Steam app {game.appid}</p>
        </div>
      </a>
    </article>
  )
}

function App() {
  const [query, setQuery] = useState('')
  const [selectedGame, setSelectedGame] = useState<GameSummary | null>(null)
  const [searchResults, setSearchResults] = useState<GameSummary[]>([])
  const [searchState, setSearchState] = useState<RequestState>('idle')
  const [searchMessage, setSearchMessage] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [activeResult, setActiveResult] = useState(-1)
  const [recommendationState, setRecommendationState] = useState<RequestState>('idle')
  const [recommendationData, setRecommendationData] =
    useState<RecommendationResponse | null>(null)
  const [recommendationMessage, setRecommendationMessage] = useState('')
  const searchRequestGeneration = useRef(0)
  const debouncedQuery = useDebouncedValue(query, 250)

  useEffect(() => {
    const normalizedQuery = debouncedQuery.trim()
    if (normalizedQuery !== query.trim()) return
    if (normalizedQuery.length < 2) {
      setSearchResults([])
      setSearchState('idle')
      setSearchMessage('')
      return
    }
    if (selectedGame && normalizedQuery === selectedGame.title) return

    const controller = new AbortController()
    const requestGeneration = ++searchRequestGeneration.current
    setSearchState('loading')
    setSearchMessage('')

    searchGames(normalizedQuery, 8, controller.signal)
      .then((response) => {
        if (requestGeneration !== searchRequestGeneration.current) return
        setSearchResults(response.results)
        setSearchState('success')
        setSearchOpen(true)
        setActiveResult(response.results.length > 0 ? 0 : -1)
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        if (requestGeneration !== searchRequestGeneration.current) return
        setSearchResults([])
        setSearchState('error')
        setSearchMessage('Search is unavailable. Make sure the API is running and try again.')
        setSearchOpen(true)
      })

    return () => controller.abort()
  }, [debouncedQuery, query, selectedGame])

  useEffect(() => {
    if (!selectedGame) return

    const controller = new AbortController()
    setRecommendationState('loading')
    setRecommendationData(null)
    setRecommendationMessage('')

    getRecommendations(selectedGame.appid, 12, controller.signal)
      .then((response) => {
        setRecommendationData(response)
        setRecommendationState('success')
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setRecommendationState('error')
        setRecommendationMessage('Recommendations could not be loaded. Please try again.')
      })

    return () => controller.abort()
  }, [selectedGame])

  function updateQuery(value: string) {
    searchRequestGeneration.current += 1
    setQuery(value)
    setSearchResults([])
    setSearchState('idle')
    setSearchMessage('')
    setSearchOpen(true)
    setActiveResult(-1)
    if (selectedGame && value !== selectedGame.title) {
      setSelectedGame(null)
      setRecommendationData(null)
      setRecommendationState('idle')
    }
  }

  function selectGame(game: GameSummary) {
    searchRequestGeneration.current += 1
    setSelectedGame(game)
    setQuery(game.title)
    setSearchOpen(false)
    setSearchResults([])
    setActiveResult(-1)
  }

  function clearSelection() {
    searchRequestGeneration.current += 1
    setQuery('')
    setSelectedGame(null)
    setSearchResults([])
    setSearchOpen(false)
    setSearchState('idle')
    setRecommendationData(null)
    setRecommendationState('idle')
  }

  function handleSearchKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (!searchOpen || searchResults.length === 0) {
      if (event.key === 'ArrowDown' && searchResults.length > 0) {
        event.preventDefault()
        setSearchOpen(true)
        setActiveResult(0)
      }
      return
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActiveResult((current) => (current + 1) % searchResults.length)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveResult((current) => (current <= 0 ? searchResults.length - 1 : current - 1))
    } else if (event.key === 'Enter' && activeResult >= 0) {
      event.preventDefault()
      selectGame(searchResults[activeResult])
    } else if (event.key === 'Escape') {
      setSearchOpen(false)
      setActiveResult(-1)
    }
  }

  const showDropdown =
    searchOpen && query.trim().length >= 2 && (searchState !== 'idle' || searchResults.length > 0)
  const recommendationCount = recommendationData?.recommendations.length ?? 0

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="/" aria-label="Next Play home">
          <span className="brand__mark" aria-hidden="true">
            NP
          </span>
          <span>NEXT PLAY</span>
        </a>
        <div className="model-note">
          <span className="status-dot" aria-hidden="true" />
          Review-powered recommendations
        </div>
      </header>

      <main>
        <section className="hero-section" aria-labelledby="hero-title">
          <div className="eyebrow">
            <span>01</span>
            Pick a game you already love
          </div>
          <h1 id="hero-title">
            Your next favorite game is <em>already in the data.</em>
          </h1>
          <p className="hero-copy">
            Start with one Steam game you enjoyed. We’ll use patterns from millions of player
            reviews to build your ranked shortlist.
          </p>

          <div
            className="search-block"
            onBlur={(event) => {
              if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget)) {
                setSearchOpen(false)
                setActiveResult(-1)
              }
            }}
          >
            <label htmlFor="game-search">Game you already enjoy</label>
            <div className="search-control">
              <span className="search-control__icon">
                <SearchIcon />
              </span>
              <input
                id="game-search"
                type="search"
                value={query}
                placeholder="Try Portal, Hades, Stardew Valley…"
                maxLength={100}
                autoComplete="off"
                role="combobox"
                aria-autocomplete="list"
                aria-expanded={showDropdown}
                aria-controls={showDropdown ? 'game-search-results' : undefined}
                aria-activedescendant={
                  showDropdown && activeResult >= 0
                    ? `game-result-${searchResults[activeResult]?.appid}`
                    : undefined
                }
                onChange={(event) => updateQuery(event.target.value)}
                onFocus={() => {
                  if (query.trim().length >= 2) setSearchOpen(true)
                }}
                onKeyDown={handleSearchKeyDown}
              />
              {query && (
                <button className="clear-button" type="button" onClick={clearSelection}>
                  Clear
                </button>
              )}
            </div>

            <div className="search-status" aria-live="polite">
              {searchState === 'loading' && 'Searching the Steam catalog…'}
              {searchState === 'success' && searchResults.length === 0 && 'No matching games found.'}
            </div>

            {showDropdown && (
              <div className="search-dropdown" id="game-search-results" role="listbox">
                {searchState === 'loading' && (
                  <div className="search-dropdown__message">
                    <span className="spinner" aria-hidden="true" /> Searching…
                  </div>
                )}
                {searchState === 'error' && (
                  <div className="search-dropdown__message search-dropdown__message--error" role="alert">
                    {searchMessage}
                  </div>
                )}
                {searchState === 'success' && searchResults.length === 0 && (
                  <div className="search-dropdown__message">No matching games found.</div>
                )}
                {searchState === 'success' &&
                  searchResults.map((game, index) => (
                    <button
                      id={`game-result-${game.appid}`}
                      key={game.appid}
                      type="button"
                      role="option"
                      aria-selected={index === activeResult}
                      aria-label={`${game.title} Steam app ${game.appid}`}
                      className={index === activeResult ? 'is-active' : ''}
                      onMouseDown={(event) => event.preventDefault()}
                      onMouseEnter={() => setActiveResult(index)}
                      onClick={() => selectGame(game)}
                    >
                      <span>{game.title}</span>
                      <small>APP {game.appid}</small>
                    </button>
                  ))}
              </div>
            )}
          </div>

          <div className="dataset-strip" aria-label="Dataset summary">
            <div>
              <strong>74,780</strong>
              <span>searchable titles</span>
            </div>
            <div>
              <strong>59,745</strong>
              <span>modeled games</span>
            </div>
            <div>
              <strong>100M+</strong>
              <span>source reviews</span>
            </div>
          </div>
        </section>

        <section className="results-section" aria-live="polite">
          {recommendationState === 'idle' && (
            <div className="empty-state">
              <span className="empty-state__number">02</span>
              <div>
                <p className="section-kicker">Your ranked shortlist</p>
                <h2>Choose a game above to reveal what comes next.</h2>
              </div>
              <div className="empty-state__tracks" aria-hidden="true">
                <span />
                <span />
                <span />
              </div>
            </div>
          )}

          {recommendationState === 'loading' && (
            <div className="recommendation-loading" role="status">
              <span className="spinner spinner--large" aria-hidden="true" />
              <div>
                <p className="section-kicker">Reading the recommendation matrix</p>
                <h2>Building a shortlist for {selectedGame?.title}…</h2>
              </div>
            </div>
          )}

          {recommendationState === 'error' && (
            <div className="results-error" role="alert">
              <p className="section-kicker">The data path broke</p>
              <h2>{recommendationMessage}</h2>
              <button
                type="button"
                onClick={() => selectedGame && setSelectedGame({ ...selectedGame })}
              >
                Try again
              </button>
            </div>
          )}

          {recommendationState === 'success' && recommendationData && (
            <>
              <div className="results-heading">
                <div>
                  <p className="section-kicker">02 / Your ranked shortlist</p>
                  <h2>
                    If you liked <span>{recommendationData.source.title}</span>, try these next.
                  </h2>
                </div>
                <p className="results-count">
                  <strong>{String(recommendationCount).padStart(2, '0')}</strong>
                  recommendations
                </p>
              </div>

              {recommendationCount > 0 ? (
                <div className="recommendation-grid">
                  {recommendationData.recommendations.map((game) => (
                    <RecommendationCard key={game.appid} game={game} />
                  ))}
                </div>
              ) : (
                <div className="no-results">
                  <h3>No ranked recommendations are available for this game yet.</h3>
                  <p>Try another title from the search box.</p>
                </div>
              )}
            </>
          )}
        </section>
      </main>

      <footer>
        <p>
          Built from co-review patterns. Recommendations estimate what you may enjoy next — not
          what looks most similar.
        </p>
        <p>Independent portfolio project · Not affiliated with Valve</p>
      </footer>
    </div>
  )
}

export default App
