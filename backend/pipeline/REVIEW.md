# Pipeline review

Two reviews of `backend/pipeline/`, the code that scrapes secondhand listings and turns them into the catalog
(`data/listings.jsonl`). The newest is first.

## Second review (2026-10-24, branch `pipeline-review-2`, macOS)

**Result:** the pipeline is sound, and its live data is now correct enough to build on. I found 11 problems: 4 that
changed what listings say or which category they are in, 2 that cost money for rows we throw away, 3 in how it runs,
and 2 small ones. All 11 are fixed, each with a test that failed first. 698 pipeline tests pass (15 runs in a row),
plus the 69 ranker and API tests that run without the ML runtime.

**Live testing:** 59 actor runs (2,540 raw rows, 2,242 listings after cleaning) on all five marketplaces, for **$11.14**
of the $20 budget. Every actor works, Apify's bill matched our estimate to the cent on every checked batch, no seller
identity reached a file, and all acceptance checks pass on the sample (all three demo props are in it). The data is in
`pipeline/data/review2/` on this Mac (git ignores it).

### What I did

1. Read `DESCRIPTION.md`, the API contract and every file in `backend/pipeline`; merged the latest `main` (its own
   Ctrl-C fix for `run_lanes`, PR #19, replaced mine).
2. Checked the five actors on Apify's public API (prices, memory, timeouts, inputs, builds): all match `scrape.py`.
3. Live: the go/no-go run, a sweep of every category on every marketplace through the real lanes and batch checks
   (with Grailed at 200 rows for the first time), targeted probes, and a final run of the fixed code at full size.
4. Opened 13 scraped listings on their marketplaces and compared every field: all match, except the fees and
   shipping noted below.
5. Probed every rule with real labels, checked doubtful ones on the marketplaces' own sites, and diffed the extraction
   on all live rows before and after each change.

### Fixed

| Problem | Effect | Fix |
| --- | --- | --- |
| **eBay's actor sometimes browses as a buyer abroad** (1 of 9 live runs) | 16 of 18 results were foreign sellers, and even US items were quoted international shipping ($29.60, $34.80 instead of ~$8), so `total_cents` and cost per wear were wrong | The search is a URL shipped to a US buyer (`_fcid=1`, a US ZIP): 150 of 150 good, 148 US-located, shipping $0–18. No location filter, so decision 12 stands |
| **Grailed resellers paste eBay's item specifics into descriptions** ("Outer Shell Material: Cotton … Lining Material: Nylon … Insulation Material: Polyester") and hashtag every field | 14% of live Grailed rows, many of them the Carhartt Detroit demo prop, read as cotton + nylon/polyester: the lining shown as the material, and the ranker's durable-fiber point lost | Text labeled as lining or insulation is skipped, as eBay's own lining fields already were; hashtags are not material claims. Labeled shell + lining tags are no longer `composition_suspect`. 37 live rows corrected, none worse |
| The North Face sells **Nuptse booties** (checked on thenorthface.com) | A "Nuptse" boot got the jacket's "nylon shell, down fill" and a "known durable line" (+2 quality) | Each product line names its categories. Live: 11 Nuptse boots, none credited |
| Depop is British: its tops group files tank tops as **`vests-tanks-camis`** (checked on depop.com) | Depop tank tops became **jackets** | A Depop vest under tops is a tank top, dropped like every tank top |
| Poshmark files rompers under **`Pants & Jumpsuits > Jumpsuits & Rompers`** | Rompers became **pants** (live: 20 of 20 in a probe) | A label part naming a garment outside the 8 (romper, tank top, cami, crop top) ends the search; Mercari's and Poshmark's tank tops under a shirts parent are dropped too |
| **Mercari searches included kids' items** | 7 of 20 rows of a plain search were kids', paid for and dropped | The search is limited to Women and Men (`usCategoryIds`): 300 of 300 adult rows |
| **eBay auctions were paid for, then dropped** | 4.5% of live eBay rows | Buy It Now only (`LH_BIN=1`) |
| **Grailed's dress queries return dress shirts** | "100% cotton dress": 1 dress in 20 rows, at $0.012 a row | Grailed runs no dress queries; its quota goes to the 7 categories it has |
| Crawlee logs `Request failed and reached maximum retries` for each page that fails for good, and `health.py` read it as "the actor gave up" | One dead page would make a healthy run **blocked**: rows quarantined, marketplace stopped for the night. Not seen in the 59 live runs (eBay retries each page up to 20 times), but certain once a page fails for good | That line is a note; "most requests failed" still catches real blocks |
| apify-client streams every actor's log into ours by default | 1,480 of 1,517 lines of a live batch's output, five actors interleaved, `ALERT` lines buried | Not streamed (the runner still reads each log once): a 5-run test now prints 26 lines |
| Small: the docs put the token in `/workspace/.env` (it is the repo root); a Depop description starting with emoji became the title; "100% 2-Ply Cashmere" lost its percentage | | Fixed |

### Found, not changed (decisions for the team)

| Finding | Why it matters | Suggestion |
| --- | --- | --- |
| **Buyer fees are not in `cost`**: Depop now shows "$47.95 incl. marketplace fee" for a $45 listing, Mercari adds a buyer-protection fee (~3.5%) | The receipt's price is below what the user sees after clicking through | Decide whether `total_cents` should include them (a known rate per marketplace) |
| **Poshmark's actor returns no condition** (poshmark.com shows one on every listing); main's text rule now finds one on 37% of rows | 63% of Poshmark rows use the "condition not stated" assumption | Probe `xtracto/poshmark-detail-scraper` if this matters for the demo |
| **Listings sell fast**: 1 of 3 Mercari fixtures was gone within a day | A link-out to a sold item looks broken in the demo | Re-scrape or re-check the demo props' results the night before |
| 34% of live Grailed rows come from sellers abroad (Malaysia 11%), shipping $20+ from Asia | Decision 12 keeps them; their shipping is real | Fine; a US-only view is one filter on `seller.region` |
| Depop shows a structured material ("Wool") the actor does not return; a Depop brand of "Other" is null even when the title names the brand | Depop materials come from text only (68% stated, fine) | Leave |
| Mercari's and Poshmark's actors each had 1 user in 30 days (probably us) | If one breaks, nobody else will notice first | Fallbacks in `BLOCKING.md` |
| Brand prefix rule: "Jordan Craig" → Jordan, "Columbia University" → Columbia | Wrong brand facts once `ml/evidence/brands.yaml` has rows (empty today) | Add exceptions with the brand table |
| Sizes are raw strings (`M`, `M (38-40)`) | The API's size filter is exact (`API.md`), so it misses Mercari's | A decision for the API owners |
| The fixtures were trimmed at 400 characters when saved (live descriptions are complete) | Tests never see text late in a long description | Keep one untrimmed record per marketplace |
| Cross-listed duplicates across marketplaces | One jacket shown several times | Already handled at search time on `main` (PR #21) |

### Next

The plan is ready for the real batches (see `run/README.md`): with a token in `.env`, `sync` first if teammates have
already scraped with this account, then `uv run python pipeline/run/cli.py batch --rows 5000 --batches all`.

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
