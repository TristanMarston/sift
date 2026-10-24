# Sample search results

Used only when `NEXT_PUBLIC_API_URL` is empty, and always shown with a "Sample results" tag.

- Made by running the team's ranker (`origin/ranker`, `backend/src/backend/ranker.py`) on the test scrape
  (426 listings, Oct 24 2026), one file per demo prop: `jackets_outerwear` (Carhartt Detroit jacket),
  `sweaters_knitwear` (Patagonia Better Sweater), `sneakers` (Nike Dunk Low).
- Listings, photos, prices, materials and every marker, wear and cost-per-wear number come from the ranker.
- **Look-match scores are made up** (there were no image embeddings yet): listings closer to the prop score higher.
- Shape: `SearchResponse` in `schema/API.md` (the ranker branch's version), plus a `sample` note.
