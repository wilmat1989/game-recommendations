"""API request and response models."""

from typing import Literal

from pydantic import BaseModel

RecommendationModel = Literal["asymmetric", "symmetric", "matrix", "peabrain"]


class GameSummary(BaseModel):
    appid: int
    title: str


class SearchResponse(BaseModel):
    query: str
    results: list[GameSummary]


class RecommendationItem(GameSummary):
    rank: int


class RecommendationResponse(BaseModel):
    model: RecommendationModel
    source: GameSummary
    recommendations: list[RecommendationItem]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    lookup_games: int
    recommendation_sources: int
