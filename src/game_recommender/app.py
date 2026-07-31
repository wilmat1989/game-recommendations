"""FastAPI application entry point."""

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from game_recommender.config import Settings
from game_recommender.models import RecommendationModel
from game_recommender.repository import GameRepository
from game_recommender.routes import router


def create_app(
    settings: Settings | None = None,
    repository: GameRepository | None = None,
    model_repositories: Mapping[RecommendationModel, GameRepository] | None = None,
) -> FastAPI:
    """Create an application with injectable settings and data access."""

    runtime_settings = settings or Settings()
    if model_repositories is not None:
        runtime_model_repositories = dict(model_repositories)
    elif repository is not None:
        runtime_model_repositories = {
            "asymmetric": repository,
            "symmetric": repository,
            "matrix": repository,
            "peabrain": repository,
        }
    else:
        runtime_model_repositories = {
            "symmetric": GameRepository(
                runtime_settings.game_lookup_path,
                runtime_settings.game_recommendations_path,
            ),
            "asymmetric": GameRepository(
                runtime_settings.game_lookup_path,
                runtime_settings.game_recommendations_asymmetric_path,
            ),
            "matrix": GameRepository(
                runtime_settings.game_lookup_path,
                runtime_settings.game_recommendations_matrix_path,
            ),
            "peabrain": GameRepository(
                runtime_settings.game_lookup_path,
                runtime_settings.game_recommendations_peabrain_path,
            ),
        }
    required_models = {"asymmetric", "symmetric", "matrix", "peabrain"}
    if set(runtime_model_repositories) != required_models:
        raise ValueError(f"Model repositories must contain exactly: {sorted(required_models)}")

    runtime_repository = runtime_model_repositories["symmetric"]
    frontend_index = runtime_settings.frontend_dist_path / "index.html"
    if runtime_settings.app_env == "production" and not frontend_index.is_file():
        raise RuntimeError(
            f"Production frontend build is missing: {frontend_index}"
        )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.model_data_stats = {
            model: model_repository.validate_data()
            for model, model_repository in runtime_model_repositories.items()
        }
        app.state.data_stats = app.state.model_data_stats["symmetric"]
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
    application.state.model_repositories = runtime_model_repositories
    application.include_router(router)
    if frontend_index.is_file():
        application.mount(
            "/",
            StaticFiles(directory=runtime_settings.frontend_dist_path, html=True),
            name="frontend",
        )
    return application


app = create_app()
