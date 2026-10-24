"""Step 03b: read care tags in listing photos for listings that state no fabric (Claude Haiku, ~$0.0005 each).

  uv run python pipeline/03b_tags.py --dry-run          # how many listings would be read, and the cost (free)
  uv run python pipeline/03b_tags.py [--limit 500]      # needs ANTHROPIC_API_KEY (repo root .env or environment)

Answers are cached in data/tags.jsonl, so rerun it after every rebuild of listings.jsonl: cached tags are re-applied
for free and only new listings are paid for."""
import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

import jsonl
import tags

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", action="store_true", help="work on data/test/")
    ap.add_argument("--data-dir", type=Path, help="work here instead of pipeline/data")
    ap.add_argument("--limit", type=int, help="read at most this many new listings (caps the spend)")
    ap.add_argument("--dry-run", action="store_true", help="count and estimate only")
    args = ap.parse_args()
    data = args.data_dir or HERE / "data" / ("test" if args.test else "")
    cache = data / "tags.jsonl"
    if args.dry_run:
        done = {d["id"] for d in (jsonl.load(cache) if cache.exists() else []) if not d.get("error")}
        new = sum(tags.needs_tag(r) and r["id"] not in done for r in jsonl.load(data / "listings.jsonl"))
        n = min(new, args.limit) if args.limit is not None else new
        print(f"{new} listings need a tag read ({len(done)} already answered); this run: {n}, about ${n * tags.USD_PER_LISTING:.2f}")
        return
    load_dotenv(HERE.parents[1] / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set (repo root .env or environment)")
    print(dict(tags.tag_file(data / "listings.jsonl", cache, limit=args.limit)))


if __name__ == "__main__":
    main()
