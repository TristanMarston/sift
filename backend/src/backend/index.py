"""In-memory catalog search over the step-05 index (pipeline/data/index/). Exact cosine search: one
matrix-vector product, then numpy masks for the API filters. ~10 ms at 50k rows."""
import json
import re
from pathlib import Path

import numpy as np

from backend import color as C
from backend.markers import brand_key

BRAND_BOOST = 0.1   # a brand Haiku read off the photo (a logo, a label) outranks a look-alike of another brand
# Rows the index refuses to serve: lots, bundles and scrap. "Bulk Denim Jeans Lot 10+ lb Scrap Crafting" was the #1 look
# match for a pair of jeans. Titles only (descriptions say "bundle discounts"), and "lot" only next to a count: "lots of
# life left" and "without the bulk" are single garments. ~200 of 75,841 rows. Dropped at load, so no re-embedding; the
# pipeline can drop them upstream later and this stays a no-op.
JUNK = re.compile(r"\blots?\s*(?:of\s*)?\(?\d|\b\d+\+?\s*(?:pcs?|pieces?|items?|pairs?)?\s*lot\b|\bbundles?\b"
                  r"|\bscrap\b|\bcrafting\b|\bwholesale\b|\b\d+\s?lbs?\b", re.I)
NOT_JUNK = re.compile(r"off[- ]white", re.I)   # Nike Dunk Low x Off-White "Lot 08" is a colourway, not a lot
STOCK = {"new", "nwt", "nwot", "nib", "bnwt", "on", "hold", "lightly", "used", "product", "details", "title", "deadstock",
         "brand", "excellent", "condition", "sold", "as", "is", "sale", "listing", "item"}   # a title made only of these says nothing
NAME = {"jackets_outerwear": "jacket", "hoodies_sweatshirts": "hoodie", "tshirts": "t-shirt", "sneakers": "sneakers",
        "jeans_pants": "pants", "sweaters_knitwear": "sweater", "shirts": "shirt", "dresses_skirts": "dress"}


def junk(row: dict) -> bool:
    title = row.get("title") or ""
    return bool(JUNK.search(title)) and not NOT_JUNK.search(title)


def mend_title(row: dict) -> str:
    """Strip a pasted "Title:"; a one-word title ("UNIQLO", "9M") or one made of stock words ("New", "ON HOLD", "Lightly
    used!") becomes brand + colour + garment. "Brown sweater" stays as the seller wrote it."""
    title = re.sub(r"^\s*title:\s*", "", row.get("title") or "", flags=re.I).strip()
    words = re.findall(r"[a-z0-9]+", title.lower())
    if len(words) >= 2 and not set(words) <= STOCK:
        return title
    colour = (row.get("color") or "").split(",")[0].strip().lower()
    made = " ".join(x for x in (row.get("brand"), colour, NAME.get(row.get("category"))) if x)
    return (made[:1].upper() + made[1:]) if made else title


class Index:
    def __init__(self, vecs: np.ndarray, rows: list[dict], colors: np.ndarray | None = None):
        if len(vecs) != len(rows):
            raise ValueError(f"{len(vecs)} vectors but {len(rows)} rows")
        if colors is not None and len(colors) != len(rows):
            raise ValueError(f"{len(colors)} colours but {len(rows)} rows")
        self.vecs, self.rows = np.asarray(vecs, np.float32), rows
        self.colors = None if colors is None else np.asarray(colors, np.float32)   # CIELAB per row, NaN = unknown
        col = lambda f: np.array([f(r) or "" for r in rows], dtype=str)  # noqa: E731
        self._category = col(lambda r: r["category"])
        self._marketplace = col(lambda r: r["marketplace"])
        self._size = col(lambda r: (r.get("size") or "").lower())
        self._condition = col(lambda r: r.get("condition"))
        self._total = np.array([r["cost"]["total_cents"] for r in rows], dtype=np.int64)
        self._brand = col(lambda r: brand_key(r.get("brand")))

    @classmethod
    def load(cls, path) -> "Index":
        path = Path(path)
        rows = [json.loads(line) for line in (path / "rows.jsonl").read_text().splitlines()]
        colors = np.load(path / "colors.npy") if (path / "colors.npy").exists() else None
        vecs = np.load(path / "embeddings.npy")
        if len(vecs) != len(rows) or (colors is not None and len(colors) != len(rows)):
            raise ValueError(f"{len(vecs)} vectors, {len(rows)} rows, {None if colors is None else len(colors)} colours")
        keep = np.array([not junk(r) for r in rows], bool)
        rows = [{**r, "title": mend_title(r)} for r, k in zip(rows, keep) if k]
        return cls(vecs[keep], rows, None if colors is None else colors[keep])

    def __len__(self):
        return len(self.rows)

    def by_category(self) -> dict:
        """Rows per category: what a search in that category actually looks through."""
        cats, counts = np.unique(self._category, return_counts=True)
        return {str(c): int(n) for c, n in zip(cats, counts) if c}

    def search(self, query: np.ndarray, k: int = 50, min_sim: float = 0.0, category=None, max_price_cents=None,
               marketplaces=None, sizes=None, conditions=None, dedupe: float | None = None,
               color=None, brand: str | None = None) -> list[tuple[dict, float]]:
        """Up to k (row, cosine) pairs above min_sim that pass every filter, most similar first. With `dedupe`, listings
        whose photos are at least that similar to each other are one item (cross-posted or relisted): the cheapest
        copy is kept, and duplicates don't use up result slots. With `color` (the query's CIELAB) and an index that
        has colours, the order is similarity minus a colour penalty (backend.color); the returned cosine is unchanged.
        `brand` (read off the photo) adds BRAND_BOOST to that brand's listings."""
        if not self.rows:
            return []
        sims = self.vecs @ np.asarray(query, np.float32)
        score = sims
        if color is not None and self.colors is not None and not np.isnan(np.asarray(color, np.float64)).any():
            score = sims - C.penalty(self.colors, color)
        if brand and brand_key(brand):
            score = score + BRAND_BOOST * (self._brand == brand_key(brand))
        keep = sims >= min_sim
        if category:
            keep &= self._category == category
        if max_price_cents is not None:
            keep &= self._total <= max_price_cents
        if marketplaces:
            keep &= np.isin(self._marketplace, marketplaces)
        if sizes:
            keep &= np.isin(self._size, [s.lower() for s in sizes])
        if conditions:
            keep &= np.isin(self._condition, conditions)
        hits = np.flatnonzero(keep)
        hits = hits[np.argsort(-score[hits], kind="stable")]
        if dedupe is None:
            hits = hits[:k]
        else:
            pool = hits[:3 * k]                       # enough room for the copies we drop
            kept = []
            for i in pool[np.argsort(self._total[pool], kind="stable")]:   # cheapest copy first
                if not kept or float(np.max(self.vecs[kept] @ self.vecs[i])) < dedupe:
                    kept.append(i)
            hits = np.array(kept, dtype=int)
            hits = hits[np.argsort(-score[hits], kind="stable")][:k]
        return [(self.rows[i], float(sims[i])) for i in hits]
