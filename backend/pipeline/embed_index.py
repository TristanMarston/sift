"""Step 05 logic: embed one photo per active listing and write the search index.

out_dir/
  embeddings.npy   (n, dim) float32, unit vectors, row i <-> line i of rows.jsonl
  rows.jsonl       the indexed listings, in listings.jsonl order
  manifest.json    model, dim, count, built_at, stats
  parts/           resume state: one .npz of {ids, vecs} per finished chunk

`fetch(url) -> PIL.Image` raises on failure; `embed(images) -> (n, dim) array`. Both are injected so the tests
need no network and no model. A rerun skips listings already embedded and retries the ones whose photos failed."""
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from pydantic import ValidationError

from backend.images import small_url
from listing import Listing

TRIES = 2  # photos tried per listing: the first, then one fallback


def _read(listings_path, stats):
    rows = []
    for line in Path(listings_path).read_text().splitlines():
        try:
            listing = Listing.model_validate_json(line)
        except ValidationError:
            stats["drop:invalid"] += 1
            continue
        if listing.status != "active":
            stats[f"skip:{listing.status}"] += 1
            continue
        rows.append(listing.model_dump(mode="json"))
    return rows


def _load_parts(parts):
    done = {}
    for p in sorted(parts.glob("*.npz")):
        with np.load(p) as z:
            done.update(zip(z["ids"].tolist(), z["vecs"]))
    return done


def _first_photo(fetch, urls):
    for url in urls[:TRIES]:
        for candidate in dict.fromkeys([small_url(url), url]):
            try:
                return fetch(candidate)
            except Exception:
                pass
    return None


def _write(path, data: bytes):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def build_index(listings_path, out_dir, fetch, embed, *, dim=768, chunk=512, workers=16, model="") -> Counter:
    out_dir, stats = Path(out_dir), Counter()
    parts = out_dir / "parts"
    parts.mkdir(parents=True, exist_ok=True)
    rows = _read(listings_path, stats)
    done = _load_parts(parts)
    stats["resumed"] = sum(r["id"] in done for r in rows)
    todo = [r for r in rows if r["id"] not in done]
    n_part = len(list(parts.glob("*.npz")))
    with ThreadPoolExecutor(workers) as pool:
        for i in range(0, len(todo), chunk):
            batch = todo[i:i + chunk]
            photos = list(pool.map(lambda r: _first_photo(fetch, r["image_urls"]), batch))
            ok = [(r["id"], im) for r, im in zip(batch, photos) if im is not None]
            stats["drop:no_image"] += len(batch) - len(ok)
            if not ok:
                continue
            vecs = np.asarray(embed([im for _, im in ok]), np.float32)
            buf = parts / f"{n_part:05d}.npz.tmp"
            with buf.open("wb") as f:
                np.savez(f, ids=np.array([i for i, _ in ok]), vecs=vecs)
            buf.replace(parts / f"{n_part:05d}.npz")
            n_part += 1
            done.update(zip([i for i, _ in ok], vecs))
    kept = [r for r in rows if r["id"] in done]
    vecs = np.stack([done[r["id"]] for r in kept]).astype(np.float32) if kept else np.zeros((0, dim), np.float32)
    stats["indexed"] = len(kept)
    with (out_dir / "embeddings.npy.tmp").open("wb") as f:
        np.save(f, vecs)
    (out_dir / "embeddings.npy.tmp").replace(out_dir / "embeddings.npy")
    _write(out_dir / "rows.jsonl", "".join(json.dumps(r) + "\n" for r in kept).encode())
    manifest = dict(model=model, dim=dim, count=len(kept), built_at=datetime.now(timezone.utc).isoformat(),
                    stats=dict(stats))
    _write(out_dir / "manifest.json", json.dumps(manifest, indent=2).encode())
    return stats
