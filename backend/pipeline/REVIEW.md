# Pipeline review

Two reviews of `backend/pipeline/`, the code that scrapes secondhand listings and turns them into the catalog
(`data/listings.jsonl`). The newest is first.

## Second review (2026-10-24, branch `pipeline-review-2`, macOS)

**Result:** the pipeline is sound. I found 6 problems: 1 that could silently cut a marketplace out of an overnight run,
3 that filed or described listings wrongly, and 2 small ones. All 6 are fixed, each with a test that failed first. The
673 pipeline tests pass, plus the 58 ranker and API tests that run without the ML runtime. **No live scrape was
possible:** this computer has no Apify token (the docs pointed to a path that does not exist, now fixed), so the $20 test
budget is unspent. See "Live check" below.

### What I did

1. Read `DESCRIPTION.md`, the API contract, and every file in `backend/pipeline` (code, docs, tests, fixtures, logs).
2. Checked all five actors against Apify's public API: price per row and per run, memory (the start fee is per GB),
   timeouts, the input fields we send, and the latest build. All match `scrape.py`, and every build predates our test
   runs, so the fixtures show what the actors return today.
3. Opened the fixtures' real listings on Mercari, Grailed, eBay and Poshmark and compared each field (price,
   shipping, condition, size, original price, material).
4. Probed every rule (condition, category, brand, country, retail price, Depop title) with real marketplace labels,
   and checked the labels I doubted on the marketplaces' own sites.
5. Pushed the fixtures through steps 02–03 and the ranker: all 20 rows become valid API results.

### Fixed

| Problem | Effect | Fix |
| --- | --- | --- |
| Crawlee (the crawler inside the eBay, Poshmark and Depop actors) logs `Request failed and reached maximum retries` for **each** page that fails for good, and `health.py` read that as "the actor gave up" | One dead detail page in a healthy 150-row run made the run **blocked**: its rows were quarantined and the marketplace was stopped for the rest of the command, overnight too | That line is now a note. The request statistics ("most requests failed") still catch real blocks |
| The North Face sells **Nuptse Traction Booties** (checked on thenorthface.com) | A sneaker titled "Nuptse" got the jacket's "nylon shell, down fill" and a "known durable line" (+2 quality points in the ranker) | Each product line names its categories |
| Depop is British: its tops group files tank tops as **`vests-tanks-camis`** (checked on depop.com) | Depop tank tops became **jackets** | A Depop vest under tops is a tank top, and is dropped like other tank tops |
| Poshmark files rompers under **`Women > Pants & Jumpsuits > Jumpsuits & Rompers`** (checked on poshmark.com) | Rompers became **pants** | A label part that names a garment outside the 8 (romper, tank top, cami, crop top) ends the search. Tank tops under Mercari's `Tops & blouses` and Poshmark's `Shirts` are now dropped too, like eBay's already were |
| The docs and `01_scrape.py` said the token goes in `/workspace/.env` | That path is from another computer; the code reads `.env` at the repo root | Docs fixed; the error message prints the real path |
| A Depop description that starts with a line of emoji (`✨✨✨`) | That line became the title | Lines without a letter or digit are skipped |

### Found, not changed (decisions for the team)

| Finding | Why it matters | Suggestion |
| --- | --- | --- |
| **Poshmark shows condition and shipping on every listing page** (e.g. "Condition: Good", "Shipping $6.49"); our actor returns neither | Every Poshmark row has an unknown condition (the ranker assumes 85% of life left) and no shipping | Probe `xtracto/poshmark-detail-scraper` (has condition) in the live check |
| **Listings sell fast.** 1 of 3 Mercari fixtures was gone (HTTP 410) within a day of the scrape | A link-out to a sold item in the demo looks broken | Re-scrape or re-check the demo props' results the night before the demo |
| The same item is often cross-listed on several marketplaces | A search can show one jacket three times | Image-based dedupe across marketplaces (beyond Grailed's cross-listing, already noted) |
| eBay's shipping is calculated for the buyer's location (the record said $6.66; from this browser $10.15) | `shipping_cents` on eBay is an estimate for the actor's US proxy location | Fine as is; worth knowing |
| eBay auctions are paid for, then dropped (3.5% of eBay rows) | About $1.40 of the plan | The actor accepts `listingType: "bin"`; try it in the live check before switching |
| Mercari's and Poshmark's actors each had 1 user in the last 30 days (probably us); Mercari's changed its pricing text on Oct 19 | If either breaks, nobody else will notice first | The fallbacks are listed in `BLOCKING.md` |
| Brand prefix rule: "Jordan Craig" becomes Jordan, "Columbia University" becomes Columbia | Wrong brand facts once `ml/evidence/brands.yaml` has rows (it is empty today) | Add exceptions when the brand table is filled |
| Sizes are raw strings (`M`, `M (38-40)`, `US L / EU 52-54`) | The API's size filter is an exact match (`API.md`), so it misses Mercari's `M (38-40)` | A decision for the API owners |
| Every fixture description of 400+ characters is cut at exactly 400 (four different actors), so the fixtures were trimmed when saved | Tests never see composition text that sits late in a long description | Keep one untrimmed record per marketplace in the fixtures |

Checked and fine: prices, start fees and memory of all five actors; the input fields we send; the Apify client
signatures (v3.3.0); Mercari's shipping payer and free shipping; Grailed's price drops and US shipping; eBay's material
specifics; that US sellers write `100% cotton` rather than `Cotton 100%` (19 to 0 in 260 eBay titles, so no new rule);
the money, quota and resume logic; the ledger and snapshot code; privacy scrubbing.

### Live check (when a token is in `.env` at the repo root)

About $6 of the $20. From `backend/`:

```bash
uv run python pipeline/01_scrape.py --test                       # ~$0.55: every actor answers, 20 rows each, in data/test/
uv run python pipeline/02_normalize.py --test
uv run python pipeline/03_extract.py --test
uv run python pipeline/04_report.py --test --min-rows 80
uv run python pipeline/run/cli.py batch --rows 1000 --max-spend 8  # the real plan's first checked batch, ~$5
```

The batch is real work, not a throwaway: its runs count toward the quotas and are shared through the team ledger.
Read `data/batches/<id>/CHECKS.md`, look for `ALERT` lines and `request(s) failed after every retry` notes, and check
that no Depop tank top or Poshmark romper is in `data/listings.jsonl`.

## First review (2026-10-24, branch `pipeline-review`)

**Result:** the pipeline works, and its data is now correct enough to build the ranker on. The review found 13 problems:
10 in the data it produced and 3 in how it runs. All are fixed, each with a test that failed first. 597 tests pass on
Windows and Linux.

### Does it run on Windows, macOS and Linux?

| OS | Checked how | Result |
| --- | --- | --- |
| Windows 11 | Tests, a real `01_scrape.py --test` run with output sent to a log file, steps 02–04 on the review data | Works (it did not before this review: see "Windows" below) |
| Linux (Ubuntu 24.04, in WSL) | A clean copy of the branch with Linux line endings: tests, `01_scrape.py --dry-run`, steps 02–04 on the review data | Works. `normalized.jsonl` and `listings.jsonl` are byte-identical to the Windows output |
| macOS | Not run (no Mac here) | Expected to work like Linux: the code uses only `pathlib`, UTF-8 files and plain `\n` newlines, nothing OS-specific |

### What I did

1. Read `DESCRIPTION.md`, the API contract (`schema/`), and every file in `backend/pipeline` (code, docs, tests).
2. Finished the tasks the earlier review left open: the 4 failing tests, the eBay "Tops" problem, and Depop kids items.
3. Scraped fresh test data, for **$5.41** of the $10 budget. The plan was the first query of each of the 8 categories on all 5
   marketplaces at 20 items, plus full-size runs (Depop 200, Poshmark 200, eBay 150). All 44 runs were healthy.
4. Ran steps 02–04 on that data and checked each field against real listings, two of them on the marketplace's own
   site: categories, brands, materials, flags, country, retail price, condition, price, photos, sizes, seller data and
   privacy.
5. Fixed each problem test-first, and reran the steps to see the effect.

### Findings and fixes

#### Wrong data (found in the live scrape)

| Problem | Effect | Fix |
| --- | --- | --- |
| Grailed's `short_sleeve_shirts` / `long_sleeve_shirts` are its **T-shirt** categories (checked on grailed.com) | Every Grailed tee was filed as a button-up shirt: 0 Grailed rows in `tshirts` | They map to `tshirts` (now 27 rows) |
| eBay files women's tees under a generic `Women's Clothing > Tops` | A whole tee query was dropped, and eBay was stopped as "degraded" | eBay's `Type` field (T-Shirt, Blouse…) decides the category (your choice). The query now gives 20/20 good rows |
| The category rule for boots matched `Jeans > Boot cut` (Mercari, Poshmark) | Boot-cut jeans became sneakers | Fixed. `Hooded jacket` was also a hoodie and is now a jacket |
| Depop's kids items only have the broad categories `Clothing` / `Shoes` (checked on Depop: "Kids" vs "Men › Footwear › Sneakers") | Kids items got through when the size said "Other" or "One size" | Both categories are dropped as kids (12 of 12 such rows were kids items) |
| An eBay auction's price is only the current bid | A $16 bid on a fleece would rank near the top on cost per wear | Auctions are dropped (3.5% of eBay rows) |
| eBay shoes keep their size in `US Shoe Size` | 0 of 146 eBay sneakers had a size | Read it (146 of 146) |
| Poshmark sellers type the model into the brand field (`Nike Dunk Low`, `Levi's 501`) | Brand is the key that joins brand facts, so these would get none | A known brand followed by more words is that brand |
| Grailed lists style tags as designers (`Flannel`, `Designer`, `Band Tees`) | Brands like "Carhartt × Flannel" | The tags are not brands |
| eBay sneakers' `Upper Material` was not read | Sneakers had a material on 2 of 217 rows (the Nike Dunk Low demo prop is a sneaker) | Read it, with suede counting as leather: 70 of 217 |
| A bare eBay `Material: Wool` beat a description saying `100% merino wool` | The percentage was lost (8.5% of eBay rows) | The text wins when it names the same fibers with percentages. eBay rows with a stated material went from 46% to 70% |

#### Robustness

| Problem | Fix |
| --- | --- |
| **Windows:** files used the platform encoding (cp1252). Product-line notes came out as garbled text, the run report crashed at the end of a scrape, and 45 tests failed | Every file is read and written as UTF-8, and the command-line scripts print UTF-8 |
| **Windows:** text files were written with `\r\n` line endings, so the same data gave different files on different machines | Every file is written with plain `\n` |
| **Privacy:** the seller-data allowlist only applied one level deep | It applies at every depth |
| Steps 02–04 could only read `data/` or `data/test/` | They take `--data-dir`, like step 01 |

#### Decided with you

- The Depop title is the first line of the description, without hashtags and at most 120 characters. Depop's own title is
  five words cut mid-phrase.
- Poshmark's "Original Price" is the retail price (`retail_price_cents`), not a markdown.
- eBay's `Type` field decides the category under a generic "Tops".

#### Earlier in the review (first session)

Country names ("Made in Hong Kong" gave "Hong"), compositions like `100% pure new wool`, "Vtg" as vintage, shorts filed
as jeans, Depop kids sizes, eBay's 0% feedback read as a 0.0 rating, Grailed's "Vintage" designer, two Depop seller
fields in the raw files, and failed runs booked at too low a cost.

### The test data in numbers

1,257 listings after cleaning, from 1,350 raw rows. The other 93 were duplicates (35) or left out on purpose (58: kids
items, shorts, auctions, crop tops).

| | Depop | Poshmark | Grailed | Mercari | eBay | All |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Listings | 348 | 334 | 160 | 133 | 282 | 1,257 |
| Real description (> 40 chars) | 97% | 94% | 98% | 92% | 95% | 95% |
| Stated material | 21% | 42% | 68% | 47% | 70% | 46% |
| Material with percentages | 16% | 32% | 42% | 37% | 23% | 27% |
| Median price | $85 | $33 | $54 | $30 | $46 | |

All acceptance checks pass at this scale except one demo prop. The Patagonia Better Sweater was not among the queries
sampled; the real plan does search for it. The data is in `pipeline/data/review/all/`, which git ignores, so it is on
this computer only.

### Next steps

**Before the real 20k run**
1. Merge PR #6 (`pipeline-review` → `main`). It holds the whole pipeline: `pipeline-scraping` plus this review.
   Its only change outside the pipeline is one line in `CLAUDE.md`. Once it merges, GitHub marks PR #3
   (`pipeline-scraping` → `main`) as merged too. Keep the `pipeline-scraping` branch, because PR #4 targets it.
2. Run the real scrape (about $94, at most $118):
   `uv run python pipeline/01_scrape.py --max-spend 120 > scrape.log 2>&1 &`. Watch for `ALERT` lines. Then run steps
   02–04 and check `REPORT.md`.

**For the ranker and the evidence tables (Anthony)**
3. **Shipping is unknown on Depop and Poshmark**, so their `total_cents` is the price alone, while eBay, Grailed and
   Mercari include shipping. Comparing totals across marketplaces makes Depop and Poshmark look cheaper. The ranker
   should handle unknown shipping explicitly, for example with a labeled typical-shipping assumption.
4. **Brands:** the cleaner only fixes the spelling of the 25 brands in `normalize/common.py` (`_BRANDS`). When the
   ~40-brand facts table exists, add its brands to that list, or join on `slug(brand)`, so every spelling matches.
5. **Demo prop:** Nike Dunk Low has no entry in `product_lines.yaml`. Add one if Nike's own page states the material.
6. Poshmark has no condition (null on 26% of rows), and only 7% of its titles say NWT/NWOT. The ranker should treat
   null condition as unknown.

**Later**
7. Grailed resellers list one item several times under different ids. This needs image-based dedupe.
8. Coats whose tag lists a shell and a lining add up past 100% and are marked `composition_suspect`. A parser for the
   "Shell:" / "Lining:" labels would recover most of them.
9. Small: tank tops under a `Shirts` parent are filed as shirts. The duplicate counts in `run_report.md` ignore earlier
   runs (step 02 still dedupes). Grailed logs a harmless "site layout may have changed" warning on every run.
