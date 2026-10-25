# Sift diagnostic: live app, Oct 24 2026 (evening)

Tested by Tristan's agent on <https://sift-calhacks.vercel.app> and the live API
(`https://lu-anthony-73--sift-api.us-west.modal.run`, 75,839 listings), at `main` = `4fa4621` (#68).
For each teammate's coding agent: find your name, fix your items top to bottom, and check each one against its
**Done when** line. Items marked **Decide** need a quick team call first.

**Severity:** **P0** = a judge will likely see it in the core demo. **P1** = hurts credibility if noticed.
**P2** = polish.

## How it was tested

- **Live site, phone and desktop size:** landing, item panels, upload → detect → results, every garment tab, the
  slider, the Eco tab, the item panel, refresh on `/results` and `/scan`, "< Photo" → "See 50 look-alikes", browser
  Back/Forward, "Draw a box", camera blocked, the internal routes.
- **Live API, 12 photos not in the index** (Wikimedia Commons): product shots and photos of people wearing
  sneakers, t-shirts, a dress, a sweater, a flannel shirt, jeans, a leather jacket and hoodies. These ran the same
  steps the app runs: shrink to 1024 px, `/detect`, crop each garment with 4% padding, `/search`. That's 14 searches
  and 700 results.
- **Every result was checked** for the math and wording rules listed under "What's working".
- **Edge cases:** non-image files, missing fields, bad params, an unknown category, HEIC, a 6000 px photo, the
  wrong HTTP method, and CORS from the live site.

## What's working (keep it that way)

- **The math holds on all 700 results, with 0 failures:**
  - total = price + shipping + buyer fee
  - cost per wear = total ÷ expected wears
  - low ≤ mid ≤ high wears
  - `eco.parts` add up exactly to `eco.score`
  - the `wear.steps` multiply out to the expected wears
- **The data is complete:** every result has `percentile`, and every eco fact has a `part`.
- **The wording is clean:** no em dashes, exclamation marks or virtue words in any server-written text, every URL
  matches its marketplace, and every price is in USD.
- **The API rejects bad input cleanly** with `{"error": {code, message}}`: `invalid_image`, `invalid_params`, an
  unknown category. HEIC works. CORS allows the live site.
- **Speed:** detection takes 2.2–5.5 s warm (12 photos). Search takes 0.4–1.9 s, with one outlier at 3.6 s.
- **The web flow works end to end:** refresh restores results (garment, tab, slider, open item), and the photo
  screen offers "See 50 look-alikes". Back/Forward, Draw a box and the camera-blocked notice all work. The landing
  count is live (75,839).
- **Accessibility basics pass:** every button has a name, images have alt text, inputs are labelled, and there are
  no duplicate IDs.
- **Product shots match well:** a white Air Force 1 photo scored 0.87–0.94, the "exact" band, all Air Force 1s.

## Summary

| ID | Sev | Owner | Finding |
| --- | --- | --- | --- |
| W1 | P0 | Tristan | Accessories (beanie, gloves) are searched anyway: the gloves tab shows puffer jackets |
| D1 | P0 | Team | **Decide** the slider's starting point: main opens at 10 (pure look match), so the cost-per-wear idea is hidden |
| A1 | P0 | Anthony | "No close match" shows on most real photos (7 of 14 searches, all 4 tabs of the outfit photo) |
| N1 | P0 | Andy | Junk listings rank high: a bulk scrap-denim lot, joggers for jeans, titles like "New" and "Title: …" |
| W2 | P0 | Tristan | Landing item panels: stale prices from before buyer fees, and a "86% look match" with no scan |
| A2 | P1 | Anthony | Colour isn't respected: purple and light-blue hoodies for a black one |
| A3 | P1 | Anthony | Detection mislabels: flannel shirt → "plaid shirt jacket" (jackets), black → "navy", a doubtful brand |
| A4 | P1 | Anthony + Andy | Sneakers: quality unknown on 42–45 of 50 results ("Not enough evidence yet" everywhere) |
| A5 | P1 | Anthony + Tristan + Haram | Prices drift (Mercari jacket: $42.75 in our data, $50 live) and nothing says when they were checked |
| A6 | P1 | Anthony | Cold or large photos take 12.8–16.7 s to detect, against the app's 15 s limit |
| W3 | P1 | Tristan | No link-preview tags: a shared link shows no title card or image |
| W4 | P1 | Tristan + Haram | The landing's WRAP stat links to a news article, not WRAP |
| H1 | P1 | Haram | The README doesn't link the live app or say how to try it |
| W5 | P2 | Tristan | After a refresh, "Searching 0 listings" flashes during the transition |
| A7 | P2 | Anthony + Tristan | The counter says "75,839 listings" while searching one category |
| W6 | P2 | Tristan | `/design` (design lab, sample data) and `/landing/*` are public and indexable |
| W7 | P2 | Tristan | "Wrong garment? Draw a box" is an 18 px tap target; no h2 between the h1 and the results |
| A8 | P2 | Anthony | `GET /search` returns FastAPI's `{"detail": …}`, not the error shape |

---

## Team decisions

### D1 (P0, Decide): where the slider starts

- **Now on main** (#68, `web/components/scan/scan-flow.tsx`): `mix: 10`, so a new scan opens on pure look match.
  The tab still says "Cost per wear" while the list is sorted by look. The landing promises "ranked by cost per wear".
  On the outfit photo the gloves tab's #1 cost **$3.84 a wear**, and the headline is hidden.
- **Tristan's open branch `slider-middle`** sets `mix: 5`. It conflicts with #68 on that same line.
- **Data:** at pure cost per wear (0), the #1 result was a median of #31 of 50 by look (range #12–#50). At 5, the top
  rows were close matches with good value in every search tried (black hoodies for a black hoodie, Levi's for jeans,
  Air Force 1s for Air Force 1s).
- **Recommendation:** start at 5, so the first screen shows both the idea and close matches. Resolve the conflict in
  one PR.

### Demo photos (Haram)

Product-style photos (shoes on a plain background) had top matches of 0.81–0.94 and reached "exact" or "close".
Photos of people wearing clothes had top matches of 0.64–0.82. For judging, scan props laid flat or held up against a plain wall.

---

## Tristan (web)

### W1 (P0): accessories are searched as other categories

- **Seen:** the outfit photo returned 4 garments. "Black knit beanie" gets titled **Sweaters** with sweater results,
  and "Black winter gloves" gets titled **Jackets** with puffer jackets.
- **Cause:** `/detect` returns `category: null` for things outside the 8 categories. `toGarments`
  (`web/lib/detect.ts`) turns null into `''`, and an empty category means "let the backend guess"
  (`web/components/scan/scan-flow.tsx`), so it guesses the nearest category.
- **Fix:** keep `null` as "not in our catalog" (a flag on `Garment`). Don't search those garments. Their tab shows
  a short notice: "Hats and gloves aren't in our catalog yet." Drawn boxes and the whole-photo fallback keep `''`
  (guessing is right for those). If every garment is out of catalog, show the notice instead of results.
- **Done when:** the outfit photo's beanie and gloves tabs show the notice, the jacket and jeans tabs are unchanged,
  and there's a red/green test in `web/lib/detect.test.ts`.

### W2 (P0): landing item panels use stale data and scan wording

- **Seen:** `web/public/landing/wall.json` was built from the 51,131-listing index, before buyer fees. Its prices
  don't include fees, though the panel says "Price with shipping and fees". It has no `eco.parts`, `wear.steps` or
  `percentile`. The panel also says "86% look match" and "Half of these look-alikes…", but a landing visitor hasn't
  scanned anything.
- **Fix:**
  - Rebuild `wall.json` from the live API with the same three queries in its `meta`.
  - Pass `context='landing'` from `web/components/landing/hero-wall.tsx` to `ReceiptSheet`.
  - In that context, hide the look-match line and the "Compared with a typical look-alike" card.
- **Done when:** a landing panel shows the eco bars and the wear steps, no look match, and a total that includes fees.

### W3 (P1): link previews

- **Seen:** no `og:*` or `twitter:*` tags, `/opengraph-image` is 404, and `/favicon.ico` is 404 (`/icon.svg` works).
- **Fix:** add `metadataBase`, `openGraph` and `twitter` in `web/app/layout.tsx`, plus `web/app/opengraph-image.png`
  (the forest card with the logo and "Buy it once.").
- **Done when:** pasting the link into Slack or iMessage shows the card.

### W4 (P1): WRAP citation

- **Seen:** "Wearing clothes 9 months longer cuts… 20–30%. WRAP" links to a sustainablebrands.com news article
  (`WRAP_URL`, `web/components/landing/landing-shell.tsx`).
- **Fix:** link to WRAP's own "Valuing our clothes" report on wrap.ngo, after confirming the page states the figure.
- **Done when:** the link lands on a WRAP page that shows the 20–30% figure.

### W5 (P2): "Searching 0 listings" flash after a refresh

- **Seen:** a restored scan starts its counter at `total: 0`. The counter shows under the results while they fade in,
  so it flashes "Searching 0 listings".
- **Fix:** in `scan-flow.tsx`, fill `total` from `indexSize()` on restore. Or, in `camera-screen.tsx`, render no
  counter when `handedOff` and the scan was restored.
- **Done when:** refreshing `/results` never shows "0 listings".

### W6 (P2): internal pages are public

- **Fix:** add `robots: { index: false }` to `web/app/design/page.tsx` and `web/app/landing/[variant]/page.tsx`.
  Optionally, hide `/design` in production.

### W7 (P2): small tap target and headings

- **Fix:** add `py-2 -my-2` to the "Draw a box" button in `results-screen.tsx`. Make the results list's section
  heading an `h2`, or make the row titles `h2`.

---

## Anthony (backend, ranking, detection)

**Status (Anthony, Oct 24 evening, PR #71):** A1, A2, A3, A5, A6 (server shrink), A7, A8 done; A4 partly (seller-stated
uppers from descriptions; the product-line list the fix asks for contradicts the evidence rule in
`backend/pipeline/product_lines.yaml`: Air Force 1, Dunk and 550 ship in synthetic leather too, so they are not one
fabric per line); N1 done in the API (lots and bundles dropped and titles mended when the index loads, no re-embedding;
Andy can move it into the pipeline). Live after the redeploy; `SIFT_MIN_CONTAINERS=1` is set for judging.

### A1 (P0): bands are tuned on product shots, so real photos read "No close match"

- **Seen:** the band of the best result (`headline.match`) was `similar` in 7 of 14 searches. The web shows "No close
  match: 50 similar jackets" for those, including all 4 tabs of the outfit photo, even when the matches look right
  (Levi's for blue jeans). Product shots had top matches of 0.81–0.94. Worn photos had top matches of 0.64–0.82.
- **Fix:**
  - Calibrate the bands on real phone photos of the demo props, or make them relative to the query: a best match
    within about 0.03 of the best possible for that kind of photo counts as "close".
  - At minimum, only send `headline.match: "similar"` when the top similarity is really low (below about 0.6).
  - Tristan will soften the web copy to match whatever you choose.
- **Done when:** the demo props and a typical worn photo say "close" or better, and a bad match (a t-shirt with an
  unusual print) still says "similar".

### A2 (P1): colour isn't respected

- **Seen:**
  - The black zip hoodie's #2 by look was "Purple cropped hoodie" (0.67), and its cheapest-per-wear pick was "Women's
    Light blue cropped hoodie".
  - A black jacket photo's top 8 included navy, blue, yellow and grey listings (seen earlier today).
- **Check:** is `colors.npy` built for the current 75,839-listing index? HANDOFF says to run
  `modal run modal_app.py::colors --name full` after every `::embed`, then redeploy.
- **Done when:** a black garment's top 10 by look are all black or dark grey.

### A3 (P1): detection labels and categories

- **Seen:**
  - A flannel shirt was labelled "plaid shirt jacket" in `jackets_outerwear`.
  - A black graphic hoodie was labelled "navy hoodie", with the brand "Shadywear" (unverified, and if wrong, it lifts
    the wrong listings).
  - Wrangler jeans on a table were labelled "pants" at 0.37 confidence.
- **Fix:**
  - In `backend/src/backend/detect.py`: shirts with buttons and a collar go to `shirts` unless clearly padded.
  - Name colours conservatively (black over navy when unsure).
  - Only send `brand` when the logo or text is clearly legible.
- **Done when:** these three photos come back as shirt, black hoodie (no brand) and jeans.

### A4 (P1, with Andy): sneaker quality is almost always unknown

- **Seen:** quality was unknown on 44/50, 42/50 and 45/50 sneaker results, so almost every row says "Not enough
  evidence yet" and the Quality card is empty.
- **Fix:** add the top resale models to the product-line table (#12): Air Force 1, Dunk Low, Chuck Taylor and Jack
  Purcell, Samba, New Balance 550/990. Materials and construction are known per line.
- **Done when:** under 50% of sneaker results are unknown.

### A5 (P1, with Tristan and Haram): price freshness

- **Seen:** Mercari `m86859246185` is $42.75 + $8.49 shipping in our data, but $50 on Mercari now. The listings
  spot-checked were all still for sale. The facts date from Oct 23–24.
- **Fix:**
  - Anthony: pass `scraped_at` through on each result (`PASS_THROUGH` in `ranker.py`).
  - Tristan: show "Price checked Oct 24" under the View button.
  - Haram: re-check the demo props' top 3 results on the morning of judging.
- **Done when:** the item panel shows the date, and the demo listings are confirmed live.

### A6 (P1): slow detection on cold starts and large photos

- **Seen:** a HEIC photo took 12.8 s and a 6000 px photo took 16.7 s. The web gives up at 15 s and searches the whole
  photo. The web already shrinks photos to 1024 px, so cold starts are the real risk.
- **Fix:** deploy with `SIFT_MIN_CONTAINERS=1` for judging, as HANDOFF suggests. Optionally shrink anything over
  2048 px on the server before detection.
- **Done when:** detection stays under 5 s for an hour of idle followed by a scan.

### A7 (P2, with Tristan): the counter overstates the search

- **Seen:** the counter reads "Searched jackets" with 75,839 listings, but only the jacket listings are searched.
- **Fix:** add `by_category` counts to `/health` (asked in `web/NOTES-FOR-BACKEND.md`). Tristan shows "Searched
  N jackets" with the real count.

### A8 (P2): error shape for the wrong method

- **Seen:** `GET /search` returns `{"detail": "Method Not Allowed"}`.
- **Fix:** map 405 and 404 to `{"error": {...}}` in `app.py`.

---

## Andy (data)

### N1 (P0): junk listings and messy titles

- **Seen in top results:**
  - "Bulk Denim Jeans Lot 10+ lb Mens Womens Scrap Crafting" was the **#1 look match** for a pair of Wrangler jeans.
  - "Women's CloudKnit Jogger" was #2, and "Nike sweatpants" was #1 at slider 5, for jeans.
  - Some titles are "New", "Title: Uniqlo Ultra Light Down…", or sales copy ("Introducing our versatile…",
    "Discover ultimate comfort and…", "The ultimate winter staple!…").
- **Fix (pipeline cleaning, then re-index):**
  - Drop lots, bundles and scrap or crafting listings (title or description matching
    `lot|bundle|bulk|scrap|crafting|wholesale|\d+ ?lb`).
  - Strip a leading `Title:`.
  - When a title is under 3 words or a stock opener, build it from brand + category + colour.
  - Optional: tag sweatpants and joggers as `subcategory` so jeans searches can push them down.
- **Done when:** none of those appear in the top 10 for the Wrangler and outfit photos, and no title starts with
  "Title:" or is just "New".

### A4 (with Anthony): sneaker evidence

Listing fields for sneaker materials, where they exist (eBay item specifics: Upper Material).

---

## Haram (demo and story)

### H1 (P1): README

- **Fix:** put the live link and a 3-line "try it" at the top of `README.md`: open on a phone, tap Scan an outfit,
  tap any result for its cost-per-wear breakdown.

### Demo checklist (the morning of Oct 25)

1. Scan each prop. Confirm the band says close or exact (A1), the colours match (A2), and the top 3 are live listings
   (A5).
2. Ask Anthony to confirm `SIFT_MIN_CONTAINERS=1` is deployed (A6).
3. Open the item panel on the #1 result. Walk through price ÷ wears, how the wears were reached, the eco bars, and
   the comparison with a typical look-alike.

---

## Re-check recipe

```bash
API=https://lu-anthony-73--sift-api.us-west.modal.run
curl -s $API/health
curl -s -F image=@photo.jpg $API/detect
curl -s -F image=@crop.jpg -F 'params={"category":"jeans_pants"}' $API/search | head -c 800
```
