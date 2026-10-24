# Sift — Scraping and Ingest Spec (for coding agents)

Location: `backend/pipeline/SCRAPING.md`. How these fields surface to the web is defined in `schema/API.md`.
Audience: an AI coding agent (or Andy) working in `backend/pipeline/` and `backend/database/`.
Read fully before writing code. Facts marked **verified** were read off the actor
page or docs on Fri Oct 23, 2026. Facts marked **assumption** must be confirmed by
the 20-item test run before the full scrape.

## 0. Goal and hard rules

Build a Postgres table of secondhand clothing listings with, per listing: the
fields needed for three markers (cost, fabric/product quality, eco), the full
description text, all image URLs, and a 768-d image embedding.

- Index size: 20,000 listings first, verify the app end to end, then grow to
  ~50,000 overnight. Apify credits (~$200) cover this.
- Scraping happens only during the build. **Nothing is scraped at request time.**
- Store **no seller personal identifiers** (no usernames, no profile URLs).
  Derive `seller_type` and `seller_listing_count`, then discard the username.
- Never invent material or sustainability values. If the text does not state it,
  the field is `null`, and the evidence record says `unknown`.
- Keep the raw actor record in `raw jsonb` next to the normalized columns so a
  new idea never needs a re-scrape.
- Every Apify `.call()` passes `max_total_charge_usd`.
- Python 3.12, `uv`, `apify-client>=3.3` (typed: `run.default_dataset_id`),
  `supabase>=2.33`. Secrets only in `.env` (`APIFY_TOKEN`, `SUPABASE_URL`,
  `SUPABASE_SECRET_KEY`, `ANTHROPIC_API_KEY`).

## 1. Marketplaces and actors (verified Oct 23, 2026)

| Marketplace | Primary actor | Mode / inputs that matter | Price (free tier) | Returns description? | Fallback |
| --- | --- | --- | --- | --- | --- |
| Depop | `jongoose/depop-scraper` | `query`, `maxItems`, optional `startUrls`; datacenter proxy default | $0.001/result | listed in schema, **absent from the sample record → verify in test run** | `123webdata/depop-scraper` detail mode ($0.00999, has description) |
| Poshmark | `123webdata/poshmark-scraper` | `categoryUrls` = Poshmark search URLs, `scrapeProductDetails: true` | $0.00199/detail + $0.01 start | yes (detail mode) | `xtracto/poshmark-detail-scraper` ($0.003, has `condition`, which 123webdata lacks) |
| Grailed | `piotrv1001/grailed-listings-scraper` | `scrapeDetails: true` | $0.01 with details ($0.003–0.005 without) | detail mode only | `lulzasaur/grailed-scraper` ($0.01, 1,000/query cap) |
| Mercari US | `getascraper/mercari-us-scraper` | search queries; built-in US residential proxy | $0.00275/listing + $0.04/search | yes | none cheap; use more Depop/eBay |
| eBay | `memo23/ebay-search-scraper-ppe` | search queries, `includeDescription: true`; detail mode for `itemSpecifics` | $0.003 fast / $0.005 detail + $0.02 start | yes | eBay Browse API (free, 5k calls/day; `Material` needs `getItem` per item) |

Do not use `markdolanmoore/depop-scraper` (no description) or
`parsebird/mercari-us-scraper` (30% non-success in the last 30 days).

Budget at 20k: ≈ $67 (Depop 8k $8, Poshmark 4k $8, Grailed 3k $30, Mercari 3k
$11, eBay 2k $10). At 50k ≈ $150. Grailed detail mode is the expensive line.

## 2. Query plan

Categories (final, 8): jackets and outerwear, hoodies and sweatshirts, t-shirts
and graphic tees, sneakers, jeans and pants, sweaters and knitwear, shirts
(flannels, button-ups, overshirts), dresses and skirts.

**US only.** Keep a listing only when the seller or item location is in the US:
Depop `country == "US"`, eBay marketplace `EBAY_US` with item location US,
Mercari US (US by construction), Grailed and Poshmark filtered on location when
the record carries it; drop records whose currency is not USD.

Per category, ~25 queries per marketplace mixing:

- brands judges wear: Carhartt, Patagonia, The North Face, Nike, New Balance,
  Levi's, Uniqlo, Arc'teryx, Columbia, Champion, Adidas, Dr. Martens;
- silhouettes: boxy tee, oversized hoodie, cropped jacket, wide-leg pants;
- material-rich phrases (so the eco re-rank visibly changes results):
  "100% cotton", "100% wool", "merino", "cashmere", "linen", "organic cotton",
  "recycled polyester", "deadstock", "vintage wool";
- demo props by exact title (Carhartt Detroit jacket, Patagonia Better Sweater,
  Nike Dunk Low) so the first scan always hits;
- ~10% of tee queries aimed at "conference tee" / "hackathon shirt".

Queries live in `backend/pipeline/queries.yaml` keyed by category then marketplace.
Cap each query with `maxItems` (200–500) so the long tail of one query cannot
eat the budget.

## 3. Fields to capture per listing

Normalize every actor record into this shape (Pydantic `Listing` in
`backend/src/backend/models.py`). Field names differ per actor; the mapping lives in
`backend/pipeline/normalize/<marketplace>.py`.

### Identity and linking (required)

| Field | Source | Notes |
| --- | --- | --- |
| `marketplace` | constant | `depop` `poshmark` `grailed` `mercari` `ebay` |
| `external_id` | actor id field, else last path segment of `url` | unique with `marketplace` |
| `url` | actor | the link-out |
| `title` | actor | |
| `description` | actor (detail mode where needed) | full text; extraction runs on it |
| `image_urls[]` | actor | **all images**, not only the first; later images are where care tags appear |
| `status` | actor | active / sold; index active only, keep sold for comps |
| `scraped_at` | now | |
| `raw` | whole actor record | `jsonb` |

### Cost

| Field | Source | Notes |
| --- | --- | --- |
| `price_cents`, `currency` | actor | convert to cents; keep currency, do not convert FX |
| `original_price_cents` | actor when returned (Depop `originalPrice`, Poshmark markdowns) | null otherwise |
| `retail_price_cents` | text regex `retail(s)? (for )?\$?(\d+)` or an actor field | null otherwise; the UI shows "vs retail" only when present |
| `shipping_cents` / `free_shipping` | actor when returned | assumption: eBay and Mercari expose it; verify |
| `condition`, `condition_raw` | actor | keep the raw string; map to `new_with_tags` `like_new` `good` `fair` |

### Fabric and product quality

| Field | Source | Notes |
| --- | --- | --- |
| `brand` | actor | normalize case; the join key for brand-level facts |
| `size`, `color` | actor | raw strings |
| `category`, `subcategory` | actor labels, else the query's category | marketplace label beats vision guess |
| `materials[]` | extraction (§4) | `[{fiber, pct, organic?, recycled?}]` |
| `synthetic_share` | derived | sum of synthetic fiber pct; null if no composition |
| `certifications[]` | extraction | `gots` `oeko_tex` `bluesign` `fair_trade` `rws` `rds` `b_corp` |
| `country_of_manufacture` | eBay `itemSpecifics`, text regex `made in (\w+)` | |
| `ebay_specifics` | eBay detail rows | keep whole `itemSpecifics` dict in `raw`; map Material, Fabric Type, Lining, Style, Fit |
| `is_vintage`, `is_deadstock`, `is_upcycled` | text keywords | booleans |

### Eco (derived from the above, no new scraping)

`animal_materials` (any of leather, wool, cashmere, silk, down, alpaca, mohair),
`recycled_or_deadstock`, `synthetic_share`, `seller_region` (below), era keywords.

### Seller (store these four, nothing else)

| Field | Source | Notes |
| --- | --- | --- |
| `seller_listing_count` | actor seller block when present | used in memory to derive `seller_type`; username discarded |
| `seller_type` | derived | `individual` (≤ 20 listings) / `small_shop` (≤ 200) / `large_reseller`; thresholds set after the test run |
| `seller_rating` | actor when present | number, no identity |
| `seller_region` | Depop `country`, eBay `itemLocation`, Mercari state when present | coarse only (state/country), also the US-only filter |

Nothing else about the seller is stored: no username, profile URL, avatar, or
full location.

### Sold comps: out of scope for now

Not part of the build. If a resale-retention number is wanted later, it is one
extra actor run (`kalilfagundes.w/resale-sold-comps-scraper`, ~5k rows, ~$8
before Oct 27) into a `sold_comps` table with `brand, category, condition,
sold_price_cents, original_price_cents, sold_at, listed_at, days_to_sell`, then
a median per (brand, category). Do not start it without a team decision.

### Brand facts (hand-curated, not scraped)

`brands` table, ~40 rows: `name, repair_program (bool + url), published_supplier_list
(bool + url), material_commitments (text + url), certifications[] + url`.
Every claim has a `source_url`. Optional: Apify Website Content Crawler on brand
sustainability pages, then an LLM extracts claims with quoted snippets.

## 4. Extraction rules (run once at ingest, in this order)

1. **Regex pass** over `title + " " + description + specifics`:
   - composition: `(\d{1,3})\s*%\s*(organic\s+|recycled\s+)?(cotton|polyester|poly|nylon|polyamide|wool|merino|linen|hemp|silk|viscose|rayon|modal|lyocell|tencel|acrylic|elastane|spandex|lycra|cashmere|alpaca|mohair|leather|down)`
   - synonyms → canonical: poly→polyester, polyamide→nylon, spandex/lycra→elastane, rayon→viscose, tencel→lyocell
   - bare material words with no percent ("100% cotton" absent but "cotton tee" present) → `materials=[{fiber, pct:null}]`, evidence `claimed`
   - certification keywords (case-insensitive, hyphen-tolerant): GOTS, OEKO-TEX, bluesign, Fair Trade, RWS, RDS, B Corp
   - flags: vintage, deadstock, upcycled, "vegan leather" (→ synthetic, not animal), "genuine leather" (→ animal)
2. **Structured fields win over text**: eBay `Material` specific, Poshmark material attribute.
3. **Known product lines** (small table, `product_lines.yaml`): e.g. Carhartt Detroit → cotton duck; Patagonia Better Sweater → recycled polyester. Evidence `inferred`, lower weight than stated.
4. **LLM fallback** (`claude-haiku-5-5`, structured output) only for listings that contain a material word but no clean parse. Cap: 2,000 calls per batch.
5. **Evidence record** per field: `{field, status: verified|claimed|inferred|unknown, source: specifics|listing_text|product_line|tag_image|model, snippet}`.
6. **P1, after the golden path works**: run the care-tag OCR over `image_urls[1:]` for listings with no composition; tag-read values get status `verified`, source `tag_image`.

Percentages that sum to 90–110 are normalized to 100; outside that range the
composition is kept but flagged `composition_suspect=true`.

## 5. Pipeline steps (one script each, rerunnable, idempotent)

1. `01_scrape.py` — for each (category, marketplace, query): run the actor with
   `max_total_charge_usd`, write the dataset items to `data/raw/<marketplace>/<run_id>.jsonl`.
   Log items returned and charge per run.
2. `02_normalize.py` — raw → `Listing`; drop records without `url`, `title`, `price`, or at least one image; dedupe on `(marketplace, external_id)`.
3. `03_extract.py` — §4 rules; writes `materials`, `synthetic_share`, `certifications`, flags, evidence.
4. `04_thumbs.py` — download `image_urls[0]`, resize to 384 px JPEG (256 px if the index passes 40k), upload to Supabase bucket `thumbs/<marketplace>/<external_id>.jpg`, set `thumb_url`. Thread pool of 16; retry twice; skip on failure (`thumb_url=null`, still indexed).
5. `05_embed.py` — embed the thumbnail with `backend.embed.embed_image` (Marqo-FashionSigLIP, 768-d, `normalize=True`). Batches of 64. Run on a Modal T4 (minutes) or laptop CPU (~40 min per 20k).
6. `06_upsert.py` — `supabase.table("listings").upsert(rows, on_conflict="marketplace,external_id")` in chunks of 500.
7. `07_report.py` — prints per marketplace: rows, % with description, % with any material, % with composition pct, % with certification, median price, thumbs failed. Paste the output into the Devpost write-up.

Steps 4–5 should stream (download → resize → embed → upsert per batch) so a
crash halfway loses one batch, not the night.

## 6. Test run first (Friday ~6:30 PM, go/no-go input)

For each primary actor, one query, `maxItems: 20`. Pass criteria:

- ≥ 18 of 20 records have `url`, `title`, `price`, `image_urls` non-empty;
- `description` present and non-trivial (> 40 chars) on ≥ 15 of 20 for Depop (jongoose), Poshmark (detail), Grailed (details), Mercari, eBay (`includeDescription`);
- total charge < $1.
- Also: classify the extra images of those ~100 records as tag / not tag with one Haiku call each (~$0.03) and record the per-marketplace care-tag rate for the pitch.

If Depop and Poshmark both fail, switch Depop to `123webdata` detail mode and
Poshmark to `xtracto`; if those fail too, raise it to the team (pivot rule).

## 7. Acceptance for the full index

- ≥ 20,000 active rows across ≥ 4 marketplaces, no marketplace above 50% of the total.
- Every row has a 768-d embedding and a `thumb_url` or a working `image_urls[0]`.
- ≥ 25% of rows have at least one stated material; ≥ 10% have percentages (expect eBay and Grailed to carry this; if below, add material-rich queries).
- The three demo props return themselves in the top 3 of a `/search`.
- `07_report.py` output committed to `backend/pipeline/REPORT.md`.

## 8. Things that will bite

- Poshmark's terms prohibit automated collection; Depop and Mercari sit behind Cloudflare. Use the actors above (96%+ success over 30 days), run Friday night only, store no seller identity, link out. Say this in the Trust section.
- Field names differ per actor (`price.amount` vs `price`, `pictureUrls` vs `images`); write one mapper per marketplace and unit-test it on the 20-item samples.
- Grailed caps 1,000 results per search; split by brand.
- Mercari charges per search ($0.04): use fewer, broader queries there.
- Venue wifi: run the scrape and the thumbnail download from the venue early, or from a hotspot; both are network-bound.
