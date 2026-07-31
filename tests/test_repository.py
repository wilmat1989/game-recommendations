from game_recommender.repository import DataValidationError, GameRepository


def test_search_prioritizes_exact_then_prefix_then_substring(
    repository: GameRepository,
) -> None:
    results = repository.search_games("PoRtAl", limit=10)

    assert [(game.appid, game.title) for game in results] == [
        (200, "Portal"),
        (201, "Portal 2"),
        (202, "My Portal Collection"),
    ]


def test_search_retains_duplicate_titles(repository: GameRepository) -> None:
    results = repository.search_games("alpha", limit=10)

    assert [game.appid for game in results] == [100, 101]


def test_recommendations_preserve_rank_and_omit_unknown_titles(
    repository: GameRepository,
) -> None:
    results = repository.get_recommendations(100, limit=10)

    assert [(game.appid, game.title, game.rank) for game in results] == [
        (300, "Other Game", 1),
        (200, "Portal", 3),
    ]


def test_recommendation_limit_is_applied_after_title_resolution(
    repository: GameRepository,
) -> None:
    results = repository.get_recommendations(100, limit=1)

    assert [(game.appid, game.rank) for game in results] == [(300, 1)]


def test_data_stats_report_unresolved_ids(repository: GameRepository) -> None:
    stats = repository.validate_data()

    assert stats.lookup_games == 7
    assert stats.recommendation_sources == 3
    assert stats.recommendation_links == 6
    assert stats.unresolved_sources == 1
    assert stats.unresolved_target_links == 1
    assert stats.self_recommendations == 0
    assert stats.duplicate_recommendations == 0


def test_missing_data_file_fails_clearly(tmp_path) -> None:
    repository = GameRepository(tmp_path / "missing.parquet", tmp_path / "also-missing.parquet")

    try:
        repository.validate_data()
    except DataValidationError as error:
        assert "does not exist" in str(error)
    else:
        raise AssertionError("Expected missing files to fail validation")
