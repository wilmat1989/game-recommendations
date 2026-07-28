export interface GameSummary {
  appid: number
  title: string
}

export interface SearchResponse {
  query: string
  results: GameSummary[]
}

export interface RecommendationItem extends GameSummary {
  rank: number
}

export interface RecommendationResponse {
  source: GameSummary
  recommendations: RecommendationItem[]
}
