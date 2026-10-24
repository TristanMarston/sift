"""Run the Apify actors listed in queries.yaml.
Every call carries max_total_charge_usd as a call option (never inside run_input). Seller identity is scrubbed
before anything is written. Reruns resume: finished queries are skipped and quotas count earlier rows."""
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import ROUND_UP, Decimal
from pathlib import Path
from typing import Callable
from urllib.parse import quote_plus

import yaml

import health as H
import jsonl
import scrape_report as R

OK = "SUCCEEDED"
MAX_SOFT_BAD_IN_A_ROW = 2   # empty runs and failures: the second one in a row stops the marketplace
# Title words that mean children's clothing. The Mercari actor matches word *prefixes*, so these are whole words:
# "boy" would also drop "boyfriend jeans" and "baby" would drop "baby alpaca". normalize/mercari.py drops what slips through.
KIDS_WORDS = ["kids", "kid's", "boys", "boy's", "girls", "girl's", "toddler", "toddlers", "infant", "youth"]
CAP_MARGIN, CAP_FLOOR = Decimal("1.25"), Decimal("0.05")
RUN_TIMEOUT = timedelta(minutes=30)  # Apify ends a hung run as TIMED-OUT


@dataclass(frozen=True)
class Actor:
    id: str
    item_usd: Decimal          # price per result (SPEC.md §6)
    start_usd: Decimal         # price per run start
    build_input: Callable[[str, int], dict]
    keep: frozenset | None = None   # if set, only these top-level keys of a record are written
    drop: frozenset = frozenset()   # top-level keys never written (on top of the identity keys scrub() removes)
    is_item: Callable[[dict], bool] | None = None   # if set, other rows (free summary rows) are not written or counted
    expects_description: bool = True   # rows with no real description mean the actor returned card data only


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
    # Depop records carry the seller's city (`location`) and a `slug` that starts with their handle.
    "depop": Actor("jongoose/depop-scraper", Decimal("0.001"), Decimal("0"),
                   lambda q, n: {"query": q, "maxItems": n}, drop=frozenset({"location", "slug"})),
    "poshmark": Actor("123webdata/poshmark-scraper", Decimal("0.00199"), Decimal("0.02"),
                      lambda q, n: {"categoryUrls": [f"https://poshmark.com/search?query={quote_plus(q)}&type=listings&src=dir"],
                                    "maxResultsPerScrape": n, "usePagination": True, "scrapeProductDetails": True}),
    "grailed": Actor("piotrv1001/grailed-listings-scraper", Decimal("0.012"), Decimal("0.00005"),
                     lambda q, n: {"searchQuery": q, "maxItems": n, "scrapeDetails": True}),
    # Details mode returns description, all photos, size, shipping and seller counts. The first Mercari actor we
    # tried (getascraper) returned card data only. The dataset also holds free search/status/summary rows.
    "mercari": Actor("automation_craft/mercari-us-scraper", Decimal("0.00273"), Decimal("0.006"),
                     lambda q, n: {"keywords": [q], "statuses": ["on_sale"], "includeDetails": True, "maxItems": n,
                                   "excludeKeywords": KIDS_WORDS},
                     is_item=lambda row: row.get("type") == "listing"),
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


def build_plan(queries) -> list[Task]:
    """Breadth first (query 1 of every category and marketplace, then query 2, ...), so stopping early
    still leaves every category and marketplace covered. Put the most valuable queries first."""
    depth = max(len(qs) for by_mp in queries.values() for qs in by_mp.values())
    return [Task(mp, cat, *by_mp[mp][i]) for i in range(depth) for cat, by_mp in queries.items()
            for mp in by_mp if i < len(by_mp[mp])]


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

@dataclass
class Outcome:
    entry: dict
    counts: H.RowCounts
    log: str        # the actor's run log (diagnostic evidence; "" if it could not be fetched)
    ids: set        # ids of the good rows this run saved


def _fetch_log(client, run) -> str:
    try:
        return client.run(run.id).log().get() or ""
    except Exception:
        return ""


def _execute(client, task: Task, cap: Decimal, data_dir: Path, classify, seen: set) -> Outcome:
    """One actor run: call it, save the scrubbed rows, and classify every row (good / duplicate / filtered / bad)."""
    actor = ACTORS[task.marketplace]
    entry = dict(marketplace=task.marketplace, category=task.category, query=task.query, max_items=task.max_items,
                 run_id=None, status="ERROR", status_message=None, items=0, est_charge_usd=0.0,
                 at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    counts, ids = H.RowCounts(), set()
    try:
        run = client.actor(actor.id).call(run_input=actor.build_input(task.query, task.max_items),
                                          max_total_charge_usd=cap, run_timeout=RUN_TIMEOUT)
    except Exception as e:
        return Outcome({**entry, "status_message": f"{type(e).__name__}: {e}"}, counts, "", ids)
    if run is None:
        return Outcome({**entry, "status": "NO_RUN", "status_message": "call() returned no run"}, counts, "", ids)
    entry.update(run_id=run.id, status=run.status, status_message=run.status_message, est_charge_usd=float(actor.start_usd))
    log = _fetch_log(client, run)
    if run.status != OK:   # its rows were billed but are not saved: book the worst case so --max-spend stays safe
        return Outcome({**entry, "est_charge_usd": float(cap)}, counts, log, ids)
    path = data_dir / "raw" / task.marketplace / f"{run.id}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    try:
        with path.with_suffix(".tmp").open("w") as f:
            for item in client.dataset(run.default_dataset_id).iterate_items():
                if actor.is_item is not None and not actor.is_item(item):
                    continue
                clean = scrub({k: v for k, v in item.items() if k not in actor.drop}, keep=actor.keep)
                f.write(jsonl.dumps(clean) + "\n")
                n += 1
                if classify is None:
                    counts.add("good", described=True)
                    continue
                kind, reason, norm = classify(task, clean)
                if kind == "good":
                    kind = "duplicate" if norm.id in seen or norm.id in ids else "good"
                    ids.add(norm.id)
                counts.add(kind, reason, described=bool(norm and len(norm.description or "") > 40))
        path.with_suffix(".tmp").replace(path)
    except Exception as e:
        entry.update(status="ERROR", status_message=f"dataset fetch failed: {type(e).__name__}: {e}")
        return Outcome(entry, counts, log, ids)
    entry.update(items=n, est_charge_usd=float(n * actor.item_usd + actor.start_usd))
    return Outcome(entry, counts, log, ids)


def finished_queries(past: list[dict]) -> set:
    """Queries a rerun must not repeat: runs judged ok or short (old log lines without a verdict count as ok), and
    queries that came back empty twice (they are really empty). Blocked, degraded and failed runs are retried."""
    done, empties = set(), Counter()
    for r in past:
        key = (r["marketplace"], r["category"], r["query"])
        verdict = r.get("verdict", "ok")
        if r["status"] == OK and verdict in ("ok", "short"):
            done.add(key)
        elif r["status"] == OK and verdict == "empty":
            empties[key] += 1
    return done | {key for key, n in empties.items() if n >= 2}


def say(message: str) -> None:
    """Progress line. Flushed, so a log file fills as the run goes (stdout is buffered when redirected)."""
    print(message, flush=True)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def run_plan(client, plan, quotas, data_dir, max_spend: Decimal | None = None, log=say, classify=None,
             stop_all_on_block: bool = False, now=_now) -> R.Summary:
    """Run the plan. After every run the outcome is judged (health.py): a bad run raises an ALERT line at once (and a
    line in alerts.jsonl); a hard block or junk data stops that marketplace immediately, a second empty or failed run
    in a row stops it too. `classify(task, raw) -> (kind, reason, normalized)` judges single rows; without it every row
    counts as good. Create <data_dir>/STOP to halt before the next run. Writes run_report.md/.json and returns the Summary."""
    data_dir = Path(data_dir)
    runs_path, alerts_path, stop_path = data_dir / "runs.jsonl", data_dir / "alerts.jsonl", data_dir / "STOP"
    past = jsonl.load(runs_path)
    done = finished_queries(past)
    summary = R.Summary(started=now(), max_spend=max_spend)
    spent = sum((Decimal(str(r["est_charge_usd"])) for r in past), Decimal(0))
    rows, streak, seen = Counter(), Counter(), defaultdict(set)
    for r in past:
        if r["status"] == OK and r.get("verdict", "ok") not in H.BAD:
            rows[r["marketplace"]] += r["items"]

    def alert(mp, task, entry, verdict, action, text):
        url = f"{R.CONSOLE}{entry['run_id']}" if entry["run_id"] else "no run id"
        log(f"ALERT [{mp}] {verdict.kind.upper()} on {task.query!r} (run {url}): {'; '.join(verdict.reasons)}. {text}")
        record = dict(at=now().isoformat(timespec="seconds"), marketplace=mp, category=task.category, query=task.query,
                      verdict=verdict.kind, reasons=verdict.reasons, notes=verdict.notes, run_id=entry["run_id"], action=action)
        summary.alerts.append(record)
        alerts_path.parent.mkdir(parents=True, exist_ok=True)
        with alerts_path.open("a") as f:
            f.write(jsonl.dumps(record) + "\n")

    try:
        for task in plan:
            mp = task.marketplace
            st = summary.markets.setdefault(mp, R.MarketStats(quota=(quotas or {}).get(mp)))
            st.rows_toward_quota = rows[mp]
            if (mp, task.category, task.query) in done:
                st.queries_done_before += 1
                continue
            if st.stopped or summary.halted or (quotas and mp in quotas and rows[mp] >= quotas[mp]):
                continue
            if stop_path.exists():
                summary.manual_stop = True
                log(f"STOP file found at {stop_path}: stopping before the next run.")
                break
            cap = charge_cap(mp, task.max_items)
            if max_spend is not None and spent + cap > max_spend:
                summary.budget_stop = True
                log(f"stopping: estimated spend ${spent} + next cap ${cap} would pass --max-spend ${max_spend}")
                break
            out = _execute(client, task, cap, data_dir, classify, seen[mp])
            entry, c = out.entry, out.counts
            verdict = H.assess(entry["status"], entry["status_message"], task.max_items, c, out.log,
                               expects_description=ACTORS[mp].expects_description and classify is not None)
            entry.update(verdict=verdict.kind, reasons=verdict.reasons, notes=verdict.notes, rows_good=c.good,
                         rows_duplicate=c.duplicates, rows_filtered=sum(c.filtered.values()), rows_bad=sum(c.bad.values()))
            runs_path.parent.mkdir(parents=True, exist_ok=True)
            with runs_path.open("a") as f:
                f.write(jsonl.dumps(entry) + "\n")
            est = Decimal(str(entry["est_charge_usd"]))
            spent += est
            st.est_spend += est
            if verdict.bad:
                st.queries_bad += 1
                st.wasted += est
                st.quarantined += c.saved
                streak[mp] += 1
                stop = verdict.hard or streak[mp] >= MAX_SOFT_BAD_IN_A_ROW
                if stop:
                    st.stopped, st.stopped_run_id = f"{verdict.kind.upper()} at {task.query!r}: {'; '.join(verdict.reasons)}", entry["run_id"]
                    summary.halted = stop_all_on_block and verdict.hard
                    alert(mp, task, entry, verdict, "stopped",
                          ("ALL marketplaces halted (--stop-all-on-block). " if summary.halted else "Marketplace STOPPED, the others continue. ")
                          + "Re-run the same command to resume once it is fixed.")
                else:
                    alert(mp, task, entry, verdict, "warned", f"Strike {streak[mp]} of {MAX_SOFT_BAD_IN_A_ROW}: one more bad run in a row stops this marketplace.")
            else:
                streak[mp] = 0
                rows[mp] += entry["items"]
                st.rows_toward_quota = rows[mp]
                st.queries_short += verdict.kind == "short"
                st.queries_ok += verdict.kind == "ok"
                st.rows.good, st.rows.duplicates, st.rows.described = st.rows.good + c.good, st.rows.duplicates + c.duplicates, st.rows.described + c.described
                st.rows.filtered.update(c.filtered)
                st.rows.bad.update(c.bad)
                seen[mp] |= out.ids
            log(f"{'!! ' if verdict.bad else ''}[{mp}] {task.category} {task.query!r}: {verdict.kind.upper()} {c.saved} rows "
                f"(good {c.good}, duplicate {c.duplicates}, filtered {sum(c.filtered.values())}, unusable {sum(c.bad.values())}) | "
                f"toward quota {rows[mp]}/{(quotas or {}).get(mp, '-')} | est. spend ${spent:.2f}"
                + (f" | note: {'; '.join(verdict.notes)}" if verdict.notes else ""))
    except KeyboardInterrupt:
        summary.interrupted = True
        log("interrupted (Ctrl-C): writing the report for what was collected so far.")
    summary.finished, summary.spent_total = now(), spent
    R.write(summary, data_dir)
    return summary
