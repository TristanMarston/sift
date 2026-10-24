"""The end-of-run report of 01_scrape.py, and the process exit code (so a wrapper or cron job can react)."""
import json
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import health as H

CONSOLE = "https://console.apify.com/actors/runs/"
EXIT_OK, EXIT_STOPPED, EXIT_BUDGET, EXIT_MANUAL, EXIT_INTERRUPTED = 0, 2, 3, 4, 130


@dataclass
class MarketStats:
    queries_ok: int = 0
    queries_short: int = 0            # fewer rows than asked for: a warning, not a problem
    queries_bad: int = 0
    queries_done_before: int = 0      # skipped because an earlier invocation finished them
    rows: H.RowCounts = field(default_factory=H.RowCounts)  # rows saved by runs that were not bad
    quarantined: int = 0              # rows saved by bad runs: kept on disk, never normalized
    est_spend: Decimal = Decimal(0)
    wasted: Decimal = Decimal(0)      # estimated spend of the bad runs
    rows_toward_quota: int = 0        # earlier invocations included
    quota: int | None = None
    stopped: str | None = None        # why this marketplace was stopped
    stopped_run_id: str | None = None


@dataclass
class Summary:
    markets: dict[str, MarketStats] = field(default_factory=dict)
    alerts: list[dict] = field(default_factory=list)
    started: datetime | None = None
    finished: datetime | None = None
    max_spend: Decimal | None = None
    spent_total: Decimal = Decimal(0)  # estimated, earlier invocations in the same data folder included
    budget_stop: bool = False
    manual_stop: bool = False          # a STOP file was found
    interrupted: bool = False          # Ctrl-C
    halted: bool = False               # --stop-all-on-block fired


def exit_code(s: Summary) -> int:
    """130 interrupted, 2 a marketplace was stopped (blocked, junk, or failing), 3 budget limit, 4 STOP file, else 0."""
    if s.interrupted:
        return EXIT_INTERRUPTED
    if s.halted or any(m.stopped for m in s.markets.values()):
        return EXIT_STOPPED
    return EXIT_BUDGET if s.budget_stop else EXIT_MANUAL if s.manual_stop else EXIT_OK


def _result(s: Summary) -> str:
    if s.interrupted:
        return "INTERRUPTED (Ctrl-C)"
    if s.halted:
        return "HALTED: a marketplace was blocked and --stop-all-on-block is on"
    if any(m.stopped for m in s.markets.values()):
        return "STOPPED: at least one marketplace was blocked, returned junk, or kept failing"
    if s.budget_stop:
        return "STOPPED: the --max-spend limit"
    return "STOPPED: a STOP file was found" if s.manual_stop else "FINISHED"


def to_dict(s: Summary) -> dict:
    return {
        "result": _result(s), "exit_code": exit_code(s), "started": s.started and s.started.isoformat(timespec="seconds"),
        "finished": s.finished and s.finished.isoformat(timespec="seconds"), "estimated_spend_total_usd": float(s.spent_total),
        "markets": {mp: dict(
            queries_ok=m.queries_ok, queries_short=m.queries_short, queries_bad=m.queries_bad,
            queries_done_before=m.queries_done_before, rows_saved=m.rows.saved + m.quarantined, rows_good=m.rows.good,
            rows_duplicate=m.rows.duplicates, rows_filtered=dict(m.rows.filtered), rows_bad=dict(m.rows.bad),
            rows_quarantined=m.quarantined, est_spend_usd=float(m.est_spend), wasted_usd=float(m.wasted),
            rows_toward_quota=m.rows_toward_quota, quota=m.quota, stopped=m.stopped) for mp, m in s.markets.items()},
        "alerts": s.alerts}


def render(s: Summary) -> str:
    code = exit_code(s)
    took = f", ran {round((s.finished - s.started).total_seconds() / 60, 1)} min" if s.started and s.finished else ""
    lines = ["# Scrape run report", "",
             f"**Result: {_result(s)}** (exit code {code}){took}.",
             f"Estimated spend in this data folder: ${s.spent_total:.2f}"
             + (f" of the ${s.max_spend} limit" if s.max_spend is not None else "")
             + f"; ${sum(m.wasted for m in s.markets.values()):.2f} of it went on bad runs.", "",
             "| marketplace | queries ok | short | bad | done earlier | rows saved | good | duplicate | filtered | unusable | quarantined | toward quota | est. spend | wasted | status |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for mp, m in s.markets.items():
        quota = f"{m.rows_toward_quota}/{m.quota}" if m.quota else str(m.rows_toward_quota)
        lines.append(f"| {mp} | {m.queries_ok} | {m.queries_short} | {m.queries_bad} | {m.queries_done_before} | "
                     f"{m.rows.saved + m.quarantined} | {m.rows.good} | {m.rows.duplicates} | {sum(m.rows.filtered.values())} | "
                     f"{sum(m.rows.bad.values())} | {m.quarantined} | {quota} | ${m.est_spend:.2f} | ${m.wasted:.2f} | "
                     f"{'**STOPPED**' if m.stopped else 'ok'} |")
    saved = sum(m.rows.saved + m.quarantined for m in s.markets.values())
    good = sum(m.rows.good for m in s.markets.values())
    lines += ["", "## Rows", "",
              f"- good rows saved: {good} of {saved} rows saved ({round(100 * good / saved) if saved else 0}%)",
              "- good = usable and new; duplicate = usable but already seen; filtered = left out on purpose (kids, wrong category, not USD);",
              "  unusable = missing price, photo, url or title; quarantined = everything saved by a bad run (never normalized)"]
    for mp, m in s.markets.items():
        notes = []
        if m.rows.filtered:
            notes.append("filtered " + ", ".join(f"{r} {c}" for r, c in m.rows.filtered.most_common(4)))
        if m.rows.bad:
            notes.append("unusable " + ", ".join(f"{r} {c}" for r, c in m.rows.bad.most_common(4)))
        if notes:
            lines.append(f"- {mp}: " + " · ".join(notes))
    for mp, m in s.markets.items():   # a partial block looks like this: nothing fails, every query is a trickle
        runs = m.queries_ok + m.queries_short
        if m.queries_short >= 3 and m.queries_short * 2 >= runs:
            lines.append(f"- watch: {mp} returned far fewer rows than asked for in {m.queries_short} of {runs} queries "
                         "(narrow queries do this, and so does a site that cuts us off after a few pages)")
    if s.alerts:
        lines += ["", "## Alerts", ""]
        lines += [f"- {a['at']} **{a['marketplace']}** {a['verdict'].upper()} on '{a['query']}': {'; '.join(a['reasons'])} → {a['action']}"
                  for a in s.alerts]
    stopped = {mp: m for mp, m in s.markets.items() if m.stopped}
    if stopped:
        lines += ["", "## What to do next", ""]
        for mp, m in stopped.items():
            run = f" Look at the run: {CONSOLE}{m.stopped_run_id}." if m.stopped_run_id else ""
            lines.append(f"- **{mp}** was STOPPED: {m.stopped}.{run} Fix the cause or wait, then re-run the same command: "
                         "finished queries are skipped, bad runs are retried.")
    return "\n".join(lines) + "\n"


def write(s: Summary, data_dir) -> str:
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    text = render(s)
    (data_dir / "run_report.md").write_text(text, encoding="utf-8")
    (data_dir / "run_report.json").write_text(json.dumps(to_dict(s), indent=1), encoding="utf-8")
    return text
