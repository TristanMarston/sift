# Sift — Scraping Pipeline Spec (v1 build)

Location: `backend/pipeline/SPEC.md`. Status: **built on branch `pipeline-scraping`; the 20-item test run is done (§13a); the 20k scrape waits for approval**.
Companion to `SCRAPING.md` (Anthony's original spec). Where the two differ, **this file reflects the
decisions made on Fri Oct 23, 2026** and the findings from checking the actor pages. Update
`SCRAPING.md` or this file if either changes.

Sources read: `DESCRIPTION.md`, `backend/pipeline/SCRAPING.md`, `schema/API.md`,
`schema/api.schema.json`, `https://apify.com/agents.md`, and the five Apify actor pages.

---

## 1. Goal

Produce **large JSONL files of clean secondhand clothing listings** from five marketplaces
(Depop, Poshmark, Grailed, Mercari, eBay). Any listing priced in USD counts, wherever it ships from. Each row carries what the ranker and the frontend later need
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
| 6 | The user adds `APIFY_TOKEN` to `.env` at the repo root; Claude runs the scrapes after the user approves the spend | Apify guidance: get a go-ahead before the first paid run |
| 7 | Targets are 20k, then 50k, over-scraping ~30% | Covers dedup, non-USD rows and rows with no images |
| 8 | Python 3.12 (the repo's pin: `.python-version`, `pyproject.toml`, README, API.md) | The repo moved from 3.14 to 3.12 in commit 0523172, after this spec was drafted. All dependencies install on 3.12 |
| 9 | Raw files have seller identity keys scrubbed at write time | SCRAPING.md says "keep raw" and "store no seller identity", which conflict |
| 10 | Pipeline steps renumbered 01–04 | Steps for thumbs, embed, and upsert are dropped |
| 11 | Time estimates are ignored; build in the order in §14 | User instruction |
| 12 | **USD only.** Any listing priced in USD counts, wherever the seller is. There is no location filter; the seller's country is stored in `seller.region` | `api.schema.json` requires USD, not US. In the test run only 4 of 20 Grailed items were US-located, so a location filter would waste ~80% of that spend. A US-only view is a one-line filter on `seller.region` later. DESCRIPTION.md, SCRAPING.md and API.md were updated to say USD only |
| 13 | **Mercari uses `automation_craft/mercari-us-scraper` with details on.** The first Mercari actor we tried (`getascraper/mercari-us-scraper`) failed the go/no-go and was dropped; this one passed (§13b) | `getascraper` only reads the card data embedded in Mercari's search page: no description, one photo, no size or shipping, and it can return 0 rows while billing $0.04. `automation_craft` returns all of them at $0.00273 per listing + $0.006 per run. `tortuga/mercari-scraper` is the fallback |
| 14 | Seller blocks are scrubbed by **allowlist** (rating/count/location only); eBay records keep a top-level key whitelist | The test run showed Grailed `sellerProfile` (account id, PayPal id) and eBay page modules (seller handle, buyer feedback) slipping past a denylist |
| 15 | Category: the marketplace label wins; a present label that maps to none of the 8 drops the record instead of using the query's category; eBay's root "Clothing, **Shoes** & Accessories" is ignored; kids' labels are dropped | A hat must not inherit "jackets"; the root made every eBay item "sneakers"; children's clothes are outgrown, not worn out |
| 16 | `is_vintage` / `is_deadstock` / `is_upcycled` come from the **title** and structured style fields, never the description | Shop-wide boilerplate ("especially for pre-owned or vintage goods") made most Grailed items look vintage |
| 17 | eBay is scraped as a used, Buy It Now search shipped to a US buyer (`startUrls`, see `scrape.ebay_search`); its material is `Outer Shell Material` (lining and insulation are excluded); `Product Line`/`Model` feed product-line matching | eBay has no `Material` specific; without `condition` the actor returns new items. The second review saw the actor's session act as a buyer abroad on 1 of 9 runs (foreign sellers, international shipping on US items); shipping to the US pins it |
| 18 | JSON Lines are read on `\n` only and written ASCII-escaped (`jsonl.py`) | Real Mercari descriptions contain U+2028, which `str.splitlines()` treats as a line break: records were cut in half and ~5% of Mercari rows would have been dropped silently |
| 19 | Titles and descriptions lose zero-width characters and non-breaking spaces at the normalize step; the Mercari actor excludes kids' titles at the source (whole words only) | A zero-width space inside `100%cotton` defeats the composition regex. Kids' listings were 40% of a broad Mercari query and are now ~2% |
| 20 | Runs are judged by outcome first (rows returned, unusable rows, rows with a description) and by the log second; a block or junk data stops the marketplace at once, a second empty or failed run in a row stops it too; bad runs are quarantined and retried; the run ends with a report and an exit code | An Apify run can end `SUCCEEDED` with `0 failed` requests having collected nothing (the blocked Mercari run did). Healthy logs also contain `HTTP 403` and `blockedStatusCodes`, so log words alone cause false alarms. See `BLOCKING.md` |
| 21 | **Batches** (`run/`): one runner at a time drives all 5 marketplaces side by side, in batches split in the quota ratio, each checked before the next (a failed check stops that marketplace; seller identity stops everything). Runs are shared through a named Apify dataset (`sift-runs`) and zip snapshots. Quotas are the "cheap-heavy" mix for the ~$190 left: Grailed stays at 3,900 rows, the other four get the rest (73.6k raw rows) | The work runs on Apify, which allows 5 runs at once per account, so one laptop uses the whole account and several would only need coordination. Money, not the query list, is the limit |

## 4. Repo state and layout

At the start of this work `backend/` was an empty uv scaffold: Python 3.12, no dependencies, no tests, no config. `schema/` holds
the frontend↔backend API contract (it is **not** a row schema for scraped data). SCRAPING.md's `supabase/`
and `contract/` paths do not exist.

Files, all under `backend/pipeline/` (see `README.md` there for how to use them):

```
jsonl.py                read JSON Lines on newline only, write them ASCII-escaped
listing.py              Pydantic Listing, Normalized (Listing + specifics), Evidence; enums mirror schema/api.schema.json
scrape.py               actors, charge caps, scrubbing, plan, run loop, cost estimate (01_scrape.py is the CLI)
health.py               judges a run (ok / short / empty / failed / degraded / blocked) and every saved row
scrape_report.py        the end-of-run report and the exit code
normalize/common.py     price -> cents, condition map, category rules, brand names, region, cost block, Drop
normalize/depop.py      one mapper per marketplace: raw dict -> Normalized, or raises Drop(reason)
normalize/poshmark.py
normalize/grailed.py
normalize/mercari.py
normalize/ebay.py
normalize/run.py        applies the mappers to the raw files, counts drop reasons, dedupes
extract.py              composition, certifications, flags, retail price, origin, product lines, evidence
report.py               per-marketplace stats and the acceptance checklist
product_lines.yaml      brand/line -> material table (status "inferred")
queries.yaml            category -> marketplace -> queries, per-marketplace quotas and caps
01_scrape.py ... 04_report.py   the four steps; data/ and REPORT.md are their outputs
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
| Mercari US | `automation_craft/mercari-us-scraper` | `keywords`, `statuses`, `includeDetails: true`, `maxItems`, `excludeKeywords`, `usCategoryIds: [1, 2]` (Women, Men: no kids' rows to pay for) | **$0.00133 per listing + $0.0014 for details (= $0.00273), $0.006 per run** | Yes, with `includeDetails` | `tortuga/mercari-scraper` (`market: us`, $0.0048/listing) |
| eBay | `memo23/ebay-search-scraper-ppe` | `startUrls` (an eBay search URL: used, Buy It Now, shipped to the US), `marketplace`, `mode`, `detailedItems`, `includeDescription`, `maxItems` (per search, default 1000) | **$5 per 1,000 detailed items** | Only with `includeDescription: true` (one extra request per item) | eBay Browse API |

Do not use `markdolanmoore/depop-scraper` (no description) or `getascraper/mercari-us-scraper` (§13a: card data
only, and flaky).

Known risks per actor:
- **Depop**: the input schema defaults to a *residential* proxy while SCRAPING.md says *datacenter*. Only
  7 monthly users. Keyword-less URLs return a single page. `description`, `originalPrice` and `country`
  must be confirmed in the test run.
- **Poshmark (123webdata)**: no `condition` and no location field in the sample. List-level records omit
  `description`, `category`, `color`. Poshmark's region is recorded as `US`.
- **Grailed**: a single search shows at most 1,000 results, so split by brand. Records contain
  `seller.username` and `avatarUrl`, which must be dropped.
- **eBay**: the connection country follows `marketplace`. Near-match rows are returned and billed. If
  `max_total_charge_usd` is hit, some rows may not be delivered. `Material` comes from
  `itemSpecifics` in detail mode.
- **Mercari** (`automation_craft`): created Oct 13 and used by only a few accounts, so reliability beyond the ~220 listings we tested
  (§13b) is only proven up to 150 items per run. Mercari serves at most 1,000 results per search, so use several queries. `color` is never
  filled. The dataset also holds free `search`/`status`/`summary` rows, which the runner drops (`type != listing`).
  The buyer's total includes a buyer-protection fee (~3.5%) that `cost` does not model.
- **Terms of service**: Poshmark's terms prohibit automated collection; Depop sits behind
  Cloudflare. We use public listing data only, store no seller identity, link out, and state this in the
  Trust section.

## 6. Cost model

Per-record prices, confirmed against the test-run bills (§13a, §13b): Depop $0.001; Poshmark $0.00199 (+ $0.02 per run);
Grailed $0.012 with details; Mercari $0.00273 (+ $0.006 per run); eBay $0.005 detail rows (+ $0.02 per run). Quotas
count **raw rows**, 30% above the 20k target to cover duplicates and dropped records.

| Marketplace | Raw rows (quota) | Runs | Best-case cost |
| --- | --- | --- | --- |
| Depop | 10,400 | 52 | ~$10 |
| Poshmark | 5,200 | 26 | ~$11 |
| Grailed | 4,000 | 20 | ~$48 |
| Mercari | 3,900 | 13 | ~$11 |
| eBay | 2,700 | 18 | ~$14 |
| **Total** | 26,200 | 129 | **~$94** (~$118 if every run hit its charge cap) |

`01_scrape.py --dry-run` prints this table from the live config. At 50k (about 2.5× the rows) the estimate is
~$235, which can exceed the ~$200 credit budget. The main cost lever is Grailed detail mode. Options if needed:
fewer Grailed rows, or shift volume to Depop, Poshmark and Mercari. The quotas in `queries.yaml` are where this is tuned.

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

USD only (decision 12). Keep any listing priced in USD and drop the rest (no FX conversion). Store the seller's
country as `seller.region` (`US` for any US place; otherwise the country the actor reports, as a code or a name).
Poshmark is `US`; the field stays null where the actor reports no location.

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
budget. Grailed queries are split by
brand because of the 1,000-result cap. Poshmark queries are search URLs for `categoryUrls`.

## 8. Row schema: `Listing`

One JSON object per line in `data/listings.jsonl`. Names and enums mirror
`schema/api.schema.json#Result`; if that file changes, `listing.py` and its parity test change with it.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | `<marketplace>:<external_id>`; matches `^(depop\|poshmark\|grailed\|mercari\|ebay):.+$` |
| `marketplace` | enum | `depop poshmark grailed mercari ebay` (the schema enum) |
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
Grailed `seller.username`/`avatarUrl`, Poshmark `seller_name`/`seller_url`).
`data/` is gitignored. `data/runs.jsonl` logs one line per actor run: marketplace, query, run id, status,
items, charge, timestamp.

## 9. Field mapping (real field names, from the test run; the code is `normalize/<marketplace>.py`)

| Listing field | Depop | Poshmark | Grailed | Mercari | eBay |
| --- | --- | --- | --- | --- | --- |
| external id | `id` | `product_id` | `id` | `listingId` | `itemId` (url rebuilt as `ebay.com/itm/<id>`) |
| price | `price.amount`, `.currency` | `price`, `currency` | `price` (USD) | `price`, `currency` | `priceValue`, `currency` |
| title | first line of `description` without hashtags (≤ 120 chars), else `title` | `name` | `title` | `title` | `title` |
| original price | `originalPrice.amount`, if above the price | none | highest earlier price in `priceDrops` | `originalPrice`, if above the price | none |
| retail price | none (text regex) | `regular_price` ("Original Price"; 0 = none) | none (text regex) | none (text regex) | none (text regex) |
| shipping | none | none | seller's US rate `shipping.us`, if enabled | `shippingFee` only when `shippingPayer` is `buyer` (seller pays = free) | `shippingCost` (`shippingType: free` = free) |
| description | `description` | `description` | `description` | `description` | `description` (HTML entities decoded) |
| images | `pictureUrls` | `images` | `photos`, else `coverPhoto` | `photoUrls`, else `imageUrl` | `images` |
| brand | `brand` | `brand` | `designer` | `brand` | `brand`, else specifics `Brand` |
| size / color | `sizes[0]`, `colours` | `size`, `color` | `size`, `color` | `size`, `color` (never filled) | specifics `Size` (shoes: `US Shoe Size`), `Color` |
| condition | `condition` | none | `condition` | `condition` | specifics `Condition`, the label before the seller's prose |
| category label | `category` `productType` `group` (kids items have only `Clothing` or `Shoes`) | breadcrumbs + `category` | `category` `categoryPath` (`short_sleeve_shirts` = T-shirts) | `categoryPath` (a string with `>`) + `category` | `categoryPath` (root ignored) + specifics `Type` as the leaf |
| status | `isSold` | `listing_status`, `in_stock` | `sold` | `status`, `sold` | `listingStatus` |
| seller type / rating | none | none | listing count (`sellerProfile.listings_for_sale_count`), `seller.ratingAverage` | `sellerListingCount`; `sellerRating` when `sellerRatingCount` > 0 | account type + feedback score; `sellerFeedbackPercentage` ÷ 20 |
| region | `country` | `US` | `sellerProfile.country_code`, else `location` | `US` | `itemLocation` |
| specifics (for 03) | none | none | `styles` | none | every `itemSpecifics` entry |

Normalization rules (`02_normalize.py`):
- Drop records missing `url`, `title`, `price`, or at least one image.
- Convert price to integer cents; keep currency; do not convert FX; drop non-USD.
- Dedupe on `id` (keep the newest `scraped_at`).
- Drop kids' items and eBay auctions (an auction's price is the current bid).
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
   composition percentages, % with certification, % with a region, median price. Write to `pipeline/REPORT.md`.

## 12. Testing (red/green TDD)

Every piece of computational code gets a failing test first.
- `listing.py`: enum and field parity with `schema/api.schema.json`; a sample row validates; rows with
  seller identity fields are rejected.
- `extract.py`: composition cases (percent, synonyms, organic/recycled), certifications, flags, "vegan
  leather" vs "genuine leather", structured-over-text, product-line inference, the 90–110 rule.
- Mappers: one test per marketplace on sanitized real samples in `tests/fixtures/`, covering price→cents,
  condition, category, region, drop rules.
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
condition and location; whether eBay exposes shipping; the real seller-count fields; and which
fields carry seller identity (for scrubbing).

If Depop and Poshmark both fail, switch to `123webdata/depop-scraper` (detail mode) and
`xtracto/poshmark-detail-scraper`. If those fail too, raise it with the team.

## 13a. Test-run results (Oct 24, 2026, 1 query × 20 items per actor, measured cost $0.535)

| Actor | Core fields | Description > 40 chars | Images avg | Location | Cost | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| Depop | 20/20 | 18/20 | 4.0 | `country` US 20/20 | $0.020 | pass |
| Poshmark | 20/20 | 15/20 (at the threshold) | 6.8 | none (recorded as US) | $0.060 | pass |
| Grailed | 20/20 | 20/20 | 8.2 | listing location US 4/20, seller country US 6/20 | $0.240 | pass |
| eBay | 20/20 | 20/20 | 7.3 | US 20/20 | $0.120 | pass |
| Mercari (`getascraper`) | 20/20 | **0/20** | **1.0** | none | $0.095 | **fail** |

- The price table in §6 was right for every actor except Mercari, which also bills **$0.04 per search request**
  (SCRAPING.md had this; §5 did not). eBay's `includeDescription` costs nothing extra. A run's
  `usage_total_usd` is a stale snapshot when `call()` returns, so the log records our own estimate instead.
- Depop returns `description`, `originalPrice` and `country`. Poshmark returns no condition and no location.
  Grailed returns `location` as a region ("Asia"), the seller country in `sellerProfile.country_code`, a per-region
  shipping rate and `priceDrops` (earlier prices). eBay has `itemSpecifics` but no `Material` key.
- Seller identity found and removed by the scrubber: Grailed `sellerProfile`, eBay `about_this_seller_section_module`
  and feedback modules. Depop product URLs and slugs begin with the seller's handle: they are kept in `url` for the
  link-out, and replaced in the committed fixtures. Sellers also sometimes write their own store name into the
  description text, which is kept.
- Coverage on this single generic query (north face jackets): stated material 41%, percentages 6%. Material-rich
  queries should lift both; check after the 20k run.

## 13b. Mercari, second attempt

**Why `getascraper/mercari-us-scraper` failed** (run log, three probes, two research passes):
- It never opens a listing. Its log reads `Fallback: Extracting first-page hydrated listings from Next.js payload`, and its
  search-API path produced nothing in any run. That payload holds only card data. The zero-valued fields (`id`,
  `likes_count`, `sales_count`, `seller_review_count`) are placeholders (its dataset schema says so), and the README
  sample is synthetic (fake listing id, timestamp before the actor existed).
- Listing URLs do not help: given two item URLs it returned the same card fields, plus an unrelated listing.
- It is flaky: the same query returned 20 listings once and 0 the next time, billing $0.04 for nothing. Its public
  "221/222 runs succeeded" counts a run that returns 0 rows as a success.
- Mercari's own prices were suspected and cleared: both actors report the same discounted prices (e.g. 23.94, was 27.94).

**Alternatives probed (3 items each):** `automation_craft/mercari-us-scraper` and `tortuga/mercari-scraper` returned
identical descriptions, photo counts and shipping fees for the same three listings. `parsebird/mercari-us-scraper`
was not probed: its public stats show only 155 of 221 runs succeeding.

**`automation_craft` through the real pipeline** (a 20-item smoke test, then 80 + 80 + 40 + 150 items for `carhartt detroit
jacket`, `100% wool sweater`, `nike dunk low` and `100% wool coat`; 370 raw rows; billed $1.04, equal to our estimate):

| Measure | Result |
| --- | --- |
| Core fields (url, title, price, photo) | 346/346 |
| Description > 40 chars | 326/346 (94%) |
| Photos | 8.0 on average, none with a single photo |
| Size / condition / shipping known / seller type | 344 / 346 / 346 / 346 of 346 |
| Seller rating (0 reviews = unknown) | 299/346 |
| Stated material / with percentages | 242/346 (70%) / 173/346 (50%) |
| Demo props | Carhartt Detroit 68 listings, Nike Dunk Low 33 |
| Kids' items | 8 of 20 in the unfiltered smoke test; 6 of 350 once `excludeKeywords` was added |
| Color | 0/346 (Mercari rarely has it) |
| A 150-item run (two results pages) | 150 delivered in 106 s, no warnings; 7 duplicates across queries were collapsed |

Mercari's total price is `price + shipping (only when the buyer pays) + buyer-protection fee`, checked on 25 of 25
rows. `cost.total_cents` includes the shipping but not the fee.

The real run also exposed two pipeline bugs, fixed here: JSON Lines were mis-split on U+2028 (decision 18) and invisible
characters survived into the text (decision 19).

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
- Every row has ≥ 1 image URL, a USD price, and a recorded region.
- ≥ 25% of rows have at least one stated material; ≥ 10% have percentages. If below, add material-rich
  queries.
- The three demo props are present (Carhartt Detroit jacket, Patagonia Better Sweater, Nike Dunk Low).
- No seller identity fields in `data/raw` or `data/listings.jsonl`.
- `pytest` passes; `REPORT.md` committed.

## 16. Open items and risks

- Mercari (`automation_craft`) is 11 days old and lightly used. It ran cleanly in all 8 runs (400 listings, up to 150 per run =
  two pages); the plan's 300-item queries span three pages, so watch the first real Mercari runs, and keep `tortuga/mercari-scraper` as the fallback.
- Grailed costs $0.012 per row and is the biggest line; its quota is where to trim.
- Depop returned US items 20/20 in the test run; check the country spread on the full run.
- 50k (~$235) may exceed the ~$200 credits (§6). Decide quotas after the 20k run.
- `seller.type`: Grailed and Depop have no common scale. Grailed uses the seller's listing count (≤20 / ≤200 / more); eBay uses
  account type and feedback score (business with ≥ 5000 feedback is a large reseller); Depop and Poshmark give none (null). All guesses.
- Material coverage may fall short of the 25% / 10% targets; the fix is more material-rich queries.
- Multi-part tags: 53 of 346 Mercari rows (15%, 49 of them coats) are `composition_suspect`, and 47 of those are "shell, then a
  100% lining". A parser that reads the "Shell:" / "Lining:" labels would recover them. Not built: picking the first group
  instead would give a wool coat a polyester label whenever the seller lists the lining first.
- Terms of service (see §5).
- The two product specs differ (new+used vs secondhand-only; eco score vs eco facts). Decision 1 and 2
  settle this for the pipeline; the team should reconcile `DESCRIPTION.md`.
