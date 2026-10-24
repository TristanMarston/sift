# Sift — Frontend ↔ Backend API Contract

Location: `schema/API.md`. Machine-readable source of truth: `schema/api.schema.json`
(JSON Schema 2020-12). If this file and the schema disagree, **the schema wins**.
Changing either one needs a quick team huddle (DESCRIPTION.md §9).

Audience: Tristan (web) and Anthony/Andy (backend), plus their coding agents.
Decided in the interview on Fri Oct 23, 2026.

## 0. Decisions

| Topic | Decision |
| --- | --- |
| Backend | Python FastAPI. JSON over HTTPS, except image uploads (multipart). |
| Markers | Three markers per item: **cost**, **quality**, **eco**, plus **cost per wear** as the hero sort. |
| Marker form | `level` (`high`/`medium`/`low`/`unknown`) + `score` 0–1 (**for sorting only, never shown**) + `facts[]` with source and status. |
| Eco | Shown as facts (materials, recycled, deadstock, certifications). It is not a "sustainable" claim (DESCRIPTION.md §10.6). |
| Photo flow | Two calls: `POST /detect` → the frontend crops → `POST /search` per garment. |
| Ranking | The **backend** computes every number *and* every order: the 4 sorts, 11 slider stops and the "cheapest drops to #N" headline arrive in one response. The frontend only picks a list to show, so the reshuffle is instant with no extra calls. |
| Result set | A fixed top 50 with no paging. Items below the similarity cutoff are dropped, so the list may be empty. |
| Receipt | Embedded in each search result. There is no per-item endpoint. |
| Evidence in v1 | Listing materials (backend/pipeline/SCRAPING.md §4) and brand facts (the curated `brands` table). There are no owner reviews or community counts yet. |
| Money | Integer cents, USD only. The index holds any secondhand listing priced in USD, wherever it ships from; `seller.region` records the country. |
| Not in v1 | Resale, owner reviews, community evidence, "what you have" input. Reviews/community will arrive as new `fact.kind`s with no schema change. |
| Backend models | Pydantic models are hand-written in `backend/src/backend/`. A pytest validates real responses against `api.schema.json`. Python 3.12. |

## 1. Endpoints

### `GET /health`
→ `200 {"status": "ok", "index_size": 20412}`

### `POST /detect`
Finds the garments in a photo.

- Request: `multipart/form-data`, field `image` (JPEG/PNG/WebP/HEIC, ≤ 10 MB).
  The frontend should downscale to a long edge of ~1024 px before upload.
- Response `200`: `DetectResponse`

```json
{
  "image": {"width": 1024, "height": 768},
  "garments": [
    {"id": "g0", "category": "jackets_outerwear", "label": "jacket",
     "box": {"x": 0.12, "y": 0.08, "w": 0.55, "h": 0.70}, "confidence": 0.91}
  ]
}
```

- `box` is normalized 0–1 relative to the uploaded image, with the origin at the top left.
- The list is sorted by `confidence` descending. One tab per garment.
- **Empty `garments`** → the frontend treats the whole image as one garment (or lets
  the user draw a box) and calls `/search` with no `category`.

### `POST /search`
Finds look-alikes for one garment crop and returns the full receipt data for each result.

- Request: `multipart/form-data`
  - `image`: the cropped garment (the frontend crops on a canvas using `box`).
  - `params`: a JSON string matching `SearchParams`:

```json
{
  "category": "jackets_outerwear",
  "filters": {
    "max_price_cents": 15000,
    "marketplaces": ["depop", "ebay"],
    "sizes": ["M", "L"],
    "conditions": ["like_new", "good"]
  }
}
```

  Every field is optional. `category` (from `/detect`) restricts the search to that
  category. `sizes` is a case-insensitive exact match on the raw size string.
- Response `200`: `SearchResponse` (§2). The results come pre-sorted by CPW. 0–50 items.

### `POST /jpeg`
For a browser that cannot decode the photo it was handed (Chrome with an iPhone HEIC): the same photo back as an
upright JPEG with a long edge of at most 1024 px, so the usual crop-and-search carries on. Same request shape and
error codes as `/detect`; response `200` is the image (`Content-Type: image/jpeg`).

### Errors
Any non-2xx response has the body `{"error": {"code": "...", "message": "..."}}`.

| HTTP | `code` | When |
| --- | --- | --- |
| 400 | `invalid_image` | The image is unreadable or of an unsupported type |
| 400 | `invalid_params` | `params` is not valid JSON or fails the schema |
| 413 | `image_too_large` | The image is > 10 MB |
| 500 | `internal` | Anything else |

## 2. `SearchResponse`

```json
{
  "query": {"category": "jackets_outerwear", "filters": {}},
  "typical": {"price_cents": 4000, "expected_wears_mid": 60, "cpw_cents": 67},
  "results": [ /* Result × 0–50, in cost-per-wear order */ ],
  "orders": {
    "cpw":   ["poshmark:64f1a2", "depop:91", "ebay:77"],
    "price": ["depop:91", "poshmark:64f1a2", "ebay:77"],
    "match": ["ebay:77", "poshmark:64f1a2", "depop:91"],
    "eco":   ["poshmark:64f1a2", "ebay:77", "depop:91"]
  },
  "slider": [ /* 11 id lists: slider[0] = orders.cpw … slider[10] = orders.match */ ],
  "headline": {"cheapest_id": "depop:91", "cheapest_rank_by_cpw": 2}
}
```

- `typical` is the median match among `results` (median price, median expected wears). It is the
  "vs. typical match" baseline on the receipt and the reference for `break_even_wears`. `null` when `results` is empty.
- `orders`, `slider` and `headline` are §3. Every list is a permutation of the `results` ids.

### `Result` (one card + its receipt)

```json
{
  "id": "poshmark:64f1a2",
  "marketplace": "poshmark",
  "url": "https://poshmark.com/listing/...",
  "title": "Carhartt Detroit Jacket Brown Duck",
  "brand": "Carhartt",
  "category": "jackets_outerwear",
  "subcategory": "work jacket",
  "size": "M",
  "color": "brown",
  "condition": "good",
  "condition_raw": "Good - used",
  "thumb_url": "https://<supabase>/storage/v1/object/public/thumbs/poshmark/64f1a2.jpg",
  "image_urls": ["https://...", "https://..."],
  "flags": {"is_vintage": true, "is_deadstock": false, "is_upcycled": false},

  "match": {"similarity": 0.91, "band": "exact"},

  "cost": {
    "price_cents": 4800, "currency": "USD",
    "shipping_cents": null, "free_shipping": null,
    "fee_cents": 0,
    "total_cents": 4800,
    "original_price_cents": 6000,
    "retail_price_cents": null
  },

  "materials": {
    "fibers": [{"fiber": "cotton", "pct": 100, "organic": false, "recycled": false}],
    "synthetic_share": 0,
    "certifications": [],
    "composition_suspect": false
  },

  "quality": {
    "level": "high", "score": 0.82,
    "facts": [
      {"kind": "materials", "label": "Materials", "value": "100% cotton duck",
       "status": "inferred", "source": "product_line", "source_url": null,
       "snippet": "Carhartt Detroit → cotton duck", "as_of": "2026-10-23"},
      {"kind": "repair_program", "label": "Maker support", "value": "Repair program offered",
       "status": "claimed", "source": "brand_table",
       "source_url": "https://www.carhartt.com/...", "snippet": null, "as_of": "2026-10-24"}
    ]
  },

  "eco": {
    "level": "medium", "score": 0.6, "percentile": 72,
    "facts": [
      {"kind": "secondhand", "label": "Secondhand", "value": "Already in use (vintage)",
       "status": "verified", "source": "listing_text", "source_url": null,
       "snippet": "vintage 90s", "as_of": "2026-10-23"}
    ]
  },

  "wear": {
    "expected_wears": {"low": 120, "high": 200, "mid": 160},
    "basis": "evidence_adjusted",
    "cpw_cents": {"at_30": 160, "at_60": 80, "at_100": 48, "at_mid": 30},
    "break_even_wears": 72,
    "facts": [
      {"kind": "baseline", "label": "Typical lifespan", "value": "67–167 wears for jackets & outerwear",
       "status": "inferred", "source": "baseline", "source_url": "https://www.carbonfact.com/hubfs/A&FW_PEFCR_v3.1.pdf",
       "snippet": "EU PEFCR Apparel & Footwear v3.1 (2025), Table 6 default uses, ...", "as_of": "2026-10-23"},
      {"kind": "condition", "label": "Condition", "value": "Good: about 80% of its life left (assumption)",
       "status": "inferred", "source": "baseline", "source_url": null, "snippet": "Good - used", "as_of": "2026-10-23"}
    ]
  },

  "confidence": "high",
  "seller": {"type": "small_shop", "rating": 4.9, "region": "CA"}
}
```

### Field rules

- **Nullable means "unknown".** The UI renders `null` as "unknown". It never hides the line
  and never shows 0. This covers `retail_price_cents`, `shipping_cents`, `fibers[].pct`,
  `synthetic_share`, `seller.*`, `subcategory`, `size`, `color`, `brand`, and `thumb_url`.
- `id` = `"<marketplace>:<external_id>"`. It is stable across responses, so use it as the React key
  and as the animation key for the reshuffle.
- `cost.total_cents` = price + shipping when shipping is known (otherwise price) + `fee_cents`. Price sorting and CPW
  both use it. `fee_cents` is what the marketplace charges the buyer at checkout: Mercari's Buyer Protection fee
  (Mercari's own figure, 3.6% of item + buyer-paid shipping) and Depop's Marketplace fee at its stated maximum
  ("up to 5% + $1" of the item price: show it as "up to"). eBay US, Grailed and Poshmark charge buyers nothing, so 0.
- `cost.original_price_cents` is the seller's own markdown. `retail_price_cents` is the new
  retail price. Show "vs retail" only when it is non-null.
- `wear.cpw_cents.at_N` = `round(total_cents / N)`. `at_mid` uses `expected_wears.mid`.
- `wear.basis`: `category_baseline` (no evidence, so the range is the labelled per-category
  assumption) or `evidence_adjusted`.
- `wear.break_even_wears` = how many wears it takes for this item's CPW to drop below
  `typical.cpw_cents`, i.e. `ceil(total_cents / typical.cpw_cents)`. It is **non-null only when the item
  costs more than the typical match**, so the UI shows "Break-even: wear this N+ times to win" exactly when it is set.
- `wear.facts` are the assumptions behind `expected_wears` (the category baseline and the condition factor).
  Show them under "Expected wears" so the number is never a black box.
- `match.band`: `exact` when `similarity ≥ 0.9`, `close` from 0.8 (the same garment in another colour or cut),
  otherwise `similar` (the kind of thing).
- `thumb_url` is a small (~320 px) variant of the first photo, fast on a phone. Use `image_urls` for the full gallery.
- `quality.level == "unknown"` and `facts == []` → show **"Not enough evidence yet."**
  `score` is then `null`, and the item sorts last on that marker but stays in the list.
- `eco.score` (0–1) is continuous, so the eco sort always separates a result list. Every item is secondhand (the
  new-garment impact is avoided for all of them); what separates them: **natural-fiber share** 35% (stated, or a
  fabric named in the title; 50% neutral when unstated), **durability** 30% (expected wears vs the category's typical:
  a garment that lasts replaces more new clothing), **shipping** 15% (US 1.0, abroad 0.4, unknown 0.6), **circularity**
  20% (vintage/deadstock/upcycled, recycled, organic, certifications, capped). Weights are a team judgement.
  `level`: `high` ≥ 0.70 (cotton + vintage, or cotton + built to last), `low` < 0.40 (synthetic, or long-haul with
  nothing else), else `medium`; never `unknown`. `eco.percentile` = share of the other results with a lower score:
  show "Greener than 72% of these matches". The facts say which signals applied (`fabric_unknown`, `durability`,
  `shipping` are new kinds).
- `confidence` is the overall amount of evidence behind `wear`. `unknown` is allowed.
- `fact.status`: `verified | claimed | inferred | unknown`. Suggested UI: verified = solid,
  claimed = "as declared", inferred = "likely", unknown = grey "unknown".
- `fact.source`: `specifics | listing_text | product_line | tag_image | model | brand_table | baseline`.
- `fact.kind` is open-ended (for example `materials`, `certification`, `repair_program`,
  `supplier_list`, `secondhand`, `recycled`, `deadstock`, `animal_materials`,
  `synthetic_share`, `country_of_manufacture`). The frontend should render any unknown
  `kind` generically using `label` + `value`.
- The seller block never contains a username, profile URL or full location (backend/pipeline/SCRAPING.md §3).

## 3. Sorting (done by the backend)

The frontend never sorts or scores. It shows `results` looked up by id in the order it needs:

| UI control | Use |
| --- | --- |
| Sort: cost per wear (default) | `orders.cpw` (lowest `wear.cpw_cents.at_mid` first) |
| Sort: price | `orders.price` (lowest `cost.total_cents` first) |
| Sort: look match | `orders.match` (highest `match.similarity` first) |
| Sort: eco | `orders.eco` (highest `eco.score` first) |
| Match ↔ value slider | `slider[round(position × 10)]`, position 0 = best value … 1 = closest match |
| "The cheapest match drops to #N" | `headline.cheapest_rank_by_cpw` (null when there are no results) |

Ties always break by `id`, so an order never flickers between responses. The slider blends each item's
rank by value and by match: `slider[i]` sorts by `i/10 × match rank + (1 − i/10) × value rank`, so `slider[0]`
equals `orders.cpw` and `slider[10]` equals `orders.match`.

```ts
const byId = Object.fromEntries(resp.results.map(r => [r.id, r]));
const shown = resp.orders[sort].map(id => byId[id]);          // or resp.slider[Math.round(pos * 10)]
```

## 4. Enums

- `marketplace`: `depop poshmark grailed mercari ebay`
- `category`: `jackets_outerwear hoodies_sweatshirts tshirts sneakers jeans_pants
  sweaters_knitwear shirts dresses_skirts` (the 8 categories in backend/pipeline/SCRAPING.md §2)
- `condition`: `new_with_tags like_new good fair` (`null` if it can't be mapped)
- `level` / `confidence`: `high medium low unknown`
- `seller.type`: `individual small_shop large_reseller`

## 5. Open items (frontend to fill in as it goes)

- [ ] **Mocks:** fixture JSON files vs a server `MOCK=1` mode vs cached demo-prop responses.
- [ ] **Images:** card uses `thumb_url` (fallback `image_urls[0]`). Is there a full gallery in the receipt?
- [ ] Deployed base URL + CORS origins.
- [ ] Per-category expected-wear baselines (owned by the backend, labelled as assumptions).
- [ ] Owner reviews / community evidence: these would appear as new `fact.kind`s, so the schema does not change.
