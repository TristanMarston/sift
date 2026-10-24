"""Step 01: scrape the marketplaces with Apify. Rerunnable: finished queries are skipped, bad runs are retried.

  uv run python pipeline/01_scrape.py --dry-run          # plan + cost estimate, calls nothing
  uv run python pipeline/01_scrape.py --test             # go/no-go: 1 query x 20 items per marketplace -> data/test/
  uv run python pipeline/01_scrape.py --max-spend 120    # the real run, stops before the estimated spend passes $120

Every run is judged as it finishes (see BLOCKING.md). A bad one prints an `ALERT` line at once and is appended to
alerts.jsonl; a block or junk data stops that marketplace immediately, a second empty or failed run in a row stops it
too. Create <data folder>/STOP to halt before the next run. A report is printed and saved (run_report.md/.json).
Exit code: 0 finished, 2 a marketplace was stopped, 3 --max-spend, 4 STOP file, 130 Ctrl-C.
"""
import argparse
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from apify_client import ApifyClient
from dotenv import load_dotenv

import health
import scrape
import scrape_report
from normalize.mappers import MAPPERS

HERE = Path(__file__).resolve().parent


def main():
    sys.stdout.reconfigure(encoding="utf-8")   # the report has non-ASCII characters; Windows log files are cp1252 otherwise
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", action="store_true", help="20 items from the first query of each marketplace")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and cost estimate, call nothing")
    ap.add_argument("--only", help="comma-separated marketplaces, e.g. depop,ebay")
    ap.add_argument("--max-spend", type=Decimal, help="stop before the estimated spend (USD) would pass this")
    ap.add_argument("--stop-all-on-block", action="store_true", help="a block or junk data halts every marketplace, not just that one")
    ap.add_argument("--data-dir", type=Path, help="write here instead of pipeline/data (or data/test with --test)")
    args = ap.parse_args()

    cfg = scrape.load_config(HERE / "queries.yaml")
    only = args.only.split(",") if args.only else None
    unknown = set(only or []) - set(scrape.ACTORS)
    if unknown:
        sys.exit(f"unknown marketplace: {', '.join(sorted(unknown))}")
    plan = scrape.smoke_plan(cfg.queries) if args.test else scrape.build_plan(cfg.queries)
    plan = [t for t in plan if only is None or t.marketplace in only]
    quotas = None if args.test else cfg.quotas
    data_dir = args.data_dir or HERE / "data" / ("test" if args.test else "")

    if args.dry_run:
        total_est = total_cap = Decimal(0)
        print(f"{'marketplace':10} {'runs':>5} {'rows':>7} {'best-case $':>12} {'max (caps) $':>13}")
        for mp, e in scrape.estimate(plan, quotas).items():
            print(f"{mp:10} {e['runs']:>5} {e['rows']:>7} {e['est_usd']:>12.2f} {e['cap_usd']:>13.2f}")
            total_est += e["est_usd"]
            total_cap += e["cap_usd"]
        print(f"{'total':10} {'':>5} {'':>7} {total_est:>12.2f} {total_cap:>13.2f}")
        return

    load_dotenv(HERE.parents[1] / ".env")
    if not os.environ.get("APIFY_TOKEN"):
        sys.exit(f"APIFY_TOKEN is not set (put it in {HERE.parents[1] / '.env'})")
    started = datetime.now(timezone.utc)

    def classify(task, raw):   # judge each saved row with the marketplace's own mapper
        return health.classify_row(MAPPERS[task.marketplace], raw, task.category, started)

    summary = scrape.run_plan(ApifyClient(os.environ["APIFY_TOKEN"]), plan, quotas, data_dir, args.max_spend,
                              classify=classify, stop_all_on_block=args.stop_all_on_block)
    print("\n" + scrape_report.render(summary), flush=True)
    sys.exit(scrape_report.exit_code(summary))


if __name__ == "__main__":
    main()
