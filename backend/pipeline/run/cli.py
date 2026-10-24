"""Scrape in batches, check every batch, share the runs with the team. How to use it: README.md in this folder.

  uv run python pipeline/run/cli.py batch --rows 5000 --dry-run     # what the next batch would scrape and cost
  uv run python pipeline/run/cli.py batch --rows 5000               # one batch, then its checks
  uv run python pipeline/run/cli.py batch --rows 5000 --batches all > batch.log 2>&1 &   # until money or queries run out
  uv run python pipeline/run/cli.py sync                            # get the team's runs from Apify
  uv run python pipeline/run/cli.py export sift-data.zip            # one file with everything scraped so far
  uv run python pipeline/run/cli.py import sift-data.zip            # add a teammate's file
  uv run python pipeline/run/cli.py check <batch id>                # judge an earlier batch again

Exit code of batch: 0 done, 2 a marketplace was stopped, 3 money limit, 4 STOP file, 5 the token is busy, 130 Ctrl-C.
"""
import argparse
import os
import re
import socket
import sys
from decimal import Decimal
from pathlib import Path
from typing import get_args

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))     # pipeline/, where scrape.py and the other modules live

from apify_client import ApifyClient    # noqa: E402
from dotenv import load_dotenv          # noqa: E402

import jsonl                            # noqa: E402
import listing                          # noqa: E402
import scrape as S                      # noqa: E402
from run import batch as B              # noqa: E402
from run import checks as C             # noqa: E402
from run import ledger as L             # noqa: E402

ENV = HERE.parents[2] / ".env"          # the repo root


def token(required=True) -> str | None:
    load_dotenv(ENV)
    if required and not os.environ.get("APIFY_TOKEN"):
        sys.exit(f"APIFY_TOKEN is not set (put it in {ENV})")
    return os.environ.get("APIFY_TOKEN")


def names(value: str | None, allowed, what: str) -> set | None:
    if not value:
        return None
    chosen = set(value.split(","))
    if chosen - set(allowed):
        sys.exit(f"unknown {what}: {', '.join(sorted(chosen - set(allowed)))} (choose from {', '.join(allowed)})")
    return chosen


def dry_run(cfg, data_dir, rows, filters) -> None:
    past = jsonl.load(data_dir / "runs.jsonl")
    lanes = B.plan_batch(cfg, past, rows, **filters)
    print(f"next batch of {rows} rows, from the {len(past)} runs known in {data_dir} (run `sync` first to include the team's)")
    print(f"{'marketplace':12} {'rows':>6} {'runs':>5} {'best $':>8} {'worst $':>8} {'queries left':>13}")
    for mp, l in lanes.items():
        print(f"{mp:12} {l.rows:>6} {l.runs:>5} {l.est_usd:>8.2f} {l.cap_usd:>8.2f} {len(l.tasks):>13}")
    print(f"{'total':12} {sum(l.rows for l in lanes.values()):>6} {sum(l.runs for l in lanes.values()):>5} "
          f"{sum(l.est_usd for l in lanes.values()):>8.2f} {sum(l.cap_usd for l in lanes.values()):>8.2f}")
    if not lanes:
        print("nothing left to scrape: every chosen query has run.")
    if token(required=False):
        lim = ApifyClient(token()).user().limits()
        print(f"account: ${lim.limits.max_monthly_usage_usd - lim.current.monthly_usage_usd:.2f} left this month, "
              f"{lim.current.active_actor_job_count} runs active now")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--data-dir", type=Path, default=HERE.parent / "data", help="default: pipeline/data")
    sub = ap.add_subparsers(dest="command", required=True)
    b = sub.add_parser("batch", parents=[common], help="scrape batches and check each one")
    b.add_argument("--rows", type=int, default=5000, help="raw rows per batch, split in the quota ratio (default 5000)")
    b.add_argument("--batches", type=lambda v: None if v == "all" else int(v), default=1, help="how many, or 'all' (default 1)")
    b.add_argument("--only", help="comma-separated marketplaces, e.g. depop,ebay")
    b.add_argument("--categories", help="comma-separated categories, e.g. tshirts,sneakers")
    b.add_argument("--max-spend", type=Decimal, help="estimated USD this command may spend in total")
    b.add_argument("--who", default=re.sub(r"[^\w-]", "", socket.gethostname().split(".")[0]) or "me",
                   help="your name in batch ids (default: this computer's name)")
    b.add_argument("--force", action="store_true", help="start even if the account has active Apify runs")
    b.add_argument("--dry-run", action="store_true", help="show the next batch and its cost, scrape nothing")
    sub.add_parser("sync", parents=[common], help="pull the team's runs from the Apify ledger and rebuild the catalog")
    e = sub.add_parser("export", parents=[common], help="write everything scraped so far to one zip")
    e.add_argument("zip", type=Path)
    i = sub.add_parser("import", parents=[common], help="add a snapshot (zip or data folder) and rebuild the catalog")
    i.add_argument("source", type=Path)
    c = sub.add_parser("check", parents=[common], help="judge an earlier batch again")
    c.add_argument("batch_id")
    args = ap.parse_args()
    data_dir = args.data_dir

    if args.command == "batch":
        cfg = S.load_config(HERE.parent / "queries.yaml")
        filters = dict(only=names(args.only, list(S.ACTORS), "marketplace"),
                       categories=names(args.categories, get_args(listing.Category), "category"))
        if args.dry_run:
            return dry_run(cfg, data_dir, args.rows, filters)
        key = token()
        sys.exit(B.run_batches(ApifyClient(key), cfg, data_dir, rows=args.rows, batches=args.batches,
                               max_spend=args.max_spend, who=args.who, force=args.force,
                               make_client=lambda: ApifyClient(key), **filters))
    if args.command == "sync":
        print(dict(L.sync(ApifyClient(token()), data_dir)) or "already up to date")
        B.rebuild(data_dir)
    elif args.command == "export":
        n = L.export(data_dir, args.zip)
        print(f"{args.zip}: {n} files, {args.zip.stat().st_size / 1e6:.1f} MB")
    elif args.command == "import":
        print(dict(L.import_snapshot(data_dir, args.source)) or "nothing new")
        B.rebuild(data_dir)
    elif args.command == "check":
        checks = B.recheck(ApifyClient(token()), data_dir, args.batch_id)
        print((data_dir / "batches" / args.batch_id / "CHECKS.md").read_text(encoding="utf-8"))
        sys.exit(2 if C.failed(checks) or C.stop_all(checks) else 0)


if __name__ == "__main__":
    main()
