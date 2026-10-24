"""Step 03c: add Depop shipping per listing (Apify parsebird/depop-scraper, ~$0.0016 each). Cached by listing id.

  uv run python pipeline/03c_depop_shipping.py --dry-run     # how many listings and the cost (free)
  uv run python pipeline/03c_depop_shipping.py [--limit 500] # needs APIFY_TOKEN (repo root .env)

Rerun it after every rebuild of listings.jsonl: cached answers are re-applied for free."""
import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

import depop_shipping as D
import jsonl

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", action="store_true", help="work on data/test/")
    ap.add_argument("--data-dir", type=Path, help="work here instead of pipeline/data")
    ap.add_argument("--limit", type=int, help="fetch at most this many new listings (caps the spend)")
    ap.add_argument("--dry-run", action="store_true", help="count and estimate only")
    args = ap.parse_args()
    data = args.data_dir or HERE / "data" / ("test" if args.test else "")
    cache = data / "depop_shipping.jsonl"
    if args.dry_run:
        done = {d["id"] for d in (jsonl.load(cache) if cache.exists() else [])}
        new = sum(D.needs_shipping(r) and r["external_id"] not in done for r in jsonl.load(data / "listings.jsonl"))
        n = min(new, args.limit) if args.limit is not None else new
        print(f"{new} Depop listings need shipping ({len(done)} already answered); this run: {n}, about ${n * D.USD_PER_LISTING:.2f}")
        return
    load_dotenv(HERE.parents[1] / ".env")
    if not os.environ.get("APIFY_TOKEN"):
        raise SystemExit("APIFY_TOKEN is not set (repo root .env)")
    print(dict(D.ship_file(data / "listings.jsonl", cache, limit=args.limit)))


if __name__ == "__main__":
    main()
