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
| Ranking | The backend computes every number (expected wears, CPW, break-even). The **client** sorts and applies the slider locally, with no extra calls. |
| Result set | A fixed top 50 with no paging. Items below the similarity cutoff are dropped, so the list may be empty. |
| Receipt | Embedded in each search result. There is no per-item endpoint. |
| Evidence in v1 | Listing materials (SCRAPING.md §4) and brand facts (the curated `brands` table). There are no owner reviews or community counts yet. |
| Money | Integer cents, USD only (the index is US-only). |

## 1. Endpoints

### `GET /health`
→ `200 {"status": "ok", "index_size": 20412}`

### `POST /detect`
Finds the garments in a photo.

- Request: `multipart/form-data`, field `image` (JPEG/PNG/WebP, ≤ 10 MB).
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
  "typical": {"price_cents": 6500, "expected_wears_mid": 60, "cpw_cents": 108},
  "results": [ /* Result × 0–50 */ ]
}
```

`typical` is the median match among `results`. It is the "vs. typical match" baseline
on the receipt and the reference for `break_even_wears`. It is `null` when `results` is empty.

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

  "match": {"similarity": 0.91},

  "cost": {
    "price_cents": 4800, "currency": "USD",
    "shipping_cents": null, "free_shipping": null,
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
    "level": "medium", "score": 0.6,
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
    "break_even_wears": 45
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
- `cost.total_cents` = price + shipping when shipping is known, otherwise price. Price sorting and CPW both use it.
- `cost.original_price_cents` is the seller's own markdown. `retail_price_cents` is the new
  retail price. Show "vs retail" only when it is non-null.
- `wear.cpw_cents.at_N` = `round(total_cents / N)`. `at_mid` uses `expected_wears.mid`.
- `wear.basis`: `category_baseline` (no evidence, so the range is the labelled per-category
  assumption) or `evidence_adjusted`.
- `wear.break_even_wears` = how many wears it takes for this item's CPW to drop below
  `typical.cpw_cents`, i.e. `ceil(total_cents / typical.cpw_cents)`. Show the line
  "Break-even: wear this N+ times to win" only when the item costs more than `typical.price_cents`.
- `quality.level == "unknown"` and `facts == []` → show **"Not enough evidence yet."**
  `score` is then `null`, and the item sorts last on that marker but stays in the list.
- `confidence` is the overall amount of evidence behind `wear`. `unknown` is allowed.
- `fact.status`: `verified | claimed | inferred | unknown`. Suggested UI: verified = solid,
  claimed = "as declared", inferred = "likely", unknown = grey "unknown".
- `fact.source`: `specifics | listing_text | product_line | tag_image | model | brand_table | baseline`.
- `fact.kind` is open-ended (for example `materials`, `certification`, `repair_program`,
  `supplier_list`, `secondhand`, `recycled`, `deadstock`, `animal_materials`,
  `synthetic_share`, `country_of_manufacture`). The frontend should render any unknown
  `kind` generically using `label` + `value`.
- The seller block never contains a username, profile URL or full location (SCRAPING.md §3).

## 3. Client-side sorting

The frontend does all re-ordering. Nulls always go last.

| Sort | Key |
| --- | --- |
| Cost per wear (default) | `wear.cpw_cents.at_mid` ascending |
| Price | `cost.total_cents` ascending |
| Look match | `match.similarity` descending |
| Eco | `eco.score` descending |

**Match ↔ value slider** (`w` from 0 = value to 1 = match): sort by
`w · rank_pct(similarity) + (1 − w) · rank_pct(cpw_at_mid)`, where `rank_pct`
is the item's percentile within the current 50 (higher = better). Ties are broken by `id`.
The "cheapest match drops to #N" headline is computed by the client.

## 4. Enums

- `marketplace`: `depop poshmark grailed mercari ebay`
- `category`: `jackets_outerwear hoodies_sweatshirts tshirts sneakers jeans_pants
  sweaters_knitwear shirts dresses_skirts` (the 8 categories in SCRAPING.md §2)
- `condition`: `new_with_tags like_new good fair` (`null` if it can't be mapped)
- `level` / `confidence`: `high medium low unknown`
- `seller.type`: `individual small_shop large_reseller`

## 5. Open items (frontend to fill in as it goes)

- [ ] **Mocks:** fixture JSON files vs a server `MOCK=1` mode vs cached demo-prop responses.
- [ ] **Images:** card uses `thumb_url` (fallback `image_urls[0]`). Is there a full gallery in the receipt?
- [ ] Deployed base URL + CORS origins.
- [ ] Per-category expected-wear baselines (owned by the backend, labelled as assumptions).
- [ ] Owner reviews / community evidence: these would appear as new `fact.kind`s, so the schema does not change.
