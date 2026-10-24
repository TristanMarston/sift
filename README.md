# Sift

Take a photo of clothing. We find look-alikes across secondhand marketplaces and rank them by
**cost per wear**, with a Wear Receipt showing the cost, quality, and eco evidence.
Cal Hacks 13.0.

## Docs

| Doc | What it covers | Owner |
| --- | --- | --- |
| [`DESCRIPTION.md`](DESCRIPTION.md) | Why, product intent, scope, demo, decisions | Everyone |
| [`backend/pipeline/README.md`](backend/pipeline/README.md) | How to run the data pipeline: steps, inputs, outputs | Andy |
| [`backend/pipeline/run/README.md`](backend/pipeline/run/README.md) | How the team runs the scrape: batches, checks, sync, handing off | Andy |
| [`backend/pipeline/BLOCKING.md`](backend/pipeline/BLOCKING.md) | What happens when a marketplace blocks the scraper: detection, alerts, stopping, the end-of-run report | Andy |
| [`backend/pipeline/SPEC.md`](backend/pipeline/SPEC.md) | Pipeline decisions, costs, test-run results (newer than SCRAPING.md where they differ) | Andy |
| [`backend/pipeline/SCRAPING.md`](backend/pipeline/SCRAPING.md) | Marketplaces, fields per listing, extraction, pipeline steps | Andy |
| [`schema/API.md`](schema/API.md) | Frontend ↔ backend endpoints, payloads, sort rules | Anthony + Tristan |
| [`schema/api.schema.json`](schema/api.schema.json) | Machine-readable API contract (JSON Schema) | Anthony + Tristan |

**When docs disagree, the more specific one wins:**
`api.schema.json` > `API.md` > `SCRAPING.md` > `DESCRIPTION.md`.
Fix the loser in the same PR. Changing the schema needs a quick team huddle.

## Layout

```
backend/            Python 3.12, uv
  pipeline/         scrape → normalize → extract → thumbs → embed → upsert
  database/         Supabase / Postgres (pgvector)
  ml/               garment detection, embeddings, wear_baselines.yaml
  src/backend/      shared package: models, embed, FastAPI app
schema/             API contract (the source of truth for web ↔ backend)
web/                frontend
```

## Rules

See [`CLAUDE.md`](CLAUDE.md): never push to main, one branch + PR per feature, red/green TDD for data and ML code.
