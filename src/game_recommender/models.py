"""API request and response models."""

from typing import Literal

from pydantic import BaseModel


class GameSummary(BaseModel):
    appid: int
    title: str


class SearchResponse(BaseModel):
    query: str
    results: list[GameSummary]


class RecommendationItem(GameSummary):
    rank: int


class RecommendationResponse(BaseModel):
    source: GameSummary
    recommendations: list[RecommendationItem]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    lookup_games: int
    recommendation_sources: int
