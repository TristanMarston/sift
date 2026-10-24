"""In-memory catalog search over the step-05 index (pipeline/data/index/). Exact cosine search: one
matrix-vector product, then numpy masks for the API filters. ~10 ms at 50k rows."""
import json
from pathlib import Path

import numpy as np


class Index:
    def __init__(self, vecs: np.ndarray, rows: list[dict]):
        if len(vecs) != len(rows):
            raise ValueError(f"{len(vecs)} vectors but {len(rows)} rows")
        self.vecs, self.rows = np.asarray(vecs, np.float32), rows
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
        return cls(np.load(path / "embeddings.npy"), rows)

    def __len__(self):
        return len(self.rows)

    def search(self, query: np.ndarray, k: int = 50, min_sim: float = 0.0, category=None, max_price_cents=None,
               marketplaces=None, sizes=None, conditions=None) -> list[tuple[dict, float]]:
        """Up to k (row, cosine) pairs above min_sim that pass every filter, most similar first."""
        if not self.rows:
            return []
        sims = self.vecs @ np.asarray(query, np.float32)
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
        hits = hits[np.argsort(-sims[hits], kind="stable")][:k]
        return [(self.rows[i], float(sims[i])) for i in hits]
