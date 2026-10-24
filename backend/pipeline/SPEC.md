# Sift — Scraping Pipeline Spec (v1 build)

Location: `backend/pipeline/SPEC.md`. Status: **planned, nothing built yet**.
Companion to `SCRAPING.md` (Anthony's original spec). Where the two differ, **this file reflects the
decisions made on Fri Oct 23, 2026** and the findings from checking the actor pages. Update
`SCRAPING.md` or this file if either changes.

Sources read: `DESCRIPTION.md`, `backend/pipeline/SCRAPING.md`, `schema/API.md`,
`schema/api.schema.json`, `https://apify.com/agents.md`, and the five Apify actor pages.

---

## 1. Goal

Produce **large JSONL files of clean secondhand clothing listings** from five US marketplaces
(Depop, Poshmark, Grailed, Mercari, eBay). Each row carries what the ranker and the frontend later need
for three markers (cost, quality, eco): price, full description, all images, condition, brand, size,
materials, certifications, flags, and a coarse seller profile.

Targets:
- **20,000 active rows first.** Verify, then grow to **~50,000**.
- At least 4 marketplaces, none above 50% of the total.
- Scraping happens only during the build. Nothing is scraped at request time.

## 2. Scope

### In scope
- Scrape, normalize, and extract materials into JSONL (pipeline steps 01–04 below).
- Pydantic `Listing` model for the row format.
- Query plan (`queries.yaml`), product-line table (`product_lines.yaml`).
- Tests (red/green TDD), a stats report.

### Out of scope (this PR)
- Supabase tables, upsert, storage bucket (SCRAPING.md steps 04 thumbs, 05 embed, 06 upsert).
- Thumbnails and image embeddings (the matching workstream).
- Evidence collectors (retail reviews, forum posts, brand-level tables). **A later PR.** The row schema
  leaves room via the `evidence[]` list and open-ended fact kinds.
- Haiku LLM fallback for materials and care-tag OCR (SCRAPING.md §4 steps 4 and 6). Deferred.
- Sold-comps scraping and the hand-curated `brands` table.
- Any eco *score*. Only eco **facts** are stored (materials, recycled, deadstock, certifications, flags).

## 3. Decisions log

| # | Decision | Why |
| --- | --- | --- |
| 1 | `SCRAPING.md` beats `DESCRIPTION.md` on scope: secondhand only, three markers, 8 categories | It is the newer, build-oriented spec |
| 2 | Eco is stored as facts, never as a "sustainable" grade | Keeps DESCRIPTION.md §10.6 true |
| 3 | Row = static fields of `api.schema.json#Result` + description + status + evidence | The ranker can map rows to `Result` without renaming |
| 4 | Ranker fields (`match`, `quality`, `eco`, `wear`, `confidence`, `thumb_url`) are not emitted | They are computed downstream |
| 5 | Extraction = regex + structured fields + product lines | Deterministic, free, fits TDD |
| 6 | The user adds `APIFY_TOKEN` to `/workspace/.env`; Claude runs the scrapes after the user approves the spend | Apify guidance: get a go-ahead before the first paid run |
| 7 | Targets are 20k, then 50k, over-scraping ~30% | Covers the US filter, dedup, and rows with no images |
| 8 | Python 3.12 (the repo's pin: `.python-version`, `pyproject.toml`, README, API.md) | The repo moved from 3.14 to 3.12 in commit 0523172, after this spec was drafted. All dependencies install on 3.12 |
| 9 | Raw files have seller identity keys scrubbed at write time | SCRAPING.md says "keep raw" and "store no seller identity", which conflict |
| 10 | Pipeline steps renumbered 01–04 | Steps for thumbs, embed, and upsert are dropped |
| 11 | Time estimates are ignored; build in the order in §14 | User instruction |

## 4. Repo state and layout

At the start of this work `backend/` was an empty uv scaffold: Python 3.12, no dependencies, no tests, no config. `schema/` holds
the frontend↔backend API contract (it is **not** a row schema for scraped data). SCRAPING.md's `supabase/`
and `contract/` paths do not exist.

Planned files, all under `backend/pipeline/` unless noted:

```
listing.py              Pydantic Listing + Evidence; enums mirror schema/api.schema.json
normalize/common.py     price -> cents, condition map, category fallback, seller_type, US filter
normalize/depop.py      one mapper per marketplace: raw dict -> Listing | None
normalize/poshmark.py
normalize/grailed.py
normalize/mercari.py
normalize/ebay.py
extract.py              regex composition, certifications, flags, structured specifics, product lines
product_lines.yaml      brand/line -> material table (status "inferred")
queries.yaml            category -> marketplace -> [{query, max_items}] + per-marketplace quotas
01_scrape.py            run actors, write data/raw/<marketplace>/<run_id>.jsonl, log runs
02_normalize.py         raw -> data/normalized.jsonl
03_extract.py           normalized -> data/listings.jsonl   (the final output)
04_report.py            stats per marketplace -> REPORT.md
tests/                  pytest; tests/fixtures/<marketplace>.json (sanitized real samples)
```

Repo-level changes:
- `backend/pyproject.toml`: add `apify-client>=3.3`, `pydantic`, `pyyaml`, `python-dotenv`; dev: `pytest`.
- `.gitignore`: add `.venv`, `__pycache__`, `.pytest_cache`, `data/`.
- `.env` (already ignored) holds `APIFY_TOKEN`. No `ANTHROPIC_API_KEY` is needed in this PR.

Git: work on branch `pipeline-scraping`. Never push to `main`. Open a PR when finished.

## 5. Marketplaces and actors

Checked against the actor pages on Oct 24, 2026. **Bold** marks places where the page disagrees with
SCRAPING.md.

| Marketplace | Actor | Inputs we use | Price (page) | Description? | Fallback |
| --- | --- | --- | --- | --- | --- |
| Depop | `jongoose/depop-scraper` | `query`, `maxItems`, `startUrls`, `proxyConfiguration` | $0.001/result | In the full field list but **absent from the sample record** | `123webdata/depop-scraper` (detail mode) |
| Poshmark | `123webdata/poshmark-scraper` | `categoryUrls`, `maxResultsPerScrape`, `usePagination`, `scrapeProductDetails: true` | $0.00199/detail, **$0.02 per run start** | Yes, in detail mode only | `xtracto/poshmark-detail-scraper` (has `condition`) |
| Grailed | `piotrv1001/grailed-listings-scraper` | `searchQuery`, `department`, `minPrice`, `maxPrice`, `scrapeDetails: true`, `maxItems` (default 50) | $0.003 standard, **$0.012 with details**, $0.00005 start | Detail mode only | `lulzasaur/grailed-scraper` |
| Mercari US | `getascraper/mercari-us-scraper` | `keyword`, `sort`, `status`, `priceMin/Max`, `condition`, `limit` (default 25) | **"from $2.05–$2.99 per 1,000"; no per-search fee shown** | Yes | none cheap |
| eBay | `memo23/ebay-search-scraper-ppe` | `searchQueries` (≤500), `marketplace`, `mode`, `detailedItems`, `includeDescription`, `maxItems` (per search, default 1000) | **$5 per 1,000 detailed items** | Only with `includeDescription: true` (one extra request per item) | eBay Browse API |

Do not use `markdolanmoore/depop-scraper` (no description) or `parsebird/mercari-us-scraper` (30%
non-success in 30 days).

Known risks per actor:
- **Depop**: the input schema defaults to a *residential* proxy while SCRAPING.md says *datacenter*. Only
  7 monthly users. Keyword-less URLs return a single page. `description`, `originalPrice` and `country`
  must be confirmed in the test run.
- **Poshmark (123webdata)**: no `condition` and no location field in the sample. List-level records omit
  `description`, `category`, `color`. Poshmark is US-only, so the US filter is satisfied by construction.
- **Grailed**: a single search shows at most 1,000 results, so split by brand. Records contain
  `seller.username` and `avatarUrl`, which must be dropped.
- **Mercari**: needs a US residential proxy. Large batches may get blocked.
- **eBay**: the connection country follows `marketplace`. Near-match rows are returned and billed. If
  `max_total_charge_usd` is hit, some rows may not be delivered. `Material` comes from
  `itemSpecifics` in detail mode.
- **Terms of service**: Poshmark's terms prohibit automated collection; Depop and Mercari sit behind
  Cloudflare. We use public listing data only, store no seller identity, link out, and state this in the
  Trust section.

## 6. Cost model

Per-record prices from the pages: Depop $0.001; Poshmark $0.00199 (+ $0.02/run); Grailed $0.012;
Mercari ~$0.003; eBay $0.005 (+ start fee).

| Marketplace | Rows at 20k | Estimate |
| --- | --- | --- |
| Depop | 8,000 | ~$8 |
| Poshmark | 4,000 | ~$8 |
| Grailed | 3,000 | ~$36 |
| Mercari | 3,000 | ~$9 |
| eBay | 2,000 | ~$10 |
| **Total** | 20,000 | **~$71** (~$92 with 30% over-scrape) |

At 50k the estimate is ~$180 (~$230 with over-scrape), which can exceed the ~$200 credit budget. The main
cost lever is Grailed detail mode. Options if needed: fewer Grailed rows, or shift volume to Depop and
Poshmark. The per-marketplace quotas in `queries.yaml` are where this is tuned.

Cost controls (Apify's guidance):
- Every `.call()` passes `max_total_charge_usd` **as a call option, never inside `run_input`**.
- `maxItems` in the actor input limits the actor's output. Apify says its platform-level `maxItems` does
  not cap charges when `max_total_charge_usd` is set, so the real spend cap is the charge cap.
- Before the first paid run, state the pricing and the cap and get the user's go-ahead.
- Check run status before reading data. Treat `FAILED`, `TIMED-OUT`, `ABORTED` as errors and log the
  `statusMessage`. Use the async call flow for long runs.

## 7. Query plan

Categories (exactly the API enum): `jackets_outerwear`, `hoodies_sweatshirts`, `tshirts`, `sneakers`,
`jeans_pants`, `sweaters_knitwear`, `shirts`, `dresses_skirts`.

US only. Keep a listing only when the item or seller is in the US:
- Depop: `country == "US"` (to confirm it exists in the output).
- eBay: marketplace `ebay.com` and an item location in the US.
- Mercari: US by construction; also check `item_location`.
- Poshmark: US by construction.
- Grailed: filter on `location` when present.
- Drop any record whose currency is not USD.

Per category, up to ~25 queries per marketplace, mixing:
- Brands judges wear: Carhartt, Patagonia, The North Face, Nike, New Balance, Levi's, Uniqlo, Arc'teryx,
  Columbia, Champion, Adidas, Dr. Martens.
- Silhouettes: boxy tee, oversized hoodie, cropped jacket, wide-leg pants.
- Material-rich phrases: "100% cotton", "100% wool", "merino", "cashmere", "linen", "organic cotton",
  "recycled polyester", "deadstock", "vintage wool".
- Demo props by exact title: Carhartt Detroit jacket, Patagonia Better Sweater, Nike Dunk Low.
- About 10% of tee queries: "conference tee", "hackathon shirt".

`queries.yaml` structure: category → marketplace → list of `{query, max_items}`, plus a top-level
`quotas` map (rows per marketplace). `max_items` is 200–500 per query so one long tail cannot eat the
budget. Mercari uses fewer, broader queries (cost per search is unverified). Grailed queries are split by
brand because of the 1,000-result cap. Poshmark queries are search URLs for `categoryUrls`.

## 8. Row schema: `Listing`

One JSON object per line in `data/listings.jsonl`. Names and enums mirror
`schema/api.schema.json#Result`; if that file changes, `listing.py` and its parity test change with it.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | `<marketplace>:<external_id>`; matches `^(depop\|poshmark\|grailed\|mercari\|ebay):.+$` |
| `marketplace` | enum | `depop poshmark grailed mercari ebay` |
| `external_id` | string | actor id field, else last path segment of `url` |
| `url` | string | link-out |
| `title` | string | |
| `description` | string \| null | full text |
| `status` | enum | `active` \| `sold` (index active only; sold kept for later comps) |
| `scraped_at` | datetime | |
| `brand` | string \| null | case-normalized |
| `category` | enum | marketplace label if mappable, else the query's category |
| `subcategory` | string \| null | |
| `size`, `color` | string \| null | raw strings |
| `condition` | enum \| null | `new_with_tags like_new good fair`; `null` if unmappable |
| `condition_raw` | string \| null | the raw string |
| `image_urls` | string[] (≥1) | **all** images; later ones may show care tags |
| `flags` | object | `is_vintage`, `is_deadstock`, `is_upcycled` (booleans) |
| `cost.price_cents` | int | |
| `cost.currency` | `"USD"` | |
| `cost.shipping_cents`, `cost.free_shipping` | int \| null, bool \| null | null when the actor does not return them |
| `cost.total_cents` | int | price + shipping when known, else price |
| `cost.original_price_cents` | int \| null | seller's own markdown |
| `cost.retail_price_cents` | int \| null | from text regex `retail(s)? (for )?\$?(\d+)` or an actor field |
| `materials.fibers` | array | `{fiber, pct \| null, organic \| null, recycled \| null}` |
| `materials.synthetic_share` | number \| null | sum of synthetic fiber pct; null without composition |
| `materials.certifications` | array | `gots oeko_tex bluesign fair_trade rws rds b_corp` |
| `materials.composition_suspect` | bool | |
| `country_of_manufacture` | string \| null | eBay `itemSpecifics`, else regex `made in (\w+)` |
| `seller.type` | enum \| null | `individual small_shop large_reseller` |
| `seller.rating` | number \| null | |
| `seller.region` | string \| null | state or country only |
| `seller.listing_count` | int \| null | used to derive `type` |
| `evidence` | array | `{field, status, source, snippet, as_of}` |

Rules:
- **Nullable means unknown.** Never invent a value. A missing material is `null` with an `unknown`
  evidence record.
- **Seller privacy**: never store username, profile URL, avatar, or full location. Derive `seller.type`
  in memory, then discard the identity.
- `evidence.status`: `verified | claimed | inferred | unknown`. `evidence.source`: `specifics |
  listing_text | product_line | tag_image | model | brand_table | baseline` (the API `Fact.source` enum).
  The ranker later turns evidence into `Fact`s.
- `seller.type` thresholds: ≤20 listings `individual`, ≤200 `small_shop`, else `large_reseller`. Tuned
  after the test run.
- Not emitted: `match`, `quality`, `eco`, `wear`, `confidence`, `thumb_url`.

### Raw files
`data/raw/<marketplace>/<run_id>.jsonl` holds the actor records as returned, joinable to `listings` by
`id`, with **seller identity keys removed at write time** (for example Depop `sellerUsername`/`sellerUrl`,
Grailed `seller.username`/`avatarUrl`, Mercari `seller_username`, Poshmark `seller_name`/`seller_url`).
`data/` is gitignored. `data/runs.jsonl` logs one line per actor run: marketplace, query, run id, status,
items, charge, timestamp.

## 9. Field mapping (from the actor pages; confirm in the test run)

| Listing field | Depop | Poshmark | Grailed | Mercari | eBay |
| --- | --- | --- | --- | --- | --- |
| external id | `id` | `product_id` | `id` | `listing_id` | item id / URL |
| price | `price.amount` | `price` | `price` | `price` | numeric price + currency |
| original price | `originalPrice` | `regular_price` | none (price drops) | `original_price` | none |
| description | `description`? | `description` (detail) | `description` (details) | `description` | description (opt-in) |
| images | `pictureUrls` | `images` | `photos` (details), `coverPhoto` | `media.image_urls` | `images` |
| brand | `brand` | `brand` | `designer` | `brand` | `brand` / specifics |
| size / color | `size`, `colours` | `size`, `color` | `size`, `color` | `size`, `color` | specifics |
| condition | `condition` | none | `condition` | `condition_id` | condition label |
| category | `category`, `categoryPath` | `category` | `category`, `categoryPath` | `category_path` | category fields |
| shipping | ? | ? | per-region rates (US) | `shipping_fee`, `shipping_payer` | shipping cost |
| status | `isSold`/`status` | `listing_status` | `sold` | `listing_status` | `listingStatus` |
| seller rating | ? | none | `ratingAverage` | `seller_rating_score` | feedback % |
| seller listing count | ? | none | `totalBoughtAndSold` | `sales_count` | ? |
| region | `country`/`location` | US | `location` | `item_location` | `itemLocation` |

"?" means not seen in the page. Resolve in the test run. Each marketplace gets one mapper and one test
built on a real sample.

Normalization rules (`02_normalize.py`):
- Drop records missing `url`, `title`, `price`, or at least one image.
- Convert price to integer cents; keep currency; do not convert FX; drop non-USD.
- Dedupe on `id` (keep the newest `scraped_at`).
- Map condition strings to the 4-value enum; keep the raw string.
- Category: marketplace label wins over the query's category; fall back to the query's category.

## 10. Extraction rules (`03_extract.py`, in this order)

1. **Regex** over `title + " " + description + specifics`:
   - Composition: `(\d{1,3})\s*%\s*(organic\s+|recycled\s+)?(cotton|polyester|poly|nylon|polyamide|wool|merino|linen|hemp|silk|viscose|rayon|modal|lyocell|tencel|acrylic|elastane|spandex|lycra|cashmere|alpaca|mohair|leather|down)`
   - Canonical names: poly→polyester, polyamide→nylon, spandex/lycra→elastane, rayon→viscose,
     tencel→lyocell.
   - Bare material words with no percent ("cotton tee") → `{fiber, pct: null}`, status `claimed`.
   - Certification keywords, case-insensitive and hyphen-tolerant: GOTS, OEKO-TEX, bluesign, Fair Trade,
     RWS, RDS, B Corp.
   - Flags: vintage, deadstock, upcycled; "vegan leather" → synthetic (not animal); "genuine leather" →
     animal.
2. **Structured fields win over text** (eBay `Material`, Poshmark material attributes).
3. **Product lines** from `product_lines.yaml` (for example Carhartt Detroit → cotton duck; Patagonia
   Better Sweater → recycled polyester). Status `inferred`, lower weight than stated.
4. **Evidence record** per extracted field.
5. Percentages summing to 90–110 are normalized to 100. Outside that range, keep the composition and set
   `composition_suspect = true`.

Derived: `synthetic_share` (sum of synthetic fibers: polyester, nylon, acrylic, elastane, and similar).
Eco facts are derivable downstream from `materials`, `flags`, and `seller.region`.

## 11. Pipeline steps

All steps are rerunnable and idempotent.

1. **`01_scrape.py`**: for each (category, marketplace, query) in `queries.yaml`: call the actor with
   `max_total_charge_usd`, check the run status, fetch dataset items, scrub seller identity keys, write to
   `data/raw/<marketplace>/<run_id>.jsonl`, append to `data/runs.jsonl`. Resumable (skips queries with a
   successful run). Stops a marketplace when its quota is met. Accepts `--test` for the 20-item run.
2. **`02_normalize.py`**: raw → `data/normalized.jsonl` using the per-marketplace mappers and the rules
   in §9.
3. **`03_extract.py`**: normalized → `data/listings.jsonl` using §10.
4. **`04_report.py`**: per marketplace, print rows, % with description, % with any material, % with
   composition percentages, % with certification, % US, median price. Write to `pipeline/REPORT.md`.

## 12. Testing (red/green TDD)

Every piece of computational code gets a failing test first.
- `listing.py`: enum and field parity with `schema/api.schema.json`; a sample row validates; rows with
  seller identity fields are rejected.
- `extract.py`: composition cases (percent, synonyms, organic/recycled), certifications, flags, "vegan
  leather" vs "genuine leather", structured-over-text, product-line inference, the 90–110 rule.
- Mappers: one test per marketplace on sanitized real samples in `tests/fixtures/`, covering price→cents,
  condition, category, US filter, drop rules.
- Runner (`01_scrape.py`): with a fake Apify client, test quota stop, resume, charge-cap argument, failed
  run handling, and identity scrubbing.
- Privacy: a test that scans normalized and raw output for identity keys.

Before the token exists, work starts with `listing.py` and `extract.py` (pure text functions) and the
runner against a fake client. Mapper tests wait for the test run's real samples.

## 13. Test run (go/no-go)

Once `APIFY_TOKEN` is in `.env`, and after the user approves the pricing and caps: for each primary actor,
one query, 20 items.

Pass criteria:
- ≥ 18 of 20 records have `url`, `title`, `price`, and non-empty images.
- `description` present and longer than 40 characters on ≥ 15 of 20 for every marketplace.
- Total charge under $1.

Also record: whether Depop returns `description`, `originalPrice`, `country`; how Poshmark exposes
condition and location; whether eBay and Mercari expose shipping; the real seller-count fields; and which
fields carry seller identity (for scrubbing).

If Depop and Poshmark both fail, switch to `123webdata/depop-scraper` (detail mode) and
`xtracto/poshmark-detail-scraper`. If those fail too, raise it with the team.

## 14. Order of work

1. Branch `pipeline-scraping`; deps, `.gitignore`, pytest config.
2. `listing.py` with tests.
3. `extract.py` with tests; `product_lines.yaml`.
4. `queries.yaml` and `01_scrape.py` with a fake-client test suite.
5. Test run (needs token and approval). Save sanitized fixtures.
6. Mapper tests and mappers; `02_normalize.py`, `03_extract.py`.
7. Scrape 20k in batches; `04_report.py`; check acceptance.
8. Scrape the extra 30k (cost check against credits first).
9. Commit on the branch, open the PR with `REPORT.md`.

## 15. Acceptance

- ≥ 20,000 active rows over ≥ 4 marketplaces; no marketplace above 50%.
- Every line of `data/listings.jsonl` validates against `Listing`.
- Every row has ≥ 1 image URL, a USD price, and a US region.
- ≥ 25% of rows have at least one stated material; ≥ 10% have percentages. If below, add material-rich
  queries.
- The three demo props are present (Carhartt Detroit jacket, Patagonia Better Sweater, Nike Dunk Low).
- No seller identity fields in `data/raw` or `data/listings.jsonl`.
- `pytest` passes; `REPORT.md` committed.

## 16. Open items and risks

- `apify-client` access style: SCRAPING.md uses `run.default_dataset_id` (typed, ≥3.3); Apify's doc
  uses `run['defaultDatasetId']`. Check against the installed version.
- Depop actor: reliability (7 monthly users), proxy default, missing `description`.
- Whether Mercari and eBay charge extra per search; the Mercari page is ambiguous ($2.05 vs $2.99 per
  1,000).
- 50k may exceed the ~$200 credits (§6). Decide quotas after the 20k run.
- US filtering for Depop, Grailed, and Poshmark depends on which location fields actually come back.
- `seller.type` thresholds are guesses until the test run shows real listing counts.
- Material coverage may fall short of the 25% / 10% targets; the fix is more material-rich queries.
- Terms of service (see §5).
- The two product specs differ (new+used vs secondhand-only; eco score vs eco facts). Decision 1 and 2
  settle this for the pipeline; the team should reconcile `DESCRIPTION.md`.
