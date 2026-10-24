# Notes for backend changes, from the web app

Written by Tristan (web) for Anthony and his coding agent, Oct 24 2026. Read it with `HANDOFF.md` and
`schema/api.schema.json`. It covers what the web app depends on, what live tests showed, and the changes that would
help most. Items marked **Decide** need a team call before anyone builds them.

## 1. How the web app calls the API

- **Address:** `NEXT_PUBLIC_API_URL`, set in Vercel and in `web/.env.local`. Next.js bakes it in at build time, so
  changing it means a redeploy. Current: `https://lu-anthony-73--sift-api.us-west.modal.run`. If the hostname
  changes again, tell Tristan: Vercel needs the new value and a redeploy.
- **Routes:** in production the app calls the API directly and falls back to `/api/sift/*` (a Next.js rewrite to the
  same address) when the direct call is blocked. In development it only uses the rewrite. Code: `web/lib/api.ts`,
  `web/lib/endpoints.ts`, `web/next.config.ts`.
- **CORS:** production is `https://sift-calhacks.vercel.app` (matches the current `sift-*.vercel.app` regex). Keep
  `http://localhost:3000`.
- **No address set:** the app silently uses the bundled samples in `web/public/samples/` (jackets, sweaters,
  sneakers) and shows a "Sample results" pill. That's what Vercel served on Oct 24, before the variable was set.

| Call | When | Web timeout | If it fails |
| --- | --- | --- | --- |
| `GET /health` | landing load (wakes the container), search counter | 15 s | count falls back to a saved number |
| `POST /detect` | right after the photo | 15 s | the whole photo is searched with no category |
| `POST /search` | once per garment crop, or per box the user draws | 20 s | "Try again" screen |
| `POST /jpeg` | a photo the browser can't decode (HEIC in Chrome) | 15 s | the photo can't be used |

`/search` params are `{"category": ...}` when `/detect` gave one, and `{}` for a drawn box or the whole photo.
Filters are not sent yet. (`HANDOFF.md` says the app gives up on `/detect` at 8 s; it's 15 s now.)

## 2. What the web app reads: don't break these

Make changes additive. Renaming, removing or changing the meaning of any field below breaks a screen.

- **`/detect`:** `garments[].id`, `label` (shown in sentence case), `category` (null allowed), `box` (`x, y, w, h` as
  fractions, top-left origin), `confidence` (used to order the garment tabs).
- **`/search` top level:**
  - `query.category`: the title ("Jackets") and the counter ("Searching jackets")
  - `typical.price_cents`, `typical.cpw_cents` (nullable)
  - `orders.cpw`, `orders.eco`: the two tabs
  - `slider`: exactly 11 lists, 0 = best value, 10 = closest match
  - `headline.cheapest_id` (the Cheapest tag), `headline.cheapest_rank_by_cpw` ("drops to #N" at 3 or more, "also
    the best value per wear" at 1, nothing at 2)
- **Each result:** `id` (stable: it keys the animations), `marketplace`, `url`, `title`, `size`, `condition`,
  `thumb_url`, `image_urls`, `match.similarity`, `match.band`, `cost.total_cents`, `price_cents`, `shipping_cents`,
  `free_shipping`, `fee_cents`, `original_price_cents`, `retail_price_cents`, `quality` and `eco` (level + facts),
  `wear.expected_wears`, `wear.basis`, `wear.cpw_cents.at_30/at_60/at_100/at_mid`, `wear.break_even_wears`,
  `wear.facts`, `confidence`.
- **Each fact:** `label`, `value`, `status`, `source`, `snippet`, `source_url`, `as_of` (YYYY-MM-DD).
- **Not read today** (safe to change, but say so in the PR): `materials`, `seller`, `flags`, `color`, `brand`,
  `subcategory`, `condition_raw`, `orders.price`, `orders.match`, and marker `score`.

Rules that keep the screens honest:

- **Null means unknown.** The UI prints "unknown" and never 0. Send null rather than a guess.
- **Errors** stay `{"error": {"code", "message"}}` with a non-2xx status.
- **Fact text is shown as written** in the Wear Receipt. Keep labels short enough for one line (under ~35
  characters). The web app capitalizes the first letter of values ("cotton" shows as "Cotton").
- **A new fact `source`** needs a display name in `SOURCE` in `web/components/results/evidence.tsx`. Without one, the
  raw key shows.
- **Copy rules apply to any text the server writes:** no em dashes, no exclamation marks, no "It's not X, it's Y",
  no virtue words ("sustainable", "eco-friendly", "green"). Eco claims only as sourced facts.

## 3. What live tests showed (Oct 24, afternoon)

Method: 4 photos of people wearing black hoodies (Wikimedia Commons, so not in the index), run the way the app runs
them: shrink to 1024 px, `/detect`, crop the top garment with 4% padding, `/search` with the detected category.

1. **Detection works.** 4 of 4 found the hoodie in 2.6 to 4.9 s (warm, us-east). One zip hoodie was labelled "black
   zip jacket", so it searched `jackets_outerwear`.
2. **The closest matches were right:** black hoodies in all hoodie searches.
3. **Worn photos never reach `exact` or `close`.** Similarity ran 0.59 to 0.74, so every result was `similar`. The
   bands were tuned on product shots (0.89 to 0.99). Within one top 50 the spread is only about 0.05.
4. **The colour re-rank doesn't look live.** `orders.match` followed raw similarity exactly (0 of 49 swaps, in 2
   searches), and a black jacket's top 8 included navy, blue, yellow and grey listings. Most likely
   `modal run modal_app.py::colors` wasn't run after the last `::embed`. Also, `color` mixes cases ("black",
   "Blue") and is often null.
5. **Cost per wear picks the cheapest from a loose set.** In 2 of 4 searches the cost-per-wear #1 was #41 to #43 of
   50 by look. Across 10 earlier searches the cheapest was #1 by cost per wear 8 times, so the headline nearly
   always reads "The cheapest match is also the best value per wear". The cause: expected wears only vary about
   2.4x (quality x condition) while prices among look-alikes vary 10x or more.
6. **The Eco tab clusters by marketplace.** Ties are broken by `id` (`ranker.py`, `_order`), and ties are common
   (one search: 15 high, 21 medium, 13 unknown, 1 low). The top 10 came out as grailed, grailed, grailed, ...
   depop, depop, depop. Vintage plus cotton alone already scores High.
7. **`/health` can't answer "what's live?"** There's no index date, no colour flag and no per-category counts.
8. **Cold start** is still about 10 to 14 s on `/detect`.

## 4. Requested changes

### Before the demo

- [ ] **Run the colour step on the live index and redeploy.** Check: `orders.match` should sometimes differ from
      pure similarity order, and a black garment's top results should be black.
- [ ] **Break Eco ties by cost per wear:** sort by `(score desc, cpw asc, id)` in `ranker.py`. Red/green TDD.
- [ ] **Add metadata to `/health`** (additive): `built_at`, `colors` (bool), `by_category` and `by_marketplace`
      counts. The web app will use `by_category` for "Searching 6,200 hoodies".
- [ ] **`SIFT_MIN_CONTAINERS=1`** while judges are using it.
- [ ] **Tell Tristan when the 75,841-listing index goes live**, and whenever the URL or response shape changes.

### Ranking (Decide)

- **Keep weak matches out of the top of the cost-per-wear list.** Options:
  1. Rank only the closest N by look (say 20) by cost per wear, then append the rest.
  2. Blend a small match term into the cost-per-wear order.
  3. Frontend only: start the slider a few steps toward "Closer match".

  Option 3 is the smallest change but makes the headline less exact. Option 1 is simple and keeps the headline
  honest.
- **Should quality move cost per wear more?** Today the cheapest almost always wins. A wider wear spread needs
  sources (PEFCR or similar), not tuning by feel.
- **Match bands for worn photos.** Calibrate on real phone photos of the demo props (Haram's), or make bands relative
  to the top result, so a true match can show "Exact match".

### Later

- **`cost.fee_is_max` (bool):** the web app currently hard-codes "up to" for Depop's fee.
- **Normalized sizes** (`size_norm`) before the web app adds filters. `SearchParams.filters` (max price,
  marketplaces, sizes, conditions) is already in the contract.
- **Lower-case `color`** from a fixed list.

## 5. Checking a change from the web side

- **Types the web app expects:** `web/lib/search.ts`, `web/lib/detect.ts`. Update them in the same PR as any
  contract change.
- **Tests:** `cd web && npm test` (display logic only; fixtures are `web/public/samples/*.json`).
- **Saved data must still parse:** `web/public/samples/*.json` (no-backend fallback) and `web/public/landing/wall.json`
  (landing wall). If the shape changes, ask Tristan to regenerate them.
- **Run the app locally:** `cd web && npm run dev`, with `web/.env.local` pointing at the API (a local uvicorn on
  `:8000` works too).
- **Live probe:**

```bash
API=https://lu-anthony-73--sift-api.us-west.modal.run
curl -s -F image=@photo.jpg $API/detect
curl -s -F image=@crop.jpg -F 'params={"category":"hoodies_sweatshirts"}' $API/search | head -c 600
```
