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

export type RecommendationModel = 'asymmetric' | 'symmetric' | 'matrix' | 'peabrain'

export interface RecommendationResponse {
  model: RecommendationModel
  source: GameSummary
  recommendations: RecommendationItem[]
}
