# Where the data lives

Scraped listings are **never committed to git and never published** (no Kaggle, no public bucket). `pipeline/data/`
is gitignored. The data is ~16 KB per listing (~800 MB at 50k with the search index), and it is marketplace data we use
only inside the app (some marketplaces forbid automated collection in their terms; see DESCRIPTION.md §8.5).

| Where | What | How long |
| --- | --- | --- |
| The runner's laptop, `backend/pipeline/data/` | raw runs, `listings.jsonl`, batch checks | until deleted |
| Apify, dataset `sift-runs` (team log) | every run, so teammates can `sync` | **7 days** (Apify keeps run data a week) |
| Modal volume `sift-index`, `/snapshots/` | dated `sift-data-YYYY-MM-DD.zip` exports (runs, raw rows, batch reports, care-tag answers, Depop shipping): the long-term backup | until deleted |
| Modal volume `sift-index`, `/full/` | the search index the API serves (`embeddings.npy`, `rows.jsonl`, `manifest.json`) | until rebuilt |

## After each scrape (run from `backend/`)

```bash
# 1. back up everything scraped so far (raw runs + catalog), dated
uv run python pipeline/run/cli.py export sift-data-$(date +%F).zip
uv run modal volume put sift-index sift-data-$(date +%F).zip /snapshots/

# 2. read care tags for listings that state no fabric (cached: only new listings are paid for, ~$0.0005 each)
uv run python pipeline/03b_tags.py --dry-run && uv run python pipeline/03b_tags.py

# 2b. Depop shipping per listing (cached; only new Depop listings are paid for, ~$0.0016 each)
uv run python pipeline/03c_depop_shipping.py --dry-run && uv run python pipeline/03c_depop_shipping.py

# 3. rebuild the search index on Modal (photos download at datacenter speed; the index stays on the volume)
uv run modal run modal_app.py::embed --listings pipeline/data/listings.jsonl --name full
uv run modal run modal_app.py::colors --name full      # 3b. one colour per listing (colors.npy): the colour re-rank

# 4. check it
uv run modal run modal_app.py::query --photo some_jacket.jpg --name full
```

## Getting the data on another computer

```bash
uv run modal volume get sift-index /snapshots/sift-data-YYYY-MM-DD.zip .
uv run python pipeline/run/cli.py import sift-data-YYYY-MM-DD.zip     # rebuilds pipeline/data/listings.jsonl
```

Scraping itself (one runner at a time, budgets, checks, stopping): `pipeline/run/README.md`.

## Moving the API to another Modal account

The live API died in Nov 2026 when the original Modal app went away. To host it on a new account, run everything from
`backend/`.

**1. On the old account:** copy out the index (the four files the API serves) and the latest snapshot.

```bash
uv run modal volume ls sift-index /full/index        # embeddings.npy, rows.jsonl, manifest.json, colors.npy
uv run modal volume get sift-index /full/index ./sift-index-full
uv run modal volume get sift-index /snapshots/sift-data-haram-2026-10-25.zip .
```

**2. On the new account:** log in, upload the index, and check the files sit at `/full/index/`.

```bash
uv run modal token new                                # opens the browser to log in
uv run modal volume create sift-index
uv run modal volume put sift-index ./sift-index-full /full/index
uv run modal volume ls sift-index /full/index         # the same four files, not a nested folder
```

**3. Optional, Claude Haiku in /detect.** Without it, detection still works with simpler labels (deploy with `SIFT_HAIKU=0`).

```bash
uv run modal secret create sift-anthropic ANTHROPIC_API_KEY=<your key>
```

**4. Deploy and check.** The deploy prints the new URL (like `https://<workspace>--sift-api.us-east.modal.run`).
`PYTHONPATH=src` lets Modal find the `backend` package even when macOS hides the venv's `.pth` file. A new account
needs Modal client 1.6.4 or later (`uv.lock` has it).

```bash
PYTHONPATH=src SIFT_HAIKU=1 SIFT_INDEX_NAME=full uv run modal deploy modal_app.py
curl https://<workspace>--sift-api.us-east.modal.run/health   # {"status":"ok","index_size":161592, ...}
```

**5. Point the web app at it.** Set `NEXT_PUBLIC_API_URL` to the new URL in Vercel (all environments) and in
`web/.env.local`, then redeploy on Vercel: the address is built into the site, so a new value needs a new build.

A cold start (first request after 10 idle minutes) takes about 25 s to load the index; the web app waits up to 45 s.

Cost: containers scale to zero, and an idle API costs nothing. Leave `SIFT_MIN_CONTAINERS` at 0 and `SIFT_REGION`
unset (Modal bills a pinned region extra), and set a spending limit in the Modal dashboard.

**Only have the snapshot zip?** Rebuild the index from it: `cli.py import` (above), then `modal run modal_app.py::embed
--listings pipeline/data/listings.jsonl --name full` and `::colors --name full`. That re-downloads every listing photo,
and listings sold since October may have lost theirs, so expect fewer listings.
