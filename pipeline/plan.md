# Pipeline Plan (`pipeline/`)

The data layer for Thrift Lens. It finds new and thrifted clothes, cleans them, adds eco facts, and stores everything in Supabase. After that, `ml/` takes over (embeddings, matching, ranking).

Written 2026-10-23. Nothing here is built yet. Actor names and prices come from the live Apify Store on this date. They can change, so every Actor must pass a small test run first (Section 6).

---

## 1. Goals and limits

**Goals**
1. Collect about 20k clothing listings from resale sites (and some new-clothing sites).
2. Turn each listing into one clean, same-shaped record.
3. Add eco facts to each record (fabric, certifications, where it was made, seller size).
4. Say how sure we are about each eco fact. Never guess silently.
5. Take care-tag scans and merge them into the clothing data.
6. Store it all in Supabase so `ml/` and `web/` can read it.

**Not our job (pipeline does NOT do these)**
- Making embeddings. Anthony's `ml/` does that. We leave the `embedding` column empty.
- Reading care-tag photos (OCR). `ml/` does that. We only store and merge the result.
- Search, ranking, matching, UI.

**Rules**
- Never scrape during the demo. Everything is pre-built.
- Public listing data only. No seller names, handles, or personal info.
- Link back to the original listing.
- Eco numbers are always estimates ("est.") and always have a cited source.
- "Unknown" is a normal, honest answer. It is not an error.
- Follow `CLAUDE.md`: new branch per feature, never push to main, red/green TDD for computing code, keep code short and simple.

---

## 2. The big picture

```
 Apify Actors (listings)      Reference data (eco facts)       Tag scans (from ml/)
 Depop, Poshmark, Grailed,    Wikirate scores, Open Supply     brand, fabric %, country,
 Mercari, eBay, ThredUp,      Hub, fiber factors, weights,     RN number, certifications
 new-clothing sites           displacement rates
        |                              |                              |
        v                              v                              v
  1. SCRAPE  -->  raw files     5. REFERENCE LOAD              6. TAG MERGE
        |        (jsonl on disk)        |                              |
        v                              |                              |
  2. NORMALIZE  (one shape)            |                              |
        |                              |                              |
        v                              |                              |
  3. EXTRACT  (fabric, certs, ...)     |                              |
        |                              |                              |
        v                              v                              v
  4. ENRICH  (seller type, brand, eco evidence, savings numbers)  <---+
        |
        v
  7. THUMBNAILS  -->  8. LOAD into Supabase (upsert)
                              |
                              v
                     ml/ fills in embeddings  ->  web/ reads results
```

Each step is a small Python module that reads one thing and writes one thing. Steps can be re-run on their own. Raw data is saved first, so we can fix a bug in step 2 or 3 and re-run without paying Apify again.

---

## 3. Folder layout

```
pipeline/
  plan.md                  <- this file
  pyproject.toml           <- uv project (own deps)
  .env.example             <- names only: APIFY_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_KEY, LLM key
  config.yaml              <- queries, Actor inputs, caps, thresholds
  migrations/              <- SQL files, numbered (0001_init.sql, ...)
  data/                    <- gitignored
    raw/<source>/<run_id>.jsonl
    samples/<source>.jsonl      <- 25-item test runs (kept as test fixtures)
    cache/                      <- RN lookups, certification lookups, thumbnails
  src/thriftlens_pipeline/
    models.py              <- Pydantic models (Listing, Evidence, TagScan, ...)
    scrape.py              <- run Actors, save raw
    sources/               <- one small adapter per source
      depop.py poshmark.py grailed.py mercari.py ebay.py thredup.py asos.py ...
    extract.py             <- fabric, certs, color, etc. from text
    fibers.py              <- fiber names + synonyms (poly -> polyester)
    sellers.py             <- seller size + fast-fashion list
    brands.py              <- brand matching and brand scores
    evidence.py            <- evidence levels and merge rules
    footprint.py           <- savings math (CO2, water, dollars)
    tags.py                <- tag scan clean-up and merge
    reference.py           <- load fibers, weights, factors, displacement rates
    thumbs.py              <- download small images
    load.py                <- upsert into Supabase
    cli.py                 <- `python -m thriftlens_pipeline <command>`
  tests/
    fixtures/              <- real sample items from step 0
    test_*.py
```

Assumption: migrations live in `pipeline/migrations/` for now because we only work in `pipeline/`. They can move to `database/` later.

---

## 4. Data sources

### 4.1 Secondhand listings

Each row: first choice, then backup. Prices are per 1,000 results.

| Site | First choice | Why | Backup |
|---|---|---|---|
| Depop | `abotapi/depop-scraper` (about $1+/1k) | Has a `material` field when `fetchDetails` is on. Also description, brand, condition, colors, sizes, seller sales count. | `piotrv1001/depop-listings-scraper` ($4/1k, no material) |
| Poshmark | `shahidirfan/poshmark-listings-scraper` (about $0.80-1/1k) | Cheapest. Has description, brand, original price, size, condition, colors. | `gauzy_penguin/poshmark-scraper`, `abotapi/poshmark-scraper` |
| Grailed | `piotrv1001/grailed-listings-scraper` ($3/1k, $12/1k with details) | Best fields. Has `soldOnly` mode for sold prices. Seller sales count. | `shahidirfan/Grailed-Product-Scraper`, `jungle_synthesizer/grailed-resale-listings-scraper` |
| Mercari US | `getascraper/mercari-us-scraper` (about $2-3/1k) | Active AND sold listings. Has `original_price` (retail). Needs US residential proxy. | `automation_craft/mercari-us-scraper` |
| eBay | `delicious_zebu/ebay-product-listing-scraper` (search) then `delicious_zebu/ebay-product-details-scraper` (details) | Search has no material or description. Only the details Actor returns `item_specifics` (Material, Brand, Department) and full text. Run details only on clothing results. | `memo23/apify-ebay-search-cheerio` |
| ThredUp | `abotapi/thredup-scraper` (about $1.5/1k) | Best material data: `materials[]`. Also real retail price (`msrp`) and measurements. Needs US residential proxy. | `logiover/thredup-scraper` |

Later / optional: Vinted (`kazkn/vinted-smart-scraper`), The RealReal (`piotrv1001/the-realreal-listings-scraper`), Etsy (`epctex/etsy-scraper`) for small-shop vintage.

Sold comps (typical resale price, days to sell): Grailed `soldOnly`, Mercari `sold_out`, `caffein.dev/poshmark-sold-listings`. Stored with `status = sold`. Lower priority.

### 4.2 New clothing (kept open)

We keep new clothing in the design from day one. It is just another `kind` of listing.

- Candidates: `epctex/asos-scraper` ($2.6/1k), `madeingermany/forever21-scraper`, `studio-amba/boohoo-scraper`. More can be found with the same Store search.
- New-clothing sites usually print the fabric mix clearly. That makes them a good source of fabric data and retail prices, even if we never show them as results.
- Decision is delayed. The schema supports both:
  - `kind = 'secondhand'` or `kind = 'new'`
  - Search in `ml/` can filter on `kind`.
  - Savings math can compare "new price" vs "secondhand price".

### 4.3 Eco reference data (not listings)

| Need | Source | How we get it | Notes |
|---|---|---|---|
| Brand transparency and labor scores | Wikirate: Fashion Transparency Index 2025, Clean Clothes "Fashion Checker", Apparel 100 | Wikirate account, export CSV or JSON, or use its API | CC BY-NC 4.0 / CC BY 4.0. Non-commercial is fine for a hackathon. Show credit. |
| Factories and countries | Open Supply Hub | Free account, API token, `/facilities` search, or CSV download by country | Shows where a brand's factories are, not which one made one item. |
| Who owns an RN number (US tag ID) | FTC RN database | Web lookup only, no API or bulk file | Small crawler, cache every answer. Only look up RNs we actually see. |
| B Corp status | B Corp directory | No bulk download found. Curate a list of apparel B Corps by hand or crawl. | About 30-50 brands is enough. |
| Certifications (GOTS, OEKO-TEX) | GOTS public database, OEKO-TEX Label Check | Web lookups by license or product ID. No API found. | Only mark "certified" if we find a license or ID. |
| Fiber impact numbers | Textile Exchange LCA studies (polyester, cotton, cashmere out now; nylon, wool planned), Carbonfact open LCA database | Read the papers, copy numbers by hand into `fibers` with the source URL | Higg MSI and ecoinvent are licensed, so we skip them. |
| Garment weights | Published LCAs and industry reports (Higg, WRAP, academic papers) | Copy by hand with source | One typical weight per category. |
| How often a secondhand buy replaces a new buy | WRAP "Displacement Rates Untangled" (2025): 64.6% for peer-to-peer resale. Kansas State thesis: about 68% (US). | Copy by hand with source | Savings = new-item footprint x about 0.65, not x 1. |
| Country electricity and water stress (optional) | Ember (grid carbon), WRI Aqueduct (water stress) | Download CSV | Only if time allows. |
| Brand ratings API | Good On You | Enterprise only | Skip. |

Important: **no free dataset tells us what a specific resale item is made of.** Most listings never say. So many records will have fabric = unknown. That is expected.

---

## 5. Data model (Supabase / Postgres)

Idea: one main `listings` row per item, plus small tables for shared facts. We do NOT put every fact in one giant object, because brand, fiber, and factory facts would be copied thousands of times and could not be updated in one place. The `listings` row still has all the main datapoints that `ml/` needs, in one place.

### 5.1 `listings` (the "clothing object")

**Identity**
| Column | Type | Meaning |
|---|---|---|
| `id` | text, primary key | `"<source>:<source_id>"`, e.g. `depop:960104883` |
| `source` | text | depop, poshmark, grailed, mercari, ebay, thredup, asos, ... |
| `source_id` | text | the site's own id |
| `kind` | text | `secondhand` or `new` |
| `status` | text | `active`, `sold`, `expired` |
| `url` | text | link to the original listing |
| `scraped_at` | timestamptz | when we got it |
| `listed_at` | timestamptz null | when seller posted it |
| `sold_at` | timestamptz null | for sold comps |

**What it is (used for matching and chips)**
| Column | Type | Meaning |
|---|---|---|
| `title` | text | |
| `description` | text null | seller text |
| `brand_id` | int null | link to `brands` |
| `brand_raw` | text null | brand as written |
| `category` | text | our small fixed list: outerwear, hoodie, tee, sneakers, pants, dress, ... |
| `category_raw` | text null | site's own category |
| `gender` | text null | women, men, unisex, kids |
| `size_raw` | text null | as written |
| `size_norm` | text null | cleaned (S, M, L, 32, 9.5 ...) |
| `condition_raw` | text null | |
| `condition_norm` | text null | `new_with_tags`, `like_new`, `good`, `fair` |
| `colors` | text[] | |
| `style_tags` | text[] | vintage, graphic, boxy, ... if the site gives them |
| `image_url` | text | main photo |
| `image_urls` | text[] | all photos |
| `thumb_path` | text null | our small copy in Supabase Storage |
| `measurements` | jsonb null | chest, length, ... if given |
| `embedding` | vector(N) null | **left empty. `ml/` fills it.** N is set when Anthony picks the model. |

**Price**
| Column | Type | Meaning |
|---|---|---|
| `price_cents` | int | current asking price |
| `currency` | text | |
| `shipping_cents` | int null | |
| `retail_price_cents` | int null | only when the site truly shows it (ThredUp `msrp`, Mercari `original_price`, new-clothing sites) |
| `retail_source` | text null | `site_msrp`, `site_original_price`, `brand_page`. Never invented. |
| `sold_price_cents` | int null | sold comps |

**Eco facts (every one has a matching evidence record, see 5.3)**
| Column | Type | Meaning |
|---|---|---|
| `materials` | jsonb null | `[{"fiber":"cotton","pct":100,"organic":false}]` |
| `synthetic_share` | int null | 0-100 |
| `natural_share` | int null | 0-100 |
| `certifications` | text[] | `oeko_tex_100`, `gots`, `bluesign`, `fair_trade`, `rws`, `rds`, `ocs`, ... |
| `animal_materials` | bool null | wool, leather, down, ... |
| `recycled_or_deadstock` | bool null | |
| `country_of_origin` | text null | from tag or listing |
| `weight_kg_est` | numeric null | from category weight table |
| `co2_new_kg_est_low`, `co2_new_kg_est_high` | numeric null | footprint of making this item new, as a range |
| `water_new_l_est_low`, `water_new_l_est_high` | numeric null | same, for water |
| `co2_saved_kg_est_low`, `co2_saved_kg_est_high` | numeric null | new footprint x displacement rate. Only for `kind = secondhand`. |
| `water_saved_l_est_low`, `water_saved_l_est_high` | numeric null | same |
| `dollars_saved_cents` | int null | `retail - price`, only if retail is known |
| `seller_id` | int null | link to `sellers` |
| `seller_type` | text null | `individual`, `small_shop`, `large_reseller`, `brand_store` |
| `is_fast_fashion_brand` | bool null | from blocklist |
| `eco_unknown_count` | int | how many eco facts are still unknown (handy for ranking) |

**Safety net**
| Column | Type | Meaning |
|---|---|---|
| `raw` | jsonb | the full original item from Apify. Nothing is ever lost. |
| `product_id` | int null | link to `products` (5.2) once we group same garments |

Indexes: `(source, source_id)` unique, `category`, `kind`, `brand_id`, `price_cents`, `size_norm`. No vector index needed at 20k rows.

### 5.2 Side tables

**`brands`**
`id, name, name_norm, parent_company, country, is_fast_fashion, is_b_corp, fti_score, fti_year, fashion_checker_score, claims jsonb, notes, source_urls text[]`
Every score row stores where it came from. Brand facts are always "brand-reported", never "verified".

**`sellers`** (no names or handles)
`id, source, source_seller_hash, listing_count, items_sold, rating, rating_count, type`
`source_seller_hash` is a one-way hash so we can count a seller's listings without storing who they are.

**`fibers`** (reference)
`fiber, class (plant | animal | synthetic | regenerated), synonyms text[], co2_kg_per_kg_low, co2_kg_per_kg_high, water_l_per_kg_low, water_l_per_kg_high, notes, source_url, source_year`
Numbers are only added with a citation. If we have no good number, the cell stays empty.

**`garment_weights`** (reference)
`category, weight_kg_low, weight_kg_high, source_url`

**`displacement_rates`** (reference)
`channel (peer_to_peer, thrift_store, ...), rate, source_url, region`. Start with 0.646 (WRAP).

**`products`** (optional, later)
A "same garment" group: `id, brand_id, model_name, category, canonical_materials jsonb`. Many listings can point at one product. A tag scan of one jacket can then teach us the fabric for every listing of that same jacket. Built after the basics work.

**`facilities`** (optional, later)
`id, os_id, name, country, sector, parent_company, brand_ids int[]` from Open Supply Hub.

**`tag_scans`**
`id, created_at, image_path, brand_raw, brand_id, rn_number, wpl_number, composition jsonb, country_of_origin, care text[], certifications text[], raw_text, confidence, garment_category, listing_id null, product_id null, status`

**`evidence`** (see 5.3)

**`rn_cache`**
`rn_number, company_name, address_country, looked_up_at, raw`. Avoids repeat lookups.

### 5.3 Evidence: how sure are we?

Every eco fact on a listing has an evidence record:

`evidence(listing_id, attribute, value jsonb, level, source, snippet, url, created_at)`

`attribute` is one of: `materials`, `synthetic_share`, `certifications`, `animal_materials`, `recycled_or_deadstock`, `country_of_origin`, `seller_type`, `fast_fashion`.

`level`, from strongest to weakest:

| Level | Meaning | Example |
|---|---|---|
| `tag_verified` | Read off the care tag | "55% cotton 45% poly" from tag scan |
| `certified` | A real certificate ID was checked | GOTS license found |
| `stated` | The seller or site said it | Description says "100% wool" |
| `brand_reported` | The brand says it, not checked | Brand page claims organic cotton |
| `inferred` | We guessed from brand + category | "Patagonia Better Sweater, so polyester" |
| `unknown` | No information | |
| `contradicted` | Two sources disagree | Seller says cotton, tag says poly |

Rules:
- Higher level wins when picking the value shown in `listings`.
- If two levels disagree, keep both evidence rows and mark `contradicted`.
- A weaker level never overwrites a stronger one.
- The UI badges map to this: Verified = `tag_verified` or `certified`, Claimed = `stated` or `brand_reported`, Unknown = `inferred` or `unknown`.

---

## 6. Step by step: how the pipeline runs

### Step 0. Sample run (first thing we build)

For each chosen Actor: run it with 25 items and a small spending cap (about $0.50). Save the output to `data/samples/<source>.jsonl`. These files become our test fixtures.

Check and write down, per Actor:
- Does it return description? materials? retail price? all photos? seller counts?
- Is the output stable (same field names every run)?
- Does it need a residential proxy?
- Cost per 1,000 in practice.

Pick the winner per site by field coverage first, price second. Ask the user to approve cost before any paid run.

### Step 1. Scrape (`scrape.py`)

- Uses `apify-client` (not `apify`). Token comes from the `APIFY_TOKEN` env var. Never in code or logs.
- Call shape: start the Actor with `run_input` and a `max_total_charge_usd` cap. The cap goes on the call, not in the input.
- Wait for a final status: `SUCCEEDED`, `FAILED`, `TIMED-OUT`, `ABORTED`. On failure, read `statusMessage` and `exitCode`, then retry once or switch to the backup Actor.
- Save every dataset item to `data/raw/<source>/<run_id>.jsonl`. Also save a small `run.json` next to it (Actor name, input, cost, time).
- Queries come from `config.yaml`. Three groups:
  1. Category terms: jackets, hoodies, graphic tees, sneakers, tech event tees (matches the spec).
  2. Material terms: "100% wool", "organic cotton", "linen", "hemp", "deadstock", "GOTS", "OEKO-TEX", "recycled polyester". These make sure fabric-based filtering has real data to work with.
  3. Demo props: Carhartt jacket, Patagonia fleece, Nike Dunks, and anything else the demo team names.
- Runs one source at a time. A run can be resumed using its run ID or the Actor's own resume option (Depop has one).
- Budget guard: total spend for a full run is tracked in `data/raw/budget.json`. Stop if over the limit in `config.yaml`.

### Step 2. Normalize (`sources/*.py`, `normalize`)

One small function per source: `raw item -> Listing`. Rules:
- Fill the common columns from Section 5.1. Missing stays `null`.
- Prices become integer cents. Keep currency.
- Sizes and conditions get a `_raw` and a `_norm` version using small lookup tables.
- Categories map to our fixed list. If unsure, `category = 'other'`.
- Keep the original item in `raw`.
- Strip seller identity. Keep only counts and rating, plus a hash.
- `kind` is set per source (resale sites = `secondhand`, ASOS etc. = `new`).
- Drop sold or expired items unless we asked for sold comps.
- Duplicates: same `source + source_id` is merged. Same image hash across sources is flagged (later).

### Step 3. Extract (`extract.py`, `fibers.py`)

Order: cheap first, LLM last.

1. **Structured fields first.** Use ThredUp `materials[]`, Depop `material`, eBay `item_specifics.Material`. Level = `stated`.
2. **Regex over title + description.**
   - Percentages: `100% cotton`, `80% wool 20% nylon`, `60/40 cotton poly`.
   - Fiber words: cotton, polyester, nylon, wool, merino, linen, hemp, silk, viscose, modal, lyocell, acrylic, elastane, cashmere, alpaca, leather.
   - Certifications: OEKO-TEX, GOTS, bluesign, Fair Trade, RWS, RDS, OCS.
   - Flags: organic, recycled, deadstock, upcycled, vintage, vegan leather vs genuine leather.
3. **Fix names** to one list (in `fibers.py`): poly -> polyester, spandex/Lycra -> elastane, rayon -> viscose, TENCEL -> lyocell, "pima cotton" -> cotton.
4. **Check the numbers.** Percentages should add to about 100. If they do not, keep the parse but lower confidence and note it.
5. **LLM fallback** only for listings that mention fabric words but did not parse cleanly. Capped per run (set in `config.yaml`). Output must be strict JSON in our shape. Level stays `stated` (the text said it), and the LLM output is stored along with the quoted snippet so we can check it.
6. **Category/brand guess** (optional, `inferred`): if the brand + category is well known (for example fleece = polyester), add an `inferred` fabric. Small hand-made table, not an LLM guess.

The snippet (the exact words we matched) is saved in the evidence row.

### Step 4. Enrich (`sellers.py`, `brands.py`, `footprint.py`)

- **Seller size.** Thresholds in `config.yaml`. Examples: Depop/Mercari/Poshmark seller with few sales = `individual`; many listings = `small_shop` or `large_reseller`. Brand storefronts = `brand_store`.
- **Fast-fashion flag.** Brand name matches a maintained blocklist file (`config`/`data` list of brands).
- **Brand match.** Fuzzy-match `brand_raw` to `brands.name_norm`. Unmatched brands are still kept as text and added to `brands` with no scores.
- **Brand scores.** Attach Wikirate transparency and Fashion Checker scores, B Corp flag. Level = `brand_reported`.
- **Weight estimate.** Look up `garment_weights` by category.
- **Footprint range.**
  - If we have fibers: sum over fibers of (weight x fiber share x per-kg factor), once for the low number and once for the high number.
  - If fibers are unknown: use a category-average range, and mark the footprint as based on a category average.
  - Always a range, always "est."
- **Savings.** `co2_saved = co2_new x displacement_rate` (about 0.65), only for secondhand items. Same for water. `dollars_saved = retail - price` only when retail is a real number.
- **Unknown count.** Count of eco facts still unknown.

### Step 5. Reference data load (`reference.py`)

Run once, and again whenever the reference files change.
- `fibers`, `garment_weights`, `displacement_rates` come from small hand-edited CSV/YAML files in `pipeline/data/reference/`. Each row must have a `source_url`. A test fails if a number has no source.
- Wikirate scores: download CSV, map company names to `brands`.
- Open Supply Hub: for our top brands, search `/facilities` and store results in `facilities` (optional, later).
- B Corp list: hand-curated CSV.

### Step 6. Tag merge (`tags.py`)

`ml/` reads a tag photo and gives us raw text plus parsed fields. The pipeline stores and merges it.

1. **Receive.** A tag scan arrives as JSON (shape defined in `models.py` as `TagScan`). Save it to `tag_scans`.
2. **Clean up.**
   - Fix fiber names with `fibers.py`.
   - Parse "Shell: 100% cotton, Lining: 100% polyester" into parts.
   - Check percentages add to about 100.
   - Normalize country ("Made in Viet Nam" -> `VN`).
3. **Find the company.** If there is an RN number, look it up in `rn_cache`, then FTC if missing. Match to `brands`. Store the result.
4. **Attach it.**
   - If the scan names a known listing, set `listing_id`.
   - Otherwise try to match a `product` (same brand + model + category).
   - If nothing matches, it stays a standalone scan. The "your current garment" receipt in the UI uses the scan directly.
5. **Update the listing.** For the linked listing, write `materials`, `synthetic_share`, `country_of_origin` and recompute the footprint, with evidence level `tag_verified`.
6. **Spread to the same product.** Other listings of the same `product_id` get the fabric as `inferred` (not `tag_verified`), because we only verified one item.
7. **Conflicts.** If the tag disagrees with the seller's text, keep both evidence rows and mark `contradicted`.
8. **Feed back.** Country of origin and fiber facts flow into the footprint math.

### Step 7. Thumbnails (`thumbs.py`)

- Download the main photo, resize small (for slow venue wifi), save to Supabase Storage.
- Save the path in `thumb_path`. Keep the original `image_url` too.
- Cache by URL so re-runs do not download again. Skip broken links and log them.
- `ml/` will use these thumbnails (or the originals) for embeddings.

### Step 8. Load (`load.py`)

- Upsert in batches by `(source, source_id)`. Re-running is safe.
- Never overwrite a stronger evidence level with a weaker one.
- Never overwrite `embedding` (that column belongs to `ml/`).
- Write a short load report: rows added, updated, skipped, and why.

---

## 7. Config (`config.yaml`)

One file controls the run. Example sections:
- `budget`: max total USD, max per Actor.
- `sources`: for each source: Actor id, backup Actor id, input template, item limit, proxy setting.
- `queries`: category terms, material terms, demo props.
- `seller_thresholds`: counts that separate individual, small shop, large reseller.
- `llm`: model name, max calls per run.
- `fast_fashion_brands`: path to the blocklist file.

---

## 8. Testing plan (red/green TDD)

Write the failing test first, see it fail, then write the code. Only the computing code is tested. Network calls stay thin.

| Area | What the tests check |
|---|---|
| Fiber names | poly -> polyester, Lycra -> elastane, TENCEL -> lyocell, unknown word stays unknown |
| Percent parsing | "100% cotton", "80/20 cotton poly", "Shell: 90% wool 10% nylon", bad sums, empty text |
| Certifications | finds GOTS, OEKO-TEX, ignores look-alike words |
| Source adapters | each adapter turns a real sample item (from `tests/fixtures`) into the right `Listing` |
| Price | "$20.19" -> 2019 cents, missing retail stays null |
| Size and condition | many raw labels map to the same normalized value |
| Seller type | thresholds give the right type |
| Evidence merge | stronger always wins, weaker never overwrites, disagreement gives `contradicted` |
| Footprint | known fibers give a range; unknown gives category-average range; savings = new x displacement; secondhand only |
| Dollars saved | only when retail is real |
| Tag merge | clean-up, attach to listing, spread to product as `inferred` |
| Reference data | every number row has a `source_url` |
| Load | upsert twice gives same rows; `embedding` is never touched |

Tools: `pytest`, run with `uv run pytest pipeline/tests`.

---

## 9. Build order (one branch and one PR each)

Never push to main.

1. `pipeline-sample-actors`
   - Project setup (`pyproject.toml`, `.env.example`, `config.yaml`).
   - Sample-run script. Save fixtures. Write a short "what each Actor returns" note.
   - Ask the user to approve costs first.
2. `pipeline-schema`
   - Supabase project and migrations for all tables in Section 5.
   - `models.py` (Pydantic).
3. `pipeline-normalize`
   - Tests first. Then one adapter per chosen source.
4. `pipeline-extract`
   - Tests first. Fiber names, regex, certifications, evidence.
5. `pipeline-reference`
   - Fiber, weight, displacement files with sources.
   - Wikirate import, B Corp list.
6. `pipeline-enrich`
   - Seller type, brand match, footprint and savings.
7. `pipeline-tags`
   - Tag clean-up, RN lookup with cache, merge rules.
8. `pipeline-load`
   - Thumbnails, upsert, load report.
   - Small run (100 listings), check quality, then the full capped run.
9. Later: `pipeline-products` (group same garments), `pipeline-facilities` (Open Supply Hub), sold comps, new-clothing sources.

---

## 10. Checks before we call it done

- `uv run pytest pipeline/tests` passes.
- A 100-listing run goes end to end into Supabase.
- Report shows, per source: row count, % with price, % with retail price, % with image, % with a parsed fabric, and the count of each evidence level.
- Hand-check 20 random rows against the original listing links.
- Total Apify spend is under the budget.
- No seller names or handles anywhere in the database (search for them).
- Every eco number in `fibers`, `garment_weights`, `displacement_rates` has a source.
- Re-running the load does not create duplicates.

---

## 11. Risks and what we do about them

| Risk | What we do |
|---|---|
| An Actor breaks or gets blocked (Depop, Mercari, ThredUp) | Backup Actor per site; residential US proxy; sample-run first; saved raw data means no re-pay |
| Actor changes its field names | Adapters are tested against saved fixtures; a failing test shows the change quickly |
| Most listings have no fabric info | Expected. Store `unknown`. Bias queries toward fabric words. Use brand priors as `inferred`. Use tag scans for the demo items. |
| Footprint numbers disagree across studies | Always show a range and "est."; always cite the source |
| Scraping terms of service | Public data only, no seller info, link out; mention it in the Devpost Trust section |
| Cost grows | Cap on each Actor call and a total budget file |
| Care labels are sometimes wrong | Keep the raw tag text and confidence; allow `contradicted` |
| Embedding size not decided yet | `embedding` column is added in a small separate migration once Anthony picks the model |

---

## 12. Questions still open

1. Is new clothing shown as search results, or only used for price and fabric reference? (Design supports both; default: reference only until decided.)
2. Do we confirm skipping licensed sources (Higg MSI, ecoinvent)? (Default: yes, skip.)
3. Embedding model and size (Anthony) so we can set `vector(N)`.
4. Final category list and demo props (Haram).
5. Exact budget for the full run (event credits amount).
