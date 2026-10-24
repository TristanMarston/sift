"""In-memory catalog search over the step-05 index (pipeline/data/index/). Exact cosine search: one
matrix-vector product, then numpy masks for the API filters. ~10 ms at 50k rows."""
import json
from pathlib import Path

import numpy as np

from backend import color as C


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

    @classmethod
    def load(cls, path) -> "Index":
        path = Path(path)
        rows = [json.loads(line) for line in (path / "rows.jsonl").read_text().splitlines()]
        colors = np.load(path / "colors.npy") if (path / "colors.npy").exists() else None
        return cls(np.load(path / "embeddings.npy"), rows, colors)

    def __len__(self):
        return len(self.rows)

    def search(self, query: np.ndarray, k: int = 50, min_sim: float = 0.0, category=None, max_price_cents=None,
               marketplaces=None, sizes=None, conditions=None, dedupe: float | None = None,
               color=None) -> list[tuple[dict, float]]:
        """Up to k (row, cosine) pairs above min_sim that pass every filter, most similar first. With `dedupe`, listings
        whose photos are at least that similar to each other are one item (cross-posted or relisted): the cheapest
        copy is kept, and duplicates don't use up result slots. With `color` (the query's CIELAB) and an index that
        has colours, the order is similarity minus a colour penalty (backend.color); the returned cosine is unchanged."""
        if not self.rows:
            return []
        sims = self.vecs @ np.asarray(query, np.float32)
        score = sims
        if color is not None and self.colors is not None and not np.isnan(np.asarray(color, np.float64)).any():
            score = sims - C.penalty(self.colors, color)
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
