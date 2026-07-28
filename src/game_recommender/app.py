"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from game_recommender.config import Settings
from game_recommender.repository import GameRepository
from game_recommender.routes import router


def create_app(
    settings: Settings | None = None,
    repository: GameRepository | None = None,
) -> FastAPI:
    """Create an application with injectable settings and data access."""

    runtime_settings = settings or Settings()
    runtime_repository = repository or GameRepository(
        runtime_settings.game_lookup_path,
        runtime_settings.game_recommendations_path,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.data_stats = runtime_repository.validate_data()
        yield

    application = FastAPI(
        title="Steam Next-Game Recommendations",
        description=(
            "Search for a Steam game and retrieve an ordered list of games "
            "the player is likely to enjoy next."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.repository = runtime_repository
    application.include_router(router)
    return application


app = create_app()
