# Steam Next-Game Recommendations

A portfolio application that recommends the next game a player is likely to
enjoy based on a game they already liked. The recommendation objective is
likelihood of enjoyment, not genre or content similarity.

The current repository contains the processed recommendation artifacts,
model-building notebooks, a tested FastAPI backend, and a React browser
application for game search and ranked recommendations.

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
  ordered recommendation list using the default symmetric model.
- `data/game_recommendation_lists_asymmetric.parquet` provides the comparison
  model used by debug mode.
- `data/game_recommendation_lists_matrix.parquet` provides matrix-factorization
  game-embedding recommendations used by debug mode.
- `data/game_recommendation_lists_peabrain.parquet` provides the precomputed
  Peabrain comparison model used by debug mode.

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

## Local Frontend

The browser application uses Vite, React, and TypeScript. During local
development, keep the API and frontend running in separate Git Bash windows.

Start the API from the project root:

```bash
uv run uvicorn game_recommender.app:app --reload
```

In a second Git Bash window, start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies browser requests beginning with
`/api` to the FastAPI server at `http://127.0.0.1:8000`, so no local CORS
configuration is required.

### Model debug mode

Select a recommendation artifact with an allow-listed page query parameter:

```text
http://localhost:5173/?model=asymmetric
http://localhost:5173/?model=symmetric
http://localhost:5173/?model=matrix
http://localhost:5173/?model=peabrain
```

In the production Docker stack, use the same parameters on `http://localhost`.
The page header identifies the active debug model. With no `model` parameter,
the application uses the symmetric model without showing the debug label.

The API also accepts the model directly:

```text
GET /api/games/400/recommendations?limit=12&model=asymmetric
```

Only `asymmetric`, `symmetric`, `matrix`, and `peabrain` are accepted; other
values return HTTP 422.

Run frontend checks:

```bash
cd frontend
npm run test:run
npm run lint
npm run build
```

Run automated checks:

```bash
uv run pytest
uv run ruff check .
uv run python scripts/validate_data.py
```

The validation script checks the symmetric, asymmetric, matrix, and Peabrain
runtime artifacts and exits nonzero if any selectable model is missing or invalid.

## Production Container

The production image builds the React application and serves it from FastAPI.
Caddy is the only public service; the application port remains private inside
the Docker network.

Build and run the complete stack locally:

```bash
docker compose up --detach --build
```

Open `http://localhost` and verify the API at
`http://localhost/api/health`.

Inspect or stop the stack:

```bash
docker compose ps
docker compose logs --tail=100
docker compose down
```

For a public server, copy `.env.example` to `.env` and replace the example
hostname with the application's real subdomain. Point that subdomain at the
server, forward only TCP ports 80 and 443 to it, and then start the same Compose
stack. Optionally forward UDP 443 to enable HTTP/3. Caddy obtains and renews the
HTTPS certificate automatically. Compose bounds container CPU, memory, process
count, and log-file growth for unattended operation.

Deploy an update from the server checkout with:

```bash
git pull --ff-only
docker compose up --detach --build
```
