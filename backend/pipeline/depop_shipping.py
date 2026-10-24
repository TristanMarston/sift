"""Step 03c: Depop shipping, fetched per listing. Our Depop actor (jongoose/depop-scraper) returns none, so 43% of
the catalog had "shipping unknown". parsebird/depop-scraper in URL mode returns the US national rate per listing
(~$1.50 per 1,000). Matched by listing id; only id + shipping are kept (the actor also returns seller identity, which
is dropped). Answers are cached in depop_shipping.jsonl, so reruns after a rebuild re-apply them for free; listings
the actor no longer finds (sold or removed) are remembered as unknown; failed chunks are retried next run."""
import os
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import jsonl
from normalize.common import to_cents

ACTOR = "parsebird/depop-scraper"
USD_PER_LISTING = 0.0016  # measured: $0.0075 for 5 listings, rounded up
CHUNK = 500


def needs_shipping(row: dict) -> bool:
    return row["marketplace"] == "depop" and row["cost"]["shipping_cents"] is None


def fetch_apify(urls: list[str]) -> list[dict]:
    from apify_client import ApifyClient
    client = ApifyClient(os.environ["APIFY_TOKEN"])
    run = client.actor(ACTOR).call(run_input={"mode": "url", "urls": urls},
                                   max_total_charge_usd=round(len(urls) * USD_PER_LISTING * 1.5 + 0.05, 2))
    get = (lambda k: run.get(k)) if isinstance(run, dict) else (lambda k: getattr(run, k, None))
    if (get("status") or "") != "SUCCEEDED":
        raise RuntimeError(f"actor run {get('id')} ended {get('status')}")
    dataset = get("default_dataset_id") or get("defaultDatasetId")
    return client.dataset(dataset).list_items().items


def _record(item: dict, as_of: str) -> dict:
    free = bool(item.get("hasFreeShipping"))
    usd = item.get("nationalShippingCost")
    usd = item.get("shippingCost") if usd is None else usd
    return {"id": str(item["id"]), "as_of": as_of, "shipping_cents": 0 if free else to_cents(usd), "free_shipping": free}


def apply(row: dict, rec: dict) -> dict:
    if rec["shipping_cents"] is None:
        return row
    price = row["cost"]["price_cents"]
    cost = {**row["cost"], "shipping_cents": rec["shipping_cents"], "free_shipping": rec["free_shipping"],
            "total_cents": price + rec["shipping_cents"]}
    return {**row, "cost": cost}


def ship_file(path, cache_path, fetch=fetch_apify, chunk: int = CHUNK, limit: int | None = None,
              workers: int = 1) -> Counter:
    path, cache_path = Path(path), Path(cache_path)
    answered = {d["id"]: d for d in (jsonl.load(cache_path) if cache_path.exists() else [])}
    rows, stats, today = jsonl.load(path), Counter(), date.today().isoformat()
    todo = []
    for r in rows:
        if not needs_shipping(r):
            stats["skipped"] += 1
        elif r["external_id"] in answered:
            stats["cached"] += 1
        elif limit is None or len(todo) < limit:
            todo.append(r)
    lock = threading.Lock()

    def one(part):
        try:
            items = {str(it["id"]): it for it in fetch([r["url"] for r in part])}
        except Exception:  # noqa: BLE001  the whole chunk is retried next run
            with lock:
                stats["error"] += len(part)
            return
        for r in part:
            it = items.get(r["external_id"])
            rec = _record(it, today) if it else {"id": r["external_id"], "as_of": today, "shipping_cents": None,
                                                  "free_shipping": None}
            with lock:
                stats["fetched" if it else "not_found"] += 1
                answered[rec["id"]] = rec
            jsonl.append(cache_path, rec)

    with ThreadPoolExecutor(workers) as pool:   # the Apify account runs 5 actors at once: keep one slot free
        list(pool.map(one, [todo[i:i + chunk] for i in range(0, len(todo), chunk)]))
    out = [apply(r, answered[r["external_id"]]) if r["marketplace"] == "depop" and r["external_id"] in answered else r
           for r in rows]
    path.with_suffix(".tmp").write_text("".join(jsonl.dumps(r) + "\n" for r in out), encoding="utf-8", newline="\n")
    path.with_suffix(".tmp").replace(path)
    return stats
