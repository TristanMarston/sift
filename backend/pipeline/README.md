# Sift data pipeline

This pipeline builds the **catalog**: a big file of clean secondhand clothing listings, collected once from
Depop, Poshmark, Grailed, Mercari and eBay. For every listing it keeps the price, photos, description, condition, size and
brand, and it pulls out the facts the ranker needs later (materials, certifications, vintage/deadstock flags,
retail price, country of manufacture). Each fact records where it came from and how sure we are.

It runs once, during the build. **Nothing is scraped when a user searches.**

Any listing priced in **USD** counts, wherever it ships from. There is no location filter. The seller's country is
stored in `seller.region`, so a US-only view is a one-line filter later.

Longer background: [`SPEC.md`](SPEC.md) (decisions, costs, test-run results) and [`SCRAPING.md`](SCRAPING.md)
(the original field spec). If they disagree with this file about *how to run it*, this file is right.

## How it works

```
 queries.yaml ──▶ 01_scrape ──▶ data/raw/<marketplace>/<run_id>.jsonl      what the actors returned,
 (what to search)  Apify actors   data/runs.jsonl                           with seller identity removed
                       │
                       ▼
                  02_normalize ──▶ data/normalized.jsonl                    one common shape for all five
                  one mapper per    (drops junk, removes duplicates)        marketplaces
                  marketplace
                       │
                       ▼
                  03_extract ───▶ data/listings.jsonl                       THE OUTPUT: materials, flags,
                  regex + tables    + an evidence record per fact           evidence
                       │
                       ▼
                  04_report ────▶ REPORT.md                                 coverage per marketplace and
                                                                            the acceptance checklist
```

Each step reads the previous step's file, so you can rerun any step without repeating the earlier ones.
Steps 02–04 cost nothing and are quick. Only step 01 spends money.

## Quick start

Everything runs from the `backend/` folder with `uv` (Python 3.12).

```bash
cd backend
uv sync                                    # install dependencies
uv run pytest                              # ~380 tests, no network, no money

# put your Apify token in the repo root: /workspace/.env  ->  APIFY_TOKEN=...
uv run python pipeline/01_scrape.py --dry-run      # see the plan and what it would cost. Calls nothing.
uv run python pipeline/01_scrape.py --test         # go/no-go: 20 items per marketplace, about $0.50
uv run python pipeline/02_normalize.py --test
uv run python pipeline/03_extract.py --test
uv run python pipeline/04_report.py --test --min-rows 80

# the real run (spends money; start it in the background, it takes a while; progress goes to scrape.log)
uv run python pipeline/01_scrape.py --max-spend 120 > scrape.log 2>&1 &   # the plan costs ~$94, ~$118 at the caps
uv run python pipeline/02_normalize.py
uv run python pipeline/03_extract.py
uv run python pipeline/04_report.py                # writes pipeline/REPORT.md
```

`--test` makes every step work in `pipeline/data/test/` instead of `pipeline/data/`, so a test run never mixes
with real data.

## The four steps

### 01 · Scrape — `01_scrape.py` (logic in `scrape.py`)

Runs one Apify actor per search in `queries.yaml` and saves what comes back.

| Flag | What it does |
| --- | --- |
| `--dry-run` | Prints runs, rows, best-case cost and worst-case cost per marketplace. Calls nothing, needs no token. |
| `--test` | The go/no-go run: the first query of each marketplace, 20 items. |
| `--only depop,ebay` | Only these marketplaces. |
| `--max-spend 120` | Stop before the *estimated* spend (earlier runs included) would pass this many dollars. |
| `--stop-all-on-block` | A block or junk data halts every marketplace, not just the one affected. |
| `--data-dir PATH` | Write somewhere else than `pipeline/data` (or `data/test`). |

How it behaves:

- **Breadth first.** Query 1 of every category and marketplace, then query 2, and so on. Stopping early still leaves
  every category covered, so **put the best queries first** in each list.
- **Quotas.** A marketplace stops when its raw rows reach its quota in `queries.yaml`.
- **Resumable.** Rerun the same command after a crash or Ctrl-C. Queries that already succeeded are skipped, and
  quotas count the rows already saved. Bad runs (blocked, empty, junk, failed) are retried; a query that comes back
  empty twice is treated as really empty.
- **Safe on money.** Every actor call carries a hard charge cap (expected cost + 25%, at least $0.05) and a
  30-minute timeout. Progress lines show the estimated spend.
- **Notices blocks at once.** Each run is judged when it finishes. A bad one prints an `ALERT` line and is appended to
  `alerts.jsonl`; a block or junk data stops that marketplace immediately, and a second empty or failed run in a row
  stops it too. The other marketplaces carry on. Create `data/STOP` to halt before the next run. See [`BLOCKING.md`](BLOCKING.md).
- **Ends with a report** (printed, and saved as `run_report.md` and `.json`): per marketplace the queries that were ok,
  short or bad, and the rows that were good, duplicate, filtered, unusable or quarantined, plus estimated and wasted spend.
  The exit code tells a script what happened: 0 finished, 2 a marketplace was stopped, 3 `--max-spend`, 4 `STOP` file, 130 Ctrl-C.
- **Atomic files.** A raw file appears only when the whole dataset was downloaded.

### 02 · Normalize — `02_normalize.py` (logic in `normalize/`)

Turns each marketplace's own record format into one shape (`Normalized`: a listing plus a `specifics` dictionary
with the marketplace's structured fields, such as eBay's item specifics). There is one small mapper per
marketplace: `normalize/depop.py`, `poshmark.py`, `grailed.py`, `mercari.py`, `ebay.py`. A mapper either returns a row or
raises `Drop("reason")`. The step prints how many rows were kept and why the others were dropped:

| Drop reason | Meaning |
| --- | --- |
| `no_price`, `no_url`, `no_title`, `no_id`, `no_image` | A required field is missing |
| `non_usd` | The price is not in dollars. There is no currency conversion. |
| `not_listing` | A free summary row from an actor (Mercari's dataset has some), not a listing |
| `kids` | The category is children's clothing (it would skew wear estimates) |
| `unmapped_category` | The marketplace says what it is (hat, bag, shorts) and it is not one of our 8 categories |
| `invalid`, `error:<Type>` | The row failed validation, or the mapper crashed on an odd record |

Duplicates (same marketplace and item id) are collapsed, keeping the newest copy.

Shared rules (`normalize/common.py`): prices become integer cents; brands get one canonical spelling
(`Levis`, `LEVI'S` → `Levi's`; junk like `unbranded` → null); condition text maps to `new_with_tags`, `like_new`,
`good`, `fair` (or null); the marketplace's category label maps to one of the 8 categories (all footwear counts as
`sneakers`; the leaf of a path like `Men > Sweats & hoodies > Track jacket` wins; blazers and suits count as jackets);
a missing label falls back to the query's category. Titles and descriptions lose invisible characters (zero-width
spaces, soft hyphens) and non-breaking spaces, because a zero-width space inside `100%cotton` defeats the composition
regex.

### 03 · Extract — `03_extract.py` (logic in `extract.py`)

Adds the evidence. It never invents: if the listing does not say, the field is empty and an `unknown` record says so.

| Fact | Where it looks | Status |
| --- | --- | --- |
| Materials | 1. structured fields (eBay `Material`, `Outer Shell Material`, `Fabric Type`, …) 2. title + description 3. `product_lines.yaml` | `claimed` (1, 2) or `inferred` (3) |
| Composition | `60% cotton / 40% polyester`, `100% organic cotton`; bare words (`cotton tee`) give a fiber with no percentage | `claimed` |
| Certifications | GOTS, OEKO-TEX, bluesign, Fair Trade, RWS, RDS, B Corp | `claimed` |
| Vintage / deadstock / upcycled | **title** and structured style fields only (descriptions carry shop boilerplate) | `claimed` |
| Retail price | `retails for $120`, `MSRP $75` in the title or description | `claimed` |
| Country of manufacture | the structured country field, else `made in X` | `claimed` |

Composition details: synonyms are unified (`poly` → `polyester`, `spandex` → `elastane`, `merino` → `wool`);
percentages that add up to 90–110 are scaled to 100; any other sum is kept but marked `composition_suspect`
(multi-part tags like shell + lining land here). `synthetic_share` is the share of polyester, nylon, acrylic and
elastane, and is only computed when every fiber has a percentage and the sum is sound. Fabrics that are not fibers
(fleece, ripstop, Gore-Tex) are not reported as materials.

### 04 · Report — `04_report.py` (logic in `report.py`)

Writes `pipeline/REPORT.md` (or `data/test/REPORT.md` with `--test`): per marketplace the rows, share, % with a
real description, % with a stated material, % with percentages, % with a certification, % with a region and the
median price, plus the acceptance checklist (≥ 20,000 active rows, ≥ 4 marketplaces, none above 50%, ≥ 25% stated
material, ≥ 10% percentages, the three demo props present, a region on every row). `--min-rows` changes the
row target for small test runs.

## Inputs

| Input | What it is |
| --- | --- |
| `/workspace/.env` | `APIFY_TOKEN=...`. Needed for step 01 only (not for `--dry-run`). Never committed. |
| `queries.yaml` | What to search, and how much. See below. |
| `product_lines.yaml` | Known product lines → material (`Carhartt Detroit → cotton duck`). Used only when a listing states no material. |
| `scrape.py` → `ACTORS` | Which Apify actor serves each marketplace, its input format, its price per row (for caps and estimates), and for eBay the list of fields kept. |

**`queries.yaml`:**

```yaml
quotas:            # raw rows to collect per marketplace (20k target + ~30% over-scrape)
  depop: 10400
max_items:         # default cap per query
  depop: 200
queries:
  jackets_outerwear:          # exactly the 8 API categories
    depop:                    # one list per marketplace (YAML anchors share a list)
      - the north face jacket                        # a plain string uses the default cap
      - {query: carhartt detroit jacket, max_items: 400}   # or set a cap (keep it ≤ 500)
```

**`product_lines.yaml`:** each entry has a `brand`, the words that must all appear in the title (`title_has`), a
`note` shown as the evidence snippet, and the `fibers`. The title is also matched together with eBay's `Product Line` and `Model`.
Add a line only when the maker's own page states the material.

## Outputs

Everything lands in `pipeline/data/` (ignored by git), except `REPORT.md`.

```
data/
  runs.jsonl                     one line per actor run (the log; also how reruns know what is done)
  alerts.jsonl                   one line per bad run: marketplace, query, verdict, reasons, run id, what we did
  run_report.md / .json          the report of the last step-01 invocation
  raw/<marketplace>/<run_id>.jsonl   the actors' records, seller identity removed
  normalized.jsonl               step 02: one row per listing
  listings.jsonl                 step 03: the final catalog
  test/                          the same layout for --test runs
REPORT.md                        step 04 (committed with the PR)
```

Every file is JSON Lines: one record per line, written ASCII-escaped and read on newline only (`jsonl.py`), because real
listings contain characters like U+2028 that `str.splitlines()` treats as a line break and would cut a record in half. If you
read these files from your own code, split on `\n` (or iterate the open file), not `splitlines()`.

**`runs.jsonl`** line: `{"marketplace", "category", "query", "max_items", "run_id", "status", "status_message",
"items", "est_charge_usd", "at", "verdict", "reasons", "notes", "rows_good", "rows_duplicate", "rows_filtered", "rows_bad"}`.
`verdict` is `ok`, `short`, `empty`, `failed`, `blocked` or `degraded`; step 02 skips the rows of `empty`, `failed`, `blocked` and `degraded` runs. `est_charge_usd` is our own estimate (items × price + start fee), checked against
the real Apify bills in the test run.

**`listings.jsonl`**: one JSON object per line, validated by `listing.py`. It mirrors the static part of
`schema/api.schema.json#Result`, so the ranker can copy fields across without renaming. Fields the ranker computes
later (`match`, `quality`, `eco`, `wear`, `confidence`, `thumb_url`) are not here.

| Field | Notes |
| --- | --- |
| `id`, `marketplace`, `external_id`, `url` | `id` is `<marketplace>:<external_id>`; `url` is the link-out |
| `title`, `description` | full text |
| `status` | `active` or `sold` |
| `scraped_at` | when the run happened |
| `brand`, `category`, `subcategory`, `size`, `color` | `category` is one of the 8 API values; the rest may be null |
| `condition`, `condition_raw` | mapped value and the marketplace's own words |
| `image_urls` | all photos (at least one); later photos may show care tags |
| `flags` | `is_vintage`, `is_deadstock`, `is_upcycled` |
| `cost` | `price_cents`, `currency` (always `USD`), `shipping_cents`, `free_shipping`, `total_cents` (= price + shipping when known), `original_price_cents` (the seller's markdown), `retail_price_cents` |
| `materials` | `fibers` (`fiber`, `pct`, `organic`, `recycled`), `synthetic_share`, `certifications`, `composition_suspect` |
| `country_of_manufacture` | null when unknown |
| `seller` | `type` (`individual`/`small_shop`/`large_reseller`), `rating` (0–5), `region` (country), `listing_count` |
| `evidence` | one record per fact: `{field, status, source, snippet, as_of}` |

**Null means unknown**, never zero or a guess. `evidence.status` is `claimed` (the listing says so), `inferred`
(from a product line) or `unknown`. `evidence.source` is `specifics`, `listing_text` or `product_line`.
`evidence.field` is one of `materials.fibers`, `materials.certifications`, `flags.is_vintage`, `flags.is_deadstock`,
`flags.is_upcycled`, `cost.retail_price_cents`, `country_of_manufacture`.

A real row (description and photo list shortened):

```json
{
  "id": "ebay:860021552093", "marketplace": "ebay", "external_id": "860021552093",
  "url": "https://www.ebay.com/itm/860021552093",
  "title": "Mens North Face 1996 Retro Nuptse 700 Puffer Jacket - Black - Size Large",
  "description": "New Condition with Tags. Has no wear/defects. All zippers work.\nShips same day or next…",
  "status": "active", "scraped_at": "2026-10-24T02:17:00Z",
  "brand": "The North Face", "category": "jackets_outerwear", "subcategory": "Jacket",
  "size": "L", "color": "TNF Black / TNF White Logo",
  "condition": "like_new", "condition_raw": "Pre-owned - Excellent",
  "image_urls": ["https://i.ebayimg.com/images/g/…/s-l400.jpg", "…"],
  "flags": {"is_vintage": false, "is_deadstock": false, "is_upcycled": false},
  "cost": {"price_cents": 15500, "currency": "USD", "shipping_cents": 0, "free_shipping": true,
           "total_cents": 15500, "original_price_cents": null, "retail_price_cents": null},
  "materials": {"fibers": [{"fiber": "nylon", "pct": null, "organic": null, "recycled": null}],
                "synthetic_share": null, "certifications": [], "composition_suspect": false},
  "country_of_manufacture": "Bangladesh",
  "seller": {"type": "individual", "rating": 4.92, "region": "US", "listing_count": null},
  "evidence": [
    {"field": "materials.fibers", "status": "claimed", "source": "specifics", "snippet": "Nylon", "as_of": "2026-10-24"},
    {"field": "country_of_manufacture", "status": "claimed", "source": "specifics", "snippet": "Bangladesh", "as_of": "2026-10-24"}
  ]
}
```

## What each marketplace gives us

Measured in the test runs. This decides which facts are empty for which marketplace.

| | Depop | Poshmark | Grailed | Mercari | eBay |
| --- | --- | --- | --- | --- | --- |
| Actor | `jongoose/depop-scraper` | `123webdata/poshmark-scraper` | `piotrv1001/grailed-listings-scraper` | `automation_craft/mercari-us-scraper` | `memo23/ebay-search-scraper-ppe` |
| Cost per row | $0.001 | $0.002 (+$0.02 per run) | $0.012 | $0.00273 (+$0.006 per run) | $0.005 (+$0.02 per run) |
| Description | yes | yes (some very short) | yes | yes (94% over 40 characters) | yes |
| Photos (average) | 4 | 7 | 8 | 8 | 7 |
| Condition | yes | **no** | yes | yes | yes |
| Shipping | no | no | seller's US rate | yes (free when the seller pays) | yes |
| Markdown (`original_price_cents`) | yes | yes | from earlier prices | yes | no |
| Seller type / rating | no | no | yes | yes | yes |
| Structured materials | no | no | no | no | yes (`Outer Shell Material`) |
| Color | yes | yes | yes | **never** | yes |

Mercari's first actor (`getascraper/mercari-us-scraper`) returned card data only (no description, one photo) and was
replaced; see `SPEC.md` §13a–b for what went wrong and how the new one was tested. Mercari's own total price also
includes a buyer-protection fee (about 3.5%) that `cost` does not model.

## Privacy

No seller usernames, profile links, avatars or account ids are stored.

- `scrape.py` removes them **before anything is written**. Flat keys such as `sellerUsername` are dropped at any depth.
  Inside any seller block (`seller`, `sellerProfile`, `user`) only a short allowlist survives (ratings, counts,
  location). eBay records keep only the top-level fields the mapper reads, because its raw page data contains the
  seller's handle and buyers' feedback.
- `tests/test_privacy.py` scans the fixtures, the mapper output and any real files in `data/` for identity keys.
- Two things are deliberately kept: the listing `url` (the link-out; **Depop URLs begin with the seller's handle**)
  and the description text (sellers sometimes write their store name in it).

## Tests

```bash
uv run pytest            # everything
uv run pytest pipeline/tests/test_extract.py -k vintage
```

The computational code was written test-first (the four `0N_*.py` files are thin command-line wrappers). The tests need no network and spend nothing: the Apify client is replaced by a fake.
`tests/fixtures/<marketplace>.json` are real records from the test run (seller handle removed) and are what the
mapper tests run on. `test_listing.py` checks the row format against `schema/api.schema.json`, so a schema change
that is not mirrored in `listing.py` fails a test.

## Changing things

- **Add or reorder queries:** edit `queries.yaml`, then `01_scrape.py --dry-run` to see the cost. Already-finished
  queries are not repeated.
- **Collect more rows (the 50k stage):** raise the `quotas`, add queries at the end of the lists, and rerun step 01.
- **Add a product line:** add an entry to `product_lines.yaml`.
- **Add a marketplace:** add an `Actor` to `scrape.py`, a `normalize/<name>.py` mapper (copy the closest one), a
  fixture from a 20-item test run, tests, queries and a quota. The name must already be in the API's marketplace enum.
- **Change a rule** (condition words, category words, composition regex): edit `normalize/common.py` or
  `extract.py`, add the failing test first, then rerun steps 02–03. No scraping needed.

## Known limits

- `seller.region` mixes formats: `US` for any US place, otherwise whatever the marketplace reports (a code like `CN`
  from Grailed, a name like `China` from eBay).
- Poshmark gives no condition, so it is null. Depop gives no shipping and no seller details. Mercari gives no color.
- Sellers sometimes put the wrong category on an item; a mislabeled item passes through.
- `seller.type` thresholds are guesses (Grailed: ≤ 20 / ≤ 200 listings; eBay: business accounts with ≥ 5,000
  feedback are large resellers).
- Material coverage depends on the queries. One generic jacket query gave 41% with a stated material and 6% with
  percentages; material-rich queries lifted Mercari to 70% and 50%. Check `REPORT.md` after the run.
- Tags with several parts (shell, lining) add up past 100%, so they are kept but marked `composition_suspect` and get no
  `synthetic_share`. This is 15% of the Mercari rows we tested, almost all coats, usually "shell composition, then a 100%
  polyester lining". Reading the "Shell:" and "Lining:" labels would recover most of them; taking the first group would
  be wrong whenever a seller lists the lining first, so we do not.
- The Mercari actor is new and was tested up to 150 items per run (two results pages); the plan asks for up to 300.
  `tortuga/mercari-scraper` is the fallback.
- Not built yet: thumbnails, image embeddings, the Supabase upload, care-tag OCR, the LLM fallback for odd material
  text, sold-price comps, and the hand-curated brand facts table.
- Scraping marketplaces may break their terms of service (Poshmark prohibits automated collection). We use public
  listing data only, store no seller identity and link out.
