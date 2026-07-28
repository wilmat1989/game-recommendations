from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from game_recommender.repository import GameRepository


@pytest.fixture
def parquet_files(tmp_path: Path) -> tuple[Path, Path]:
    lookup_path = tmp_path / "game_lookup.parquet"
    recommendations_path = tmp_path / "game_recommendation_lists.parquet"

    lookup = pa.table(
        {
            "appid": pa.array([100, 101, 200, 201, 202, 300, 400], type=pa.uint32()),
            "game": [
                "Alpha",
                "Alpha",
                "Portal",
                "Portal 2",
                "My Portal Collection",
                "Other Game",
                "Lonely Game",
            ],
        }
    )
    recommendations = pa.table(
        {
            "appid": pa.array([100, 200, 777], type=pa.uint32()),
            "recommendations": pa.array(
                [[300, 200, 999], [201, 300], [200]],
                type=pa.list_(pa.uint32()),
            ),
        }
    )

    pq.write_table(lookup, lookup_path)
    pq.write_table(recommendations, recommendations_path)
    return lookup_path, recommendations_path


@pytest.fixture
def repository(parquet_files: tuple[Path, Path]) -> GameRepository:
    lookup_path, recommendations_path = parquet_files
    return GameRepository(lookup_path, recommendations_path)
