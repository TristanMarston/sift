"""Run the Apify actors listed in queries.yaml.
Every call carries max_total_charge_usd as a call option (never inside run_input). Seller identity is scrubbed
before anything is written. Reruns resume: finished queries are skipped and quotas count earlier rows."""
import json
from collections import Counter
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import ROUND_UP, Decimal
from pathlib import Path
from typing import Callable
from urllib.parse import quote_plus

import yaml

OK = "SUCCEEDED"
MAX_FAILS_IN_A_ROW = 3
CAP_MARGIN, CAP_FLOOR = Decimal("1.25"), Decimal("0.05")
RUN_TIMEOUT = timedelta(minutes=30)  # Apify ends a hung run as TIMED-OUT


@dataclass(frozen=True)
class Actor:
    id: str
    item_usd: Decimal          # price per result (SPEC.md §6)
    start_usd: Decimal         # price per run start
    build_input: Callable[[str, int], dict]
    keep: frozenset | None = None   # if set, only these top-level keys of a record are written


# eBay's default output includes ~60 KB of raw page modules per item, and they contain the seller's handle
# and buyers' feedback. Keep only the fields the mapper reads (check the real output when changing this).
EBAY_KEEP = frozenset({
    "title", "description", "images", "image", "price", "priceValue", "totalPrice", "shippingCost", "shippingType",
    "shippingCurrency", "shipping", "currency", "condition", "conditionId", "itemSpecifics", "itemLocation", "brand",
    "categoryPath", "categoryId", "listingStatus", "itemId", "url", "marketplace", "searchQuery", "scrapedAt",
    "quantity", "quantityAvailable", "quantitySold", "availability", "buyingFormat", "bestOfferEnabled", "freeReturns",
    "startDate", "endDate", "model", "mpn", "sponsored", "promoted", "topRatedPlus", "recentPriceDrop", "watchers",
    "sellerAccountType", "sellerFeedbackPercentage", "sellerFeedbackScore", "sellerHasStore", "sellerMemberSince"})


ACTORS = {
    "depop": Actor("jongoose/depop-scraper", Decimal("0.001"), Decimal("0"),
                   lambda q, n: {"query": q, "maxItems": n}),
    "poshmark": Actor("123webdata/poshmark-scraper", Decimal("0.00199"), Decimal("0.02"),
                      lambda q, n: {"categoryUrls": [f"https://poshmark.com/search?query={quote_plus(q)}&type=listings&src=dir"],
                                    "maxResultsPerScrape": n, "usePagination": True, "scrapeProductDetails": True}),
    "grailed": Actor("piotrv1001/grailed-listings-scraper", Decimal("0.012"), Decimal("0.00005"),
                     lambda q, n: {"searchQuery": q, "maxItems": n, "scrapeDetails": True}),
    "ebay": Actor("memo23/ebay-search-scraper-ppe", Decimal("0.005"), Decimal("0.02"),
                  lambda q, n: {"searchQueries": [q], "maxItems": n, "marketplace": "ebay.com", "mode": "active",
                                "condition": "used", "detailedItems": True, "includeDescription": True,
                                "includeSummary": False}, EBAY_KEEP),
}


def charge_cap(marketplace: str, max_items: int) -> Decimal:
    """Expected cost + 25%, rounded up to the cent. Passed to Apify as the hard spend limit for one run."""
    a = ACTORS[marketplace]
    cap = ((max_items * a.item_usd + a.start_usd) * CAP_MARGIN).quantize(Decimal("0.01"), ROUND_UP)
    return max(cap, CAP_FLOOR)


# --- privacy ---------------------------------------------------------------------------------

# Flat keys dropped at any depth (lowercase). Dicts under a seller-ish key (`seller`, `sellerProfile`, `user`) are
# stricter: only the rating/count/location fields in SELLER_SAFE survive, whatever else the actor puts there.
IDENTITY_KEYS = {"sellerusername", "seller_username", "sellerurl", "seller_url", "sellername", "seller_name",
                 "sellerid", "seller_id", "sellerstorename", "username", "userid", "user_id",
                 "avatarurl", "avatar_url", "profileurl", "profile_url"}
SELLER_SAFE = {"ratingaverage", "ratingcount", "totalboughtandsold", "trustedseller", "listingsforsalecount",
               "location", "locationabbreviation", "countrycode", "sellerscore", "buyerscore"}  # compared without "_"


def _seller_block(key: str) -> bool:
    return key.lower().startswith("seller") or key.lower() == "user"


def scrub(value, in_seller=False, keep=None):
    """Copy of an actor record without seller usernames, profile URLs, avatars, account ids or contact data.
    `keep`: if given, only these top-level keys survive."""
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if not isinstance(value, dict):
        return value
    return {k: scrub(v, _seller_block(k) and not in_seller) for k, v in value.items()
            if k.lower() not in IDENTITY_KEYS and (keep is None or k in keep)
            and (not in_seller or k.lower().replace("_", "") in SELLER_SAFE)}


# --- plan ------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Task:
    marketplace: str
    category: str
    query: str
    max_items: int


@dataclass
class Config:
    quotas: dict[str, int]
    queries: dict[str, dict[str, list[tuple[str, int]]]]  # category -> marketplace -> [(query, max_items)]


def load_config(path) -> Config:
    raw = yaml.safe_load(Path(path).read_text())
    default = raw["max_items"]
    queries = {cat: {mp: [(q, default[mp]) if isinstance(q, str) else (q["query"], q["max_items"]) for q in qs]
                     for mp, qs in by_mp.items()} for cat, by_mp in raw["queries"].items()}
    return Config(raw["quotas"], queries)


def build_plan(queries, only=None) -> list[Task]:
    """Breadth first (query 1 of every category and marketplace, then query 2, ...), so stopping early
    still leaves every category and marketplace covered. Put the most valuable queries first."""
    depth = max(len(qs) for by_mp in queries.values() for qs in by_mp.values())
    return [Task(mp, cat, *by_mp[mp][i]) for i in range(depth) for cat, by_mp in queries.items()
            for mp in by_mp if (only is None or mp in only) and i < len(by_mp[mp])]


def smoke_plan(queries) -> list[Task]:
    """The go/no-go test run: the first query of each marketplace, 20 items."""
    first = {}
    for task in build_plan(queries):
        first.setdefault(task.marketplace, task)
    return [replace(task, max_items=20) for task in first.values()]


def estimate(plan, quotas) -> dict[str, dict]:
    """Per marketplace: runs, rows, best-case cost (every query fills its max_items) and the sum of charge caps."""
    out = {}
    for task in plan:
        e = out.setdefault(task.marketplace, dict(runs=0, rows=0, est_usd=Decimal(0), cap_usd=Decimal(0)))
        if quotas and e["rows"] >= quotas[task.marketplace]:
            continue
        a = ACTORS[task.marketplace]
        e["runs"] += 1
        e["rows"] += task.max_items
        e["est_usd"] += task.max_items * a.item_usd + a.start_usd
        e["cap_usd"] += charge_cap(task.marketplace, task.max_items)
    return out


# --- running ---------------------------------------------------------------------------------

def _execute(client, task: Task, cap: Decimal, data_dir: Path) -> dict:
    actor = ACTORS[task.marketplace]
    entry = dict(marketplace=task.marketplace, category=task.category, query=task.query, max_items=task.max_items,
                 run_id=None, status="ERROR", status_message=None, items=0, est_charge_usd=0.0, at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    try:
        run = client.actor(actor.id).call(run_input=actor.build_input(task.query, task.max_items),
                                          max_total_charge_usd=cap, run_timeout=RUN_TIMEOUT)
    except Exception as e:
        return {**entry, "status_message": f"{type(e).__name__}: {e}"}
    if run is None:
        return {**entry, "status": "NO_RUN", "status_message": "call() returned no run"}
    entry.update(run_id=run.id, status=run.status, status_message=run.status_message,
                 est_charge_usd=float(actor.start_usd))
    if run.status != OK:
        return entry
    path = data_dir / "raw" / task.marketplace / f"{run.id}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    try:
        with path.with_suffix(".tmp").open("w") as f:
            for n, item in enumerate(client.dataset(run.default_dataset_id).iterate_items(), 1):
                f.write(json.dumps(scrub(item, keep=actor.keep), ensure_ascii=False) + "\n")
        path.with_suffix(".tmp").replace(path)
    except Exception as e:
        return {**entry, "status": "ERROR", "status_message": f"dataset fetch failed: {type(e).__name__}: {e}"}
    return {**entry, "items": n, "est_charge_usd": float(n * actor.item_usd + actor.start_usd)}


def run_plan(client, plan, quotas, data_dir, max_spend: Decimal | None = None, log=print) -> dict:
    data_dir = Path(data_dir)
    runs_path = data_dir / "runs.jsonl"
    past = [json.loads(line) for line in runs_path.read_text().splitlines()] if runs_path.exists() else []
    done = {(r["marketplace"], r["category"], r["query"]) for r in past if r["status"] == OK}
    rows = Counter()
    spent = sum((Decimal(str(r["est_charge_usd"])) for r in past), Decimal(0))
    for r in past:
        if r["status"] == OK:
            rows[r["marketplace"]] += r["items"]
    streak = Counter()
    for task in plan:
        mp = task.marketplace
        if (mp, task.category, task.query) in done or streak[mp] >= MAX_FAILS_IN_A_ROW:
            continue
        if quotas and mp in quotas and rows[mp] >= quotas[mp]:
            continue
        cap = charge_cap(mp, task.max_items)
        if max_spend is not None and spent + cap > max_spend:
            log(f"stopping: estimated spend ${spent} + next cap ${cap} would pass --max-spend ${max_spend}")
            break
        entry = _execute(client, task, cap, data_dir)
        runs_path.parent.mkdir(parents=True, exist_ok=True)
        with runs_path.open("a") as f:
            f.write(json.dumps(entry) + "\n")
        spent += Decimal(str(entry["est_charge_usd"]))
        ok = entry["status"] == OK
        rows[mp] += entry["items"]
        streak[mp] = 0 if ok else streak[mp] + 1
        log(f"[{mp}] {task.category} {task.query!r}: {entry['status']} {entry['items']} items "
            f"(rows {rows[mp]}/{(quotas or {}).get(mp, '-')}, est. spend ${spent:.2f})"
            + ("" if ok else f" -- {entry['status_message']}"))
        if streak[mp] == MAX_FAILS_IN_A_ROW:
            log(f"[{mp}] giving up after {MAX_FAILS_IN_A_ROW} failures in a row")
    return {"rows": rows, "spent": spent}
