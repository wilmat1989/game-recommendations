from fastapi.testclient import TestClient

from game_recommender.app import create_app
from game_recommender.repository import GameRepository


def test_health_reports_real_fixture_counts(repository: GameRepository) -> None:
    with TestClient(create_app(repository=repository)) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "lookup_games": 7,
        "recommendation_sources": 3,
    }


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
        "source": {"appid": 100, "title": "Alpha"},
        "recommendations": [
            {"appid": 300, "title": "Other Game", "rank": 1},
            {"appid": 200, "title": "Portal", "rank": 2},
        ],
    }


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
