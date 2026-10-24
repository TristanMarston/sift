"""Step 01: scrape the marketplaces with Apify. Rerunnable: finished queries are skipped.

  uv run python pipeline/01_scrape.py --dry-run          # plan + cost estimate, calls nothing
  uv run python pipeline/01_scrape.py --test             # go/no-go: 1 query x 20 items per marketplace -> data/test/
  uv run python pipeline/01_scrape.py --max-spend 100    # the real run, stops before the estimated spend passes $100
"""
import argparse
import os
import sys
from decimal import Decimal
from pathlib import Path

from apify_client import ApifyClient
from dotenv import load_dotenv

import scrape

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", action="store_true", help="20 items from the first query of each marketplace")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and cost estimate, call nothing")
    ap.add_argument("--only", help="comma-separated marketplaces, e.g. depop,ebay")
    ap.add_argument("--max-spend", type=Decimal, help="stop before the estimated spend (USD) would pass this")
    args = ap.parse_args()

    cfg = scrape.load_config(HERE / "queries.yaml")
    only = args.only.split(",") if args.only else None
    unknown = set(only or []) - set(scrape.ACTORS)
    if unknown:
        sys.exit(f"unknown marketplace: {', '.join(sorted(unknown))}")
    plan = scrape.smoke_plan(cfg.queries) if args.test else scrape.build_plan(cfg.queries)
    plan = [t for t in plan if only is None or t.marketplace in only]
    quotas = None if args.test else cfg.quotas
    data_dir = HERE / "data" / ("test" if args.test else "")

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
        sys.exit("APIFY_TOKEN is not set (put it in /workspace/.env)")
    scrape.run_plan(ApifyClient(os.environ["APIFY_TOKEN"]), plan, quotas, data_dir, args.max_spend)


if __name__ == "__main__":
    main()
