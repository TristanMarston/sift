"""Step 02: raw actor files -> data/normalized.jsonl (one row per listing, newest copy wins).

  uv run python pipeline/02_normalize.py [--test] [--data-dir PATH]
"""
import argparse
from pathlib import Path

from normalize.mappers import MAPPERS
from normalize.run import normalize_all

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", action="store_true", help="work on data/test/ (the go/no-go run)")
    ap.add_argument("--data-dir", type=Path, help="work here instead of pipeline/data (or data/test with --test)")
    args = ap.parse_args()
    stats = normalize_all(args.data_dir or HERE / "data" / ("test" if args.test else ""), MAPPERS)
    for key, n in sorted(stats.items()):
        print(f"{key:40} {n}")


if __name__ == "__main__":
    main()
