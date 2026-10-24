# Pipeline review

A review of `backend/pipeline/`, the code that scrapes secondhand listings and turns them into the catalog
(`data/listings.jsonl`), done on 2026-10-24 on branch `pipeline-review`.

**Result:** the pipeline works, and its data is now correct enough to build the ranker on. The review found 13 problems:
10 in the data it produced and 3 in how it runs. All are fixed, each with a test that failed first. 597 tests pass on
Windows and Linux.

## Does it run on Windows, macOS and Linux?

| OS | Checked how | Result |
| --- | --- | --- |
| Windows 11 | Tests, a real `01_scrape.py --test` run with output sent to a log file, steps 02–04 on the review data | Works (it did not before this review: see "Windows" below) |
| Linux (Ubuntu 24.04, in WSL) | A clean copy of the branch with Linux line endings: tests, `01_scrape.py --dry-run`, steps 02–04 on the review data | Works. `normalized.jsonl` and `listings.jsonl` are byte-identical to the Windows output |
| macOS | Not run (no Mac here) | Expected to work like Linux: the code uses only `pathlib`, UTF-8 files and plain `\n` newlines, nothing OS-specific |

## What I did

1. Read `DESCRIPTION.md`, the API contract (`schema/`), and every file in `backend/pipeline` (code, docs, tests).
2. Finished the tasks the earlier review left open: the 4 failing tests, the eBay "Tops" problem, and Depop kids items.
3. Scraped fresh test data, for **$5.41** of the $10 budget. The plan was the first query of each of the 8 categories on all 5
   marketplaces at 20 items, plus full-size runs (Depop 200, Poshmark 200, eBay 150). All 44 runs were healthy.
4. Ran steps 02–04 on that data and checked each field against real listings, two of them on the marketplace's own
   site: categories, brands, materials, flags, country, retail price, condition, price, photos, sizes, seller data and
   privacy.
5. Fixed each problem test-first, and reran the steps to see the effect.

## Findings and fixes

### Wrong data (found in the live scrape)

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

### Robustness

| Problem | Fix |
| --- | --- |
| **Windows:** files used the platform encoding (cp1252). Product-line notes came out as garbled text, the run report crashed at the end of a scrape, and 45 tests failed | Every file is read and written as UTF-8, and the command-line scripts print UTF-8 |
| **Windows:** text files were written with `\r\n` line endings, so the same data gave different files on different machines | Every file is written with plain `\n` |
| **Privacy:** the seller-data allowlist only applied one level deep | It applies at every depth |
| Steps 02–04 could only read `data/` or `data/test/` | They take `--data-dir`, like step 01 |

### Decided with you

- The Depop title is the first line of the description, without hashtags and at most 120 characters. Depop's own title is
  five words cut mid-phrase.
- Poshmark's "Original Price" is the retail price (`retail_price_cents`), not a markdown.
- eBay's `Type` field decides the category under a generic "Tops".

### Earlier in the review (first session)

Country names ("Made in Hong Kong" gave "Hong"), compositions like `100% pure new wool`, "Vtg" as vintage, shorts filed
as jeans, Depop kids sizes, eBay's 0% feedback read as a 0.0 rating, Grailed's "Vintage" designer, two Depop seller
fields in the raw files, and failed runs booked at too low a cost.

## The test data in numbers

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

## Next steps

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
