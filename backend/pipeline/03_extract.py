"""Step 03: data/normalized.jsonl -> data/listings.jsonl (materials, certifications, flags, evidence).

  uv run python pipeline/03_extract.py [--test]
"""
import argparse
from pathlib import Path

import extract

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", action="store_true", help="work on data/test/ (the go/no-go run)")
    data = HERE / "data" / ("test" if ap.parse_args().test else "")
    print(dict(extract.extract_file(data / "normalized.jsonl", data / "listings.jsonl")))


if __name__ == "__main__":
    main()
