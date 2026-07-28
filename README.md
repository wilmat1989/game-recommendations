# Steam Next-Game Recommendations

A portfolio application that recommends the next game a player is likely to
enjoy based on a game they already liked. The recommendation objective is
likelihood of enjoyment, not genre or content similarity.

The current repository contains the processed recommendation artifacts,
model-building notebooks, and a tested FastAPI backend. The frontend is under
development.

## Project Structure

```text
data/                  Application-ready Parquet artifacts
notebooks/             Review processing and recommendation-build notebooks
scripts/               Repeatable data validation and build scripts
src/game_recommender/  FastAPI backend package
frontend/              Browser application
tests/                  Automated tests
```

## Data

The application uses these derived artifacts:

- `data/game_lookup.parquet` maps Steam app IDs to game titles.
- `data/game_recommendation_lists.parquet` maps each source app ID to an
  ordered recommendation list.

They were generated from the MIT-licensed
[100 Million+ Steam Reviews](https://www.kaggle.com/datasets/kieranpoc/steam-reviews)
dataset published by KieranPO'C on Kaggle. The raw review dataset is not
included in this repository.

See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for the source,
transformations, attribution, and upstream license information. A copy of the
upstream MIT terms is stored in
[`licenses/steam-reviews-MIT.txt`](licenses/steam-reviews-MIT.txt).

## Licensing

Original application and processing code is licensed under the
[MIT License](LICENSE), copyright Wilson Matos.

The included Parquet files are derived from the third-party dataset identified
above and retain its attribution and published MIT terms. The root code license
does not replace that third-party notice.

Steam and related marks belong to their respective owners. This project is not
affiliated with or endorsed by Valve Corporation.

## Local API

Install the locked dependencies:

```bash
uv sync
```

Validate the serving data:

```bash
uv run python scripts/validate_data.py
```

Run the API:

```bash
uv run uvicorn game_recommender.app:app --reload
```

Open `http://localhost:8000/docs` for FastAPI's interactive documentation.

Available endpoints:

- `GET /api/health`
- `GET /api/games/search?q=portal&limit=10`
- `GET /api/games/400/recommendations?limit=12`

Run automated checks:

```bash
uv run pytest
uv run ruff check .
```
