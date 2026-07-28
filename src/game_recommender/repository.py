"""Data access for game titles and recommendation lists."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq


class DataValidationError(RuntimeError):
    """Raised when serving data is missing or violates its contract."""


@dataclass(frozen=True)
class Game:
    appid: int
    title: str


@dataclass(frozen=True)
class RankedGame(Game):
    rank: int


@dataclass(frozen=True)
class DataStats:
    lookup_games: int
    recommendation_sources: int
    recommendation_links: int
    unresolved_sources: int
    unresolved_target_links: int
    self_recommendations: int
    duplicate_recommendations: int


class GameRepository:
    """Query immutable Parquet recommendation artifacts through DuckDB."""

    LOOKUP_COLUMNS: ClassVar[frozenset[str]] = frozenset({"appid", "game"})
    RECOMMENDATION_COLUMNS: ClassVar[frozenset[str]] = frozenset({"appid", "recommendations"})

    def __init__(self, lookup_path: Path, recommendations_path: Path) -> None:
        self.lookup_path = Path(lookup_path).resolve()
        self.recommendations_path = Path(recommendations_path).resolve()

    @contextmanager
    def _connection(self) -> Iterator[duckdb.DuckDBPyConnection]:
        connection = duckdb.connect()
        try:
            yield connection
        finally:
            connection.close()

    def _validate_files_and_schema(self) -> None:
        for path in (self.lookup_path, self.recommendations_path):
            if not path.is_file():
                raise DataValidationError(f"Required data file does not exist: {path}")

        try:
            lookup_schema = pq.read_schema(self.lookup_path)
            recommendation_schema = pq.read_schema(self.recommendations_path)
            lookup_columns = set(lookup_schema.names)
            recommendation_columns = set(recommendation_schema.names)
        except Exception as error:
            raise DataValidationError(f"Unable to read Parquet schema: {error}") from error

        missing_lookup = self.LOOKUP_COLUMNS - lookup_columns
        if missing_lookup:
            raise DataValidationError(f"Lookup file is missing columns: {sorted(missing_lookup)}")

        missing_recommendations = self.RECOMMENDATION_COLUMNS - recommendation_columns
        if missing_recommendations:
            raise DataValidationError(
                f"Recommendation file is missing columns: {sorted(missing_recommendations)}"
            )

        lookup_appid_type = lookup_schema.field("appid").type
        lookup_game_type = lookup_schema.field("game").type
        recommendation_appid_type = recommendation_schema.field("appid").type
        recommendation_list_type = recommendation_schema.field("recommendations").type
        if not pa.types.is_unsigned_integer(lookup_appid_type) or not pa.types.is_string(
            lookup_game_type
        ):
            raise DataValidationError(
                "Lookup columns must be unsigned integer appid and string game"
            )
        if not pa.types.is_unsigned_integer(recommendation_appid_type):
            raise DataValidationError("Recommendation appid must be an unsigned integer")
        if not pa.types.is_list(recommendation_list_type) or not pa.types.is_unsigned_integer(
            recommendation_list_type.value_type
        ):
            raise DataValidationError("Recommendations must be a list of unsigned integer app IDs")

    def validate_data(self) -> DataStats:
        """Validate structural invariants and report resolvable data gaps."""

        self._validate_files_and_schema()
        lookup = self.lookup_path.as_posix()
        recommendations = self.recommendations_path.as_posix()

        with self._connection() as connection:
            lookup_row = connection.execute(
                """
                SELECT
                    COUNT(*) AS row_count,
                    COUNT(DISTINCT appid) AS distinct_appids,
                    COUNT(*) FILTER (
                        WHERE appid IS NULL OR game IS NULL OR length(trim(game)) = 0
                    ) AS invalid_rows
                FROM read_parquet(?)
                """,
                [lookup],
            ).fetchone()
            recommendation_row = connection.execute(
                """
                SELECT
                    COUNT(*) AS row_count,
                    COUNT(DISTINCT appid) AS distinct_appids,
                    COALESCE(SUM(array_length(recommendations)), 0) AS link_count,
                    COUNT(*) FILTER (
                        WHERE appid IS NULL OR recommendations IS NULL
                    ) AS invalid_rows,
                    COALESCE(MAX(array_length(recommendations)), 0) AS max_list_length
                FROM read_parquet(?)
                """,
                [recommendations],
            ).fetchone()

            assert lookup_row is not None
            assert recommendation_row is not None

            if lookup_row[0] != lookup_row[1]:
                raise DataValidationError("Lookup app IDs must be unique")
            if lookup_row[2] != 0:
                raise DataValidationError("Lookup contains null IDs or blank titles")
            if recommendation_row[0] != recommendation_row[1]:
                raise DataValidationError("Recommendation source app IDs must be unique")
            if recommendation_row[3] != 0:
                raise DataValidationError("Recommendations contain null source IDs or arrays")
            if recommendation_row[4] > 30:
                raise DataValidationError("A recommendation list contains more than 30 entries")

            issue_row = connection.execute(
                """
                WITH expanded AS (
                    SELECT
                        source.appid AS source_appid,
                        item.recommended_appid
                    FROM read_parquet(?) AS source,
                    UNNEST(source.recommendations) AS item(recommended_appid)
                ),
                duplicate_pairs AS (
                    SELECT source_appid, recommended_appid, COUNT(*) AS occurrences
                    FROM expanded
                    GROUP BY source_appid, recommended_appid
                    HAVING COUNT(*) > 1
                )
                SELECT
                    (
                        SELECT COUNT(*)
                        FROM read_parquet(?) AS source
                        LEFT JOIN read_parquet(?) AS lookup USING (appid)
                        WHERE lookup.appid IS NULL
                    ) AS unresolved_sources,
                    COUNT(*) FILTER (
                        WHERE lookup.appid IS NULL
                          AND expanded.recommended_appid IS NOT NULL
                    ) AS unresolved_targets,
                    COUNT(*) FILTER (
                        WHERE expanded.recommended_appid IS NULL
                    ) AS null_recommendations,
                    COUNT(*) FILTER (
                        WHERE expanded.source_appid = expanded.recommended_appid
                    ) AS self_recommendations,
                    (
                        SELECT COALESCE(SUM(occurrences - 1), 0)
                        FROM duplicate_pairs
                    ) AS duplicate_recommendations
                FROM expanded
                LEFT JOIN read_parquet(?) AS lookup
                    ON expanded.recommended_appid = lookup.appid
                """,
                [recommendations, recommendations, lookup, lookup],
            ).fetchone()

            assert issue_row is not None
            if issue_row[2] != 0:
                raise DataValidationError("Recommendation arrays contain null app IDs")
            if issue_row[3] != 0:
                raise DataValidationError("Recommendations contain self-references")
            if issue_row[4] != 0:
                raise DataValidationError("Recommendation lists contain duplicate app IDs")

        return DataStats(
            lookup_games=int(lookup_row[0]),
            recommendation_sources=int(recommendation_row[0]),
            recommendation_links=int(recommendation_row[2]),
            unresolved_sources=int(issue_row[0]),
            unresolved_target_links=int(issue_row[1]),
            self_recommendations=int(issue_row[3]),
            duplicate_recommendations=int(issue_row[4]),
        )

    def get_game(self, appid: int) -> Game | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT appid, game
                FROM read_parquet(?)
                WHERE appid = ?
                LIMIT 1
                """,
                [self.lookup_path.as_posix(), appid],
            ).fetchone()

        if row is None:
            return None
        return Game(appid=int(row[0]), title=str(row[1]))

    def search_games(self, query: str, limit: int) -> list[Game]:
        normalized_query = query.strip()
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT appid, game
                FROM read_parquet(?)
                WHERE contains(lower(game), lower(?))
                ORDER BY
                    CASE
                        WHEN lower(game) = lower(?) THEN 0
                        WHEN starts_with(lower(game), lower(?)) THEN 1
                        ELSE 2
                    END,
                    length(game),
                    lower(game),
                    appid
                LIMIT ?
                """,
                [
                    self.lookup_path.as_posix(),
                    normalized_query,
                    normalized_query,
                    normalized_query,
                    limit,
                ],
            ).fetchall()

        return [Game(appid=int(row[0]), title=str(row[1])) for row in rows]

    def get_recommendations(self, appid: int, limit: int) -> list[RankedGame]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                WITH source AS (
                    SELECT recommendations
                    FROM read_parquet(?)
                    WHERE appid = ?
                ),
                ranked AS (
                    SELECT
                        item.recommended_appid,
                        item.rank
                    FROM source,
                    UNNEST(source.recommendations) WITH ORDINALITY
                        AS item(recommended_appid, rank)
                )
                SELECT
                    ranked.recommended_appid,
                    lookup.game,
                    ranked.rank
                FROM ranked
                INNER JOIN read_parquet(?) AS lookup
                    ON ranked.recommended_appid = lookup.appid
                ORDER BY ranked.rank
                LIMIT ?
                """,
                [
                    self.recommendations_path.as_posix(),
                    appid,
                    self.lookup_path.as_posix(),
                    limit,
                ],
            ).fetchall()

        return [RankedGame(appid=int(row[0]), title=str(row[1]), rank=int(row[2])) for row in rows]
