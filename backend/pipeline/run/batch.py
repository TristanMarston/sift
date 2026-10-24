"""Scrape in batches. A batch takes `rows` raw rows, split across marketplaces in the ratio of their quotas, from the
queries nobody has run yet (breadth first, as scrape.build_plan orders them). It runs one lane per marketplace, all at
once, then checks what came back (checks.py) before the next batch starts."""
import json
import threading
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import extract as X
import health as H
import jsonl
import scrape as S
import scrape_report as R
from normalize.mappers import MAPPERS
from normalize.run import normalize_all
from run import checks as C
from run import ledger
from run.ledger import key

MIN_ROWS = 100            # a smaller batch is not worth starting


@dataclass
class Lane:
    marketplace: str
    tasks: list           # the queries still to run, best first
    rows: int             # this batch's target in raw rows
    quota: int            # rows collected so far + the target: where scrape.run_plan stops this lane
    runs: int             # expected actor runs (fewer rows per query than max_items means more runs)
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
            lanes[mp] = Lane(mp, tasks, target, have[mp] + target, e["runs"], e["est_usd"], e["cap_usd"])
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


# --- running ---------------------------------------------------------------------------------------

EXIT_BUSY = 5                 # another runner is using the token: its runs and ours would share the 5 run slots
MARGIN = Decimal("2")         # never plan to spend the account's last dollars
LANE_SLACK = Decimal("1.5")   # a lane may spend up to 1.5x its planned worst case (short queries need extra runs)


def _merge(summaries, spent_before: Decimal) -> R.Summary:
    """One report for all lanes of a batch."""
    s = R.Summary()
    for x in summaries:
        s.markets.update(x.markets)
        s.alerts += x.alerts
        s.started = min(filter(None, [s.started, x.started]), default=None)
        s.finished = max(filter(None, [s.finished, x.finished]), default=None)
        s.budget_stop, s.manual_stop = s.budget_stop or x.budget_stop, s.manual_stop or x.manual_stop
    s.spent_total = spent_before + sum((m.est_spend for m in s.markets.values()), Decimal(0))
    return s


def run_lanes(make_client, lanes: dict[str, Lane], data_dir, classify, log=S.say) -> tuple[R.Summary, dict[str, str]]:
    """One thread per marketplace, each running scrape.run_plan over its lane. The first Ctrl-C creates the STOP file,
    so every lane stops after its current run; a second one quits at once (those runs are then lost). Returns the
    merged summary and the lanes that crashed."""
    data_dir = Path(data_dir)
    past = jsonl.load(data_dir / "runs.jsonl")
    spent = sum((Decimal(str(e["est_charge_usd"])) for e in past), Decimal(0))
    results, crashed = {}, {}

    def lane(l: Lane):
        try:
            results[l.marketplace] = S.run_plan(make_client(), l.tasks, {l.marketplace: l.quota}, data_dir,
                                                max_spend=spent + LANE_SLACK * l.cap_usd, log=log, classify=classify,
                                                write_report=False, past=past)
        except Exception as e:
            crashed[l.marketplace] = f"lane crashed: {type(e).__name__}: {e}"

    threads = [threading.Thread(target=lane, args=(l,), daemon=True) for l in lanes.values()]
    pending, interrupted, made_stop, stop = list(threads), False, False, data_dir / "STOP"
    while True:
        try:
            while pending:
                pending.pop(0).start()
            for t in threads:
                while t.is_alive():
                    t.join(0.2)
            break
        except KeyboardInterrupt:
            if interrupted:
                raise
            interrupted, pending = True, []
            if not stop.exists():
                stop.touch()
                made_stop = True
            log("Ctrl-C: every lane stops after its current run. Press Ctrl-C again to quit now (those runs are lost).")
    if made_stop:
        stop.unlink(missing_ok=True)
    summary = _merge(results.values(), spent)
    summary.interrupted = interrupted
    return summary, crashed


def rebuild(data_dir, mappers=MAPPERS, log=S.say) -> None:
    """Steps 02-03 over everything known: data/normalized.jsonl and data/listings.jsonl."""
    data_dir = Path(data_dir)
    if not (data_dir / "runs.jsonl").exists():
        return
    kept = normalize_all(data_dir, mappers)["kept"]
    X.extract_file(data_dir / "normalized.jsonl", data_dir / "listings.jsonl")
    log(f"catalog: {kept} listings in {data_dir / 'listings.jsonl'}")


def _entries(data_dir, run_ids) -> list[dict]:
    return [e for e in jsonl.load(Path(data_dir) / "runs.jsonl") if e.get("run_id") in run_ids]


def _write(data_dir, batch_id, record, checks, summary=None) -> None:
    d = Path(data_dir) / "batches" / batch_id
    d.mkdir(parents=True, exist_ok=True)
    record.update(checks=C.to_dicts(checks), stopped=C.failed(checks))
    (d / "batch.json").write_text(json.dumps(record, indent=1), encoding="utf-8", newline="\n")
    (d / "CHECKS.md").write_text(C.render(batch_id, checks, record), encoding="utf-8", newline="\n")
    if summary is not None:
        R.write(summary, d)


def _spend(entries, real) -> dict:
    return dict(est_usd=round(sum(e["est_charge_usd"] for e in entries), 4),
                real_usd=round(sum(v for v in real.values() if v is not None), 4))


def recheck(client, data_dir, batch_id, mappers=MAPPERS) -> list:
    """Judge an earlier batch again (after a threshold or a mapper changed) and rewrite its CHECKS.md."""
    path = Path(data_dir) / "batches" / batch_id / "batch.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    entries = _entries(data_dir, set(record["run_ids"]))
    real = C.real_costs(client, entries)
    checks = C.judge(client, data_dir, entries, mappers=mappers, real_usd=real)
    _write(data_dir, batch_id, {**record, **_spend(entries, real)}, checks)
    return checks


def run_batches(client, cfg: S.Config, data_dir, rows=5000, batches=1, only=None, categories=None, max_spend=None,
                who="me", force=False, mappers=MAPPERS, make_client=None, log=S.say, now=S._now) -> int:
    """Up to `batches` batches (None: until quotas, queries or money run out). Each batch: sync with the team ledger,
    check the account, plan, run the lanes, share the new runs, judge them. A marketplace that fails a check sits out
    the rest of this command. Returns the exit code (scrape_report's, or EXIT_BUSY)."""
    data_dir = Path(data_dir)
    make_client = make_client or (lambda: client)
    runs, stopped, spent, n, code = data_dir / "runs.jsonl", {}, Decimal(0), 0, R.EXIT_OK
    filters = dict(only=only, categories=categories)
    ledger.push(client, data_dir)            # runs that an earlier crash left unshared
    while batches is None or n < batches:
        if (data_dir / "STOP").exists():
            log(f"STOP file found at {data_dir / 'STOP'}: no new batch. Delete it to continue.")
            code = R.EXIT_MANUAL
            break
        pulled = ledger.sync(client, data_dir, log)
        if pulled.get("runs"):
            log(f"sync: {pulled['runs']} runs from the team ledger")
        limits = client.user().limits()
        if limits.current.active_actor_job_count and not force:
            log(f"another runner is using this token ({limits.current.active_actor_job_count} active Apify runs): "
                "not starting. Wait for it, or pass --force if those runs are not a scraper.")
            code = EXIT_BUSY
            break
        balance = Decimal(str(limits.limits.max_monthly_usage_usd - limits.current.monthly_usage_usd)) - MARGIN
        budget = balance if max_spend is None else min(balance, Decimal(str(max_spend)) - spent)
        past = jsonl.load(runs)
        size, lanes = fit(cfg, past, rows, budget, skip=set(stopped), **filters)
        if not lanes:
            if plan_batch(cfg, past, rows, skip=set(stopped), **filters):
                log(f"money: the next batch's worst case does not fit ${max(budget, Decimal(0)):.2f} "
                    f"(account balance ${balance + MARGIN:.2f} minus a ${MARGIN} margin, or --max-spend).")
                code = R.EXIT_BUDGET
            else:
                log("nothing left to scrape: every chosen quota is full or every query has run"
                    + (f" (stopped in this command: {', '.join(stopped)})." if stopped else "."))
            break
        n += 1
        batch_id, started = f"{now():%Y%m%d-%H%M%S}-{who}-{n}", now()
        log(f"batch {batch_id}: {size} rows | " + " | ".join(
            f"{mp} {l.rows} rows, ${l.est_usd:.2f}-{l.cap_usd:.2f}" for mp, l in lanes.items()) + f" | balance ${balance + MARGIN:.2f}")
        before = {key(e) for e in past}

        def classify(task, raw):
            return H.classify_row(mappers[task.marketplace], raw, task.category, started)
        summary, crashed = run_lanes(make_client, lanes, data_dir, classify, log)
        entries = [e for e in jsonl.load(runs) if key(e) not in before]
        ledger.push(client, data_dir)
        lane_stops = {mp: m.stopped for mp, m in summary.markets.items() if m.stopped} | crashed
        real = C.real_costs(client, entries)
        checks = C.judge(client, data_dir, entries, lane_stops, mappers, real_usd=real)
        record = dict(id=batch_id, who=who, started=started.isoformat(timespec="seconds"),
                      finished=now().isoformat(timespec="seconds"), rows=size, only=sorted(only or []) or None,
                      categories=sorted(categories or []) or None,
                      lanes={mp: dict(rows=l.rows, est_usd=float(l.est_usd), cap_usd=float(l.cap_usd)) for mp, l in lanes.items()},
                      run_ids=[e["run_id"] for e in entries if e.get("run_id")], **_spend(entries, real))
        _write(data_dir, batch_id, record, checks, summary)
        spent += Decimal(str(record["est_usd"]))
        for mp, reasons in C.failed(checks).items():
            stopped[mp] = reasons
            log(f"ALERT batch {batch_id}: {mp} STOPPED for the rest of this command: {'; '.join(reasons)}")
        log(f"batch {batch_id} done: {len(entries)} runs, est ${record['est_usd']:.2f}, real ${record['real_usd']:.2f}. "
            f"Checks: {data_dir / 'batches' / batch_id / 'CHECKS.md'}")
        if C.stop_all(checks):
            log(f"ALERT batch {batch_id}: seller identity found, EVERYTHING STOPPED. Do not share this data; see CHECKS.md.")
            code = R.EXIT_STOPPED
            break
        if summary.interrupted or summary.manual_stop:
            code = R.EXIT_INTERRUPTED if summary.interrupted else R.EXIT_MANUAL
            break
        if not entries:
            log(f"batch {batch_id} made no runs: stopping instead of trying the same plan again.")
            break
    rebuild(data_dir, mappers, log)
    if code == R.EXIT_OK and stopped:
        code = R.EXIT_STOPPED
    log(f"finished: {n} batch(es), est ${spent:.2f} this command, exit code {code}"
        + (f"; stopped: {', '.join(stopped)}" if stopped else ""))
    return code
