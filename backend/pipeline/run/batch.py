"""Scrape in batches. A batch takes `rows` raw rows, split across marketplaces in the ratio of their quotas, from the
queries nobody has run yet (breadth first, as scrape.build_plan orders them). It runs one lane per marketplace, all at
once, then checks what came back (checks.py) before the next batch starts."""
from dataclasses import dataclass
from decimal import Decimal

import scrape as S

MIN_ROWS = 100            # a smaller batch is not worth starting


@dataclass
class Lane:
    marketplace: str
    tasks: list           # the queries still to run, best first
    rows: int             # this batch's target in raw rows
    quota: int            # rows collected so far + the target: where scrape.run_plan stops this lane
    est_usd: Decimal      # best case: every query fills its max_items
    cap_usd: Decimal      # worst case: every run costs its charge cap


def plan_batch(cfg: S.Config, past: list[dict], rows: int, only=None, categories=None, skip=()) -> dict[str, Lane]:
    """The next batch per marketplace. `past` is every run known (runs.jsonl): its finished queries are skipped and its
    rows count toward the quotas. `only` / `categories` choose what to scrape, `skip` leaves marketplaces out."""
    done, have = S.finished_queries(past), S.quota_rows(past)
    mps = [mp for mp in cfg.quotas if (only is None or mp in only) and mp not in skip]
    total = sum(cfg.quotas[mp] for mp in mps)
    lanes = {}
    for mp in mps:
        target = min(round(rows * cfg.quotas[mp] / total), cfg.quotas[mp] - have[mp])
        tasks = [t for t in S.build_plan(cfg.queries) if t.marketplace == mp and (mp, t.category, t.query) not in done
                 and (categories is None or t.category in categories)]
        if target > 0 and tasks:
            e = S.estimate(tasks, {mp: target})[mp]
            lanes[mp] = Lane(mp, tasks, target, have[mp] + target, e["est_usd"], e["cap_usd"])
    return lanes


def fit(cfg: S.Config, past: list[dict], rows: int, budget: Decimal, **filters) -> tuple[int, dict[str, Lane]]:
    """The biggest batch of at most `rows` whose worst case fits `budget`, or (0, {}) if not even a small one does."""
    while rows >= MIN_ROWS:
        lanes = plan_batch(cfg, past, rows, **filters)
        worst = sum((lane.cap_usd for lane in lanes.values()), Decimal(0))
        if worst <= budget:
            return rows, lanes
        rows = min(rows - 1, int(rows * budget / worst))
    return 0, {}
