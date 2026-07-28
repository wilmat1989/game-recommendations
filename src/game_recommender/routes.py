"""HTTP routes for search and recommendations."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status

from game_recommender.models import (
    GameSummary,
    HealthResponse,
    RecommendationItem,
    RecommendationResponse,
    SearchResponse,
)
from game_recommender.repository import GameRepository

router = APIRouter(prefix="/api")


def get_repository(request: Request) -> GameRepository:
    return request.app.state.repository


RepositoryDependency = Annotated[GameRepository, Depends(get_repository)]


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    stats = request.app.state.data_stats
    return HealthResponse(
        lookup_games=stats.lookup_games,
        recommendation_sources=stats.recommendation_sources,
    )


@router.get("/games/search", response_model=SearchResponse)
def search_games(
    repository: RepositoryDependency,
    q: Annotated[str, Query(min_length=2, max_length=100)],
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> SearchResponse:
    query = q.strip()
    if len(query) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Search query must contain at least two non-space characters",
        )

    results = repository.search_games(query, limit)
    return SearchResponse(
        query=query,
        results=[GameSummary(appid=game.appid, title=game.title) for game in results],
    )


@router.get(
    "/games/{appid}/recommendations",
    response_model=RecommendationResponse,
)
def recommendations(
    repository: RepositoryDependency,
    appid: Annotated[int, Path(ge=0)],
    limit: Annotated[int, Query(ge=1, le=30)] = 12,
) -> RecommendationResponse:
    source = repository.get_game(appid)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )

    results = repository.get_recommendations(appid, limit)
    return RecommendationResponse(
        source=GameSummary(appid=source.appid, title=source.title),
        recommendations=[
            RecommendationItem(
                appid=game.appid,
                title=game.title,
                rank=game.rank,
            )
            for game in results
        ],
    )
