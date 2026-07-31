# Third-Party Notices

## 100 Million+ Steam Reviews

This project uses derived data created from the following third-party dataset:

- **Dataset:** 100 Million+ Steam Reviews
- **Publisher:** KieranPO'C (`kieranpoc` on Kaggle)
- **Source:** https://www.kaggle.com/datasets/kieranpoc/steam-reviews
- **Published license:** MIT
- **License reference linked by Kaggle:** https://www.mit.edu/~amini/LICENSE.md

Kaggle describes the source as more than 100 million Steam reviews collected
from the Steam User Reviews API. The raw source dataset is not included in this
repository.

The project author transformed the source data by:

- rejecting malformed records and exceptionally long review text;
- iteratively removing games and users below configured review-count thresholds;
- deduplicating user/game reviews by retaining the newest review;
- creating a Steam app ID-to-title lookup;
- calculating symmetric Bayesian-smoothed game-pair rankings;
- calculating directional Bayesian-smoothed game-pair rankings;
- training a user/game matrix-factorization model and ranking games by cosine
  similarity between learned game embeddings;
- exporting an additional precomputed recommendation artifact labeled Peabrain;
  and
- exporting compact Parquet artifacts for application use.

The derived files distributed with this repository are:

- `data/game_lookup.parquet`
- `data/game_recommendation_lists.parquet`
- `data/game_recommendation_lists_asymmetric.parquet`
- `data/game_recommendation_lists_matrix.parquet`
- `data/game_recommendation_lists_peabrain.parquet`

The source dataset's MIT notice is reproduced in
`licenses/steam-reviews-MIT.txt`. The repository's root `LICENSE` applies to
Wilson Matos's original application and processing code; it does not replace
third-party attribution.

Steam, the Steam logo, game names, and related marks belong to their respective
owners. This project is not affiliated with or endorsed by Valve Corporation.
