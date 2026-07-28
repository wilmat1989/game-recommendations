from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from game_recommender.repository import DataValidationError, GameRepository


def write_parquets(
    tmp_path: Path,
    *,
    lookup_appids: list[int] | None = None,
    titles: list[str | None] | None = None,
    source_appids: list[int] | None = None,
    recommendation_lists: list[list[int | None] | None] | None = None,
) -> GameRepository:
    lookup_path = tmp_path / "lookup.parquet"
    recommendations_path = tmp_path / "recommendations.parquet"

    lookup_appids = lookup_appids or [1, 2]
    titles = titles or ["Game One", "Game Two"]
    source_appids = source_appids or [1]
    recommendation_lists = recommendation_lists or [[2]]

    pq.write_table(
        pa.table(
            {
                "appid": pa.array(lookup_appids, type=pa.uint32()),
                "game": pa.array(titles, type=pa.string()),
            }
        ),
        lookup_path,
    )
    pq.write_table(
        pa.table(
            {
                "appid": pa.array(source_appids, type=pa.uint32()),
                "recommendations": pa.array(
                    recommendation_lists,
                    type=pa.list_(pa.uint32()),
                ),
            }
        ),
        recommendations_path,
    )
    return GameRepository(lookup_path, recommendations_path)


def test_schema_validation_rejects_missing_lookup_column(tmp_path: Path) -> None:
    lookup_path = tmp_path / "lookup.parquet"
    recommendations_path = tmp_path / "recommendations.parquet"

    pq.write_table(
        pa.table({"appid": pa.array([1], type=pa.uint32())}),
        lookup_path,
    )
    pq.write_table(
        pa.table(
            {
                "appid": pa.array([1], type=pa.uint32()),
                "recommendations": pa.array([[2]], type=pa.list_(pa.uint32())),
            }
        ),
        recommendations_path,
    )

    repository = GameRepository(lookup_path, recommendations_path)

    with pytest.raises(DataValidationError, match="game"):
        repository.validate_data()


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {"lookup_appids": [1, 1], "titles": ["One", "Duplicate"]},
            "Lookup app IDs must be unique",
        ),
        (
            {"titles": ["Game One", "  "]},
            "null IDs or blank titles",
        ),
        (
            {"source_appids": [1, 1], "recommendation_lists": [[2], [2]]},
            "source app IDs must be unique",
        ),
        (
            {"recommendation_lists": [None]},
            "null source IDs or arrays",
        ),
        (
            {"recommendation_lists": [[None]]},
            "null app IDs",
        ),
        (
            {"recommendation_lists": [list(range(2, 33))]},
            "more than 30",
        ),
        (
            {"recommendation_lists": [[1]]},
            "self-references",
        ),
        (
            {"recommendation_lists": [[2, 2]]},
            "duplicate app IDs",
        ),
    ],
)
def test_data_contract_rejects_structural_violations(
    tmp_path: Path,
    kwargs: dict,
    message: str,
) -> None:
    repository = write_parquets(tmp_path, **kwargs)

    with pytest.raises(DataValidationError, match=message):
        repository.validate_data()


def test_data_contract_rejects_signed_appid_types(tmp_path: Path) -> None:
    lookup_path = tmp_path / "lookup.parquet"
    recommendations_path = tmp_path / "recommendations.parquet"

    pq.write_table(
        pa.table(
            {
                "appid": pa.array([-1, 2], type=pa.int32()),
                "game": ["Invalid", "Game Two"],
            }
        ),
        lookup_path,
    )
    pq.write_table(
        pa.table(
            {
                "appid": pa.array([-1], type=pa.int32()),
                "recommendations": pa.array([[2]], type=pa.list_(pa.int32())),
            }
        ),
        recommendations_path,
    )

    repository = GameRepository(lookup_path, recommendations_path)

    with pytest.raises(DataValidationError, match="unsigned integer"):
        repository.validate_data()
