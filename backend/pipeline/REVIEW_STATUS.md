# Pipeline review: status

Review of `backend/pipeline/`, started 2026-10-24. Work is on branch `pipeline-review` (made from `pipeline-scraping`).
Open the PR against `pipeline-scraping`. `gh` isn't installed, so open it in the GitHub web UI. Delete this file before merging.

## Done (committed, tests first)

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
| Cleanup | Duplicate bad-verdict set; unused `build_plan(only=)` | Removed |
| Docs | README/SPEC out of date | Updated |

Effect on the old test data: rows with % composition went from 41.8% to 50.4%; vintage flags from 90 to 104; about 20 countries corrected.

## User decisions

1. Depop title = first line of the description (hashtags removed, at most 120 chars, cut at a word). Fall back to the actor's title.
2. Poshmark `regular_price` goes to `cost.retail_price_cents` (not `original_price_cents`). A zero or missing value means null.

## In progress

There are 4 failing tests for the two decisions above (committed in the commit "bugs, changes to make", in `test_mappers.py` and `test_extract.py`). Still to do:
- `normalize/depop.py`: build the title from the description.
- `normalize/poshmark.py`: pass `retail=` to `make_cost`, not `original=`.
- `extract.py`: when the mapper already set the retail price, add the evidence record `("cost.retail_price_cents", "claimed",
  "specifics", "$X.XX")`.
- Then update the README (Poshmark markdown column, retail-price row, Depop title) and SPEC §9, run `uv run pytest`, and commit.

## Live check (about $5.07 of the $10 budget spent)

34 runs in `pipeline/data/review/` (report: `run_report.md`): one query per category per marketplace, plus Mercari at 300 items
and Grailed at 100. 33 runs were ok. Mercari's 3-page run and Grailed's 100-item run both worked.

## Open findings, not fixed yet

1. **Most urgent: eBay "Women's Clothing > Tops" is unmapped.** All 20 rows of `100% cotton tee` were filtered, the run was judged
   `degraded`, and eBay was stopped. In the real run eBay would most likely stop here too: this is its first t-shirt query,
   early in the order. Possible fixes: use the eBay specific `Type`/`Style` (e.g. "T-Shirt") when the leaf is generic, or treat
   a generic "Tops" as no label (fall back to the query's category). Ask the user. Also check whether Poshmark's 7 filtered
   rows are the same "Tops" issue.
2. Depop kids item with size "Other" got through. Both Depop kids items seen so far have `category: "Clothing"`, where adult
   items have "Outerwear". Check this across `data/review/raw/depop` before relying on it. Title words are risky
   ("Kids See Ghosts", "Beastie Boys").
3. Grailed resellers cross-list the same item under different listings (same title and price). This needs image-based
   dedupe later. Note it as a known limit.
4. Steps 02–04 have no `--data-dir` (step 01 does).
5. The seller-block allowlist in `scrub()` only filters one level deep. Low risk with the current actors.
6. Duplicate counts in the run report ignore rows from earlier invocations (report only; step 02 still dedupes).
7. Every Grailed run logs "site layout may have changed (fell back to cached settings)". Healthy so far, but watch it.

## Checked and fine

- `run.status` is a plain string.
- Depop descriptions are long enough for the health check (18–20 of 20 are over 40 characters).
- `--dry-run` matches SPEC §6 ($93.85 best case, $117.96 at the caps).
- Every estimated cost matched the plan.

## To finish the review

1. Make the 4 red tests pass and commit.
2. Fix the eBay "Tops" problem (finding 1) with a test, after asking the user which approach they want.
3. Decide on finding 2.
4. Rerun steps 02–03 on `data/review` and `data/test` (copy them first) and spot-check categories, materials and flags
   for the new categories.
5. Optionally re-run the eBay queries that never ran (budget left: about $4.90).
6. Push, open the PR, and give the user a short summary.
