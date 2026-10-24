"""Is a batch good enough to keep going? Each marketplace is judged on the batch's own rows, normalized and extracted
in memory with the same code as steps 02-03, and on the real Apify bill. A failed check stops that marketplace for the
rest of the command; seller identity found anywhere stops everything. The thresholds below were set against the review
scrape (REVIEW.md): descriptions were on 92-98% of rows, unusable rows 0%, our cost estimate matched the bills."""
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from pydantic import ValidationError

import extract as X
import jsonl
import report
import scrape as S
from health import BAD, EXPECTED_FILTERS
from normalize.mappers import MAPPERS
from normalize.run import normalize_runs
from run.ledger import key

MAX_UNUSABLE = 0.05              # more rows than this the mapper rejects (no price, photo, url...) = fail
WARN_FILTERED = 0.30             # more rows than this left out on purpose (kids, wrong category...) = warn
MIN_DESCRIBED, WARN_DESCRIBED = 0.70, 0.85
MIN_NEW, WARN_NEW = 0.20, 0.50   # usable rows that became listings we did not have: fewer = paying for repeats
MAX_COST_RATIO, COST_SLACK = 1.25, 0.10
MATERIAL_BASELINE = {"depop": 21, "poshmark": 42, "grailed": 68, "mercari": 47, "ebay": 70}   # % stated, review scrape
FORBIDDEN = re.compile(r"^(seller_?(user)?name|seller_?url|seller_?id|username|user_?id|avatar_?url|profile_?url|"
                       r"paypal_merchant_id|account_preferences|email|profilelogo)$", re.I)   # as tests/test_privacy.py


@dataclass
class Check:
    marketplace: str     # or "all"
    name: str
    level: str           # ok | warn | fail
    detail: str


def forbidden_keys(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if FORBIDDEN.match(k):
                yield f"{path}.{k}"
            yield from forbidden_keys(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from forbidden_keys(v, f"{path}[{i}]")


def _pct(n, total) -> str:
    return f"{n} of {total} ({round(100 * n / total) if total else 0}%)"


def _marketplace(mp, entries, listings, invalid, stats, prior_ids, real_usd, stopped) -> list[Check]:
    out = []

    def add(name, level, detail):
        out.append(Check(mp, name, level, detail))

    good = [e for e in entries if e["status"] == S.OK and e.get("verdict", "ok") not in BAD]
    add("run health", "fail" if mp in stopped else "ok", stopped.get(mp) or f"{len(good)} of {len(entries)} runs usable")
    known = [(e["est_charge_usd"], real_usd[e["run_id"]]) for e in entries if real_usd.get(e.get("run_id")) is not None]
    est, real = sum(k[0] for k in known), sum(k[1] for k in known)
    add("real cost", "fail" if known and real > est * MAX_COST_RATIO + COST_SLACK else "ok",
        f"Apify billed ${real:.2f}, we estimated ${est:.2f}" if known else "not available yet")
    raw = sum(e["items"] for e in good)
    if not raw:
        add("rows", "warn", "no usable rows in this batch")
        return out
    drops = {k.split(":", 2)[2]: n for k, n in stats.items() if k.startswith(f"drop:{mp}:")}
    unusable = sum(n for r, n in drops.items() if r not in EXPECTED_FILTERS)
    filtered = sum(n for r, n in drops.items() if r in EXPECTED_FILTERS)
    add("unusable rows", "fail" if unusable > MAX_UNUSABLE * raw else "ok", _pct(unusable, raw))
    add("filtered rows", "warn" if filtered > WARN_FILTERED * raw else "ok", _pct(filtered, raw))
    add("valid listings", "fail" if invalid[mp] else "ok", f"{invalid[mp]} rows failed the Listing schema")
    n = len(listings)
    described = sum(len(l.description or "") > 40 for l in listings)
    add("descriptions", "fail" if described < MIN_DESCRIBED * n else "warn" if described < WARN_DESCRIBED * n else "ok",
        _pct(described, n) + " with more than 40 characters")
    usable, new = raw - unusable - filtered, len({l.id for l in listings} - prior_ids)
    add("new listings", "fail" if new < MIN_NEW * usable else "warn" if new < WARN_NEW * usable else "ok",
        _pct(new, usable) + " usable rows are new listings")
    stated = sum(report._stated_material(l) for l in listings)
    floor = MATERIAL_BASELINE.get(mp, 0) / 2
    add("stated material", "warn" if n and 100 * stated / n < floor else "ok", _pct(stated, n) + f" (warn below {floor:g}%)")
    empty = sorted({e["category"] for e in good if e["items"]} - {l.category for l in listings})
    add("categories", "warn" if empty else "ok", f"no listings in: {', '.join(empty)}" if empty else "every category queried has listings")
    return out


def assess(entries, listings, invalid, stats, prior_ids, real_usd, stopped, leaks) -> list[Check]:
    """The checks of one batch. `stopped`: marketplace -> why the run judge stopped its lane. `leaks`: where seller
    identity keys were found."""
    mps = sorted({e["marketplace"] for e in entries} | set(stopped))
    out = [c for mp in mps for c in _marketplace(mp, [e for e in entries if e["marketplace"] == mp],
                                                   [l for l in listings if l.marketplace == mp], invalid, stats,
                                                   prior_ids, real_usd, stopped)]
    out.append(Check("all", "privacy", "fail" if leaks else "ok",
                     f"seller identity found: {'; '.join(leaks[:3])}" if leaks else "no seller identity in raw rows or listings"))
    return out


def failed(checks) -> dict[str, list[str]]:
    """Marketplace -> the checks it failed."""
    out = {}
    for c in checks:
        if c.level == "fail" and c.marketplace != "all":
            out.setdefault(c.marketplace, []).append(f"{c.name}: {c.detail}")
    return out


def stop_all(checks) -> bool:
    return any(c.level == "fail" and c.marketplace == "all" for c in checks)


def _real_cost(client, run_id):
    try:
        return client.run(run_id).get().usage_total_usd
    except Exception:
        return None


def judge(client, data_dir, entries, stopped=None, mappers=MAPPERS) -> list[Check]:
    """Gather everything assess() needs for these runs from data_dir and Apify. "New" means not in any run that comes
    earlier in runs.jsonl."""
    data_dir = Path(data_dir)
    batch = {key(e) for e in entries}
    known = jsonl.load(data_dir / "runs.jsonl")
    first = next((i for i, e in enumerate(known) if key(e) in batch), len(known))
    prior, _ = normalize_runs(data_dir, known[:first], mappers)
    rows, stats = normalize_runs(data_dir, entries, mappers)
    listings, invalid, leaks = [], Counter(), []
    for n in rows.values():
        try:
            listings.append(X.extract(n))
        except ValidationError:
            invalid[n.marketplace] += 1
    for e in entries:
        path = data_dir / "raw" / e["marketplace"] / f"{e.get('run_id')}.jsonl"
        for i, raw in enumerate(jsonl.load(path), 1):
            leaks += [f"{path.relative_to(data_dir).as_posix()}:{i} {k}" for k in forbidden_keys(raw)]
    for l in listings:
        leaks += [f"listing {l.id} {k}" for k in forbidden_keys(l.model_dump(mode="json"))]
    real = {e["run_id"]: _real_cost(client, e["run_id"]) for e in entries if e.get("run_id")}
    return assess(entries, listings, invalid, stats, set(prior), real, stopped or {}, leaks)


def render(batch_id: str, checks, spend: dict) -> str:
    stopped = failed(checks)
    result = ("STOPPED EVERYTHING: seller identity found" if stop_all(checks)
              else f"STOPPED: {', '.join(stopped)}" if stopped else "OK")
    lines = [f"# Batch {batch_id}", "", f"**Result: {result}.** Estimated spend ${spend['est_usd']:.2f}, "
             f"real (Apify) ${spend['real_usd']:.2f}.", "", "| marketplace | check | result | detail |", "| --- | --- | --- | --- |"]
    lines += [f"| {c.marketplace} | {c.name} | {c.level.upper() if c.level != 'ok' else 'ok'} | {c.detail} |" for c in checks]
    return "\n".join(lines) + "\n"


def to_dicts(checks) -> list[dict]:
    return [asdict(c) for c in checks]
