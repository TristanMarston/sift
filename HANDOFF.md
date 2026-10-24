# Sift handoff — backend, night of Oct 23–24, 2026

Written for teammates **and their coding agents**. Read this before starting work. `schema/api.schema.json` is still
the contract; `CLAUDE.md` rules still apply (branch per feature, PR, TDD for data/ML code).

## TL;DR

- The backend is **built, merged and live**: <https://lu-anthony-73--sift-api.us-east.modal.run> serves
  `GET /health`, `POST /detect`, `POST /search` over **20,501 real listings** (5 marketplaces), with Claude Haiku in
  `/detect`. PRs #4–#39 are merged; 885 backend tests pass; backend CI runs on every PR touching `backend/` or `schema/`.
- **Anthony's laptop is running paid jobs overnight** (below). Don't touch the Apify token, the scrape, or the Modal app.
- Biggest open items: the frontend pointing at the live API, a real phone-photo test of the demo props, and picking
  the demo moment.

## Running right now on Anthony's laptop — do not interfere

In order, unattended, all on Anthony's accounts:

1. **Depop shipping enrichment** (`pipeline/03c_depop_shipping.py`, Apify `parsebird/depop-scraper`): 8,726 Depop
   listings, ~$14.
2. **Scrape to ~50k listings** (`pipeline/run/cli.py batch`, 6 batches, ≤ $98), then shipping for the new Depop rows
   (~$21) and care tags for new listings (`03b_tags.py`, Anthropic, ~$10).
3. **Rebuild + re-index on Modal + redeploy** the live API, then a live test; Anthony gets an email report.

So, until that report:

- **Do not** use the team Apify token or run `cli.py batch`, `01_scrape.py`, `03c_depop_shipping.py` — the batch runner
  needs all 5 Apify run slots and refuses (or breaks) with other runs active (`pipeline/run/README.md`).
- **Do not** `modal deploy` the `sift` app (Anthony's Modal account; the redeploy happens from `main` at the end).
- **Do** merge to `main` freely — but keep it green: the final redeploy ships whatever `main` is.

## Live API (what the frontend calls)

Base URL: `https://lu-anthony-73--sift-api.us-east.modal.run` · Contract: `schema/api.schema.json` · Code: `backend/src/backend/app.py`

| Endpoint | Behaviour worth knowing |
| --- | --- |
| `GET /health` | `{"status":"ok","index_size":20501}` (will grow to ~50k) |
| `POST /detect` | multipart `image`. SegFormer boxes + Claude Haiku labels ("black leather jacket", "white ribbed crop top"), one garment per tab (overlaps merged, shoe pairs = 1). Product shots → one whole-photo garment with a category. `category` may be **null**. **~3 s warm, ~10 s cold** — the web app gives up at 8 s and searches the whole photo. |
| `POST /search` | multipart `image` + `params` JSON (`SearchParams`). Top 50, cross-posted duplicates collapsed to the **cheapest copy**. **No category → read from the photo**; `query.category` in the response says which was used. ~0.5 s. |
| Errors | always `{"error": {"code", "message"}}`: 400 `invalid_image` / `invalid_params`, 413 `image_too_large`, 500 `internal`. |
| CORS | `http://localhost:3000` and `https://sift(-…)?.vercel.app` (preview URLs included). |

Receipt facts to render (generic `label` + `value` works): new kinds `construction`, `survival` ("Already lasted"),
`natural_fibers`; fabric read from a care-tag photo arrives as source `tag_image`, status `verified`. `shipping_cents`
null → "Shipping unknown" (already handled). Break-even beyond the item's life → "Unlikely to beat the typical match"
(already handled, #36).

## Completed features

| Feature | Status | Where | Notes |
| --- | --- | --- | --- |
| Scrape pipeline (5 marketplaces, batches, checks, privacy) | ✅ | `backend/pipeline/`, `pipeline/run/` (Andy) | Ctrl-C bug fixed (#19); 20,501 listings, all checks passed |
| Search index (FashionSigLIP, ONNX) | ✅ | `src/backend/embed.py`, `index.py` | median top match 0.89; product shots 0.89–0.99 |
| Garment detection | ✅ | `src/backend/detect.py` | SegFormer + Haiku + FashionSigLIP naming; YOLOS swap via `backend="yolos"` |
| HTTP API + hosting | ✅ | `src/backend/app.py`, `backend/modal_app.py` | deploy: `SIFT_HAIKU=1 SIFT_INDEX_NAME=full uv run modal deploy modal_app.py` |
| Ranker: cost per wear, break-even, sorts, slider | ✅ | `src/backend/ranker.py`, `wear.py` | wear figures cited from EU PEFCR (mid = published default) |
| Quality marker | ✅ | `src/backend/markers.py` | brand promises that reach secondhand buyers, durable product lines, fabric fit, construction words, vintage-that-lasted; **unknown 32%** (was 62% at 5k) |
| Eco marker | ✅ | `markers.py` | vintage/deadstock/upcycled, recycled, organic, natural fibers, certifications, synthetic share; **unknown 34%** (was 87%) |
| Evidence: brand facts | ✅ | `backend/ml/evidence/brands.yaml` | 12 brands incl. Carhartt repairs, Patagonia B Corp. Rule at top of file |
| Evidence: product lines | ✅ | `pipeline/product_lines.yaml` | `durable: true` lines earn +2; material-only lines (Samba OG) just supply fabric |
| Evidence: care tags (Haiku) | ✅ | `pipeline/tags.py`, `03b_tags.py` | 1,979 listings got verified fabric; cached |
| Depop shipping | 🟡 running | `pipeline/depop_shipping.py`, `03c_…` | fills 43% of totals that lacked shipping |
| Poshmark condition + shipping | ✅ | `normalize/poshmark.py` | condition from seller text (41%); $6.49 flat Posh Post |
| Data storage + backups | ✅ | `backend/DATA.md` | Modal volume `sift-index`: dated snapshots, tag + shipping caches, `full/index` |
| Web: nullable types, honest break-even | ✅ | `web/lib/detect.ts`, `search.ts`, `wear.ts` | #28, #36 |

## Evidence rules (please keep them)

- **Every fact needs a source someone actually read** (URL + quoted sentence in a YAML comment). No statistical
  imputation on receipts — unknown stays "unknown".
- **Brand promises count only if they reach a secondhand buyer** (Carhartt repairs "passed-down" gear: yes; original-owner
  warranties like Nike's or The North Face's: no). Brand certifications must be true of every item of the brand.
- **Product lines only when the maker states one fabric for the whole line** (Nike Dunk / Air Force 1, NB 550/990,
  Converse vary by colorway → not lines).
- Eco is **facts, never "sustainable"**.

## How to run things

```bash
cd backend && uv sync && uv run pytest -q               # 885 tests, no network, no money
uv run uvicorn backend.app:app --port 8000              # local API (SIFT_INDEX=... for an index folder)
cd web && npm ci && npm test && npm run lint            # web (npm test needs Node >= 22.18 for .ts tests)
```

Get the data on your machine: `backend/DATA.md` (snapshot zip from the Modal volume, then `cli.py import`).

## What you (or your agent) can do now

**Tristan — web**
- Set `NEXT_PUBLIC_API_URL=https://lu-anthony-73--sift-api.us-east.modal.run` in Vercel (all envs).
- Show `query.category` when the backend inferred it ("Searching jackets").
- Loading state for `/detect` up to ~10 s on a cold start (or rely on the 8 s whole-photo fallback).
- Check the receipt renders `construction`, `survival`, `natural_fibers`, and `tag_image`/`verified` facts nicely.

**Andy — pipeline**
- Review #38/#39 (Depop shipping via a second actor; caches only id + shipping). Future Depop batches need `03c` after
  each rebuild — consider folding it into the batch runner.
- `is_vintage` is a seller claim (~38% name an era); fine for now, revisit if it skews quality.
- Don't run scrapes until Anthony's email report (see above).

**Haram — demo & story**
- Pick the demo moment: with honest numbers the cheapest item wins cost-per-wear in ~3/4 of searches. Good candidates:
  a Carhartt Detroit (quality **high**: repair program + known line + cotton) vs a cheap unbranded jacket in fair
  condition; show the break-even line.
- Photograph the demo props (worn and flat) for a live test through the deployed API.

**Anyone**
- Live phone-photo test: `curl -F image=@photo.jpg https://lu-anthony-73--sift-api.us-east.modal.run/detect`, then
  `/search` with a crop. Report misses as issues with the photo.
- Repo owner: install the Claude GitHub app on `TristanMarston/sift` so cloud agents can push and open PRs.

## Known limits

- **Sneakers 87% unknown quality** (materials vary by colorway; tags don't exist on shoes). Dresses 50%.
- `/detect` cold start ~10 s → deploy with `SIFT_MIN_CONTAINERS=1` during the demo.
- Condition factors (fair ×0.6 … new ×1.0) are labelled assumptions — no published source exists.
- The Apify and Anthropic keys were shared in a chat tonight → Anthony rotates them after the overnight jobs.

## PR index (merged tonight)

| Area | PRs |
| --- | --- |
| Search + index + ranker | #4 index · #5 ranker · #21 duplicates · #25 PEFCR midpoint |
| Detection | #7 detector · #24/#29 Haiku on · #30/#31 one tab per garment |
| API + hosting | #14 API · #15 Modal · #16 DATA.md · #27 snapshots carry tags |
| Evidence / quality | #9 cited wear baselines · #11 brand facts · #12 product lines · #17 construction & survival · #22 care tags · #23 nylon shells · #32 Carhartt · #33 dresses · #34 durable flag + Samba OG |
| Eco | #35 NOS / reworked · #37 natural fibers + Patagonia B Corp |
| Price / condition | #18 Poshmark condition · #26 Poshmark shipping · #38/#39 Depop shipping |
| Reliability | #19 Ctrl-C fix · #20 review fixes + backend CI |
| Web | #28 nullable types · #36 honest break-even |
| Teammates' (merged) | #6 pipeline review, #13 batches (Andy) · #8, #10 web (Tristan) |
