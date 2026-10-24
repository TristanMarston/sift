# Where the data lives

Scraped listings are **never committed to git and never published** (no Kaggle, no public bucket). `pipeline/data/`
is gitignored. The data is ~16 KB per listing (~800 MB at 50k with the search index), and it is marketplace data we use
only inside the app (some marketplaces forbid automated collection in their terms; see DESCRIPTION.md §8.5).

| Where | What | How long |
| --- | --- | --- |
| The runner's laptop, `backend/pipeline/data/` | raw runs, `listings.jsonl`, batch checks | until deleted |
| Apify, dataset `sift-runs` (team log) | every run, so teammates can `sync` | **7 days** (Apify keeps run data a week) |
| Modal volume `sift-index`, `/snapshots/` | dated `sift-data-YYYY-MM-DD.zip` exports (runs, raw rows, batch reports, care-tag answers): the long-term backup | until deleted |
| Modal volume `sift-index`, `/full/` | the search index the API serves (`embeddings.npy`, `rows.jsonl`, `manifest.json`) | until rebuilt |

## After each scrape (run from `backend/`)

```bash
# 1. back up everything scraped so far (raw runs + catalog), dated
uv run python pipeline/run/cli.py export sift-data-$(date +%F).zip
uv run modal volume put sift-index sift-data-$(date +%F).zip /snapshots/

# 2. read care tags for listings that state no fabric (cached: only new listings are paid for, ~$0.0005 each)
uv run python pipeline/03b_tags.py --dry-run && uv run python pipeline/03b_tags.py

# 3. rebuild the search index on Modal (photos download at datacenter speed; the index stays on the volume)
uv run modal run modal_app.py::embed --listings pipeline/data/listings.jsonl --name full

# 4. check it
uv run modal run modal_app.py::query --photo some_jacket.jpg --name full
```

## Getting the data on another computer

```bash
uv run modal volume get sift-index /snapshots/sift-data-YYYY-MM-DD.zip .
uv run python pipeline/run/cli.py import sift-data-YYYY-MM-DD.zip     # rebuilds pipeline/data/listings.jsonl
```

Scraping itself (one runner at a time, budgets, checks, stopping): `pipeline/run/README.md`.
