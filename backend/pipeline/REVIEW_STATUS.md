# Pipeline review: status

Review of `backend/pipeline/`, 2026-10-24. Work is on branch `pipeline-review` (made from `pipeline-scraping`).
Open the PR against `pipeline-scraping`. Delete this file before merging.

## Done (committed, tests first)

### First session

| Area | Problem | Fix |
| --- | --- | --- |
| Country of manufacture | Regex took one word: "Hong", "U", "Republic", even "A" | Known-country list with aliases; eBay `Unknown` ignored |
| Composition | "100% pure/virgin/Italian wool", lambswool lost the % | Allowed words between % and fiber; added acetate, ramie, polyurethane, modacrylic, camel hair |
| Composition | Same fiber listed twice (with and without %) | `add()` skips a no-% duplicate |
| Vintage flag | "Vtg" missed | `vtg` added |
| Category | "Shorts > Denim" became jeans_pants | Any label with "shorts" is unmapped |
| Depop | Kids sizes ("6 years") kept | Dropped as kids |
| eBay | 0% feedback gave rating 0.0 | Rating null |
| Grailed | Brand "The North Face × Vintage" | Brand from designer list; "Vintage" becomes a flag |
| Depop raw files | Two fields not allowed by SPEC §8 were kept | `Actor.drop` removes them |
| Budget | Failed runs booked at start fee only | Booked at their charge cap |

### Second session

| Area | Problem | Fix |
| --- | --- | --- |
| Windows | Files used the platform encoding (cp1252): product-line notes became mojibake, `run_report.md` crashed at the end of a run, 45 tests failed | Every read and write is UTF-8; the CLIs print UTF-8 |
| Depop title | The actor's title is five words of the description cut mid-phrase | First line of the description without hashtags, ≤ 120 chars (user decision) |
| Poshmark | `regular_price` was stored as a markdown | It is `retail_price_cents` (0 = none), with a `claimed`/`specifics` evidence record (user decision) |
| eBay category | `Women's Clothing > Tops` maps to nothing: a whole tee query was dropped and eBay stopped | The `Type` specific is the leaf of the path (user decision). The tee query now gives 20/20 good rows |
| Category | `Jeans > Boot cut` (Mercari, Poshmark) became sneakers; `Hooded jacket` became a hoodie | Fixed in the rules |
| Grailed category | `short_sleeve_shirts`/`long_sleeve_shirts` are Grailed's T-shirt categories (checked on grailed.com), so every Grailed tee was a "shirt" | They map to tshirts |
| Depop kids | Kids items with size "Other" or "One size" got through | Depop's kids department has only the broad categories `Clothing` and `Shoes` (checked on the listing pages); both are dropped |
| eBay auctions | An auction's price is the current bid (3.5% of eBay rows) | Dropped as `auction`, an expected filter |
| eBay size | Every eBay sneaker had no size (the key is `US Shoe Size`) | Read it |
| Brands | Poshmark sellers type `Nike Dunk Low`, `Levi's 501` as the brand; Grailed lists tags like `Flannel`, `Designer`, `Band Tees` as designers | A known brand followed by a model is that brand; the tags are not brands |
| Materials | eBay sneakers' `Upper Material` was ignored; a bare `Material: Wool` beat a text saying `100% merino wool` | Read `Upper Material` (suede = leather); take the text when it names the same fibers with percentages |
| Privacy | The seller-block allowlist only applied one level deep | Applies at every depth |
| CLI | Steps 02–04 had no `--data-dir` | Added |

## Live check (second session: $5.41 estimated, of a fresh $10)

The first session's data was on another machine, so the check was redone: the first query of each of the 8 categories on
all 5 marketplaces at 20 items, plus full-size runs (Depop 200, Poshmark 200, eBay 150) and one `01_scrape.py --test`.
Data: `pipeline/data/review/all/` (steps 02–04 run on it; `REPORT.md` there). All 44 runs were judged `ok`.

| | Depop | Poshmark | Grailed | Mercari | eBay | All |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Rows kept | 348 | 334 | 160 | 133 | 282 | 1257 |
| Stated material % | 21 | 42 | 68 | 47 | 70 | 46 |
| Percentages % | 16 | 32 | 42 | 37 | 23 | 27 |

Effect of the fixes on this data: Grailed tees 0 → 27 rows in tshirts; sneakers with a material 2 → 70 of 217; eBay
sneakers with a size 0 → 146 of 146; eBay stated material 46% → 70%.

## Still open (documented in README "Known limits")

1. Grailed resellers cross-list one item under several ids. Needs image-based dedupe later.
2. `run_report.md` duplicate counts ignore earlier invocations (step 02 still dedupes).
3. Every Grailed run logs "site layout may have changed (fell back to cached settings)". Healthy so far.
4. Poshmark has no condition (null on 26% of rows). Only 7% of its titles say NWT/NWOT, so it is not inferred.
5. Tank tops under a `Shirts` / `Tops & blouses` parent are filed as shirts (rare).
6. Poshmark and eBay repeat ~10% of rows inside one full-size run; the 30% over-scrape covers it.
7. No product line for the Nike Dunk Low demo prop (the evidence owner's call: the table needs the maker's own page).
