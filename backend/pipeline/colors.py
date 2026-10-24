"""Step 05b: one CIELAB colour per indexed listing, for the colour re-rank (backend.color).

Reads an index folder (rows.jsonl from step 05), fetches each listing's first photo again and writes colors.npy
aligned with rows.jsonl (NaN where no photo could be read). Resumable: parts/colors/*.npz keep finished chunks, so a
rerun only fetches new listings."""
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from backend.color import garment_color

UNKNOWN = np.full(3, np.nan, np.float32)


def _color(fetch, urls) -> np.ndarray:
    for url in urls[:2]:
        try:
            return garment_color(fetch(url))
        except Exception:  # noqa: BLE001  a dead photo: try the next, else unknown
            continue
    return UNKNOWN


def build_colors(index_dir, fetch, *, workers: int = 16, chunk: int = 512) -> Counter:
    index_dir, stats = Path(index_dir), Counter()
    parts = index_dir / "parts" / "colors"
    parts.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(line) for line in (index_dir / "rows.jsonl").read_text().splitlines()]
    done = {}
    for f in sorted(parts.glob("*.npz")):
        with np.load(f) as z:
            done.update(zip(z["ids"].tolist(), z["labs"]))
    stats["resumed"] = sum(r["id"] in done for r in rows)
    todo = [r for r in rows if r["id"] not in done]
    n_part = len(list(parts.glob("*.npz")))
    with ThreadPoolExecutor(workers) as pool:
        for i in range(0, len(todo), chunk):
            batch = todo[i:i + chunk]
            labs = np.stack(list(pool.map(lambda r: _color(fetch, r["image_urls"]), batch)))
            stats["no_photo"] += int(np.isnan(labs[:, 0]).sum())
            stats["colored"] += len(batch) - int(np.isnan(labs[:, 0]).sum())
            buf = parts / f"{n_part:05d}.npz.tmp"
            with buf.open("wb") as f:
                np.savez(f, ids=np.array([r["id"] for r in batch]), labs=labs)
            buf.replace(parts / f"{n_part:05d}.npz")
            n_part += 1
            done.update(zip([r["id"] for r in batch], labs))
    out = np.stack([done[r["id"]] for r in rows]).astype(np.float32) if rows else np.zeros((0, 3), np.float32)
    with (index_dir / "colors.npy.tmp").open("wb") as f:
        np.save(f, out)
    (index_dir / "colors.npy.tmp").replace(index_dir / "colors.npy")
    return stats
