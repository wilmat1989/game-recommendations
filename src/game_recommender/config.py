"""Application configuration and environment settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime paths and environment selection."""

    app_env: str = "development"
    game_lookup_path: Path = PROJECT_ROOT / "data" / "game_lookup.parquet"
    game_recommendations_path: Path = PROJECT_ROOT / "data" / "game_recommendation_lists.parquet"
    game_recommendations_asymmetric_path: Path = (
        PROJECT_ROOT / "data" / "game_recommendation_lists_asymmetric.parquet"
    )
    game_recommendations_matrix_path: Path = (
        PROJECT_ROOT / "data" / "game_recommendation_lists_matrix.parquet"
    )
    game_recommendations_peabrain_path: Path = (
        PROJECT_ROOT / "data" / "game_recommendation_lists_peabrain.parquet"
    )
    frontend_dist_path: Path = PROJECT_ROOT / "frontend" / "dist"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
