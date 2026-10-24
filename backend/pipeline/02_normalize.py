"""Step 02: raw actor files -> data/normalized.jsonl (one row per listing, newest copy wins).

  uv run python pipeline/02_normalize.py [--test]
"""
import argparse
from pathlib import Path

from normalize import depop, ebay, grailed, poshmark
from normalize.run import normalize_all

HERE = Path(__file__).resolve().parent
MAPPERS = {"depop": depop.map_item, "poshmark": poshmark.map_item, "grailed": grailed.map_item, "ebay": ebay.map_item}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", action="store_true", help="work on data/test/ (the go/no-go run)")
    stats = normalize_all(HERE / "data" / ("test" if ap.parse_args().test else ""), MAPPERS)
    for key, n in sorted(stats.items()):
        print(f"{key:40} {n}")


if __name__ == "__main__":
    main()
