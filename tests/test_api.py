from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from fastapi.testclient import TestClient

from game_recommender.app import create_app
from game_recommender.config import Settings
from game_recommender.repository import DataValidationError, GameRepository


def test_health_reports_real_fixture_counts(repository: GameRepository) -> None:
    with TestClient(create_app(repository=repository)) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "lookup_games": 7,
        "recommendation_sources": 3,
    }


def test_serves_production_frontend_and_assets(
    repository: GameRepository,
    tmp_path: Path,
) -> None:
    frontend_dist = tmp_path / "frontend-dist"
    assets = frontend_dist / "assets"
    assets.mkdir(parents=True)
    (frontend_dist / "index.html").write_text(
        '<div id="root"></div><script src="/assets/app.js"></script>',
        encoding="utf-8",
    )
    (assets / "app.js").write_text("console.log('ready')", encoding="utf-8")
    settings = Settings(frontend_dist_path=frontend_dist)

    with TestClient(create_app(settings=settings, repository=repository)) as client:
        root_response = client.get("/")
        asset_response = client.get("/assets/app.js")

    assert root_response.status_code == 200
    assert root_response.headers["content-type"].startswith("text/html")
    assert '<div id="root"></div>' in root_response.text
    assert asset_response.status_code == 200
    assert asset_response.text == "console.log('ready')"


def test_missing_frontend_build_keeps_api_available(
    repository: GameRepository,
    tmp_path: Path,
) -> None:
    settings = Settings(frontend_dist_path=tmp_path / "missing")

    with TestClient(create_app(settings=settings, repository=repository)) as client:
        root_response = client.get("/")
        health_response = client.get("/api/health")

    assert root_response.status_code == 404
    assert health_response.status_code == 200


def test_production_requires_frontend_build(
    repository: GameRepository,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_env="production",
        frontend_dist_path=tmp_path / "missing",
    )

    with pytest.raises(RuntimeError, match="frontend build"):
        create_app(settings=settings, repository=repository)


def test_search_endpoint(repository: GameRepository) -> None:
    with TestClient(create_app(repository=repository)) as client:
        response = client.get("/api/games/search", params={"q": "PoRtAl"})

    assert response.status_code == 200
    assert response.json() == {
        "query": "PoRtAl",
        "results": [
            {"appid": 200, "title": "Portal"},
            {"appid": 201, "title": "Portal 2"},
            {"appid": 202, "title": "My Portal Collection"},
        ],
    }


def test_search_rejects_blank_or_short_query(repository: GameRepository) -> None:
    with TestClient(create_app(repository=repository)) as client:
        short_response = client.get("/api/games/search", params={"q": "p"})
        blank_response = client.get("/api/games/search", params={"q": "  "})

    assert short_response.status_code == 422
    assert blank_response.status_code == 422


def test_recommendation_endpoint_preserves_model_order(repository: GameRepository) -> None:
    with TestClient(create_app(repository=repository)) as client:
        response = client.get("/api/games/100/recommendations", params={"limit": 10})

    assert response.status_code == 200
    assert response.json() == {
        "model": "symmetric",
        "source": {"appid": 100, "title": "Alpha"},
        "recommendations": [
            {"appid": 300, "title": "Other Game", "rank": 1},
            {"appid": 200, "title": "Portal", "rank": 3},
        ],
    }


def test_recommendation_model_can_be_selected(
    repository: GameRepository,
    tmp_path: Path,
) -> None:
    symmetric_path = tmp_path / "symmetric.parquet"
    pq.write_table(
        pa.table(
            {
                "appid": pa.array([100], type=pa.uint32()),
                "recommendations": pa.array([[200, 300]], type=pa.list_(pa.uint32())),
            }
        ),
        symmetric_path,
    )
    symmetric_repository = GameRepository(repository.lookup_path, symmetric_path)
    matrix_path = tmp_path / "matrix.parquet"
    pq.write_table(
        pa.table(
            {
                "appid": pa.array([100], type=pa.uint32()),
                "recommendations": pa.array([[400, 200]], type=pa.list_(pa.uint32())),
            }
        ),
        matrix_path,
    )
    matrix_repository = GameRepository(repository.lookup_path, matrix_path)
    peabrain_path = tmp_path / "peabrain.parquet"
    pq.write_table(
        pa.table(
            {
                "appid": pa.array([100], type=pa.uint32()),
                "recommendations": pa.array([[201, 400]], type=pa.list_(pa.uint32())),
            }
        ),
        peabrain_path,
    )
    peabrain_repository = GameRepository(repository.lookup_path, peabrain_path)

    with TestClient(
        create_app(
            model_repositories={
                "asymmetric": repository,
                "symmetric": symmetric_repository,
                "matrix": matrix_repository,
                "peabrain": peabrain_repository,
            }
        )
    ) as client:
        default_response = client.get("/api/games/100/recommendations")
        asymmetric_response = client.get(
            "/api/games/100/recommendations",
            params={"model": "asymmetric"},
        )
        symmetric_response = client.get(
            "/api/games/100/recommendations",
            params={"model": "symmetric"},
        )
        matrix_response = client.get(
            "/api/games/100/recommendations",
            params={"model": "matrix"},
        )
        peabrain_response = client.get(
            "/api/games/100/recommendations",
            params={"model": "peabrain"},
        )
        invalid_response = client.get(
            "/api/games/100/recommendations",
            params={"model": "unknown"},
        )

    assert default_response.status_code == 200
    assert default_response.json()["model"] == "symmetric"
    assert [game["appid"] for game in default_response.json()["recommendations"]] == [
        200,
        300,
    ]
    assert asymmetric_response.status_code == 200
    assert asymmetric_response.json()["model"] == "asymmetric"
    assert [game["appid"] for game in asymmetric_response.json()["recommendations"]] == [
        300,
        200,
    ]
    assert symmetric_response.status_code == 200
    assert symmetric_response.json()["model"] == "symmetric"
    assert [game["appid"] for game in symmetric_response.json()["recommendations"]] == [
        200,
        300,
    ]
    assert matrix_response.status_code == 200
    assert matrix_response.json()["model"] == "matrix"
    assert [game["appid"] for game in matrix_response.json()["recommendations"]] == [
        400,
        200,
    ]
    assert peabrain_response.status_code == 200
    assert peabrain_response.json()["model"] == "peabrain"
    assert [game["appid"] for game in peabrain_response.json()["recommendations"]] == [
        201,
        400,
    ]
    assert invalid_response.status_code == 422


@pytest.mark.parametrize("unexpected_model", [None, "unknown"])
def test_model_repositories_require_exact_allowlist(
    repository: GameRepository,
    unexpected_model: str | None,
) -> None:
    repositories = {
        "asymmetric": repository,
        "symmetric": repository,
        "matrix": repository,
        "peabrain": repository,
    }
    if unexpected_model is None:
        repositories.pop("matrix")
    else:
        repositories[unexpected_model] = repository

    with pytest.raises(ValueError, match="exactly"):
        create_app(model_repositories=repositories)  # type: ignore[arg-type]


@pytest.mark.parametrize("broken_model", ["asymmetric", "matrix", "peabrain"])
def test_startup_validates_non_default_model_repositories(
    repository: GameRepository,
    tmp_path: Path,
    broken_model: str,
) -> None:
    repositories = {
        "asymmetric": repository,
        "symmetric": repository,
        "matrix": repository,
        "peabrain": repository,
    }
    repositories[broken_model] = GameRepository(
        repository.lookup_path,
        tmp_path / f"missing-{broken_model}.parquet",
    )

    with (
        pytest.raises(DataValidationError, match="does not exist"),
        TestClient(create_app(model_repositories=repositories)),  # type: ignore[arg-type]
    ):
        pass


def test_known_game_without_recommendations_returns_empty_list(
    repository: GameRepository,
) -> None:
    with TestClient(create_app(repository=repository)) as client:
        response = client.get("/api/games/400/recommendations")

    assert response.status_code == 200
    assert response.json()["recommendations"] == []


def test_unknown_game_returns_404(repository: GameRepository) -> None:
    with TestClient(create_app(repository=repository)) as client:
        response = client.get("/api/games/999999/recommendations")

    assert response.status_code == 404
    assert response.json() == {"detail": "Game not found"}


def test_negative_appid_is_rejected(repository: GameRepository) -> None:
    with TestClient(create_app(repository=repository)) as client:
        response = client.get("/api/games/-1/recommendations")

    assert response.status_code == 422


def test_search_rejects_oversized_query_and_invalid_limits(
    repository: GameRepository,
) -> None:
    with TestClient(create_app(repository=repository)) as client:
        oversized = client.get("/api/games/search", params={"q": "x" * 101})
        zero_limit = client.get("/api/games/search", params={"q": "portal", "limit": 0})
        high_limit = client.get("/api/games/search", params={"q": "portal", "limit": 21})

    assert oversized.status_code == 422
    assert zero_limit.status_code == 422
    assert high_limit.status_code == 422


def test_recommendation_limit_boundaries(repository: GameRepository) -> None:
    with TestClient(create_app(repository=repository)) as client:
        one_result = client.get("/api/games/100/recommendations", params={"limit": 1})
        zero_limit = client.get("/api/games/100/recommendations", params={"limit": 0})
        high_limit = client.get("/api/games/100/recommendations", params={"limit": 31})

    assert one_result.status_code == 200
    assert len(one_result.json()["recommendations"]) == 1
    assert zero_limit.status_code == 422
    assert high_limit.status_code == 422
