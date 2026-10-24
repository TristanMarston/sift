"""Step 04: coverage stats and the acceptance checklist for data/listings.jsonl -> pipeline/REPORT.md.

  uv run python pipeline/04_report.py [--test] [--data-dir PATH] [--min-rows N]
"""
import argparse
import sys
from datetime import date
from pathlib import Path

import jsonl
import report
from listing import Listing

HERE = Path(__file__).resolve().parent


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", action="store_true", help="work on data/test/ (the go/no-go run); writes there, not REPORT.md")
    ap.add_argument("--data-dir", type=Path, help="work here instead of pipeline/data; writes REPORT.md there")
    ap.add_argument("--min-rows", type=int, default=20_000, help="active rows needed to pass (default 20000)")
    args = ap.parse_args()
    data = args.data_dir or HERE / "data" / ("test" if args.test else "")
    listings = [Listing.model_validate_json(line) for line in jsonl.read(data / "listings.jsonl")]
    s = report.stats(listings)
    md = report.render(s, report.acceptance(s, listings, args.min_rows), date.today().isoformat())
    (data / "REPORT.md" if args.test or args.data_dir else HERE / "REPORT.md").write_text(md, encoding="utf-8", newline="\n")
    print(md)


if __name__ == "__main__":
    main()
