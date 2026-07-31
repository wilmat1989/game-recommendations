"""Validate the production recommendation artifacts and print a JSON report."""

from __future__ import annotations

import json
from dataclasses import asdict

from game_recommender.config import Settings
from game_recommender.repository import DataValidationError, GameRepository


def main() -> int:
    settings = Settings()
    recommendation_paths = {
        "symmetric": settings.game_recommendations_path,
        "asymmetric": settings.game_recommendations_asymmetric_path,
        "matrix": settings.game_recommendations_matrix_path,
        "peabrain": settings.game_recommendations_peabrain_path,
    }
    model_results: dict[str, dict[str, object]] = {}

    for model, recommendations_path in recommendation_paths.items():
        repository = GameRepository(settings.game_lookup_path, recommendations_path)
        try:
            stats = repository.validate_data()
        except DataValidationError as error:
            model_results[model] = {"status": "failed", "error": str(error)}
            continue

        result: dict[str, object] = {"status": "passed", **asdict(stats)}
        if stats.unresolved_sources or stats.unresolved_target_links:
            result["warning"] = (
                "Unresolved IDs will be omitted from API results; "
                "source artifacts were not modified."
            )
        model_results[model] = result

    status = (
        "passed"
        if all(result["status"] == "passed" for result in model_results.values())
        else "failed"
    )
    print(json.dumps({"status": status, "models": model_results}, indent=2))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
