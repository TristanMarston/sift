# Sift handoff — backend, night of Oct 23–24, 2026

Written for teammates **and their coding agents**. Read this before starting work. `schema/api.schema.json` is still
the contract; `CLAUDE.md` rules still apply (branch per feature, PR, TDD for data/ML code).

## TL;DR

- The backend is **built, merged and live**: <https://lu-anthony-73--sift-api.us-west.modal.run> serves
  `GET /health`, `POST /detect`, `POST /search` over **51,101 real listings** (5 marketplaces), with Claude Haiku in
  `/detect`. PRs #4–#39 are merged; 885 backend tests pass; backend CI runs on every PR touching `backend/` or `schema/`.
- **The overnight jobs finished** (Oct 24): 51,131 listings, shipping known for 100%, index rebuilt and redeployed.
  Scraping and deploying are open again; tell the team before you run either.
- **Oct 24, 12:00 PT:** buyer fees are in every total (#47) and iPhone HEIC photos are accepted (#48); the live API
  was rebuilt and redeployed with both (51,101 listings, live test passes).
- **Oct 24 afternoon:** Haram's scrape merged (75,841 listings; shipping + tags for the new rows running, then
  re-index + redeploy). Quality: buyer fees (#47), HEIC (#48), no Grailed drift in batches (#51), a `close` match
  band (#52), fabric facts from titles (#53), **colour-aware re-rank** (#54: run `modal run modal_app.py::colors
  --name full` after every `::embed`, then redeploy), sliver-free detection (#55).
- Biggest open items: the frontend pointing at the live API, a real phone-photo test of the demo props, and picking
  the demo moment.

## Overnight run (finished Oct 24)

Depop shipping for all Depop listings (21,213 fetched) → 6 scrape batches (all checks passed, $91.54) → care tags for
new listings (3,578 got verified fabric) → snapshot `sift-data-2026-10-24.zip` in the Modal volume `/snapshots/` →
index rebuilt (51,131) → API redeployed. Live test: 21 photos, no schema errors, 50 results each.

Rebuilt again at 11:00 PT with the extraction fixes from #43 (free: no new scraping): 30 tank tops/rompers dropped,
649 listings no longer read a lining as the fabric. Live: **51,101** listings, same live test passes.

Before you scrape again, check that no one else is running a batch: the batch runner needs all 5 Apify run slots
(`pipeline/run/README.md`). After any redeploy, stop the old warm container (`modal container stop -y <id>`), or it
keeps serving the old index.

## Live API (what the frontend calls)

Base URL: `https://lu-anthony-73--sift-api.us-west.modal.run` · Contract: `schema/api.schema.json` · Code: `backend/src/backend/app.py`

| Endpoint | Behaviour worth knowing |
| --- | --- |
| `GET /health` | `{"status":"ok","index_size":51101}` |
| `POST /detect` | multipart `image` (JPEG/PNG/WebP/**HEIC**). SegFormer boxes + Claude Haiku labels ("black leather jacket", "white ribbed crop top"), one garment per tab (overlaps merged, shoe pairs = 1). Product shots → one whole-photo garment with a category. `category` may be **null**. **~3 s warm, ~10 s cold** — the web app gives up at 8 s and searches the whole photo. |
| `POST /search` | multipart `image` + `params` JSON (`SearchParams`). Top 50, cross-posted duplicates collapsed to the **cheapest copy**; ordered by similarity **minus a colour penalty** once the index has `colors.npy` (`match.similarity` stays SigLIP's; `match.band` is `exact` ≥ 0.9, `close` ≥ 0.8, else `similar`). **No category → read from the photo**; `query.category` in the response says which was used. ~0.5 s. |
| `POST /jpeg` | the uploaded photo back as an upright JPEG (long edge ≤ 1024 px), for browsers that cannot decode an iPhone HEIC. The web app calls it on its own when `createImageBitmap` fails (#48). |
| Errors | always `{"error": {"code", "message"}}`: 400 `invalid_image` / `invalid_params`, 413 `image_too_large`, 500 `internal`. |
| CORS | `http://localhost:3000` and `https://sift(-…)?.vercel.app` (preview URLs included). |

Receipt facts to render (generic `label` + `value` works): new kinds `construction`, `survival` ("Already lasted"),
`natural_fibers`; fabric read from a care-tag photo arrives as source `tag_image`, status `verified`. `shipping_cents`
null → "Shipping unknown" (already handled). Break-even beyond the item's life → "Unlikely to beat the typical match"
(already handled, #36). **`cost.fee_cents` is new (#47):** the marketplace's buyer fee, already inside
`total_cents`; the receipt shows "Includes up to $3.25 Depop buyer fee" / "Includes $1.42 Mercari buyer fee".

## Completed features

| Feature | Status | Where | Notes |
| --- | --- | --- | --- |
| Scrape pipeline (5 marketplaces, batches, checks, privacy) | ✅ | `backend/pipeline/`, `pipeline/run/` (Andy) | Ctrl-C bug fixed (#19); 51,101 listings, all checks passed |
| Search index (FashionSigLIP, ONNX) | ✅ | `src/backend/embed.py`, `index.py` | median top match 0.89; product shots 0.89–0.99 |
| Garment detection | ✅ | `src/backend/detect.py` | SegFormer + Haiku + FashionSigLIP naming; YOLOS swap via `backend="yolos"` |
| HTTP API + hosting | ✅ | `src/backend/app.py`, `backend/modal_app.py` | deploy: `SIFT_HAIKU=1 SIFT_INDEX_NAME=full uv run modal deploy modal_app.py` |
| Ranker: cost per wear, break-even, sorts, slider | ✅ | `src/backend/ranker.py`, `wear.py` | wear figures cited from EU PEFCR (mid = published default) |
| Quality marker | ✅ | `src/backend/markers.py` | brand promises that reach secondhand buyers, durable product lines, fabric fit, construction words, vintage-that-lasted; **unknown 40%** at 51k (32% at 20k: the new batches have more sneakers and dresses) |
| Eco marker | ✅ | `markers.py` | **every item has a level** (#60): secondhand alone is medium (no new garment is made); natural fibers (incl. a fabric named in the title), recycled, organic, vintage, certifications lift it; mostly synthetic lowers it. At 76k: high 20%, medium 79%, low 1%; 67% carry a fact beyond secondhand |
| Evidence: brand facts | ✅ | `backend/ml/evidence/brands.yaml` | 12 brands incl. Carhartt repairs, Patagonia B Corp. Rule at top of file |
| Evidence: product lines | ✅ | `pipeline/product_lines.yaml` | `durable: true` lines earn +2; material-only lines (Samba OG) just supply fabric |
| Evidence: care tags (Haiku) | ✅ | `pipeline/tags.py`, `03b_tags.py` | 1,979 listings got verified fabric; cached |
| Depop shipping | ✅ | `pipeline/depop_shipping.py`, `03c_…` | shipping now known for 100% of listings (was 59%) |
| Buyer fees in the total | ✅ | `normalize/common.py`, `depop.py`, `mercari.py` | Mercari's own checkout fee; Depop's stated maximum ("up to 5% + $1", help centre); eBay US, Grailed, Poshmark 0, sourced (#47) |
| HEIC photos + `POST /jpeg` | ✅ | `src/backend/app.py`, `web/components/camera/capture.ts` | pillow-heif decodes at the door; embedding pipeline unchanged (#48) |
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

## Open questions (Oct 24, 11:00 PT)

- **Apify budget: $19.73 left** of the $205 monthly limit. No more scraping this month without raising the limit;
  ~$20 buys ~6k more Depop shipping lookups or ~1 small batch.
- **Haram — `REPORT.md` says 69,027 listings.** The team ledger (`cli.py sync`: "already up to date") and the live
  index have 51,101. Where are the other ~18k? If they're on your Mac, `cli.py export` them and share the zip (they'd
  need tags + Depop shipping before indexing).
- **#42 is superseded:** its 4 commits are already on `main` through #43. Close it.
- Sizes are raw strings (`M`, `M (38-40)`) while the API's size filter is exact (Haram's review): still open.

## What you (or your agent) can do now

**Tristan — web**
- Set `NEXT_PUBLIC_API_URL=https://lu-anthony-73--sift-api.us-west.modal.run` in Vercel (all envs).
- Show `query.category` when the backend inferred it ("Searching jackets").
- Loading state for `/detect` up to ~10 s on a cold start (or rely on the 8 s whole-photo fallback).
- Check the receipt renders `construction`, `survival`, `natural_fibers`, and `tag_image`/`verified` facts nicely.

**Andy — pipeline**
- Review #38/#39 (Depop shipping via a second actor; caches only id + shipping). Future Depop batches need `03c` after
  each rebuild — consider folding it into the batch runner.
- `is_vintage` is a seller claim (~38% name an era); fine for now, revisit if it skews quality.

**Haram — demo & story**
- Pick the demo moment: with honest numbers the cheapest item wins cost-per-wear in ~3/4 of searches. Good candidates:
  a Carhartt Detroit (quality **high**: repair program + known line + cotton) vs a cheap unbranded jacket in fair
  condition; show the break-even line.
- Photograph the demo props (worn and flat) for a live test through the deployed API.

**Anyone**
- Live phone-photo test: `curl -F image=@photo.jpg https://lu-anthony-73--sift-api.us-west.modal.run/detect`, then
  `/search` with a crop. Report misses as issues with the photo.
- Repo owner: install the Claude GitHub app on `TristanMarston/sift` so cloud agents can push and open PRs.

## Known limits

- **Detection:** 1 false positive in 50 garments over 26 test photos (a dark bag under a flat-laid tee became
  "dark pants"; Haiku agrees with SegFormer, so a threshold can't fix it). Avoid clutter under demo props.
- **Colour re-rank** only applies once `colors.npy` sits next to the index (`modal run modal_app.py::colors`), and
  it re-orders the SigLIP top candidates; it never adds listings SigLIP didn't shortlist.

- **Sneakers 85% unknown quality** (materials vary by colorway; tags don't exist on shoes). Dresses 56%.
- `/detect` cold start ~10 s → deploy with `SIFT_MIN_CONTAINERS=1` during the demo.
- Condition factors (fair ×0.6 … new ×1.0) are labelled assumptions — no published source exists.
- The Apify and Anthropic keys were shared in a chat tonight → Anthony rotates them after the overnight jobs.

## PR index (merged tonight)

| Area | PRs |
| --- | --- |
| Search + index + ranker | #4 index · #5 ranker · #21 duplicates · #25 PEFCR midpoint · #52 close band · #54 colour re-rank |
| Detection | #7 detector · #24/#29 Haiku on · #30/#31 one tab per garment · #55 slivers |
| API + hosting | #14 API · #15 Modal · #16 DATA.md · #27 snapshots carry tags · #48 HEIC + /jpeg |
| Evidence / quality | #9 cited wear baselines · #11 brand facts · #12 product lines · #17 construction & survival · #22 care tags · #23 nylon shells · #32 Carhartt · #33 dresses · #34 durable flag + Samba OG · #53 fabric facts |
| Eco | #35 NOS / reworked · #37 natural fibers + Patagonia B Corp |
| Price / condition | #18 Poshmark condition · #26 Poshmark shipping · #38/#39/#41 Depop shipping · #47 buyer fees |
| Reliability | #19 Ctrl-C fix · #20 review fixes + backend CI · #51 no Grailed drift in batches |
| Web | #28 nullable types · #36 honest break-even |
| Teammates' (merged) | #6 pipeline review, #13 batches (Andy) · #8, #10 web (Tristan) |
