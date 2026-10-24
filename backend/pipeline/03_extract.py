"""Step 03: data/normalized.jsonl -> data/listings.jsonl (materials, certifications, flags, evidence).

  uv run python pipeline/03_extract.py [--test] [--data-dir PATH]
"""
import argparse
from pathlib import Path

import extract

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", action="store_true", help="work on data/test/ (the go/no-go run)")
    ap.add_argument("--data-dir", type=Path, help="work here instead of pipeline/data (or data/test with --test)")
    args = ap.parse_args()
    data = args.data_dir or HERE / "data" / ("test" if args.test else "")
    print(dict(extract.extract_file(data / "normalized.jsonl", data / "listings.jsonl")))


if __name__ == "__main__":
    main()
