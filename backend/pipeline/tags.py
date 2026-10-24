"""Step 03b: read care tags in listing photos (Claude Haiku) for listings that state no fabric.

listings.jsonl is rewritten in place: a readable tag becomes the listing's materials, as `tag_image` evidence with
status `verified` (we read it ourselves, not the seller). Every answer is cached in tags.jsonl, so a rerun, or a rerun
after the batch runner rebuilds listings.jsonl, never pays twice. Failed calls are logged but retried next time."""
import base64
import io
import json
import threading
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from functools import cache
from pathlib import Path

from PIL import Image

import jsonl
from extract import parse_fibers, to_materials

HAIKU = "claude-haiku-5-5"
SIDE = 768        # long edge sent to the model: a care tag stays legible
MAX_PHOTOS = 6
USD_PER_LISTING = 0.0005  # ~6 photos x ~790 image tokens + prompt at Haiku input prices, rounded up
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
PROMPT = """These are the photos of one secondhand clothing listing. If any photo shows the garment's care or content \
label, transcribe exactly the fiber composition printed on it (for example "80% wool, 20% nylon"; keep shell and lining \
parts as written). If no label is readable, set tag_found to false and composition to null. Never guess the fabric from \
how the garment looks."""
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["tag_found", "composition"],
          "properties": {"tag_found": {"type": "boolean"}, "composition": {"type": ["string", "null"]}}}


def needs_tag(row: dict) -> bool:
    """No fabric stated by the seller (none at all, or only a product-line guess)."""
    ev = next((e for e in row.get("evidence", []) if e["field"] == "materials.fibers"), None)
    return not row["materials"]["fibers"] or (ev is not None and ev["status"] in {"inferred", "unknown"})


def apply_tag(row: dict, text: str, as_of: str) -> dict:
    fibers, _ = parse_fibers(text, field=True)
    if not fibers:
        return row
    materials = to_materials(fibers, row["materials"]["certifications"]).model_dump(mode="json")
    evidence = [e for e in row.get("evidence", []) if e["field"] != "materials.fibers"]
    evidence.append(dict(field="materials.fibers", status="verified", source="tag_image", snippet=text, as_of=as_of))
    return {**row, "materials": materials, "evidence": evidence}


def prepare(images: list[Image.Image]) -> list[bytes]:
    out = []
    for im in images[:MAX_PHOTOS]:
        im = im.convert("RGB")
        im.thumbnail((SIDE, SIDE))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85)
        out.append(buf.getvalue())
    return out


def fetch(url: str) -> Image.Image:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        return Image.open(io.BytesIO(r.read()))


@cache
def _client():
    import anthropic
    return anthropic.Anthropic(timeout=60, max_retries=2)


def ask_haiku(images: list[bytes]) -> dict:
    content = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                           "data": base64.standard_b64encode(b).decode()}} for b in images]
    msg = _client().messages.create(
        model=HAIKU, max_tokens=512, output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": [*content, {"type": "text", "text": PROMPT}]}])
    if msg.stop_reason == "refusal":
        return {"tag_found": False, "composition": None}
    return json.loads(next(b.text for b in msg.content if b.type == "text"))


def tag_file(path, cache_path, ask=ask_haiku, fetch=fetch, limit: int | None = None, workers: int = 8) -> Counter:
    path, cache_path = Path(path), Path(cache_path)
    answered = {d["id"]: d for d in (jsonl.load(cache_path) if cache_path.exists() else []) if not d.get("error")}
    rows, stats = jsonl.load(path), Counter()
    todo = []
    for r in rows:
        if not needs_tag(r):
            stats["skipped:stated"] += 1
        elif r["id"] in answered:
            stats["cached"] += 1
        elif limit is not None and len(todo) >= limit:
            stats["skipped:limit"] += 1
        else:
            todo.append(r)

    lock = threading.Lock()

    def read(r):
        rec = {"id": r["id"], "as_of": date.today().isoformat(), "tag_found": False, "composition": None}
        try:
            rec.update(ask(prepare([fetch(u) for u in r["image_urls"][:MAX_PHOTOS]])))
            with lock:
                stats["read" if rec["composition"] else "no_tag"] += 1
                answered[r["id"]] = rec
        except Exception as e:  # noqa: BLE001  a failed listing stays as it was and is retried next run
            rec["error"] = f"{type(e).__name__}: {e}"
            with lock:
                stats["error"] += 1
        jsonl.append(cache_path, rec)

    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(read, todo))
    out = [apply_tag(r, a["composition"], a["as_of"]) if (a := answered.get(r["id"])) and a["composition"] else r
           for r in rows]
    path.with_suffix(".tmp").write_text("".join(jsonl.dumps(r) + "\n" for r in out), encoding="utf-8", newline="\n")
    path.with_suffix(".tmp").replace(path)
    return stats
