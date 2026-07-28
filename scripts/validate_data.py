"""Validate the production recommendation artifacts and print a JSON report."""

from __future__ import annotations

import json
from dataclasses import asdict

from game_recommender.config import Settings
from game_recommender.repository import DataValidationError, GameRepository


def main() -> int:
    settings = Settings()
    repository = GameRepository(
        settings.game_lookup_path,
        settings.game_recommendations_path,
    )

    try:
        stats = repository.validate_data()
    except DataValidationError as error:
        print(json.dumps({"status": "failed", "error": str(error)}, indent=2))
        return 1

    result = {"status": "passed", **asdict(stats)}
    if stats.unresolved_sources or stats.unresolved_target_links:
        result["warning"] = (
            "Unresolved IDs will be omitted from API results; source artifacts were not modified."
        )

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
